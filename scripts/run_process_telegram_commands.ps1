param(
    [string]$EndTime = "16:30",
    [int]$IntervalSeconds = 60,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $PythonExe -m stock_monitor scheduled-telegram-command-loop --end-time $EndTime --interval-seconds $IntervalSeconds
exit $LASTEXITCODE
