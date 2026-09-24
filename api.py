import json
import logging
import os
import subprocess
import sys
import threading
import time

import launcher.instances as instances
import launcher.minecraft as minecraft
import launcher.mods as mods
import launcher.discord_rpc as discord_rpc

logger = logging.getLogger(__name__)


def _open_url(url):
    try:
        subprocess.Popen(['xdg-open', url])
    except Exception:
        import webbrowser
        webbrowser.open(url)


def _ensure_glib():
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib
        return GLib
    except ImportError:
        for p in [
            "/usr/lib/python3.12/site-packages",
            "/usr/lib/python3.11/site-packages",
            "/usr/lib/python3.10/site-packages",
            "/usr/lib/python3/dist-packages",
        ]:
            if p not in sys.path:
                sys.path.insert(0, p)
            try:
                import gi
                gi.require_version("Gtk", "3.0")
                from gi.repository import GLib
                return GLib
            except (ImportError, ValueError):
                continue
    return None

_cache = {}
_CACHE_TTL = 60


def _cached(key, ttl, func, *args, **kwargs):
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry["time"] < ttl:
        return entry["data"]
    data = func(*args, **kwargs)
    # Un fallo no se cachea: si la red estaba caída, el usuario no debe quedarse
    # viendo "sin resultados" durante todo el TTL.
    if not (isinstance(data, dict) and data.get("error")):
        _cache[key] = {"data": data, "time": now}
    return data


class API:
    _window = None

    def get_settings(self):
        s = minecraft.load_settings()
        inst = self.get_current_instance()
        if inst:
            if inst.get("version"):
                s["version"] = inst["version"]
            if inst.get("ram"):
                s["ram"] = inst["ram"]
            if inst.get("java_path"):
                s["java_path"] = inst["java_path"]
            if inst.get("minecraft_dir"):
                s["minecraft_dir"] = inst["minecraft_dir"]
        return s

    def save_settings(self, data):
        if isinstance(data, str):
            updates = json.loads(data)
        else:
            updates = data
        # Normalizamos las rutas que llegan de la UI ('~/.stellaclient', rutas relativas...)
        if isinstance(updates.get("minecraft_dir"), str) and updates["minecraft_dir"].strip():
            updates["minecraft_dir"] = minecraft.expand_path(updates["minecraft_dir"])
        if isinstance(updates.get("java_path"), str):
            java_path = updates["java_path"].strip()
            updates["java_path"] = os.path.expanduser(java_path) if java_path.startswith("~") else java_path
        current = minecraft.load_settings()
        current.update(updates)
        minecraft.save_settings(current)
        inst = self.get_current_instance()
        if inst:
            instance_keys = ("version", "ram", "java_path", "minecraft_dir")
            updated = instances.update_instance(inst["id"], {k: updates[k] for k in instance_keys if k in updates})
            if updated and updated.get("mods_dir"):
                os.environ["STELLA_MODS_DIR"] = updated["mods_dir"]
        return {"ok": True}

    def get_auth(self):
        """Nunca exponer tokens al frontend: solo lo que la UI necesita mostrar."""
        auth = minecraft.load_auth()
        if not auth:
            return None
        return {"username": auth.get("username"), "uuid": auth.get("uuid")}

    def get_current_user(self):
        return minecraft.get_current_user()

    def get_offline_username(self):
        return minecraft.get_offline_username()

    def has_offline_account(self):
        return minecraft.has_offline_account()

    def logout(self):
        minecraft.logout()

    def login_offline(self, username):
        minecraft.login_offline(username)
        return {"ok": True}

    def start_microsoft_login(self):
        try:
            di = minecraft.get_device_code_info()
            _open_url(di.get("verification_uri", ""))
            return di
        except Exception as e:
            return {"error": str(e)}

    def poll_microsoft_login(self, device_code):
        import requests
        td = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb",
            "device_code": device_code,
        }
        try:
            resp = requests.post(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data=td, timeout=10,
            )
            if resp.status_code == 200:
                return self._finish_microsoft_auth(resp.json())
            elif resp.status_code != 400:
                return {"error": f"HTTP {resp.status_code}"}
            err = resp.json().get("error", "")
            if err == "authorization_pending":
                return {"status": "pending"}
            elif err in ("authorization_declined", "expired_token"):
                return {"error": err}
            elif err == "slow_down":
                return {"status": "pending", "slow_down": True}
            return {"error": err}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection failed"}
        except Exception as e:
            return {"error": str(e)}

    def _finish_microsoft_auth(self, tokens):
        # La lógica vive en launcher.minecraft: aquí solo se adapta la respuesta
        result = minecraft.finish_microsoft_auth(tokens)
        if result.get("error"):
            return result
        return {"status": "success", "username": result["username"]}

    def get_versions(self):
        return minecraft.get_available_versions()

    def list_instances(self):
        return instances.list_instances()

    def get_instance(self, instance_id):
        return instances.get_instance(instance_id)

    def create_instance(self, name, version="1.21.1", icon="📦"):
        return instances.create_instance(name, version, icon)

    def delete_instance(self, instance_id):
        ok = instances.delete_instance(instance_id)
        return {"ok": ok}

    def set_current_instance(self, instance_id):
        s = minecraft.load_settings()
        s["current_instance"] = instance_id
        minecraft.save_settings(s)
        inst = instances.get_instance(instance_id)
        if inst and inst.get("mods_dir"):
            os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
        _cache.clear()
        return {"ok": True}

    def get_current_instance(self):
        s = minecraft.load_settings()
        iid = s.get("current_instance")
        if iid:
            inst = instances.get_instance(iid)
            if inst and inst.get("mods_dir"):
                os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
            return inst
        return None

    def detect_java(self):
        javas = []
        seen = set()

        def add_java(path):
            if not os.path.exists(path) or path in seen:
                return
            seen.add(path)
            try:
                ver = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
                version_str = ver.stderr.strip()
                version_str = version_str.split('"')[1] if '"' in version_str else version_str[:50]
                javas.append({"path": path, "version": version_str})
            except Exception:
                pass

        for cmd in ["java", "java21", "java17"]:
            try:
                r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    add_java(r.stdout.strip())
            except Exception:
                pass

        import glob
        for jdir in sorted(glob.glob("/usr/lib/jvm/*"), reverse=True):
            add_java(os.path.join(jdir, "bin/java"))
            add_java(os.path.join(jdir, "jre/bin/java"))

        return javas

    def get_avatar(self, uuid=None):
        import requests
        import base64
        try:
            ident = uuid or "steve"
            url = f"https://mc-heads.net/avatar/{ident}/128"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
                b64 = base64.b64encode(resp.content).decode()
                return f"data:image/png;base64,{b64}"
        except Exception:
            pass
        return ""

    def open_url(self, url):
        _open_url(url)
        return {"ok": True}

    def get_server_info(self, address):
        import requests
        try:
            resp = requests.get(f"https://api.mcsrvstat.us/2/{address}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"error": "Could not fetch server info"}

    def get_versions_grouped(self):
        raw = minecraft.get_available_versions()
        groups = {}
        for v in raw:
            parts = v.split(".")
            major = f"{parts[0]}.{parts[1]}"
            groups.setdefault(major, []).append(v)
        result = []
        for major in sorted(groups.keys(), key=lambda x: [int(n) for n in x.split(".")], reverse=True):
            result.append({"major": major, "versions": groups[major]})
        return result

    _launch_status = {"state": "stopped"}
    _progress_lock = threading.Lock()

    # Los textos de progreso de minecraft_launcher_lib vienen en inglés y son
    # tecnicos: aquí se traducen a algo que se pueda enseñar en la barra.
    _PHASE_LABELS = {
        "Download Libraries": "Descargando librerías",
        "Download Assets": "Descargando recursos",
        "Install java runtime": "Instalando Java",
        "Installation complete": "Instalación completa",
        "Running fabric installer": "Instalando Fabric",
    }

    def _publish(self, **fields):
        """Actualiza el estado del lanzamiento desde cualquier hilo.

        Los callbacks de minecraft_launcher_lib llegan desde su ThreadPoolExecutor,
        así que el dict se reemplaza entero bajo lock (nunca se muta en sitio).
        """
        with self._progress_lock:
            if self._launch_status.get("state") != "launching":
                return
            status = dict(self._launch_status)
            status.update(fields)
            self._launch_status = status

    def _progress_callback(self):
        """CallbackDict compatible con lo que espera minecraft_launcher_lib."""
        # Marcas del callback: si la fase actual tiene nombre ("Descargando
        # librerías"), un status por archivo no debe pisarla.
        flags = {"named_phase": False}

        def set_status(text):
            text = str(text)
            label = self._PHASE_LABELS.get(text)
            if label is None and text.startswith("Download "):
                # download_file() pone el nombre del archivo en cada descarga: en la
                # barra interesa la fase, no un nombre que cambia decenas de veces
                # por segundo. Solo se usa si no hay una fase mejor que enseñar.
                if flags["named_phase"]:
                    return
                flags["named_phase"] = False
                return self._publish(phase="Descargando archivos")
            flags["named_phase"] = True
            # Fase nueva sin contador propio todavía (instalador de Fabric, Java,
            # compilar el mod...): la barra pasa a barrido indeterminado en lugar de
            # quedarse con el porcentaje de la fase anterior. Las fases que sí
            # cuentan mandan su setMax justo después de este setStatus.
            self._publish(phase=label or text, progress=0, max=0)

        def set_max(value):
            try:
                maximum = max(0, int(value))
            except (TypeError, ValueError):
                return
            # Cada fase reinicia la cuenta (la librería llama setMax al empezar);
            # sobre la marcha, un máximo nuevo empieza en 0 en lugar de heredar
            # el porcentaje de la fase anterior.
            self._publish(max=maximum, progress=0)

        def set_progress(value):
            try:
                progress = max(0, int(value))
            except (TypeError, ValueError):
                return
            self._publish(progress=progress)

        return {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}

    def launch(self):
        if self._launch_status.get("state") in ("launching", "playing"):
            return {"ok": False, "error": "Minecraft ya se está ejecutando"}

        try:
            plan = minecraft.launch_plan()
        except Exception as e:
            logger.warning(f"launch_plan failed: {e}")
            plan = {}
        self._launch_status = {
            "state": "launching",
            "needs_download": bool(plan.get("needs_download")),
            "phase": "Preparando el arranque",
            "progress": 0,
            "max": 0,
        }
        callback = self._progress_callback()

        def run():
            settings = {}
            try:
                settings = minecraft.load_settings()
                instance = self.get_current_instance()
                if instance:
                    settings["version"] = instance.get("version", settings.get("version", "1.21.11"))
                    settings["ram"] = instance.get("ram", settings.get("ram", 4))
                    settings["java_path"] = instance.get("java_path", settings.get("java_path", "java"))
                    settings["minecraft_dir"] = instance.get("minecraft_dir", settings.get("minecraft_dir", os.path.expanduser("~/.stellaclient")))
                    minecraft.save_settings(settings)
                    inst_mods = instance.get("mods_dir")
                    if inst_mods:
                        os.environ["STELLA_MODS_DIR"] = inst_mods
                self._publish(phase="Preparando el mod Stella")
                mods.install_stella_mod()
                process = minecraft.launch_minecraft(callback=callback)
                self._launch_status = {"state": "playing", "pid": process.pid}
                if settings.get("discord_rpc", True):
                    discord_rpc.update_playing()
                process.wait()
            except Exception as e:
                logger.exception("Launch failed")
                self._launch_status = {"state": "error", "message": str(e)}
                return
            if settings.get("discord_rpc", True):
                discord_rpc.update_menu()
            self._launch_status = {"state": "stopped"}

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def get_launch_status(self):
        return dict(self._launch_status)

    def get_trending_mods(self, project_type="mod", offset=0, sort="downloads"):
        try:
            instance = self.get_current_instance()
            version = (instance or {}).get("version") or minecraft.load_settings().get("version", "1.21.1")
            key = f"trending_{project_type}_{version}_{offset}_{sort}"
            def _fetch():
                data = mods.get_trending_mods(version=version, limit=15, project_type=project_type, offset=offset, sort=sort)
                result = {"mods": data["results"], "total_hits": data["total_hits"]}
                if data.get("error"):
                    result["error"] = data["error"]
                return result
            return _cached(key, _CACHE_TTL, _fetch)
        except Exception as e:
            return {"error": str(e), "mods": [], "total_hits": 0}

    def search_mods(self, query, version, source="modrinth", project_type="mod", offset=0, sort="downloads"):
        try:
            if source != "modrinth":
                return {"error": "Forge no está soportado todavía", "mods": [], "total_hits": 0}
            key = f"search_{project_type}_{version}_{query}_{offset}_{sort}"
            def _fetch():
                data = mods.search_modrinth(query, version=version, project_type=project_type, offset=offset, sort=sort)
                result = {"mods": data["results"], "total_hits": data["total_hits"]}
                if data.get("error"):
                    result["error"] = data["error"]
                return result
            return _cached(key, _CACHE_TTL, _fetch)
        except Exception as e:
            return {"error": str(e), "mods": [], "total_hits": 0}

    def get_mod_detail(self, mod_id):
        try:
            key = f"detail_{mod_id}"
            def _fetch():
                import requests
                resp = requests.get(f"https://api.modrinth.com/v2/project/{mod_id}", timeout=10)
                if resp.status_code == 200:
                    d = resp.json()
                    license_raw = d.get("license")
                    if isinstance(license_raw, dict):
                        license_name = license_raw.get("name") or license_raw.get("id") or ""
                    else:
                        license_name = license_raw or ""
                    return {
                        "mod_id": mod_id,
                        "slug": d.get("slug", ""),
                        "name": d.get("title", ""),
                        "description": d.get("description", ""),
                        "body": d.get("body", ""),
                        "thumbnail": d.get("icon_url", ""),
                        "downloads": d.get("downloads", 0),
                        "followers": d.get("followers", 0),
                        "categories": d.get("categories", []),
                        "additional_categories": d.get("additional_categories", []),
                        "client_side": d.get("client_side", ""),
                        "server_side": d.get("server_side", ""),
                        "license": license_name,
                        "game_versions": d.get("game_versions", []),
                        "loaders": d.get("loaders", []),
                        "published": d.get("published", ""),
                        "updated": d.get("updated", ""),
                        "discord_url": d.get("discord_url", ""),
                        "issues_url": d.get("issues_url", ""),
                        "source_url": d.get("source_url", ""),
                        "wiki_url": d.get("wiki_url", ""),
                        "gallery": [{"url": g.get("url", ""), "title": g.get("title", ""), "description": g.get("description", "")} for g in d.get("gallery", [])],
                        "donation_urls": [{"platform": du.get("platform", ""), "url": du.get("url", "")} for du in d.get("donation_urls", [])],
                    }
                return {"error": f"HTTP {resp.status_code}"}
            return _cached(key, _CACHE_TTL * 5, _fetch)
        except Exception as e:
            return {"error": str(e)}

    def _clear_browse_cache(self):
        for k in list(_cache):
            if k.startswith("trending_") or k.startswith("search_") or k.startswith("installed_"):
                del _cache[k]

    def download_mod(self, mod_id, mc_version, source="modrinth", project_type="mod", thumbnail="", prefer_loader="fabric"):
        self._ensure_mods_env()
        if source != "modrinth":
            return {"ok": False, "error": "Forge no está soportado todavía"}
        result = mods.download_mod(mod_id, mc_version, source=source, project_type=project_type, thumbnail=thumbnail, prefer_loader=prefer_loader)
        if result.get("ok"):
            self._clear_browse_cache()
        return result

    def minimize(self):
        if hasattr(self, '_window'):
            self._window.minimize()
        return {"ok": True}

    _maximized = True  # main.py crea la ventana maximizada

    def toggle_maximize(self):
        """El botón □ alterna maximizado/restaurado: pywebview no lo hace solo."""
        if not hasattr(self, '_window') or not self._window:
            return {"ok": False}
        try:
            native = getattr(self._window, 'native', None)
            if native is not None and hasattr(native, 'is_maximized'):
                self._maximized = bool(native.is_maximized())
            if self._maximized:
                self._window.restore()
            else:
                self._window.maximize()
            self._maximized = not self._maximized
            return {"ok": True, "maximized": self._maximized}
        except Exception as e:
            logger.info(f"toggle_maximize failed: {e}")
            return {"ok": False, "error": str(e)}

    def copy_to_clipboard(self, text):
        """Copia texto al portapapeles del sistema.

        WebKitGTK no siempre permite el portapapeles desde JS (necesita permisos
        que pywebview no pide), así que el camino fiable es GTK. Si la llamada
        llega desde otro hilo se encola en el principal con `idle_add`, que es el
        único donde GTK es seguro.
        """
        if not isinstance(text, str) or not text:
            return False
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("Gdk", "3.0")
            from gi.repository import Gdk, GLib, Gtk
        except Exception as e:
            logger.info(f"copy_to_clipboard sin GTK disponible: {e}")
            return False

        def _do_copy():
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            # Sin store() el contenido se pierde al cerrar la app.
            clipboard.store()

        try:
            # En el hilo principal GTK es seguro y podemos devolver el resultado
            # real. Si pywebview llama desde otro hilo, se encola en el principal.
            if GLib.MainContext.default().is_owner():
                _do_copy()
                return True

            def _idle_copy():
                try:
                    _do_copy()
                except Exception as e:
                    logger.info(f"copy_to_clipboard falló: {e}")
                return False  # no repetir

            GLib.idle_add(_idle_copy)
            return True
        except Exception as e:
            logger.info(f"copy_to_clipboard falló: {e}")
            return False

    def close_window(self):
        if hasattr(self, '_window'):
            self._window.destroy()
        return {"ok": True}

    def begin_window_move(self, button, root_x, root_y, timestamp):
        if not hasattr(self, '_window') or not self._window:
            return {"ok": False}
        glib = _ensure_glib()
        if not glib:
            return {"ok": False}
        try:
            native = self._window.native
            if native:
                glib.idle_add(lambda: native.begin_move_drag(int(button), int(root_x), int(root_y), int(timestamp)))
        except Exception:
            pass
        return {"ok": True}

    def _ensure_mods_env(self):
        os.environ.pop("STELLA_MODS_DIR", None)
        inst = self.get_current_instance()
        if inst and inst.get("mods_dir"):
            os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
            return inst["mods_dir"]
        return None

    def get_installed_mods(self, project_type=None):
        md = self._ensure_mods_env()
        key = f"installed_{project_type or 'all'}_{md or 'global'}"
        def _fetch():
            if project_type in (None, "all", ""):
                return {"mods": mods.get_installed_mods()}
            return {"mods": mods.get_installed_mods(project_type=project_type)}
        return _cached(key, _CACHE_TTL, _fetch)

    def delete_mod(self, filename):
        self._ensure_mods_env()
        ok = mods.delete_mod(filename)
        self._clear_browse_cache()
        return {"ok": ok}
