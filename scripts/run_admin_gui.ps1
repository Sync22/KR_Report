param(
    [string]$PythonExe = "python",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $projectRoot

$logPath = Join-Path $projectRoot "data\admin-gui.log"
"$(Get-Date -Format o) starting admin-gui port=$Port python=$PythonExe root=$projectRoot" | Out-File -FilePath $logPath -Encoding utf8 -Append
& $PythonExe -m stock_monitor admin-gui --no-open --port $Port *>> $logPath
"$(Get-Date -Format o) admin-gui exited code=$LASTEXITCODE" | Out-File -FilePath $logPath -Encoding utf8 -Append
