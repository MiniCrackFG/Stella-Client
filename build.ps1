<#
Punto de entrada del empaquetado de Stella Client en Windows.

    .\build.ps1                 payload + instalador + ZIP
    .\build.ps1 payload         sólo el binario
    .\build.ps1 installer       instalador (construye el payload si hace falta)
    .\build.ps1 zip             ZIP portátil (idem)
    .\build.ps1 check           comprueba el entorno sobre el payload (sirve en CI)
    .\build.ps1 launch          arranca la interfaz y confirma que sigue en pie
    .\build.ps1 --clean         borra los artefactos (deja el entorno de build)
    .\build.ps1 -Python <ruta>  usa otro intérprete para montar el entorno

Si PowerShell se niega a ejecutarlo por la política de scripts, se lanza así:

    powershell -ExecutionPolicy Bypass -File build.ps1

Hace deliberadamente el mismo trabajo que build.sh en Linux y con los mismos
nombres: el payload se construye una sola vez y el instalador y el ZIP envuelven
exactamente ese mismo directorio, así que no puede salir un instalador con un
binario distinto del que se acaba de comprobar.
#>
$ErrorActionPreference = "Stop"

# --- Argumentos ----------------------------------------------------------
#
# Sin bloque param() a propósito. Con param() + [CmdletBinding()] el enlazador
# de PowerShell se quedaba con el primer objetivo: al declarar $Targets como
# [Parameter(ValueFromRemainingArguments)] y tener $Python al lado, `payload`
# acababa dentro de $Python, y el script intentaba montar el entorno con
# "payload" como si fuera un intérprete —lo que reventaba justo en integración
# continua, que es el único sitio donde se pasan objetivos por línea de
# órdenes—. Sin param() nada se reordena: los argumentos llegan a $args tal
# cual y aquí se separan.
$Targets = @()

# Intérprete con el que montar el entorno de build. Por defecto se busca
# Python 3.13, que es la versión que soporta pythonnet.
$Python = ""

$index = 0
while ($index -lt $args.Count) {
    $argument = [string]$args[$index]
    $index++
    if ($argument -match '^-{1,2}python$') {
        if ($index -ge $args.Count) {
            throw "Falta la ruta del intérprete después de -Python"
        }
        $Python = [string]$args[$index]
        $index++
    } elseif ($argument -match '^-{1,2}python=(.+)$') {
        $Python = $Matches[1]
    } else {
        $Targets += $argument
    }
}

$Root = $PSScriptRoot
$Version = (Get-Content -Raw (Join-Path $Root "VERSION")).Trim()

# Igual que en Linux: el payload en dist\app y los entregables en dist\packages.
$AppDir = Join-Path $Root "dist\app"
$Payload = Join-Path $AppDir "stella-client"
$Packages = Join-Path $Root "dist\packages"
$Work = Join-Path $Root "build\pyinstaller"
$VenvDir = Join-Path $Root ".venv-win"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $Root "packaging\requirements-win.txt"

$Checks = Join-Path $Payload "stella-client-check.exe"
$GuiExe = Join-Path $Payload "stella-client.exe"


function Show-Usage {
    Write-Host "Uso: .\build.ps1 [objetivos...] [-Python <ruta>]"
    Write-Host ""
    Write-Host "Sin objetivos hace payload + installer + zip. Los objetivos son:"
    Write-Host "  payload           sólo el binario"
    Write-Host "  installer         instalador (construye el payload si hace falta)"
    Write-Host "  zip               ZIP portátil (idem)"
    Write-Host "  check             comprueba el entorno sobre el payload"
    Write-Host "  launch            arranca la interfaz y confirma que sigue en pie"
    Write-Host "  --clean           borra los artefactos (deja el entorno de build)"
    Write-Host ""
    Write-Host "-Python <ruta> usa otro intérprete para montar el entorno."
}


function Clean-Artifacts {
    # No se toca .venv-win: al igual que build.sh conserva su entorno de build,
    # esto conserva el suyo, que tarda más en montarse que el payload en salir.
    foreach ($relative in @("dist", "build\pyinstaller", "build\windows")) {
        $path = Join-Path $Root $relative
        if (Test-Path $path) {
            Write-Host "    borrando $relative"
            Remove-Item -Recurse -Force $path
        }
    }
}


function Get-SystemPython {
    if ($Python) {
        # Puede ser una ruta o un nombre que esté en el PATH (`py`). Si no es
        # ninguna de las dos cosas, es un error claro en vez de un
        # "The term '...' is not recognized" tres pasos más adelante.
        if (-not (Test-Path $Python) -and -not (Get-Command $Python -ErrorAction SilentlyContinue)) {
            throw "No encuentro el intérprete indicado con -Python: $Python"
        }
        return $Python
    }
    # `py` es el lanzador oficial y permite pedir la versión exacta. Se prefiere
    # 3.13 porque pythonnet —el puente con .NET que pywebview necesita en
    # Windows— no soporta todavía la 3.14.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $found = & py -3.13 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) {
            return $found.Trim()
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidate = & python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            $candidate = $candidate.Trim()
            $short = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            if ($short.Trim() -ne "3.13") {
                Write-Warning ("Se usa Python " + $short.Trim() + ", no 3.13. Si pywebview falla al cargar el puente con .NET, la causa es ésta.")
            }
            return $candidate
        }
    }
    throw "No encuentro Python. Instala Python 3.13 desde https://www.python.org/downloads/ marcando 'Add python.exe to PATH', o pásame su ruta con -Python."
}


function Initialize-BuildEnv {
    if (-not (Test-Path $VenvPython)) {
        $base = Get-SystemPython
        Write-Host "==> Creando el entorno de build en .venv-win"
        Write-Host "    intérprete: $base"
        & $base -m venv $VenvDir
        & $VenvPython -m pip install --quiet --upgrade pip
    }
    # Se ejecuta siempre: cuando ya está todo instalado tarda un par de segundos,
    # y a cambio cambiar requirements-win.txt nunca deja un entorno a medias.
    & $VenvPython -m pip install --quiet -r $Requirements
}


function Build-Payload {
    Initialize-BuildEnv

    Write-Host "==> Payload $Version"
    Write-Host "    intérprete: $(& $VenvPython -c 'import sys; print(sys.version.split()[0], sys.executable)')"

    # El .ico se genera aquí: PyInstaller no lo hace, y si le llega un PNG no
    # falla pero deja el ejecutable sin icono. Inno Setup sí lo exige.
    & $VenvPython (Join-Path $Root "packaging\windows\make-ico.py")
    if ($LASTEXITCODE -ne 0) { throw "No se pudo generar assets\icon.ico" }

    foreach ($path in @($Payload, $Work)) {
        if (Test-Path $path) { Remove-Item -Recurse -Force $path }
    }

    & $VenvPython -m PyInstaller `
        --noconfirm `
        --distpath $AppDir `
        --workpath $Work `
        (Join-Path $Root "packaging\stella-client-win.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }

    # La versión viaja con el payload: sin esto no hay forma de saber qué build
    # está instalada en un equipo ajeno. En ASCII para no colar un BOM.
    Set-Content -Path (Join-Path $Payload "VERSION") -Value $Version -Encoding ascii

    $size = (Get-ChildItem -Recurse -File $Payload | Measure-Object -Property Length -Sum).Sum
    Write-Host ("    {0}  ({1:N0} MB)" -f $Payload, ($size / 1MB))
}


function Find-Iscc {
    $candidates = @()
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe") }
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe") }
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw "No encuentro ISCC.exe. Instala Inno Setup 6 desde https://jrsoftware.org/isdl.php"
}


function Build-Installer {
    if (-not (Test-Path $GuiExe)) {
        throw "No hay payload. Constrúyelo primero:  .\build.ps1 payload"
    }
    New-Item -ItemType Directory -Force -Path $Packages | Out-Null
    $iscc = Find-Iscc
    Write-Host "==> Instalador $Version"
    & $iscc `
        "/DMyAppVersion=$Version" `
        "/DRepoDir=$Root" `
        "/DBuildDir=$Payload" `
        "/DOutputDir=$Packages" `
        (Join-Path $Root "packaging\windows\stella-client.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
}


function Build-Zip {
    if (-not (Test-Path $GuiExe)) {
        throw "No hay payload. Constrúyelo primero:  .\build.ps1 payload"
    }
    New-Item -ItemType Directory -Force -Path $Packages | Out-Null
    $zip = Join-Path $Packages "StellaClient-$Version-win64.zip"
    Write-Host "==> ZIP portátil $Version"
    # Comprime la carpeta entera, así que al descomprimir queda todo junto dentro
    # de stella-client\ y no suelto por medio del escritorio.
    Compress-Archive -Path $Payload -DestinationPath $zip -Force
}


function Test-Payload {
    if (-not (Test-Path $Checks)) {
        throw "No hay payload. Constrúyelo primero:  .\build.ps1 payload"
    }
    Write-Host "==> Comprobación del payload"
    # Sin sesión interactiva comprueba el runtime de WebView2 y el puente con
    # .NET; con ella, además, crea y cierra una ventana de verdad. Devuelve
    # distinto de cero si falta algo, así que sirve de puerta en integración
    # continua, donde no hay escritorio.
    & $Checks
    if ($LASTEXITCODE -ne 0) {
        throw "La comprobación del entorno devolvió $LASTEXITCODE"
    }
}


function Start-Launcher {
    if (-not (Test-Path $GuiExe)) {
        throw "No hay payload. Constrúyelo primero:  .\build.ps1 payload"
    }
    Write-Host "==> Arrancando la interfaz gráfica (se cierra sola en unos segundos)"
    # Esto es lo único que no cubre `check`: que la ventana de verdad se quede
    # abierta. Si el proceso muere enseguida, casi siempre es una excepción al
    # crear la ventana, y el rastro está en el registro.
    $process = Start-Process -FilePath $GuiExe -PassThru
    Start-Sleep -Seconds 8
    if ($process.HasExited) {
        throw "El launcher se cerró solo a los pocos segundos. Mira %LOCALAPPDATA%\StellaClient\logs\stella.log"
    }
    $process.Kill()
    Write-Host "    la ventana se mantuvo abierta"
}


# --- Objetivos -----------------------------------------------------------

if (-not $Targets -or $Targets.Count -eq 0) {
    $Targets = @("payload", "installer", "zip")
}
if ($Targets -contains "all") {
    $Targets = @("payload", "installer", "zip")
}
if ($Targets -contains "-h" -or $Targets -contains "--help" -or $Targets -contains "help") {
    Show-Usage
    exit 0
}

# Se imprime a propósito: si algún día un objetivo se pierde por el camino,
# esto lo deja ver en el registro antes de que falle nada.
Write-Host ("==> Objetivos: {0}" -f ($Targets -join " "))

foreach ($target in $Targets) {
    switch ($target) {
        "--clean" { Clean-Artifacts }
        "payload" { Build-Payload }
        "installer" {
            if (-not (Test-Path $GuiExe)) { Build-Payload }
            Build-Installer
        }
        "zip" {
            if (-not (Test-Path $GuiExe)) { Build-Payload }
            Build-Zip
        }
        "check" {
            if (-not (Test-Path $Checks)) { Build-Payload }
            Test-Payload
        }
        "launch" {
            if (-not (Test-Path $GuiExe)) { Build-Payload }
            Start-Launcher
        }
        default { throw "Objetivo desconocido: $target (usa payload, installer, zip, check, launch o --clean)" }
    }
}

if (Test-Path $Packages) {
    Write-Host ""
    Write-Host "Artefactos en dist\packages:"
    Get-ChildItem -File $Packages | Sort-Object Name | ForEach-Object {
        Write-Host ("  {0,-46} {1,6:N1} MB" -f $_.Name, ($_.Length / 1MB))
    }
}
