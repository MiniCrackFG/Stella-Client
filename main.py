import os
import sys

sys.path.append("/usr/lib/python3/dist-packages")

import threading
import webview

import launcher.discord_rpc as discord_rpc
import launcher.minecraft as minecraft
from api import API


def ensure_dirs():
    base = os.path.expanduser("~/.stellaclient")
    for d in ["", "mods", "forge", "logs", "crash-reports", "versions"]:
        os.makedirs(os.path.join(base, d), exist_ok=True)


def start_ui():
    ensure_dirs()
    settings = minecraft.load_settings()
    api = API()

    if settings.get("discord_rpc", True):
        threading.Thread(target=lambda: [discord_rpc.init_rpc(), discord_rpc.update_menu()], daemon=True).start()

    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")

    window = webview.create_window(
        title="Stella Client",
        url=html_path,
        js_api=api,
        width=1000,
        height=600,
        min_size=(800, 450),
        resizable=True,
        fullscreen=False,
        background_color="#0a0a0a",
    )

    webview.start(debug=True)


if __name__ == "__main__":
    start_ui()
