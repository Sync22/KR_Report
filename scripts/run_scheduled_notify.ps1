param(
    [switch]$DryRun,
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

$args = @("-m", "stock_monitor", "scheduled-notify")
if ($DryRun) {
    $args += "--dry-run"
}

& $PythonExe @args
exit $LASTEXITCODE
