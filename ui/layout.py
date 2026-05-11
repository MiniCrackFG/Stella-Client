import threading
import launcher.minecraft as minecraft
import launcher.discord_rpc as discord_rpc
import customtkinter as ctk
import time
import requests
import os

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

        resp = requests.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=token_data
        )

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

def start_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("900x500")
    app.configure(fg_color="#111111")

    # Crear fuente Comic Neue para usar en CustomTkinter
    FONT_MAIN = ctk.CTkFont(family="Comic Neue", size=16)
    FONT_BOLD = ctk.CTkFont(family="Comic Neue", size=18, weight="bold")
    FONT_LARGE = ctk.CTkFont(family="Comic Neue", size=36, weight="bold")
    FONT_TITLE = ctk.CTkFont(family="Comic Neue", size=48, weight="bold")
    print("✓ Fuente Comic Neue configurada")

    # Colores
    BG_COLOR = "#1C1C1C"
    SIDEBAR_BG = "#262626"
    ACCENT_GREEN = "#00FF00"

    def open_account():
        print("Abriendo ventana de cuenta...")
        account_window = ctk.CTkToplevel(app)
        account_window.title("Account")
        account_window.geometry("600x500")
        account_window.after(10, account_window.lift)
        account_window.configure(fg_color="#2b2b2b")

        header_frame = ctk.CTkFrame(account_window, fg_color="#1a1a1a", corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header_frame, text="👤  Account", font=("Arial", 20, "bold"), text_color="white").pack(pady=15, padx=20, anchor="w")

        content_frame = ctk.CTkFrame(account_window, fg_color="#2b2b2b")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Verificar si ya está logueado
        current_user = minecraft.get_current_user()

        if current_user:
            # Mostrar info de la cuenta
            ctk.CTkLabel(content_frame, text="✓ CUENTA PREMIUM", font=("Arial", 14, "bold"), text_color=ACCENT_GREEN).pack(anchor="w", pady=(10, 5))

            auth_data = minecraft.load_auth()
            ctk.CTkLabel(content_frame, text=f"Usuario: {current_user}", font=("Arial", 16, "bold"), text_color="white").pack(anchor="w", pady=5)

            uuid = auth_data.get("uuid", "N/A") if auth_data else "N/A"
            ctk.CTkLabel(content_frame, text=f"UUID: {uuid}", font=("Arial", 12), text_color="#888888").pack(anchor="w", pady=2)

            ctk.CTkLabel(content_frame, text="Puedes jugar con tu cuenta premium ahora.", font=("Arial", 12), text_color="#aaaaaa", wraplength=500).pack(anchor="w", pady=(15, 20))

            def logout():
                minecraft.logout()
                account_window.destroy()
                open_account()

            ctk.CTkButton(
                content_frame,
                text="Cerrar Sesión",
                fg_color="#c42b1c",
                hover_color="#8b1e14",
                text_color="white",
                command=logout,
                height=40
            ).pack(pady=20, padx=20, fill="x")

        else:
            # Mostrar opciones de login
            ctk.CTkLabel(content_frame, text="Iniciar Sesión", font=("Arial", 18, "bold"), text_color="white").pack(anchor="w", pady=(10, 5))
            ctk.CTkLabel(content_frame, text="Inicia sesión con tu cuenta de Microsoft para jugar con tu cuenta premium.", font=("Arial", 12), text_color="#aaaaaa", wraplength=500).pack(anchor="w", pady=(0, 15))

            status_label = ctk.CTkLabel(content_frame, text="", font=("Arial", 12), text_color="white")
            status_label.pack(pady=5)

            code_display = ctk.CTkLabel(content_frame, text="---", font=("Arial", 28, "bold"), text_color=ACCENT_GREEN)
            code_display.pack(pady=10)

            def start_login():
                try:
                    status_label.configure(text="Obteniendo código...")
                    device_info = minecraft.get_device_code_info()
                    code_display.configure(text=device_info.get("user_code", "Error"))
                    status_label.configure(text="Ingresa este código en el navegador y espera...")

                    import webbrowser
                    webbrowser.open(device_info.get("verification_uri", ""))

                    threading.Thread(target=do_login_poll, args=(device_info, account_window, status_label, code_display), daemon=True).start()
                except Exception as e:
                    status_label.configure(text=f"Error: {str(e)}", text_color="red")

            ctk.CTkButton(
                content_frame,
                text="► Iniciar Sesión con Microsoft",
                fg_color=ACCENT_GREEN,
                hover_color="#00cc00",
                text_color="black",
                command=start_login,
                height=50,
                font=("Arial", 16, "bold")
            ).pack(pady=20, padx=20, fill="x")

        # Fin de open_account

    def open_mods():
        mods_window = ctk.CTkToplevel(app)
        mods_window.title("Mods")
        mods_window.geometry("800x500")
        mods_window.after(10, mods_window.lift)
        mods_window.configure(fg_color=BG_COLOR)

        # Header
        header_frame = ctk.CTkFrame(mods_window, fg_color=SIDEBAR_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(header_frame, text="📦  Mods Manager", font=("Arial", 20, "bold")).pack(pady=20, padx=20, anchor="w")

        # Content
        content_frame = ctk.CTkFrame(mods_window, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Title and description
        ctk.CTkLabel(content_frame, text="Installed Mods", font=("Arial", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(content_frame, text="Manage your Minecraft mods here.", text_color="gray", font=("Arial", 12)).pack(anchor="w", pady=(0, 20))

        # Mods list (placeholder)
        mods_list_frame = ctk.CTkFrame(content_frame, fg_color=SIDEBAR_BG, corner_radius=10)
        mods_list_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            mods_list_frame,
            text="No mods installed yet.\nClick 'Browse Mods' to get started!",
            text_color="gray",
            font=("Arial", 12),
            justify="center"
        ).pack(fill="both", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        browse_btn = ctk.CTkButton(
            button_frame,
            text="Browse Mods",
            fg_color=ACCENT_GREEN,
            hover_color="#1B5E20"
        )
        browse_btn.pack(side="left", padx=(0, 10))

        refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh",
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT_GREEN,
            text_color=ACCENT_GREEN
        )
        refresh_btn.pack(side="left")

    def open_settings():
        settings_window = ctk.CTkToplevel(app)
        settings_window.title("Settings")
        settings_window.geometry("850x600")
        settings_window.after(10, settings_window.lift)

        # Colores Modrinth
        BG_COLOR = "#1C1C1C"
        SIDEBAR_BG = "#262626"
        ACCENT_GREEN = "#2E7D32"

        settings_window.configure(fg_color=BG_COLOR)

        # Dividimos en 2 columnas: 0 (Menú) y 1 (Contenido)
        settings_window.grid_columnconfigure(1, weight=1)
        settings_window.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (IZQUIERDA) ---
        sidebar_frame = ctk.CTkFrame(settings_window, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(10, weight=1) # Empuja lo de abajo

        # Título del sidebar
        label_title = ctk.CTkLabel(sidebar_frame, text="⚙  Settings", font=("Arial", 18, "bold"))
        label_title.pack(pady=25, padx=20, anchor="w")

        # --- CONTENIDO (DERECHA) ---
        content_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        content_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=25)

        # FUNCIÓN MÁGICA: Cambia lo que se ve a la derecha
        def select_page(page_name):
            # Limpiar todo lo que haya antes
            for widget in content_frame.winfo_children():
                widget.destroy()

            if page_name == "Appearance":
                # Título y descripción
                ctk.CTkLabel(content_frame, text="Appearance", font=("Arial", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Customize the look of Stella Client.", text_color="gray").pack(anchor="w", pady=(0, 20))

                # Sección de Temas
                ctk.CTkLabel(content_frame, text="Color theme", font=("Arial", 16, "bold")).pack(anchor="w", pady=10)

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

                    ctk.CTkLabel(box, text=name, font=("Arial", 12)).pack(side="bottom", pady=5)

                # Switch de Renderizado Avanzado
                ctk.CTkLabel(content_frame, text="Rendering", font=("Arial", 16, "bold")).pack(anchor="w", pady=(30, 10))

                render_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                render_frame.pack(fill="x")

                ctk.CTkLabel(render_frame, text="Advanced rendering effects", text_color="gray").pack(side="left")
                ctk.CTkSwitch(render_frame, text="", progress_color=ACCENT_GREEN).pack(side="right")

            elif page_name == "Java":
                # 1. Cargar los ajustes actuales desde minecraft.py
                settings = minecraft.load_settings()

                # 2. Título y descripción
                ctk.CTkLabel(content_frame, text="Java & Memory", font=("Arial", 24, "bold")).pack(anchor="w")
                ctk.CTkLabel(content_frame, text="Configure how much RAM Stella Client can use.", text_color="gray").pack(anchor="w", pady=(0, 20))

                # 3. Label dinámico de RAM
                ram_label = ctk.CTkLabel(content_frame, text=f"Allocated Memory: {settings['ram']} GB", font=("Arial", 16, "bold"))
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
                    button_color=ACCENT_GREEN,
                    progress_color=ACCENT_GREEN,
                    command=update_ram
                )
                ram_slider.set(settings['ram'])
                ram_slider.pack(fill="x", pady=10)

                ctk.CTkLabel(
                    content_frame,
                    text="Note: Allocating too much RAM can slow down your system.",
                    font=("Arial", 12),
                    text_color="gray"
                ).pack(anchor="w")

        # --- BOTONES DEL SIDEBAR ---
        def create_menu_btn(text, icon):
            return ctk.CTkButton(
                sidebar_frame,
                text=f"{icon}  {text}",
                anchor="w",
                fg_color="transparent",
                hover_color="#333333",
                height=40,
                command=lambda: select_page(text)
            )

        btn_app = create_menu_btn("Appearance", "🎨")
        btn_app.configure(fg_color=ACCENT_GREEN) # Marcamos la primera por defecto
        btn_app.pack(fill="x", padx=10, pady=2)

        create_menu_btn("Language", "🌐").pack(fill="x", padx=10, pady=2)
        create_menu_btn("Privacy", "🛡️").pack(fill="x", padx=10, pady=2)
        create_menu_btn("Java", "☕").pack(fill="x", padx=10, pady=2)

        # Información de versión abajo
        info_label = ctk.CTkLabel(sidebar_frame, text="Stella Client 0.1.0\nLinux 6.8.0", font=("Arial", 10), text_color="gray")
        info_label.pack(side="bottom", pady=20)

        # Iniciar mostrando Appearance
        select_page("Appearance")

    # Configure grid layout for the main window
    app.grid_columnconfigure(0, weight=1)
    app.grid_columnconfigure(1, weight=0)  # Right column for buttons (no weight to stay fixed width)
    app.grid_rowconfigure(0, weight=0)
    app.grid_rowconfigure(1, weight=1)
    app.grid_rowconfigure(2, weight=0)

    # --- ROW 0: TITLE + ACCOUNT BUTTON ---
    title_frame = ctk.CTkFrame(app, fg_color="transparent")
    title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(50, 20), padx=20)
    title_frame.grid_columnconfigure(0, weight=1)

    title_label = ctk.CTkLabel(title_frame, text="Stella Client", font=FONT_TITLE)
    title_label.grid(row=0, column=0, sticky="w")

    current_user = minecraft.get_current_user()
    if current_user:
        account_btn_text = f"👤 {current_user[:12]}"
    else:
        account_btn_text = "👤 Account"

    account_btn = ctk.CTkButton(
        title_frame,
        text=account_btn_text,
        width=140,
        height=40,
        font=FONT_MAIN,
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
            # Update RPC to playing status
            discord_rpc.update_playing()
            # Launch the game
            minecraft.launch_minecraft()
            # Update RPC back to menu when done
            discord_rpc.update_menu()

        threading.Thread(target=game_thread, daemon=True).start()

    play_btn = ctk.CTkButton(
        play_frame,
        text="▶  Play",
        font=FONT_LARGE,
        height=70,
        width=220,
        fg_color="#2E7D32",
        hover_color="#1B5E20",
        command=launch_game
    )
    play_btn.grid(row=0, column=0, sticky="ew")

    # Version dropdown (right side)
    def on_version_change(selected_version):
        minecraft.set_version(selected_version)

    available_versions = minecraft.get_available_versions()
    current_version = minecraft.load_settings()["version"]

    version_dropdown = ctk.CTkOptionMenu(
        play_frame,
        values=available_versions,
        command=on_version_change,
        button_color="#3a3a3a",
        button_hover_color="#4a4a4a",
        text_color="white"
    )
    version_dropdown.set(current_version)
    version_dropdown.grid(row=0, column=1, sticky="e", padx=(10, 0))

    # --- ROW 2: MODS + SETTINGS BUTTONS (bottom right) ---
    bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
    bottom_frame.grid(row=2, column=0, columnspan=2, sticky="se", padx=20, pady=20)

    buttons_stack = ctk.CTkFrame(bottom_frame, fg_color="transparent")
    buttons_stack.pack()

    mods_btn = ctk.CTkButton(
        buttons_stack,
        text="📦 Mods",
        width=120,
        height=40,
        font=FONT_MAIN,
        command=open_mods
    )
    mods_btn.pack(pady=(0, 10))

    settings_btn = ctk.CTkButton(
        buttons_stack,
        text="⚙ Settings",
        font=FONT_MAIN,
        width=120,
        height=40,
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
        # Cerrar todas las ventanas primero
        for widget in app.winfo_children():
            if isinstance(widget, ctk.CTkToplevel):
                try:
                    widget.destroy()
                except:
                    pass

        # Cerrar RPC y esperar un poco
        discord_rpc.close_rpc()
        time.sleep(0.5)

        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()