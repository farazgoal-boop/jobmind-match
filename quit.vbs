' JobMind Match - stop background server (no CMD window)
Option Explicit

Dim shell, msg
Set shell = CreateObject("WScript.Shell")

shell.Run "powershell.exe -NoProfile -WindowStyle Hidden -Command ""Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }""", 0, True

WScript.Sleep 500

msg = "JobMind Match has been closed." & vbCrLf & vbCrLf & "You can launch it again from the desktop shortcut."
shell.Popup msg, 3, "JobMind Match", 64
