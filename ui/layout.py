import threading
import time
import requests
import webbrowser
import launcher.minecraft as minecraft
import launcher.discord_rpc as discord_rpc
import launcher.mods as mods
import customtkinter as ctk

def start_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("950x550")
    app.resizable(False, False)

    # Colores
    BG_COLOR = "#1C1C1C"
    SIDEBAR_BG = "#262626"
    ACCENT_BLUE = "#114066"
    ACCENT_BLUE_LIGHT = "#4A8FBF"
    ACCENT_LIGHT = "#4A8FBF"
    CARD_BG = "#2D2D2D"

    # Fuentes Comic Neue
    FONT_TITLE = ctk.CTkFont(family="Comic Neue", size=42, weight="bold")
    FONT_HEADING = ctk.CTkFont(family="Comic Neue", size=24, weight="bold")
    FONT_SUBHEADING = ctk.CTkFont(family="Comic Neue", size=18, weight="bold")
    FONT_BODY = ctk.CTkFont(family="Comic Neue", size=14)
    FONT_SMALL = ctk.CTkFont(family="Comic Neue", size=12)

    def do_login_poll(device_info, account_window, status_label, code_display):
        import minecraft_launcher_lib.microsoft_account as ma

        device_code = device_info.get("device_code", "")
        interval = device_info.get("interval", 5)
        max_attempts = 120
        attempt = 0

        status_label.configure(text="Esperando autorización... (puede tomar 1-2 minutos)")

        while attempt < max_attempts:
            time.sleep(interval)
            attempt += 1

            token_data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb",
                "device_code": device_code
            }

            resp = requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", data=token_data)

            if resp.status_code == 200:
                status_label.configure(text="¡Token recibido!", text_color="white")
                tokens = resp.json()
                break
            elif resp.status_code != 400:
                status_label.configure(text=f"Error: {resp.status_code}", text_color="red")
                return

            error_data = resp.json()
            error = error_data.get("error", "")
            if error == "authorization_pending":
                if attempt % 6 == 0:
                    status_label.configure(text=f"Esperando... ({attempt * interval}s)", text_color="yellow")
            elif error in ["authorization_declined", "expired_token"]:
                status_label.configure(text=f"Error: {error}", text_color="red")
                return
            elif error == "slow_down":
                interval += 1

        if attempt >= max_attempts:
            status_label.configure(text="Tiempo de espera agotado", text_color="red")
            return

        try:
            access_token = tokens["access_token"]
            xbl_data = ma.authenticate_with_xbl(access_token)
            display_claims = xbl_data.get("DisplayClaims", {})
            xui = display_claims.get("xui", [{}])[0]
            userhash = xui.get("uhs", "")

            xsts_data = ma.authenticate_with_xsts(xbl_data["Token"])
            mc_data = ma.authenticate_with_minecraft(userhash, xsts_data["Token"])
            profile = ma.get_profile(mc_data["access_token"])

            minecraft.save_auth({
                "access_token": access_token,
                "refresh_token": tokens.get("refresh_token", ""),
                "xbl_token": xbl_data["Token"],
                "xsts_token": xsts_data["Token"],
                "mc_access_token": mc_data["access_token"],
                "uuid": profile["id"],
                "username": profile["name"],
            })

            status_label.configure(text=f"✓ Logueado como {profile['name']}", text_color="#00FF00")
            account_window.after(2000, account_window.destroy)

        except Exception as e:
            status_label.configure(text=f"Error: {str(e)}", text_color="red")

    def open_account():
        account_window = ctk.CTkToplevel(app)
        account_window.title("Account")
        account_window.geometry("600x500")
        account_window.after(10, account_window.lift)
        account_window.configure(fg_color="#2b2b2b")

        header_frame = ctk.CTkFrame(account_window, fg_color="#1a1a1a", corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header_frame, text="👤  Account", font=("Comic Neue", 20, "bold"), text_color="white").pack(pady=15, padx=20, anchor="w")

        content_frame = ctk.CTkFrame(account_window, fg_color="#2b2b2b")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        current_user = minecraft.get_current_user()
        offline_user = minecraft.get_offline_username()

        if current_user:
            ctk.CTkLabel(content_frame, text="✓ CUENTA PREMIUM", font=("Comic Neue", 14, "bold"), text_color="#00FF00").pack(anchor="w", pady=(10, 5))
            auth_data = minecraft.load_auth()
            ctk.CTkLabel(content_frame, text=f"Usuario: {current_user}", font=("Comic Neue", 16, "bold"), text_color="white").pack(anchor="w", pady=5)
            uuid = auth_data.get("uuid", "N/A") if auth_data else "N/A"
            ctk.CTkLabel(content_frame, text=f"UUID: {uuid}", font=("Comic Neue", 12), text_color="#888888").pack(anchor="w", pady=2)
            ctk.CTkLabel(content_frame, text="Puedes jugar con tu cuenta premium ahora.", font=("Comic Neue", 12), text_color="#aaaaaa", wraplength=500).pack(anchor="w", pady=(15, 20))

            def logout():
                minecraft.logout()
                account_window.destroy()
                open_account()

            ctk.CTkButton(content_frame, text="Cerrar Sesión", fg_color="#c42b1c", hover_color="#8b1e14", text_color="white", command=logout, height=40).pack(pady=20, padx=20, fill="x")
        elif offline_user and offline_user != "mini":
            ctk.CTkLabel(content_frame, text="☁ MODO OFFLINE", font=("Comic Neue", 14, "bold"), text_color="#4A8FBF").pack(anchor="w", pady=(10, 5))
            ctk.CTkLabel(content_frame, text=f"Usuario: {offline_user}", font=("Comic Neue", 16, "bold"), text_color="white").pack(anchor="w", pady=5)
            ctk.CTkLabel(content_frame, text="Usando nombre de usuario offline.", font=("Comic Neue", 12), text_color="#aaaaaa", wraplength=500).pack(anchor="w", pady=(15, 20))

            def logout_offline():
                minecraft.clear_offline_account()
                account_window.destroy()
                open_account()

            ctk.CTkButton(content_frame, text="Cambiar Usuario", fg_color=ACCENT_BLUE, hover_color="#0d3553", text_color="white", command=logout_offline, height=40).pack(pady=20, padx=20, fill="x")
        else:
            ctk.CTkLabel(content_frame, text="Iniciar Sesión", font=("Comic Neue", 18, "bold"), text_color="white").pack(anchor="w", pady=(10, 5))
            ctk.CTkLabel(content_frame, text="Inicia sesión con tu cuenta de Microsoft o juega en modo offline.", font=("Comic Neue", 12), text_color="#aaaaaa", wraplength=500).pack(anchor="w", pady=(0, 15))

            offline_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            offline_frame.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(offline_frame, text="Nombre de usuario:", font=("Comic Neue", 12, "bold")).pack(side="left", padx=(0, 10))
            offline_name_var = ctk.StringVar(value="Player")
            offline_entry = ctk.CTkEntry(offline_frame, textvariable=offline_name_var, width=200)
            offline_entry.pack(side="left", padx=(0, 10))

            def do_offline_login():
                username = offline_name_var.get().strip()
                if username:
                    minecraft.login_offline(username)
                    try:
                        account_window.destroy()
                    except:
                        pass
                    open_account()
                    try:
                        app.destroy()
                    except:
                        pass

            ctk.CTkButton(offline_frame, text="Jugar Offline", fg_color=ACCENT_BLUE, hover_color="#0d3553", command=do_offline_login, width=120).pack(side="left")

            separator = ctk.CTkFrame(content_frame, fg_color="#444444", height=1)
            separator.pack(fill="x", pady=15)

            ctk.CTkLabel(content_frame, text="O inicia sesión con Microsoft:", font=("Comic Neue", 12), text_color="gray").pack(anchor="w")

            status_label = ctk.CTkLabel(content_frame, text="", font=("Comic Neue", 12), text_color="white")
            status_label.pack(pady=5)

            code_display = ctk.CTkLabel(content_frame, text="---", font=("Comic Neue", 28, "bold"), text_color="#4A8FBF")
            code_display.pack(pady=10)

            def start_login():
                try:
                    status_label.configure(text="Obteniendo código...")
                    device_info = minecraft.get_device_code_info()
                    code_display.configure(text=device_info.get("user_code", "Error"))
                    status_label.configure(text="Ingresa este código en el navegador y espera...")

                    webbrowser.open(device_info.get("verification_uri", ""))

                    threading.Thread(target=do_login_poll, args=(device_info, account_window, status_label, code_display), daemon=True).start()
                except Exception as e:
                    status_label.configure(text=f"Error: {str(e)}", text_color="red")

            ctk.CTkButton(content_frame, text="► Iniciar Sesión con Microsoft", fg_color=ACCENT_BLUE_LIGHT, hover_color="#3a7f9f", text_color="white", command=start_login, height=50, font=("Comic Neue", 16, "bold")).pack(pady=20, padx=20, fill="x")

    def open_browse_mods(parent_window=None):
        """Open the browse mods window to search for and download mods"""
        browse_window = ctk.CTkToplevel(app)
        browse_window.title("Browse Mods")
        browse_window.geometry("900x600")
        browse_window.after(10, browse_window.lift)
        browse_window.configure(fg_color=BG_COLOR)

        # Header
        header_frame = ctk.CTkFrame(browse_window, fg_color=SIDEBAR_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(header_frame, text="🔍  Browse Mods", font=("Comic Neue", 20, "bold")).pack(pady=15, padx=20, anchor="w")

        # Controls frame (search, version, source)
        controls_frame = ctk.CTkFrame(browse_window, fg_color="transparent")
        controls_frame.pack(fill="x", padx=30, pady=10)

        # Search bar
        ctk.CTkLabel(controls_frame, text="Search:", font=("Comic Neue", 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(controls_frame, textvariable=search_var, placeholder_text="Search mods...", width=300)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        # Version selector
        ctk.CTkLabel(controls_frame, text="Version:", font=("Comic Neue", 12, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 10))
        current_version = minecraft.load_settings()["version"]
        available_versions = minecraft.get_available_versions()
        version_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            values=available_versions,
            button_color="#114066",
            button_hover_color="#0d3553",
            text_color="#4A8FBF",
            dropdown_text_color="white",
            width=120
        )
        version_dropdown.set(current_version)
        version_dropdown.grid(row=0, column=3, sticky="w", padx=(0, 20))

        # Source selector
        ctk.CTkLabel(controls_frame, text="Source:", font=("Comic Neue", 12, "bold")).grid(row=0, column=4, sticky="w", padx=(0, 10))
        source_var = ctk.StringVar(value="modrinth")
        source_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            values=["modrinth", "forge"],
            command=lambda x: search_mods(),
            button_color="#114066",
            button_hover_color="#0d3553",
            text_color="#4A8FBF",
            dropdown_text_color="white",
            width=120
        )
        source_dropdown.set("modrinth")
        source_dropdown.grid(row=0, column=5, sticky="w", padx=(0, 10))

        controls_frame.grid_columnconfigure(1, weight=1)

        # Mods list frame with scrollbar
        mods_frame = ctk.CTkFrame(browse_window, fg_color="transparent")
        mods_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # Create a scrollable frame for mods
        scrollable_frame = ctk.CTkScrollableFrame(mods_frame, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True)

        def display_mods(mod_list):
            """Display mods in the scrollable frame"""
            # Clear existing mods
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            if not mod_list:
                ctk.CTkLabel(scrollable_frame, text="No mods found. Try a different search.", text_color="gray", font=("Comic Neue", 12)).pack(pady=20)
                return

            for mod in mod_list:
                mod_card = ctk.CTkFrame(scrollable_frame, fg_color=SIDEBAR_BG, corner_radius=8)
                mod_card.pack(fill="x", pady=5)

                # Mod info frame
                info_frame = ctk.CTkFrame(mod_card, fg_color="transparent")
                info_frame.pack(fill="x", expand=True, padx=15, pady=10, side="left")

                mod_name = ctk.CTkLabel(info_frame, text=mod.get("name", "Unknown"), font=("Comic Neue", 14, "bold"))
                mod_name.pack(anchor="w")

                mod_desc = ctk.CTkLabel(info_frame, text=mod.get("description", "")[:100] + "...", text_color="gray", font=("Comic Neue", 10))
                mod_desc.pack(anchor="w", pady=(2, 0))

                mod_info = f"Version: {mod.get('version', 'N/A')} | Downloads: {mod.get('downloads', 0)}"
                mod_info_label = ctk.CTkLabel(info_frame, text=mod_info, text_color="#888888", font=("Comic Neue", 9))
                mod_info_label.pack(anchor="w", pady=(2, 0))

                # Download button
                def download_handler(m=mod):
                    source = source_dropdown.get()
                    selected_version = version_dropdown.get()
                    
                    def download_thread():
                        if source == "modrinth":
                            mod_id = m.get("mod_id")
                            result = mods.download_mod(mod_id, selected_version, source="modrinth")
                            if result:
                                print(f"✓ Downloaded {m.get('name')}!")
                            else:
                                print(f"✗ Failed to download {m.get('name')}")
                        elif source == "forge":
                            result = mods.download_forge(selected_version)
                            if result:
                                print(f"✓ Downloaded Forge for {selected_version}!")
                            else:
                                print(f"✗ Failed to download Forge")
                    
                    threading.Thread(target=download_thread, daemon=True).start()



                download_btn = ctk.CTkButton(
                    mod_card,
                    text="Download",
                    fg_color=ACCENT_BLUE,
                    hover_color="#0d3553",
                    width=100,
                    command=download_handler
                )
                download_btn.pack(side="right", padx=15, pady=10)

        def search_mods():
            """Search for mods based on current filters"""
            search_query = search_var.get() or "fabric"
            selected_version = version_dropdown.get()
            selected_source = source_dropdown.get()

            # Show loading message
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(scrollable_frame, text="Searching...", text_color="gray", font=("Comic Neue", 12)).pack(pady=20)

            def search_thread():
                try:
                    if selected_source == "modrinth":
                        mod_list = mods.search_modrinth(search_query, version=selected_version)
                    else:  # forge
                        mod_list = mods.search_forge(selected_version)

                    browse_window.after(0, lambda: display_mods(mod_list))
                except Exception as e:
                    print(f"Error searching mods: {e}")
                    browse_window.after(0, lambda: display_mods([]))

            threading.Thread(target=search_thread, daemon=True).start()

        # Search button
        search_btn = ctk.CTkButton(
            controls_frame,
            text="Search",
            fg_color=ACCENT_BLUE,
            hover_color="#0d3553",
            width=80,
            command=search_mods
        )
        search_btn.grid(row=0, column=6, sticky="e", padx=(10, 0))

        # Initial search
        search_mods()

    def open_mods():
        mods_window = ctk.CTkToplevel(app)
        mods_window.title("Mods")
        mods_window.geometry("800x500")
        mods_window.after(10, mods_window.lift)
        mods_window.configure(fg_color=BG_COLOR)

        # Header
        header_frame = ctk.CTkFrame(mods_window, fg_color=SIDEBAR_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(header_frame, text="📦  Mods Manager", font=("Comic Neue", 20, "bold")).pack(pady=20, padx=20, anchor="w")

        # Content
        content_frame = ctk.CTkFrame(mods_window, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Title and description
        ctk.CTkLabel(content_frame, text="Installed Mods", font=("Comic Neue", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(content_frame, text="Manage your Minecraft mods here.", text_color="gray", font=("Comic Neue", 12)).pack(anchor="w", pady=(0, 20))

        # Mods list (scrollable)
        mods_list_frame = ctk.CTkScrollableFrame(content_frame, fg_color=SIDEBAR_BG, corner_radius=10)
        mods_list_frame.pack(fill="both", expand=True, pady=10)

        def refresh_mods_list():
            """Refresh and display installed mods"""
            # Clear existing widgets
            for widget in mods_list_frame.winfo_children():
                widget.destroy()

            installed_mods = mods.get_installed_mods()

            if not installed_mods:
                ctk.CTkLabel(
                    mods_list_frame,
                    text="No mods installed yet.\nClick 'Browse Mods' to get started!",
                    text_color="gray",
                    font=("Comic Neue", 12),
                    justify="center"
                ).pack(fill="both", expand=True, pady=20)
            else:
                for mod in installed_mods:
                    mod_card = ctk.CTkFrame(mods_list_frame, fg_color=BG_COLOR, corner_radius=8)
                    mod_card.pack(fill="x", pady=5, padx=5)

                    # Mod info
                    info_frame = ctk.CTkFrame(mod_card, fg_color="transparent")
                    info_frame.pack(fill="x", expand=True, padx=10, pady=10, side="left")

                    mod_name = ctk.CTkLabel(info_frame, text=mod.get("name", "Unknown"), font=("Comic Neue", 12, "bold"))
                    mod_name.pack(anchor="w")

                    mod_size = f"Size: {mod.get('size', 0) / (1024*1024):.2f} MB"
                    mod_size_label = ctk.CTkLabel(info_frame, text=mod_size, text_color="gray", font=("Comic Neue", 10))
                    mod_size_label.pack(anchor="w", pady=(2, 0))

                    # Delete button
                    def delete_handler(filename=mod.get("filename")):
                        mods.delete_mod(filename)
                        refresh_mods_list()

                    delete_btn = ctk.CTkButton(
                        mod_card,
                        text="Delete",
                        fg_color="#D32F2F",
                        hover_color="#B71C1C",
                        width=80,
                        command=delete_handler
                    )
                    delete_btn.pack(side="right", padx=10, pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        browse_btn = ctk.CTkButton(
            button_frame,
            text="Browse Mods",
            fg_color=ACCENT_BLUE,
            hover_color="#0d3553",
            command=open_browse_mods
        )
        browse_btn.pack(side="left", padx=(0, 10))

        refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh",
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT_BLUE,
            text_color=ACCENT_BLUE,
            command=refresh_mods_list
        )
        refresh_btn.pack(side="left")

        # Initial display
        refresh_mods_list()



    def open_settings():
        settings_window = ctk.CTkToplevel(app)
        settings_window.title("Settings")
        settings_window.geometry("850x600")
        settings_window.after(10, settings_window.lift)

        settings_window.configure(fg_color=BG_COLOR)

        # Dividimos en 2 columnas: 0 (Menú) y 1 (Contenido)
        settings_window.grid_columnconfigure(1, weight=1)
        settings_window.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (IZQUIERDA) ---
        sidebar_frame = ctk.CTkFrame(settings_window, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(10, weight=1) # Empuja lo de abajo

        # Título del sidebar
        label_title = ctk.CTkLabel(sidebar_frame, text="⚙  Settings", font=("Comic Neue", 18, "bold"))
        label_title.pack(pady=25, padx=20, anchor="w")

        # --- CONTENIDO (DERECHA) ---
        content_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        content_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=25)

        # FUNCIÓN MÁGICA: Cambia lo que se ve a la derecha
        current_page = "Appearance"

        def update_menu_buttons(selected_text):
            for text, btn in menu_buttons.items():
                if text == selected_text:
                    btn.configure(fg_color="#114066", hover_color="#0d3553")
                else:
                    btn.configure(fg_color="transparent", hover_color="#333333")

        def select_page(page_name):
            nonlocal current_page
            # Si ya está en esta página, no hacer nada
            if current_page == page_name:
                return
            
            current_page = page_name
            update_menu_buttons(page_name)

            # Limpiar todo lo que haya antes
            for widget in content_frame.winfo_children():
                widget.destroy()

            if page_name == "Appearance":
                # Título y descripción
                ctk.CTkLabel(content_frame, text="Appearance", font=("Comic Neue", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Customize the look of Stella Client.", text_color="gray").pack(anchor="w", pady=(0, 20))

                # Sección de Temas
                ctk.CTkLabel(content_frame, text="Color theme", font=("Comic Neue", 16, "bold")).pack(anchor="w", pady=10)

                themes_row = ctk.CTkFrame(content_frame, fg_color="transparent")
                themes_row.pack(fill="x")

                # Cajas de tema (Simuladas como en tu diseño de Modrinth)
                for name in ["Dark", "Light", "OLED"]:
                    box = ctk.CTkFrame(themes_row, width=160, height=100, corner_radius=10, border_width=1, border_color="#333333")
                    box.pack(side="left", padx=10)
                    box.pack_propagate(0) # Evita que la caja se encoja al contenido

                    # Mini preview del tema
                    preview = ctk.CTkFrame(box, fg_color="#111111" if name != "Light" else "#DDDDDD", height=40, corner_radius=5)
                    preview.pack(fill="x", padx=10, pady=(15, 5))

                    ctk.CTkLabel(box, text=name, font=("Comic Neue", 12)).pack(side="bottom", pady=5)

                # Switch de Renderizado Avanzado
                ctk.CTkLabel(content_frame, text="Rendering", font=("Comic Neue", 16, "bold")).pack(anchor="w", pady=(30, 10))

                render_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                render_frame.pack(fill="x")

                ctk.CTkLabel(render_frame, text="Advanced rendering effects", text_color="gray").pack(side="left")
                ctk.CTkSwitch(render_frame, text="", progress_color=ACCENT_BLUE).pack(side="right")

            elif page_name == "Java":
                # 1. Cargar los ajustes actuales desde minecraft.py
                settings = minecraft.load_settings()

                # 2. Título y descripción
                ctk.CTkLabel(content_frame, text="Java & Memory", font=("Comic Neue", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Configure how much RAM Stella Client can use.", text_color="gray").pack(anchor="w", pady=(0, 20))

                # 3. Label dinámico de RAM
                ram_label = ctk.CTkLabel(content_frame, text=f"Allocated Memory: {settings['ram']} GB", font=("Comic Neue", 16, "bold"))
                ram_label.pack(anchor="w", pady=(10, 0))

                def update_ram(value):
                    val = int(value)
                    ram_label.configure(text=f"Allocated Memory: {val} GB")
                    current_conf = minecraft.load_settings()
                    current_conf["ram"] = val
                    minecraft.save_settings(current_conf)

                # 4. Slider
                ram_slider = ctk.CTkSlider(
                    content_frame,
                    from_=2,
                    to=16,
                    number_of_steps=14,
                    button_color=ACCENT_BLUE,
                    progress_color=ACCENT_BLUE,
                    command=update_ram
                )
                ram_slider.set(settings['ram'])
                ram_slider.pack(fill="x", pady=10)

                ctk.CTkLabel(
                    content_frame,
                    text="Note: Allocating too much RAM can slow down your system.",
                    font=("Comic Neue", 12),
                    text_color="gray"
                ).pack(anchor="w")

            elif page_name == "Language":
                ctk.CTkLabel(content_frame, text="Language", font=("Comic Neue", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Select your preferred language.", text_color="gray").pack(anchor="w", pady=(0, 20))
                ctk.CTkLabel(content_frame, text="Language", font=("Comic Neue", 16, "bold")).pack(anchor="w", pady=10)
                language_dropdown = ctk.CTkOptionMenu(content_frame, values=["English", "Spanish", "French", "German", "Italian", "Portuguese", "Japanese", "Korean", "Chinese"], button_color="#114066", button_hover_color="#0d3553")
                language_dropdown.set("English")
                language_dropdown.pack(anchor="w")

            elif page_name == "Privacy":
                ctk.CTkLabel(content_frame, text="Privacy", font=("Comic Neue", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Configure your privacy settings.", text_color="gray").pack(anchor="w", pady=(0, 20))
                privacy_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                privacy_frame.pack(fill="x", pady=10)
                ctk.CTkSwitch(privacy_frame, text="Send crash reports", progress_color=ACCENT_BLUE).pack(anchor="w", pady=5)
                ctk.CTkSwitch(privacy_frame, text="Send usage statistics", progress_color=ACCENT_BLUE).pack(anchor="w", pady=5)
                ctk.CTkSwitch(privacy_frame, text="Show online status to friends", progress_color=ACCENT_BLUE).pack(anchor="w", pady=5)

        # --- BOTONES DEL SIDEBAR ---
        menu_buttons = {}

        def create_menu_btn(text, icon):
            btn = ctk.CTkButton(
                sidebar_frame,
                text=f"{icon}  {text}",
                anchor="w",
                fg_color="transparent",
                hover_color="#333333",
                height=40,
                command=lambda: select_page(text)
            )
            menu_buttons[text] = btn
            return btn

        create_menu_btn("Appearance", "🎨").pack(fill="x", padx=10, pady=2)
        create_menu_btn("Language", "🌐").pack(fill="x", padx=10, pady=2)
        create_menu_btn("Privacy", "🛡️").pack(fill="x", padx=10, pady=2)
        create_menu_btn("Java", "☕").pack(fill="x", padx=10, pady=2)

        # Información de versión abajo
        info_label = ctk.CTkLabel(sidebar_frame, text="Stella Client 0.1.0\nLinux 6.8.0", font=("Comic Neue", 10), text_color="gray")
        info_label.pack(side="bottom", pady=20)

        # Iniciar mostrando Appearance
        update_menu_buttons("Appearance")
        select_page("Appearance")

    # Configure grid layout for the main window
    app.grid_columnconfigure(0, weight=1)
    app.grid_columnconfigure(1, weight=0)  # Right column for buttons (no weight to stay fixed width)
    app.grid_rowconfigure(0, weight=0)
    app.grid_rowconfigure(1, weight=1)
    app.grid_rowconfigure(2, weight=0)

    # --- ROW 0: TITLE + ACCOUNT BUTTON ---
    title_frame = ctk.CTkFrame(app, fg_color="transparent")
    title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(40, 20), padx=40)
    title_frame.grid_columnconfigure(0, weight=1)

    # Título con gradiente simulado
    title_label = ctk.CTkLabel(title_frame, text="Stella Client", font=FONT_TITLE, text_color="#FFFFFF")
    title_label.grid(row=0, column=0, sticky="w")

    # Botón de cuenta mejorado
    current_user = minecraft.get_current_user()
    account_text = f"👤 {current_user[:15]}" if current_user else "👤 Account"
    
    account_btn = ctk.CTkButton(
        title_frame,
        text=account_text,
        width=140,
        height=42,
        fg_color=CARD_BG,
        border_color=ACCENT_BLUE,
        border_width=2,
        hover_color="#3D3D3D",
        font=FONT_BODY,
        command=open_account
    )
    account_btn.grid(row=0, column=1, sticky="e")

    # --- ROW 1: PLAY BUTTON + VERSION DROPDOWN ---
    play_frame = ctk.CTkFrame(app, fg_color="transparent")
    play_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20)
    play_frame.grid_columnconfigure(0, weight=1)

    # Play button (left-ish, centered)
    def launch_game():
        def game_thread():
            # Check if version will change due to mod compatibility
            settings = minecraft.load_settings()
            original_version = settings["version"]
            
            # Update RPC to playing status
            discord_rpc.update_playing()
            
            # Launch the game (this may change the version internally)
            minecraft.launch_minecraft()
            
            # Check if version was changed
            new_settings = minecraft.load_settings()
            if new_settings["version"] != original_version:
                # Show warning about version change
                def show_warning():
                    warning = ctk.CTkToplevel(app)
                    warning.title("Version Changed")
                    warning.geometry("500x200")
                    warning.after(10, warning.lift)
                    warning.configure(fg_color=BG_COLOR)
                    
                    ctk.CTkLabel(
                        warning, 
                        text="⚠️ Version Auto-Changed", 
                        font=("Comic Neue", 16, "bold")
                    ).pack(pady=20)
                    
                    ctk.CTkLabel(
                        warning, 
                        text=f"The game version was automatically changed from {original_version} to {new_settings['version']}\nto be compatible with your installed mods.\n\nPlease re-download mods from the Mods menu for the new version.",
                        font=("Comic Neue", 12),
                        justify="center"
                    ).pack(pady=10, padx=20)
                    
                    ctk.CTkButton(
                        warning,
                        text="OK",
                        command=warning.destroy,
                        fg_color=ACCENT_BLUE,
                        hover_color="#0d3553"
                    ).pack(pady=20)
                
                app.after(1000, show_warning)  # Show warning after 1 second
            
            # Update RPC back to menu when done
            discord_rpc.update_menu()

        threading.Thread(target=game_thread, daemon=True).start()

    play_btn = ctk.CTkButton(
        play_frame,
        text="▶  PLAY",
        font=FONT_SUBHEADING,
        height=65,
        width=220,
        fg_color=ACCENT_BLUE,
        hover_color="#0d3553",
        border_width=0,
        corner_radius=12,
        command=launch_game
    )
    play_btn.grid(row=0, column=0, sticky="ew", padx=(0, 15))

    # Version dropdown (right side)
    def on_version_change(selected_version):
        minecraft.set_version(selected_version)

    available_versions = minecraft.get_available_versions()
    current_version = minecraft.load_settings()["version"]

    version_dropdown = ctk.CTkOptionMenu(
        play_frame,
        values=available_versions,
        command=on_version_change,
        button_color="#114066",
        button_hover_color="#0d3553",
        text_color="#4A8FBF",
        fg_color=CARD_BG,
        font=FONT_BODY
    )
    version_dropdown.set(current_version)
    version_dropdown.grid(row=0, column=1, sticky="e", padx=(10, 0))

    # --- ROW 2: MODS + SETTINGS BUTTONS (bottom right) ---
    bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
    bottom_frame.grid(row=2, column=0, columnspan=2, sticky="se", padx=40, pady=(10, 25))

    buttons_stack = ctk.CTkFrame(bottom_frame, fg_color="transparent")
    buttons_stack.pack()

    mods_btn = ctk.CTkButton(
        buttons_stack,
        text="📦  Mods",
        width=130,
        height=42,
        fg_color=CARD_BG,
        border_color="#3a3a3a",
        border_width=1,
        hover_color="#3D3D3D",
        font=FONT_BODY,
        command=open_mods
    )
    mods_btn.pack(pady=(0, 8))

    settings_btn = ctk.CTkButton(
        buttons_stack,
        text="⚙  Settings",
        width=130,
        height=42,
        fg_color=CARD_BG,
        border_color="#3a3a3a",
        border_width=1,
        hover_color="#3D3D3D",
        font=FONT_BODY,
        command=open_settings
    )
    settings_btn.pack()

    # Initialize Discord RPC on app start (in background thread to avoid blocking UI)
    def init_rpc_thread():
        import time as time_module
        time_module.sleep(1)  # Give Discord time to detect the app
        print("\n" + "=" * 50)
        print("DISCORD RPC INITIALIZATION")
        print("=" * 50)
        discord_rpc.init_rpc()
        discord_rpc.update_menu()
        print("=" * 50 + "\n")

    rpc_thread = threading.Thread(target=init_rpc_thread, daemon=True)
    rpc_thread.start()

    # Close RPC on app close
    def on_closing():
        discord_rpc.close_rpc()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()