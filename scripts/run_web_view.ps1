param(
    [string]$PythonExe = "python",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = (87 * 100 + 80),
    [switch]$AllowNonLoopback
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "resolve_project_python.ps1")
$PythonExe = Resolve-StockMonitorPython -ProjectRoot $projectRoot -PythonExe $PythonExe
Set-Location -LiteralPath $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONIOENCODING = "utf-8"

$argsList = @("-m", "stock_monitor", "web-view", "--host", $HostAddress, "--port", $Port, "--no-open")
if ($AllowNonLoopback) {
    $argsList += "--allow-non-loopback"
}

Write-Output "Starting read-only web-view"
Write-Output "- bind: ${HostAddress}:${Port}"
Write-Output "- Cloudflare Tunnel target candidate: http://${HostAddress}:${Port}"
Write-Output "- Do not expose admin-gui, /api/status, scheduler, settings, DB, .env, Telegram, or shell/control endpoints."
Write-Output "- Keep Cloudflare Access or an equivalent allow-list enabled before sharing."
Write-Output "- Default safe target remains the configured loopback web-view target."

& $PythonExe @argsList
exit $LASTEXITCODE
