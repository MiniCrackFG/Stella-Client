import logging
import requests
import json
import os
import shutil
import stat
import subprocess
import threading
from pathlib import Path

from launcher.storage import load_json, save_json

logger = logging.getLogger(__name__)

MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")
MODS_DIR = Path(MINECRAFT_DIR) / "mods"
_install_lock = threading.Lock()

# Registros de versiones anteriores. Se adoptan solo la primera vez que una
# instancia no tiene todavía el suyo, para no perder lo ya instalado.
LEGACY_REGISTRY_FILES = (
    Path(MINECRAFT_DIR) / "installed_mods.json",
    Path(MINECRAFT_DIR) / "instances" / "installed_mods.json",
)

# Carpeta real de cada tipo de proyecto de Modrinth
TYPE_DIRS = {
    "mod": "mods",
    "resourcepack": "resourcepacks",
    "shader": "shaderpacks",
    "modpack": "modpacks",
}
TYPE_EXTENSIONS = {
    "mod": (".jar",),
    "resourcepack": (".zip",),
    "shader": (".zip",),
    "modpack": (".mrpack", ".zip"),
}
LOADERLESS_TYPES = ("resourcepack", "shader", "datapack", "modpack")
_SORT_OPTIONS = {"relevance", "downloads", "follows", "newest", "updated"}


def get_mods_dir():
    env = os.environ.get("STELLA_MODS_DIR")
    p = Path(env) if env else MODS_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_base_dir():
    """Directorio raíz de la instancia, el que contiene mods/, resourcepacks/, etc."""
    mods_dir = get_mods_dir()
    return mods_dir.parent if mods_dir.name == "mods" else mods_dir


def get_content_dir(project_type=None, create=True):
    dest = get_base_dir() / TYPE_DIRS.get(project_type or "mod", "mods")
    if create:
        dest.mkdir(parents=True, exist_ok=True)
    return dest


def _content_dirs(create=False):
    return [get_content_dir(t, create=create) for t in TYPE_DIRS]


def _find_installed_file(filename):
    if not filename:
        return None
    for folder in _content_dirs(create=False):
        candidate = folder / filename
        if candidate.is_file():
            return candidate
    return None


def get_registry_file():
    """Cada instancia guarda su registro junto a sus carpetas de contenido."""
    return get_base_dir() / "installed_mods.json"


def _read_registry():
    current = load_json(get_registry_file(), None)
    if isinstance(current, dict):
        return current
    # Primera lectura de esta instancia: adoptamos el registro antiguo (global)
    migrated = {}
    for path in LEGACY_REGISTRY_FILES:
        legacy = load_json(path, {})
        if isinstance(legacy, dict):
            migrated.update(legacy)
    return migrated


def _write_registry(data):
    save_json(get_registry_file(), data)


def _entry_filename(entry):
    if isinstance(entry, str):
        return entry
    return (entry or {}).get("filename", "")


def _download_file(url, dest, timeout=60):
    """Descarga a un temporal y renombra al final: nunca deja un archivo a medias."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            expected = resp.headers.get("Content-Length")
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        if expected is not None and tmp.stat().st_size != int(expected):
            tmp.unlink(missing_ok=True)
            return False, "descarga incompleta"
        os.replace(tmp, dest)
        return True, None
    except Exception as e:
        logger.error(f"Download error: {e}")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False, str(e)


def save_installed_mod_info(mod_id, filename, project_type="mod", thumbnail=""):
    with _install_lock:
        data = _read_registry()
        data[mod_id] = {"filename": filename, "project_type": project_type, "thumbnail": thumbnail}
        _write_registry(data)


def remove_installed_mod_info(filename):
    """Quita del registro las entradas que apuntan al archivo indicado."""
    if not filename:
        return 0
    with _install_lock:
        data = _read_registry()
        stale = [mod_id for mod_id, entry in data.items() if _entry_filename(entry) == filename]
        if not stale:
            return 0
        for mod_id in stale:
            del data[mod_id]
        _write_registry(data)
        return len(stale)


def _facets(project_type, loader, version):
    """Modrinth: array externo = AND, interno = OR."""
    facets = [[f"project_type:{project_type or 'mod'}"]]
    if loader and project_type not in LOADERLESS_TYPES:
        facets.append([f"categories:{loader}"])
    if version:
        facets.append([f"versions:{version}"])
    return facets


def _hit_to_result(hit, version, project_type):
    """Normaliza un hit de Modrinth. Único sitio donde se decide la versión que
    se muestra: la pedida si el proyecto la soporta, si no la más antigua que
    traiga el hit (nunca basura tipo 'Unknown' salvo que no haya nada)."""
    versions = hit.get("versions") or []
    if version and version in versions:
        best_version = version
    else:
        best_version = versions[0] if versions else (version or "Unknown")
    return {
        "name": hit.get("title", ""),
        "description": hit.get("description", ""),
        "mod_id": hit.get("project_id", ""),
        "version": best_version,
        "downloads": hit.get("downloads", 0),
        "thumbnail": hit.get("icon_url") or hit.get("thumbnail_url", ""),
        "project_type": hit.get("project_type", project_type),
        "source": "modrinth",
    }


def search_modrinth(query, version="1.20.1", loader="fabric", project_type="mod", offset=0, limit=15, sort="downloads"):
    if sort not in _SORT_OPTIONS:
        sort = "relevance"
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "index": sort,
        "facets": json.dumps(_facets(project_type, loader, version)),
    }
    try:
        resp = requests.get("https://api.modrinth.com/v2/search", params=params, timeout=10)
        if resp.status_code != 200:
            logger.info(f"Modrinth search failed: HTTP {resp.status_code}")
            return {"results": [], "total_hits": 0, "error": f"Modrinth respondió HTTP {resp.status_code}"}
        data = resp.json()
        results = [_hit_to_result(hit, version, project_type) for hit in data.get("hits", [])]
        return {"results": results, "total_hits": data.get("total_hits", 0)}
    except Exception as e:
        logger.info(f"Error searching Modrinth: {e}")
        return {"results": [], "total_hits": 0, "error": f"No se pudo conectar con Modrinth: {e}"}


def get_mod_versions(mod_id, mc_version="1.20.1", prefer_loader="fabric", project_type="mod"):
    """Solo devuelve versiones compatibles con la MC (y el loader) pedidos, sin fallbacks a ciegas."""
    if not mod_id:
        return None
    try:
        url = f"https://api.modrinth.com/v2/project/{mod_id}/version"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            logger.info(f"Modrinth versions failed for {mod_id}: HTTP {resp.status_code}")
            return None
        matches = [v for v in resp.json() if mc_version in v.get("game_versions", [])]
        if project_type not in LOADERLESS_TYPES and prefer_loader:
            matches = [v for v in matches if prefer_loader in v.get("loaders", [])]
        if not matches:
            return None
        v = matches[0]
        return {"version_id": v.get("id", ""), "version_name": v.get("name", ""), "files": v.get("files", []), "dependencies": v.get("dependencies", [])}
    except Exception as e:
        logger.info(f"Error getting mod versions: {e}")
        return None


def _is_mod_installed(mod_id):
    info = _read_registry().get(mod_id)
    if not info:
        return False
    return _find_installed_file(_entry_filename(info)) is not None


def download_mod_with_deps(mod_id, mc_version="1.20.1", project_type="mod", thumbnail="", _depth=0, prefer_loader="fabric"):
    if _depth > 5:
        logger.info(f"Max dependency depth reached for {mod_id}")
        return {"ok": False, "error": "Cadena de dependencias demasiado larga"}
    if _is_mod_installed(mod_id):
        logger.info(f"{mod_id} already installed")
        return {"ok": True, "already_installed": True}

    version_info = get_mod_versions(mod_id, mc_version, prefer_loader, project_type)
    if not version_info:
        return {"ok": False, "error": f"No hay versión compatible con Minecraft {mc_version}"}

    for dep in version_info.get("dependencies", []):
        if dep.get("dependency_type") == "required":
            dep_id = dep.get("project_id")
            if dep_id and dep_id != mod_id and not _is_mod_installed(dep_id):
                logger.info(f"Installing dependency {dep_id}...")
                dep_thumb = ""
                try:
                    dr = requests.get(f"https://api.modrinth.com/v2/project/{dep_id}", timeout=10)
                    if dr.status_code == 200:
                        dep_thumb = dr.json().get("icon_url", "") or ""
                except Exception:
                    pass
                download_mod_with_deps(dep_id, mc_version, project_type, dep_thumb, _depth + 1, prefer_loader)

    files = version_info.get("files") or []
    if not files:
        return {"ok": False, "error": "El proyecto no publica archivos"}

    primary = next((f for f in files if f.get("primary")), files[0])
    download_url = primary.get("url", "")
    filename = primary.get("filename", f"{mod_id}.jar")
    if not download_url:
        return {"ok": False, "error": "El archivo no tiene URL de descarga"}

    dest_dir = get_content_dir(project_type)
    logger.info(f"Downloading {filename} to {dest_dir}...")
    ok, error = _download_file(download_url, dest_dir / filename)
    if not ok:
        return {"ok": False, "error": f"No se pudo descargar {filename}: {error}"}

    save_installed_mod_info(mod_id, filename, project_type, thumbnail)
    logger.info(f"Downloaded {filename}")
    return {"ok": True, "path": str(dest_dir / filename), "filename": filename}


def get_trending_mods(version="1.20.4", loader="fabric", limit=15, project_type="mod", offset=0, sort="downloads"):
    if sort not in _SORT_OPTIONS:
        sort = "downloads"
    params = {
        "query": "",
        "limit": limit,
        "offset": offset,
        "index": sort,
        "facets": json.dumps(_facets(project_type, loader, version)),
    }
    try:
        resp = requests.get("https://api.modrinth.com/v2/search", params=params, timeout=10)
        if resp.status_code != 200:
            logger.info(f"Modrinth trending failed: HTTP {resp.status_code}")
            return {"results": [], "total_hits": 0, "error": f"Modrinth respondió HTTP {resp.status_code}"}
        data = resp.json()
        return {
            "results": [_hit_to_result(hit, version, project_type) for hit in data.get("hits", [])],
            "total_hits": data.get("total_hits", 0),
        }
    except Exception as e:
        logger.info(f"Error getting trending mods: {e}")
        return {"results": [], "total_hits": 0, "error": f"No se pudo conectar con Modrinth: {e}"}


def download_mod(mod_id, mc_version="1.20.1", source="modrinth", project_type="mod", thumbnail="", prefer_loader="fabric"):
    if source != "modrinth":
        return {"ok": False, "error": "Forge no está soportado todavía"}
    return download_mod_with_deps(mod_id, mc_version, project_type, thumbnail, 0, prefer_loader)


def get_installed_mods(project_type=None):
    installed_map = _read_registry()

    def _get_info(entry):
        if isinstance(entry, str):
            return {"filename": entry, "project_type": None, "thumbnail": ""}
        return entry or {}

    by_filename = {}
    for mid, entry in installed_map.items():
        info = _get_info(entry)
        if info.get("filename"):
            by_filename[info["filename"]] = (mid, info)

    types = [project_type] if project_type else list(TYPE_DIRS)
    results = []
    for ptype in types:
        extensions = TYPE_EXTENSIONS.get(ptype, (".jar", ".zip"))
        folder = get_content_dir(ptype, create=False)
        if not folder.exists():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file() or f.suffix.lower() not in extensions:
                continue
            mod_id, info = by_filename.get(f.name, (None, {}))
            entry_type = info.get("project_type") or ptype
            if project_type and entry_type != project_type:
                continue
            results.append({
                "name": f.stem,
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "mod_id": mod_id,
                "project_type": entry_type,
                "thumbnail": info.get("thumbnail", ""),
            })
    return results


def delete_mod(filename):
    name = Path(str(filename)).name
    if not name or name in (".", ".."):
        return False
    for folder in _content_dirs(create=False):
        filepath = folder / name
        if filepath.is_file():
            filepath.unlink()
            remove_installed_mod_info(name)
            logger.info(f"Deleted {name}")
            return True
    return False


STELLA_MOD_DIR = Path(__file__).parent.parent.parent / "stella-client-mod"
STELLA_JAR_NAME = "stella-client.jar"
_STELLA_BUILD_TIMEOUT = 90
_stella_build_failed = False


def _newest_mtime(path):
    """Fecha del archivo más reciente dentro de `path` (None si no existe)."""
    path = Path(path)
    if not path.exists():
        return None
    skip = {"build", ".git", ".gradle", "run", "out"}
    newest = path.stat().st_mtime
    for item in path.rglob("*"):
        if any(part in skip for part in item.parts):
            continue
        try:
            if item.is_file():
                newest = max(newest, item.stat().st_mtime)
        except OSError:
            pass
    return newest


def build_stella_mod():
    """Compila el mod Stella con Gradle. Como mucho se intenta una vez por ejecución,
    para que un fallo no cueste 90 s en cada arranque."""
    global _stella_build_failed
    mod_dir = STELLA_MOD_DIR
    if not mod_dir.exists():
        logger.info(f"Stella mod sources not found at {mod_dir}; se usará el jar ya instalado")
        return None
    if _stella_build_failed:
        logger.info("Stella mod build already failed in this run; skipping")
        return None

    gradlew = mod_dir / "gradlew"
    if gradlew.exists() and not os.access(str(gradlew), os.X_OK):
        gradlew.chmod(gradlew.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    logger.info(f"Building Stella mod in {mod_dir}...")
    try:
        result = subprocess.run(
            [str(gradlew), "build"],
            cwd=str(mod_dir),
            capture_output=True, text=True, timeout=_STELLA_BUILD_TIMEOUT
        )
        if result.returncode != 0:
            _stella_build_failed = True
            logger.error(f"Stella mod build failed:\n{result.stderr}")
            return None

        jars = list((mod_dir / "build" / "libs").glob("*.jar"))
        mod_jar = next((j for j in jars if not j.name.endswith("-sources.jar")), None)
        if mod_jar and mod_jar.exists():
            logger.info(f"Stella mod built: {mod_jar}")
            return str(mod_jar)
    except subprocess.TimeoutExpired:
        _stella_build_failed = True
        logger.error(f"Stella mod build timed out after {_STELLA_BUILD_TIMEOUT}s; no se reintenta en esta ejecución")
    except Exception as e:
        _stella_build_failed = True
        logger.error(f"Build error: {e}")
    return None


FABRIC_API_MODRINTH_ID = "P7dR8mSH"


def _get_instance_mods_dir():
    settings_path = os.path.expanduser("~/.stellaclient/config.json")
    if not os.path.exists(settings_path):
        return None
    try:
        with open(settings_path) as f:
            settings = json.load(f)
        iid = settings.get("current_instance")
        if not iid:
            return None
        instances_path = os.path.expanduser("~/.stellaclient/instances/instances.json")
        if not os.path.exists(instances_path):
            return None
        with open(instances_path) as f:
            instances_data = json.load(f)
        inst = instances_data.get(iid)
        if inst and inst.get("mods_dir"):
            mods_dir = Path(inst["mods_dir"])
            mods_dir.mkdir(parents=True, exist_ok=True)
            return mods_dir
    except Exception:
        pass
    return None


def install_stella_mod(force=False):
    """Deja el mod Stella en la instancia activa.

    Si el jar instalado es más reciente que las fuentes no se compila nada, así que
    el arranque no se bloquea (antes cada lanzamiento podía esperar hasta 2 minutos).
    """
    mods_dir = _get_instance_mods_dir() or get_mods_dir()
    dest = mods_dir / STELLA_JAR_NAME

    try:
        settings = load_json(os.path.expanduser("~/.stellaclient/config.json"), {})
        _ensure_fabric_api_in(mods_dir, settings.get("version", "1.21.11"))
    except Exception as e:
        logger.info(f"Could not prepare Fabric API: {e}")

    if not force and dest.exists():
        newest_source = _newest_mtime(STELLA_MOD_DIR)
        if newest_source is None or dest.stat().st_mtime >= newest_source:
            logger.info("Stella mod ya está al día; no se recompila")
            return str(dest)

    jar_path = build_stella_mod()
    if not jar_path:
        # Nunca dejamos el arranque sin mod si ya había uno instalado
        return str(dest) if dest.exists() else None

    shutil.copy2(jar_path, dest)
    logger.info(f"Installed Stella mod to {dest}")
    return str(dest)


def _ensure_fabric_api_in(mods_dir, mc_version):
    for f in mods_dir.glob("fabric-api*.jar"):
        logger.info(f"Fabric API already installed: {f.name}")
        return True

    logger.info("Downloading Fabric API...")
    version_info = get_mod_versions(FABRIC_API_MODRINTH_ID, mc_version, "fabric", "mod")
    if not version_info:
        logger.info(f"Fabric API has no build for Minecraft {mc_version}")
        return False

    files = version_info.get("files") or []
    if not files:
        return False

    primary = next((f for f in files if f.get("primary")), files[0])
    download_url = primary.get("url", "")
    filename = primary.get("filename", "fabric-api.jar")
    if not download_url:
        return False

    ok, error = _download_file(download_url, Path(mods_dir) / filename)
    if not ok:
        logger.error(f"Failed to download Fabric API: {error}")
        return False
    logger.info(f"Downloaded Fabric API: {filename}")
    return True
