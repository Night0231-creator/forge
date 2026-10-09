#define StudioName "Astronyx Mini Forge Studio"
#define StudioVersion "2.2.0"
[Setup]
AppId={{C31F9C66-FF88-4C88-87F4-41618861D139}
AppName={#StudioName}
AppVersion={#StudioVersion}
AppPublisher=Astronyx
AppPublisherURL=https://github.com/Night0231-creator/forge
AppSupportURL=https://github.com/Night0231-creator/forge/issues
AppUpdatesURL=https://github.com/Night0231-creator/forge/releases/latest
VersionInfoCompany=Astronyx
VersionInfoDescription=Astronyx Mini Forge Studio - Instalador Windows
VersionInfoVersion=2.2.0.0
VersionInfoProductName={#StudioName}
DefaultDirName={localappdata}\Programs\AstronyxMiniForgeStudio
DefaultGroupName=Astronyx Mini Forge Studio
OutputDir=..\dist\installer
OutputBaseFilename=AstronyxMiniForgeStudio-Setup-v2.2.0
SetupIconFile=..\assets\astronyx.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\AstronyxMiniForgeStudio.exe
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\AstronyxMiniForgeStudio.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Astronyx Mini Forge Studio"; Filename: "{app}\AstronyxMiniForgeStudio.exe"
Name: "{autodesktop}\Astronyx Mini Forge Studio"; Filename: "{app}\AstronyxMiniForgeStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\AstronyxMiniForgeStudio.exe"; Description: "Abrir o Astronyx Mini Forge Studio"; Flags: nowait postinstall skipifsilent
