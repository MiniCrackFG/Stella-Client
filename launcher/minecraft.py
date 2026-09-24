import logging
import subprocess
import minecraft_launcher_lib
import os

from launcher.storage import load_json, save_json

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.expanduser("~/.stellaclient/config.json")
AUTH_FILE = os.path.expanduser("~/.stellaclient/auth.json")
MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")

MICROSOFT_CLIENT_ID = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"

DEFAULT_SETTINGS = {
    "ram": 4,
    "version": "1.21.11",
    "username": "Player",
    "java_path": "java",
}


def expand_path(value):
    """Convierte '~', variables de entorno y rutas relativas en una ruta absoluta."""
    if not isinstance(value, str) or not value.strip():
        return ""
    return os.path.abspath(os.path.expanduser(os.path.expandvars(value.strip())))


def load_settings():
    stored = load_json(CONFIG_FILE, {})
    if not isinstance(stored, dict):
        stored = {}
    settings = {**DEFAULT_SETTINGS, **stored}
    # Configuraciones antiguas pueden guardar '~/.stellaclient' tal cual
    if settings.get("minecraft_dir"):
        settings["minecraft_dir"] = expand_path(settings["minecraft_dir"])
    return settings


def save_settings(data):
    save_json(CONFIG_FILE, data)


def load_auth():
    auth = load_json(AUTH_FILE, None)
    return auth if isinstance(auth, dict) else None


def save_auth(data):
    save_json(AUTH_FILE, data)


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


def finish_microsoft_auth(tokens):
    """Cadena completa XBL → XSTS → Minecraft guardando la sesión.

    Único sitio con esta lógica (api.py delega aquí). Devuelve
    {"username", "uuid"} o {"error": <motivo>}.
    """
    try:
        import minecraft_launcher_lib.microsoft_account as ma
        xbl = ma.authenticate_with_xbl(tokens["access_token"])
        uhs = xbl.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", "")
        xsts = ma.authenticate_with_xsts(xbl["Token"])
        mc = ma.authenticate_with_minecraft(uhs, xsts["Token"])
        profile = ma.get_profile(mc["access_token"])
    except Exception as e:
        logger.warning(f"Microsoft auth failed: {e}")
        return {"error": str(e)}

    save_auth({
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "xbl_token": xbl["Token"],
        "xsts_token": xsts["Token"],
        "mc_access_token": mc["access_token"],
        "uuid": profile["id"],
        "username": profile["name"],
    })
    return {"username": profile["name"], "uuid": profile["id"]}


def offline_uuid(username):
    """UUID offline con el mismo cálculo que el servidor: md5('OfflinePlayer:<nombre>')."""
    import hashlib
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # versión 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # variante RFC 4122
    value = digest.hex()
    return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"


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


def game_dir_for(settings=None):
    settings = settings if settings is not None else load_settings()
    return expand_path(settings.get("minecraft_dir")) or MINECRAFT_DIR


def mods_dir_for(game_dir):
    return os.environ.get("STELLA_MODS_DIR") or os.path.join(game_dir, "mods")


def has_game_mods(game_dir):
    mods_dir = mods_dir_for(game_dir)
    try:
        return os.path.isdir(mods_dir) and any(f.endswith(".jar") for f in os.listdir(mods_dir))
    except OSError:
        return False


def is_version_installed(version, game_dir):
    """Comprueba barato (sin red) si el cliente de esa versión ya está en disco.

    Sirve para saber si el arranque va a tener que descargar algo y, con eso,
    decidir si tiene sentido mostrar la barra de progreso.
    """
    base = os.path.join(game_dir, "versions", version)
    return (os.path.isfile(os.path.join(base, version + ".json"))
            and os.path.isfile(os.path.join(base, version + ".jar")))


def launch_plan():
    """Qué va a hacer el arranque: versión, carpeta y si hace falta descargar.

    Sin llamadas de red a propósito: se ejecuta en el hilo del lanzamiento y solo
    mira el disco. Para Fabric se acepta cualquier perfil instalado de esa versión
    de Minecraft (el loader exacto lo decide la librería más tarde).
    """
    settings = load_settings()
    version = settings.get("version", "1.21.11")
    game_dir = game_dir_for(settings)
    has_mods = has_game_mods(game_dir)

    needs_download = not is_version_installed(version, game_dir)
    if has_mods and not needs_download:
        versions_dir = os.path.join(game_dir, "versions")
        suffix = f"-{version}"
        try:
            needs_download = not any(
                name.startswith("fabric-loader-") and name.endswith(suffix)
                and os.path.isdir(os.path.join(versions_dir, name))
                for name in os.listdir(versions_dir)
            )
        except OSError:
            needs_download = True

    return {
        "version": version,
        "game_dir": game_dir,
        "has_mods": has_mods,
        "needs_download": needs_download,
    }


def launch_minecraft(callback=None):
    """Lanza el juego. `callback` es el CallbackDict de minecraft_launcher_lib
    (setStatus/setProgress/setMax) y sirve para seguir la descarga de archivos."""
    callback = callback or {}

    def report(text):
        set_status = callback.get("setStatus")
        if set_status:
            try:
                set_status(text)
            except Exception:  # nunca romper el arranque por un fallo de la UI
                pass

    settings = load_settings()
    version = settings.get("version", "1.21.11")
    ram = settings.get("ram", 4)
    java_path = settings.get("java_path") or "java"
    if java_path.startswith("~"):
        java_path = os.path.expanduser(java_path)
    ram_argument = f"-Xmx{ram}G"
    game_dir = game_dir_for(settings)

    logger.info("--- Launching Stella Client ---")
    logger.info(f"Version: {version}")
    logger.info(f"RAM: {ram_argument}")
    logger.info(f"Java: {java_path}")
    logger.info(f"Dir: {game_dir}")

    os.makedirs(game_dir, exist_ok=True)

    has_mods = has_game_mods(game_dir)

    if has_mods:
        logger.info(f"Installing Fabric for {version}...")
        report(f"Descargando Fabric para {version}")
        try:
            minecraft_launcher_lib.fabric.install_fabric(version, game_dir, callback=callback)
            logger.info("Fabric installed")
        except Exception as e:
            logger.warning(f"Fabric install failed: {e}")
            has_mods = False

    if not has_mods:
        logger.info(f"Installing Minecraft {version} (vanilla)...")
        report(f"Descargando Minecraft {version}")
        minecraft_launcher_lib.install.install_minecraft_version(version, game_dir, callback=callback)

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
        offline_name = settings.get("username", "Player")
        logger.info(f"Playing offline as {offline_name}")
        options = {
            "username": offline_name,
            "uuid": offline_uuid(offline_name),
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
    report("Iniciando Minecraft")
    return subprocess.Popen(filtered)


if __name__ == "__main__":
    process = launch_minecraft()
    process.wait()
