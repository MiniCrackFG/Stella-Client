import subprocess
import minecraft_launcher_lib
import os
import json

# --- Configuración de archivos ---
# Se guarda en una carpeta oculta en tu home de Linux (~/.stellaclient)
CONFIG_FILE = os.path.expanduser("~/.stellaclient/config.json")
MINECRAFT_DIR = os.path.expanduser("~/.stellaclient")

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

def get_available_versions():
    """Returns a list of available Minecraft versions."""
    return ["1.21.11", "1.21.1", "1.21", "1.20.4", "1.20.1", "1.20", "1.19.2"]

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
    # Formatear la RAM para Java (ej: 4 -> -Xmx4G)
    ram_argument = f"-Xmx{settings['ram']}G"
    
    print(f"--- Iniciando Stella Client ---")
    print(f"Versión: {version}")
    print(f"Asignando: {ram_argument}")

    # 2. Asegurar que el directorio existe
    if not os.path.exists(MINECRAFT_DIR):
        os.makedirs(MINECRAFT_DIR, exist_ok=True)

    # 3. Instalar la versión (si no existe)
    print(f"Verificando instalación de {version}...")
    minecraft_launcher_lib.install.install_minecraft_version(
        version,
        MINECRAFT_DIR
    )

    # 4. Configurar opciones de lanzamiento
    # Aquí unimos la RAM personalizada con los datos de usuario
    options = {
        "username": settings["username"],
        "uuid": "00000000000000000000000000000000",
        "token": "offline",
        "executablePath": "java",
        "jvmArguments": [ram_argument, "-XX:+UseG1GC"] # Inyectamos la RAM aquí
    }

    # 5. Generar el comando de ejecución
    command = minecraft_launcher_lib.command.get_minecraft_command(
        version,
        MINECRAFT_DIR,
        options
    )

    # 6. Ejecutar el juego
    print("Lanzando proceso...")
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Error al lanzar el juego: {e}")

if __name__ == "__main__":
    launch_minecraft()