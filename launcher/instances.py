import logging
import os
import shutil

import launcher.minecraft as minecraft
from launcher.storage import load_json, save_json

logger = logging.getLogger(__name__)

BASE_DIR = os.path.expanduser("~/.stellaclient")
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
INSTANCES_FILE = os.path.join(INSTANCES_DIR, "instances.json")


def _ensure():
    os.makedirs(INSTANCES_DIR, exist_ok=True)


def _load():
    _ensure()
    data = load_json(INSTANCES_FILE, {})
    if not isinstance(data, dict):
        return {}
    # Descartamos entradas incompletas (JSON editado a mano o a medias)
    clean = {k: v for k, v in data.items() if isinstance(v, dict) and v.get("id")}
    # Dos instancias no pueden compartir carpeta de juego (al borrar una se
    # llevaría por delante los archivos de la otra). Si alguna quedó apuntando a
    # la carpeta de otra, se devuelve a la suya y se guarda la corrección.
    if _repair_shared_dirs(clean):
        _save(clean)
    return clean


def instance_dir_for(instance_id):
    return os.path.join(INSTANCES_DIR, instance_id)


def _repair_shared_dirs(data):
    """Devuelve True si ha tenido que separar instancias que compartían carpeta."""
    by_dir = {}
    for iid, inst in data.items():
        d = inst.get("minecraft_dir")
        if d:
            by_dir.setdefault(os.path.abspath(d), []).append(iid)
    changed = False
    for dir_path, ids in by_dir.items():
        if len(ids) < 2:
            continue
        # La dueña de la carpeta es la instancia cuyo id coincide con el nombre
        # de la carpeta; si ninguna coincide, se queda la primera.
        owner = next((i for i in ids if os.path.basename(dir_path) == i), ids[0])
        for iid in ids:
            if iid == owner:
                continue
            own_dir = instance_dir_for(iid)
            data[iid]["minecraft_dir"] = own_dir
            data[iid]["mods_dir"] = os.path.join(own_dir, "mods")
            try:
                os.makedirs(data[iid]["mods_dir"], exist_ok=True)
            except OSError:
                pass
            logger.warning(
                f"La instancia '{iid}' apuntaba a {dir_path} (carpeta de '{owner}'); restaurada a {own_dir}"
            )
            changed = True
    return changed


def _save(data):
    _ensure()
    save_json(INSTANCES_FILE, data)


def list_instances():
    return list(_load().values())


def get_instance(instance_id):
    return _load().get(instance_id)


def create_instance(name, version="1.21.1", icon="📦"):
    data = _load()
    instance_id = name.lower().replace(" ", "-").replace("/", "-")
    # Make unique
    base_id = instance_id
    counter = 1
    while instance_id in data:
        instance_id = f"{base_id}-{counter}"
        counter += 1
    instance_dir = os.path.join(INSTANCES_DIR, instance_id)
    mods_dir = os.path.join(instance_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    instance = {
        "id": instance_id,
        "name": name,
        "icon": icon,
        "version": version,
        "ram": 4,
        "java_path": "java",
        "minecraft_dir": instance_dir,
        "mods_dir": mods_dir,
    }
    data[instance_id] = instance
    _save(data)
    return instance


def delete_instance(instance_id):
    data = _load()
    if instance_id not in data:
        return False

    instance_dir = data[instance_id].get("minecraft_dir")
    if instance_dir and os.path.exists(instance_dir):
        shutil.rmtree(instance_dir)
    del data[instance_id]
    _save(data)

    # El entorno de mods apunta a la instancia borrada: se limpia siempre
    env_dir = os.environ.get("STELLA_MODS_DIR")
    if env_dir and instance_dir and os.path.abspath(env_dir).startswith(os.path.abspath(instance_dir)):
        os.environ.pop("STELLA_MODS_DIR", None)

    settings = minecraft.load_settings()
    if settings.get("current_instance") == instance_id:
        remaining = next(iter(data.values()), None)
        if remaining:
            settings["current_instance"] = remaining["id"]
            minecraft.save_settings(settings)
        else:
            settings.pop("current_instance", None)
            minecraft.save_settings(settings)
            # Nunca dejamos la app sin ninguna instancia
            ensure_default_instance()

    return True


def update_instance(instance_id, updates):
    data = _load()
    if instance_id not in data:
        return None
    updates = dict(updates)
    if updates.get("minecraft_dir"):
        new_dir = minecraft.expand_path(updates["minecraft_dir"])
        taken = next(
            (i for i, inst in data.items()
             if i != instance_id
             and os.path.abspath(inst.get("minecraft_dir") or "") == os.path.abspath(new_dir)),
            None,
        )
        if taken:
            # Una instancia no puede adoptar la carpeta de otra: normalmente es
            # un valor viejo de la UI que se cuela al guardar los ajustes.
            logger.warning(
                f"Se ignora minecraft_dir '{new_dir}' para '{instance_id}': pertenece a '{taken}'"
            )
            updates.pop("minecraft_dir", None)
            updates.pop("mods_dir", None)
        else:
            updates["minecraft_dir"] = new_dir
            # La carpeta de mods siempre cuelga del directorio del juego
            updates["mods_dir"] = os.path.join(new_dir, "mods")
    data[instance_id].update(updates)
    _save(data)
    return data[instance_id]


def ensure_default_instance():
    data = _load()
    settings = minecraft.load_settings()
    current_id = settings.get("current_instance")
    if current_id and current_id in data:
        return data[current_id]
    # Check if there's already a default
    for inst in data.values():
        if inst.get("name") == "Default":
            settings["current_instance"] = inst["id"]
            minecraft.save_settings(settings)
            return inst
    # Create it
    default_mods = os.path.join(os.path.expanduser("~/.stellaclient"), "mods")
    instance_dir = os.path.join(INSTANCES_DIR, "default")
    mods_dir = os.path.join(instance_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    # Move existing mods and registry if any
    if os.path.exists(default_mods):
        for f in os.listdir(default_mods):
            if f.endswith(".jar"):
                try:
                    shutil.move(os.path.join(default_mods, f), os.path.join(mods_dir, f))
                except Exception:
                    pass
    # El registro de mods antiguo (global) ya no se mueve: mods.py lo lee como
    # respaldo la primera vez que una instancia no tiene el suyo propio.
    instance = {
        "id": "default",
        "name": "Default",
        "icon": "📦",
        "version": settings.get("version", "1.21.1"),
        "ram": settings.get("ram", 4),
        "java_path": settings.get("java_path", "java"),
        "minecraft_dir": instance_dir,
        "mods_dir": mods_dir,
    }
    data["default"] = instance
    _save(data)
    settings["current_instance"] = "default"
    minecraft.save_settings(settings)
    return instance
