param(
    [string]$PythonExe = "python",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = (87 * 100 + 80),
    [int]$HealthTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runScript = Join-Path $PSScriptRoot "run_web_view.ps1"
$healthUrl = "http://${HostAddress}:${Port}/health"

Set-Location -LiteralPath $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONIOENCODING = "utf-8"

Write-Output "Restarting read-only web-view"
Write-Output "- bind: ${HostAddress}:${Port}"
Write-Output "- Cloudflare Tunnel target candidate: http://${HostAddress}:${Port}"
Write-Output "- Do not expose admin-gui, /api/status, scheduler, settings, DB, .env, Telegram, or shell/control endpoints."

function Get-ListeningProcessIdsForPort {
    param([int]$TargetPort)

    $processIds = @()
    $lines = netstat -ano | Select-String -Pattern ":$TargetPort\s+.*LISTENING\s+\d+"
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim() -split "\s+")
        if ($parts.Count -lt 5) {
            continue
        }
        $localAddress = [string]$parts[1]
        $state = [string]$parts[3]
        $pidText = [string]$parts[4]
        if ($state -ne "LISTENING") {
            continue
        }
        if ($localAddress -notmatch ":$TargetPort$") {
            continue
        }
        $parsedPid = 0
        if ([int]::TryParse($pidText, [ref]$parsedPid) -and $parsedPid -gt 0) {
            $processIds += $parsedPid
        }
    }
    return $processIds | Sort-Object -Unique
}

$existingProcessIds = @(Get-ListeningProcessIdsForPort -TargetPort $Port)
foreach ($processId in $existingProcessIds) {
    try {
        Write-Output "- stopping existing web-view listener pid=$processId"
        Stop-Process -Id $processId -Force -ErrorAction Stop
    }
    catch {
        Write-Output "- warning: failed to stop pid=${processId}: $($_.Exception.Message)"
    }
}

if ($existingProcessIds.Count -gt 0) {
    Start-Sleep -Seconds 2
}

$startArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $runScript,
    "-PythonExe",
    $PythonExe,
    "-HostAddress",
    $HostAddress,
    "-Port",
    $Port
)

Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $startArgs `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden | Out-Null

$deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
do {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            Write-Output "- health: $($response.StatusCode) $($response.Content)"
            Write-Output "web-view restarted."
            exit 0
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
} while ((Get-Date) -lt $deadline)

throw "web-view did not become healthy at $healthUrl within ${HealthTimeoutSeconds}s"
