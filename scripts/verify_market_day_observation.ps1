param(
    [string]$PythonExe = "python",
    [string]$Date = "",
    [int]$RecentReportDates = 5,
    [int]$StockLimit = 20
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONIOENCODING = "utf-8"

function Invoke-MarketObservationPythonStep {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    Write-Output ""
    Write-Output "== $Label =="
    Write-Output "$PythonExe $($Arguments -join ' ')"
    & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Output ""
        Write-Output "Market-day observation verification failed: $Label (exit code $LASTEXITCODE)"
        Write-Output "Run this wrapper from an elevated local PowerShell session when Task Scheduler metadata is required."
        exit $LASTEXITCODE
    }
}

Write-Output "Market-day observation verification"
Write-Output "- read-only closeout helper; no Telegram send, scheduler registration, DB write, or live fetch is requested."
Write-Output "- StockMonitor-Shutdown should remain unregistered for mini-PC always-on operation."
Write-Output "- use elevated local PowerShell if Task Scheduler metadata access is denied."

Invoke-MarketObservationPythonStep `
    -Label "operator health" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "operator-status",
        "--json",
        "--health-exit"
    )

Write-Output ""
Write-Output "== scheduler registration =="
$schedulerScript = Join-Path $PSScriptRoot "verify_task_scheduler_registration.ps1"
Write-Output "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $schedulerScript -PythonExe $PythonExe"
& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $schedulerScript `
    -PythonExe $PythonExe
if ($LASTEXITCODE -ne 0) {
    Write-Output ""
    Write-Output "Market-day observation verification failed: scheduler registration (exit code $LASTEXITCODE)"
    Write-Output "Use an elevated local PowerShell session if the result is Task Scheduler metadata access denied."
    exit $LASTEXITCODE
}

$marketObservationArgs = @(
    "-m",
    "stock_monitor",
    "market-day-observation",
    "--json"
)
if ($Date) {
    $marketObservationArgs += @("--date", $Date)
}
Invoke-MarketObservationPythonStep `
    -Label "market-day observation audit" `
    -Arguments $marketObservationArgs

Invoke-MarketObservationPythonStep `
    -Label "db verify" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "db-verify",
        "--json"
    )

Invoke-MarketObservationPythonStep `
    -Label "next-phase readiness" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "next-phase-readiness",
        "--recent-report-dates",
        "$RecentReportDates",
        "--stock-limit",
        "$StockLimit",
        "--json"
    )

Write-Output ""
Write-Output "Market-day observation verification completed."
Write-Output "- if next-phase-readiness still blocks on market-day observation, rerun after the next due task time."
Write-Output "- if it blocks on phone readability, review the recorded Telegram messages before accepting."
Write-Output "- if it blocks on external web-view provider smoke, finish Cloudflare/Tailscale setup separately."
