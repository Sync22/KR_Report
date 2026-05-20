param(
    [string]$PythonExe = "python",
    [int]$LookbackDays = 31,
    [int]$MentionThreshold = 1,
    [int]$MaxCalls = 300,
    [double]$SleepSeconds = 1
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

& $PythonExe -m stock_monitor scheduled-krx-mentioned-flow-backfill --lookback-days $LookbackDays --mention-threshold $MentionThreshold --max-calls $MaxCalls --sleep-seconds $SleepSeconds
exit $LASTEXITCODE
