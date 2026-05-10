import customtkinter as ctk
import threading
from launcher.minecraft import launch_minecraft

def start_ui():

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Stella Client")
    app.geometry("900x500")

    title = ctk.CTkLabel(
        app,
        text="Stella Client",
        font=("Arial", 32)
    )
    title.pack(pady=40)

    def play():
        print("Launching Minecraft...")
        threading.Thread(
            target=launch_minecraft,
            daemon=True
        ).start()

    play_button = ctk.CTkButton(
        app,
        text="PLAY",
        width=200,
        height=50,
        command=play
    )
    play_button.pack(pady=20)

    app.mainloop()
