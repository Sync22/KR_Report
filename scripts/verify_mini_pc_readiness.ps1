param(
    [string]$PythonExe = "python",
    [int]$RecentBusinessDays = 4,
    [int]$StockLimit = 20,
    [switch]$RequireAccessCode,
    [switch]$RequireMiniPcProfile,
    [switch]$SkipPytest,
    [switch]$SkipBackupRequirement,
    [switch]$SkipEnvRequirement,
    [switch]$SkipRestoreSmoke,
    [switch]$SkipWebViewBrowserSmoke,
    [switch]$SkipOperatorStatus
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONIOENCODING = "utf-8"

function Invoke-ReadinessStep {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    Write-Output ""
    Write-Output "== $Label =="
    Write-Output "$PythonExe $($Arguments -join ' ')"
    & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

if (-not $SkipPytest) {
    Invoke-ReadinessStep -Label "pytest" -Arguments @("-m", "pytest", "-q")
}

Invoke-ReadinessStep -Label "db-verify" -Arguments @("-m", "stock_monitor", "db-verify")

if ($SkipBackupRequirement -and -not $SkipRestoreSmoke) {
    Write-Output "Skipping restore smoke because backup requirement was skipped."
}

if (-not $SkipBackupRequirement -and -not $SkipRestoreSmoke) {
    $backupDir = Join-Path $projectRoot "data\backups"
    $latestBackup = Get-ChildItem -LiteralPath $backupDir -Filter "stock_monitor_*.db" -File -ErrorAction SilentlyContinue |
        Sort-Object -Property LastWriteTime, Name -Descending |
        Select-Object -First 1
    if (-not $latestBackup) {
        throw "No stock_monitor_*.db backup found in $backupDir"
    }
    Invoke-ReadinessStep -Label "db-restore-smoke" -Arguments @(
        "-m",
        "stock_monitor",
        "db-restore-smoke",
        $latestBackup.FullName
    )
}

$preflightArgs = @("-m", "stock_monitor", "mini-pc-preflight")
if (-not $SkipEnvRequirement) {
    $preflightArgs += "--require-env"
}
if (-not $SkipBackupRequirement) {
    $preflightArgs += "--require-backup"
}
if ($RequireAccessCode) {
    $preflightArgs += "--require-access-code"
}
if ($RequireMiniPcProfile) {
    $preflightArgs += "--require-mini-pc-profile"
}
Invoke-ReadinessStep -Label "mini-pc-preflight" -Arguments $preflightArgs

Invoke-ReadinessStep -Label "web-view-value-qa" -Arguments @(
    "-m",
    "stock_monitor",
    "web-view-value-qa",
    "--recent-business-days",
    "$RecentBusinessDays",
    "--stock-limit",
    "$StockLimit"
)

if (-not $SkipWebViewBrowserSmoke) {
    Invoke-ReadinessStep -Label "web-view-browser-smoke" -Arguments @(
        "-m",
        "stock_monitor",
        "web-view-browser-smoke",
        "--stock-limit",
        "$StockLimit"
    )
}

if (-not $SkipOperatorStatus) {
    Invoke-ReadinessStep -Label "operator-status" -Arguments @(
        "-m",
        "stock_monitor",
        "operator-status",
        "--json",
        "--health-exit"
    )
}

Write-Output ""
Write-Output "Mini PC readiness verification completed."
