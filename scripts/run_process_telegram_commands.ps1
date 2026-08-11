param(
    [string]$EndTime = "16:30",
    [int]$IntervalSeconds = 60,
    [string]$PythonExe = "python"
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
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $PythonExe -m stock_monitor scheduled-telegram-command-loop --end-time $EndTime --interval-seconds $IntervalSeconds
exit $LASTEXITCODE
