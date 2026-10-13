param([switch]$Status)

$projectRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $projectRoot 'web'
$port = 3010
$dotenvPath = Join-Path $projectRoot '.env'
$tossDotenvPath = Join-Path $projectRoot '.env.toss-openapi'
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCommand) { throw 'Node.js is required to start the Next.js preview.' }

$projectNextProcesses = Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue | Where-Object {
  $commandLine = [string]$_.CommandLine
  $portMatch = [regex]::Match($commandLine, '(?i)(?:--port|-p)\s+"?(\d+)')
  $commandLine.IndexOf($webRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
    $commandLine -match '(?i)\bnext(?:\.js)?\b' -and
    $commandLine -match '(?i)\b(start|dev)\b' -and
    $portMatch.Success -and [int]$portMatch.Groups[1].Value -eq $port
}
$listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $listener -and [int]$listener.OwningProcess -in @(0, 4)) { $listener = $null }
if ($null -eq $listener -and $null -ne $projectNextProcesses) {
  foreach ($candidate in $projectNextProcesses) {
    for ($attempt = 0; $attempt -lt 5 -and $null -eq $listener; $attempt++) {
      $listener = Get-NetTCPConnection -OwningProcess ([int]$candidate.ProcessId) -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -eq $port -and [string]$_.State -eq 'Listen' } |
        Select-Object -First 1
      if ($null -eq $listener) { Start-Sleep -Milliseconds 100 }
    }
    if ($null -ne $listener) { break }
  }
}
if ($null -eq $listener) {
  $listenPattern = "^\s*TCP\s+\S+:$port\s+\S+\s+LISTENING\s+(\d+)\s*$"
  $listenerLine = & netstat.exe -ano -p tcp 2>$null | Where-Object { $_ -match $listenPattern } | Select-Object -First 1
  if ($listenerLine) {
    $listenerPid = [regex]::Match($listenerLine, $listenPattern).Groups[1].Value
    if ([int]$listenerPid -notin @(0, 4)) { $listener = [pscustomobject]@{ OwningProcess = [int]$listenerPid } }
  }
}
$portResponds = Test-NetConnection -ComputerName '127.0.0.1' -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue

if ($null -ne $listener) {
  $ownerPid = [int]$listener.OwningProcess
  $projectNext = $projectNextProcesses | Where-Object { [int]$_.ProcessId -eq $ownerPid } | Select-Object -First 1
  if ($null -eq $projectNext) {
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerPid" -ErrorAction SilentlyContinue
    throw "Port 3010 is occupied by an unverified process (PID $ownerPid; $($owner.Name)); it was not stopped and no alternate port will be used."
  }
  if (-not $portResponds) {
    throw "This project's Next process exists for port 3010 (PID $ownerPid) but does not accept connections. Stop it normally in its server terminal before restarting."
  }
  try {
    $health = Invoke-WebRequest -Uri 'http://127.0.0.1:3010/health' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    $main = Invoke-WebRequest -Uri 'http://127.0.0.1:3010/' -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Output "Next.js preview is already running and healthy at http://127.0.0.1:3010 (PID $ownerPid; health $($health.StatusCode); Main $($main.StatusCode))."
  }
  catch {
    throw "This project's Next.js process owns port 3010 (PID $ownerPid), but its health check failed. Stop it normally in its server terminal, then restart this script on port 3010."
  }
  return
}

if ($null -ne $projectNextProcesses) {
  $projectNext = $projectNextProcesses | Select-Object -First 1
  if (-not $portResponds) {
    throw "This project's Next process exists for port 3010 (PID $($projectNext.ProcessId)) but does not accept connections. Stop it normally in its server terminal before restarting."
  }
  try {
    $health = Invoke-WebRequest -Uri 'http://127.0.0.1:3010/health' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    $main = Invoke-WebRequest -Uri 'http://127.0.0.1:3010/' -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($health.Headers['x-stock-monitor-service'] -ne 'next-web-view') {
      throw 'The health response does not identify this Stock Monitor Next service.'
    }
    Write-Output "Next.js preview is healthy at http://127.0.0.1:3010 (project process PID $($projectNext.ProcessId); health $($health.StatusCode); Main $($main.StatusCode); listener PID unavailable)."
  }
  catch {
    throw 'Port 3010 responds, but the project Next process could not be confirmed by its health identity and Main page. No process was stopped and no alternate port will be used.'
  }
  return
}

if ($portResponds) {
  throw 'Port 3010 accepts connections but the listener could not be confirmed as this project Next server. It was not stopped and no alternate port will be used.'
}

if ($Status) {
  Write-Output 'Next.js preview is stopped; port 3010 is free.'
  return
}

$runtimeKeys = @(
  'STOCK_MONITOR_DB_PATH',
  'STOCK_MONITOR_TIMEZONE',
  'STOCK_MONITOR_HOLIDAYS',
  'STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH',
  'STOCK_MONITOR_TOSS_OPENAPI_READY',
  'STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID',
  'STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET',
  'STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED',
  'STOCK_MONITOR_TOSS_OPENAPI_BASE_URL',
  'STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS'
)
$addedRuntimeKeys = @()

if (-not (Test-Path -LiteralPath $pythonExe)) {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($null -eq $pythonCommand) { throw 'Python is required to resolve Next.js runtime settings.' }
  $pythonExe = $pythonCommand.Source
}

if ((Test-Path -LiteralPath $dotenvPath) -or (Test-Path -LiteralPath $tossDotenvPath)) {
  $loader = @'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from stock_monitor.config import RuntimeConfig
from stock_monitor.fetch.toss_openapi import TOSS_OPENAPI_BASE_URL, TossOpenApiLabConfig

config = RuntimeConfig.from_env(root_dir=root)
toss = TossOpenApiLabConfig.from_env(root_dir=root)
db_path = config.db_path if config.db_path.is_absolute() else root / config.db_path
ready = bool(
    toss.live_enabled
    and toss.client_id
    and toss.client_secret
    and toss.base_url.rstrip("/") == TOSS_OPENAPI_BASE_URL
)
print(json.dumps({
    "STOCK_MONITOR_DB_PATH": str(db_path.resolve()),
    "STOCK_MONITOR_TIMEZONE": config.timezone,
    "STOCK_MONITOR_HOLIDAYS": ",".join(sorted(day.isoformat() for day in config.holiday_overrides)),
    "STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH": str(config.rotation_overlay_coordinates_path.resolve()),
    "STOCK_MONITOR_TOSS_OPENAPI_READY": str(ready).lower(),
    "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID": toss.client_id if ready else "",
    "STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET": toss.client_secret if ready else "",
    "STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED": str(toss.live_enabled).lower(),
    "STOCK_MONITOR_TOSS_OPENAPI_BASE_URL": toss.base_url,
    "STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS": str(toss.timeout_seconds),
}))
'@
  $loaderBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($loader))
  $pythonCommand = "import base64; exec(compile(base64.b64decode('$loaderBase64'), '<next-settings>', 'exec'))"
  $settingsJson = & $pythonExe -c $pythonCommand $projectRoot 2>&1
  $pythonExitCode = $LASTEXITCODE
  if ($pythonExitCode -ne 0) {
    $pythonErrorType = [regex]::Match(($settingsJson | Out-String), '(?m)^([A-Za-z][A-Za-z0-9]*(?:Error|Exception))(?::|$)').Groups[1].Value
    $pythonErrorSummary = if ($pythonErrorType) { ", $pythonErrorType" } else { '' }
    throw "Unable to load Next.js database and calendar settings (Python exit $pythonExitCode$pythonErrorSummary)."
  }
  try {
    $settings = $settingsJson | ConvertFrom-Json -ErrorAction Stop
  }
  catch {
    throw 'Unable to parse Next.js runtime settings.'
  }
  foreach ($key in $runtimeKeys) {
    if ($null -ne [Environment]::GetEnvironmentVariable($key, 'Process')) { continue }
    $property = $settings.PSObject.Properties[$key]
    if ($null -ne $property) {
      Set-Item -Path "Env:$key" -Value ([string]$property.Value)
      $addedRuntimeKeys += $key
    }
  }
}

$serverExitCode = 0
$transcriptStarted = $false
$locationPushed = $false
try {
  Push-Location $webRoot
  $locationPushed = $true
  $logDirectory = Join-Path $projectRoot 'logs'
  New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
  Start-Transcript -Path (Join-Path $logDirectory 'next-web-view.log') -Append | Out-Null
  $transcriptStarted = $true
  $nextCli = Join-Path $webRoot 'node_modules\next\dist\bin\next'
  & $nodeCommand.Source $nextCli start --hostname 127.0.0.1 --port $port
  $serverExitCode = $LASTEXITCODE
}
finally {
  if ($transcriptStarted) { Stop-Transcript | Out-Null }
  if ($locationPushed) { Pop-Location }
  foreach ($key in $addedRuntimeKeys) {
    Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue
  }
}

if ($serverExitCode -ne 0) {
  throw "Next.js exited with code $serverExitCode. Check logs/next-web-view.log and port 3010 ownership before retrying."
}
