param(
    [string]$PythonExe = "python",
    [int]$LookbackDays = 7,
    [int]$MaxDates = 3,
    [double]$SleepSeconds = 3
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

& $PythonExe -m stock_monitor scheduled-krx-daily-backfill --lookback-days $LookbackDays --max-dates $MaxDates --sleep-seconds $SleepSeconds
exit $LASTEXITCODE
