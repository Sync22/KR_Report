param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$srcPath = Join-Path $projectRoot "src"
if (Test-Path -LiteralPath $srcPath) {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$srcPath$([IO.Path]::PathSeparator)$env:PYTHONPATH" } else { $srcPath }
}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$today = Get-Date -Format "yyyy-MM-dd"
& $PythonExe -m stock_monitor toss-market-context-capture `
    --date $today `
    --live `
    --confirm-token-reissue `
    --confirm-save `
    --scheduled
exit $LASTEXITCODE
