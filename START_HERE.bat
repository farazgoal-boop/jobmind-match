@echo off
cd /d "%~dp0"
if exist "%~dp0JobMindMatch.exe" (
  start "" "%~dp0JobMindMatch.exe"
) else (
  wscript.exe "%~dp0launch.vbs"
)
