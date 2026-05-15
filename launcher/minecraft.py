import logging
import subprocess
import minecraft_launcher_lib
import minecraft_launcher_lib.microsoft_account as microsoft_account
import os
import json
import webbrowser
import http.server
import socketserver
import urllib.parse

# --- Configuración de archivos ---
CONFIG_FILE = os.path.expanduser("~/.stellaclient/config.json")
AUTH_FILE = os.path.expanduser("~/.stellaclient/auth.json")
MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")

# Client ID público de Prism Launcher
MICROSOFT_CLIENT_ID = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"

def load_settings():
    """Carga los ajustes desde el JSON o crea unos por defecto si no existe."""
    default_settings = {
        "ram": 4, 
        "version": "1.21.11",
        "username": "mini"
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
    """Guarda los ajustes actuales en el archivo JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_auth():
    """Carga la autenticación desde el archivo JSON."""
    if not os.path.exists(AUTH_FILE):
        return None
    try:
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_auth(data):
    """Guarda la autenticación en el archivo JSON."""
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_logged_in():
    """Verifica si hay sesión activa."""
    auth = load_auth()
    return auth is not None and "access_token" in auth

def get_login_url():
    """Genera la URL de login de Microsoft usando el flujo del launcher oficial."""
    state = microsoft_account.generate_state()
    code_verifier, code_challenge, _ = microsoft_account._generate_pkce_data()

    # Usar los parámetros del launcher oficial de Minecraft
    redirect_uri = "https://login.live.com/oauth20_desktop.srf"
    scope = "service::user.auth.xboxlive.com::MBI_SSL"

    url = f"https://login.live.com/oauth20_authorize.srf?client_id={MICROSOFT_CLIENT_ID}&response_type=code&redirect_uri={urllib.parse.quote(redirect_uri)}&scope={urllib.parse.quote(scope)}&state={state}&lc=1033&lw=1&fl=dob,easi2&xsup=1&nopa=2"

    return url, state, code_verifier

def get_device_code_info():
    """Obtiene el código de dispositivo para login."""
    import requests

    device_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
    scope = "XboxLive.signin offline_access"

    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "scope": scope
    }

    response = requests.post(device_url, data=data)
    device_data = response.json()

    return device_data

def complete_login_with_browser(callback_url, state, code_verifier):
    """Completa el login usando la URL del callback."""
    try:
        auth_code = microsoft_account.get_auth_code_from_url(callback_url, state)
        auth_data = microsoft_account.get_authorization_token(
            auth_code,
            "http://localhost:8000/callback",
            MICROSOFT_CLIENT_ID,
            code_verifier
        )

        xbl_data = microsoft_account.authenticate_with_xbl(auth_data["access_token"])
        xsts_data = microsoft_account.authenticate_with_xsts(xbl_data["Token"])
        mc_data = microsoft_account.authenticate_with_minecraft(xsts_data["Token"])
        profile = microsoft_account.get_profile(mc_data["access_token"])

        auth_info = {
            "access_token": auth_data["access_token"],
            "refresh_token": auth_data.get("refresh_token", ""),
            "xbl_token": xbl_data["Token"],
            "xsts_token": xsts_data["Token"],
            "mc_access_token": mc_data["access_token"],
            "uuid": profile["id"],
            "username": profile["name"],
        }

        save_auth(auth_info)
        return profile["name"]
    except Exception as e:
        logging.info(f"Error en login: {e}")
        return None

def logout():
    """Cierra la sesión premium conservando el perfil offline."""
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)


def logout_all():
    """Cierra la sesión premium y limpia la cuenta offline."""
    logout()
    clear_offline_account()


def set_offline_username(username):
    """Establece el nombre de usuario para el modo offline."""
    settings = load_settings()
    settings["username"] = username
    save_settings(settings)
    return username


def login_offline(username):
    """Guarda un nombre de usuario para modo offline y cierra cualquier sesión premium existente."""
    logout()
    return set_offline_username(username)

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handler para el callback de OAuth."""
    callback_data = None

    def do_GET(self):
        OAuthCallbackHandler.callback_data = self.path
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Login successful! You can close this window.</h1></body></html>")

    def log_message(self, format, *args):
        pass

def login_with_microsoft(callback=None):
    """Inicia el proceso de login con Microsoft."""
    logging.info("Iniciando sesión con Microsoft...")
    url, state, code_verifier = get_login_url()

    logging.info("Abriendo navegador...")
    browser = webbrowser.get('xdg-open')
    browser.open(url)

    logging.info("\nDespués de iniciar sesión, serás redirigido a una página.")
    logging.info("Copia la URL de esa página (desde https://login.live.com/...)")
    logging.info("y pégala aquí:")

    callback_url = input("URL completa: ").strip()

    if callback_url:
        try:
            result = complete_login_with_browser(callback_url, state, code_verifier)
            if result and callback:
                callback(result)
            return result
        except Exception as e:
            logging.info(f"Error: {e}")
    return None

def get_current_user():
    """Retorna el usuario actual (premium u offline)."""
    auth = load_auth()
    if auth and "username" in auth:
        return auth["username"]
    settings = load_settings()
    if settings.get("username") and settings.get("username") != "mini":
        return settings["username"]
    return None

def get_offline_username():
    """Retorna el username offline guardado."""
    settings = load_settings()
    return settings.get("username", "Player")

def has_offline_account():
    """Verifica si hay cuenta offline configurada."""
    settings = load_settings()
    return settings.get("username", "mini") != "mini" and not is_logged_in()

def clear_offline_account():
    """Limpia la cuenta offline."""
    settings = load_settings()
    settings["username"] = "mini"
    save_settings(settings)

def complete_login_with_browser_from_url(callback_url):
    """Completa el login usando la URL que pegó el usuario."""
    try:
        state = microsoft_account.generate_state()
        code_verifier, _, _ = microsoft_account._generate_pkce_data()

        # Usar la función complete_login de la librería
        result = microsoft_account.complete_login(
            MICROSOFT_CLIENT_ID,
            None,  # client_secret ya no es necesario
            "https://login.live.com/oauth20_desktop.srf",
            callback_url,
            code_verifier
        )

        logging.info(f"Login completo. Usuario: {result['profile']['name']}")

        auth_info = {
            "access_token": result["authorization_token"]["access_token"],
            "refresh_token": result["authorization_token"].get("refresh_token", ""),
            "xbl_token": result["xbl_token"],
            "xsts_token": result["xsts_token"],
            "mc_access_token": result["minecraft_access_token"],
            "uuid": result["profile"]["id"],
            "username": result["profile"]["name"],
        }

        save_auth(auth_info)
        return result["profile"]["name"]
    except Exception as e:
        logging.info(f"Error en login: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_available_versions():
    """Returns a list of available Minecraft versions, newest first."""
    try:
        manifest = minecraft_launcher_lib.utils.get_version_list()
        all_v = [v["id"] for v in manifest if v["type"] == "release"]
        filtered = [v for v in all_v if v.startswith(("26.", "1.8","1.9","1.10","1.11","1.12","1.13","1.14","1.15","1.16","1.17","1.18","1.19","1.20","1.21"))]
        def sort_key(v):
            parts = v.split(".")
            return [int(x) for x in parts]
        filtered.sort(key=sort_key, reverse=True)
        return filtered
    except:
        return ["26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.1", "1.21", "1.20.4", "1.20.1", "1.20", "1.19.2", "1.18.2", "1.17.1", "1.16.5", "1.15.2", "1.14.4", "1.13.2", "1.12.2", "1.11.2", "1.10.2", "1.9.4", "1.8.9"]

def set_version(version):
    """Updates the selected Minecraft version in settings."""
    settings = load_settings()
    settings["version"] = version
    save_settings(settings)
    return version

def launch_minecraft():
    # 1. Cargar configuración
    settings = load_settings()
    version = settings["version"]
    ram_argument = f"-Xmx{settings['ram']}G"

    # Usar el minecraft_dir de la instancia si está configurado
    game_dir = settings.get("minecraft_dir", MINECRAFT_DIR)

    logging.info(f"--- Iniciando Stella Client ---")
    logging.info(f"Versión configurada: {version}")
    logging.info(f"Asignando: {ram_argument}")
    logging.info(f"Directorio: {game_dir}")

    # 2. Asegurar que el directorio existe
    os.makedirs(game_dir, exist_ok=True)

    # 3. Verificar si hay mods instalados
    mods_dir = os.environ.get("STELLA_MODS_DIR", os.path.join(game_dir, "mods"))
    has_mods = os.path.exists(mods_dir) and len([f for f in os.listdir(mods_dir) if f.endswith('.jar')]) > 0

    if has_mods:
        logging.info(f"Instalando Fabric para {version}...")
        try:
            minecraft_launcher_lib.fabric.install_fabric(version, game_dir)
            logging.info("✓ Fabric instalado correctamente")
        except Exception as e:
            logging.info(f"Error instalando Fabric: {e}")
            # Fallback a vanilla si Fabric falla
            has_mods = False

    if not has_mods:
        # Instalar versión vanilla
        logging.info(f"Instalando Minecraft {version} (vanilla)...")
        minecraft_launcher_lib.install.install_minecraft_version(
            version,
            game_dir
        )

    # 4. Verificar autenticación
    auth = load_auth()
    if auth and "mc_access_token" in auth:
        logging.info(f"Jugando como: {auth['username']}")
        options = {
            "username": auth["username"],
            "uuid": auth["uuid"],
            "token": auth["mc_access_token"],
            "executablePath": "java",
            "jvmArguments": [ram_argument, "-XX:+UseG1GC"]
        }
    else:
        logging.info("Jugando en modo offline")
        options = {
            "username": settings["username"],
            "uuid": "00000000000000000000000000000000",
            "token": "offline",
            "executablePath": "java",
            "jvmArguments": [ram_argument, "-XX:+UseG1GC"]
        }

    # 5. Generar el comando de ejecución
    if has_mods:
        # Usar versión de Fabric (el nombre que crea Fabric)
        loader_version = minecraft_launcher_lib.fabric.get_latest_loader_version()
        fabric_version = f"fabric-loader-{loader_version}-{version}"
        logging.info(f"Lanzando con Fabric (con mods) - versión: {fabric_version}...")
        command = minecraft_launcher_lib.command.get_minecraft_command(
            fabric_version,
            game_dir,
            options
        )
    else:
        # Usar comando vanilla
        logging.info("Lanzando vanilla...")
        command = minecraft_launcher_lib.command.get_minecraft_command(
            version,
            game_dir,
            options
        )

    # 6. Filtrar flags JVM no soportados (Java 21 no reconoce --sun-misc-unsafe-memory-access)
    filtered = []
    skip_next = False
    for arg in command:
        if skip_next:
            skip_next = False
            continue
        if arg.startswith("--sun-misc-unsafe-memory-access"):
            continue
        filtered.append(arg)

    # 7. Ejecutar el juego
    logging.info("Lanzando proceso...")
    try:
        subprocess.run(filtered)
    except Exception as e:
        logging.info(f"Error al lanzar el juego: {e}")

if __name__ == "__main__":
    launch_minecraft()