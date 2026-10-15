#ifndef AppVersion
  #error AppVersion must be supplied by build_windows.ps1
#endif
[Setup]
AppId={{1B98B470-057B-4FCF-94A1-29537A83739C}
AppName=AulaOS
AppVersion={#AppVersion}
AppPublisher=AulaOS
DefaultDirName={localappdata}\Programs\AulaOS
DefaultGroupName=AulaOS
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=AulaOS-{#AppVersion}-windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AulaOS.exe
CloseApplications=yes
RestartApplications=no
[Files]
Source: "..\dist\AulaOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\AulaOS"; Filename: "{app}\AulaOS.exe"
[Run]
Filename: "{app}\AulaOS.exe"; Description: "Abrir AulaOS"; Flags: nowait postinstall skipifsilent
; No UninstallDelete: user data stays in LOCALAPPDATA\AulaOSLab.
