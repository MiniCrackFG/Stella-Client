#!/bin/bash
# Construye el AppImage.
#
# El AppDir se monta con packaging/files.sh, el mismo que usan el .deb y el .rpm,
# y encima se le añaden las tres cosas que el formato exige en su raíz: AppRun,
# el .desktop y el icono (más .DirIcon, que es como lo encuentra el escritorio al
# integrarlo).
#
# appimagetool no está instalado en el sistema a propósito: se descarga a
# .build-tools/ para que compilar no obligue a tocar el sistema anfitrión.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
# shellcheck source=files.sh
. "$HERE/files.sh"

NAME="stella-client"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PAYLOAD="$ROOT/dist/app/stella-client"
APPDIR="$ROOT/build/AppDir"
OUTDIR="$ROOT/dist/packages"
TOOL="$ROOT/.build-tools/appimagetool-x86_64.AppImage"

if [ "$(uname -m)" != "x86_64" ]; then
    echo "El AppImage sólo se construye para x86_64 por ahora." >&2
    exit 1
fi

if [ ! -x "$TOOL" ]; then
    echo "Falta appimagetool. Descárgalo con:" >&2
    echo "  mkdir -p .build-tools && curl -fL -o $TOOL \\" >&2
    echo "    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" >&2
    echo "  chmod +x $TOOL" >&2
    exit 1
fi

stella_check_inputs

echo "==> AppImage $VERSION (x86_64)"
stella_install_payload "$APPDIR"

# Lo que el formato pide en la raíz del AppDir.
install -m 0755 "$HERE/AppRun" "$APPDIR/AppRun"
install -m 0644 "$ROOT/assets/stella-client.desktop" "$APPDIR/${NAME}.desktop"
install -m 0644 "$ROOT/assets/icon-256.png" "$APPDIR/${NAME}.png"
ln -sf "${NAME}.png" "$APPDIR/.DirIcon"

mkdir -p "$OUTDIR"
TARGET="$OUTDIR/${NAME}_${VERSION}_x86_64.AppImage"

# `--appimage-extract-and-run` evita depender de FUSE, que no está en todas las
# máquinas (ni en los contenedores donde se verifica esto).
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$TARGET"

echo
echo "==> $(basename "$TARGET")"
echo "    tamaño:  $(du -h "$TARGET" | cut -f1)"
echo "    extraído: $(find "$APPDIR" -type f | wc -l) ficheros en el AppDir"
