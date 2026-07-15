# Registers the susurrate dictation daemon as a Task Scheduler logon task
# (Windows' launchd equivalent) and starts it now. Idempotent; run after
# setup-windows.ps1:
#   powershell -ExecutionPolicy Bypass -File .\contrib\install-daemon-windows.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { throw "no .venv found - run setup-windows.ps1 first" }

$action = New-ScheduledTaskAction -Execute "wscript.exe" `
    -Argument "`"$PSScriptRoot\daemon-windows.vbs`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "susurrate" -Action $action -Trigger $trigger `
    -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "susurrate"

Write-Host "susurrate daemon registered (Task Scheduler task 'susurrate') and started."
Write-Host "Hold Ctrl+Win anywhere to dictate."
Write-Host "Log: $env:USERPROFILE\.local\share\susurrate\daemon.log"
Write-Host "Stop/remove: Stop-ScheduledTask susurrate; Unregister-ScheduledTask susurrate"
