' JobMind Match - silent launcher (zero CMD window)
Option Explicit

Dim shell, fso, appRoot, batPath, pythonw, i, maxWait

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appRoot = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = appRoot & "\setup\START_WINDOWS.bat"
pythonw = appRoot & "\.venv\Scripts\pythonw.exe"

If IsServerUp() Then
  OpenDashboard
  WScript.Quit 0
End If

If Not fso.FileExists(appRoot & "\.venv\Scripts\python.exe") Then
  shell.Popup "Starting JobMind Match..." & vbCrLf & vbCrLf & _
    "First launch installs components (about 1-2 minutes)." & vbCrLf & _
    "Your browser will open automatically.", 4, "JobMind Match", 64
Else
  shell.Popup "Starting JobMind Match...", 2, "JobMind Match", 64
End If

If shell.Run("cmd /c """ & batPath & """ --hidden", 0, True) <> 0 Then
  ShowStartupError
  WScript.Quit 1
End If

If IsServerUp() Then
  OpenDashboard
  WScript.Quit 0
End If

If Not fso.FileExists(pythonw) Then
  ShowStartupError
  WScript.Quit 1
End If

shell.CurrentDirectory = appRoot
shell.Run """" & pythonw & """ -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning", 0, False

maxWait = 180
For i = 1 To maxWait
  WScript.Sleep 1000
  If IsServerUp() Then
    OpenDashboard
    WScript.Quit 0
  End If
Next

ShowStartupError
WScript.Quit 1

Function IsServerUp()
  On Error Resume Next
  Dim http
  Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  http.open "GET", "http://127.0.0.1:8000/dashboard", False
  http.setTimeouts 2000, 2000, 2000, 2000
  http.send
  IsServerUp = (Err.Number = 0 And http.Status = 200)
  On Error GoTo 0
End Function

Sub OpenDashboard()
  shell.Run "http://127.0.0.1:8000/dashboard", 1, False
End Sub

Sub ShowStartupError()
  Dim msg
  msg = "JobMind Match could not start." & vbCrLf & vbCrLf & _
    "1) Install Python 3.11 from python.org (check Add to PATH)" & vbCrLf & _
    "2) Use Start Menu -> Quit JobMind Match, then try again" & vbCrLf & _
    "3) Restart your PC if port 8000 is still busy"
  shell.Popup msg, 0, "JobMind Match", 16
End Sub
