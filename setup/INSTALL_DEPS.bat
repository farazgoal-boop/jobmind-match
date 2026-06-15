@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set "ROOT=%CD%"
set "BUNDLED_PY=%ROOT%\runtime\python\python.exe"

if exist "%BUNDLED_PY%" (
  goto :finalize
)

REM Dev fallback only (buyer installer ships bundled Python)
set "PY_CMD="
where py >nul 2>&1 && py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
if not defined PY_CMD (
  where python >nul 2>&1 && (
    python --version 2>&1 | findstr /R "3\.1[1-9]" >nul && set "PY_CMD=python"
  )
)
if not defined PY_CMD exit /b 1

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  %PY_CMD% -m venv "%ROOT%\.venv"
  if errorlevel 1 exit /b 1
)

call "%ROOT%\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet --disable-pip-version-check 2>nul
python -m pip install -r "%ROOT%\requirements.txt" --quiet --disable-pip-version-check --no-cache-dir
if errorlevel 1 exit /b 1
set "BUNDLED_PY=%ROOT%\.venv\Scripts\python.exe"

:finalize
if not exist "%ROOT%\app\main.py" exit /b 1

if not exist "%ROOT%\.env" (
  copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
)

if exist "%ROOT%\icon.png" (
  if not exist "%ROOT%\app\static\icon.ico" (
    "%BUNDLED_PY%" "%ROOT%\scripts\generate_icons.py" >nul 2>&1
    "%BUNDLED_PY%" "%ROOT%\scripts\make_icon_ico.py" >nul 2>&1
  )
)

exit /b 0
