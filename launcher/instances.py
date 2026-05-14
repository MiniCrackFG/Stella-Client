import json
import os
import shutil
from pathlib import Path

import launcher.minecraft as minecraft

BASE_DIR = os.path.expanduser("~/.stellaclient")
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
INSTANCES_FILE = os.path.join(INSTANCES_DIR, "instances.json")


def _ensure():
    os.makedirs(INSTANCES_DIR, exist_ok=True)


def _load():
    _ensure()
    if not os.path.exists(INSTANCES_FILE):
        return {}
    with open(INSTANCES_FILE) as f:
        return json.load(f)


def _save(data):
    _ensure()
    with open(INSTANCES_FILE, "w") as f:
        json.dump(data, f, indent=2)


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
    return True


def update_instance(instance_id, updates):
    data = _load()
    if instance_id not in data:
        return None
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
                except: pass
    old_reg = os.path.join(os.path.expanduser("~/.stellaclient"), "installed_mods.json")
    if os.path.exists(old_reg):
        try:
            shutil.move(old_reg, os.path.join(instance_dir, "installed_mods.json"))
        except: pass
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
