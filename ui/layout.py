import threading
import launcher.minecraft as minecraft
import customtkinter as ctk

def start_ui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("900x500")

    topbar = ctk.CTkFrame(app, height=50, fg_color="#111111")
    topbar.pack(fill="x")

    account = ctk.CTkLabel(topbar, text="Account", font=("Arial", 16))
    account.pack(side="right", padx=20, pady=10)

    sidebar = ctk.CTkFrame(app, width=220, fg_color="#111111")
    sidebar.pack(side="left", fill="y")

    settings = ctk.CTkLabel(sidebar, text="Settings", font=("Arial", 16))
    settings.pack(side="bottom", anchor="w", padx=20, pady=20)

    title = ctk.CTkLabel(app, text="Stella Client", font=("Arial", 32))
    title.pack(pady=40)

    def play():
        print("Launching Minecraft...")
        # Movemos el hilo AQUÍ ADENTRO
        threading.Thread(
            target=minecraft.launch_minecraft,
            daemon=True
        ).start()

    play_button = ctk.CTkButton(
        app,
        text="PLAY",
        command=play  # Ahora 'play' sí ejecutará el hilo
    )
    play_button.pack(pady=20)

    app.mainloop()