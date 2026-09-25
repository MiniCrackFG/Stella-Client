"""La ventana de Windows: lo que hay que poner de nuestra parte sin marco.

El launcher dibuja su propia barra de título, así que pywebview crea la ventana
sin marco. Eso no es sólo "una ventana sin adornos": con `FormBorderStyle.None`
Windows se queda sin nada que agarrar, y con ello desaparecen tres cosas que allí
da por hechas con cualquier ventana.

- Sin área no-cliente no hay borde que arrastrar, así que no hay forma de
  redimensionarla por mucho `resizable=True` que se ponga.
- No hay colocación automática: la posición hay que darla a mano.
- Y aplicarle `WindowState = Maximized` antes de quitarle el marco —que es el
  orden en el que lo hace pywebview— deja una ventana grande y descolocada, que
  es exactamente lo que se veía al abrir.

Aquí está esa parte: devolverle el borde de tamaño nativo (`WS_THICKFRAME`, el
estilo que le dice a Windows qué zona se arrastra), colocar la ventana donde toca
y leer su geometría para poder recordarla entre sesiones.

Nada de este módulo se usa fuera de Windows: se importa siempre después de
comprobar `paths.is_windows()`.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

# --- Win32: constantes que no vienen en ctypes.wintypes ---
GWL_STYLE = -16
WS_THICKFRAME = 0x00040000

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020

MONITOR_DEFAULTTONEAREST = 0x00000002
SPI_GETWORKAREA = 0x0030

# Atributos de DWM (Windows 11). En Windows 10 la llamada falla y se ignora: no
# es motivo para dejar de colocar la ventana.
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWCP_ROUND = 2
_BORDER_COLOR = 0x0050181E  # COLORREF (0x00BBGGRR) del morado de --border

# Lo mínimo que se acepta al recordar una geometría: sin este suelo, una ventana
# guardada en un estado absurdo se quedaría absurda para siempre.
_MIN_WIDTH = 800
_MIN_HEIGHT = 450

# Parte de la ventana que tiene que caer dentro de alguna pantalla para dar por
# buena la posición recordada. Si el monitor donde estaba ya no está enchufado,
# se abre centrada en vez de en un sitio donde no se vería.
_MIN_VISIBLE = 0.25

# Cuánto puede salirse una ventana maximizada de su área de trabajo sin que se
# dé por mal colocada. El sistema añade un par de píxeles de borde invisible al
# calcular el máximo, así que exigir coincidencia exacta sería pelearse con él.
_MAX_SLACK = 2

# Vueltas y espera al comprobar una maximización: el sistema la termina de
# aplicar en cuanto atiende el mensaje, pero se le da un suspiro por si acaso.
_SETTLE_ATTEMPTS = 3
_SETTLE_PAUSE = 0.08


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("rcNormalPosition", _RECT),
    ]


_MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(_RECT),
    wintypes.LPARAM,
)

_libs = {}


def _user32():
    """`user32` con los tipos declarados una sola vez.

    Sin `argtypes`, ctypes convierte un HWND (un puntero de 64 bits) en un entero
    de 32: se perdería media dirección y las llamadas irían a parar a otra
    ventana. Por eso cada función declara aquí lo que recibe.
    """
    if "user32" not in _libs:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.IsZoomed.argtypes = [wintypes.HWND]
        user32.IsZoomed.restype = wintypes.BOOL
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(_WINDOWPLACEMENT)]
        user32.GetWindowPlacement.restype = wintypes.BOOL
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HMONITOR
        user32.MonitorFromRect.argtypes = [ctypes.POINTER(_RECT), wintypes.DWORD]
        user32.MonitorFromRect.restype = wintypes.HMONITOR
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        user32.EnumDisplayMonitors.argtypes = [
            wintypes.HDC,
            ctypes.POINTER(_RECT),
            _MONITORENUMPROC,
            wintypes.LPARAM,
        ]
        user32.EnumDisplayMonitors.restype = wintypes.BOOL
        user32.SystemParametersInfoW.argtypes = [
            wintypes.UINT,
            wintypes.UINT,
            ctypes.c_void_p,
            wintypes.UINT,
        ]
        user32.SystemParametersInfoW.restype = wintypes.BOOL
        _libs["user32"] = user32
    return _libs["user32"]


def _dwmapi():
    if "dwmapi" not in _libs:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        dwmapi.DwmSetWindowAttribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
        _libs["dwmapi"] = dwmapi
    return _libs["dwmapi"]


def _handle(window):
    """El HWND de la ventana de pywebview, o 0 si todavía no hay ventana."""
    native = getattr(window, "native", None)
    handle = getattr(native, "Handle", None)
    if handle is None:
        return 0
    try:
        return int(handle.ToInt64())
    except Exception:
        return 0


def _box(left, top, right, bottom):
    return (int(left), int(top), int(right - left), int(bottom - top))


def _rect(handle):
    """Rectángulo actual de la ventana en píxeles de pantalla."""
    box = _RECT()
    if not _user32().GetWindowRect(wintypes.HWND(handle), ctypes.byref(box)):
        return None
    return _box(box.left, box.top, box.right, box.bottom)


def _accepted(box):
    """El rectángulo, o None si no describe una ventana que valga la pena recordar.

    Hay fuentes que no siempre saben contestar —el rectángulo de reposo de .NET
    sólo es válido con la ventana maximizada o minimizada, y si no lo está
    devuelve uno vacío— y una tupla de ceros, que es lo que sale de ahí, pasaría
    por buena en cualquier comprobación de "¿hay algo?".
    """
    if not box or box[2] < _MIN_WIDTH or box[3] < _MIN_HEIGHT:
        return None
    return box


def _slack(box, work):
    """Cuánto se sale un rectángulo del área de trabajo, en píxeles."""
    return max(
        work[0] - box[0],
        work[1] - box[1],
        box[0] + box[2] - work[0] - work[2],
        box[1] + box[3] - work[1] - work[3],
    )


def _restore_bounds(native):
    """Rectángulo de reposo según .NET, que ya lo guarda en píxeles de pantalla."""
    try:
        bounds = native.RestoreBounds
        return (int(bounds.X), int(bounds.Y), int(bounds.Width), int(bounds.Height))
    except Exception:
        return None


def _normal_placement(handle):
    """Rectángulo de reposo según Win32, por si .NET no lo puede dar.

    `rcNormalPosition` viene en coordenadas del área de trabajo en vez de las de
    pantalla; con la barra de tareas abajo o a la derecha coinciden, así que sólo
    estorba en configuraciones poco habituales.
    """
    placement = _WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(_WINDOWPLACEMENT)
    if not _user32().GetWindowPlacement(wintypes.HWND(handle), ctypes.byref(placement)):
        return None
    normal = placement.rcNormalPosition
    return _box(normal.left, normal.top, normal.right, normal.bottom)


def _monitor_work(monitor):
    if not monitor:
        return None
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not _user32().GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return _box(info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)


def _monitors():
    """Todas las pantallas, con su área de trabajo y su área completa."""
    found = []

    def collect(monitor, _hdc, _rect_ptr, _param):
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if _user32().GetMonitorInfoW(monitor, ctypes.byref(info)):
            found.append(
                {
                    "monitor": _box(
                        info.rcMonitor.left,
                        info.rcMonitor.top,
                        info.rcMonitor.right,
                        info.rcMonitor.bottom,
                    ),
                    "work": _box(info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom),
                }
            )
        return True

    callback = _MONITORENUMPROC(collect)
    _user32().EnumDisplayMonitors(None, None, callback, 0)
    return found


def _primary_work_area():
    """Área de trabajo del monitor principal (el escritorio menos la barra de tareas)."""
    box = _RECT()
    if _user32().SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(box), 0):
        return _box(box.left, box.top, box.right, box.bottom)
    return None


def _work_area(handle):
    """Área de trabajo del monitor donde está la ventana."""
    monitor = _user32().MonitorFromWindow(wintypes.HWND(handle), MONITOR_DEFAULTTONEAREST)
    return _monitor_work(monitor) or _primary_work_area()


def _nearest_work_area(box):
    """Área de trabajo del monitor más cercano a un rectángulo."""
    rect = _RECT(box[0], box[1], box[0] + box[2], box[1] + box[3])
    monitor = _user32().MonitorFromRect(ctypes.byref(rect), MONITOR_DEFAULTTONEAREST)
    return _monitor_work(monitor) or _primary_work_area()


def _intersection(first, second):
    """Área común de dos rectángulos, en píxeles cuadrados."""
    width = min(first[0] + first[2], second[0] + second[2]) - max(first[0], second[0])
    height = min(first[1] + first[3], second[1] + second[3]) - max(first[1], second[1])
    if width <= 0 or height <= 0:
        return 0
    return width * height


def _visible_ratio(box):
    """Qué parte del rectángulo cae dentro de alguna pantalla (1.0 = toda)."""
    area = box[2] * box[3]
    if area <= 0:
        return 0.0
    visible = sum(_intersection(box, screen["work"]) for screen in _monitors())
    return visible / area


def _centered_in(work, size):
    """Centra un tamaño en el área de trabajo (encogiéndolo si no cabe)."""
    if not work:
        return None
    width = min(size[0], work[2])
    height = min(size[1], work[3])
    return (
        int(work[0] + (work[2] - width) // 2),
        int(work[1] + (work[3] - height) // 2),
        int(width),
        int(height),
    )


def _fit(box, work):
    """Deja el rectángulo dentro del área de trabajo: primero encoge, luego acerca."""
    if not work:
        return box
    x, y, width, height = box
    width = min(width, work[2])
    height = min(height, work[3])
    x = min(max(x, work[0]), work[0] + work[2] - width)
    y = min(max(y, work[1]), work[1] + work[3] - height)
    return (int(x), int(y), int(width), int(height))


def _move(handle, box):
    """Coloca la ventana.

    Se llama desde el hilo que arranca la interfaz, no desde el de la ventana: la
    llamada espera a que su dueño la atienda. Eso es justo lo que se quiere aquí,
    porque después viene `show()` y el orden tiene que respetarse.
    """
    return bool(
        _user32().SetWindowPos(
            wintypes.HWND(handle), None, box[0], box[1], box[2], box[3], SWP_NOZORDER
        )
    )


def _polish(handle):
    """Esquinas redondeadas y borde del color de la interfaz, si el sistema lo admite."""
    for attribute, value in (
        (_DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND),
        (_DWMWA_BORDER_COLOR, _BORDER_COLOR),
    ):
        try:
            data = ctypes.c_int(value)
            _dwmapi().DwmSetWindowAttribute(
                wintypes.HWND(handle), attribute, ctypes.byref(data), ctypes.sizeof(data)
            )
        except Exception:
            return


def enable_sizing_frame(window):
    """Devuelve a la ventana el borde de tamaño nativo.

    Sin `WS_THICKFRAME` no hay forma de redimensionar: es el estilo que le dice a
    Windows que la ventana tiene una zona que se arrastra. Al perderlo con el
    marco, el ratón sobre el borde no encuentra nada que agarrar.

    `SWP_FRAMECHANGED` es obligatorio al cambiar el estilo: sin él Windows sigue
    usando el cálculo del área no-cliente que ya tenía y el cambio no se nota.
    """
    handle = _handle(window)
    if not handle:
        return False
    user32 = _user32()
    style = user32.GetWindowLongPtrW(wintypes.HWND(handle), GWL_STYLE)
    if not style:
        return False
    if style & WS_THICKFRAME:
        return True
    user32.SetWindowLongPtrW(wintypes.HWND(handle), GWL_STYLE, style | WS_THICKFRAME)
    user32.SetWindowPos(
        wintypes.HWND(handle),
        None,
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
    )
    _polish(handle)
    logger.info("Borde de tamaño nativo activado en la ventana")
    return True


def primary_work_area():
    """Área de trabajo del monitor principal: lo que ocupa una ventana maximizada."""
    return _primary_work_area()


def remembered_box(remembered):
    """Rectángulo recordado, o None si no lo hay o si ya no sirve."""
    if not isinstance(remembered, dict):
        return None
    try:
        box = (
            int(remembered["x"]),
            int(remembered["y"]),
            int(remembered["width"]),
            int(remembered["height"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if box[2] < _MIN_WIDTH or box[3] < _MIN_HEIGHT:
        return None
    if _visible_ratio(box) < _MIN_VISIBLE:
        return None
    return box


def place(window, remembered=None):
    """Coloca la ventana antes de que se vea y devuelve el rectángulo aplicado.

    Vale la geometría recordada cuando sigue habiendo pantalla debajo; si no, se
    centra con el tamaño que ya tiene la ventana (el que le dio quien la creó).
    """
    handle = _handle(window)
    if not handle:
        return None
    current = _rect(handle)
    if not current:
        return None

    box = remembered_box(remembered)
    if box is None:
        work = _work_area(handle)
        box = _centered_in(work, (current[2], current[3])) or _fit(current, work)
        logger.info("Ventana centrada en %s (área de trabajo %s)", box, work)
    else:
        box = _fit(box, _nearest_work_area(box))
        logger.info("Ventana colocada donde se dejó: %s", box)

    if not _move(handle, box):
        logger.warning("No se pudo colocar la ventana")
        return None
    return box


def is_visible(window):
    """Si Windows tiene la ventana en pantalla.

    Hace falta porque pedir que se enseñe puede quedarse en nada sin dar error:
    pywebview ignora la petición si la ventana todavía no está registrada.
    """
    handle = _handle(window)
    return bool(handle and _user32().IsWindowVisible(wintypes.HWND(handle)))


def is_maximized(window):
    """Si Windows tiene la ventana maximizada, que es el estado que cuenta.

    Llevar la cuenta por nuestra parte se desincroniza en cuanto se maximiza por
    otra vía: doble clic en la barra, `Win` + flechas o arrastrarla al borde.
    """
    handle = _handle(window)
    return bool(handle and _user32().IsZoomed(wintypes.HWND(handle)))


def is_minimized(window):
    """Si la ventana está minimizada, que es el otro estado sin rectángulo propio."""
    handle = _handle(window)
    return bool(handle and _user32().IsIconic(wintypes.HWND(handle)))


def _set_maximized_bounds(window, work):
    """Apunta dónde tiene que acabar la ventana maximizada.

    Es la respuesta que WinForms da cuando Windows pregunta por el tamaño máximo
    de la ventana, que es lo que decide de verdad una maximización, así que vale
    también para los caminos que no pasan por nuestro botón: `Win` + flecha
    arriba o arrastrarla al borde superior de la pantalla.

    En .NET la propiedad está protegida —su sitio natural es una clase derivada
    de `Form`, no un módulo de fuera—, así que se pide por reflexión. Si algo de
    esto faltara, se devuelve False sin más: el trabajo lo termina
    `_settle_maximized`.
    """
    native = getattr(window, "native", None)
    if native is None or not work:
        return False
    try:
        import clr  # noqa: F401  (deja listo el puente con .NET)
        from System.Drawing import Rectangle
        from System.Reflection import BindingFlags

        prop = native.GetType().GetProperty(
            "MaximizedBounds", BindingFlags.Instance | BindingFlags.NonPublic
        )
        if prop is None:
            return False
        prop.SetValue(native, Rectangle(work[0], work[1], work[2], work[3]))
        return True
    except Exception as e:
        logger.info("No se pudo fijar el máximo de la ventana: %s", e)
        return False


def _settle_maximized(handle, work):
    """Confirma que la ventana maximizada cabe en su área de trabajo, y la ajusta.

    El aviso de `_set_maximized_bounds` no es de fiar en todas las versiones de
    .NET, y una ventana maximizada que se sale se lleva por delante la barra de
    tareas, que es justo lo que se está arreglando. Aquí se mide el resultado y,
    si se sale, se coloca a mano: aunque se pierdan de vista unos píxeles de
    borde, la barra de tareas queda a la vista.
    """
    box = None
    for _ in range(_SETTLE_ATTEMPTS):
        box = _rect(handle)
        if box and _slack(box, work) <= _MAX_SLACK:
            return True
        time.sleep(_SETTLE_PAUSE)
    if not box:
        return False
    logger.info(
        "La ventana maximizada se salía del área de trabajo (%s): se coloca en %s", box, work
    )
    return _move(handle, work)


def maximize(window):
    """Maximiza la ventana al área de trabajo, no al rectángulo entero del monitor.

    Es la diferencia entre dejar la barra de tareas a la vista y taparla, que es
    lo que hacía Windows al estirar la ventana hasta el borde de la pantalla.
    """
    handle = _handle(window)
    if not handle:
        return False
    work = _work_area(handle)
    if not work:
        window.maximize()
        return True
    _set_maximized_bounds(window, work)
    window.maximize()
    _settle_maximized(handle, work)
    return True


def capture(window):
    """Geometría que merece recordarse, o None si todavía no hay ventana.

    De una ventana maximizada o minimizada se guarda el rectángulo al que vuelve
    al restaurarse —el que se ve en pantalla es el de la pantalla entera, y
    guardarlo dejaría el launcher abierto así para siempre—. De una ventana
    normal se guarda el suyo a secas: es el dato bueno, y además el único camino
    que no depende de que el sistema tenga una posición de reposo apuntada, que
    no la tiene mientras la ventana está en su estado normal.
    """
    handle = _handle(window)
    if not handle:
        return None
    native = getattr(window, "native", None)
    if is_maximized(window) or is_minimized(window):
        box = (
            _accepted(_restore_bounds(native))
            or _accepted(_normal_placement(handle))
            or _accepted(_rect(handle))
        )
    else:
        box = _accepted(_rect(handle)) or _accepted(_normal_placement(handle))
    if not box:
        return None
    return {
        "x": box[0],
        "y": box[1],
        "width": box[2],
        "height": box[3],
        "maximized": is_maximized(window),
    }
