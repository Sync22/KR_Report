param(
    [string]$PythonExe = "python",
    [int]$LookbackDays = 7,
    [int]$MaxDates = 3,
    [double]$SleepSeconds = 3
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_project_python.ps1")
$PythonExe = Resolve-StockMonitorPython -ProjectRoot $projectRoot -PythonExe $PythonExe
Set-Location $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}

& $PythonExe -m stock_monitor scheduled-krx-daily-backfill --lookback-days $LookbackDays --max-dates $MaxDates --sleep-seconds $SleepSeconds
exit $LASTEXITCODE
