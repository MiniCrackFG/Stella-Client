# Stella Client

![GitHub release (latest by date)](https://img.shields.io/github/v/release/MiniCrackFG/Stella-Client?display_name=tag&style=flat-square)
![GitHub downloads](https://img.shields.io/github/downloads/MiniCrackFG/Stella-Client/total?style=flat-square)
![GitHub Repo stars](https://img.shields.io/github/stars/MiniCrackFG/Stella-Client?style=flat-square)
![GitHub issues](https://img.shields.io/github/issues/MiniCrackFG/Stella-Client?style=flat-square)
![GitHub license](https://img.shields.io/github/license/MiniCrackFG/Stella-Client?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Linux-supported-success?style=flat-square&logo=linux)

<img width="1917" height="1034" alt="image" src="https://github.com/user-attachments/assets/8be878d9-1701-4246-8ca3-dc46a588652e" />

<img width="1917" height="1034" alt="image" src="https://github.com/user-attachments/assets/74f42dda-9130-4eef-9e47-e5e7ab7273ac" />

Un launcher moderno de Minecraft con soporte para mods Fabric, Discord Rich Presence y autenticación de Microsoft y mucho más.

## Características
- 🚀 Lanzamiento de Minecraft vanilla y Fabric
- 📦 Gestión de mods desde Modrinth (búsqueda, descarga, dependencias)
- 👤 Autenticación Microsoft y modo offline
- 🎮 Discord Rich Presence integrado
- ⚡ Múltiples instancias con mods independientes
- 🎨 Interfaz moderna con tema oscuro/light/OLED
- 🔄 Actualización automática del mod Stella Client
- 🖥️ Compatible con VulkanMod

# Instalación

El paquete incluye su propio intérprete de Python; **GTK 3 y WebKitGTK 4.1 los pone la distribución**. Empaquetarlos dentro congelaría su versión y la glibc de la máquina donde se compilan, que es lo que dejaría el binario atado a unas pocas distros.

| Distro | Dependencias |
|---|---|
| Ubuntu 24.04+ / Debian 13+ | `sudo apt install libgtk-3-0t64 libwebkit2gtk-4.1-0 gir1.2-gtk-3.0 gir1.2-webkit2-4.1` |
| Fedora 40+ / RHEL 10 | `sudo dnf install gtk3 webkit2gtk4.1` |
| openSUSE Leap 16 / Tumbleweed | `sudo zypper install gtk3 libwebkit2gtk-4_1-0` |
| Arch / CachyOS / Manjaro | `sudo pacman -S gtk3 webkit2gtk-4.1` |

Con los paquetes `.deb` y `.rpm` no hace falta hacerlo a mano: están declarados como dependencias y el gestor los instala.

**Compatibilidad:** el binario pide `glibc 2.27`, que cualquier distro viva supera con creces, pero lo que marca el suelo real es `libgirepository-2.0` (glib 2.80): Ubuntu 24.04+, Debian 13+, Fedora 40+, openSUSE Leap 16/Tumbleweed y Arch. Ubuntu 22.04 y anteriores quedan fuera, y el instalador lo dice al negarse a resolver las dependencias en vez de fallar al arrancar.

## Desde .deb

```bash
sudo apt install ./stella-client_0.1.0_amd64.deb
```

Con `apt install ./fichero.deb` (en vez de `dpkg -i`) se resuelven solas las dependencias.

## Desde .rpm

```bash
sudo dnf install ./stella-client-0.1.0-1.x86_64.rpm      # Fedora, RHEL
sudo zypper install ./stella-client-0.1.0-1.x86_64.rpm  # openSUSE
```

## Desde AppImage

```bash
chmod +x stella-client_0.1.0_x86_64.AppImage
./stella-client_0.1.0_x86_64.AppImage
```

El AppImage no necesita instalación, pero sí tener GTK 3 y WebKitGTK 4.1 en el sistema.

# Compilar los paquetes

```bash
./build.sh                 # payload + .deb + .rpm + AppImage  ->  dist/packages/
./build.sh payload         # sólo el binario
./build.sh deb rpm         # los formatos que pidas
./build.sh check           # arranca el payload para comprobarlo
./build.sh --clean
```

El payload se construye **una sola vez** y los tres formatos envuelven exactamente ese mismo directorio: así no puede salir un `.deb` y un AppImage con binarios distintos.

Hace falta, además de las herramientas habituales:

- `dpkg-deb` (paquete `dpkg`) y `rpmbuild` (paquete `rpm-tools`) para los paquetes nativos.
- `appimagetool` en `.build-tools/` para el AppImage. Si no está, el script dice cómo descargarlo.
- Nada más: el intérprete con el que se compila se descarga solo a `.build-tools/` y el entorno se monta en `build/buildenv`.

**Por qué no se compila con el Python del sistema:** los módulos del intérprete de Arch se compilan contra su glibc y su `math` pide `GLIBC_2.44`, así que el binario resultante sólo arrancaría en Arch y derivados. El Python portátil de [python-build-standalone](https://github.com/astral-sh/python-build-standalone) se compila contra glibc 2.17, y con él el mismo payload sirve en todas las distros modernas.

Cada build imprime una auditoría del payload (`packaging/audit_libs.py`) que comprueba dos cosas: que no se haya colado ninguna librería gráfica dentro, y qué librerías de fuera hacen falta de verdad. De ahí salen, medidas y no escritas a mano, las dependencias del `.deb` y del `.rpm`.

## 📄 Licencia
Este proyecto está bajo la licencia MIT.
