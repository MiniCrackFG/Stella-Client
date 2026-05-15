import logging
import subprocess
import minecraft_launcher_lib
import os
import json

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.expanduser("~/.stellaclient/config.json")
AUTH_FILE = os.path.expanduser("~/.stellaclient/auth.json")
MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")

MICROSOFT_CLIENT_ID = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"


def load_settings():
    default_settings = {
        "ram": 4,
        "version": "1.21.11",
        "username": "Player",
        "java_path": "java",
    }

    if not os.path.exists(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        save_settings(default_settings)
        return default_settings

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return default_settings


def save_settings(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_auth():
    if not os.path.exists(AUTH_FILE):
        return None
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_auth(data):
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=4)


def is_logged_in():
    auth = load_auth()
    return auth is not None and "mc_access_token" in auth


def get_device_code_info():
    import requests
    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "scope": "XboxLive.signin offline_access",
    }
    resp = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode",
        data=data, timeout=15,
    )
    return resp.json()


def _finish_auth(tokens):
    import minecraft_launcher_lib.microsoft_account as ma
    xbl = ma.authenticate_with_xbl(tokens["access_token"])
    uhs = xbl.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", "")
    xsts = ma.authenticate_with_xsts(xbl["Token"])
    mc = ma.authenticate_with_minecraft(uhs, xsts["Token"])
    profile = ma.get_profile(mc["access_token"])
    auth_info = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "xbl_token": xbl["Token"],
        "xsts_token": xsts["Token"],
        "mc_access_token": mc["access_token"],
        "uuid": profile["id"],
        "username": profile["name"],
    }
    save_auth(auth_info)
    return profile["name"]


def logout():
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)


def login_offline(username):
    logout()
    username = username.strip() or "Player"
    settings = load_settings()
    settings["username"] = username
    save_settings(settings)
    return username


def get_current_user():
    auth = load_auth()
    if auth and "username" in auth:
        return auth["username"]
    settings = load_settings()
    name = settings.get("username", "Player")
    return name if name else None


def get_offline_username():
    settings = load_settings()
    return settings.get("username", "Player")


def has_offline_account():
    settings = load_settings()
    return not is_logged_in() and settings.get("username", "Player") != "Player"


def clear_offline_account():
    settings = load_settings()
    settings["username"] = "Player"
    save_settings(settings)


def get_available_versions():
    try:
        manifest = minecraft_launcher_lib.utils.get_version_list()
        all_v = [v["id"] for v in manifest if v["type"] == "release"]
        filtered = [v for v in all_v if v.startswith(("26.", "1.8","1.9","1.10","1.11","1.12","1.13","1.14","1.15","1.16","1.17","1.18","1.19","1.20","1.21"))]
        def sort_key(v):
            parts = v.split(".")
            return [int(x) for x in parts]
        filtered.sort(key=sort_key, reverse=True)
        return filtered
    except Exception as e:
        logger.warning(f"Failed to fetch versions: {e}")
        return ["26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.1", "1.21", "1.20.4", "1.20.1", "1.20", "1.19.2", "1.18.2", "1.17.1", "1.16.5", "1.15.2", "1.14.4", "1.13.2", "1.12.2", "1.11.2", "1.10.2", "1.9.4", "1.8.9"]


def launch_minecraft():
    settings = load_settings()
    version = settings.get("version", "1.21.11")
    ram = settings.get("ram", 4)
    java_path = settings.get("java_path", "java")
    ram_argument = f"-Xmx{ram}G"
    game_dir = settings.get("minecraft_dir", MINECRAFT_DIR)

    logger.info("--- Launching Stella Client ---")
    logger.info(f"Version: {version}")
    logger.info(f"RAM: {ram_argument}")
    logger.info(f"Java: {java_path}")
    logger.info(f"Dir: {game_dir}")

    os.makedirs(game_dir, exist_ok=True)

    mods_dir = os.environ.get("STELLA_MODS_DIR", os.path.join(game_dir, "mods"))
    has_mods = os.path.isdir(mods_dir) and any(f.endswith(".jar") for f in os.listdir(mods_dir))

    if has_mods:
        logger.info(f"Installing Fabric for {version}...")
        try:
            minecraft_launcher_lib.fabric.install_fabric(version, game_dir)
            logger.info("Fabric installed")
        except Exception as e:
            logger.warning(f"Fabric install failed: {e}")
            has_mods = False

    if not has_mods:
        logger.info(f"Installing Minecraft {version} (vanilla)...")
        minecraft_launcher_lib.install.install_minecraft_version(version, game_dir)

    auth = load_auth()
    if auth and "mc_access_token" in auth:
        logger.info(f"Playing as: {auth['username']}")
        options = {
            "username": auth["username"],
            "uuid": auth["uuid"],
            "token": auth["mc_access_token"],
            "executablePath": java_path,
            "jvmArguments": [ram_argument, "-XX:+UseG1GC"],
        }
    else:
        logger.info("Playing offline")
        options = {
            "username": settings.get("username", "Player"),
            "uuid": "00000000000000000000000000000000",
            "token": "offline",
            "executablePath": java_path,
            "jvmArguments": [ram_argument, "-XX:+UseG1GC"],
        }

    if has_mods:
        loader_version = minecraft_launcher_lib.fabric.get_latest_loader_version()
        fabric_version = f"fabric-loader-{loader_version}-{version}"
        logger.info(f"Launching with Fabric: {fabric_version}")
        command = minecraft_launcher_lib.command.get_minecraft_command(fabric_version, game_dir, options)
    else:
        logger.info("Launching vanilla...")
        command = minecraft_launcher_lib.command.get_minecraft_command(version, game_dir, options)

    filtered = []
    skip_next = False
    for arg in command:
        if skip_next:
            skip_next = False
            continue
        if arg.startswith("--sun-misc-unsafe-memory-access"):
            continue
        filtered.append(arg)

    logger.info("Launching process...")
    try:
        subprocess.run(filtered)
    except Exception as e:
        logger.error(f"Failed to launch: {e}")


if __name__ == "__main__":
    launch_minecraft()
