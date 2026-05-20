param(
    [switch]$DryRun,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$args = @("-m", "stock_monitor", "scheduled-notify")
if ($DryRun) {
    $args += "--dry-run"
}

& $PythonExe @args
exit $LASTEXITCODE
