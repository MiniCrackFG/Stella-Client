import subprocess
import minecraft_launcher_lib
import os
import threading
import customtkinter as ctk

# modo oscuro tipo launcher gaming
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ventana principal
app = ctk.CTk()
app.title("Stella Client")
app.geometry("900x500")

# titulo
title = ctk.CTkLabel(
    app,
    text="Stella Client",
    font=("Arial", 32)
)
title.pack(pady=40)

# boton play
def play():
    print("Launching Minecraft...")

play_button = ctk.CTkButton(
    app,
    text="PLAY",
    width=200,
    height=50,
    command=play
)
play_button.pack(pady=20)

# lanzar minecraft
def launch_minecraft():

    minecraft_directory = os.path.expanduser("~/.stellaclient")
    version = "1.21.1"   # ← usa una versión válida

    # descarga si no existe
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

    print("Command:", command)
    subprocess.run(command)


# boton play
def play():
    print("Launching Minecraft...")

    # ejecuta en segundo plano
    threading.Thread(
        target=launch_minecraft,
        daemon=True
    ).start()

app.mainloop()