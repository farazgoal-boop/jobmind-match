; JobMind Match Premium — Windows Installer (Inno Setup)

#define MyAppName "JobMind Match Premium"
#define MyAppVersion Trim(FileRead(FileOpen("..\VERSION")))
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
; Belt-and-suspenders for the update flow: the app is supposed to have
; already closed itself (see app/routes/web.py's install-update PID-wait
; helper) before this installer ever runs, but a real packaged-install
; test still hit "DeleteFile failed; code 5" once. CloseApplications lets
; Inno use the Windows Restart Manager to detect + close JobMindMatch.exe
; itself if it's somehow still holding the file open when Setup gets here.
; (ForceCloseApplications isn't a recognized directive in this Inno Setup
; 6.7.3 — Restart Manager's own close attempt below plus the PrepareToInstall
; retry loop are the safety net instead.)
CloseApplications=yes
RestartApplications=no

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
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExePath, ProbePath: String;
  Attempts: Integer;
  Unlocked: Boolean;
begin
  { Extra retry-wait directly in front of the file-copy step, on top of
    CloseApplications/ForceCloseApplications above and the app's own
    PID-wait helper: a real packaged-install test still hit "DeleteFile
    failed; code 5" once. A plain read-open (AssignFile/Reset) would give
    a false "unlocked" reading here — Windows lets a running .exe be
    opened for shared read while it executes, it only denies delete/
    rename/write, which is the actual DeleteFile failure mode being
    guarded against. RenameFile exercises that same sharing restriction,
    so a successful rename (immediately renamed back) is a true "the old
    process has fully released this file" signal. Retries for ~5 seconds
    instead of failing on the very first attempt like the automatic file
    copy does in silent mode. }
  Result := '';
  ExePath := ExpandConstant('{app}\{#MyAppExeName}');
  ProbePath := ExePath + '.lockcheck';
  if FileExists(ExePath) then
  begin
    Attempts := 0;
    Unlocked := False;
    while (Attempts < 25) and (not Unlocked) do
    begin
      Unlocked := RenameFile(ExePath, ProbePath);
      if Unlocked then
        RenameFile(ProbePath, ExePath)
      else
        Sleep(200);
      Attempts := Attempts + 1;
    end;
  end;
end;

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
