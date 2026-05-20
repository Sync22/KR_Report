param(
    [string]$PythonExe = "python",
    [int]$MinutesBefore = 5,
    [string]$PlannedTime = "16:50"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}

& $PythonExe -m stock_monitor krx-flow-login-reminder --minutes-before $MinutesBefore --planned-time $PlannedTime
