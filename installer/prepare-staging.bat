@echo off
title JobMind Match — Prepare Installer Staging
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "STAGING=%~dp0staging"

echo.
echo  Preparing clean staging folder for setup.exe...
echo.

if not exist "%ROOT%\dist\JobMindMatch.exe" (
  echo [ERROR] Missing dist\JobMindMatch.exe
  exit /b 1
)

if not exist "%ROOT%\installer\runtime\python\python.exe" (
  echo [ERROR] Missing bundled Python - run scripts\bundle_python_runtime.bat first.
  exit /b 1
)

if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%"
mkdir "%STAGING%\app"
mkdir "%STAGING%\setup"
mkdir "%STAGING%\scripts"
mkdir "%STAGING%\runtime"

xcopy /E /I /Y "%ROOT%\app" "%STAGING%\app" >nul
if exist "%STAGING%\app\__pycache__" rmdir /s /q "%STAGING%\app\__pycache__"
for /d /r "%STAGING%\app" %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"

xcopy /E /I /Y "%ROOT%\installer\runtime\python" "%STAGING%\runtime\python" >nul
xcopy /E /I /Y "%ROOT%\setup" "%STAGING%\setup" >nul
copy /Y "%ROOT%\dist\JobMindMatch.exe" "%STAGING%\" >nul
copy /Y "%ROOT%\requirements.txt" "%STAGING%\" >nul
copy /Y "%ROOT%\.env.example" "%STAGING%\" >nul
copy /Y "%ROOT%\.python-version" "%STAGING%\" >nul
copy /Y "%ROOT%\icon.png" "%STAGING%\" >nul
copy /Y "%ROOT%\README.md" "%STAGING%\" >nul
copy /Y "%ROOT%\scripts\generate_icons.py" "%STAGING%\scripts\" >nul
copy /Y "%ROOT%\scripts\make_icon_ico.py" "%STAGING%\scripts\" >nul
copy /Y "%ROOT%\START_HERE.bat" "%STAGING%\" >nul

echo  Staging ready: %STAGING%
if /I not "%~1"=="silent" pause
exit /b 0
