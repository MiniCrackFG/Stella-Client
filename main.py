import logging
import logging.handlers
import os
import re
import subprocess
import sys
import threading
import time

import launcher.paths as paths


def _setup_logging():
    """Deja el registro también en un fichero cuando no hay consola donde escribirlo.

    El ejecutable de Windows va sin consola —una ventana de consola aparecería
    detrás del launcher—, así que `sys.stderr` es None y un registro sólo a
    consola se perdería entero. Ese fichero es lo único que queda después para
    leer qué falló en una máquina donde no hay terminal.
    """
    handlers = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))

    log_file_error = None
    if paths.is_windows():
        try:
            os.makedirs(paths.logs_dir(), exist_ok=True)
            handlers.append(
                logging.handlers.RotatingFileHandler(
                    os.path.join(paths.logs_dir(), "stella.log"),
                    maxBytes=1_000_000,
                    backupCount=3,
                    encoding="utf-8",
                )
            )
        except OSError as e:
            log_file_error = e  # sin sitio para el registro, pero se arranca igual

    if not handlers:
        handlers = [logging.NullHandler()]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    if log_file_error is not None:
        logging.warning(f"No se pudo escribir el registro en fichero: {log_file_error}")


def _drop_bundled_gui_paths():
    """Retira las variables con las que PyInstaller apunta la pila gráfica al bundle.

    PyInstaller da por hecho que una aplicación con `gi` empaqueta GTK, así que sus
    runtime hooks apuntan GI_TYPELIB_PATH, GTK_PATH, GDK_PIXBUF_MODULE_FILE y
    XDG_DATA_DIRS a `sys._MEIPASS`. Aquí GTK y WebKitGTK los pone la distro a
    propósito —empaquetarlos congelaría su versión y la glibc de la máquina donde
    se compiló—, y esas variables dejarían al programa buscando en directorios que
    el paquete no lleva.
    """
    if not sys.platform.startswith("linux"):
        return  # en Windows y macOS la pila gráfica no sale de aquí
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


def _use_gtk_backend():
    """Deja claro que en Linux la ventana la dibuja GTK.

    pywebview se pasa a Qt por su cuenta cuando ve `KDE_FULL_SESSION`, y eso en
    KDE significa dos cosas: que cada arranque empieza intentando cargar Qt
    —con su volcado de error en el registro, que parece un fallo y no lo es— y
    que en un equipo con Qt instalado la ventana cambiaría de motor. Aquí la
    interfaz está escrita contra GTK: el icono, el portapapeles y `--check` son
    de GTK. Se pide ese backend y se respeta lo que alguien haya fijado a mano.
    """
    os.environ.setdefault("PYWEBVIEW_GUI", "gtk")


def _avoid_wayland_frame():
    """Pide el backend X11 cuando la sesión es Wayland.

    Sin marco nativo, en Wayland el compositor dibuja su propia barra y no hay
    forma de pedirle que no la dibuje: el protocolo sólo permite elegir entre
    "la dibuja la aplicación" o "la dibuja el compositor", y GTK 3 no puede
    elegir ninguna de las dos a secas. El resultado es que al título que ya trae
    el launcher se le suma por encima el del sistema. Por X11 la petición sí
    llega al gestor de ventanas, así que la ventana queda con una sola barra:
    la del launcher.

    Se respeta `GDK_BACKEND` si ya viene puesto —quien lo fija a mano manda— y
    sin XWayland (no hay `DISPLAY`) no se toca nada: forzar X11 ahí dejaría al
    launcher sin ventana.
    """
    if os.environ.get("GDK_BACKEND"):
        return
    if not os.environ.get("WAYLAND_DISPLAY") or not os.environ.get("DISPLAY"):
        return
    os.environ["GDK_BACKEND"] = "x11"


def _x11_backend():
    """Si esta sesión va a acabar dibujando por X11, sea por el sistema o por nosotros.

    Tres casos cuentan: quien ya trae `GDK_BACKEND=x11`, la sesión Wayland con
    XWayland (donde lo pedimos nosotros, ver `_avoid_wayland_frame`) y la sesión
    X11 de toda la vida, que no tiene `WAYLAND_DISPLAY` y sí `DISPLAY`.
    """
    backend = os.environ.get("GDK_BACKEND", "")
    if backend:
        return "x11" in backend.split(":")
    return bool(os.environ.get("DISPLAY")) and not os.environ.get("WAYLAND_DISPLAY")


def _avoid_client_side_decorations():
    """Pide al gestor de ventanas que la ventana vaya sin decoración, por la vía clásica.

    En X11 GTK puede llevar las decoraciones por su cuenta (CSD) o dejarlas en
    manos del gestor. Con CSD, GTK se queda con los bordes de la ventana para sí
    —son suyos los márgenes invisibles que permiten redimensionar— y eso choca
    con una ventana sin marco a la que le ponemos tiradores propios: `GTK_CSD=0`
    deja la ventana completamente lisa y con la petición de «sin decoración»
    puesta donde el gestor la lee, que es lo que se quiere aquí. Es una variable
    de GTK y no un ajuste nuestro, así que no se pisa si alguien la fija.

    Sin gestor de ventanas de por medio —Wayland puro— no se toca: allí las
    decoraciones las dibuja el compositor y `GTK_CSD=0` sólo traería rarezas.
    """
    if not _x11_backend():
        return
    os.environ.setdefault("GTK_CSD", "0")


# Antes de importar webview a propósito: pywebview elige backend al importarse y
# las variables tienen que estar ya en su sitio.
if not paths.is_windows():
    _use_gtk_backend()
    _avoid_wayland_frame()
    _avoid_client_side_decorations()
_drop_bundled_gui_paths()

import webview

import launcher.discord_rpc as discord_rpc
import launcher.instances as instances
import launcher.minecraft as minecraft
from api import API


_setup_logging()


def ensure_dirs():
    base = paths.data_dir()
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
    """Icono por defecto de las ventanas GTK.

    En Windows no hay nada que fijar en tiempo de ejecución: el icono va como
    recurso dentro del propio `.exe` y la barra de tareas lo toma de ahí.
    """
    if paths.is_windows():
        return
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
    """Icono de esta ventana concreta. Para Windows, ver `_set_default_icon`."""
    if paths.is_windows():
        return
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



def _winwindow():
    """El módulo de ventana de Windows, importado sólo cuando se está en Windows.

    Aquí arriba no puede estar: en Linux ni siquiera existe `ctypes.WINFUNCTYPE`,
    que es con lo que declara sus llamadas al sistema.
    """
    from launcher import winwindow

    return winwindow


def _wait_for_window(window, timeout=5.0):
    """Espera a que la ventana pueda atendernos y devuelve si llegó a tiempo.

    `webview.start(func=...)` lanza este hilo *antes* de crear la ventana, así
    que sin esta espera el trabajo llegaría a una ventana que todavía no está
    —no haría nada, y la ventana aparecería en su sitio de siempre, que es justo
    lo que se quería arreglar—. Se espera también a que pywebview la haya
    enseñado una vez (es su forma de dejarla lista antes de ocultarla), porque
    hasta ese momento pedir que se enseñe se queda en nada, sin error ninguno.

    Dura milisegundos: la ventana se construye en cuanto arranca el bucle.
    """
    events = getattr(window, "events", None)
    shown = getattr(events, "shown", None)
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready = getattr(window, "native", None) is not None
        if ready and (shown is None or shown.is_set()):
            return True
        time.sleep(0.05)
    return False


def _show_window(window, attempts=8):
    """Enseña la ventana y comprueba que de verdad se ve.

    Con la ventana creada oculta, una petición que llegue antes de tiempo no
    falla: simplemente no la enseña. Como quedarse sin interfaz es el peor final
    posible, aquí se insiste hasta que Windows confirma que está en pantalla.
    """
    winwindow = _winwindow()
    for _ in range(attempts):
        try:
            window.show()
            if winwindow.is_visible(window):
                return True
        except Exception as e:
            logging.warning("No se pudo mostrar la ventana: %s", e)
            return False
        time.sleep(0.25)
    logging.warning("La ventana no confirmó que esté visible")
    return False


def _place_window(window, settings):
    """Coloca la ventana antes de que se vea, con la geometría de la última vez.

    Pase lo que pase la ventana se enseña: quedarse sin interfaz por no poder
    centrarla sería un arreglo peor que el problema.
    """
    try:
        _wait_for_window(window)
        winwindow = _winwindow()
        # Sin marco nativo Windows no ofrece redimensionar; devolverle ese borde
        # es lo primero, y de paso es también lo que hace que maximizar de
        # verdad ocupe la pantalla menos la barra de tareas.
        winwindow.enable_sizing_frame(window)
        remembered = settings.get("window")
        winwindow.place(window, remembered)
        if isinstance(remembered, dict) and remembered.get("maximized"):
            # No `window.maximize()`: en Windows maximizar así es estirar la
            # ventana hasta el borde de la pantalla, barra de tareas incluida.
            winwindow.maximize(window)
    except Exception as e:
        logging.warning("No se pudo colocar la ventana: %s", e)
    finally:
        _show_window(window)


def _remember_window(window):
    """Guarda tamaño, posición y si estaba maximizada, para abrir igual la próxima vez."""
    try:
        geometry = _winwindow().capture(window)
        if not geometry:
            return
        settings = minecraft.load_settings()
        settings["window"] = geometry
        minecraft.save_settings(settings)
        logging.info("Geometría de la ventana guardada en %s: %s", paths.config_file(), geometry)
    except Exception as e:
        logging.warning("No se pudo guardar la geometría de la ventana: %s", e)


def _report_start_failure(error):
    """Explica en la terminal por qué no se abrió la ventana.

    Sin esto, lo que ve quien lo sufre es el rastro interno de pywebview, que
    intenta GTK, luego Qt y luego se rinde: veinte líneas de tres módulos que no
    nombran ni una vez lo que falta. Un usuario reportó exactamente eso —un
    `undefined symbol` en `_gi.so` por un paquete compilado contra una GLib más
    nueva que la del sistema— y el mensaje no daba ninguna pista.

    El caso `undefined symbol` se reconoce aparte porque no es un problema de esa
    máquina: es el paquete el que está mal y quien lo recibe no puede arreglarlo
    instalando nada.
    """
    detail = str(error) or error.__class__.__name__
    recognized = False

    print()
    print("No se pudo abrir la ventana.")

    if "undefined symbol" in detail:
        recognized = True
        print("  Esta compilación pide una versión de GLib más nueva que la del sistema:")
        print(f"    {detail}")
        print("  No es un problema de tu instalación: avisa de esta línea, que el")
        print("  paquete se puede reconstruir contra lo que sí tienes.")
    elif paths.is_windows():
        recognized = True
        print("  En Windows la ventana la dibuja el motor de Edge (WebView2), con el")
        print("  puente de pythonnet. Las dos cosas se comprueban con:")
        print("    stella-client-check")
    else:
        recognized = True
        print("  La ventana la dibujan GTK 3 y WebKitGTK, que las tiene que poner tu")
        print("  sistema. Instálalas y vuelve a intentarlo:")
        print("    Debian/Ubuntu : sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1")
        print("    Fedora        : sudo dnf install python3-gobject gtk3 webkit2gtk4.1")
        print("    Arch          : sudo pacman -S python-gobject gtk3 webkit2gtk-4.1")
        print(f"  Detalle: {detail}")
        print("  Versiones y de dónde sale cada librería:")
        print("    stella-client --check")

    if recognized:
        logging.error("No se pudo abrir la ventana: %s", detail)
    else:
        # Aquí no se sabe qué pasó, así que el rastro entero al registro.
        logging.exception("No se pudo abrir la ventana")


def start_ui():
    # Antes que nada: si los datos vienen de la ruta antigua se trasladan, y así
    # cualquier lectura posterior ya los encuentra donde toca.
    paths.migrate_once()
    ensure_dirs()
    instances.ensure_default_instance()
    settings = minecraft.load_settings()
    api = API()

    if settings.get("discord_rpc", True):
        threading.Thread(target=lambda: [discord_rpc.init_rpc(), discord_rpc.update_menu()], daemon=True).start()

    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")

    if not settings.get("hw_accel", True):
        if paths.is_windows():
            # WebView2 acepta argumentos de Chromium por esta variable: es el
            # equivalente en Windows de lo que abajo se hace por WebKitGTK.
            os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
                "--disable-gpu --disable-gpu-compositing"
            )
        else:
            os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

    _set_default_icon()

    window = webview.create_window(
        title="Stella Client",
        url=html_path,
        js_api=api,
        # En Windows la ventana nace oculta y se coloca en `_place_window` con la
        # geometría de la última sesión: crearla ya maximizada y sin marco es
        # justo lo que la dejaba grande y descolocada. En Linux no se cambia nada.
        width=1200 if paths.is_windows() else 1000,
        height=750 if paths.is_windows() else 600,
        min_size=(800, 450),
        resizable=True,
        fullscreen=False,
        maximized=not paths.is_windows(),
        frameless=True,
        easy_drag=False,
        hidden=paths.is_windows(),
        background_color="#0a0a0a",
    )

    api._window = window

    if window and window.events:
        window.events.closing += discord_rpc.close_rpc
        if paths.is_windows():
            # Este evento se ejecuta en el sitio, así que la ventana todavía está
            # ahí y se puede medir su geometría.
            window.events.closing += lambda: _remember_window(window)

    def _after_start():
        set_window_icon(window)
        if paths.is_windows():
            _place_window(window, settings)

    try:
        webview.start(debug=False, func=_after_start)
    except Exception as error:
        _report_start_failure(error)
        raise SystemExit(1)


# --- Comprobación del entorno (--check) ---------------------------------

_DISPLAY_VARS = ("DISPLAY", "WAYLAND_DISPLAY")

# Librerías gráficas cuyo origen conviene poder citar al verificar un paquete.
_CHECK_LIBS = ("libgtk-3", "libwebkit2gtk", "libglib-2.0", "libgirepository-")

# Con qué se identifica el runtime de WebView2 en el registro de Windows. Hay
# dos rutas porque una instalación de 64 bits aparece en la vista de 32 bits.
_WEBVIEW2_CLIENT = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
_WEBVIEW2_REG_KEYS = (
    r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients",
    r"SOFTWARE\Microsoft\EdgeUpdate\Clients",
)


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

    Existe para poder verificar los paquetes sin pantalla: carga la pila gráfica
    de verdad, informa de dónde sale cada pieza —el diseño del paquete es que la
    ponga el sistema, así que verla dentro del bundle sería un aviso— y, si hay
    sesión gráfica, llega a crear y cerrar la ventana.

    La pila es distinta en cada sistema —GTK y WebKitGTK en Linux, el motor de
    Edge sobre .NET en Windows—, así que cada uno tiene su comprobación.
    """
    print("stella-client — comprobación del entorno")
    print(f"  ejecutable : {sys.executable}")
    print(f"  python     : {sys.version.split()[0]}")
    print(f"  sistema    : {sys.platform}")
    print(f"  datos      : {paths.data_dir()}")
    bundle = getattr(sys, "_MEIPASS", "") or ""
    if bundle:
        print(f"  bundle     : {bundle}")

    if paths.is_windows():
        return _check_windows()
    return _check_gtk()


def _check_gtk():
    """Comprobación en Linux: typelibs de GTK y WebKitGTK del sistema."""
    bundle = getattr(sys, "_MEIPASS", "") or ""

    try:
        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gdk, GLib, Gtk, WebKit2

        # Por dónde salió la ventana de verdad, que es la mitad de la respuesta a
        # cualquier cosa rara que se vea: el nombre de la clase de la pantalla es
        # `X11Display` o `GdkWaylandDisplay`, y las dos rutas no se comportan
        # igual (Wayland no sabe pedir una ventana sin decoración).
        display_object = Gdk.Display.get_default()
        backend = (
            type(display_object).__name__.replace("Gdk", "").replace("Display", "").lower()
            if display_object
            else "?"
        )

        print(f"  PyGObject  : {gi.__version__}")
        print(f"  GLib       : {GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}")
        print(f"  GTK        : {Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}")
        print(
            "  WebKitGTK  : "
            f"{WebKit2.get_major_version()}.{WebKit2.get_minor_version()}.{WebKit2.get_micro_version()}"
        )
        print(f"  sesión     : {_session_description()} — GDK dibuja por {backend}")
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
    return _check_window()


def _session_description():
    """Cómo se llama esta sesión gráfica según el entorno."""
    kind = os.environ.get("XDG_SESSION_TYPE") or "sin declarar"
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return f"{kind} ({desktop})" if desktop else kind


def _x11_window_id(window):
    """Identificador X de la ventana, o None si no hay ninguna (o no es X11)."""
    native = getattr(window, "native", None)
    gdk_window = native.get_window() if native is not None else None
    identifier = getattr(gdk_window, "get_xid", None)
    if gdk_window is None or not callable(identifier):
        return None
    try:
        return identifier()
    except Exception:
        return None


def _x11_property(identifier, name):
    """Una propiedad de la ventana, leída con `xprop`.

    Se usa `xprop` porque GDK no expone ninguna de las dos en GTK 3 —`GdkX11`
    tiene el escritor del `WM_CLASS` y no el lector, y su `get_frame_extents`
    devuelve el rectángulo entero de la ventana, no lo que se le añade—, y
    `xprop` está en cualquier escritorio X11. Si no está, simplemente no se
    informa.
    """
    try:
        result = subprocess.run(
            ["xprop", "-id", hex(identifier), name],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or "=" not in result.stdout or "not found" in result.stdout:
        return None
    return result.stdout.split("=", 1)[1].strip()


def _report_window_frame(window):
    """Cuenta si el gestor de ventanas le puso marco, que es lo que decide si se ven dos barras.

    La medida la publica el propio servidor X en `_NET_FRAME_EXTENTS`: si el
    gestor no añade nada la propiedad no está, y la única barra es la del
    launcher. Con decoración de verdad su valor es `4, 4, 30, 4`, que es el
    control que confirma que la propiedad está diciendo algo y no que falte por
    otro motivo.

    El `WM_CLASS` es lo que asocia la ventana con su lanzador en el dock y en el
    menú de ventanas: tiene que ser el mismo que el `StartupWMClass` del
    `.desktop`.
    """
    identifier = _x11_window_id(window)
    if identifier is None:
        return
    extents = _x11_property(identifier, "_NET_FRAME_EXTENTS")
    # Cada gestor lo publica a su manera: KWin no pone la propiedad cuando no hay
    # decoración y openbox la pone a ceros, así que las dos cosas se leen igual.
    values = [int(value) for value in re.findall(r"-?\d+", extents or "")]
    if not any(values):
        print("  marco      : sin decoración del gestor de ventanas (una sola barra)")
    else:
        print(f"  marco      : {extents} ← el gestor añade decoración, se verán dos barras")
    class_name = _x11_property(identifier, "WM_CLASS")
    if class_name:
        print(f"  WM_CLASS   : {class_name}")


def _check_windows():
    """Comprobación en Windows: motor de Edge (WebView2) y el puente con .NET."""
    problems = []

    webview2 = _webview2_version()
    print(f"  WebView2   : {webview2 or 'NO ENCONTRADO'}")
    if not webview2:
        problems.append(
            "falta el runtime de WebView2; llega con Microsoft Edge o con su instalador propio"
        )

    try:
        import clr  # noqa: F401  (el puente con .NET que pywebview usa aquí)

        print("  pythonnet  : disponible")
    except Exception as e:
        problems.append(f"pythonnet no carga: {e}")

    try:
        from launcher import winwindow

        print(f"  pantalla   : área de trabajo {winwindow.primary_work_area()}")
        remembered = minecraft.load_settings().get("window")
        usable = winwindow.remembered_box(remembered)
        print(f"  ventana    : {remembered if remembered else 'sin geometría guardada'}")
        print(
            "  colocación : "
            + (f"se abrirá en {usable}" if usable else "se abrirá centrada (sin geometría utilizable)")
        )
    except Exception as e:
        problems.append(f"no se pudo leer la geometría de la ventana: {e}")

    if problems:
        for problem in problems:
            print(f"  FALLO      : {problem}")
        print("RESULTADO: este sistema no tiene lo necesario para arrancar")
        return 1

    if not os.environ.get("SESSIONNAME"):
        # Sin sesión interactiva no hay escritorio donde abrir una ventana: es lo
        # que pasa en un servidor de integración continua. Ahí crear la ventana
        # no puede ser condición para publicar el paquete.
        print("  pantalla   : sesión no interactiva; no se crea la ventana")
        print("RESULTADO: la pila gráfica carga correctamente")
        return 0

    return _check_window()


def _webview2_version():
    """Versión del runtime de WebView2 según el registro, o None si no está.

    pywebview dibuja con el motor de Edge en Windows, así que sin este runtime la
    ventana no se crea. Comprobarlo aquí da un mensaje claro en vez del volcado de
    error que suelta el puente con .NET cuando no lo encuentra.
    """
    try:
        import winreg
    except ImportError:
        return None
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key in _WEBVIEW2_REG_KEYS:
            try:
                with winreg.OpenKey(root, key + "\\" + _WEBVIEW2_CLIENT) as handle:
                    return winreg.QueryValueEx(handle, "pv")[0]
            except OSError:
                continue
    return None


def _check_window():
    """Crea y cierra una ventana de verdad. Devuelve el código de salida."""
    # Si la web se cuelga, el vigilante lo convierte en un código de salida claro
    # en vez de dejar el proceso vivo para siempre.
    watchdog = threading.Timer(60, os._exit, [124])
    watchdog.daemon = True
    watchdog.start()
    try:
        # La ventana se enseña, no se crea oculta: sin llegar a mostrarse el
        # gestor de ventanas no la ve, y entonces no hay `_NET_FRAME_EXTENTS` que
        # leer ni `WM_CLASS` que comprobar. Dura segundo y medio, y es lo que
        # convierte esta comprobación en una medida de la ventana de verdad.
        # `frameless` igual que la ventana real, para que la medida sea la suya.
        window = webview.create_window(
            "Stella Client (check)",
            html="<html><body>ok</body></html>",
            frameless=True,
        )

        def _close_after_start():
            # Se espera a que la ventana esté de verdad en pantalla antes de
            # medir: recién creada todavía no tiene ventana de GDK, y sin ella no
            # hay nada que preguntarle al gestor.
            time.sleep(1.5)
            _report_window_frame(window)
            window.destroy()

        webview.start(debug=False, func=_close_after_start)
    except Exception as e:
        print(f"  FALLO al crear la ventana: {e}")
        print("RESULTADO: la pila gráfica carga pero la ventana no se pudo abrir")
        return 1
    finally:
        watchdog.cancel()

    print("RESULTADO: la ventana se creó y se cerró correctamente")
    return 0


if __name__ == "__main__":
    # El paquete de Windows trae un segundo ejecutable con consola para esto, y se
    # reconoce por su nombre: así se puede hacer doble clic sin pasar argumentos.
    if "--check" in sys.argv[1:] or os.path.basename(sys.executable).startswith("stella-client-check"):
        sys.exit(check_environment())
    start_ui()
