param(
    [string]$PythonExe = "python",
    [int]$RecentBusinessDays = 4,
    [int]$StockLimit = 20,
    [switch]$SkipBrowserSmoke
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONIOENCODING = "utf-8"

function Invoke-ExternalReadinessStep {
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
        Write-Output "External readiness step failed: $Label (exit code $LASTEXITCODE)"
        Write-Output "If access-code is disabled, run:"
        Write-Output "  python -m stock_monitor access-code set"
        Write-Output "  python -m stock_monitor access-code status"
        Write-Output "Then rerun this script before sharing the web-view."
        exit $LASTEXITCODE
    }
}

Invoke-ExternalReadinessStep `
    -Label "external-sharing preflight" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "mini-pc-preflight",
        "--require-access-code",
        "--require-backup",
        "--require-env",
        "--require-mini-pc-profile"
    )

Invoke-ExternalReadinessStep `
    -Label "web-view public value QA" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "web-view-value-qa",
        "--recent-business-days",
        "$RecentBusinessDays",
        "--stock-limit",
        "$StockLimit"
    )

if (-not $SkipBrowserSmoke) {
    Invoke-ExternalReadinessStep `
        -Label "web-view browser/mobile smoke" `
        -Arguments @(
            "-m",
            "stock_monitor",
            "web-view-browser-smoke",
            "--stock-limit",
            "$StockLimit"
        )
}

Write-Output ""
Write-Output "External web-view readiness checks completed."
Write-Output "- tunnel_target: http://127.0.0.1:8780"
Write-Output "- share only web-view; do not expose admin-gui."
Write-Output "- enable Cloudflare Access or an equivalent allow-list before sharing."
Write-Output "- after provider setup, run: python -m stock_monitor external-web-view-smoke --url https://YOUR-WEB-VIEW-URL --date YYYY-MM-DD --record-success --json"
Write-Output "- avoid router port forwarding as the default exposure path."
