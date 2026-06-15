@echo off
setlocal
cd /d "%~dp0.."
echo.
echo ========================================
echo  JobMind Match - Mobile Connect Helper
echo ========================================
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  set "IP=%%a"
  goto :found
)
:found
set IP=%IP: =%
echo Your PC IPv4: %IP%
echo Enter this in the phone APK, port 8000.
echo.

netstat -ano | findstr ":8000" | findstr LISTENING
echo.
echo If you only see 127.0.0.1:8000 the phone CANNOT connect.
echo You need 0.0.0.0:8000 — restart JobMind after updating.
echo.
echo 1. Quit JobMind Match (Start Menu -^> Quit)
echo 2. Run scripts\allow_mobile_lan.bat as Administrator
echo 3. Start JobMind Match again
echo 4. Phone APK: %IP% port 8000
echo.
pause
