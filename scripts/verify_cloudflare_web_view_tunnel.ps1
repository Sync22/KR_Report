param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [string]$PythonExe = "python",
    [string]$Date = "",
    [int]$RecentBusinessDays = 4,
    [int]$StockLimit = 20,
    [switch]$SkipLocalReadiness
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONIOENCODING = "utf-8"

try {
    $uri = [System.Uri]$Url
}
catch {
    throw "Url must be a valid absolute HTTPS provider origin, for example https://view.example.com"
}

if ($uri.Scheme -ne "https") {
    throw "Cloudflare web-view URL must use HTTPS."
}
if ($uri.IsLoopback) {
    throw "Cloudflare web-view URL must be the external provider origin, not localhost or loopback."
}
if (($uri.AbsolutePath -ne "/") -or $uri.Query -or $uri.Fragment) {
    throw "Cloudflare web-view URL must be the provider origin only, with no path, query, or fragment."
}

$providerOrigin = "$($uri.Scheme)://$($uri.Authority)"

function Invoke-CloudflareTunnelStep {
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
        Write-Output "Cloudflare web-view tunnel verification failed: $Label (exit code $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

Write-Output "Cloudflare web-view tunnel verification"
Write-Output "- provider_origin: $providerOrigin"
Write-Output "- local_tunnel_target_must_be: configured loopback web-view target"
Write-Output "- share only web-view; do not expose admin-gui."
Write-Output "- keep Cloudflare Access or an equivalent allow-list enabled before sharing."

Invoke-CloudflareTunnelStep `
    -Label "provider prerequisite gate" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "mini-pc-preflight",
        "--require-access-code",
        "--require-backup",
        "--require-env",
        "--require-mini-pc-profile"
    )

if (-not $SkipLocalReadiness) {
    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File (Join-Path $PSScriptRoot "verify_external_web_view_readiness.ps1") `
        -PythonExe $PythonExe `
        -RecentBusinessDays $RecentBusinessDays `
        -StockLimit $StockLimit
    if ($LASTEXITCODE -ne 0) {
        Write-Output ""
        Write-Output "Cloudflare web-view tunnel verification failed: local external readiness (exit code $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

$smokeArgs = @(
    "-m",
    "stock_monitor",
    "external-web-view-smoke",
    "--url",
    $providerOrigin,
    "--record-success",
    "--json"
)
if ($Date) {
    $smokeArgs += @("--date", $Date)
}

Invoke-CloudflareTunnelStep `
    -Label "external provider smoke with success record" `
    -Arguments $smokeArgs

Invoke-CloudflareTunnelStep `
    -Label "next-phase readiness after provider smoke" `
    -Arguments @(
        "-m",
        "stock_monitor",
        "next-phase-readiness",
        "--recent-report-dates",
        "5",
        "--stock-limit",
        "$StockLimit",
        "--json"
    )

Write-Output ""
Write-Output "Cloudflare web-view tunnel verification completed."
Write-Output "- provider smoke success is recorded only if the external HTTPS origin passed with zero issues."
Write-Output "- if next-phase-readiness still has blockers, continue with phone readability acceptance and market-day observation."
