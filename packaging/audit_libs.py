#!/usr/bin/env python3
"""Auditoría del payload de Stella Client.

Hace dos comprobaciones, y las dos son la razón por la que el mismo binario
sirve en varias distros:

1. **Que ninguna librería gráfica del sistema se haya colado dentro del
   payload.** Si entran, se congela su versión —y la glibc de la máquina donde
   se compiló—, y el binario pasa a arrancar sólo en distros parecidas a la de
   origen. Se comprueba con el nombre del fichero dentro del payload.

2. **Qué librerías de fuera necesita de verdad**, resueltas con `ldd` para cada
   ELF del payload. De ahí salen las dependencias del `.deb` y del `.rpm`:
   medidas, no recordadas.

Sobre los nombres de soname: muchos son específicos de versión (`libicu74` en
Ubuntu 24.04 es `libicu72` en Debian 12), así que traducirlos a un paquete por
nombre sería frágil y falso en cuanto cambia una distro. Por eso la tabla
distingue tres casos:

- `deb:<paquete>`     — nombre estable, se declara tal cual.
- `transitive`        — llega arrastrado por la pila gráfica que sí declaramos.
- `base`              — lo pone el sistema base (glibc, libgcc) y no se declara.

Un soname que no esté en la tabla **no pasa en silencio**: se reporta y el
script falla, que es como se evita publicar un paquete con dependencias
incompletas.

Para el `.rpm` se piden las mismas cosas por **soname** (`libgtk-3.so.0()(64bit)`),
que es el único nombre que Fedora, RHEL y openSUSE comparten sin conocer el
paquete. Los `Provides` `typelib(...)` y los nombres de paquete NO sirven para
esto: `typelib(Gtk)` sólo existe en openSUSE (Fedora mete los typelibs dentro
del propio paquete de la librería, sin generarlos como provided), y `gtk3` /
`webkit2gtk4.1` son nombres que cambian por familia. Con ellos, `dnf` aborta con
«nada proporciona typelib(Gtk) = 3.0» antes de instalar nada.

Escribe `build/external-libs.txt`, `build/depends-deb.txt` y
`build/requires-rpm.txt`.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Familias de soname que NUNCA deben viajar dentro del payload.
BLOCKED_PREFIXES = (
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

# soname -> categoría. Ver el docstring para el significado de cada una.
LIBRARY_MAP = {
    # Lo pone el sistema base; no se declara (glibc ya es dependencia implícita
    # de cualquier paquete y listarla a mano sólo añade ruido).
    "libc.so.6": "base",
    "libm.so.6": "base",
    "libdl.so.2": "base",
    "libpthread.so.0": "base",
    "librt.so.1": "base",
    "libgcc_s.so.1": "base",
    "libstdc++.so.6": "base",
    "ld-linux-x86-64.so.2": "base",
    "libutil.so.1": "base",
    "libcrypt.so.1": "base",
    # Pila gráfica: estos sí se declaran, y con las alternativas de Ubuntu 24.04
    # (el renombrado `t64` de la transición a time_t de 64 bits).
    "libgtk-3.so.0": "deb:libgtk-3-0t64 | libgtk-3-0",
    "libgdk-3.so.0": "deb:libgtk-3-0t64 | libgtk-3-0",
    "libwebkit2gtk-4.1.so.0": "deb:libwebkit2gtk-4.1-0",
    "libjavascriptcoregtk-4.1.so.0": "deb:libjavascriptcoregtk-4.1-0",
    "libgirepository-2.0.so.0": "deb:libgirepository-2.0-0",
    "libglib-2.0.so.0": "deb:libglib2.0-0t64 | libglib2.0-0",
    "libgobject-2.0.so.0": "deb:libglib2.0-0t64 | libglib2.0-0",
    "libgio-2.0.so.0": "deb:libglib2.0-0t64 | libglib2.0-0",
    "libgmodule-2.0.so.0": "deb:libglib2.0-0t64 | libglib2.0-0",
    "libgdk_pixbuf-2.0.so.0": "deb:libgdk-pixbuf-2.0-0",
    "libpango-1.0.so.0": "deb:libpango-1.0-0",
    "libpangocairo-1.0.so.0": "deb:libpango-1.0-0",
    "libpangoft2-1.0.so.0": "deb:libpango-1.0-0",
    "libcairo.so.2": "deb:libcairo2",
    "libcairo-gobject.so.2": "deb:libcairo-gobject2",
    "libatk-1.0.so.0": "deb:libatk1.0-0t64 | libatk1.0-0",
    "libsoup-3.0.so.0": "deb:libsoup-3.0-0",
    "libX11.so.6": "deb:libx11-6",
    "libXext.so.6": "deb:libxext6",
    "libXrender.so.1": "deb:libxrender1",
    "libXcomposite.so.1": "deb:libxcomposite1",
    "libXdamage.so.1": "deb:libxdamage1",
    "libXfixes.so.3": "deb:libxfixes3",
    "libXi.so.6": "deb:libxi6",
    "libXtst.so.6": "deb:libxtst6",
    "libxcb.so.1": "deb:libxcb1",
    "libxkbcommon.so.0": "deb:libxkbcommon0",
    "libwayland-client.so.0": "deb:libwayland-client0",
    "libwayland-cursor.so.0": "deb:libwayland-cursor0",
    "libwayland-egl.so.1": "deb:libwayland-egl1",
    "libepoxy.so.0": "deb:libepoxy0",
    "libgbm.so.1": "deb:libgbm1",
    "libdrm.so.2": "deb:libdrm2",
    "libdbus-1.so.3": "deb:libdbus-1-3",
    "libfontconfig.so.1": "deb:libfontconfig1",
    "libfreetype.so.6": "deb:libfreetype6",
    "libexpat.so.1": "deb:libexpat1",
    "libharfbuzz.so.0": "deb:libharfbuzz0b",
    "libpixman-1.so.0": "deb:libpixman-1-0",
    "libffi.so.8": "deb:libffi8",
    "libz.so.1": "deb:zlib1g",
    # Pedido por deb: en rpm NO se puede pedir por soname (ver
    # RPM_SONAME_EXCEPTIONS): Fedora lo llama `libbz2.so.1`.
    "libbz2.so.1.0": "deb:libbz2-1.0",
    "libpcre2-8.so.0": "deb:libpcre2-8-0",
    "liblcms2.so.2": "deb:liblcms2-2",
    "libgcrypt.so.20": "deb:libgcrypt20",
    "libsystemd.so.0": "deb:libsystemd0",
    "libXau.so.6": "deb:libxau6",
    "libXdmcp.so.6": "deb:libxdmcp6",
    "libxcb-render.so.0": "deb:libxcb-render0",
    "libxcb-shm.so.0": "deb:libxcb-shm0",
    "libbrotlicommon.so.1": "deb:libbrotli1",
    "libbrotlidec.so.1": "deb:libbrotli1",
    "libbrotlienc.so.1": "deb:libbrotli1",
    "libzstd.so.1": "deb:libzstd1",
    "libpng16.so.16": "deb:libpng16-16t64 | libpng16-16",
    "libjpeg.so.8": "deb:libjpeg62-turbo | libjpeg-turbo8",
    # Específicos de versión: llegan arrastrados por la pila gráfica que sí
    # declaramos, así que no se traducen a un nombre que cambiaría por distro.
    "libicuuc.so.": "transitive",
    "libicui18n.so.": "transitive",
    "libicudata.so.": "transitive",
    "libxml2.so.": "transitive",
    "libxslt.so.": "transitive",
    "libsqlite3.so.": "transitive",
    "libjpeg.so.": "transitive",
    "libwebp.so.": "transitive",
    "libwebpmux.so.": "transitive",
    "libwebpdemux.so.": "transitive",
    "libpng16.so.": "transitive",
    "libtiff.so.": "transitive",
    "libopenjp2.so.": "transitive",
    "libbrotli": "transitive",
    "libsharpyuv.so.": "transitive",
    "libavif.so.": "transitive",
    "libzstd.so.": "transitive",
    "liblzma.so.": "transitive",
    "libgst": "transitive",
    "liborc-0.4.so.": "transitive",
    "libgraphene-1.0.so.": "transitive",
    "libsecret-1.so.": "transitive",
    "libenchant-2.so.": "transitive",
    "libhyphen.so.": "transitive",
    "libpsl.so.": "transitive",
    "libnghttp2.so.": "transitive",
    "libgssapi_krb5.so.": "transitive",
    "libkrb5.so.": "transitive",
    "libk5crypto.so.": "transitive",
    "libkrb5support.so.": "transitive",
    "libcom_err.so.": "transitive",
    "libkeyutils.so.": "transitive",
    "libGL.so.": "transitive",
    "libGLX.so.": "transitive",
    "libGLdispatch.so.": "transitive",
    "libEGL.so.": "transitive",
    "libselinux.so.": "transitive",
    "libmount.so.": "transitive",
    "libblkid.so.": "transitive",
    "libuuid.so.": "transitive",
}

# GTK y WebKitGTK NO salen en `ldd`: se cargan al vuelo a través de los typelibs de
# GObject Introspection, así que no son DT_NEEDED de nada. Sin declararlos, el
# paquete se instala sin un solo error y luego no arranca — que es la peor clase
# de fallo, porque aparece en la máquina del usuario y no en la del que empaqueta.
#
# En dpkg hay que tirar de nombres de paquete, con alternativas donde el
# renombrado `t64` de Ubuntu 24.04 los cambió.
#
# En rpm se piden por **soname**, que es lo único que direccionan igual Fedora,
# RHEL y openSUSE: el paquete de la librería arrastra el typelib en las tres
# familias (`gtk3` trae `Gtk-3.0.typelib`, `webkit2gtk4.1` trae `WebKit2-4.1.typelib`).
# NO se piden `typelib(...)`: ese provided sólo lo genera openSUSE, y en Fedora
# hacen abortar `dnf` con «nada proporciona typelib(Gtk) = 3.0».
RUNTIME_DEPS_DEB = (
    "gir1.2-glib-2.0",
    "gir1.2-gtk-3.0",
    "gir1.2-gdkpixbuf-2.0",
    "gir1.2-pango-1.0",
    "gir1.2-atk-1.0",
    "gir1.2-harfbuzz-0.0",
    "gir1.2-webkit2-4.1",
    "gir1.2-javascriptcoregtk-4.1",
    "libgtk-3-0t64 | libgtk-3-0",
    "libwebkit2gtk-4.1-0",
)
RUNTIME_DEPS_RPM = (
    "libgtk-3.so.0()(64bit)",
    "libgdk-3.so.0()(64bit)",
    "libgdk_pixbuf-2.0.so.0()(64bit)",
    "libpango-1.0.so.0()(64bit)",
    "libatk-1.0.so.0()(64bit)",
    "libharfbuzz.so.0()(64bit)",
    "libwebkit2gtk-4.1.so.0()(64bit)",
    "libjavascriptcoregtk-4.1.so.0()(64bit)",
)

# Sonames que NO se pueden declarar en rpm porque su nombre no es el mismo en
# todas las familias. bzip2 es el caso clásico: Debian y Arch publican
# `libbz2.so.1.0`, Fedora y RHEL sólo `libbz2.so.1`. Pedir cualquiera de los dos
# deja el paquete sin resolver en la mitad de las distros. Como lo arrastra la
# pila gráfica (`libfreetype.so.6`, que sí se declara), no hay que pedirlo: en
# cada sistema lo pone el freetype nativo, que enlaza contra su propio bzip2.
RPM_SONAME_EXCEPTIONS = {"libbz2.so.1.0"}

_GLIBC_VERSION = re.compile(r"GLIBC_(\d+)\.(\d+)")

_BLOCKED_HINT = {
    "libglib-2.0": "glib",
    "libgobject-2.0": "glib",
    "libgio-2.0": "glib",
    "libgmodule-2.0": "glib",
    "libgirepository-": "girepository",
    "libgtk-3": "GTK 3",
    "libgdk-3": "GTK 3",
    "libatk-1.0": "ATK",
    "libatk-bridge": "ATK",
    "libwebkit2gtk-": "WebKitGTK",
    "libjavascriptcoregtk-": "WebKitGTK",
    "libsoup-3.0": "libsoup",
    "libgdk_pixbuf": "gdk-pixbuf",
    "libpango-1.0": "Pango",
    "libpangocairo": "Pango",
    "libpangoft2": "Pango",
    "libcairo": "Cairo",
}

_LDD_LINE = re.compile(r"^\s+(\S+)\s+=>\s+(\S+)")


def is_elf(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"
    except OSError:
        return False


def ldd(path):
    """Devuelve (resueltas: {soname: ruta}, no_encontradas: [soname])."""
    try:
        out = subprocess.run(
            ["ldd", str(path)], capture_output=True, text=True, timeout=60
        ).stdout
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  aviso: no se pudo analizar {path} ({e})")
        return {}, []

    resolved, missing = {}, []
    for line in out.splitlines():
        match = _LDD_LINE.match(line)
        if not match:
            continue
        soname, target = match.group(1), match.group(2)
        if target == "not":
            missing.append(soname)
        else:
            resolved[soname] = target
    return resolved, missing


def classify(soname):
    for prefix, category in LIBRARY_MAP.items():
        if soname == prefix or soname.startswith(prefix):
            return category
    return None


def min_glibc(payload):
    """Versión mínima de glibc que exige el payload, medida y no supuesta.

    La mayoría de las distros modernas van sobradas, pero conviene declarar el
    suelo real en lugar de dejar que el binario falle con "GLIBC_2.xx not found"
    en la máquina del usuario.
    """
    highest = (0, 0)
    for path in payload.rglob("*"):
        if not path.is_file() or not is_elf(path):
            continue
        try:
            out = subprocess.run(
                ["objdump", "-T", str(path)], capture_output=True, text=True, timeout=60
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        for line in out.splitlines():
            if "*UND*" not in line:
                continue
            for match in _GLIBC_VERSION.finditer(line):
                version = (int(match.group(1)), int(match.group(2)))
                if version > highest:
                    highest = version
    return highest


def names_provided_by_payload(payload):
    """Nombres que el payload ya aporta.

    El bootloader de PyInstaller pone `_internal/` en LD_LIBRARY_PATH antes de
    cargar nada, así que cualquier soname que esté ahí lo resuelve el propio
    paquete y no hay que pedírselo a la distro. Sin esto, la auditoría lista como
    externas cosas como libssl o libmpdec que sí van dentro.
    """
    return {child.name for child in payload.rglob("*")}


def main():
    if len(sys.argv) != 2:
        print("uso: audit_libs.py <directorio-del-payload>", file=sys.stderr)
        return 2

    payload = Path(sys.argv[1]).resolve()
    if not payload.is_dir():
        print(f"no existe el payload: {payload}", file=sys.stderr)
        return 2

    build_dir = Path(__file__).resolve().parent.parent / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    provided = names_provided_by_payload(payload)

    bundled, external, missing, needed_by, internal = [], {}, {}, {}, set()
    for path in sorted(payload.rglob("*")):
        if not path.is_file() or not is_elf(path):
            continue
        origin = str(path.relative_to(payload))
        for prefix in BLOCKED_PREFIXES:
            if path.name.startswith(prefix):
                bundled.append((origin, prefix))
                break
        resolved, not_found = ldd(path)
        for soname, target in resolved.items():
            key = os.path.basename(soname)
            if key in provided or Path(target).resolve().is_relative_to(payload):
                internal.add(key)
                continue
            external.setdefault(key, target)
            needed_by.setdefault(key, set()).add(origin)
        for soname in not_found:
            missing.setdefault(os.path.basename(soname), origin)

    print(
        f"\n==> Auditoría del payload "
        f"({len(external)} librerías externas, {len(internal)} las pone el propio paquete)"
    )

    if bundled:
        print("\n  ERROR: hay librerías gráficas DENTRO del payload.")
        print("  Congelan su versión y la glibc de esta máquina, y el binario")
        print("  deja de servir en otras distros:\n")
        for rel, prefix in bundled[:20]:
            print(f"    {rel}  ({_BLOCKED_HINT.get(prefix, prefix)})")
        if len(bundled) > 20:
            print(f"    … y {len(bundled) - 20} más")

    if missing:
        print("\n  ERROR: librerías que no se resuelven ni en esta máquina:")
        for soname, origin in sorted(missing.items()):
            print(f"    {soname}  (lo necesita {origin})")

    declared, transitive, unknown = set(), set(), set()
    for soname in sorted(external):
        category = classify(soname)
        if category is None:
            unknown.add(soname)
        elif category == "base":
            continue
        elif category == "transitive":
            transitive.add(soname)
        else:
            declared.add(category.removeprefix("deb:"))

    if unknown:
        print("\n  ERROR: sonames sin traducir; revisa LIBRARY_MAP antes de publicar.")
        print("  Un paquete con dependencias incompletas falla en la distro del usuario:")
        for soname in sorted(unknown):
            print(f"    {soname}  ->  {external[soname]}")

    # El tercer campo es quién lo necesita, que es lo que permite entender de un
    # vistazo por qué está en la lista cuando algo chirría.
    (build_dir / "external-libs.txt").write_text(
        "".join(
            f"{soname}\t{external[soname]}\t{','.join(sorted(needed_by.get(soname, ())))}\n"
            for soname in sorted(external)
        ),
        encoding="utf-8",
    )
    glibc = min_glibc(payload)
    glibc_str = f"{glibc[0]}.{glibc[1]}"

    deb_entries = [f"libc6 (>= {glibc_str})"] + sorted(declared) + list(RUNTIME_DEPS_DEB)
    (build_dir / "depends-deb.txt").write_text(
        ",\n ".join(deb_entries) + "\n", encoding="utf-8"
    )
    (build_dir / "glibc-min.txt").write_text(glibc_str + "\n", encoding="utf-8")

    # rpm entiende requerimientos por soname, así que no hay que traducir nada:
    # funcionan igual en Fedora, RHEL y openSUSE sin saber el nombre del paquete.
    soname_requires = sorted(
        s
        for s in external
        if classify(s) not in ("base", None) and s not in RPM_SONAME_EXCEPTIONS
    )
    (build_dir / "requires-rpm.txt").write_text(
        "".join(
            [f"Requires:        glibc >= {glibc_str}\n"]
            + [f"Requires:        {s}()(64bit)\n" for s in soname_requires]
            + [f"Requires:        {dep}\n" for dep in RUNTIME_DEPS_RPM]
        ),
        encoding="utf-8",
    )
    (build_dir / "audit.json").write_text(
        json.dumps(
            {
                "external": {k: external[k] for k in sorted(external)},
                "declared_deb": sorted(declared),
                "transitive": sorted(transitive),
                "unknown": sorted(unknown),
                "glibc_min": glibc_str,
                "runtime_deps_deb": list(RUNTIME_DEPS_DEB),
                "runtime_deps_rpm": list(RUNTIME_DEPS_RPM),
                "needed_by": {k: sorted(v) for k, v in sorted(needed_by.items())},
                "provided_by_payload": sorted(internal),
                "bundled": [b[0] for b in bundled],
                "missing": missing,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\n  declaradas (deb)   : {len(deb_entries)}")
    print(f"  glibc mínimo       : {glibc_str}")
    print(f"  base               : {len([s for s in external if classify(s) == 'base'])}")
    print(f"  fuera de ldd       : deb {len(RUNTIME_DEPS_DEB)}, rpm {len(RUNTIME_DEPS_RPM)} (GTK/WebKitGTK)")
    print("  escritas en        : build/depends-deb.txt y build/requires-rpm.txt")

    if bundled or missing or unknown:
        return 1
    print("  OK: nada gráfico dentro del payload y todas las externas identificadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
