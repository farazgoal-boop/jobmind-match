@echo off
title Repair JobMind Shortcuts
set "APP=%LOCALAPPDATA%\Programs\JobMind Match"
set "ICON=%APP%\app\static\icon.ico"
set "EXE=%APP%\JobMindMatch.exe"
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs\JobMind Match Premium"
set "DESK=%USERPROFILE%\Desktop"

if not exist "%EXE%" (
  echo Install folder not found: %APP%
  echo Please run JobMind-Match-Setup.exe first.
  pause
  exit /b 1
)

if not exist "%ICON%" set "ICON=%EXE%"
if not exist "%SM%" mkdir "%SM%"

powershell -NoProfile -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut('%SM%\JobMind Match Premium.lnk');" ^
  "$s.TargetPath='%EXE%';" ^
  "$s.WorkingDirectory='%APP%';" ^
  "$s.IconLocation='%ICON%,0';" ^
  "$s.Description='JobMind Match Premium';" ^
  "$s.Save();" ^
  "$d=$w.CreateShortcut('%DESK%\JobMind Match Premium.lnk');" ^
  "$d.TargetPath='%EXE%';" ^
  "$d.WorkingDirectory='%APP%';" ^
  "$d.IconLocation='%ICON%,0';" ^
  "$d.Description='JobMind Match Premium';" ^
  "$d.Save()"

echo.
echo Shortcuts created:
echo   Start Menu: %SM%
echo   Desktop:    %DESK%\JobMind Match Premium.lnk
echo.
echo Starting app...
start "" "%EXE%"
pause
