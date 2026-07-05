$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Python runtime not found: $Python. Create the project .venv before running realtime-first review snapshots."
}

$LogDir = Join-Path $ProjectRoot "data\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "realtime-first-review-snapshot.log"

Push-Location $ProjectRoot
try {
    & $Python -m stock_monitor realtime-first-review-snapshot --date today --time 15:00 --output-dir data/reviews/realtime-first *>> $LogFile
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
