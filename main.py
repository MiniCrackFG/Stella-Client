import logging
import os
import sys
import threading
import time


def _drop_bundled_gui_paths():
    """Retira las variables con las que PyInstaller apunta la pila gráfica al bundle.

    PyInstaller da por hecho que una aplicación con `gi` empaqueta GTK, así que sus
    runtime hooks apuntan GI_TYPELIB_PATH, GTK_PATH, GDK_PIXBUF_MODULE_FILE y
    XDG_DATA_DIRS a `sys._MEIPASS`. Aquí GTK y WebKitGTK los pone la distro a
    propósito —empaquetarlos congelaría su versión y la glibc de la máquina donde
    se compiló—, y esas variables dejarían al programa buscando en directorios que
    el paquete no lleva.
    """
    bundle = getattr(sys, "_MEIPASS", None)
    if not bundle:
        return  # sin congelar no hay nada que deshacer
    bundle = os.path.abspath(bundle)

    def _is_bundled(value):
        value = os.path.abspath(value)
        return value == bundle or value.startswith(bundle + os.sep)

    for var in (
        "GI_TYPELIB_PATH",
        "GTK_DATA_PREFIX",
        "GTK_EXE_PREFIX",
        "GTK_PATH",
        "GTK_MODULES",
        "PANGO_LIBDIR",
        "PANGO_SYSCONFDIR",
        "GDK_PIXBUF_MODULE_FILE",
        "GDK_PIXBUF_MODULEDIR",
        "GIO_MODULE_DIR",
        "GSETTINGS_SCHEMA_DIR",
    ):
        value = os.environ.get(var)
        if value and _is_bundled(value):
            os.environ.pop(var, None)

    # XDG_DATA_DIRS es una lista: se quita sólo la entrada del bundle, para no
    # arrastrar con ella las rutas del sistema.
    entries = [e for e in os.environ.get("XDG_DATA_DIRS", "").split(os.pathsep) if e]
    if entries:
        remaining = [e for e in entries if not _is_bundled(e)]
        if remaining:
            os.environ["XDG_DATA_DIRS"] = os.pathsep.join(remaining)
        else:
            os.environ.pop("XDG_DATA_DIRS", None)


# Antes de importar webview a propósito: pywebview carga su backend GTK y las
# variables tienen que estar ya en su sitio.
_drop_bundled_gui_paths()

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


# --- Comprobación del entorno (--check) ---------------------------------

_DISPLAY_VARS = ("DISPLAY", "WAYLAND_DISPLAY")

# Librerías gráficas cuyo origen conviene poder citar al verificar un paquete.
_CHECK_LIBS = ("libgtk-3", "libwebkit2gtk", "libglib-2.0", "libgirepository-")


def _loaded_library_paths(prefixes):
    """Rutas de las librerías realmente cargadas, leídas de `/proc/self/maps`."""
    found = {}
    try:
        with open("/proc/self/maps", "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if " /" not in line:
                    continue
                path = "/" + line.rstrip("\n").split(" /", 1)[1]
                name = os.path.basename(path)
                for prefix in prefixes:
                    if name.startswith(prefix):
                        found.setdefault(prefix, path)
    except OSError:
        pass
    return found


def check_environment():
    """Comprueba que el binario puede arrancar en este sistema y devuelve el código de salida.

    Existe para poder verificar los paquetes en otras distros sin pantalla: carga los
    typelibs de GTK y WebKitGTK, informa de dónde sale cada librería —el diseño del
    paquete es que las ponga la distro, así que verlas dentro del bundle sería un aviso—
    y, si hay pantalla, llega a crear y cerrar la ventana de verdad.
    """
    bundle = getattr(sys, "_MEIPASS", "") or ""
    print("stella-client — comprobación del entorno")
    print(f"  ejecutable : {sys.executable}")
    print(f"  python     : {sys.version.split()[0]}")
    if bundle:
        print(f"  bundle     : {bundle}")

    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import GLib, Gtk, WebKit2

        print(f"  PyGObject  : {gi.__version__}")
        print(f"  GLib       : {GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}")
        print(f"  GTK        : {Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}")
        print(
            "  WebKitGTK  : "
            f"{WebKit2.get_major_version()}.{WebKit2.get_minor_version()}.{WebKit2.get_micro_version()}"
        )
    except Exception as e:
        print(f"  FALLO al cargar GTK/WebKitGTK: {e}")
        print("RESULTADO: este sistema no tiene lo necesario para arrancar")
        return 1

    bundled = []
    for prefix, path in sorted(_loaded_library_paths(_CHECK_LIBS).items()):
        inside = bool(bundle) and os.path.abspath(path).startswith(os.path.abspath(bundle))
        if inside:
            bundled.append(prefix)
        print(f"  {prefix:<14} {'[EN EL BUNDLE] ' if inside else ''}{path}")
    if bundled:
        print(
            "  AVISO: van dentro del paquete " + ", ".join(bundled)
            + "; deberían venir de la distro para no fijar su versión"
        )

    display = next(((v, os.environ[v]) for v in _DISPLAY_VARS if os.environ.get(v)), None)
    if not display:
        print("  pantalla   : sin DISPLAY ni WAYLAND_DISPLAY; no se crea la ventana")
        print("RESULTADO: las librerías gráficas cargan correctamente")
        return 0

    print(f"  pantalla   : {display[0]}={display[1]}")
    # Si WebKit se cuelga, el vigilante lo convierte en un código de salida claro
    # en vez de dejar el proceso vivo para siempre.
    watchdog = threading.Timer(60, os._exit, [124])
    watchdog.daemon = True
    watchdog.start()
    try:
        window = webview.create_window(
            "Stella Client (check)", html="<html><body>ok</body></html>", hidden=True
        )

        def _close_after_start():
            time.sleep(1.5)
            window.destroy()

        webview.start(debug=False, func=_close_after_start)
    except Exception as e:
        print(f"  FALLO al crear la ventana: {e}")
        print("RESULTADO: GTK carga pero la ventana no se pudo abrir")
        return 1
    finally:
        watchdog.cancel()

    print("RESULTADO: la ventana se creó y se cerró correctamente")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        sys.exit(check_environment())
    start_ui()
