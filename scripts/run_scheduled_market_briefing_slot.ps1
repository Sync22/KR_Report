param(
    [string]$PythonExe = "python",
    [ValidateSet("mood", "lunch", "preclose")]
    [string]$Slot = "mood",
    [int]$Limit = 5,
    [switch]$DryRun,
    [switch]$AllowLate
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$args = @(
    "-m",
    "stock_monitor",
    "scheduled-market-briefing-slot",
    "--slot",
    $Slot,
    "--limit",
    "$Limit"
)
if ($DryRun) {
    $args += "--dry-run"
}
if ($AllowLate) {
    $args += "--allow-late"
}

& $PythonExe @args
exit $LASTEXITCODE
