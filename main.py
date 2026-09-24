import logging
import os
import sys
import threading
import webview

import launcher.discord_rpc as discord_rpc
import launcher.instances as instances
import launcher.minecraft as minecraft
from api import API


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def ensure_dirs():
    base = os.path.expanduser("~/.stellaclient")
    for d in ["", "mods", "forge", "logs", "crash-reports", "versions", "instances"]:
        os.makedirs(os.path.join(base, d), exist_ok=True)


def _find_asset(name):
    for base in (os.path.dirname(__file__), getattr(sys, '_MEIPASS', None)):
        if base:
            for sub in ("assets", "ui"):
                p = os.path.join(base, sub, name)
                if os.path.exists(p):
                    return p
    return os.path.join(os.path.dirname(__file__), "assets", name)


def _set_default_icon():
    icon_path = _find_asset("icon-256.png")
    if not icon_path:
        return
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        Gtk.Window.set_default_icon_from_file(icon_path)
        logging.info("Default window icon set")
    except Exception as e:
        logging.warning("Could not set default icon: %s", e)


def set_window_icon(window):
    icon_path = _find_asset("icon-256.png")
    if not icon_path:
        return
    try:
        if hasattr(window, 'set_icon'):
            window.set_icon(icon_path)
            logging.info("Icon set via window.set_icon")
            return
    except Exception:
        pass
    try:
        import gi
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
        if hasattr(window, 'native') and window.native:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            window.native.set_icon(pixbuf)
            logging.info("Icon set via native Gtk window")
    except Exception as e:
        logging.warning("Could not set window icon: %s", e)



def start_ui():
    ensure_dirs()
    instances.ensure_default_instance()
    settings = minecraft.load_settings()
    api = API()

    if settings.get("discord_rpc", True):
        threading.Thread(target=lambda: [discord_rpc.init_rpc(), discord_rpc.update_menu()], daemon=True).start()

    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")

    if not settings.get("hw_accel", True):
        os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

    _set_default_icon()

    window = webview.create_window(
        title="Stella Client",
        url=html_path,
        js_api=api,
        width=1000,
        height=600,
        min_size=(800, 450),
        resizable=True,
        fullscreen=False,
        maximized=True,
        frameless=True,
        easy_drag=False,
        background_color="#0a0a0a",
    )

    api._window = window

    if window and window.events:
        window.events.closing += discord_rpc.close_rpc

    webview.start(debug=False, func=lambda: set_window_icon(window))


if __name__ == "__main__":
    start_ui()
