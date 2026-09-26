#!/bin/bash
# Construye el paquete .rpm.
#
# Mismo payload que el .deb y el AppImage. Dos cosas se hacen a propósito y
# conviene no "arreglarlas" sin pensar:
#
# - `AutoReqProv: no` en el spec, porque si no rpmbuild pide los .so que el
#   propio paquete lleva dentro y el RPM queda ininstalable.
# - Las dependencias van por soname (`libgtk-3.so.0()(64bit)`,
#   `libwebkit2gtk-4.1.so.0()(64bit)`), que es lo único que direccionan igual Fedora,
#   RHEL y openSUSE. NO por `typelib(...)` (provided sólo de openSUSE, que hace
#   abortar a dnf en Fedora) ni por nombre de paquete, que cambia por familia.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
# shellcheck source=files.sh
. "$HERE/files.sh"

NAME="stella-client"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PAYLOAD="$ROOT/dist/app/stella-client"
STAGE="$ROOT/build/rpm-root"
TOPDIR="$ROOT/build/rpmbuild"
OUTDIR="$ROOT/dist/packages"
REQUIRES_FILE="$ROOT/build/requires-rpm.txt"
# rpm se empeña en abrir su base de datos del sistema hasta para consultar un
# fichero .rpm suelto, y en Arch esa base no existe. Con un dbpath propio,
# dentro del árbol de build, no hace falta tenerla.
RPMDB="$ROOT/build/rpmdb"

command -v rpmbuild >/dev/null 2>&1 || { echo "Falta rpmbuild (paquete rpm-tools)." >&2; exit 1; }
stella_check_inputs
if [ ! -f "$REQUIRES_FILE" ]; then
    echo "Falta $REQUIRES_FILE. Ejecuta antes:  ./build.sh payload" >&2
    exit 1
fi

echo "==> Paquete .rpm $VERSION (x86_64)"
stella_install_payload "$STAGE"

rm -rf "$TOPDIR"
mkdir -p "$TOPDIR/BUILD" "$TOPDIR/RPMS" "$TOPDIR/SOURCES" "$TOPDIR/SPECS" "$TOPDIR/SRPMS"

SPEC="$TOPDIR/SPECS/${NAME}.spec"
sed -e "s/@VERSION@/${VERSION}/" \
    -e "/@REQUIRES@/r ${REQUIRES_FILE}" \
    -e "/@REQUIRES@/d" \
    "$HERE/stella-client.spec.in" > "$SPEC"

mkdir -p "$RPMDB"
rpmbuild -bb "$SPEC" \
    --define "_topdir ${TOPDIR}" \
    --define "_payload ${STAGE}" \
    --define "_dbpath ${RPMDB}" \
    --target x86_64 \
    --quiet

mkdir -p "$OUTDIR"
BUILT="$(find "$TOPDIR/RPMS" -name '*.rpm' -type f | head -1)"
if [ -z "$BUILT" ]; then
    echo "rpmbuild no produjo ningún paquete." >&2
    exit 1
fi
cp "$BUILT" "$OUTDIR/"

RPM="$OUTDIR/$(basename "$BUILT")"
rpmq() { rpm --dbpath "$RPMDB" "$@"; }

echo
echo "==> $(basename "$RPM")"
rpmq -qp --queryformat '    nombre:     %{NAME}\n    version:    %{VERSION}-%{RELEASE}\n    arquitectura: %{ARCH}\n    tamano:     %{SIZE} bytes\n' "$RPM"
echo "    dependencias: $(rpmq -qp --requires "$RPM" | wc -l)"
echo "    ficheros:     $(rpmq -qpl "$RPM" | wc -l)"
echo "    tamano rpm:   $(du -h "$RPM" | cut -f1)"
