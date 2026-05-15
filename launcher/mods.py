import logging
import requests
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")
MODS_DIR = Path(MINECRAFT_DIR) / "mods"
_install_lock = threading.Lock()


def _installed_file():
    mods_dir = get_mods_dir()
    return os.path.join(str(mods_dir.parent), "installed_mods.json")


def save_installed_mod_info(mod_id, filename, project_type="mod", thumbnail=""):
    with _install_lock:
        data = {}
        if os.path.exists(_installed_file()):
            with open(_installed_file()) as f:
                data = json.load(f)
        data[mod_id] = {"filename": filename, "project_type": project_type, "thumbnail": thumbnail}
        os.makedirs(os.path.dirname(_installed_file()), exist_ok=True)
        with open(_installed_file(), "w") as f:
            json.dump(data, f)

def get_mods_dir():
    env = os.environ.get("STELLA_MODS_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    return MODS_DIR

def search_modrinth(query, version="1.20.1", loader="fabric", project_type="mod", offset=0, limit=20):
    """Search for mods on Modrinth with version filtering and pagination"""
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
                best_version = None
                if versions:
                    for v in versions:
                        if v == version:
                            best_version = v
                            break
                    if not best_version and versions:
                        best_version = versions[0]
                loaders = hit.get("loaders", [])
                if loader in loaders or not loaders:
                    ptype = hit.get("project_type", project_type)
                    results.append({
                        "name": hit.get("title", ""),
                        "description": hit.get("description", ""),
                        "mod_id": mod_id,
                        "version": best_version or (versions[0] if versions else "Unknown"),
                        "downloads": hit.get("downloads", 0),
                        "thumbnail": hit.get("icon_url") or hit.get("thumbnail_url", ""),
                        "project_type": ptype,
                        "source": "modrinth"
                    })
            return {"results": results, "total_hits": data.get("total_hits", 0)}
    except Exception as e:
        logging.info(f"Error searching Modrinth: {e}")
    return {"results": [], "total_hits": 0}

def get_mod_versions(mod_id, mc_version="1.20.1", prefer_loader="fabric"):
    """Get all versions of a mod and return the one matching the MC version"""
    try:
        url = f"https://api.modrinth.com/v2/project/{mod_id}/version"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            versions = resp.json()
            # First try: matching MC version + preferred loader
            for v in versions:
                if mc_version in v.get("game_versions", []) and prefer_loader in v.get("loaders", []):
                    return {
                        "version_id": v.get("id", ""),
                        "version_name": v.get("name", ""),
                        "files": v.get("files", []),
                        "dependencies": v.get("dependencies", []),
                    }
            # Second try: matching MC version, any loader
            for v in versions:
                if mc_version in v.get("game_versions", []):
                    return {
                        "version_id": v.get("id", ""),
                        "version_name": v.get("name", ""),
                        "files": v.get("files", []),
                        "dependencies": v.get("dependencies", []),
                    }
            # Fallback: first available version
            if versions:
                return {
                    "version_id": versions[0].get("id", ""),
                    "version_name": versions[0].get("name", ""),
                    "files": versions[0].get("files", []),
                    "dependencies": versions[0].get("dependencies", []),
                }
    except Exception as e:
        logging.info(f"Error getting mod versions: {e}")
    return None


def _is_mod_installed(mod_id):
    if not os.path.exists(_installed_file()):
        return False
    with open(_installed_file()) as f:
        data = json.load(f)
    info = data.get(mod_id)
    if not info:
        return False
    filename = info.get("filename") if isinstance(info, dict) else info
    filepath = get_mods_dir() / filename
    return filepath.exists()


def download_mod_with_deps(mod_id, mc_version="1.20.1", project_type="mod", thumbnail="", _depth=0, prefer_loader="fabric"):
    """Download a mod and all its required dependencies recursively"""
    if _depth > 5:
        logging.info(f"Max dependency depth reached for {mod_id}")
        return None

    if _is_mod_installed(mod_id):
        logging.info(f"{mod_id} already installed, skipping")
        return None

    version_info = get_mod_versions(mod_id, mc_version, prefer_loader)
    if not version_info:
        logging.info(f"No compatible versions found for mod {mod_id}")
        return None

    # Install required dependencies first
    for dep in version_info.get("dependencies", []):
        if dep.get("dependency_type") == "required":
            dep_id = dep.get("project_id")
            if dep_id and dep_id != mod_id and not _is_mod_installed(dep_id):
                logging.info(f"Installing dependency {dep_id} for {mod_id}...")
                dep_thumb = ""
                try:
                    dr = requests.get(f"https://api.modrinth.com/v2/project/{dep_id}", timeout=10)
                    if dr.status_code == 200:
                        dep_thumb = dr.json().get("icon_url", "") or ""
                except: pass
                download_mod_with_deps(dep_id, mc_version, project_type, dep_thumb, _depth + 1, prefer_loader)

    # Download the mod itself
    files = version_info.get("files", [])
    if not files:
        logging.info(f"No files found for {mod_id}")
        return None

    download_url = files[0].get("url", "")
    filename = files[0].get("filename", f"{mod_id}.jar")
    if not download_url:
        logging.info(f"No download URL for {mod_id}")
        return None

    mods_dir = get_mods_dir()
    filepath = mods_dir / filename

    logging.info(f"Downloading {filename}...")
    mod_resp = requests.get(download_url, stream=True, timeout=60)
    if mod_resp.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in mod_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        save_installed_mod_info(mod_id, filename, project_type, thumbnail)
        logging.info(f"Downloaded {filename}")
        return str(filepath)
    else:
        logging.info(f"Failed to download {mod_id}: HTTP {mod_resp.status_code}")
        return None

FORGE_VERSIONS = {
    "1.21.11": "52.0.0",
    "1.21.10": "51.2.0",
    "1.21.9": "51.1.0",
    "1.21.8": "51.0.20",
    "1.21.5": "50.0.20",
    "1.21.4": "49.0.20",
    "1.21.3": "49.0.10",
    "1.21.1": "48.0.20",
    "1.21": "48.0.10",
    "1.20.4": "49.0.20",
    "1.20.2": "48.0.20",
    "1.20.1": "47.1.0",
    "1.20": "45.0.0",
    "1.19.4": "45.0.0",
    "1.19.3": "44.1.0",
    "1.19.2": "43.1.0",
    "1.18.2": "40.1.0",
    "1.17.1": "37.1.0",
    "1.16.5": "36.2.0"
}

def get_trending_mods(version="1.20.4", loader="fabric", limit=15, project_type="mod", offset=0):
    """Get trending mods from Modrinth with pagination"""
    url = "https://api.modrinth.com/v2/search"
    facets = [[f"project_type:{project_type}"]]
    if loader != "fabric":
        facets.append([f"categories:{loader}"])
    params = {
        "query": "",
        "limit": limit,
        "offset": offset,
        "index": "downloads",
        "facets": json.dumps(facets),
    }
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
        logging.info(f"Error getting trending mods: {e}")
    return {"results": [], "total_hits": 0}

def search_forge(mc_version="1.20.1"):
    """Get Forge installer for a specific Minecraft version"""
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

def get_forge_download_url(mc_version, installer_version=None):
    """Get the download URL for Forge"""
    if installer_version:
        return f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{mc_version}-{installer_version}/forge-{mc_version}-{installer_version}-installer.jar"
    return f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{mc_version}/forge-{mc_version}-latest-installer.jar"

def download_forge(mc_version):
    """Download Forge installer for a specific Minecraft version"""
    url = get_forge_download_url(mc_version)
    try:
        forge_dir = Path(MINECRAFT_DIR) / "forge"
        forge_dir.mkdir(parents=True, exist_ok=True)
        filename = f"forge-{mc_version}-installer.jar"
        filepath = forge_dir / filename
        
        logging.info(f"Downloading Forge installer...")
        resp = requests.get(url, stream=True, timeout=60)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Downloaded Forge to {filepath}")
            return str(filepath)
    except Exception as e:
        logging.info(f"Error downloading Forge: {e}")
    return None

def download_mod(mod_id, mc_version="1.20.1", source="modrinth", project_type="mod", thumbnail="", prefer_loader="fabric"):
    """Download a mod with automatic dependency resolution"""
    if source == "modrinth":
        return download_mod_with_deps(mod_id, mc_version, project_type, thumbnail, 0, prefer_loader)
    return None

def get_installed_mods(project_type=None):
    """Get list of installed mods, optionally filtered by project_type"""
    installed_map = {}
    if os.path.exists(_installed_file()):
        with open(_installed_file()) as f:
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

STELLA_MOD_DIR = Path(__file__).parent.parent.parent / "stella-client-mod"

def set_stella_mod_dir(path):
    global STELLA_MOD_DIR
    STELLA_MOD_DIR = Path(path)

def build_stella_mod():
    """Build the Stella Client mod using Gradle and return the jar path"""
    mod_dir = STELLA_MOD_DIR
    if not mod_dir.exists():
        logging.info(f"Stella mod directory not found at {mod_dir}")
        return None

    logging.info(f"Building Stella mod in {mod_dir}...")
    result = subprocess.run(
        [str(mod_dir / "gradlew"), "build"],
        cwd=str(mod_dir),
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        logging.error(f"Stella mod build failed:\n{result.stderr}")
        return None

    jars = list((mod_dir / "build" / "libs").glob("*.jar"))
    mod_jar = next((j for j in jars if not j.name.endswith("-sources.jar")), None)
    if mod_jar and mod_jar.exists():
        logging.info(f"Stella mod built: {mod_jar}")
        return str(mod_jar)
    return None


FABRIC_API_MODRINTH_ID = "P7dR8mSH"


def _get_instance_mods_dir():
    """Get the current instance mods directory from settings"""
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
    """Build and install the Stella Client mod into the current mods directory"""
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
    logging.info(f"Installed Stella mod to {mods_dir / 'stella-client.jar'}")
    return str(mods_dir / "stella-client.jar")


def _ensure_fabric_api_in(mods_dir, mc_version):
    """Download Fabric API from Modrinth if not already in the given directory"""
    for f in mods_dir.glob("fabric-api*.jar"):
        logging.info(f"Fabric API already installed: {f.name}")
        return True

    logging.info("Downloading Fabric API...")
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
            logging.info(f"Downloaded Fabric API: {filename}")
            return True
    except Exception as e:
        logging.error(f"Failed to download Fabric API: {e}")
    return False


def delete_mod(filename):
    """Delete an installed mod"""
    mods_dir = get_mods_dir()
    filepath = mods_dir / filename
    if filepath.exists():
        filepath.unlink()
        logging.info(f"Deleted {filename}")
        return True
    return False