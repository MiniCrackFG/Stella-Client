"""Rutas de datos de Stella Client, definidas en un solo sitio.

`~/.stellaclient` estaba escrito a mano en seis ficheros, y esa duplicación ya
se cobró un fallo: al añadirse las instancias, una de las copias siguió
apuntando a la carpeta antigua. Aquí está la definición y el resto la importa.

La ruta cambia según el sistema porque cada uno tiene su convención. En Windows
los datos de la aplicación van en `%LOCALAPPDATA%`, que además queda fuera del
perfil itinerante —no es sitio para varios GB de juego—; en Linux y macOS sigue
siendo `~/.stellaclient`, así que ahí no cambia absolutamente nada.
"""

import logging
import os
import shutil
import sys

from launcher.storage import load_json, save_json

logger = logging.getLogger(__name__)

APP_DIR_NAME = "StellaClient"
LEGACY_DIR_NAME = ".stellaclient"


def is_windows():
    """True sólo en Windows."""
    return sys.platform == "win32"


def legacy_data_dir():
    """La ruta que usaban las versiones anteriores al porte a Windows."""
    return os.path.expanduser("~/" + LEGACY_DIR_NAME)


def data_dir():
    """Directorio raíz de datos: ajustes, cuentas, instancias y el juego."""
    if is_windows():
        # %LOCALAPPDATA% y no %APPDATA%: este último es el del perfil
        # itinerante, que se sincroniza entre máquinas, y aquí van varios GB.
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_DIR_NAME)
    return legacy_data_dir()


def config_file():
    return os.path.join(data_dir(), "config.json")


def auth_file():
    return os.path.join(data_dir(), "auth.json")


def mods_dir():
    return os.path.join(data_dir(), "mods")


def instances_dir():
    return os.path.join(data_dir(), "instances")


def instances_file():
    return os.path.join(instances_dir(), "instances.json")


def logs_dir():
    return os.path.join(data_dir(), "logs")


def _relocated(value, old, new):
    """Devuelve `value` con el prefijo `old` cambiado por `new`, o None.

    Compara sin distinguir mayúsculas ni separadores, porque en Windows eso da
    igual y el usuario puede haber escrito la ruta con barras normales.
    """
    if not isinstance(value, str) or not value:
        return None
    normalized = os.path.normcase(os.path.normpath(value))
    normalized_old = os.path.normcase(os.path.normpath(old))
    if normalized == normalized_old:
        return new
    if normalized.startswith(normalized_old + os.sep):
        return os.path.join(new, value[len(old):].lstrip("/\\"))
    return None


def _rewrite_tree(node, old, new):
    """Recorre el JSON y reapunta al sitio nuevo cualquier ruta que lo citara."""
    if isinstance(node, dict):
        return {key: _rewrite_tree(value, old, new) for key, value in node.items()}
    if isinstance(node, list):
        return [_rewrite_tree(value, old, new) for value in node]
    moved = _relocated(node, old, new)
    return moved if moved is not None else node


def _rewrite_stored_paths(old, new):
    """Ajusta las rutas absolutas guardadas, que si no quedarían huérfanas.

    `instances.json` guarda `minecraft_dir` y `mods_dir` de cada instancia, y
    `config.json` la carpeta del juego: mover la carpeta sin tocar el JSON
    dejaría al launcher buscando el juego en el sitio antiguo.
    """
    for path in (config_file(), instances_file()):
        data = load_json(path, None)
        if data is None:
            continue
        rewritten = _rewrite_tree(data, old, new)
        if rewritten != data:
            save_json(path, rewritten)
            logger.info(f"Rutas reapuntadas a {new} en {path}")


def migrate_once():
    """Traslada los datos de la ruta antigua a la nueva. Devuelve lo movido.

    En Linux y macOS no hace nada, porque las dos rutas son la misma. En Windows
    es una red de seguridad: la build de Windows es la primera que existe, pero
    quien haya ejecutado el launcher desde el código fuente tiene sus ajustes y
    sus instancias en `~/.stellaclient`, y esa carpeta se quedaría atrás.
    """
    old = legacy_data_dir()
    new = data_dir()
    if os.path.normcase(os.path.abspath(old)) == os.path.normcase(os.path.abspath(new)):
        return []
    if not os.path.isdir(old):
        return []

    os.makedirs(new, exist_ok=True)
    moved = []
    for entry in sorted(os.listdir(old)):
        source = os.path.join(old, entry)
        destination = os.path.join(new, entry)
        if os.path.exists(destination):
            continue  # nunca se pisan datos de la instalación nueva
        try:
            shutil.move(source, destination)
            moved.append(entry)
        except OSError as e:
            logger.warning(f"No se pudo mover {source} a {destination}: {e}")

    if moved:
        logger.info(f"Datos trasladados de {old} a {new}: {', '.join(moved)}")
        _rewrite_stored_paths(old, new)
    return moved
