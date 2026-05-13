import requests
import json
import os
import threading
from pathlib import Path

MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")
MODS_DIR = Path(MINECRAFT_DIR) / "mods"
INSTALLED_MODS_FILE = os.path.join(MINECRAFT_DIR, "installed_mods.json")
_install_lock = threading.Lock()


def save_installed_mod_info(mod_id, filename, project_type="mod", thumbnail=""):
    with _install_lock:
        data = {}
        if os.path.exists(INSTALLED_MODS_FILE):
            with open(INSTALLED_MODS_FILE) as f:
                data = json.load(f)
        data[mod_id] = {"filename": filename, "project_type": project_type, "thumbnail": thumbnail}
        os.makedirs(os.path.dirname(INSTALLED_MODS_FILE), exist_ok=True)
        with open(INSTALLED_MODS_FILE, "w") as f:
            json.dump(data, f)

def get_mods_dir():
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    return MODS_DIR

def search_modrinth(query, version="1.20.1", loader="fabric", project_type="mod"):
    """Search for mods on Modrinth with version filtering"""
    url = "https://api.modrinth.com/v2/search"
    facets = [[f"project_type:{project_type}"]]
    if loader != "fabric":
        facets.append([f"categories:{loader}"])
    params = {
        "query": query,
        "limit": 20,
        "facets": json.dumps(facets),
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                # Get the best matching version for this mod
                mod_id = hit.get("project_id", "")
                versions = hit.get("versions", [])
                
                # Find version that matches the requested version
                best_version = None
                
                if versions:
                    for v in versions:
                        if v == version:
                            best_version = v
                            break
                    if not best_version and versions:
                        best_version = versions[0]
                
                # Only include mods that have at least the requested loader
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
            return results
    except Exception as e:
        print(f"Error searching Modrinth: {e}")
    return []

def get_mod_versions(mod_id, mc_version="1.20.1"):
    """Get all versions of a mod and return the one matching the MC version"""
    try:
        url = f"https://api.modrinth.com/v2/project/{mod_id}/version"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            versions = resp.json()
            # Find version that supports the requested MC version
            for v in versions:
                if mc_version in v.get("game_versions", []):
                    return {
                        "version_id": v.get("id", ""),
                        "version_name": v.get("name", ""),
                        "files": v.get("files", [])
                    }
            # If no exact match, return first available version
            if versions:
                return {
                    "version_id": versions[0].get("id", ""),
                    "version_name": versions[0].get("name", ""),
                    "files": versions[0].get("files", [])
                }
    except Exception as e:
        print(f"Error getting mod versions: {e}")
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

def get_trending_mods(version="1.20.4", loader="fabric", limit=15, project_type="mod"):
    """Get trending mods from Modrinth"""
    url = "https://api.modrinth.com/v2/search"
    facets = [[f"project_type:{project_type}"]]
    if loader != "fabric":
        facets.append([f"categories:{loader}"])
    params = {
        "query": "",
        "limit": limit,
        "index": "downloads",
        "facets": json.dumps(facets),
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return [{
                "name": hit.get("title", ""),
                "description": hit.get("description", ""),
                "mod_id": hit.get("project_id", ""),
                "version": hit.get("versions", ["Unknown"])[0] if hit.get("versions") else "Unknown",
                "downloads": hit.get("downloads", 0),
                "thumbnail": hit.get("icon_url") or hit.get("thumbnail_url", ""),
                "project_type": hit.get("project_type", project_type),
                "source": "modrinth"
            } for hit in data.get("hits", [])]
    except Exception as e:
        print(f"Error getting trending mods: {e}")
    return []

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
        
        print(f"Downloading Forge installer...")
        resp = requests.get(url, stream=True, timeout=60)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded Forge to {filepath}")
            return str(filepath)
    except Exception as e:
        print(f"Error downloading Forge: {e}")
    return None

def download_mod(mod_id, mc_version="1.20.1", source="modrinth", project_type="mod", thumbnail=""):
    """Download a mod from Modrinth, selecting the version that matches the MC version"""
    if source == "modrinth":
        try:
            # Get available versions for this mod
            version_info = get_mod_versions(mod_id, mc_version)
            if not version_info:
                print(f"No compatible versions found for mod {mod_id}")
                return None
            
            version_id = version_info.get("version_id", "")
            files = version_info.get("files", [])
            
            if not files:
                print(f"No files found for version {version_id}")
                return None
            
            # Get the first JAR file
            download_url = files[0].get("url", "")
            filename = files[0].get("filename", f"{mod_id}.jar")
            
            if not download_url:
                print(f"No download URL found")
                return None
            
            mods_dir = get_mods_dir()
            filepath = mods_dir / filename
            
            print(f"Downloading {filename}...")
            mod_resp = requests.get(download_url, stream=True, timeout=60)
            if mod_resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in mod_resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                save_installed_mod_info(mod_id, filename, project_type, thumbnail)
                print(f"\nSuccessfully downloaded to {filepath}")
                return str(filepath)
            else:
                print(f"Failed to download: HTTP {mod_resp.status_code}")
        except Exception as e:
            print(f"Error downloading mod: {e}")
    return None

def get_installed_mods(project_type=None):
    """Get list of installed mods, optionally filtered by project_type"""
    installed_map = {}
    if os.path.exists(INSTALLED_MODS_FILE):
        with open(INSTALLED_MODS_FILE) as f:
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
    """Delete an installed mod"""
    mods_dir = get_mods_dir()
    filepath = mods_dir / filename
    if filepath.exists():
        filepath.unlink()
        print(f"Deleted {filename}")
        return True
    return False