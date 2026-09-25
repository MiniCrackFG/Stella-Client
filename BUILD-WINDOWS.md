# Compilar Stella Client en Windows

Esta guía se sigue **desde Windows**, donde no hay agente que pueda ayudar, así que
está escrita para no tener que decidir nada. Al final hay una sección de "si algo
falla" y otra de qué traerme de vuelta.

**Por qué hay que hacerlo aquí y no en Linux:** PyInstaller no cross-compila. Sólo
genera un `.exe` si se ejecuta en Windows. No hay ninguna opción que diga "hazlo
para Windows" desde otra máquina.

**Lo que se instala y por qué:**

| Qué | Para qué | ¿Imprescindible? |
|---|---|---|
| Python 3.13 | Es el intérprete que se empaqueta dentro del `.exe` | Sí |
| Inno Setup 6.3 o superior | Convierte el payload en el instalador `Setup.exe` | Sí, para el instalador |
| Git para Windows | Traer el código | Sólo si no descargas el ZIP |

No hace falta WSL, ni Docker, ni Visual Studio, ni compilador de C: todas las
dependencias vienen ya compiladas como ruedas.

---

## 1. Instalar Python 3.13

1. <https://www.python.org/downloads/> → **Python 3.13.x** → *Windows installer (64-bit)*.
2. En la primera pantalla del instalador, **marca la casilla "Add python.exe to PATH"**. Es la única que importa.
3. Instalar con el resto de opciones por defecto.

Comprueba en PowerShell:

```powershell
py -3.13 --version
```

Tiene que decir `Python 3.13.x`.

> **3.13 y no 3.14.** `pythonnet` —el puente con .NET que pywebview usa en Windows—
> todavía no soporta la 3.14. Si instalas la 3.14, el launcher compila pero la
> ventana no se abre.

## 2. Traer el código

**Con Git** (recomendado, así puedes actualizar):

1. <https://git-scm.com/download/win> → instalar con las opciones por defecto.
2. En PowerShell:

```powershell
cd $HOME
git clone https://github.com/MiniCrackFG/Stella-Client.git
cd Stella-Client
```

La primera vez, si el repositorio es privado, se abrirá una ventana del navegador
para que inicies sesión en GitHub. Es normal.

**Sin Git:** en la página del repositorio, botón verde **Code → Download ZIP**,
y descomprimir en `C:\Stella-Client`. Todo lo demás de esta guía funciona igual.

## 3. Instalar Inno Setup

<https://jrsoftware.org/isdl.php> → *Stable Release* → `innosetup-6.x.x.exe`.

Con las opciones por defecto. **Hace falta la 6.3 o superior** (la directiva
`x64compatible` del script se añadió en esa versión).

## 4. Compilar

En PowerShell, desde la carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

El `-ExecutionPolicy Bypass` es para que Windows no se niegue a ejecutar el script.
Es sólo para esta ejecución, no cambia nada del sistema.

La primera vez tarda unos minutos porque monta el entorno (`.venv-win`) e instala
las dependencias. Las siguientes tarda menos de la mitad.

### Qué hace, en orden

1. **Entorno de build** — crea `.venv-win` con Python 3.13 e instala las dependencias.
2. **Payload** — genera `assets/icon.ico` desde el PNG y empaqueta con PyInstaller en `dist\app\stella-client\`. Dentro quedan `stella-client.exe` (el que ve el jugador), `stella-client-check.exe` (el comprobador, con consola) y `_internal\` con el intérprete y las librerías.
3. **Instalador** — Inno Setup lo envuelve en `dist\packages\StellaClient-Setup-<versión>.exe`.
4. **ZIP portátil** — `dist\packages\StellaClient-<versión>-win64.zip`, para quien no quiera instalar nada.

La `<versión>` de los nombres es la que dice el fichero `VERSION` del repositorio: es
el único sitio donde vive, así que no la busques escrita en ningún script.

Al final imprime los artefactos y su tamaño. Cuenta con **40–60 MB** el instalador.

### Si sólo quieres una parte

```powershell
.\build.ps1 payload       # sólo el binario, sin instalador
.\build.ps1 installer     # sólo el instalador (construye el payload si falta)
.\build.ps1 zip           # sólo el ZIP
.\build.ps1 check         # comprueba el entorno sobre el payload
.\build.ps1 launch        # arranca la interfaz y confirma que sigue en pie
.\build.ps1 --clean       # borra los artefactos
```

## 5. Comprobarlo

Primero lo automático:

```powershell
.\build.ps1 check
```

Eso comprueba el runtime de WebView2 y el puente con .NET, imprime el área de
trabajo de la pantalla y la geometría de ventana guardada (y si esa geometría se
va a usar o se va a abrir centrada), y crea y cierra una ventana de verdad. Si
devuelve error, no instales nada todavía: pásame la salida.

Después, **instala el `Setup.exe` y prueba esto a mano**, que es lo que no se puede
comprobar sin un Windows delante:

- [ ] La ventana abre y se ve la interfaz (no en blanco).
- [ ] La primera vez abre **centrada**.
- [ ] **Recuerda el tamaño y el sitio**: redimensiónala (por un borde o una esquina), ciérrala y vuelve a abrirla; tiene que aparecer con ese tamaño y en ese sitio, no centrada otra vez. La prueba buena es estirarla hasta que ocupe media pantalla, cerrar y abrir.
- [ ] **Si la cierras maximizada**, la próxima vez abre maximizada (y al restaurar vuelve a su tamaño de antes).
- [ ] **□ maximiza dejando la barra de tareas a la vista**: la ventana ocupa la pantalla menos la barra, no la pantalla entera. Al volver del maximizado, deja la ventana donde estaba. El doble clic en la barra de título hace lo mismo.
- [ ] La ventana se puede **redimensionar** arrastrando bordes y esquinas.
- [ ] **La barra de título arrastra la ventana**, y con el ratón el movimiento se ve fluido (sin tirones). Pulsar en los botones no arrastra.
- [ ] En **Account** se ve la cabeza de la skin; si no hay red, el dibujo de reserva. Nunca un icono de imagen rota ni un hueco vacío.
- [ ] La **barra de scroll** de Mods es morada como en Linux, no blanca.
- [ ] Se puede **copiar** algo al portapapeles (por ejemplo el código de inicio de sesión de Microsoft) y pegarlo en otro sitio.
- [ ] **Ajustes → Detectar Java** encuentra tu Java instalado.
- [ ] Al **jugar**, descarga el juego y arranca Minecraft sin una ventana negra de consola detrás.
- [ ] La barra de progreso de abajo aparece mientras descarga.

El registro de todo lo que hace el launcher está en:

```
%LOCALAPPDATA%\StellaClient\logs\stella.log
```

---

## Si algo falla

| Síntoma | Causa | Qué hacer |
|---|---|---|
| "no se puede cargar el archivo build.ps1 porque la ejecución de scripts está deshabilitada" | Política de PowerShell | Es exactamente para lo que está el `-ExecutionPolicy Bypass -File` del paso 4 |
| "No encuentro Python..." | Python no está en el PATH | Reinstala marcando la casilla del PATH, o pásale la ruta: `.\build.ps1 -Python "C:\...\python.exe"` |
| Aviso de que se usa Python 3.14, y al abrir no pasa nada | `pythonnet` no soporta 3.14 | Instala la 3.13 y borra `.venv-win`, o pásale la ruta con `-Python` |
| "No encuentro ISCC.exe" | Inno Setup no instalado o en otra ruta | Instálalo desde <https://jrsoftware.org/isdl.php> |
| "Unknown identifier 'x64compatible'" al compilar el instalador | Inno Setup anterior a la 6.3 | Actualiza Inno Setup |
| El instalador sale, pero al abrir el programa no aparece la ventana | Suele ser el runtime de WebView2 o el puente con .NET | Mira `stella.log`, que ahí está la excepción concreta |
| La ventana abre en un sitio incómodo y no hay forma de dejarla donde quieres | Es la geometría que se recuerda entre sesiones | Cierra el launcher, borra la clave `"window"` de `%LOCALAPPDATA%\StellaClient\config.json` y vuelve a abrirlo |
| La ventana no recuerda el tamaño entre sesiones | Hay una geometría inservible guardada (las versiones anteriores a la 0.2.1 guardaban ceros) | Borra la clave `"window"` de `%LOCALAPPDATA%\StellaClient\config.json` y vuelve a probar: en `stella.log` queda la línea «Geometría de la ventana guardada en …» con lo que se guardó |
| Windows avisa de que "protegió tu PC" | El instalador no está firmado | Es esperado: *Más información → Ejecutar de todas formas*. Se arregla con un certificado de firma, que es dinero y trámite, no código |
| `pip` se queja de PyGObject | No debería: está marcado como sólo para Linux | Mándame el error, porque significa que la marca no está funcionando |

## Cómo traerme la información de vuelta

Al reiniciar en Linux ya vuelvo a estar disponible. Para que pueda arreglar lo que
salga mal necesito una de estas dos cosas, o las dos:

1. **El archivo** `%LOCALAPPDATA%\StellaClient\logs\stella.log` — tiene el registro
   completo con la excepción concreta. Cópialo a un pendrive, o pégame su contenido.
2. **La salida completa de `build.ps1`** — desde el `==> Payload` hasta el final.

## Después de la primera vez

Una vez subido el código a GitHub, el workflow `Windows` compila en una máquina
Windows de GitHub y deja el instalador como artefacto descargable. Se lanza desde
la pestaña *Actions* o publicando una etiqueta `v*`. **A partir de ahí no hace
falta volver a reiniciar** para reconstruir o corregir algo.
