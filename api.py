import base64
import json
import os
import subprocess
import sys
import threading
import time

import launcher.instances as instances
import launcher.minecraft as minecraft
import launcher.mods as mods
import launcher.discord_rpc as discord_rpc

_gi_available = False


def _open_url(url):
    try:
        subprocess.Popen(['xdg-open', url])
    except Exception:
        import webbrowser
        webbrowser.open(url)


def _ensure_glib():
    try:
        global _gi_available
        if not _gi_available:
            import gi
            gi.require_version("Gtk", "3.0")
            _gi_available = True
        from gi.repository import GLib
        return GLib
    except ImportError:
        return None

_cache = {}
_CACHE_TTL = 60


def _cached(key, ttl, func, *args, **kwargs):
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry["time"] < ttl:
        return entry["data"]
    data = func(*args, **kwargs)
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
        current = minecraft.load_settings()
        current.update(updates)
        minecraft.save_settings(current)
        inst = self.get_current_instance()
        if inst:
            for key in ("version", "ram", "java_path"):
                if key in updates:
                    instances.update_instance(inst["id"], {key: updates[key]})
        return {"ok": True}

    def get_auth(self):
        return minecraft.load_auth()

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

    def poll_microsoft_login(self, device_code, interval=5):
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
        try:
            import minecraft_launcher_lib.microsoft_account as ma
            xbl = ma.authenticate_with_xbl(tokens["access_token"])
            uhs = xbl.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", "")
            xsts = ma.authenticate_with_xsts(xbl["Token"])
            mc = ma.authenticate_with_minecraft(uhs, xsts["Token"])
            profile = ma.get_profile(mc["access_token"])
            minecraft.save_auth({
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token", ""),
                "xbl_token": xbl["Token"],
                "xsts_token": xsts["Token"],
                "mc_access_token": mc["access_token"],
                "uuid": profile["id"],
                "username": profile["name"],
            })
            return {"status": "success", "username": profile["name"]}
        except Exception as e:
            return {"error": str(e)}

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

    def _get_java_version(self, path):
        try:
            ver = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
            version_str = ver.stderr.strip()
            if '"' in version_str:
                return version_str.split('"')[1]
            return version_str[:50]
        except Exception:
            return None

    def detect_java(self):
        javas = []
        seen = set()

        for cmd in ("java", "java21", "java17"):
            try:
                r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    path = r.stdout.strip()
                    if path and path not in seen:
                        seen.add(path)
                        version_str = self._get_java_version(path)
                        if version_str:
                            javas.append({"path": path, "version": version_str})
            except Exception:
                pass

        import glob
        for jdir in sorted(glob.glob("/usr/lib/jvm/*"), reverse=True):
            for jbin in ("bin/java", "jre/bin/java"):
                path = os.path.join(jdir, jbin)
                if os.path.exists(path) and path not in seen:
                    seen.add(path)
                    version_str = self._get_java_version(path)
                    if version_str:
                        javas.append({"path": path, "version": version_str})

        return javas

    def get_avatar(self, uuid=None):
        import requests
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

    def _detect_java(self):
        try:
            import psutil
        except ImportError:
            time.sleep(5)
            self._launch_status["state"] = "playing"
            return
        time.sleep(3)
        for _ in range(120):
            for proc in psutil.process_iter(['name']):
                try:
                    if 'java' in proc.info['name'].lower():
                        self._launch_status["state"] = "playing"
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(1)

    def launch(self):
        self._launch_status["state"] = "launching"
        threading.Thread(target=self._detect_java, daemon=True).start()
        def run():
            s = minecraft.load_settings()
            instance = self.get_current_instance()
            if instance:
                s["version"] = instance.get("version", s["version"])
                s["ram"] = instance.get("ram", s.get("ram", 4))
                s["java_path"] = instance.get("java_path", s.get("java_path", "java"))
                s["minecraft_dir"] = instance.get("minecraft_dir", s.get("minecraft_dir", os.path.expanduser("~/.stellaclient")))
                minecraft.save_settings(s)
                inst_mods = instance.get("mods_dir")
                if inst_mods:
                    os.environ["STELLA_MODS_DIR"] = inst_mods
            mods.install_stella_mod()
            if s.get("discord_rpc", True):
                discord_rpc.update_playing()
            minecraft.launch_minecraft()
            if s.get("discord_rpc", True):
                discord_rpc.update_menu()
            self._launch_status["state"] = "stopped"
        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def install_stella_mod(self):
        result = mods.install_stella_mod()
        if result:
            self._clear_browse_cache()
            return {"ok": True, "path": result}
        return {"ok": False, "error": "Failed to build/install Stella mod"}

    def get_launch_status(self):
        return self._launch_status

    def get_trending_mods(self, project_type="mod", offset=0):
        try:
            version = minecraft.load_settings().get("version", "1.21.1")
            key = f"trending_{project_type}_{version}_{offset}"
            def _fetch():
                data = mods.get_trending_mods(version=version, limit=15, project_type=project_type, offset=offset)
                return {"mods": data["results"], "total_hits": data["total_hits"]}
            return _cached(key, _CACHE_TTL, _fetch)
        except Exception as e:
            return {"error": str(e), "mods": [], "total_hits": 0}

    def search_mods(self, query, version, source="modrinth", project_type="mod", offset=0):
        try:
            if source == "modrinth":
                key = f"search_{project_type}_{version}_{query}_{offset}"
                def _fetch():
                    data = mods.search_modrinth(query, version=version, project_type=project_type, offset=offset)
                    return {"mods": data["results"], "total_hits": data["total_hits"]}
                return _cached(key, _CACHE_TTL, _fetch)
            return {"mods": mods.search_forge(version), "total_hits": 0}
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
                        "license": d.get("license", ""),
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
        self._clear_browse_cache()
        if source == "modrinth":
            mods.download_mod(mod_id, mc_version, source=source, project_type=project_type, thumbnail=thumbnail, prefer_loader=prefer_loader)
        else:
            mods.download_forge(mc_version)

    def minimize(self):
        if self._window:
            self._window.minimize()
        return {"ok": True}

    def maximize(self):
        if self._window:
            self._window.maximize()
        return {"ok": True}

    def close_window(self):
        if self._window:
            self._window.destroy()
        return {"ok": True}

    def move_window(self, x, y):
        try:
            if self._window:
                self._window.move(x, y)
        except Exception:
            pass
        return {"ok": True}

    def begin_window_move(self, button, root_x, root_y, timestamp):
        if not self._window:
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
        mods.delete_mod(filename)
        self._clear_browse_cache()
        return {"ok": True}
