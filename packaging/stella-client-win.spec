# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para Stella Client en Windows.

Vive en `packaging/` por el mismo motivo que la de Linux: `.gitignore` excluye
`*.spec`, y una receta que hay que versionar no puede estar en un fichero
ignorado. La excepción `!packaging/*.spec` es la que lo permite.

Tres decisiones que importan:

- **onedir, no onefile.** `onefile` se descomprime en `%TEMP%` en cada arranque,
  tarda unos segundos en abrir y es lo que más hace saltar a los antivirus.
- **Dos ejecutables del mismo programa.** `stella-client.exe` va sin consola, que
  es lo que ve el jugador, y `stella-client-check.exe` con consola, que es el que
  permite ejecutar la comprobación del entorno y leer el resultado. Comparten el
  `COLLECT`, así que el intérprete y las dependencias están una sola vez.
- **Sin GTK.** Aquí la ventana la dibuja el motor de Edge (WebView2), que ya está
  en el sistema. No hay pila gráfica que empaquetar ni dependencias de sistema que
  declarar, y por eso no se porta la auditoría de `ldd` de la receta de Linux: allí
  hace falta porque GTK no aparece en `ldd`, aquí porque no hay nada que auditar.
"""

import os

REPO = os.path.dirname(SPECPATH)
ICON = os.path.join(REPO, "assets", "icon.ico")

if not os.path.isfile(ICON):
    raise SystemExit(
        f"Falta {ICON}. Lo genera el build:  python packaging/windows/make-ico.py"
    )

with open(os.path.join(REPO, "VERSION"), encoding="utf-8") as handle:
    VERSION = handle.read().strip()


def _version_quad(version):
    """'0.1.0' -> (0, 1, 0, 0), que es lo que pide un recurso de versión."""
    parts = []
    for chunk in version.split(".")[:4]:
        digits = "".join(character for character in chunk if character.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def _write_version_resource(version, path):
    """Genera el recurso que hace que Propiedades muestre nombre y versión.

    Se escribe en el build a partir de `VERSION` en vez de mantener un fichero
    aparte, que es justo la clase de copia que se queda desincronizada sin avisar.
    El texto va sólo en ASCII a propósito: este fichero lo evalúa PyInstaller.
    """
    quad = _version_quad(version)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "VSVersionInfo(\n"
            "  ffi=FixedFileInfo(\n"
            f"    filevers={quad},\n"
            f"    prodvers={quad},\n"
            "    mask=0x3f,\n"
            "    flags=0x0,\n"
            "    OS=0x40004,\n"
            "    fileType=0x1,\n"
            "    subtype=0x0,\n"
            "    date=(0, 0)\n"
            "  ),\n"
            "  kids=[\n"
            "    StringFileInfo([\n"
            "      StringTable(\n"
            "        '040904B0',\n"
            "        [StringStruct('CompanyName', 'miniloopp'),\n"
            "         StringStruct('FileDescription', 'Stella Client'),\n"
            f"         StringStruct('FileVersion', '{version}'),\n"
            "         StringStruct('InternalName', 'stella-client'),\n"
            "         StringStruct('OriginalFilename', 'stella-client.exe'),\n"
            "         StringStruct('ProductName', 'Stella Client'),\n"
            f"         StringStruct('ProductVersion', '{version}'),\n"
            "         StringStruct('LegalCopyright', 'MIT License')])\n"
            "    ]),\n"
            "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
            "  ]\n"
            ")\n"
        )
    return path


VERSION_RESOURCE = _write_version_resource(
    VERSION, os.path.join(REPO, "build", "windows", "version-info.txt")
)

a = Analysis(
    [os.path.join(REPO, "main.py")],
    pathex=[REPO],
    binaries=[],
    datas=[
        (os.path.join(REPO, "ui"), "ui"),
        (os.path.join(REPO, "launcher"), "launcher"),
        (os.path.join(REPO, "assets"), "assets"),
        # La licencia MIT pide que su texto acompañe a lo que se distribuye.
        (os.path.join(REPO, "LICENSE"), "."),
    ],
    hiddenimports=[
        # pywebview elige backend por nombre según el sistema, así que el análisis
        # estático no llega a verlo y hay que decírselo. Igual con el puente .NET.
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "clr",
        "clr_loader",
        "pythonnet",
        "bottle",
        "proxy_tools",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Los backends y la pila de pywebview que aquí no se usan: sin esto, el
        # análisis sigue los imports condicionales y arrastra medio entorno
        # gráfico que en Windows ni existe ni hace falta.
        "gi",
        "gi.repository",
        "qtpy",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "cefpython3",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# `console=False`: es el que abre el jugador, y una ventana de consola asomaría
# detrás del launcher. Su precio es que `sys.stderr` es None, y de ahí que
# `main.py` escriba el registro en un fichero cuando corre en Windows.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stella-client",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_RESOURCE,
)

# El mismo programa con consola, para poder ejecutar la comprobación del entorno
# y leer lo que imprime. `main.py` lo distingue por el nombre del ejecutable, así
# que no hay que pasarle ningún argumento.
check_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stella-client-check",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_RESOURCE,
)

coll = COLLECT(
    exe,
    check_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="stella-client",
)
