param(
    [string]$PythonExe = "python",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8780,
    [switch]$AllowNonLoopback
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
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
Write-Output "- Default safe target remains http://127.0.0.1:8780."

& $PythonExe @argsList
exit $LASTEXITCODE
