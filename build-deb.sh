#!/bin/bash
set -e

NAME="stella-client"
VERSION="0.1.0"
ARCH="amd64"
ROOT="/tmp/${NAME}-debroot"

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN"
mkdir -p "$ROOT/usr/bin"
mkdir -p "$ROOT/usr/share/applications"
mkdir -p "$ROOT/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$ROOT/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$ROOT/usr/share/${NAME}"

echo "Package: ${NAME}
Version: ${VERSION}
Section: games
Priority: optional
Architecture: ${ARCH}
Depends: libgtk-3-0, libwebkit2gtk-4.1-0, libjavascriptcoregtk-4.1-0, libgirepository1.0-dev, gobject-introspection, gir1.2-gtk-3.0
Maintainer: Ivan <ivan@stellaclient.dev>
Description: Stella Client - Minecraft Launcher
 A modern Minecraft launcher with Fabric mod support,
 Discord Rich Presence, and Microsoft account authentication." > "$ROOT/DEBIAN/control"

# Copy the PyInstaller binary
cp "dist/${NAME}" "$ROOT/usr/bin/${NAME}"

# Write proper desktop file
echo "[Desktop Entry]
Name=Stella Client
Comment=Minecraft Launcher
Exec=${NAME}
Icon=${NAME}
Terminal=false
Type=Application
Categories=Game;Utility;
StartupNotify=true" > "$ROOT/usr/share/applications/${NAME}.desktop"

# Copy icons
cp assets/icon-64.png "$ROOT/usr/share/icons/hicolor/64x64/apps/${NAME}.png"
cp assets/icon-128.png "$ROOT/usr/share/icons/hicolor/128x128/apps/${NAME}.png"
cp assets/icon-256.png "$ROOT/usr/share/icons/hicolor/256x256/apps/${NAME}.png"

# Copy jar if exists
if [ -f "dist/${NAME}.jar" ]; then
    cp "dist/${NAME}.jar" "$ROOT/usr/share/${NAME}/${NAME}.jar"
fi

# Build .deb
dpkg-deb --build "$ROOT" "dist/${NAME}_${VERSION}_${ARCH}.deb"

rm -rf "$ROOT"
echo "Built dist/${NAME}_${VERSION}_${ARCH}.deb"
