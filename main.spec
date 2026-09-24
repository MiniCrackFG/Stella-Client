# -*- mode: python ; coding: utf-8 -*-
"""Receta retirada.

La de PyInstaller vive ahora en `packaging/stella-client.spec`, y la usan tanto
`./build.sh payload` como los tres empaquetadores (.deb, .rpm y AppImage), que
envuelven el mismo payload.

Se retiró por un motivo concreto: este fichero está en `.gitignore` (`*.spec`),
así que era imposible versionarlo, y tener una segunda receta viva al lado de la
buena es una forma segura de que alguien construya un binario distinto sin
enterarse. La ruta relativa del icono que se arregló aquí está incorporada en la
receta nueva.

Se deja el fichero para que quien ejecute `pyinstaller main.spec` por costumbre
reciba esta explicación en vez de un binario con una receta vieja.
"""

raise SystemExit(__doc__)
