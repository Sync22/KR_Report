param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8780,
    [string]$ShortcutName = "StockMonitor-WebView.lnk",
    [switch]$UsePython,
    [string]$PythonExe = "python",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$webViewScript = if ($UsePython) { Join-Path $PSScriptRoot "run_web_view.ps1" } else { Join-Path $PSScriptRoot "ensure_next_web_view.ps1" }
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

if ($UsePython) {
    . (Join-Path $PSScriptRoot "resolve_project_python.ps1")
    $PythonExe = Resolve-StockMonitorPython -ProjectRoot $projectRoot -PythonExe $PythonExe
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = if ($UsePython) {
    "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$webViewScript`" -PythonExe `"$PythonExe`" -HostAddress $HostAddress -Port $Port"
} else {
    "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$webViewScript`" -Port $Port"
}
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = if ($UsePython) { "Start Stock Monitor Python web-view on $HostAddress`:$Port for rollback. Do not expose admin-gui." } else { "Ensure Stock Monitor Next web-view on $HostAddress`:$Port for the existing tunnel target. Do not expose admin-gui." }
$shortcut.Save()

Write-Output "Created web-view Startup shortcut: $shortcutPath"
Write-Output "- target: http://${HostAddress}:${Port}"
Write-Output "- Cloudflare Tunnel should point only to the configured loopback web-view target."
Write-Output "- Do not expose admin-gui, scheduler, settings, DB, .env, Telegram, or shell/control endpoints."
