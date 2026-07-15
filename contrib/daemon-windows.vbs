' Launches the susurrate daemon with a hidden console. Task Scheduler (and
' uv's pythonw shim, which respawns console-mode python.exe) would otherwise
' show a console window. wscript.exe runs this without any window; the 0
' below hides the python console. Registered by install-daemon-windows.ps1.
Set shell = CreateObject("WScript.Shell")
contrib = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
root = Left(contrib, InStrRev(contrib, "\") - 1)
' Wait on the daemon and pass its exit code through, so the task stays
' "Running" while alive, Task Scheduler's restart-on-failure works, and
' Stop-ScheduledTask stops the daemon too.
code = shell.Run("""" & root & "\.venv\Scripts\python.exe"" """ & contrib & "\daemon-windows.py""", 0, True)
WScript.Quit code
