import threading
import launcher.minecraft as minecraft
import launcher.discord_rpc as discord_rpc
import customtkinter as ctk

def start_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("900x500")

    # Colores Modrinth
    BG_COLOR = "#1C1C1C"
    SIDEBAR_BG = "#262626"
    ACCENT_GREEN = "#2E7D32"

    def open_account():
        account_window = ctk.CTkToplevel(app)
        account_window.title("Account")
        account_window.geometry("600x400")
        account_window.after(10, account_window.lift)
        account_window.configure(fg_color=BG_COLOR)

        # Header
        header_frame = ctk.CTkFrame(account_window, fg_color=SIDEBAR_BG, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(header_frame, text="👤  Account", font=("Arial", 20, "bold")).pack(pady=20, padx=20, anchor="w")

        # Content
        content_frame = ctk.CTkFrame(account_window, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Username section
        ctk.CTkLabel(content_frame, text="Username", font=("Arial", 16, "bold")).pack(anchor="w")
        settings = minecraft.load_settings()
        username_var = ctk.StringVar(value=settings.get("username", "mini"))
        username_entry = ctk.CTkEntry(content_frame, textvariable=username_var)
        username_entry.pack(fill="x", pady=(5, 20))

        # Save button
        def save_account():
            settings = minecraft.load_settings()
            settings["username"] = username_var.get()
            minecraft.save_settings(settings)
            ctk.CTkLabel(content_frame, text="✓ Saved successfully!", text_color=ACCENT_GREEN, font=("Arial", 12)).pack(pady=(10, 0))

        save_btn = ctk.CTkButton(
            content_frame,
            text="Save Changes",
            fg_color=ACCENT_GREEN,
            hover_color="#1B5E20",
            command=save_account
        )
        save_btn.pack(pady=20)

        # Placeholder info
        ctk.CTkLabel(
            content_frame,
            text="Profile features coming soon...",
            font=("Arial", 12),
            text_color="gray"
        ).pack(anchor="w", pady=(20, 0))

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

    title_label = ctk.CTkLabel(title_frame, text="Stella Client", font=("Arial", 32, "bold"))
    title_label.grid(row=0, column=0, sticky="w")

    account_btn = ctk.CTkButton(
        title_frame,
        text="👤 Account",
        width=120,
        height=40,
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
        font=("Arial", 24, "bold"),
        height=60,
        width=200,
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
        button_color=ACCENT_GREEN,
        button_hover_color="#1B5E20",
        text_color="gray"
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
        command=open_mods
    )
    mods_btn.pack(pady=(0, 10))

    settings_btn = ctk.CTkButton(
        buttons_stack,
        text="⚙ Settings",
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
        discord_rpc.close_rpc()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()