@echo off
setlocal
set "ROOT=%~dp0.."
set "SRC=%ROOT%\app"
set "PYROOT=%ROOT%\mobile-wrapper\android\app\src\main\python"
set "DST=%PYROOT%\app"

if not exist "%PYROOT%" mkdir "%PYROOT%"
if not exist "%DST%" mkdir "%DST%"

echo Syncing Python app into Android APK...
robocopy "%SRC%" "%DST%" /E /XD __pycache__ .venv /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /NP
if errorlevel 8 exit /b 1

copy /Y "%PYROOT%\jobmind_bootstrap.py" "%PYROOT%\jobmind_bootstrap.py" >nul 2>&1
echo Done: %DST%
endlocal
