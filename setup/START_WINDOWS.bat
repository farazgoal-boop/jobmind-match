@echo off
setlocal EnableExtensions
title JobMind Match - Starting...

REM App root = parent of this setup folder
cd /d "%~dp0\.."
set "APP_ROOT=%CD%"
set "HIDDEN_MODE=0"
if /i "%~1"=="--hidden" set "HIDDEN_MODE=1"

if "%HIDDEN_MODE%"=="0" (
  echo.
  echo  ========================================
  echo   JobMind Match - Premium Job Console
  echo  ========================================
  echo.
)

REM --- Find Python 3.11 ---
set "PY_CMD="
where py >nul 2>&1 && (
  py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
)
if not defined PY_CMD (
  where python >nul 2>&1 && (
    python --version 2>&1 | findstr /R "3\.1[1-9]" >nul && set "PY_CMD=python"
  )
)
if not defined PY_CMD (
  echo [ERROR] Python 3.11+ not found.>> "%APP_ROOT%\jobmind-startup.log"
  if "%HIDDEN_MODE%"=="0" (
    echo [ERROR] Python 3.11+ not found.
    echo Download from: https://www.python.org/downloads/
    pause
  )
  exit /b 1
)

REM --- Virtual environment ---
if not exist "%APP_ROOT%\.venv\Scripts\python.exe" (
  if "%HIDDEN_MODE%"=="0" echo [1/5] Creating virtual environment...
  %PY_CMD% -m venv "%APP_ROOT%\.venv"
  if errorlevel 1 exit /b 1
) else (
  if "%HIDDEN_MODE%"=="0" echo [1/5] Virtual environment ready.
)

if "%HIDDEN_MODE%"=="0" echo [2/5] Activating environment...
call "%APP_ROOT%\.venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

if "%HIDDEN_MODE%"=="0" echo [3/5] Installing dependencies (first run may take 1-2 min)...
python -m pip install --upgrade pip --quiet --disable-pip-version-check 2>nul
python -m pip install -r "%APP_ROOT%\requirements.txt" --quiet --disable-pip-version-check --no-cache-dir
if errorlevel 1 exit /b 1

if not exist "%APP_ROOT%\app\static\icon.ico" (
  if exist "%APP_ROOT%\icon.png" (
    if "%HIDDEN_MODE%"=="0" echo [4/5] Applying owl app icon...
    python "%APP_ROOT%\scripts\generate_icons.py" >nul 2>&1
    python "%APP_ROOT%\scripts\make_icon_ico.py" >nul 2>&1
  )
) else (
  if "%HIDDEN_MODE%"=="0" echo [4/5] Owl icons ready.
)

if not exist "%APP_ROOT%\.env" (
  copy /Y "%APP_ROOT%\.env.example" "%APP_ROOT%\.env" >nul
)

REM --- Already running? ---
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/dashboard', timeout=3)" >nul 2>&1
if not errorlevel 1 (
  if "%HIDDEN_MODE%"=="0" (
    echo [5/5] JobMind Match is already running.
    start "" "http://127.0.0.1:8000/dashboard"
    timeout /t 3 >nul
  )
  exit /b 0
)

if "%HIDDEN_MODE%"=="1" (
  REM Setup only - launch.vbs starts server with pythonw (no window)
  exit /b 0
)

echo [5/5] Starting server...
echo  Dashboard (PC):  http://127.0.0.1:8000/dashboard
echo  Mobile (phone):    http://YOUR-PC-IP:8000/dashboard
echo  Keep this window OPEN while using the app.
echo.
start "" "http://127.0.0.1:8000/dashboard"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
if errorlevel 1 (
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/dashboard', timeout=3)" >nul 2>&1
  if not errorlevel 1 (
    start "" "http://127.0.0.1:8000/dashboard"
    exit /b 0
  )
  echo [ERROR] Server could not start. Port 8000 may be busy.
  pause
  exit /b 1
)

exit /b 0
