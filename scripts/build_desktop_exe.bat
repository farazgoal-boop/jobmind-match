@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set "ROOT=%CD%"

echo.
echo  Building JobMindMatch desktop launcher (onedir)...
echo.

REM onedir (no --onefile): a real packaged-install test found the onefile
REM bootloader's per-launch self-extract-to-%%TEMP%%\_MEI<pid> step racing
REM Windows Defender's real-time scan of the freshly-written python311.dll,
REM intermittently (2 failures out of 7 launches under load) failing with
REM "Failed to load Python DLL ... LoadLibrary: The specified module could
REM not be found." onedir runs directly from the installed folder with
REM every DLL already sitting on disk (scanned once, at install time) --
REM no re-extraction, no race, on every single launch thereafter.
if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" -m pip install pyinstaller pywebview pythonnet --quiet --disable-pip-version-check
  if not exist "%ROOT%\app\static\icon.ico" (
    "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\make_icon_ico.py"
  )
  "%ROOT%\.venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --noconsole ^
    --name JobMindMatch ^
    --icon "%ROOT%\app\static\icon.ico" ^
    --distpath "%ROOT%\dist" ^
    --workpath "%ROOT%\build\launcher" ^
    --specpath "%ROOT%\build\launcher" ^
    "%ROOT%\scripts\desktop_launcher.py"
) else (
  py -3.11 -m pip install pyinstaller pywebview pythonnet --quiet --disable-pip-version-check
  if not exist "%ROOT%\app\static\icon.ico" (
    py -3.11 "%ROOT%\scripts\make_icon_ico.py"
  )
  py -3.11 -m PyInstaller ^
    --noconfirm ^
    --noconsole ^
    --name JobMindMatch ^
    --icon "%ROOT%\app\static\icon.ico" ^
    --distpath "%ROOT%\dist" ^
    --workpath "%ROOT%\build\launcher" ^
    --specpath "%ROOT%\build\launcher" ^
    "%ROOT%\scripts\desktop_launcher.py"
)

if errorlevel 1 (
  echo.
  echo [ERROR] Failed to build JobMindMatch
  exit /b 1
)

if not exist "%ROOT%\dist\JobMindMatch\JobMindMatch.exe" (
  echo [ERROR] dist\JobMindMatch\JobMindMatch.exe not found
  exit /b 1
)

echo.
echo  Done: dist\JobMindMatch\ (folder build)
exit /b 0
