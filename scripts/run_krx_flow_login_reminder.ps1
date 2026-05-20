param(
    [string]$PythonExe = "python",
    [int]$MinutesBefore = 5,
    [string]$PlannedTime = "16:50"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

& $PythonExe -m stock_monitor krx-flow-login-reminder --minutes-before $MinutesBefore --planned-time $PlannedTime
