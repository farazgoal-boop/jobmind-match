@echo off
title JobMind Match Premium
cd /d "%~dp0\.."
if not exist "JobMindMatch.exe" (
  echo [ERROR] JobMindMatch.exe not found in install folder.
  pause
  exit /b 1
)
start "" "%~dp0..\JobMindMatch.exe"
exit /b 0
