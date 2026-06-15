@echo off
REM Shortcut from project root — builds setup.exe
cd /d "%~dp0installer"
call build-setup.bat
