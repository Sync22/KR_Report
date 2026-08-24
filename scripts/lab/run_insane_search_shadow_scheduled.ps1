param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("12:00", "15:00")]
    [string]$Slot,
    [string]$RunDate = (Get-Date).ToString("yyyy-MM-dd"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$cutoff = [DateTimeOffset]::ParseExact(
    "${RunDate}T${Slot}:00+09:00",
    "yyyy-MM-ddTHH:mm:sszzz",
    [Globalization.CultureInfo]::InvariantCulture
)

if ($DryRun) {
    [ordered]@{
        dry_run = $true
        cutoff = $cutoff.ToString("yyyy-MM-ddTHH:mm:sszzz")
        slot = $Slot
    } | ConvertTo-Json -Compress
    exit 0
}

$projectPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$enginePython = Join-Path $env:USERPROFILE "Codex\_tools\insane-search\.venv\Scripts\python.exe"
$engineRoot = Join-Path $env:USERPROFILE ".codex\plugins\cache\gptaku-codex\insane-search-codex\0.8.2\skills\insane-search\engine"
$runner = Join-Path $projectRoot "scripts\lab\run_insane_search_shadow.py"
$logPath = Join-Path $projectRoot "docs\codex\operations\insane-search-shadow-task.log"

foreach ($requiredPath in @($projectPython, $enginePython, $engineRoot, $runner)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required isolated shadow-run path is missing: $requiredPath"
    }
}

$logDirectory = Split-Path -Parent $logPath
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
Set-Location $projectRoot

& $projectPython $runner `
    --cutoff $cutoff.ToString("yyyy-MM-ddTHH:mm:sszzz") `
    --engine-python $enginePython `
    --engine-root $engineRoot 2>&1 | Out-File -FilePath $logPath -Append -Encoding utf8
$runExitCode = $LASTEXITCODE

if ($runExitCode -eq 0 -and $Slot -eq "15:00") {
    & $projectPython $runner --aggregate 2>&1 | Out-File -FilePath $logPath -Append -Encoding utf8
}

exit $runExitCode
