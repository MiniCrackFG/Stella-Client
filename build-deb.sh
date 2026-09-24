#!/bin/bash
# Este script está retirado: la receta del .deb vive ahora en packaging/deb.sh,
# junto a la del .rpm y la del AppImage, y se gobierna desde ./build.sh
#
# Antes eran dos recetas distintas (esta y main.spec) que podían divergir sin que
# nadie se enterara: de hecho esta fijaba a mano `Depends:` mientras el spec lo
# hacía a su manera. Ahora las dependencias de los dos formatos salen de la misma
# auditoría medida sobre el payload (build/depends-deb.txt y build/requires-rpm.txt).
#
# Se conserva como aviso para que quien lo llame por costumbre acabe en el sitio
# bueno en vez de en un error.
set -euo pipefail

echo "build-deb.sh está retirado. Usa:" >&2
echo "  ./build.sh deb        # el .deb" >&2
echo "  ./build.sh            # payload + .deb + .rpm + AppImage" >&2
exit 1
