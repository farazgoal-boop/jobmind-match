@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set "ROOT=%CD%"

echo.
echo  Building JobMindMatch.exe desktop launcher...
echo.

if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" -m pip install pyinstaller --quiet --disable-pip-version-check
  if not exist "%ROOT%\app\static\icon.ico" (
    "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\make_icon_ico.py"
  )
  "%ROOT%\.venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --noconsole ^
    --name JobMindMatch ^
    --icon "%ROOT%\app\static\icon.ico" ^
    --distpath "%ROOT%\dist" ^
    --workpath "%ROOT%\build\launcher" ^
    --specpath "%ROOT%\build\launcher" ^
    "%ROOT%\scripts\desktop_launcher.py"
) else (
  py -3.11 -m pip install pyinstaller --quiet --disable-pip-version-check
  if not exist "%ROOT%\app\static\icon.ico" (
    py -3.11 "%ROOT%\scripts\make_icon_ico.py"
  )
  py -3.11 -m PyInstaller ^
    --noconfirm ^
    --onefile ^
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
  echo [ERROR] Failed to build JobMindMatch.exe
  exit /b 1
)

if not exist "%ROOT%\dist\JobMindMatch.exe" (
  echo [ERROR] dist\JobMindMatch.exe not found
  exit /b 1
)

echo.
echo  Done: dist\JobMindMatch.exe
exit /b 0
