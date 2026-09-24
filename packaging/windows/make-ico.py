"""Genera `assets/icon.ico` a partir del PNG grande del proyecto.

Windows exige un `.ico`: PyInstaller, si le das un PNG, no falla pero deja el
ejecutable sin icono, y el instalador de Inno Setup directamente no lo acepta. Se
genera durante el build en vez de versionarlo porque es un derivado: si el PNG
cambia, el `.ico` se quedaría viejo sin que nadie se entere.

Dentro del mismo fichero van varios tamaños, que es lo que hace que el icono se
vea nítido en la barra de tareas, en el explorador y en el instalador. Pillow ya
es dependencia del proyecto, así que no hace falta nada más.
"""

import sys
from pathlib import Path

from PIL import Image

# Los tamaños que Windows acaba pidiendo: 16 para el explorador, 32 para la barra
# de tareas, 48 y 256 para el escritorio y las vistas grandes.
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    repo = Path(__file__).resolve().parents[2]
    source = repo / "assets" / "icon.png"
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "assets" / "icon.ico"

    if not source.is_file():
        print(f"No encuentro el icono de origen: {source}", file=sys.stderr)
        return 1

    image = Image.open(source).convert("RGBA")
    # Nunca se agranda: un tamaño mayor que el original se vería borroso dentro
    # del .ico y ocuparía sin aportar nada.
    sizes = [size for size in SIZES if size[0] <= image.width]
    if not sizes:
        sizes = [SIZES[0]]

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="ICO", sizes=sizes)
    print(f"{destination}  ({image.width}x{image.height}, tamaños: "
          + ", ".join(str(size[0]) for size in sizes) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
