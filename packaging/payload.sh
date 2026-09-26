#!/bin/bash
# Construye el payload (binario + _internal/) que comparten .deb, .rpm y AppImage.
#
# Se construye una sola vez y los tres formatos envuelven exactamente lo mismo:
# así no hay forma de que un formato se quede con un binario distinto.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
OUT="$ROOT/dist/app"
WORK="$ROOT/build/pyinstaller"

# buildenv.sh deja el intérprete portátil a punto y devuelve su ruta. Se usa ese
# y no el `.venv` de desarrollo para que el payload no herede la glibc de Arch.
PY="$(bash "$HERE/buildenv.sh")"
if ! "$PY" -c 'import PyInstaller' 2>/dev/null; then
    echo "El entorno de build no tiene PyInstaller: $PY" >&2
    exit 1
fi

echo "==> Payload $VERSION"
echo "    intérprete: $("$PY" -c 'import sys; print(sys.version.split()[0], sys.executable)')"
rm -rf "$OUT" "$WORK"
"$PY" -m PyInstaller \
    --noconfirm \
    --distpath "$OUT" \
    --workpath "$WORK" \
    "$HERE/stella-client.spec"

# La versión viaja con el payload: sin esto no hay forma de saber qué build está
# instalada en un sistema ajeno.
printf '%s\n' "$VERSION" > "$OUT/stella-client/VERSION"

# El Python portátil viene sin strip y su libpython ocupa 230 MB, de los que 200
# son símbolos. Se recortan aquí y no en el spec porque solo afecta a las
# librerías del payload: el ejecutable lo hace PyInstaller por su cuenta.
before=$(du -sb "$OUT/stella-client" | cut -f1)
find "$OUT/stella-client/_internal" -type f -print0 | while IFS= read -r -d '' f; do
    if [ "$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')" = "7f454c46" ]; then
        strip --strip-unneeded "$f" 2>/dev/null || true
    fi
done
after=$(du -sb "$OUT/stella-client" | cut -f1)
awk -v b="$before" -v a="$after" 'BEGIN { printf "    símbolos: %.0f MB menos (%.0f → %.0f MB)\n", (b-a)/1048576, b/1048576, a/1048576 }'

echo "    $OUT/stella-client"
"$PY" "$HERE/audit_libs.py" "$OUT/stella-client"

# Qué pide el payload y qué existe de verdad en Ubuntu 24.04. La 0.2.1 se publicó
# con un `import gi` que no podía funcionar allí por un símbolo (`import` que
# pedía GLib 2.86): el payload se había comprobado sólo en la máquina donde se
# construyó. Esta comprobación es la que faltaba.
"$PY" "$HERE/audit_symbols.py" "$OUT/stella-client"
