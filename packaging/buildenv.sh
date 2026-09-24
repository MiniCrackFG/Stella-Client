#!/bin/bash
# Prepara el intérprete con el que se construye el payload e imprime su ruta.
#
# NO se usa el Python de la distro, y no es un capricho: los módulos del
# intérprete que trae Arch se compilan contra su glibc, y su `math` pide
# GLIBC_2.44 (por `cosh`/`sinh`). Un payload construido con él sólo arranca en
# Arch y derivados, por muchas librerías que se le metan dentro: el que las mete
# arrastra su propia glibc.
#
# El Python portátil de python-build-standalone se compila contra glibc 2.17, así
# que el mismo payload arranca en cualquier distro moderna y en bastantes
# antiguas. La versión y la etiqueta están fijadas aquí a propósito: un
# intérprete que cambia solo es un build que deja de ser reproducible.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"

PYTHON_TAG="20260901"
PYTHON_VERSION="3.13.15"
PYTHON_SHORT="3.13"
TARBALL="cpython-${PYTHON_VERSION}+${PYTHON_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_TAG}/${TARBALL}"

TOOLS="$ROOT/.build-tools"
PREFIX="$TOOLS/python"
BUILDENV="$ROOT/build/buildenv"

if [ "$(uname -m)" != "x86_64" ]; then
    echo "Este empaquetado sólo está preparado para x86_64 (esta máquina es $(uname -m))." >&2
    exit 1
fi

if [ ! -x "$PREFIX/bin/python${PYTHON_SHORT}" ]; then
    echo "==> Descargando Python portátil ${PYTHON_VERSION} (glibc 2.17)" >&2
    mkdir -p "$TOOLS"
    if [ ! -f "$TOOLS/$TARBALL" ]; then
        curl -fL --retry 3 -o "$TOOLS/$TARBALL" "$URL"
    fi
    tar -xzf "$TOOLS/$TARBALL" -C "$TOOLS"
fi

if [ ! -x "$BUILDENV/bin/python" ]; then
    echo "==> Creando el entorno de build en build/buildenv" >&2
    "$PREFIX/bin/python${PYTHON_SHORT}" -m venv "$BUILDENV"
    "$BUILDENV/bin/python" -m pip install --quiet --upgrade pip
    "$BUILDENV/bin/python" -m pip install --quiet -r "$HERE/requirements-build.txt"
fi

printf '%s\n' "$BUILDENV/bin/python"
