import logging
import requests
import json
import os
import shutil
import stat
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")
MODS_DIR = Path(MINECRAFT_DIR) / "mods"
_INSTALLED_FILE = os.path.join(MINECRAFT_DIR, "instances", "installed_mods.json")
_install_lock = threading.Lock()


def get_mods_dir():
    env = os.environ.get("STELLA_MODS_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    return MODS_DIR


def save_installed_mod_info(mod_id, filename, project_type="mod", thumbnail=""):
    with _install_lock:
        data = {}
        if os.path.exists(_INSTALLED_FILE):
            with open(_INSTALLED_FILE) as f:
                data = json.load(f)
        data[mod_id] = {"filename": filename, "project_type": project_type, "thumbnail": thumbnail}
        os.makedirs(os.path.dirname(_INSTALLED_FILE), exist_ok=True)
        with open(_INSTALLED_FILE, "w") as f:
            json.dump(data, f)


def search_modrinth(query, version="1.20.1", loader="fabric", project_type="mod", offset=0, limit=20):
    url = "https://api.modrinth.com/v2/search"
    facets = [[f"project_type:{project_type}"]]
    if loader != "fabric":
        facets.append([f"categories:{loader}"])
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "facets": json.dumps(facets),
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                mod_id = hit.get("project_id", "")
                versions = hit.get("versions", [])
                best_version = next((v for v in versions if v == version), None) or (versions[0] if versions else None)
                loaders = hit.get("loaders", [])
                if loader in loaders or not loaders:
                    ptype = hit.get("project_type", project_type)
                    results.append({
                        "name": hit.get("title", ""),
                        "description": hit.get("description", ""),
                        "mod_id": mod_id,
                        "version": best_version or "Unknown",
                        "downloads": hit.get("downloads", 0),
                        "thumbnail": hit.get("icon_url") or hit.get("thumbnail_url", ""),
                        "project_type": ptype,
                        "source": "modrinth"
                    })
            return {"results": results, "total_hits": data.get("total_hits", 0)}
    except Exception as e:
        logger.info(f"Error searching Modrinth: {e}")
    return {"results": [], "total_hits": 0}


def get_mod_versions(mod_id, mc_version="1.20.1", prefer_loader="fabric"):
    try:
        url = f"https://api.modrinth.com/v2/project/{mod_id}/version"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            versions = resp.json()
            for v in versions:
                if mc_version in v.get("game_versions", []) and prefer_loader in v.get("loaders", []):
                    return {"version_id": v.get("id", ""), "version_name": v.get("name", ""), "files": v.get("files", []), "dependencies": v.get("dependencies", [])}
            for v in versions:
                if mc_version in v.get("game_versions", []):
                    return {"version_id": v.get("id", ""), "version_name": v.get("name", ""), "files": v.get("files", []), "dependencies": v.get("dependencies", [])}
            if versions:
                v = versions[0]
                return {"version_id": v.get("id", ""), "version_name": v.get("name", ""), "files": v.get("files", []), "dependencies": v.get("dependencies", [])}
    except Exception as e:
        logger.info(f"Error getting mod versions: {e}")
    return None


def _is_mod_installed(mod_id):
    if not os.path.exists(_INSTALLED_FILE):
        return False
    try:
        with open(_INSTALLED_FILE) as f:
            data = json.load(f)
        info = data.get(mod_id)
        if not info:
            return False
        filename = info.get("filename") if isinstance(info, dict) else info
        return (get_mods_dir() / filename).exists()
    except Exception:
        return False


def download_mod_with_deps(mod_id, mc_version="1.20.1", project_type="mod", thumbnail="", _depth=0, prefer_loader="fabric"):
    if _depth > 5:
        logger.info(f"Max dependency depth reached for {mod_id}")
        return None
    if _is_mod_installed(mod_id):
        logger.info(f"{mod_id} already installed")
        return None

    version_info = get_mod_versions(mod_id, mc_version, prefer_loader)
    if not version_info:
        logger.info(f"No compatible versions for {mod_id}")
        return None

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

    files = version_info.get("files", [])
    if not files:
        logger.info(f"No files for {mod_id}")
        return None

    download_url = files[0].get("url", "")
    filename = files[0].get("filename", f"{mod_id}.jar")
    if not download_url:
        logger.info(f"No download URL for {mod_id}")
        return None

    mods_dir = get_mods_dir()
    filepath = mods_dir / filename

    logger.info(f"Downloading {filename}...")
    try:
        mod_resp = requests.get(download_url, stream=True, timeout=60)
        if mod_resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in mod_resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            save_installed_mod_info(mod_id, filename, project_type, thumbnail)
            logger.info(f"Downloaded {filename}")
            return str(filepath)
        else:
            logger.info(f"Failed to download {mod_id}: HTTP {mod_resp.status_code}")
    except Exception as e:
        logger.error(f"Download error: {e}")
    return None


FORGE_VERSIONS = {
    "1.21.11": "52.0.0",
    "1.21.10": "51.2.0",
    "1.21.9": "51.1.0",
    "1.21.8": "51.0.20",
    "1.21.5": "50.0.20",
}


def get_trending_mods(version="1.20.4", loader="fabric", limit=15, project_type="mod", offset=0):
    url = "https://api.modrinth.com/v2/search"
    facets = [[f"project_type:{project_type}"]]
    if loader != "fabric":
        facets.append([f"categories:{loader}"])
    params = {"query": "", "limit": limit, "offset": offset, "index": "downloads", "facets": json.dumps(facets)}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "results": [{
                    "name": hit.get("title", ""),
                    "description": hit.get("description", ""),
                    "mod_id": hit.get("project_id", ""),
                    "version": hit.get("versions", ["Unknown"])[0] if hit.get("versions") else "Unknown",
                    "downloads": hit.get("downloads", 0),
                    "thumbnail": hit.get("icon_url") or hit.get("thumbnail_url", ""),
                    "project_type": hit.get("project_type", project_type),
                    "source": "modrinth"
                } for hit in data.get("hits", [])],
                "total_hits": data.get("total_hits", 0)
            }
    except Exception as e:
        logger.info(f"Error getting trending mods: {e}")
    return {"results": [], "total_hits": 0}


def search_forge(mc_version="1.20.1"):
    forge_versions = []
    version = FORGE_VERSIONS.get(mc_version)
    if version:
        forge_versions.append({
            "name": f"Forge {mc_version}",
            "description": f"Forge {version} for Minecraft {mc_version}",
            "version": version,
            "mc_version": mc_version,
            "source": "forge",
            "downloads": 0
        })
    return forge_versions


def download_mod(mod_id, mc_version="1.20.1", source="modrinth", project_type="mod", thumbnail="", prefer_loader="fabric"):
    if source == "modrinth":
        return download_mod_with_deps(mod_id, mc_version, project_type, thumbnail, 0, prefer_loader)
    return None


def download_forge(mc_version):
    logger.info(f"Forge download for {mc_version} not yet implemented")
    return None


def get_installed_mods(project_type=None):
    installed_map = {}
    if os.path.exists(_INSTALLED_FILE):
        with open(_INSTALLED_FILE) as f:
            installed_map = json.load(f)
    mods_dir = get_mods_dir()

    def _get_info(entry):
        if isinstance(entry, str):
            return {"filename": entry, "project_type": None, "thumbnail": ""}
        return entry

    mods = []
    for f in mods_dir.glob("*.jar"):
        entry = next((v for k, v in installed_map.items() if _get_info(v).get("filename") == f.name), None)
        info = _get_info(entry) if entry else None
        if project_type and (not info or info.get("project_type") != project_type):
            continue
        mod_id = next((k for k, v in installed_map.items() if _get_info(v).get("filename") == f.name), None)
        mods.append({
            "name": f.stem,
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "mod_id": mod_id,
            "project_type": info.get("project_type") if info else None,
            "thumbnail": info.get("thumbnail", "") if info else "",
        })
    return mods


def delete_mod(filename):
    mods_dir = get_mods_dir()
    filepath = mods_dir / filename
    if filepath.exists():
        filepath.unlink()
        logger.info(f"Deleted {filename}")
        return True
    return False


STELLA_MOD_DIR = Path(__file__).parent.parent.parent / "stella-client-mod"


def set_stella_mod_dir(path):
    global STELLA_MOD_DIR
    STELLA_MOD_DIR = Path(path)


def build_stella_mod():
    mod_dir = STELLA_MOD_DIR
    if not mod_dir.exists():
        logger.info(f"Stella mod directory not found at {mod_dir}")
        return None

    gradlew = mod_dir / "gradlew"
    if gradlew.exists() and not os.access(str(gradlew), os.X_OK):
        gradlew.chmod(gradlew.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    logger.info(f"Building Stella mod in {mod_dir}...")
    try:
        result = subprocess.run(
            [str(gradlew), "build"],
            cwd=str(mod_dir),
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.error(f"Stella mod build failed:\n{result.stderr}")
            return None

        jars = list((mod_dir / "build" / "libs").glob("*.jar"))
        mod_jar = next((j for j in jars if not j.name.endswith("-sources.jar")), None)
        if mod_jar and mod_jar.exists():
            logger.info(f"Stella mod built: {mod_jar}")
            return str(mod_jar)
    except subprocess.TimeoutExpired:
        logger.error("Stella mod build timed out")
    except Exception as e:
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


def install_stella_mod():
    mods_dir = _get_instance_mods_dir()
    if not mods_dir:
        mods_dir = get_mods_dir()

    try:
        settings_path = os.path.expanduser("~/.stellaclient/config.json")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                mc_version = json.load(f).get("version", "1.21.11")
        else:
            mc_version = "1.21.11"
        _ensure_fabric_api_in(mods_dir, mc_version)
    except Exception:
        pass

    jar_path = build_stella_mod()
    if not jar_path:
        return None

    shutil.copy2(jar_path, mods_dir / "stella-client.jar")
    logger.info(f"Installed Stella mod to {mods_dir / 'stella-client.jar'}")
    return str(mods_dir / "stella-client.jar")


def _ensure_fabric_api_in(mods_dir, mc_version):
    for f in mods_dir.glob("fabric-api*.jar"):
        logger.info(f"Fabric API already installed: {f.name}")
        return True

    logger.info("Downloading Fabric API...")
    version_info = get_mod_versions(FABRIC_API_MODRINTH_ID, mc_version, "fabric")
    if not version_info:
        return False

    files = version_info.get("files", [])
    if not files:
        return False

    download_url = files[0].get("url", "")
    filename = files[0].get("filename", "fabric-api.jar")
    if not download_url:
        return False

    filepath = mods_dir / filename
    try:
        resp = requests.get(download_url, stream=True, timeout=60)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded Fabric API: {filename}")
            return True
    except Exception as e:
        logger.error(f"Failed to download Fabric API: {e}")
    return False
