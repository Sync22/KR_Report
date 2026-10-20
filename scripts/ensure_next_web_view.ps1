param([int]$Port = 8780)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $projectRoot 'web'
$startScript = Join-Path $PSScriptRoot 'start_next_web_view.ps1'
$identityHeader = 'next-web-view'

function Get-ListenerProcess([int]$LocalPort) {
  $connections = @(Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue)
  if ($connections.Count -gt 0) {
    if (@($connections | Where-Object { $_.LocalAddress -ne '127.0.0.1' }).Count -gt 0) {
      throw "Port $LocalPort has a non-loopback listener; it was not stopped."
    }
    $connection = $connections | Select-Object -First 1
    $processId = [int]$connection.OwningProcess
  }
  else {
    $pattern = "^\s*TCP\s+(\S+):$LocalPort\s+\S+\s+LISTENING\s+(\d+)\s*$"
    $line = & netstat.exe -ano -p tcp 2>$null | Where-Object { $_ -match $pattern } | Select-Object -First 1
    if (-not $line) { return $null }
    $matches = [regex]::Match($line, $pattern)
    if ($matches.Groups[1].Value -ne '127.0.0.1') { throw "Port $LocalPort has a non-loopback listener; it was not stopped." }
    $processId = [int]$matches.Groups[2].Value
  }
  if ($processId -in @(0, 4)) { return [pscustomobject]@{ ProcessId = $processId; Process = $null } }
  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
  return [pscustomobject]@{ ProcessId = $processId; Process = $process }
}

function Test-ProjectNextProcess($Listener, [int]$LocalPort) {
  if ($null -eq $Listener -or $null -eq $Listener.Process) { return $false }
  $commandLine = [string]$Listener.Process.CommandLine
  $portMatch = [regex]::Match($commandLine, '(?i)(?:--port|-p)\s+"?(\d+)')
  return (
    $commandLine.IndexOf($webRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
    $commandLine -match '(?i)\bnext(?:\.js)?\b' -and
    $commandLine -match '(?i)\bstart\b' -and
    $commandLine -match '(?i)--hostname\s+"?127\.0\.0\.1\b' -and
    $portMatch.Success -and [int]$portMatch.Groups[1].Value -eq $LocalPort
  )
}

function Test-HealthyProjectNext([int]$LocalPort) {
  try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    $main = Invoke-WebRequest -Uri "http://127.0.0.1:$LocalPort/" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    return $health.StatusCode -eq 200 -and $health.Headers['x-stock-monitor-service'] -eq $identityHeader -and $main.StatusCode -eq 200
  }
  catch {
    return $false
  }
}

if (-not (Test-Path -LiteralPath $startScript)) { throw "Missing Next launcher: $startScript" }
$listener = Get-ListenerProcess -LocalPort $Port
if ($null -ne $listener) {
  if (-not (Test-ProjectNextProcess -Listener $listener -LocalPort $Port)) {
    $name = if ($null -eq $listener.Process) { 'unknown/system process' } else { [string]$listener.Process.Name }
    throw "Port $Port is occupied by an unverified process (PID $($listener.ProcessId); $name). It was not stopped."
  }
  if (-not (Test-HealthyProjectNext -LocalPort $Port)) {
    throw "Verified Next process on port $Port is not healthy. It was not stopped."
  }
  Write-Output "Existing project Next service is healthy at http://127.0.0.1:$Port (PID $($listener.ProcessId)); no child started."
  exit 0
}

$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`" -Port $Port"
$child = Start-Process -FilePath $powershell -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

for ($attempt = 0; $attempt -lt 60; $attempt++) {
  Start-Sleep -Milliseconds 500
  $listener = Get-ListenerProcess -LocalPort $Port
  if ($null -ne $listener) {
    if (Test-ProjectNextProcess -Listener $listener -LocalPort $Port) {
      if (Test-HealthyProjectNext -LocalPort $Port) {
        Write-Output "Started project Next service at http://127.0.0.1:$Port (PID $($listener.ProcessId); launcher PID $($child.Id))."
        exit 0
      }
    }
    else {
      throw "Port $Port became occupied by an unverified listener (PID $($listener.ProcessId)). It was not stopped."
    }
  }
  if ($child.HasExited) { throw "Next launcher exited with code $($child.ExitCode) before port $Port became healthy. Check logs/next-web-view.log." }
}

throw "Next did not become healthy on 127.0.0.1:$Port within 30 seconds. The child was left running for inspection; no listener was stopped."
