import subprocess
import minecraft_launcher_lib
import os
import threading
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Stella Client")
app.geometry("900x500")

title = ctk.CTkLabel(app, text="Stella Client", font=("Arial", 32))
title.pack(pady=40)


# ---------- LAUNCH ----------
def launch_minecraft():
    try:
        print("Installing / Launching...")

        minecraft_directory = os.path.expanduser("~/.stellaclient")
        version = "1.21.11"  

        minecraft_launcher_lib.install.install_minecraft_version(
            version,
            minecraft_directory
        )

        options = {
            "username": "mini",
            "uuid": "00000000000000000000000000000000",
            "token": "offline",
            "executablePath": "java"
        }

        command = minecraft_launcher_lib.command.get_minecraft_command(
            version,
            minecraft_directory,
            options
        )

        print("Starting Minecraft...")
        subprocess.Popen(command)

    except Exception as e:
        print("ERROR:", e)


# ---------- BUTTON ----------
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