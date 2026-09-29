; Inno Setup 6 Script for SANKET — AI-Assisted Virtual Camera Tracking System
; Official SIH Problem Statement 26169 Deliverable #1 (Standalone Windows Application)
; Department of Space / Indian Space Research Organisation (ISRO)

#define MyAppName "SANKET"
#define MyAppFullName "SANKET - AI-Assisted Virtual Camera Tracking System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SIH 26169 Engineering Team"
#define MyAppExeName "SANKET.exe"

[Setup]
AppId={{D37E84B0-76D4-4903-9A52-87C9E7D01B69}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppFullName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SANKET
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=SANKET-Setup-v1.0
SetupIconFile=..\App_Logo_Assets_Final\favicon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.10240
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
UsePreviousAppDir=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=SANKET Standalone Tracking System
VersionInfoProductName=SANKET

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\SANKET\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\App_Logo_Assets_Final\favicon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\App_Logo_Assets_Final\favicon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
