#!/bin/bash
# Punto de entrada único del empaquetado de Stella Client.
#
#   ./build.sh                 payload + .deb + .rpm + AppImage
#   ./build.sh payload         sólo el binario
#   ./build.sh deb rpm         los que pidas (construye el payload si hace falta)
#   ./build.sh check           arranca el payload en frío para comprobarlo
#   ./build.sh --clean         borra los artefactos (deja el entorno de build)
#
# El payload se construye una sola vez y los tres formatos envuelven ese mismo
# directorio. Así no hay manera de publicar un .deb y un AppImage con binarios
# distintos, que es el fallo clásico de tener tres scripts que compilan cada uno
# por su cuenta.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PAYLOAD="$ROOT/dist/app/stella-client"

TARGETS=()

clean_artifacts() {
    rm -rf "$ROOT/dist" \
           "$ROOT/build/pyinstaller" \
           "$ROOT/build/deb" \
           "$ROOT/build/rpm-root" \
           "$ROOT/build/rpmbuild" \
           "$ROOT/build/rpmdb" \
           "$ROOT/build/AppDir"
}

for arg in "$@"; do
    case "$arg" in
        --clean) clean_artifacts ;;
        -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        payload|deb|rpm|appimage|check) TARGETS+=("$arg") ;;
        all) TARGETS=(payload deb rpm appimage) ;;
        *) echo "Objetivo desconocido: $arg (usa payload, deb, rpm, appimage o check)" >&2; exit 2 ;;
    esac
done

if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS=(payload deb rpm appimage)
fi

requires_payload() {
    local t
    for t in "${TARGETS[@]}"; do
        case "$t" in deb|rpm|appimage) return 0 ;; esac
    done
    return 1
}

needs_payload=false
if requires_payload && [ ! -x "$PAYLOAD/stella-client" ]; then
    needs_payload=true
fi

echo "Stella Client $VERSION"
echo "  objetivos: ${TARGETS[*]}"

for target in "${TARGETS[@]}"; do
    case "$target" in
        payload)
            bash "$ROOT/packaging/payload.sh"
            ;;
        deb)
            if [ "$needs_payload" = true ]; then bash "$ROOT/packaging/payload.sh"; needs_payload=false; fi
            bash "$ROOT/packaging/deb.sh"
            ;;
        rpm)
            if [ "$needs_payload" = true ]; then bash "$ROOT/packaging/payload.sh"; needs_payload=false; fi
            bash "$ROOT/packaging/rpm.sh"
            ;;
        appimage)
            if [ "$needs_payload" = true ]; then bash "$ROOT/packaging/payload.sh"; needs_payload=false; fi
            bash "$ROOT/packaging/appimage.sh"
            ;;
        check)
            if [ ! -x "$PAYLOAD/stella-client" ]; then
                echo "==> No hay payload; se construye antes de comprobarlo" >&2
                bash "$ROOT/packaging/payload.sh" >&2
            fi
            echo "==> Comprobación del payload"
            # Sin pantalla el binario valida las librerías; con pantalla, además,
            # crea y cierra la ventana de verdad.
            "$PAYLOAD/stella-client" --check
            ;;
    esac
done

if [ -d "$ROOT/dist/packages" ]; then
    echo
    echo "Artefactos en dist/packages:"
    ls -lh "$ROOT/dist/packages" | awk 'NR>1 { printf "  %-46s %s\n", $9, $5 }'
fi
