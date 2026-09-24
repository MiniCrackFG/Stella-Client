# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para Stella Client.

Vive aquí y no en `main.spec` porque `.gitignore` excluye `*.spec`: una receta
que hay que versionar no puede estar en un fichero ignorado.

Dos decisiones que importan para que el binario sirva en cualquier distro
moderna:

- **onedir**, no onefile. El modo onefile se descomprime en `/tmp` en cada
  arranque, y hay sistemas con `/tmp` montado `noexec` donde no arranca nunca.
- **La pila gráfica NO se empaqueta.** En cuanto PyInstaller ve
  `gi.repository.Gtk` intenta meter GTK, sus satellites (atspi, dconf, gvfs,
  módulos de GIO), los loaders de gdk-pixbuf, los typelibs y hasta el tema de
  iconos de Adwaita: miles de ficheros que además fijan versiones concretas y,
  con ellas, la glibc de esta máquina. Todo eso lo pone la distro.

Política, en una frase: **dentro van sólo los ficheros propios del proyecto, los
wheels de la venv y el intérprete de Python con sus dependencias**; lo demás
viene del sistema. Es lo que mantiene el payload pequeño y las dependencias
declarables.
"""

import os
import re
import subprocess
import sys

# El spec vive en packaging/, así que todo se resuelve desde la raíz del repo:
# las rutas de un spec son relativas a su propio directorio.
REPO = os.path.dirname(SPECPATH)
PYTHON_DIR = f"/python{sys.version_info[0]}.{sys.version_info[1]}/"

# La pila gráfica no entra nunca, aunque `_gi.so` la enlace: la pone la distro
# para no congelar su versión ni su glibc. Se descarta ANTES de podar huérfanos,
# porque si no, el seguimiento de dependencias la vuelve a meter por la puerta de
# atrás. Las dependencias resultantes se declaran en el paquete.
GUI_STACK_PREFIXES = (
    "libglib-2.0",
    "libgobject-2.0",
    "libgio-2.0",
    "libgmodule-2.0",
    "libgirepository-",
    "libgtk-3",
    "libgdk-3",
    "libatk-1.0",
    "libatk-bridge",
    "libwebkit2gtk-",
    "libjavascriptcoregtk-",
    "libsoup-3.0",
    "libgdk_pixbuf",
    "libpango-1.0",
    "libpangocairo",
    "libpangoft2",
    "libcairo",
)


def _drop_gui_stack(binaries):
    def _keep(entry):
        source = entry[1] or ""
        if _is_project(source) or not os.path.isabs(source):
            return True
        name = os.path.basename(source)
        return not any(name.startswith(prefix) for prefix in GUI_STACK_PREFIXES)

    return TOC([entry for entry in binaries if _keep(entry)])


def _dt_needed(path):
    """Nombres de las librerías de las que depende un ELF, leídos con readelf."""
    try:
        out = subprocess.run(
            ["readelf", "-d", str(path)], capture_output=True, text=True, timeout=60
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {m.group(1) for m in re.finditer(r"\(NEEDED\)\s+.*?\[([^\]]+)\]", out)}


def _prune_orphans(binaries):
    """Quita del payload las librerías del sistema que no necesita nadie.

    PyInstaller las recoge por sus hooks (la pila de OpenSSL, sqlite, expat...) sin
    comprobar si algo las enlaza de verdad, y cada una arrastra la glibc de esta
    máquina al paquete. En el Python portátil todo eso va dentro de `libpython`,
    así que aquí sobran.

    Se calcula siguiendo los `DT_NEEDED` desde los ficheros propios en vez de
    mantener una lista a mano, que es justo lo que se queda obsoleto sin avisar.
    """
    sources = {}
    for entry in binaries:
        if entry[1] and os.path.isabs(entry[1]):
            sources[entry[0]] = entry[1]

    needed = set()
    queue = [src for name, src in sources.items() if _is_project(src)]
    # El bootloader (el propio ejecutable) necesita libpython y no está en esta lista.
    needed.add("libpython")
    while queue:
        current = queue.pop()
        for name in _dt_needed(current):
            if name in needed:
                continue
            needed.add(name)
            source = sources.get(name)
            if source and not _is_project(source):
                queue.append(source)

    def _keep(entry):
        source = entry[1] or ""
        if _is_project(source) or not os.path.isabs(source):
            return True
        name = os.path.basename(source)
        return name.startswith("libpython") or name in needed

    return TOC([entry for entry in binaries if _keep(entry)])


# Datos del sistema que PyInstaller añade al ver GTK: temas de iconos (39 000
# enlaces simbólicos al tema del sistema, que en otra máquina estarían rotos),
# schemas de glib, configuración de fontconfig, caché de loaders de gdk-pixbuf y
# los typelibs. Nada de eso va dentro.
FOREIGN_DATA_PREFIXES = (
    "share/",
    "lib/",
    "etc/",
    "gi_typelibs/",
    "gio_modules/",
)


def _is_project(path):
    """True si el fichero es nuestro, de un wheel, o del intérprete de Python."""
    return (
        path.startswith(REPO + os.sep)
        or "/site-packages/" in path
        or PYTHON_DIR in path
    )


def _keep_data(entry):
    """Los datos se filtran por DESTINO.

    Por origen no basta: los enlaces simbólicos de los temas de iconos llegan con
    rutas relativas, así que colarse por ese lado es lo más fácil del mundo.
    """
    dest = entry[0] or ""
    if any(dest.startswith(prefix) for prefix in FOREIGN_DATA_PREFIXES):
        return False
    return _is_project(entry[1] or "")


a = Analysis(
    [os.path.join(REPO, "main.py")],
    pathex=[REPO],
    binaries=[],
    datas=[
        (os.path.join(REPO, "ui"), "ui"),
        (os.path.join(REPO, "launcher"), "launcher"),
        (os.path.join(REPO, "assets"), "assets"),
    ],
    hiddenimports=[
        "optparse",
        "gi",
        "gi.repository.GLib",
        "gi.repository.GObject",
        "gi.repository.GdkPixbuf",
        "gi.repository.Gtk",
        "gi.repository.Gio",
        "gi.repository.WebKit2",
        "gi.repository.JavaScriptCore",
        "gi.repository.Pango",
        "gi.repository.PangoCairo",
        "gi.repository.cairo",
        "gi.repository.HarfBuzz",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = _prune_orphans(_drop_gui_stack(a.binaries))
a.datas = TOC([entry for entry in a.datas if _keep_data(entry)])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stella-client",
    debug=False,
    bootloader_ignore_signals=False,
    # PyInstaller quita aquí los símbolos del bootloader ANTES de pegarle el
    # archivo con el payload: hacerlo después, desde fuera, pondría en riesgo
    # justo ese añadido.
    strip=True,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(REPO, "assets", "icon-256.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="stella-client",
)
