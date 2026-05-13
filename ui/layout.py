import threading
import time
from io import BytesIO

import requests
from PIL import Image
import launcher.minecraft as minecraft
import launcher.discord_rpc as discord_rpc
import launcher.mods as mods
import customtkinter as ctk

def start_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("1000x550")
    app.minsize(800, 450)
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    def toggle_fullscreen():
        app.attributes('-fullscreen', not app.attributes('-fullscreen'))
    app.bind("<F11>", lambda e: toggle_fullscreen())

    ui_ready = {"value": False}
    preload_data_store = {"settings": None, "auth": None, "mods": None}

    # --- SPLASH SCREEN ---
    splash_frame = ctk.CTkFrame(app, fg_color="#1C1C1C")
    splash_frame.grid(row=0, column=0, sticky="nsew")
    splash_frame.grid_columnconfigure(0, weight=1)
    splash_frame.grid_rowconfigure(0, weight=1)

    splash_content = ctk.CTkFrame(splash_frame, fg_color="transparent")
    splash_content.grid(row=0, column=0, sticky="")
    splash_content.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(splash_content, text="Stella Client", font=("Comic Neue", 48, "bold"), text_color="#4A8FBF").grid(row=0, column=0, pady=(160, 20))

    progress_label = ctk.CTkLabel(splash_content, text="Cargando...", font=("Comic Neue", 14), text_color="#888888")
    progress_label.grid(row=1, column=0, pady=(20, 10))

    progress_bar = ctk.CTkProgressBar(splash_content, width=300, height=8, progress_color="#4A8FBF")
    progress_bar.set(0)
    progress_bar.grid(row=2, column=0, pady=10)

    def update_splash(text, progress):
        progress_label.configure(text=text)
        progress_bar.set(progress)
    app.update()

    BG_COLOR = "#1C1C1C"
    SIDEBAR_BG = "#262626"
    ACCENT_BLUE = "#114066"
    ACCENT_BLUE_LIGHT = "#4A8FBF"
    CARD_BG = "#2D2D2D"

    FONT_TITLE = ctk.CTkFont(family="Comic Neue", size=42, weight="bold")
    FONT_HEADING = ctk.CTkFont(family="Comic Neue", size=24, weight="bold")
    FONT_SUBHEADING = ctk.CTkFont(family="Comic Neue", size=18, weight="bold")
    FONT_BODY = ctk.CTkFont(family="Comic Neue", size=14)
    FONT_SMALL = ctk.CTkFont(family="Comic Neue", size=12)

    thumbnail_cache = {}
    cached_mods = {"trending": [], "search": [], "loaded": False}
    cached_versions = []

    def load_mod_thumbnail(url):
        if not url or url in thumbnail_cache:
            return thumbnail_cache.get(url)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                image = Image.open(BytesIO(resp.content)).convert("RGBA")
                thumbnail_cache[url] = image
                return image
        except Exception:
            return None

    def preload_thumbnails(mod_list, max_thumbnails=8):
        for m in mod_list[:max_thumbnails]:
            url = m.get("thumbnail")
            if url and url not in thumbnail_cache:
                threading.Thread(target=lambda u=url: load_mod_thumbnail(u), daemon=True).start()

    def bind_mousewheel(widget):
        def _on_mousewheel_linux(event):
            if event.num == 4:
                widget._parent_canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                widget._parent_canvas.yview_scroll(3, "units")
        def _on_mousewheel_windows(event):
            widget._parent_canvas.yview_scroll(-int(event.delta / 120) * 3, "units")
        try:
            widget.bind_all("<Button-4>", _on_mousewheel_linux)
            widget.bind_all("<Button-5>", _on_mousewheel_linux)
        except:
            pass
        try:
            widget.bind_all("<MouseWheel>", _on_mousewheel_windows)
        except:
            pass

    # --- PRE-CARGAR DATOS ---
    def preload_data():
        app.after(0, lambda: update_splash("Cargando configuración...", 0.1))
        minecraft.load_settings()
        settings = minecraft.load_settings()
        preload_data_store["settings"] = settings

        app.after(0, lambda: update_splash("Cargando perfil...", 0.2))
        auth = minecraft.load_auth()
        preload_data_store["auth"] = auth

        app.after(0, lambda: update_splash("Cargando versiones...", 0.3))
        global cached_versions
        try: cached_versions = minecraft.get_available_versions()
        except: pass

        app.after(0, lambda: update_splash("Cargando mods instalados...", 0.5))
        try:
            installed = mods.get_installed_mods()
            preload_data_store["mods"] = installed
        except: pass

        app.after(0, lambda: update_splash("Cargando mods trending...", 0.7))
        try:
            version = settings.get("version", "1.21.1")
            trending = mods.get_trending_mods(version=version, limit=15)
            cached_mods["trending"] = trending
            preload_thumbnails(trending, max_thumbnails=8)
        except: pass

        app.after(0, lambda: update_splash("Inicializando Discord RPC...", 0.9))
        try: discord_rpc.init_rpc(); discord_rpc.update_menu()
        except: pass

        app.after(0, lambda: update_splash("¡Listo!", 1.0))
        cached_mods["loaded"] = True
        ui_ready["value"] = True

    threading.Thread(target=preload_data, daemon=True).start()

    # --- SISTEMA DE PÁGINAS ---
    main_container = ctk.CTkFrame(app, fg_color=BG_COLOR)
    main_container.grid(row=0, column=0, sticky="nsew")
    main_container.grid_columnconfigure(0, weight=1)
    main_container.grid_rowconfigure(0, weight=1)
    main_container.grid_remove()

    page_container = ctk.CTkFrame(main_container, fg_color=BG_COLOR)
    page_container.grid(row=0, column=0, sticky="nsew")
    page_container.grid_rowconfigure(1, weight=1)
    page_container.grid_columnconfigure(0, weight=1)

    nav_bar = ctk.CTkFrame(page_container, fg_color=SIDEBAR_BG, corner_radius=0, height=50)
    nav_bar.grid(row=0, column=0, sticky="ew")
    nav_bar.grid_columnconfigure(0, weight=1)
    nav_bar.grid_propagate(False)

    nav_title = ctk.CTkLabel(nav_bar, text="Stella Client", font=FONT_SUBHEADING, text_color="#4A8FBF")
    nav_title.grid(row=0, column=0, sticky="w", padx=20)

    nav_back_btn = ctk.CTkButton(nav_bar, text="← Volver", font=FONT_BODY,
        fg_color="transparent", hover_color="#3D3D3D", width=100, command=lambda: None)
    nav_back_btn.grid(row=0, column=1, sticky="e", padx=10)
    nav_back_btn.grid_remove()

    content_area = ctk.CTkFrame(page_container, fg_color=BG_COLOR)
    content_area.grid(row=1, column=0, sticky="nsew")
    content_area.grid_columnconfigure(0, weight=1)
    content_area.grid_rowconfigure(0, weight=1)

    def clear_content():
        for w in content_area.winfo_children():
            w.destroy()


    account_btn_ref = {"btn": None}


    def refresh_account_btn():
        if account_btn_ref["btn"]:
            user = minecraft.get_current_user()
            account_btn_ref["btn"].configure(
                text=f"👤 {user[:15]}" if user else "👤 Account"
        )

    # --- HOME ---
    def show_home():
        clear_content()
        nav_title.configure(text="Stella Client")
        nav_back_btn.grid_remove()

        inner = ctk.CTkFrame(content_area, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew")
        inner.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", pady=(60, 40), padx=60)
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_frame, text="Stella Client", font=FONT_TITLE, text_color="#FFFFFF").grid(row=0, column=0, sticky="w")

        account_btn = ctk.CTkButton(
            title_frame, text="👤 Account", width=150, height=44,
            fg_color=CARD_BG, border_color=ACCENT_BLUE, border_width=2,
            hover_color="#3D3D3D", font=FONT_BODY,
            command=lambda: show_account())
        account_btn.grid(row=0, column=1, sticky="e")
        account_btn_ref["btn"] = account_btn
        refresh_account_btn()

        play_frame = ctk.CTkFrame(inner, fg_color="transparent")
        play_frame.grid(row=1, column=0, sticky="ew", padx=60, pady=(30, 40))
        play_frame.grid_columnconfigure(0, weight=1)

        def launch_game():
            def game_thread():
                settings = minecraft.load_settings()
                original_version = settings["version"]
                discord_rpc.update_playing()
                minecraft.launch_minecraft()
                new_settings = minecraft.load_settings()
                if new_settings["version"] != original_version:
                    def show_warning():
                        w = ctk.CTkToplevel(app)
                        w.title("Version Changed")
                        w.geometry("500x200")
                        w.after(10, w.lift)
                        w.configure(fg_color=BG_COLOR)
                        ctk.CTkLabel(w, text="⚠️ Version Auto-Changed", font=("Comic Neue", 16, "bold")).pack(pady=20)
                        ctk.CTkLabel(w, text=f"The game version was changed from {original_version} to {new_settings['version']}\nto be compatible with your mods.", font=("Comic Neue", 12), justify="center").pack(pady=10, padx=20)
                        ctk.CTkButton(w, text="OK", command=w.destroy, fg_color=ACCENT_BLUE, hover_color="#0d3553").pack(pady=20)
                    app.after(1000, show_warning)
                discord_rpc.update_menu()
            threading.Thread(target=game_thread, daemon=True).start()

        ctk.CTkButton(
            play_frame, text="▶  PLAY", font=FONT_SUBHEADING,
            height=70, width=240, fg_color=ACCENT_BLUE, hover_color="#0d3553",
            corner_radius=12, command=launch_game
        ).grid(row=0, column=0, sticky="ew", padx=(0, 20))

        def on_version_change(v):
            minecraft.set_version(v)

        av = minecraft.get_available_versions()
        cv = minecraft.load_settings()["version"]
        vd = ctk.CTkOptionMenu(
            play_frame, values=av, command=on_version_change,
            button_color="#114066", button_hover_color="#0d3553",
            text_color="#4A8FBF", fg_color=CARD_BG, font=FONT_BODY
        )
        vd.set(cv)
        vd.grid(row=0, column=1, sticky="e", padx=(10, 0))

        bottom_frame = ctk.CTkFrame(inner, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="se", padx=60, pady=(40, 50))

        bs = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bs.pack()

        ctk.CTkButton(bs, text="📦  Mods", width=140, height=44,
            fg_color=CARD_BG, border_color="#3a3a3a", border_width=1,
            hover_color="#3D3D3D", font=FONT_BODY,
            command=lambda: show_mods()).pack(pady=(0, 10))

        ctk.CTkButton(bs, text="⚙  Settings", width=140, height=44,
            fg_color=CARD_BG, border_color="#3a3a3a", border_width=1,
            hover_color="#3D3D3D", font=FONT_BODY,
            command=lambda: show_settings()).pack()

    # --- ACCOUNT PAGE ---
    def show_account():
        clear_content()
        nav_title.configure(text="👤  Account")
        nav_back_btn.configure(command=lambda: show_home())
        nav_back_btn.grid()

        main = ctk.CTkFrame(content_area, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=60, pady=30)
        main.grid_columnconfigure(0, weight=1)

        auth_data = minecraft.load_auth()
        offline_username = minecraft.get_offline_username()
        offline_exists = minecraft.has_offline_account()
        is_premium = auth_data is not None and "username" in auth_data

        if is_premium:
            ctk.CTkLabel(main, text="✓  CUENTA PREMIUM", font=FONT_HEADING, text_color="#00FF00").pack(anchor="w", pady=(10, 10))
            ctk.CTkLabel(main, text=f"Usuario: {auth_data['username']}", font=FONT_SUBHEADING, text_color="white").pack(anchor="w", pady=5)
            ctk.CTkLabel(main, text=f"UUID: {auth_data.get('uuid', 'N/A')}", font=FONT_BODY, text_color="#888888").pack(anchor="w", pady=2)
            ctk.CTkLabel(main, text="Puedes jugar con tu cuenta premium ahora.", font=FONT_BODY, text_color="#aaaaaa").pack(anchor="w", pady=(15, 30))
            ctk.CTkButton(main, text="Cerrar Sesión Premium", fg_color="#c42b1c", hover_color="#8b1e14",
                text_color="white", command=lambda: [minecraft.logout(), show_account()], height=50, font=FONT_SUBHEADING).pack(pady=10, fill="x")
            if offline_exists:
                ctk.CTkButton(main, text="Usar Cuenta Offline", fg_color="#4A8FBF", hover_color="#36749c",
                    text_color="white", command=lambda: [minecraft.logout(), show_account()], height=50, font=FONT_SUBHEADING).pack(pady=10, fill="x")
        else:
            ctk.CTkLabel(main, text="Cuenta Offline / Microsoft", font=FONT_HEADING, text_color="white").pack(anchor="w", pady=(10, 5))

            sep = ctk.CTkFrame(main, fg_color="#333333", height=1)
            sep.pack(fill="x", pady=(10, 20))

            if offline_exists:
                ctk.CTkLabel(main, text=f"✓ Modo offline activo como:", font=FONT_BODY, text_color="#aaaaaa").pack(anchor="w")
                ctk.CTkLabel(main, text=offline_username, font=FONT_SUBHEADING, text_color="#00FF00").pack(anchor="w", pady=(0, 15))
            else:
                ctk.CTkLabel(main, text="No hay perfil offline configurado.", font=FONT_BODY, text_color="#666666").pack(anchor="w", pady=(0, 15))

            ctk.CTkLabel(main, text="Nombre de usuario", font=FONT_SUBHEADING).pack(anchor="w")
            offline_entry = ctk.CTkEntry(main, placeholder_text="Ingresa un nickname", font=FONT_BODY, height=45)
            offline_entry.pack(fill="x", pady=(5, 15))

            sl = ctk.CTkLabel(main, text="", font=FONT_BODY, text_color="white")
            sl.pack(pady=2)

            def apply_offline():
                name = offline_entry.get().strip()
                if not name:
                    sl.configure(text="Ingresa un nombre válido.", text_color="red")
                    return
                minecraft.login_offline(name)
                sl.configure(text=f"Modo offline activado como {name}", text_color="#00FF00")

            def clear_offline():
                minecraft.clear_offline_account()
                sl.configure(text="Perfil offline eliminado.", text_color="#00FF00")

            br = ctk.CTkFrame(main, fg_color="transparent")
            br.pack(fill="x", pady=(0, 20))
            br.grid_columnconfigure(0, weight=1)
            br.grid_columnconfigure(1, weight=1)
            ctk.CTkButton(br, text="✓ Guardar Offline", fg_color="#4A8FBF", hover_color="#36749c", command=apply_offline, height=50, font=FONT_BODY).grid(row=0, column=0, sticky="ew", padx=(0, 5))
            ctk.CTkButton(br, text="✕ Eliminar Offline", fg_color="#8b1e14", hover_color="#6a1510", command=clear_offline, height=50, font=FONT_BODY).grid(row=0, column=1, sticky="ew", padx=(5, 0))

            sep2 = ctk.CTkFrame(main, fg_color="#333333", height=1)
            sep2.pack(fill="x", pady=(10, 20))

            ctk.CTkLabel(main, text="O inicia sesión con Microsoft:", font=FONT_SUBHEADING).pack(anchor="w", pady=(0, 10))

            cd = ctk.CTkLabel(main, text="---", font=("Comic Neue", 36, "bold"), text_color="#00FF00")
            cd.pack(pady=10)

            def start_login():
                try:
                    sl.configure(text="Obteniendo código...")
                    di = minecraft.get_device_code_info()
                    cd.configure(text=di.get("user_code", "Error"))
                    sl.configure(text="Ingresa este código en el navegador y espera...")
                    import webbrowser
                    webbrowser.open(di.get("verification_uri", ""))
                    threading.Thread(target=lambda: do_login_poll(di, sl, cd), daemon=True).start()
                except Exception as e:
                    sl.configure(text=f"Error: {str(e)}", text_color="red")

            ctk.CTkButton(main, text="► Iniciar Sesión con Microsoft", fg_color="#00FF00", hover_color="#00cc00",
                text_color="black", command=start_login, height=55, font=("Comic Neue", 17, "bold")).pack(pady=(10, 5), fill="x")

    def do_login_poll(device_info, status_label, code_display):
        import minecraft_launcher_lib.microsoft_account as ma
        dc = device_info.get("device_code", "")
        interval = device_info.get("interval", 5)
        maxt = 120
        attempt = 0
        status_label.configure(text="Esperando autorización... (puede tomar 1-2 minutos)")
        while attempt < maxt:
            time.sleep(interval)
            attempt += 1
            td = {"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "client_id": "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb", "device_code": dc}
            resp = requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data=td)
            if resp.status_code == 200:
                status_label.configure(text="¡Token recibido!", text_color="white")
                tokens = resp.json()
                break
            elif resp.status_code != 400:
                status_label.configure(text=f"Error: {resp.status_code}", text_color="red")
                return
            err = resp.json().get("error", "")
            if err == "authorization_pending":
                if attempt % 6 == 0:
                    status_label.configure(text=f"Esperando... ({attempt * interval}s)", text_color="yellow")
            elif err in ["authorization_declined", "expired_token"]:
                status_label.configure(text=f"Error: {err}", text_color="red")
                return
            elif err == "slow_down":
                interval += 1
        if attempt >= maxt:
            status_label.configure(text="Tiempo de espera agotado", text_color="red")
            return
        try:
            xbl = ma.authenticate_with_xbl(tokens["access_token"])
            uhs = xbl.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", "")
            xsts = ma.authenticate_with_xsts(xbl["Token"])
            mc = ma.authenticate_with_minecraft(uhs, xsts["Token"])
            profile = ma.get_profile(mc["access_token"])
            minecraft.save_auth({"access_token": tokens["access_token"], "refresh_token": tokens.get("refresh_token", ""), "xbl_token": xbl["Token"], "xsts_token": xsts["Token"], "mc_access_token": mc["access_token"], "uuid": profile["id"], "username": profile["name"]})
            status_label.configure(text=f"✓ Logueado como {profile['name']}", text_color="#00FF00")
        except Exception as e:
            status_label.configure(text=f"Error: {str(e)}", text_color="red")

    # --- BROWSE MODS PAGE ---
    def show_browse_mods():
        clear_content()
        nav_title.configure(text="🔍  Browse Mods")
        nav_back_btn.configure(command=lambda: show_mods())
        nav_back_btn.grid()

        cf = ctk.CTkFrame(content_area, fg_color="transparent")
        cf.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(cf, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls, text="Search:", font=FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 5))
        sv = ctk.StringVar()
        ctk.CTkEntry(controls, textvariable=sv, placeholder_text="Search mods...", width=280).grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(controls, text="Version:", font=FONT_BODY).grid(row=0, column=2, sticky="w", padx=(0, 5))
        av = minecraft.get_available_versions()
        cv = minecraft.load_settings()["version"]
        vd = ctk.CTkOptionMenu(controls, values=av, button_color="#114066", button_hover_color="#0d3553", text_color="#4A8FBF", dropdown_text_color="white", width=110)
        vd.set(cv)
        vd.grid(row=0, column=3, sticky="w", padx=(0, 10))

        ctk.CTkLabel(controls, text="Source:", font=FONT_BODY).grid(row=0, column=4, sticky="w", padx=(0, 5))
        sd = ctk.CTkOptionMenu(controls, values=["modrinth", "forge"], button_color="#114066", button_hover_color="#0d3553", text_color="#4A8FBF", dropdown_text_color="white", width=110)
        sd.set("modrinth")
        sd.grid(row=0, column=5, sticky="w", padx=(0, 10))

        sf = ctk.CTkScrollableFrame(cf, fg_color="transparent")
        sf.grid(row=1, column=0, sticky="nsew")
        bind_mousewheel(sf)

        def display(mod_list):
            for w in sf.winfo_children(): w.destroy()
            if not mod_list:
                ctk.CTkLabel(sf, text="No mods found.", text_color="gray", font=FONT_BODY).pack(pady=20)
                return
            preload_thumbnails(mod_list, max_thumbnails=6)
            for m in mod_list:
                card = ctk.CTkFrame(sf, fg_color=SIDEBAR_BG, corner_radius=8)
                card.pack(fill="x", pady=5)

                tf = ctk.CTkFrame(card, width=90, height=90, fg_color="#1f1f1f", corner_radius=10)
                tf.pack(side="left", padx=(15, 10), pady=10)
                tf.pack_propagate(False)
                tl = ctk.CTkLabel(tf, text="📦", font=("Comic Neue", 28), text_color="#4A8FBF")
                tl.pack(expand=True)
                turl = m.get("thumbnail")
                if turl:
                    threading.Thread(target=lambda u=turl, l=tl: l.configure(image=ctk.CTkImage(light_image=load_mod_thumbnail(u), size=(64, 64)), text="") if load_mod_thumbnail(u) else None, daemon=True).start()

                iff = ctk.CTkFrame(card, fg_color="transparent")
                iff.pack(fill="x", expand=True, padx=(0, 15), pady=10, side="left")
                ctk.CTkLabel(iff, text=m.get("name", "Unknown"), font=("Comic Neue", 14, "bold")).pack(anchor="w")
                ctk.CTkLabel(iff, text=(m.get("description", "")[:100] + "..."), text_color="gray", font=FONT_SMALL).pack(anchor="w", pady=(2, 0))
                ctk.CTkLabel(iff, text=f"Version: {m.get('version', 'N/A')} | Downloads: {m.get('downloads', 0)}", text_color="#888888", font=FONT_SMALL).pack(anchor="w", pady=(2, 0))

                def dl(m=m):
                    src = "modrinth" if sd.get() == "modrinth" else "forge"
                    threading.Thread(target=lambda: mods.download_mod(m.get("mod_id"), vd.get(), source=src) if src == "modrinth" else mods.download_forge(vd.get()), daemon=True).start()
                ctk.CTkButton(card, text="Download", fg_color=ACCENT_BLUE, hover_color="#0d3553", width=100, command=dl).pack(side="right", padx=15, pady=10)

        def search():
            q = sv.get() or "fabric"
            for w in sf.winfo_children(): w.destroy()
            ctk.CTkLabel(sf, text="🔍 Buscando mods...", text_color="#4A8FBF", font=FONT_BODY).pack(pady=30)
            def t():
                try:
                    ml = mods.search_modrinth(q, version=vd.get()) if sd.get() == "modrinth" else mods.search_forge(vd.get())
                    app.after(0, lambda: display(ml))
                except:
                    app.after(0, lambda: display([]))
            threading.Thread(target=t, daemon=True).start()

        ctk.CTkButton(controls, text="Search", fg_color=ACCENT_BLUE, hover_color="#0d3553", width=80, command=search).grid(row=0, column=6, sticky="e", padx=(10, 0))

        if cached_mods["loaded"] and cached_mods["trending"]:
            display(cached_mods["trending"])
        else:
            search()

    # --- MODS PAGE ---
    def show_mods():
        clear_content()
        nav_title.configure(text="📦  Mods Manager")
        nav_back_btn.configure(command=lambda: show_home())
        nav_back_btn.grid()

        cf = ctk.CTkFrame(content_area, fg_color="transparent")
        cf.grid(row=0, column=0, sticky="nsew", padx=40, pady=25)
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(cf, text="Installed Mods", font=FONT_HEADING).pack(anchor="w")
        ctk.CTkLabel(cf, text="Manage your Minecraft mods here.", text_color="gray", font=FONT_BODY).pack(anchor="w", pady=(0, 20))

        mlf = ctk.CTkScrollableFrame(cf, fg_color=SIDEBAR_BG, corner_radius=10)
        mlf.pack(fill="both", expand=True, pady=10)
        bind_mousewheel(mlf)

        def refresh():
            for w in mlf.winfo_children(): w.destroy()
            mods_list = mods.get_installed_mods()
            if not mods_list:
                ctk.CTkLabel(mlf, text="No mods installed yet.\nClick 'Browse Mods' to get started!", text_color="gray", font=FONT_BODY, justify="center").pack(fill="both", expand=True, pady=20)
            else:
                for m in mods_list:
                    card = ctk.CTkFrame(mlf, fg_color=BG_COLOR, corner_radius=8)
                    card.pack(fill="x", pady=5, padx=5)
                    iff = ctk.CTkFrame(card, fg_color="transparent")
                    iff.pack(fill="x", expand=True, padx=10, pady=10, side="left")
                    ctk.CTkLabel(iff, text=m.get("name", "Unknown"), font=("Comic Neue", 12, "bold")).pack(anchor="w")
                    ctk.CTkLabel(iff, text=f"Size: {m.get('size', 0) / (1024*1024):.2f} MB", text_color="gray", font=FONT_SMALL).pack(anchor="w", pady=(2, 0))
                    ctk.CTkButton(card, text="Delete", fg_color="#D32F2F", hover_color="#B71C1C", width=80, command=lambda fn=m.get("filename"): [mods.delete_mod(fn), refresh()]).pack(side="right", padx=10, pady=10)

        bf = ctk.CTkFrame(cf, fg_color="transparent")
        bf.pack(fill="x", pady=(20, 0))
        ctk.CTkButton(bf, text="Browse Mods", fg_color=ACCENT_BLUE, hover_color="#0d3553", command=show_browse_mods).pack(side="left", padx=(0, 10))
        ctk.CTkButton(bf, text="Refresh", fg_color="transparent", border_width=1, border_color=ACCENT_BLUE, text_color=ACCENT_BLUE, command=refresh).pack(side="left")
        refresh()

    # --- SETTINGS PAGE ---
    def show_settings():
        clear_content()
        nav_title.configure(text="⚙  Settings")
        nav_back_btn.configure(command=lambda: show_home())
        nav_back_btn.grid()

        body = ctk.CTkFrame(content_area, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=30, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(body, fg_color=BG_COLOR, segmented_button_fg_color=SIDEBAR_BG,
                              segmented_button_selected_color=ACCENT_BLUE, segmented_button_selected_hover_color="#0d3553",
                              text_color="white")
        tabs.grid(row=0, column=0, sticky="nsew")

        tab_appearance = tabs.add("🎨 Appearance")
        tab_java = tabs.add("☕ Java & Memory")
        tab_language = tabs.add("🌐 Language")
        tab_privacy = tabs.add("🛡️ Privacy")

        ctk.CTkLabel(tab_appearance, text="Customize the look of Stella Client", text_color="gray", font=FONT_BODY).pack(anchor="w", pady=(0, 25))
        ctk.CTkLabel(tab_appearance, text="Color theme", font=FONT_SUBHEADING).pack(anchor="w", pady=(0, 15))
        tr = ctk.CTkFrame(tab_appearance, fg_color="transparent")
        tr.pack(anchor="w")
        for name in ["Dark", "Light", "OLED"]:
            box = ctk.CTkFrame(tr, width=150, height=100, corner_radius=10, border_width=1, border_color="#444444")
            box.pack(side="left", padx=(0, 12))
            box.pack_propagate(0)
            ctk.CTkFrame(box, fg_color="#111111" if name != "Light" else "#DDDDDD", height=40, corner_radius=5).pack(fill="x", padx=10, pady=(15, 5))
            ctk.CTkLabel(box, text=name, font=FONT_BODY).pack(side="bottom", pady=5)
        ctk.CTkLabel(tab_appearance, text="Rendering", font=FONT_SUBHEADING).pack(anchor="w", pady=(30, 15))
        rf = ctk.CTkFrame(tab_appearance, fg_color="transparent")
        rf.pack(fill="x")
        ctk.CTkLabel(rf, text="Advanced rendering effects", text_color="gray", font=FONT_BODY).pack(side="left")
        ctk.CTkSwitch(rf, text="", progress_color=ACCENT_BLUE).pack(side="right")

        s = minecraft.load_settings()
        ctk.CTkLabel(tab_java, text="Configure how much RAM to allocate.", text_color="gray", font=FONT_BODY).pack(anchor="w", pady=(0, 25))
        rl = ctk.CTkLabel(tab_java, text=f"Allocated Memory: {s['ram']} GB", font=("Comic Neue", 28, "bold"), text_color="#4A8FBF")
        rl.pack(anchor="w", pady=(15, 10))
        def update_ram(v):
            val = int(v)
            rl.configure(text=f"Allocated Memory: {val} GB")
            c = minecraft.load_settings()
            c["ram"] = val
            minecraft.save_settings(c)
        rs = ctk.CTkSlider(tab_java, from_=2, to=16, number_of_steps=14,
            button_color=ACCENT_BLUE, progress_color=ACCENT_BLUE, command=update_ram, height=20)
        rs.set(s['ram'])
        rs.pack(fill="x", pady=(10, 15))
        ctk.CTkLabel(tab_java, text="Too much RAM can slow down your system.", font=FONT_SMALL, text_color="gray").pack(anchor="w")

        ctk.CTkLabel(tab_language, text="Select your preferred language.", text_color="gray", font=FONT_BODY).pack(anchor="w", pady=(0, 25))
        ctk.CTkLabel(tab_language, text="Language", font=FONT_SUBHEADING).pack(anchor="w", pady=(10, 15))
        ctk.CTkOptionMenu(tab_language,
            values=["English", "Spanish", "French", "German", "Italian", "Portuguese", "Japanese", "Korean", "Chinese"],
            button_color="#114066", button_hover_color="#0d3553", font=FONT_BODY, width=250).pack(anchor="w")

        ctk.CTkLabel(tab_privacy, text="Configure your privacy settings.", text_color="gray", font=FONT_BODY).pack(anchor="w", pady=(0, 25))
        pf = ctk.CTkFrame(tab_privacy, fg_color=SIDEBAR_BG, corner_radius=10)
        pf.pack(fill="x", pady=(10, 0))
        for i, t in enumerate(["Send crash reports", "Send usage statistics", "Show online status to friends"]):
            frame = ctk.CTkFrame(pf, fg_color="transparent")
            frame.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(frame, text=t, font=FONT_BODY).pack(side="left")
            ctk.CTkSwitch(frame, text="", progress_color=ACCENT_BLUE).pack(side="right")
            if i < 2:
                ctk.CTkFrame(pf, fg_color="#333333", height=1).pack(fill="x", padx=15)

    # --- TRANSICIÓN SPLASH A MAIN ---
    def show_main():
        if not ui_ready["value"]:
            app.after(100, show_main)
            return
        splash_frame.grid_remove()
        main_container.grid()
        show_home()

    app.after(100, show_main)

    def init_rpc_thread():
        time.sleep(1)
        discord_rpc.init_rpc()
        discord_rpc.update_menu()
    threading.Thread(target=init_rpc_thread, daemon=True).start()

    def on_closing():
        discord_rpc.close_rpc()
        app.destroy()
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
