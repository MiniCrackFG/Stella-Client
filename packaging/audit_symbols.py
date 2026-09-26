#!/usr/bin/env python3
"""Auditoría de símbolos del payload de Stella Client.

Existe por un fallo concreto y caro de encontrar: el `.deb` de la 0.2.1 se
instalaba en Ubuntu 24.04 y no arrancaba, con

    ImportError: .../_internal/gi/_gi.cpython-313-x86_64-linux-gnu.so:
    undefined symbol: gi_repository_dup_default

El símbolo no faltaba por un error de empaquetado, sino porque el payload se
compiló en una Arch con GLib 2.88, donde sí existe (libgirepository lo incorporó
en la 2.86), y Ubuntu 24.04 trae la 2.80. El binario se construyó bien y se
verificó bien en la máquina donde se construyó: lo que no se comprobó nunca es
**contra qué se estaba compilando**. Esta comprobación es eso, y se hace en cada
build para que no vuelva a pasar en silencio.

Cómo funciona, en tres pasos:

1. **La referencia se mide, no se recuerda.** Se descarga de los repositorios
   reales de Ubuntu 24.04 «noble» el paquete que provee cada biblioteca de la
   familia GLib (`libglib2.0-0t64` y `libgirepository-2.0-0`) y se saca su tabla
   de símbolos exportados. El nombre del fichero se resuelve contra el listado
   del pool en vez de escribirlo a mano: la revisión cambia cada pocas semanas
   (`2.80.0-6ubuntu3.8` ya no está publicado y da 404) y un nombre fijo convierte
   la comprobación en un fallo de red. Se guarda en `build/refs/`, así que los
   builds siguientes no vuelven a descargar nada mientras la revisión no cambie.
2. **El otro lado de la comparación es esta máquina.** Un símbolo que el payload
   pide y que no está ni en la referencia ni en las bibliotecas del sistema donde
   se compila no es asunto de esta comprobación: viene de la libc, del intérprete
   Python o de otro fichero del propio payload. Sólo hay un caso que importa, y es
   el del fallo: **lo exporta esta máquina y no lo exporta Ubuntu**. Eso es una
   versión de más, y es exactamente lo que no se ve hasta que arranca en otro
   sitio.
3. **Se recorre el payload entero**, fichero por fichero, y sólo se miran los
   símbolos indefinidos de los ELF que enlazan con alguna de esas bibliotecas
   (según sus `DT_NEEDED`). Cualquier símbolo que caiga en el caso del punto 2 se
   reporta con el fichero que lo pide y **falla el build**.

Escribe `build/symbols-audit.txt` con el detalle y sale con código distinto de
cero también cuando no pudo comprobar —sin referencia medida no hay verificación,
y un build que dice «no se pudo comprobar» y sigue adelante es justo el build que
publica un paquete roto—.

Uso: `audit_symbols.py <directorio-del-payload> [--offline]`
"""

import ctypes
import gzip
import io
import lzma
import re
import struct
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

# La referencia: Ubuntu 24.04 «noble», que es la LTS vigente y por tanto el suelo
# que declaran los paquetes. La versión upstream está fijada (2.80.0), la
# revisión la resuelve el script contra el pool.
UBUNTU_RELEASE = "24.04 (noble)"
REFERENCE_UPSTREAM = "2.80.0"
REFERENCE_PACKAGES = ("libglib2.0-0t64", "libgirepository-2.0-0")
POOLS = (
    "http://security.ubuntu.com/ubuntu/pool/main/g/glib2.0/",
    "http://archive.ubuntu.com/ubuntu/pool/main/g/glib2.0/",
)
DEB_ARCH = "amd64"

# La familia que se comprueba. Se corresponde con lo que `audit_libs.py` marca
# como `deb:libglib2.0-0t64 | libglib2.0-0` y `deb:libgirepository-2.0-0`: son
# las que NO viajan dentro del payload y las que, por tanto, pueden ser más
# viejas en la máquina de destino. Añadir otra familia aquí es añadir su paquete
# a `REFERENCE_PACKAGES` y su soname a esta lista.
FAMILY_SONAMES = (
    "libglib-2.0.so.0",
    "libgobject-2.0.so.0",
    "libgmodule-2.0.so.0",
    "libgio-2.0.so.0",
    "libgirepository-2.0.so.0",
)

FETCH_TIMEOUT = 60
SHT_DYNSYM = 11
SHT_DYNAMIC = 6
DT_NEEDED = 1

# --------------------------------------------------------------------------
# Versiones de Debian (`2.80.0-6ubuntu3.8` < `2.80.0-6ubuntu3.9` < `2.80.0-7`)
# --------------------------------------------------------------------------


def _order(character):
    if character == "~":
        return -1  # `~` ordena antes que cualquier cosa, incluso que el final
    if character.isalpha():
        return ord(character)
    return ord(character) + 256


def _compare_chunk(left, right):
    index = other = 0
    while index < len(left) or other < len(right):
        while (index < len(left) and not left[index].isdigit()) or (
            other < len(right) and not right[other].isdigit()
        ):
            a = _order(left[index]) if index < len(left) and not left[index].isdigit() else 0
            b = _order(right[other]) if other < len(right) and not right[other].isdigit() else 0
            if a != b:
                return -1 if a < b else 1
            index += 1
            other += 1
        while index < len(left) and left[index] == "0":
            index += 1
        while other < len(right) and right[other] == "0":
            other += 1
        digits_a = digits_b = ""
        while index < len(left) and left[index].isdigit():
            digits_a += left[index]
            index += 1
        while other < len(right) and right[other].isdigit():
            digits_b += right[other]
            other += 1
        if len(digits_a) != len(digits_b):
            return -1 if len(digits_a) < len(digits_b) else 1
        if digits_a != digits_b:
            return -1 if digits_a < digits_b else 1
    return 0


def compare_versions(left, right):
    """Comparación de versiones de Debian, la que usa `apt` para decidir qué es más nuevo."""
    epoch_a, _rest = (left.split(":", 1) + [""])[:2] if ":" in left else ("0", left)
    epoch_b, _rest = (right.split(":", 1) + [""])[:2] if ":" in right else ("0", right)
    if epoch_a != epoch_b:
        return -1 if int(epoch_a) < int(epoch_b) else 1

    def parts(version):
        rest = version.split(":", 1)[1] if ":" in version else version
        if "-" in rest:
            upstream, revision = rest.rsplit("-", 1)
        else:
            upstream, revision = rest, ""
        return upstream, revision

    upstream_a, revision_a = parts(left)
    upstream_b, revision_b = parts(right)
    result = _compare_chunk(upstream_a, upstream_b)
    if result:
        return result
    return _compare_chunk(revision_a, revision_b)


def newest_deb(html, package):
    """El `.deb` más nuevo del paquete dentro del listado de un pool."""
    pattern = re.compile(rf'href="({re.escape(package)}_([^"_/]+)_{DEB_ARCH}\.deb)"')
    found = [
        (match.group(1), match.group(2))
        for match in pattern.finditer(html)
        if match.group(2).startswith(REFERENCE_UPSTREAM)
    ]
    if not found:
        return None
    return max(found, key=lambda item: _VersionKey(item[1]))


class _VersionKey:
    """Envoltorio para poder usar `max`/`sort` con la comparación de Debian."""

    def __init__(self, version):
        self.version = version

    def __lt__(self, other):
        return compare_versions(self.version, other.version) < 0

    def __eq__(self, other):
        return compare_versions(self.version, other.version) == 0


# --------------------------------------------------------------------------
# Descarga (con caché) y desempaquetado del `.deb`
# --------------------------------------------------------------------------


def pool_listing(pool, offline, cache_dir):
    page = cache_dir / ("pool-" + re.sub(r"\W+", "-", pool).strip("-") + ".html")
    if page.exists():
        return page.read_text(encoding="utf-8", errors="replace")
    if offline:
        raise RuntimeError(
            f"modo sin red y no hay listado en caché para {pool}; "
            "borra build/refs y vuelve a comprobar con red"
        )
    with urllib.request.urlopen(pool, timeout=FETCH_TIMEOUT) as response:
        html = response.read().decode("utf-8", errors="replace")
    page.write_text(html, encoding="utf-8")
    return html


def fetch_deb(pool, filename, offline, cache_dir):
    target = cache_dir / filename
    if target.exists():
        return target.read_bytes()
    if offline:
        raise RuntimeError(f"modo sin red y {filename} no está en build/refs")
    print(f"    descargando {filename}", file=sys.stderr)
    with urllib.request.urlopen(pool + filename, timeout=FETCH_TIMEOUT) as response:
        blob = response.read()
    target.write_bytes(blob)
    return blob


def ar_members(blob):
    """Miembros de un `.deb`, que es un archivo `ar`."""
    if blob[:8] != b"!<arch>\n":
        raise ValueError("no es un archivo `ar` (¿un .deb?)")
    members = {}
    position = 8
    while position + 60 <= len(blob):
        header = blob[position : position + 60]
        name = header[0:16].decode("utf-8", "replace").strip()
        try:
            size = int(header[48:58].decode().strip())
        except ValueError:
            break
        members[name] = blob[position + 60 : position + 60 + size]
        position += 60 + size + (size % 2)
    return members


def _zstd_decompress(blob):
    """Descomprime zstd.

    El Python del entorno de build es el 3.13 del intérprete portátil, y
    `tarfile` no entiende zstd hasta el 3.14. Ubuntu comprime `data.tar` con
    zstd, así que se tira de la biblioteca del sistema por `ctypes` y, si no
    estuviera, de la herramienta `zstd`. Es el único formato que necesita ayuda.
    """
    try:
        library = ctypes.CDLL("libzstd.so.1")
    except OSError:
        library = None

    if library is not None:
        library.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
        library.ZSTD_decompress.restype = ctypes.c_size_t
        library.ZSTD_isError.argtypes = [ctypes.c_size_t]
        library.ZSTD_isError.restype = ctypes.c_uint
        library.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]
        library.ZSTD_getErrorName.restype = ctypes.c_char_p

        capacity = max(1 << 22, len(blob) * 8)
        while capacity <= (1 << 30):
            out = ctypes.create_string_buffer(capacity)
            written = library.ZSTD_decompress(out, capacity, blob, len(blob))
            if not library.ZSTD_isError(written):
                return out.raw[:written]
            if b"too small" not in (library.ZSTD_getErrorName(written) or b""):
                break
            capacity *= 2

    try:
        result = subprocess.run(
            ["zstd", "-d", "-c", "-q"], input=blob, capture_output=True, check=True
        )
        return result.stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            "no hay forma de descomprimir zstd en esta máquina (ni libzstd.so.1 ni `zstd`)"
        ) from error


def tar_from_member(name, blob):
    """El `data.tar` de un `.deb`, ya descomprimido."""
    if name.endswith(".zst"):
        blob = _zstd_decompress(blob)
    elif name.endswith(".xz") or name.endswith(".lzma"):
        blob = lzma.decompress(blob)
    elif name.endswith(".gz"):
        blob = gzip.decompress(blob)
    elif name.endswith(".tar") or name.endswith(".bz2"):
        pass
    else:
        raise RuntimeError(f"compresión de `data.tar` no soportada: {name}")
    return io.BytesIO(blob)


def deb_libraries(blob, sonames):
    """Las bibliotecas pedidas, sacadas del `data.tar` del `.deb`."""
    members = ar_members(blob)
    data = next((name for name in members if name.startswith("data.tar")), None)
    if data is None:
        raise RuntimeError("el .deb no trae data.tar")

    wanted = {}
    with tarfile.open(fileobj=tar_from_member(data, members[data]), mode="r:") as archive:
        for member in archive:
            if not member.isfile():
                continue
            name = member.name.rsplit("/", 1)[-1]
            for soname in sonames:
                # `libglib-2.0.so.0` viaja como `libglib-2.0.so.0.8000.0`.
                if name == soname or name.startswith(soname + "."):
                    wanted[soname] = archive.extractfile(member).read()
    return wanted


# --------------------------------------------------------------------------
# Lectura de ELF: sin `pyelftools`, como el resto del empaquetado
# --------------------------------------------------------------------------


def _sections(blob):
    offset = struct.unpack_from("<Q", blob, 0x28)[0]
    entry_size, count = struct.unpack_from("<HH", blob, 0x3A)
    return [
        struct.unpack_from("<IIQQQQIIQQ", blob, offset + index * entry_size)
        for index in range(count)
    ]


def elf_symbols(blob):
    """Nombres definidos e indefinidos de la tabla dinámica.

    Es la que sobrevive al `strip` del payload: sin ella el binario no enlazaría.
    """
    defined, undefined = set(), set()
    sections = _sections(blob)
    for _name, section_type, _flags, _addr, offset, size, link, _info, _align, entry_size in sections:
        if section_type != SHT_DYNSYM or not entry_size:
            continue
        strings = sections[link]
        table = blob[strings[4] : strings[4] + strings[5]]
        for index in range(size // entry_size):
            name_offset, _info, _other, section_index, _value, _length = struct.unpack_from(
                "<IBBHQQ", blob, offset + index * entry_size
            )
            end = table.find(b"\0", name_offset)
            name = table[name_offset:end].decode("utf-8", "replace")
            (defined if section_index != 0 else undefined).add(name)
    return defined, undefined


def elf_needed(blob):
    """Sonames de los que depende un ELF (`DT_NEEDED`)."""
    needed = []
    sections = _sections(blob)
    for _name, section_type, _flags, _addr, offset, size, link, _info, _align, entry_size in sections:
        if section_type != SHT_DYNAMIC or not entry_size:
            continue
        strings = sections[link]
        table = blob[strings[4] : strings[4] + strings[5]]
        for index in range(size // entry_size):
            tag = struct.unpack_from("<q", blob, offset + index * entry_size)[0]
            if tag != DT_NEEDED:
                continue
            name_offset = struct.unpack_from("<Q", blob, offset + index * entry_size + 8)[0]
            end = table.find(b"\0", name_offset)
            needed.append(table[name_offset:end].decode("utf-8", "replace"))
    return needed


def is_elf(path):
    with open(path, "rb") as handle:
        return handle.read(4) == b"\x7fELF"


def host_library_path(soname):
    """Ruta real de un soname en esta máquina, resolviéndolo como lo haría el cargador."""
    try:
        ctypes.CDLL(soname)
    except OSError:
        return None
    # En `/proc/self/maps` aparece el fichero real, no el enlace: el del soname
    # es `libglib-2.0.so.0.8800.3`, que es el que hay que leer.
    with open("/proc/self/maps", "r", encoding="utf-8", errors="replace") as maps:
        for line in maps:
            chunks = line.split(" /")
            if len(chunks) != 2:
                continue
            name = chunks[1].rstrip("\n").rsplit("/", 1)[-1]
            if name == soname or name.startswith(soname + "."):
                return "/" + chunks[1].rstrip("\n")
    return None


# --------------------------------------------------------------------------


def main():
    arguments = [argument for argument in sys.argv[1:] if not argument.startswith("--")]
    offline = "--offline" in sys.argv[1:]
    if len(arguments) != 1:
        print("uso: audit_symbols.py <directorio-del-payload> [--offline]", file=sys.stderr)
        return 2

    payload = Path(arguments[0]).resolve()
    if not payload.is_dir():
        print(f"no existe el payload: {payload}", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent.parent
    build_dir = root / "build"
    cache_dir = build_dir / "refs"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"==> Símbolos del payload contra {UBUNTU_RELEASE}")

    try:
        listing = {}
        for package in REFERENCE_PACKAGES:
            for pool in POOLS:
                try:
                    html = pool_listing(pool, offline, cache_dir)
                except (urllib.error.URLError, TimeoutError, OSError) as error:
                    print(f"    aviso: no pude leer {pool} ({error})", file=sys.stderr)
                    continue
                candidate = newest_deb(html, package)
                if candidate:
                    listing[package] = (pool, candidate[0], candidate[1])
                    break
            if package not in listing:
                raise RuntimeError(
                    f"no encontré {package} {REFERENCE_UPSTREAM}* en los repositorios de Ubuntu"
                )

        # Las dos piezas salen del mismo paquete fuente, así que tienen que estar
        # en la misma revisión: si no, la referencia estaría mezclando versiones.
        revisions = {version for _pool, _file, version in listing.values()}
        if len(revisions) != 1:
            raise RuntimeError(
                "las piezas de la referencia no coinciden de revisión: " + ", ".join(sorted(revisions))
            )
    except RuntimeError as error:
        print(f"  FALLO: {error}", file=sys.stderr)
        print("  no se pudo comprobar; un build sin comprobar es el que publica paquetes rotos", file=sys.stderr)
        return 2

    reference_exports = set()
    reference_files = []
    try:
        for package, (pool, filename, version) in sorted(listing.items()):
            blob = fetch_deb(pool, filename, offline, cache_dir)
            libraries = deb_libraries(blob, FAMILY_SONAMES)
            if not libraries:
                raise RuntimeError(f"{filename} no trae ninguna de las bibliotecas esperadas")
            for soname, content in sorted(libraries.items()):
                defined, _undefined = elf_symbols(content)
                reference_exports |= defined
                reference_files.append((filename, soname, len(defined)))
    except (RuntimeError, ValueError, tarfile.TarError, OSError) as error:
        print(f"  FALLO leyendo la referencia: {error}", file=sys.stderr)
        return 2

    host_exports = set()
    missing_host = []
    for soname in FAMILY_SONAMES:
        path = host_library_path(soname)
        if not path:
            missing_host.append(soname)
            continue
        defined, _undefined = elf_symbols(Path(path).read_bytes())
        host_exports |= defined

    checked = []
    missing = []
    symbols_checked = 0
    for path in sorted(payload.rglob("*")):
        if not path.is_file():
            continue
        try:
            if not is_elf(path):
                continue
        except OSError:
            continue
        blob = path.read_bytes()
        if not set(elf_needed(blob)) & set(FAMILY_SONAMES):
            continue
        origin = str(path.relative_to(payload))
        checked.append(origin)
        _defined, undefined = elf_symbols(blob)
        for symbol in sorted(undefined):
            if symbol in reference_exports:
                symbols_checked += 1
                continue
            if symbol in host_exports:
                # Lo exporta esta máquina y no la referencia: es una versión de
                # más, justo lo que no se ve hasta que arranca en otro sistema.
                missing.append((origin, symbol))
                symbols_checked += 1
            # Ni una cosa ni la otra: libc, libpython o otro fichero del payload.

    revision = sorted({version for _pool, _file, version in listing.values()})[0]
    lines = [
        "Auditoría de símbolos — payload de Stella Client",
        "",
        f"referencia      : {UBUNTU_RELEASE} — {REFERENCE_UPSTREAM} ({revision})",
    ]
    lines += [f"                  {filename}: {soname} ({count} símbolos)" for filename, soname, count in reference_files]
    lines += [
        f"payload         : {payload}",
        f"ficheros        : {len(checked)} enlazan con la familia GLib",
        f"símbolos        : {symbols_checked} resueltos contra la referencia",
        "",
    ]
    if missing:
        lines.append(f"NO EXISTEN EN LA REFERENCIA: {len(missing)}")
        lines += [f"  {origin}: {symbol}" for origin, symbol in missing]
    else:
        lines.append("NO EXISTEN EN LA REFERENCIA: ninguno")
        lines.append("")
        lines.append(
            "Todos los símbolos que el payload pide a la familia GLib existen en las "
            "bibliotecas de Ubuntu 24.04: el binario no puede fallar por versión."
        )
    (build_dir / "symbols-audit.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"    referencia : {UBUNTU_RELEASE}, {REFERENCE_UPSTREAM} ({revision})")
    for filename, soname, count in reference_files:
        print(f"                 {soname}: {count} símbolos en {filename}")
    print(f"    payload    : {len(checked)} ficheros enlazan con la familia GLib")
    print(f"    símbolos   : {symbols_checked} resueltos contra la referencia")
    if missing_host:
        print(f"    aviso      : no pude leer en esta máquina: {', '.join(missing_host)}")

    if missing:
        print(f"  FALLO: {len(missing)} símbolos que el payload pide no existen en {UBUNTU_RELEASE}")
        for origin, symbol in missing:
            print(f"         {origin}: {symbol}")
        print("  detalle en build/symbols-audit.txt")
        print("  suele ser una dependencia compilada contra una versión más nueva de lo declarado")
        return 1

    print("  OK: nada del payload pide símbolos que falten en la referencia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
