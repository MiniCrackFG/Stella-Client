import json

import launcher.minecraft as minecraft
import launcher.mods as mods
import launcher.discord_rpc as discord_rpc


class API:
    def get_settings(self):
        return minecraft.load_settings()

    def save_settings(self, data):
        current = minecraft.load_settings()
        current.update(json.loads(data))
        minecraft.save_settings(current)
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
            import webbrowser
            webbrowser.open(di.get("verification_uri", ""))
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

    def launch(self):
        def run():
            s = minecraft.load_settings()
            if s.get("discord_rpc", True):
                discord_rpc.update_playing()
            minecraft.launch_minecraft()
            if s.get("discord_rpc", True):
                discord_rpc.update_menu()
        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def get_trending_mods(self, project_type="mod"):
        try:
            version = minecraft.load_settings().get("version", "1.21.1")
            return {"mods": mods.get_trending_mods(version=version, limit=15, project_type=project_type)}
        except Exception as e:
            return {"error": str(e), "mods": []}

    def search_mods(self, query, version, source="modrinth", project_type="mod"):
        try:
            if source == "modrinth":
                return {"mods": mods.search_modrinth(query, version=version, project_type=project_type)}
            return {"mods": mods.search_forge(version)}
        except Exception as e:
            return {"error": str(e), "mods": []}

    def get_mod_detail(self, mod_id):
        try:
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
        except Exception as e:
            return {"error": str(e)}

    def download_mod(self, mod_id, mc_version, source="modrinth", project_type="mod", thumbnail=""):
        if source == "modrinth":
            mods.download_mod(mod_id, mc_version, source=source, project_type=project_type, thumbnail=thumbnail)
        else:
            mods.download_forge(mc_version)

    def get_installed_mods(self, project_type=None):
        if project_type == "all" or not project_type:
            return {"mods": mods.get_installed_mods()}
        return {"mods": mods.get_installed_mods(project_type=project_type)}

    def delete_mod(self, filename):
        mods.delete_mod(filename)
        return {"ok": True}
