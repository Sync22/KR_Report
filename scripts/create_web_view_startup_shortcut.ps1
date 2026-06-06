param(
    [string]$PythonExe = "python",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = (87 * 100 + 80),
    [string]$ShortcutName = "StockMonitor-WebView.lnk",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$webViewScript = Join-Path $PSScriptRoot "run_web_view.ps1"
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir $ShortcutName

if ($HostAddress -ne "127.0.0.1" -and $HostAddress -ne "localhost") {
    throw "web-view startup shortcut must target loopback only. Use the configured loopback web-view target for Cloudflare Tunnel; do not expose admin-gui."
}

if ($Remove) {
    if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
        Write-Output "Removed web-view Startup shortcut: $shortcutPath"
    }
    else {
        Write-Output "No web-view Startup shortcut found: $shortcutPath"
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $webViewScript)) {
    throw "Missing web-view runner script: $webViewScript"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$webViewScript`" -PythonExe `"$PythonExe`" -HostAddress $HostAddress -Port $Port"
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Start Stock Monitor read-only web-view on $HostAddress`:$Port for Cloudflare Tunnel. Do not expose admin-gui."
$shortcut.Save()

Write-Output "Created web-view Startup shortcut: $shortcutPath"
Write-Output "- target: http://${HostAddress}:${Port}"
Write-Output "- Cloudflare Tunnel should point only to the configured loopback web-view target."
Write-Output "- Do not expose admin-gui, scheduler, settings, DB, .env, Telegram, or shell/control endpoints."
