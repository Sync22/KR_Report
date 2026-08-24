param(
    [string]$TaskPrefix = "StockMonitor",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_project_python.ps1")
$PythonExe = Resolve-StockMonitorPython -ProjectRoot $projectRoot -PythonExe $PythonExe
$registerScript = Join-Path $PSScriptRoot "register_task_scheduler_tasks.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify_task_scheduler_registration.ps1"

Write-Output "Registering mini PC scheduler tasks without scheduled shutdown."
Write-Output "StockMonitor-Shutdown is intentionally not registered for the always-on mini PC profile."
Write-Output "StockMonitor-WebViewHourlyRestart is registered by default to refresh the Cloudflare web-view target every hour."

$registerArgs = @{
    TaskPrefix = $TaskPrefix
    PythonExe = $PythonExe
    SkipShutdown = $true
}
& $registerScript @registerArgs

if (-not $?) {
    throw "mini PC scheduler registration failed"
}

$verifyArgs = @{
    TaskPrefix = $TaskPrefix
    PythonExe = $PythonExe
}
& $verifyScript @verifyArgs

if (-not $?) {
    throw "mini PC scheduler verification failed"
}

Write-Output "Mini PC scheduler tasks registered and verified."
Write-Output "- project: $projectRoot"
Write-Output "- python_exe: $PythonExe"
Write-Output "- shutdown_task: skipped"
Write-Output "- web_view_hourly_restart: StockMonitor-WebViewHourlyRestart"
Write-Output "- toss_close_snapshot: StockMonitor-TossCloseSnapshot at 20:05 on weekdays (20:00 integrated-market baseline)"
