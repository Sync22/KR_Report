param(
    [string]$PythonExe = "python",
    [string]$Date = "",
    [int]$RecentReportDates = 5,
    [int]$StockLimit = 20,
    [switch]$RecordStartupFallbackSuccess,
    [switch]$SkipOperatorStatus,
    [switch]$SkipSchedulerRegistration
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONIOENCODING = "utf-8"

function Invoke-CloseoutPythonStep {
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
        Write-Output "Next-phase closeout verification failed: $Label (exit code $LASTEXITCODE)"
        Write-Output "Use an elevated local PowerShell session when Task Scheduler metadata is required."
        exit $LASTEXITCODE
    }
}

Write-Output "Next-phase closeout verification"
Write-Output "- read-only by default; no Telegram send, scheduler registration, Cloudflare configuration, or live KRX fetch is requested."
Write-Output "- do not expose admin-gui; the external candidate remains the read-only web-view on 127.0.0.1:8780."
Write-Output "- access-code values and other secrets must not be printed."
Write-Output "- StockMonitor-Shutdown should remain unregistered for mini-PC always-on operation."
Write-Output "- use -RecordStartupFallbackSuccess only after a real Windows logon/reboot started web-view through the Startup shortcut."
Write-Output "- use elevated local PowerShell if Task Scheduler metadata access is denied."

Invoke-CloseoutPythonStep `
    -Label "db verify" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "db-verify",
        "--json"
    )

$startupFallbackArgs = @(
    "-m",
    "stock_monitor",
    "web-view-startup-fallback-check",
    "--json"
)
if ($RecordStartupFallbackSuccess) {
    $startupFallbackArgs += "--record-success"
}
Invoke-CloseoutPythonStep `
    -Label "web-view Startup fallback" `
    -Arguments $startupFallbackArgs

if (-not $SkipOperatorStatus) {
    Invoke-CloseoutPythonStep `
        -Label "operator health" `
        -Arguments @(
            "-m",
            "stock_monitor",
            "operator-status",
            "--json",
            "--health-exit"
        )
}

if (-not $SkipSchedulerRegistration) {
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
        Write-Output "Next-phase closeout verification failed: scheduler registration (exit code $LASTEXITCODE)"
        Write-Output "Use an elevated local PowerShell session if the result is Task Scheduler metadata access denied."
        exit $LASTEXITCODE
    }
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
Invoke-CloseoutPythonStep `
    -Label "market-day observation audit" `
    -Arguments $marketObservationArgs

Invoke-CloseoutPythonStep `
    -Label "observation summary audit" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "observation-summary-audit",
        "--recent-report-dates",
        "$RecentReportDates",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "observation reaction distribution" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "observation-reaction-distribution",
        "--mention-threshold",
        "2",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "candidate evidence readiness" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "candidate-evidence-readiness",
        "--recent-report-dates",
        "$RecentReportDates",
        "--stock-limit",
        "$StockLimit",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "market briefing readiness" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "market-briefing-readiness",
        "--recent-report-dates",
        "$RecentReportDates",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "web-view value QA" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "web-view-value-qa",
        "--recent-business-days",
        "4",
        "--stock-limit",
        "$StockLimit",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "web-view browser smoke" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "web-view-browser-smoke",
        "--stock-limit",
        "$StockLimit",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "external web-view sharing plan" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "external-web-view-sharing-plan",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "category snapshot status" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "category-snapshot-status",
        "--mode",
        "fallback",
        "--limit",
        "100",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "category snapshot plan" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "category-snapshot-plan",
        "--limit",
        "100",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "rotation mapping audit" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "rotation-mapping-audit",
        "--json"
    )

Invoke-CloseoutPythonStep `
    -Label "KRX baseline analysis" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "krx-baseline-analysis",
        "--json"
    )

Invoke-CloseoutPythonStep `
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
Write-Output "Next-phase closeout verification completed."
Write-Output "- if next-phase-readiness still blocks on market-day observation, rerun after the next due task time."
Write-Output "- if it blocks on phone readability, review the recorded Telegram messages before accepting."
Write-Output "- if it blocks on Startup fallback, reboot/log on and rerun with -RecordStartupFallbackSuccess after local web-view health is confirmed."
