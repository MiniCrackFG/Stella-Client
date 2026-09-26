import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import time

import launcher.instances as instances
import launcher.minecraft as minecraft
import launcher.mods as mods
import launcher.discord_rpc as discord_rpc
from launcher import paths

logger = logging.getLogger(__name__)

# Algunas redes (y algún CDN por delante) rechazan el agente con el que `requests`
# se presenta por defecto: se manda el de un navegador, que es lo que esperan.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _open_url(url):
    """Abre una URL en el navegador del sistema."""
    try:
        if paths.is_windows():
            os.startfile(url)  # sólo existe en Windows
        else:
            subprocess.Popen(['xdg-open', url])
    except Exception:
        import webbrowser
        webbrowser.open(url)


def _ensure_glib():
    """GLib de GTK, o None si esta plataforma no lo usa.

    En Windows la ventana la dibuja WebView2 y no hay GTK que buscar: se sale
    antes de intentarlo, para no ensuciar `sys.path` con rutas que allí no
    existen.
    """
    if paths.is_windows():
        return None
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib
        return GLib
    except ImportError:
        for p in [
            "/usr/lib/python3.12/site-packages",
            "/usr/lib/python3.11/site-packages",
            "/usr/lib/python3.10/site-packages",
            "/usr/lib/python3/dist-packages",
        ]:
            if p not in sys.path:
                sys.path.insert(0, p)
            try:
                import gi
                gi.require_version("Gtk", "3.0")
                from gi.repository import GLib
                return GLib
            except (ImportError, ValueError):
                continue
    return None

# Los tiradores de redimensión que pinta la interfaz, traducidos a lo que entiende
# GDK. Los nombres son los de `ui/app.js`: los cuatro bordes y las cuatro esquinas.
_WINDOW_EDGES = {
    "n": "NORTH",
    "s": "SOUTH",
    "e": "EAST",
    "w": "WEST",
    "ne": "NORTH_EAST",
    "nw": "NORTH_WEST",
    "se": "SOUTH_EAST",
    "sw": "SOUTH_WEST",
}


def _gdk_button(button):
    """Del número de botón del navegador al de GDK.

    La página los cuenta desde cero —0 izquierdo, 1 central, 2 derecho— y X11
    desde uno —1 izquierdo, 2 central, 3 derecho—. Pasar el 0 tal cual deja al
    gestor de ventanas con un botón que no existe: no empieza el gesto y se queda
    esperando la suelta de ese botón, de forma que el gesto a medias se come el
    siguiente. El arrastre de la barra se libraba por casualidad; la redimensión
    no arrancaba nunca.
    """
    try:
        return int(button) + 1
    except (TypeError, ValueError):
        return 1


def _gtk_query(glib, function, default=None):
    """Le pregunta algo a GTK desde el hilo de la página y espera la respuesta.

    Las llamadas de la página —los métodos que expone `js_api`— pueden llegar en
    otro hilo, y GTK no se puede tocar desde ahí: su estado interno se corrompe
    (se ha visto terminar en un `corrupted double-linked list` de la libc, sin
    más rastro que ese). Se encola en el bucle principal, que es donde GTK espera
    que se le hable, y se espera aquí: son microsegundos, y sólo se usa para
    preguntar o para una orden corta, nunca para llevar un gesto.
    """
    if glib.MainContext.default().is_owner():
        try:
            return function()
        except Exception:
            return default

    result = {}
    done = threading.Event()

    def _run():
        try:
            result["value"] = function()
        except Exception as error:
            result["error"] = error
        finally:
            done.set()
        return False  # no repetir

    glib.idle_add(_run)
    done.wait(2)
    return result.get("value", default)


# El gestor de ventanas escucha `_NET_WM_MOVERESIZE` en la ventana raíz, así que el
# mensaje se manda ahí, con las dos máscaras del árbol de ventanas.
_SUBSTRUCTURE_NOTIFY = 1 << 19
_SUBSTRUCTURE_REDIRECT = 1 << 20
_CLIENT_MESSAGE = 33
_MOVERESIZE_MOVE = 8


class _XClientMessage(ctypes.Structure):
    """La parte de `XEvent` que usa el mensaje que entiende el gestor de ventanas."""

    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int),
        ("data", ctypes.c_long * 5),
    ]


_x11 = None  # (libX11, conexión): se abre una vez, la primera que hace falta


def _x11_connection():
    """Conexión propia con el servidor X para hablar con el gestor de ventanas.

    Va aparte de la de GDK a propósito: PyGObject no expone el puntero al `Display`
    de GDK, y abrir otra conexión no cuesta nada (se abre una sola vez).
    """
    global _x11
    if _x11 is None:
        library = ctypes.CDLL("libX11.so.6")
        library.XOpenDisplay.restype = ctypes.c_void_p
        library.XOpenDisplay.argtypes = [ctypes.c_char_p]
        display = library.XOpenDisplay(None)
        if not display:
            logger.info("sin conexión con el servidor X para pedirle cosas al gestor")
            return None
        library.XDefaultRootWindow.restype = ctypes.c_ulong
        library.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        library.XInternAtom.restype = ctypes.c_ulong
        library.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        library.XSendEvent.restype = ctypes.c_int
        library.XSendEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long,
            ctypes.POINTER(_XClientMessage),
        ]
        library.XFlush.argtypes = [ctypes.c_void_p]
        _x11 = (library, display)
    return _x11


def _request_wm_move(native, button, root_x, root_y, timestamp):
    """Le pide al gestor de ventanas que empiece a mover la ventana. En X11.

    No se usa `begin_move_drag` de GTK: necesita un «evento actual» para saber con
    qué dispositivo arrastra, y esta orden llega del puente —ya fuera del manejador
    del ratón—, así que se queda en nada sin decir nada. Medido con una ventana de
    control: la misma llamada desde un manejador de pulsación mueve la ventana y
    desde el bucle principal no la mueve ni un píxel, sin error ni aviso ninguno.

    Lo que hace GTK por dentro es mandarle `_NET_WM_MOVERESIZE` al gestor de
    ventanas; aquí se manda eso mismo, que no depende de ningún evento actual.
    Devuelve False cuando no se puede (Wayland, sin libX11, sin servidor X) y quien
    llama se queda con el camino de GTK.
    """
    try:
        gdk_window = native.get_window()
        identifier = gdk_window.get_xid() if gdk_window is not None else None
        if not identifier:
            return False
        connection = _x11_connection()
    except Exception as error:
        logger.info(f"petición de mover sin X11: {error}")
        return False
    if connection is None:
        return False

    library, display = connection
    try:
        message = _XClientMessage()
        message.type = _CLIENT_MESSAGE
        message.display = display
        message.window = int(identifier)
        message.message_type = library.XInternAtom(display, b"_NET_WM_MOVERESIZE", False)
        message.format = 32
        message.data[0] = int(root_x)
        message.data[1] = int(root_y)
        message.data[2] = _MOVERESIZE_MOVE
        message.data[3] = int(button)
        message.data[4] = int(timestamp)
        sent = library.XSendEvent(
            display,
            library.XDefaultRootWindow(display),
            False,
            _SUBSTRUCTURE_NOTIFY | _SUBSTRUCTURE_REDIRECT,
            ctypes.byref(message),
        )
        library.XFlush(display)
        return bool(sent)
    except Exception as error:
        logger.info(f"la petición de mover falló: {error}")
        return False


def _x11_event_time(native, fallback):
    """Marca de tiempo del servidor X para las peticiones al gestor de ventanas.

    Arrastrar y redimensionar una ventana sin bordes no se hace desde Python: se
    le pide al gestor de ventanas (`_NET_WM_MOVERESIZE`) y él se queda con el
    gesto, que es lo que evita que la ventana vaya a tirones por el puente. Esa
    petición lleva una marca de tiempo del servidor X, y los gestores la comparan
    con la última interacción del usuario para no dejar que una ventana se
    coloque encima por sorpresa.

    La que manda el navegador es un contador de milisegundos desde que se cargó
    la página, no una marca del servidor, así que se pide una de verdad —una ida
    y vuelta con el servidor, una sola vez por gesto— y sólo si eso no está
    disponible (Wayland, o un servidor que no contesta) se usa la del navegador.
    """
    try:
        import gi

        gi.require_version("GdkX11", "3.0")
        from gi.repository import GdkX11

        gdk_window = native.get_window()
        if gdk_window is None:
            return int(fallback)
        return int(GdkX11.x11_get_server_time(gdk_window)) or int(fallback)
    except Exception:
        return int(fallback)


def _copy_to_clipboard_gtk(text):
    """Portapapeles en Linux: GTK, encolando en el hilo principal si hace falta."""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, GLib, Gtk
    except Exception as e:
        logger.info(f"copy_to_clipboard sin GTK disponible: {e}")
        return False

    def _do_copy():
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        # Sin store() el contenido se pierde al cerrar la app.
        clipboard.store()

    try:
        # En el hilo principal GTK es seguro y podemos devolver el resultado
        # real. Si pywebview llama desde otro hilo, se encola en el principal.
        if GLib.MainContext.default().is_owner():
            _do_copy()
            return True

        def _idle_copy():
            try:
                _do_copy()
            except Exception as e:
                logger.info(f"copy_to_clipboard falló: {e}")
            return False  # no repetir

        GLib.idle_add(_idle_copy)
        return True
    except Exception as e:
        logger.info(f"copy_to_clipboard falló: {e}")
        return False


def _copy_to_clipboard_windows(text):
    """Portapapeles en Windows: `clip.exe` con el texto en UTF-16LE.

    `clip` viene con el propio sistema, y dándoselo en UTF-16LE no se rompen los
    acentos ni los emoji —que es justo lo que pasa si se le pasa la codificación
    de la consola—. El único detalle es `CREATE_NO_WINDOW`: sin él, el intérprete
    de consola de `clip` asomaría una ventana negra un instante de nada.
    """
    try:
        completed = subprocess.run(
            ["clip"],
            input=text.encode("utf-16-le"),
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode == 0:
            return True
        logger.info(f"clip devolvió el código {completed.returncode}")
        return False
    except Exception as e:
        logger.info(f"copy_to_clipboard en Windows falló: {e}")
        return False


_cache = {}
_CACHE_TTL = 60


def _cached(key, ttl, func, *args, **kwargs):
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry["time"] < ttl:
        return entry["data"]
    data = func(*args, **kwargs)
    # Un fallo no se cachea: si la red estaba caída, el usuario no debe quedarse
    # viendo "sin resultados" durante todo el TTL.
    if not (isinstance(data, dict) and data.get("error")):
        _cache[key] = {"data": data, "time": now}
    return data


class API:
    _window = None

    def get_settings(self):
        s = minecraft.load_settings()
        inst = self.get_current_instance()
        if inst:
            if inst.get("version"):
                s["version"] = inst["version"]
            if inst.get("ram"):
                s["ram"] = inst["ram"]
            if inst.get("java_path"):
                s["java_path"] = inst["java_path"]
            if inst.get("minecraft_dir"):
                s["minecraft_dir"] = inst["minecraft_dir"]
        return s

    def save_settings(self, data):
        if isinstance(data, str):
            updates = json.loads(data)
        else:
            updates = data
        # Normalizamos las rutas que llegan de la UI ('~/.stellaclient', rutas relativas...)
        if isinstance(updates.get("minecraft_dir"), str) and updates["minecraft_dir"].strip():
            updates["minecraft_dir"] = minecraft.expand_path(updates["minecraft_dir"])
        if isinstance(updates.get("java_path"), str):
            java_path = updates["java_path"].strip()
            updates["java_path"] = os.path.expanduser(java_path) if java_path.startswith("~") else java_path
        current = minecraft.load_settings()
        current.update(updates)
        minecraft.save_settings(current)
        inst = self.get_current_instance()
        if inst:
            instance_keys = ("version", "ram", "java_path", "minecraft_dir")
            updated = instances.update_instance(inst["id"], {k: updates[k] for k in instance_keys if k in updates})
            if updated and updated.get("mods_dir"):
                os.environ["STELLA_MODS_DIR"] = updated["mods_dir"]
        return {"ok": True}

    def get_auth(self):
        """Nunca exponer tokens al frontend: solo lo que la UI necesita mostrar."""
        auth = minecraft.load_auth()
        if not auth:
            return None
        return {"username": auth.get("username"), "uuid": auth.get("uuid")}

    def get_current_user(self):
        return minecraft.get_current_user()

    def get_offline_username(self):
        return minecraft.get_offline_username()

    def has_offline_account(self):
        return minecraft.has_offline_account()

    def logout(self):
        minecraft.logout()

    def login_offline(self, username):
        minecraft.login_offline(username)
        return {"ok": True}

    def start_microsoft_login(self):
        try:
            di = minecraft.get_device_code_info()
            _open_url(di.get("verification_uri", ""))
            return di
        except Exception as e:
            return {"error": str(e)}

    def poll_microsoft_login(self, device_code):
        import requests
        td = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb",
            "device_code": device_code,
        }
        try:
            resp = requests.post(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data=td, timeout=10,
            )
            if resp.status_code == 200:
                return self._finish_microsoft_auth(resp.json())
            elif resp.status_code != 400:
                return {"error": f"HTTP {resp.status_code}"}
            err = resp.json().get("error", "")
            if err == "authorization_pending":
                return {"status": "pending"}
            elif err in ("authorization_declined", "expired_token"):
                return {"error": err}
            elif err == "slow_down":
                return {"status": "pending", "slow_down": True}
            return {"error": err}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection failed"}
        except Exception as e:
            return {"error": str(e)}

    def _finish_microsoft_auth(self, tokens):
        # La lógica vive en launcher.minecraft: aquí solo se adapta la respuesta
        result = minecraft.finish_microsoft_auth(tokens)
        if result.get("error"):
            return result
        return {"status": "success", "username": result["username"]}

    def get_versions(self):
        return minecraft.get_available_versions()

    def list_instances(self):
        return instances.list_instances()

    def get_instance(self, instance_id):
        return instances.get_instance(instance_id)

    def create_instance(self, name, version="1.21.1", icon="📦"):
        return instances.create_instance(name, version, icon)

    def delete_instance(self, instance_id):
        ok = instances.delete_instance(instance_id)
        return {"ok": ok}

    def set_current_instance(self, instance_id):
        s = minecraft.load_settings()
        s["current_instance"] = instance_id
        minecraft.save_settings(s)
        inst = instances.get_instance(instance_id)
        if inst and inst.get("mods_dir"):
            os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
        _cache.clear()
        return {"ok": True}

    def get_current_instance(self):
        s = minecraft.load_settings()
        iid = s.get("current_instance")
        if iid:
            inst = instances.get_instance(iid)
            if inst and inst.get("mods_dir"):
                os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
            return inst
        return None

    def detect_java(self):
        """Java que hay en el sistema, para poder elegirlo en Ajustes."""
        javas = []
        seen = set()

        def add_java(path):
            if not os.path.exists(path) or path in seen:
                return
            seen.add(path)
            try:
                ver = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
                version_str = ver.stderr.strip()
                version_str = version_str.split('"')[1] if '"' in version_str else version_str[:50]
                javas.append({"path": path, "version": version_str})
            except Exception:
                pass

        for candidate in self._java_candidates():
            add_java(candidate)
        return javas

    def _java_candidates(self):
        """Rutas donde puede haber un Java, en orden de preferencia.

        Cada sistema los pone en un sitio: en Linux van los paquetes a
        `/usr/lib/jvm` y en Windows a `Program Files`, con instalaciones que
        meten además una carpeta por versión. `add_java` ya descarta lo que no
        exista, así que aquí se puede ser generoso listando.
        """
        import glob

        if paths.is_windows():
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            roots = [
                os.environ.get("JAVA_HOME"),
                os.path.join(program_files, "Java"),
                os.path.join(program_files, "Eclipse Adoptium"),
                os.path.join(program_files, "Microsoft"),
                os.path.join(program_files, "Zulu"),
                os.path.join(program_files, "BellSoft"),
                os.path.join(program_files, "Amazon Corretto"),
                os.path.join(program_files_x86, "Java"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            ]
            candidates = []
            for root in roots:
                if not root:
                    continue
                candidates.append(os.path.join(root, "bin", "java.exe"))
                for sub in sorted(glob.glob(os.path.join(root, "*")), reverse=True):
                    candidates.append(os.path.join(sub, "bin", "java.exe"))
            return candidates

        candidates = []
        for cmd in ["java", "java21", "java17"]:
            try:
                r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    candidates.append(r.stdout.strip())
            except Exception:
                pass
        for jdir in sorted(glob.glob("/usr/lib/jvm/*"), reverse=True):
            candidates.append(os.path.join(jdir, "bin/java"))
            candidates.append(os.path.join(jdir, "jre/bin/java"))
        return candidates

    def get_avatar(self, uuid=None):
        """La cabeza de la skin como imagen lista para pintar, o "" si no se pudo.

        La vista de la cuenta ya no depende de esto —carga la imagen desde la
        propia página, que es el camino que el motor de la ventana tiene
        probado—: queda como segundo intento, así que lo que importa aquí es que
        el motivo de un fallo quede en el registro en vez de perderse.
        """
        import requests
        import base64
        ident = uuid or "steve"
        url = f"https://mc-heads.net/avatar/{ident}/128"
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": _BROWSER_UA})
            if resp.status_code != 200:
                logger.info(f"get_avatar: {url} respondió {resp.status_code}")
                return ""
            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                logger.info(f"get_avatar: {url} respondió con tipo {content_type or 'desconocido'}")
                return ""
            b64 = base64.b64encode(resp.content).decode()
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            logger.info(f"get_avatar: {url} falló: {e}")
            return ""

    def get_platform(self):
        """Sistema en el que corre el launcher.

        La interfaz tiene detalles que sólo valen en uno —la barra de scroll la
        pinta Chromium en Windows y el tema del escritorio en Linux—, y esto lo
        responde la misma función que decide todo lo demás en vez del
        `navigator.userAgent`.
        """
        return "windows" if paths.is_windows() else "linux"

    def open_url(self, url):
        _open_url(url)
        return {"ok": True}

    def get_server_info(self, address):
        import requests
        try:
            resp = requests.get(f"https://api.mcsrvstat.us/2/{address}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"error": "Could not fetch server info"}

    def get_versions_grouped(self):
        raw = minecraft.get_available_versions()
        groups = {}
        for v in raw:
            parts = v.split(".")
            major = f"{parts[0]}.{parts[1]}"
            groups.setdefault(major, []).append(v)
        result = []
        for major in sorted(groups.keys(), key=lambda x: [int(n) for n in x.split(".")], reverse=True):
            result.append({"major": major, "versions": groups[major]})
        return result

    _launch_status = {"state": "stopped"}
    _progress_lock = threading.Lock()

    # Los textos de progreso de minecraft_launcher_lib vienen en inglés y son
    # tecnicos: aquí se traducen a algo que se pueda enseñar en la barra.
    _PHASE_LABELS = {
        "Download Libraries": "Descargando librerías",
        "Download Assets": "Descargando recursos",
        "Install java runtime": "Instalando Java",
        "Installation complete": "Instalación completa",
        "Running fabric installer": "Instalando Fabric",
    }

    def _publish(self, **fields):
        """Actualiza el estado del lanzamiento desde cualquier hilo.

        Los callbacks de minecraft_launcher_lib llegan desde su ThreadPoolExecutor,
        así que el dict se reemplaza entero bajo lock (nunca se muta en sitio).
        """
        with self._progress_lock:
            if self._launch_status.get("state") != "launching":
                return
            status = dict(self._launch_status)
            status.update(fields)
            self._launch_status = status

    def _progress_callback(self):
        """CallbackDict compatible con lo que espera minecraft_launcher_lib."""
        # Marcas del callback: si la fase actual tiene nombre ("Descargando
        # librerías"), un status por archivo no debe pisarla.
        flags = {"named_phase": False}

        def set_status(text):
            text = str(text)
            label = self._PHASE_LABELS.get(text)
            if label is None and text.startswith("Download "):
                # download_file() pone el nombre del archivo en cada descarga: en la
                # barra interesa la fase, no un nombre que cambia decenas de veces
                # por segundo. Solo se usa si no hay una fase mejor que enseñar.
                if flags["named_phase"]:
                    return
                flags["named_phase"] = False
                return self._publish(phase="Descargando archivos")
            flags["named_phase"] = True
            # Fase nueva sin contador propio todavía (instalador de Fabric, Java,
            # compilar el mod...): la barra pasa a barrido indeterminado en lugar de
            # quedarse con el porcentaje de la fase anterior. Las fases que sí
            # cuentan mandan su setMax justo después de este setStatus.
            self._publish(phase=label or text, progress=0, max=0)

        def set_max(value):
            try:
                maximum = max(0, int(value))
            except (TypeError, ValueError):
                return
            # Cada fase reinicia la cuenta (la librería llama setMax al empezar);
            # sobre la marcha, un máximo nuevo empieza en 0 en lugar de heredar
            # el porcentaje de la fase anterior.
            self._publish(max=maximum, progress=0)

        def set_progress(value):
            try:
                progress = max(0, int(value))
            except (TypeError, ValueError):
                return
            self._publish(progress=progress)

        return {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}

    def launch(self):
        if self._launch_status.get("state") in ("launching", "playing"):
            return {"ok": False, "error": "Minecraft ya se está ejecutando"}

        try:
            plan = minecraft.launch_plan()
        except Exception as e:
            logger.warning(f"launch_plan failed: {e}")
            plan = {}
        self._launch_status = {
            "state": "launching",
            "needs_download": bool(plan.get("needs_download")),
            "phase": "Preparando el arranque",
            "progress": 0,
            "max": 0,
        }
        callback = self._progress_callback()

        def run():
            settings = {}
            try:
                settings = minecraft.load_settings()
                instance = self.get_current_instance()
                if instance:
                    settings["version"] = instance.get("version", settings.get("version", "1.21.11"))
                    settings["ram"] = instance.get("ram", settings.get("ram", 4))
                    settings["java_path"] = instance.get("java_path", settings.get("java_path", "java"))
                    settings["minecraft_dir"] = instance.get("minecraft_dir", settings.get("minecraft_dir", paths.data_dir()))
                    minecraft.save_settings(settings)
                    inst_mods = instance.get("mods_dir")
                    if inst_mods:
                        os.environ["STELLA_MODS_DIR"] = inst_mods
                self._publish(phase="Preparando el mod Stella")
                mods.install_stella_mod()
                process = minecraft.launch_minecraft(callback=callback)
                self._launch_status = {"state": "playing", "pid": process.pid}
                if settings.get("discord_rpc", True):
                    discord_rpc.update_playing()
                process.wait()
            except Exception as e:
                logger.exception("Launch failed")
                self._launch_status = {"state": "error", "message": str(e)}
                return
            if settings.get("discord_rpc", True):
                discord_rpc.update_menu()
            self._launch_status = {"state": "stopped"}

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True}

    def get_launch_status(self):
        return dict(self._launch_status)

    def get_trending_mods(self, project_type="mod", offset=0, sort="downloads"):
        try:
            instance = self.get_current_instance()
            version = (instance or {}).get("version") or minecraft.load_settings().get("version", "1.21.1")
            key = f"trending_{project_type}_{version}_{offset}_{sort}"
            def _fetch():
                data = mods.get_trending_mods(version=version, limit=15, project_type=project_type, offset=offset, sort=sort)
                result = {"mods": data["results"], "total_hits": data["total_hits"]}
                if data.get("error"):
                    result["error"] = data["error"]
                return result
            return _cached(key, _CACHE_TTL, _fetch)
        except Exception as e:
            return {"error": str(e), "mods": [], "total_hits": 0}

    def search_mods(self, query, version, source="modrinth", project_type="mod", offset=0, sort="downloads"):
        try:
            if source != "modrinth":
                return {"error": "Forge no está soportado todavía", "mods": [], "total_hits": 0}
            key = f"search_{project_type}_{version}_{query}_{offset}_{sort}"
            def _fetch():
                data = mods.search_modrinth(query, version=version, project_type=project_type, offset=offset, sort=sort)
                result = {"mods": data["results"], "total_hits": data["total_hits"]}
                if data.get("error"):
                    result["error"] = data["error"]
                return result
            return _cached(key, _CACHE_TTL, _fetch)
        except Exception as e:
            return {"error": str(e), "mods": [], "total_hits": 0}

    def get_mod_detail(self, mod_id):
        try:
            key = f"detail_{mod_id}"
            def _fetch():
                import requests
                resp = requests.get(f"https://api.modrinth.com/v2/project/{mod_id}", timeout=10)
                if resp.status_code == 200:
                    d = resp.json()
                    license_raw = d.get("license")
                    if isinstance(license_raw, dict):
                        license_name = license_raw.get("name") or license_raw.get("id") or ""
                    else:
                        license_name = license_raw or ""
                    return {
                        "mod_id": mod_id,
                        "slug": d.get("slug", ""),
                        "name": d.get("title", ""),
                        "description": d.get("description", ""),
                        "body": d.get("body", ""),
                        "thumbnail": d.get("icon_url", ""),
                        "downloads": d.get("downloads", 0),
                        "followers": d.get("followers", 0),
                        "categories": d.get("categories", []),
                        "additional_categories": d.get("additional_categories", []),
                        "client_side": d.get("client_side", ""),
                        "server_side": d.get("server_side", ""),
                        "license": license_name,
                        "game_versions": d.get("game_versions", []),
                        "loaders": d.get("loaders", []),
                        "published": d.get("published", ""),
                        "updated": d.get("updated", ""),
                        "discord_url": d.get("discord_url", ""),
                        "issues_url": d.get("issues_url", ""),
                        "source_url": d.get("source_url", ""),
                        "wiki_url": d.get("wiki_url", ""),
                        "gallery": [{"url": g.get("url", ""), "title": g.get("title", ""), "description": g.get("description", "")} for g in d.get("gallery", [])],
                        "donation_urls": [{"platform": du.get("platform", ""), "url": du.get("url", "")} for du in d.get("donation_urls", [])],
                    }
                return {"error": f"HTTP {resp.status_code}"}
            return _cached(key, _CACHE_TTL * 5, _fetch)
        except Exception as e:
            return {"error": str(e)}

    def _clear_browse_cache(self):
        for k in list(_cache):
            if k.startswith("trending_") or k.startswith("search_") or k.startswith("installed_"):
                del _cache[k]

    def download_mod(self, mod_id, mc_version, source="modrinth", project_type="mod", thumbnail="", prefer_loader="fabric"):
        self._ensure_mods_env()
        if source != "modrinth":
            return {"ok": False, "error": "Forge no está soportado todavía"}
        result = mods.download_mod(mod_id, mc_version, source=source, project_type=project_type, thumbnail=thumbnail, prefer_loader=prefer_loader)
        if result.get("ok"):
            self._clear_browse_cache()
        return result

    def minimize(self):
        if hasattr(self, '_window'):
            self._window.minimize()
        return {"ok": True}

    _maximized = True  # sólo se usa donde no se le puede preguntar al sistema

    def toggle_maximize(self):
        """El botón □ alterna maximizado/restaurado: pywebview no lo hace solo.

        En Windows el estado lo sabe el propio sistema, así que se le pregunta en
        vez de llevarlo por nuestra cuenta: adivinarlo era lo que dejaba el botón
        desincronizado en cuanto la ventana se maximizaba de otra forma.
        """
        if not hasattr(self, '_window') or not self._window:
            return {"ok": False}
        try:
            if paths.is_windows():
                from launcher import winwindow

                if winwindow.is_maximized(self._window):
                    self._window.restore()
                    return {"ok": True, "maximized": False}
                # Maximizar a la ventana, no por `window.maximize()`: ver
                # `launcher/winwindow.py`, que es quien deja la barra de tareas
                # a la vista.
                winwindow.maximize(self._window)
                return {"ok": True, "maximized": True}

            glib = _ensure_glib()
            native = getattr(self._window, "native", None)
            if native is not None and hasattr(native, "is_maximized") and glib:
                self._maximized = bool(_gtk_query(glib, native.is_maximized, False))

            if self._maximized:
                self._restore_gtk(glib, native)
            else:
                self._maximize_gtk(glib, native)
            self._maximized = not self._maximized
            return {"ok": True, "maximized": self._maximized}
        except Exception as e:
            logger.info(f"toggle_maximize failed: {e}")
            return {"ok": False, "error": str(e)}

    def copy_to_clipboard(self, text):
        """Copia texto al portapapeles del sistema.

        El navegador no siempre puede hacerlo por su cuenta —WebKitGTK necesita
        unos permisos que pywebview no pide—, así que el camino fiable es la vía
        nativa de cada sistema. En `ui/app.js` queda además el intento por
        `navigator.clipboard`, que es a lo que se recurre si esto devuelve False.
        """
        if not isinstance(text, str) or not text:
            return False
        if paths.is_windows():
            return _copy_to_clipboard_windows(text)
        return _copy_to_clipboard_gtk(text)

    def close_window(self):
        if hasattr(self, '_window'):
            self._window.destroy()
        return {"ok": True}

    def begin_window_move(self, button, root_x, root_y, timestamp):
        """Arrastra la ventana sin bordes desde la barra de título propia.

        Cada sistema tiene su forma de ceder el arrastre al gestor de ventanas, y
        en los dos casos se delega en él a propósito: mover la ventana desde
        Python obligaría a un viaje de ida y vuelta por cada movimiento del ratón
        —navegador, puente, Python, ventana— y el arrastre se ve a tirones.

        `button` llega tal cual desde el evento de la página, que cuenta los
        botones desde cero (ver `_gdk_button`).
        """
        if not hasattr(self, '_window') or not self._window:
            return {"ok": False}
        if paths.is_windows():
            return self._begin_window_move_windows()
        return self._begin_window_move_gtk(button, root_x, root_y, timestamp)

    def _begin_window_move_gtk(self, button, root_x, root_y, timestamp):
        glib = _ensure_glib()
        if not glib:
            return {"ok": False}
        try:
            native = self._window.native
            if not native:
                return {"ok": False}
        except Exception as e:
            logger.info(f"begin_window_move falló: {e}")
            return {"ok": False}

        # Igual que en la redimensión: todo dentro del hilo de GTK. La marca de
        # tiempo del servidor X también es una llamada a GDK, así que va aquí.
        def _move():
            marca = _x11_event_time(native, timestamp)
            # En X11 se le pide al gestor nosotros mismos: el `begin_move_drag` de
            # GTK no hace nada sin un evento actual (ver `_request_wm_move`).
            if _request_wm_move(native, _gdk_button(button), root_x, root_y, marca):
                return False
            native.begin_move_drag(
                _gdk_button(button),
                int(root_x),
                int(root_y),
                marca,
            )
            return False

        glib.idle_add(_move)
        return {"ok": True}

    def _begin_window_move_windows(self):
        """Entrega el arrastre al gestor de ventanas de Windows.

        `ReleaseCapture` más `WM_NCLBUTTONDOWN` sobre la barra de título es el
        equivalente de `begin_move_drag` en GTK: el sistema entra en su propio
        bucle de movimiento y no vuelve a cruzar nada por el puente hasta que se
        suelta el botón.

        Va con `PostMessage` y no con `SendMessage` a propósito: las llamadas de
        la página llegan en un hilo aparte, y con `SendMessage` el bucle nativo
        arrancaba dentro de esa llamada, entre hilos, y el movimiento salía a
        tirones. Encolado, lo recoge el hilo de la interfaz en su bomba de
        mensajes, exactamente igual que si lo hubiera iniciado el ratón.
        """
        try:
            import ctypes
            from ctypes import wintypes

            native = getattr(self._window, "native", None)
            if native is None:
                return {"ok": False}
            handle = native.Handle.ToInt64()
            if not handle:
                return {"ok": False}

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.ReleaseCapture.argtypes = []
            user32.ReleaseCapture.restype = wintypes.BOOL
            user32.PostMessageW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user32.PostMessageW.restype = wintypes.BOOL

            user32.ReleaseCapture()
            posted = user32.PostMessageW(
                wintypes.HWND(handle), 0x00A1, 2, 0
            )  # WM_NCLBUTTONDOWN, HTCAPTION
            return {"ok": bool(posted)}
        except Exception as e:
            logger.info(f"begin_window_move en Windows falló: {e}")
            return {"ok": False}

    def begin_window_resize(self, edge, button, root_x, root_y, timestamp):
        """Redimensiona la ventana desde los tiradores de la interfaz (Linux).

        La ventana no tiene marco —ni el suyo ni el del sistema—, así que sus
        bordes no se pueden agarrar: en X11 el gestor de ventanas no dibuja nada
        alrededor (medido: sin `_NET_FRAME_EXTENTS`), y eso es lo mismo que hace
        que la barra de título salga una sola vez. El precio es que
        redimensionar hay que pedirlo, y se le pide al gestor, que es quien sabe
        hacerlo sin tirones: la interfaz manda el borde o la esquina y el gestor
        lleva el gesto, igual que en el arrastre de la barra.

        `window_state()` publica si esto está disponible. Donde no lo está no se
        pintan tiradores, en vez de dejar zonas que no hacen nada.
        """
        if not hasattr(self, "_window") or not self._window:
            return {"ok": False}
        if paths.is_windows():
            return {"ok": False, "error": "no implementado en Windows"}
        return self._begin_window_resize_gtk(edge, button, root_x, root_y, timestamp)

    def _begin_window_resize_gtk(self, edge, button, root_x, root_y, timestamp):
        glib = _ensure_glib()
        if not glib:
            return {"ok": False}
        try:
            import gi

            gi.require_version("Gdk", "3.0")
            from gi.repository import Gdk

            direction = _WINDOW_EDGES.get(str(edge).lower())
            if direction is None:
                return {"ok": False, "error": f"borde desconocido: {edge}"}
            native = self._window.native
            if not native:
                return {"ok": False}
            gdk_edge = getattr(Gdk.WindowEdge, direction)
        except Exception as e:
            logger.info(f"begin_window_resize falló: {e}")
            return {"ok": False, "error": str(e)}

        # El gesto entero se prepara dentro del hilo de GTK: la marca de tiempo
        # del servidor X es una llamada a GDK y tampoco se puede hacer desde el
        # hilo de la página.
        def _resize():
            native.begin_resize_drag(
                gdk_edge,
                _gdk_button(button),
                int(root_x),
                int(root_y),
                _x11_event_time(native, timestamp),
            )
            return False

        glib.idle_add(_resize)
        return {"ok": True}

    def _maximize_gtk(self, glib, native):
        """Maximiza la ventana en Linux."""
        if native is not None and hasattr(native, "maximize") and glib:
            _gtk_query(glib, native.maximize)
        else:
            self._window.maximize()

    def _restore_gtk(self, glib, native):
        """Devuelve la ventana a su tamaño de antes de maximizar.

        No se usa `window.restore()` de pywebview: en GTK sólo hace `deiconify()`
        y `present()`, así que una ventana maximizada se queda maximizada y el
        botón □ no haría nada —lo que deja al launcher sin forma de volver a su
        tamaño normal, y sin ventana normal no hay nada que redimensionar—. La
        orden que desmaximiza es `unmaximize()` de la propia ventana GTK.
        """
        if native is not None and hasattr(native, "unmaximize") and glib:
            _gtk_query(glib, native.unmaximize)
        else:
            self._window.restore()

    def window_state(self):
        """Si la ventana está maximizada y si se puede redimensionar por los bordes.

        Lo primero lo pregunta la interfaz para esconder los tiradores con la
        ventana maximizada, y se le pregunta al sistema en vez de llevarlo por
        nuestra cuenta: la ventana también se maximiza con doble clic en su barra,
        desde el menú del gestor o con un atajo del escritorio, y nada de eso pasa
        por aquí.
        """
        state = {"maximized": False, "resizable": not paths.is_windows()}
        if not hasattr(self, "_window") or not self._window:
            return state
        try:
            native = getattr(self._window, "native", None)
            glib = _ensure_glib()
            if native is not None and hasattr(native, "is_maximized") and glib:
                state["maximized"] = bool(_gtk_query(glib, native.is_maximized, False))
            else:
                state["maximized"] = bool(getattr(self, "_maximized", False))
        except Exception as e:
            logger.info(f"window_state falló: {e}")
        return state

    def _ensure_mods_env(self):
        os.environ.pop("STELLA_MODS_DIR", None)
        inst = self.get_current_instance()
        if inst and inst.get("mods_dir"):
            os.environ["STELLA_MODS_DIR"] = inst["mods_dir"]
            return inst["mods_dir"]
        return None

    def get_installed_mods(self, project_type=None):
        md = self._ensure_mods_env()
        key = f"installed_{project_type or 'all'}_{md or 'global'}"
        def _fetch():
            if project_type in (None, "all", ""):
                return {"mods": mods.get_installed_mods()}
            return {"mods": mods.get_installed_mods(project_type=project_type)}
        return _cached(key, _CACHE_TTL, _fetch)

    def delete_mod(self, filename):
        self._ensure_mods_env()
        ok = mods.delete_mod(filename)
        self._clear_browse_cache()
        return {"ok": ok}
