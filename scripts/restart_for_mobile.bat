@echo off
setlocal
cd /d "%~dp0.."
title JobMind - Mobile LAN Server

echo.
echo ==========================================
echo  JobMind Match - Restart for Mobile APK
echo ==========================================
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set "IP=%%a"
set IP=%IP: =%
echo Your phone should use IP: %IP%
echo Port: 8000
echo.

echo [1/3] Stopping old server on port 8000...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Start-Sleep -Seconds 2"

echo [2/3] Starting server on 0.0.0.0 (phone can connect)...
if exist "runtime\python\python.exe" (
  set "PY=runtime\python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

start "JobMind Server" /MIN cmd /c ""%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning"
powershell -NoProfile -Command "Start-Sleep -Seconds 4"

echo [3/3] Checking...
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/dashboard' -UseBasicParsing -TimeoutSec 8; Write-Host 'PC OK - Status' $r.StatusCode } catch { Write-Host 'PC FAILED:' $_.Exception.Message }"
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://%IP%:8000/dashboard' -UseBasicParsing -TimeoutSec 8; Write-Host 'PHONE OK - LAN Status' $r.StatusCode } catch { Write-Host 'PHONE BLOCKED - Run allow_mobile_lan.bat as Admin, then retry.' }"

echo.
echo Phone APK settings:
echo   IP:   %IP%
echo   Port: 8000
echo.
echo Keep this PC on. Do NOT close JobMind desktop app.
echo.
pause
