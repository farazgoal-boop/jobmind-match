@echo off
title JobMind Match - Build setup.exe
cd /d "%~dp0"

echo.
echo  ============================================
echo   JobMind Match - setup.exe Builder
echo  ============================================
echo.

echo [1/6] Generating icons...
cd ..
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\generate_icons.py
    .\.venv\Scripts\python.exe scripts\make_icon_ico.py
) else (
    py -3.11 scripts\generate_icons.py
    py -3.11 scripts\make_icon_ico.py
)

echo [2/6] Building JobMindMatch.exe...
call scripts\build_desktop_exe.bat
if errorlevel 1 (
    echo Desktop launcher build failed.
    pause
    exit /b 1
)

echo [3/6] Bundling Python runtime (no python.org for buyers)...
call scripts\bundle_python_runtime.bat
if errorlevel 1 (
    echo Python bundle failed.
    pause
    exit /b 1
)

cd installer

echo [4/6] Preparing staging...
call prepare-staging.bat silent
if errorlevel 1 exit /b 1

set ISCC=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC 2^>nul') do set "ISCC=%%I"
)

if not defined ISCC (
    echo [ERROR] Inno Setup 6 not found.
    pause
    exit /b 1
)

echo [5/6] Compiling setup.exe...
"%ISCC%" jobmind-match.iss
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo [6/6] DONE!
echo.
echo  Your installer:
echo  installer\output\JobMind-Match-Setup.exe
echo.
echo  Buyers do NOT need python.org - Python is bundled inside.
echo.
exit /b 0
