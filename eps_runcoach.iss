; Inno Setup script for EPS RunCoach.
; Builds a Windows installer from the already-packaged PyInstaller output
; in dist\EPS_RunCoach\. Run `uv run pyinstaller eps_runcoach.spec --noconfirm`
; first to produce that folder, then compile this script with Inno Setup
; (ISCC.exe eps_runcoach.iss, or open it in the Inno Setup Compiler GUI).

#define MyAppName "EPS RunCoach"
#define MyAppVersion "0.3.1"
#define MyAppPublisher "Edwin Scull"
#define MyAppExeName "EPS_RunCoach.exe"

[Setup]
AppId={{B6C6C9C7-6E9C-4B4A-9C7A-3F2A6D6F6A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=dist_installer
OutputBaseFilename=EPS_RunCoach_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\icon.ico
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\EPS_RunCoach\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
