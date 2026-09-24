"""Lectura tolerante y escritura atómica de JSON para los datos del launcher.

Los archivos de configuración se escribían directamente sobre el original: un
corte a mitad de escritura dejaba un JSON corrupto y el launcher no arrancaba.
Con `save_json` se escribe en un temporal y se renombra al final, y con
`load_json` un archivo ilegible se trata como "sin datos" en vez de romper.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def load_json(path, default=None):
    """Devuelve el contenido del JSON o `default` si no existe o está corrupto."""
    try:
        with open(Path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        logger.warning(f"No se pudo leer {path} ({e}); se usan valores por defecto")
        return default


def save_json(path, data):
    """Escribe el JSON de forma atómica: temporal en el mismo directorio + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise
