#!/bin/bash
# Construye el paquete .deb.
#
# El payload es el mismo que usan el .rpm y el AppImage; aquí solo se le pone el
# envoltorio de Debian. Las dependencias no están escritas a mano: salen de
# `build/depends-deb.txt`, que genera la auditoría midiendo el payload con ldd
# más las que se cargan en caliente por typelib (GTK y WebKitGTK, que en `ldd` no
# aparecen nunca).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
# shellcheck source=files.sh
. "$HERE/files.sh"

NAME="stella-client"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PAYLOAD="$ROOT/dist/app/stella-client"
STAGE="$ROOT/build/deb/${NAME}_${VERSION}"
OUTDIR="$ROOT/dist/packages"
DEPS_FILE="$ROOT/build/depends-deb.txt"

case "$(uname -m)" in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    *) ARCH="$(uname -m)" ;;
esac

command -v dpkg-deb >/dev/null 2>&1 || { echo "Falta dpkg-deb (paquete dpkg)." >&2; exit 1; }
stella_check_inputs
if [ ! -f "$DEPS_FILE" ]; then
    echo "Falta $DEPS_FILE. Ejecuta antes:  ./build.sh payload" >&2
    exit 1
fi

echo "==> Paquete .deb $VERSION ($ARCH)"
stella_install_payload "$STAGE"

# Las dependencias en varias líneas se leen mejor en `apt show` y en el propio
# fichero de control.
DEPS="$(sed 's/^ //' "$DEPS_FILE" | tr -d '\n')"
INSTALLED_KIB="$(du -sk "$STAGE" | cut -f1)"

mkdir -p "$STAGE/DEBIAN"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: ${NAME}
Version: ${VERSION}
Section: games
Priority: optional
Architecture: ${ARCH}
Depends: ${DEPS}
Installed-Size: ${INSTALLED_KIB}
Maintainer: Ivan <ivan@stellaclient.dev>
Homepage: https://github.com/MiniCrackFG/Stella-Client
Description: Stella Client - launcher de Minecraft
 Launcher de Minecraft para Linux con soporte de mods Fabric, multiples
 instancias, Discord Rich Presence y autenticacion de Microsoft.
 .
 Incluye su propio interprete de Python y deja GTK y WebKitGTK a la distro,
 asi que funciona en cualquier distribucion moderna sin fijar su version.
EOF

mkdir -p "$OUTDIR"
# -Zxz: la compresion xz es la mas compatible entre versiones de dpkg.
# --root-owner-group evita depender de fakeroot para que los ficheros vayan a root.
dpkg-deb --build --root-owner-group -Zxz "$STAGE" "$OUTDIR/${NAME}_${VERSION}_${ARCH}.deb"

echo
echo "==> ${NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --info "$OUTDIR/${NAME}_${VERSION}_${ARCH}.deb" | sed -n '1,20p'
echo "    contenido: $(dpkg-deb --contents "$OUTDIR/${NAME}_${VERSION}_${ARCH}.deb" | wc -l) entradas"
echo "    tamaño:    $(du -h "$OUTDIR/${NAME}_${VERSION}_${ARCH}.deb" | cut -f1)"
