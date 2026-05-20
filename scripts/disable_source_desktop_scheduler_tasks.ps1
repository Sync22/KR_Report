param(
    [string]$PythonExe = "python",
    [switch]$DryRun,
    [switch]$ConfirmDisable
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONIOENCODING = "utf-8"

Write-Output "Source desktop scheduler cutover helper."
Write-Output "Use this only on the old source desktop after the mini PC scheduler has been registered and verified."

if (-not $DryRun -and -not $ConfirmDisable) {
    Write-Output "Refusing to disable source desktop scheduler tasks without -ConfirmDisable."
    Write-Output "Preview first:"
    Write-Output "  .\scripts\disable_source_desktop_scheduler_tasks.ps1 -DryRun"
    Write-Output "Then disable after mini PC verification:"
    Write-Output "  .\scripts\disable_source_desktop_scheduler_tasks.ps1 -ConfirmDisable"
    exit 2
}

$schedulerArgs = @(
    "-m",
    "stock_monitor",
    "scheduler-control",
    "disable",
    "--task",
    "all"
)

if ($DryRun) {
    $schedulerArgs += "--dry-run"
}
else {
    $schedulerArgs += "--confirm"
}

Write-Output "$PythonExe $($schedulerArgs -join ' ')"
& $PythonExe @schedulerArgs
if ($LASTEXITCODE -ne 0) {
    throw "source desktop scheduler disable failed with exit code $LASTEXITCODE"
}

if ($DryRun) {
    Write-Output "Dry-run completed. No source desktop scheduler task was changed."
}
else {
    Write-Output "Source desktop scheduler tasks were disabled. Keep this host from running duplicate StockMonitor automation."
}
