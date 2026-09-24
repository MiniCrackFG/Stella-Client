# Coloca el payload y los ficheros auxiliares dentro del árbol de un paquete.
#
# Lo comparten el .deb y el .rpm a propósito: si el layout se define en un solo
# sitio, los dos formatos no pueden acabar con árboles distintos ni con un icono
# instalado en una ruta y en otra no.
#
# Layout:
#   /usr/lib/stella-client/        payload completo (binario, _internal/, VERSION)
#   /usr/lib/stella-client/stella-client-run   lanzador
#   /usr/bin/stella-client          enlace simbólico al lanzador
#   /usr/share/applications/stella-client.desktop
#   /usr/share/icons/hicolor/<N>x<N>/apps/stella-client.png
#   /usr/share/licenses/stella-client/LICENSE
#
# El payload NO va en /usr/lib/<distro> ni mezclado con el resto del sistema: su
# _internal/ es un árbol privado y así queda claro que se puede borrar entero.

stella_install_payload() {
    local root="$1"
    local lib="$root/usr/lib/stella-client"
    local appdir="$root/usr/share/applications"
    local licensedir="$root/usr/share/licenses/stella-client"
    local icondir="$root/usr/share/icons/hicolor"

    rm -rf "$root"
    mkdir -p "$lib" "$appdir" "$licensedir" "$root/usr/bin"

    cp -a "$PAYLOAD/." "$lib/"
    install -m 0755 "$ROOT/packaging/stella-client-run" "$lib/stella-client-run"
    install -m 0644 "$ROOT/assets/stella-client.desktop" "$appdir/stella-client.desktop"
    install -m 0644 "$ROOT/LICENSE" "$licensedir/LICENSE"

    mkdir -p "$icondir/64x64/apps" "$icondir/128x128/apps" "$icondir/256x256/apps" "$icondir/512x512/apps"
    install -m 0644 "$ROOT/assets/icon-64.png" "$icondir/64x64/apps/stella-client.png"
    install -m 0644 "$ROOT/assets/icon-128.png" "$icondir/128x128/apps/stella-client.png"
    install -m 0644 "$ROOT/assets/icon-256.png" "$icondir/256x256/apps/stella-client.png"
    install -m 0644 "$ROOT/assets/icon.png" "$icondir/512x512/apps/stella-client.png"

    ln -sf "../lib/stella-client/stella-client-run" "$root/usr/bin/stella-client"
}

# Comprobaciones que deben pasar los dos formatos antes de empaquetar nada.
stella_check_inputs() {
    if [ ! -x "$PAYLOAD/stella-client" ]; then
        echo "No hay payload. Constrúyelo primero:  ./build.sh payload" >&2
        exit 1
    fi
    if ! command -v desktop-file-validate >/dev/null 2>&1; then
        echo "Falta desktop-file-validate (paquete desktop-file-utils)." >&2
        exit 1
    fi
    if ! desktop-file-validate "$ROOT/assets/stella-client.desktop"; then
        echo "El .desktop no pasa la validación; no se empaqueta." >&2
        exit 1
    fi
}
