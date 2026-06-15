@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
set "ROOT=%CD%"

echo.
echo  Bundling Python 3.11 runtime for installer...
echo.

if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\bundle_python_runtime.py"
) else (
  py -3.11 "%ROOT%\scripts\bundle_python_runtime.py"
)

if errorlevel 1 (
  echo.
  echo [ERROR] Failed to bundle Python runtime.
  exit /b 1
)

echo.
echo  Python runtime ready: installer\runtime\python
exit /b 0
