[Setup]
AppName=F12 Automation
AppVersion=1.0
DefaultDirName={pf}\F12Automation
DefaultGroupName=F12 Automation
OutputDir=dist
OutputBaseFilename=F12Automation_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
; Copy the built EXE
Source: "C:\Users\04DELL\Desktop\F12\App\dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion

; Copy icons folder (optional)
Source: "C:\Users\04DELL\Desktop\F12\App\icons\*"; DestDir: "{app}\icons"; Flags: recursesubdirs ignoreversion

; Copy any other required files (README, etc.)
Source: "C:\Users\04DELL\Desktop\F12\App\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Shortcut in Start Menu
Name: "{group}\F12 Automation"; Filename: "{app}\main.exe"; WorkingDir: "{app}"

; Shortcut on Desktop
Name: "{commondesktop}\F12 Automation"; Filename: "{app}\main.exe"; WorkingDir: "{app}"

[Run]
; Optionally launch after install
Filename: "{app}\main.exe"; Description: "Launch F12 Automation"; Flags: nowait postinstall skipifsilent
