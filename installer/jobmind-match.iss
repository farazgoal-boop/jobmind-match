; JobMind Match Premium — Windows Installer (Inno Setup)

#define MyAppName "JobMind Match Premium"
#define MyAppVersion "1.0.3"
#define MyAppPublisher "JobMind"
#define MyAppURL "https://gumroad.com"
#define MyAppExeName "JobMindMatch.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\JobMind Match
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\setup\LICENSE.txt
InfoBeforeFile=..\setup\GUMROAD_README.txt
OutputDir=output
OutputBaseFilename=JobMind-Match-Setup
SetupIconFile=..\app\static\icon.ico
UninstallDisplayIcon={app}\app\static\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\setup"
Type: filesandordirs; Name: "{app}\scripts"
Type: filesandordirs; Name: "{app}\runtime"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app\static\icon.ico"
Name: "{group}\Open JobMind (if app won't start)"; Filename: "{app}\setup\OPEN_JOBMIND.bat"; WorkingDir: "{app}"; IconFilename: "{app}\app\static\icon.ico"
Name: "{group}\Quit {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--quit"; WorkingDir: "{app}"; IconFilename: "{app}\app\static\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app\static\icon.ico"; Tasks: desktopicon

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--quit"; Flags: runhidden waituntilterminated

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Finishing JobMind Match setup...';
    WizardForm.ProgressGauge.Style := npbstMarquee;
    try
      if not Exec(ExpandConstant('{cmd}'), '/c "' + ExpandConstant('{app}\setup\INSTALL_DEPS.bat') + '"',
        ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
        MsgBox('Setup could not finish. Please run the installer again.',
          mbError, MB_OK);
    finally
      WizardForm.ProgressGauge.Style := npbstNormal;
    end;
  end;

  if CurStep = ssDone then
  begin
    Sleep(1500);
    if not Exec(ExpandConstant('{app}\{#MyAppExeName}'), '', ExpandConstant('{app}'), SW_SHOWNORMAL, ewNoWait, ResultCode) then
      MsgBox('JobMind Match is installed. Open it from Start Menu or run setup\OPEN_JOBMIND.bat',
        mbInformation, MB_OK);
  end;
end;
