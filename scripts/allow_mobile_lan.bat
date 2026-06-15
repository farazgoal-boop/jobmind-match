@echo off
:: Allow phone on same Wi-Fi to reach JobMind on port 8000
:: Run as Administrator (right-click -> Run as administrator)

netsh advfirewall firewall add rule name="JobMind Match Mobile LAN" dir=in action=allow protocol=TCP localport=8000 profile=private
netsh advfirewall firewall add rule name="JobMind Match Mobile LAN Public" dir=in action=allow protocol=TCP localport=8000 profile=public

echo.
echo Firewall rule added for TCP port 8000.
echo Now RESTART JobMind Match on PC, then use phone APK with your IPv4.
pause
