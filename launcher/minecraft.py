import subprocess
import minecraft_launcher_lib
import os

def launch_minecraft():

    print("Installing / Launching Minecraft...")

    minecraft_directory = os.path.expanduser("~/.stellaclient")
    os.makedirs(minecraft_directory, exist_ok=True)

    version = "1.21.1" 

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

    print(command)

    subprocess.run(command)


if __name__ == "__main__":
    launch_minecraft()