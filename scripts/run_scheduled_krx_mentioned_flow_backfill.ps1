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
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}

& $PythonExe -m stock_monitor scheduled-krx-mentioned-flow-backfill --lookback-days $LookbackDays --mention-threshold $MentionThreshold --max-calls $MaxCalls --sleep-seconds $SleepSeconds
exit $LASTEXITCODE
