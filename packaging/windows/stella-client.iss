; Instalador de Stella Client para Windows.
;
; No se compila a mano: lo llama `build.ps1` y le pasa tres datos por la línea de
; órdenes para que `VERSION` siga siendo el único sitio donde vive la versión.
;
;   /DMyAppVersion=<versión de VERSION>
;   /DRepoDir=<ruta absoluta del repositorio>
;   /DBuildDir=<ruta absoluta del payload>
;   /DOutputDir=<ruta absoluta donde dejar el Setup.exe>
;
; Se instala por usuario, en %LOCALAPPDATA%\Programs: así no hace falta ser
; administrador, y los datos del juego quedan en la misma cuenta que los ajustes.
;
; **El desinstalador no toca la carpeta de datos** (%LOCALAPPDATA%\StellaClient).
; Ahí están las cuentas, los ajustes y los gigas de juego ya descargados, y
; desinstalar el launcher no es motivo para borrarlos. Si algún día se quiere
; ofrecer esa opción, que sea preguntando y por defecto en "no".

#ifndef MyAppVersion
  #error Falta /DMyAppVersion. Compílalo con build.ps1, no a mano.
#endif
#ifndef RepoDir
  #error Falta /DRepoDir. Compílalo con build.ps1, no a mano.
#endif
#ifndef BuildDir
  #error Falta /DBuildDir. Compílalo con build.ps1, no a mano.
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define MyAppName "Stella Client"
#define MyAppExeName "stella-client.exe"
#define MyAppPublisher "miniloopp"
#define MyAppUrl "https://github.com/MiniCrackFG/Stella-Client"

[Setup]
; El AppId es lo que hace que Windows reconozca esta instalación como la misma
; aplicación al actualizar, en vez de instalar una segunda copia al lado. No se
; cambia nunca, ni aunque cambie el nombre visible.
AppId={{8E4B1F52-6C7A-4D3E-9A21-5B7C0D9E4F31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppUrl}
AppSupportURL={#MyAppUrl}
AppUpdatesURL={#MyAppUrl}
VersionInfoVersion={#MyAppVersion}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Sólo hay build de 64 bits: el payload lleva un intérprete de Python de 64 bits.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir={#OutputDir}
OutputBaseFilename=StellaClient-Setup-{#MyAppVersion}
SetupIconFile={#RepoDir}\assets\icon.ico
LicenseFile={#RepoDir}\LICENSE
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; El payload entero: el ejecutable, su _internal con el intérprete y las
; dependencias, el comprobador y el VERSION que identifica la build.
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
