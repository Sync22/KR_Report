param(
    [string]$PythonExe = "python",
    [string]$VenvPath = ".venv",
    [switch]$SkipPlaywrightInstall,
    [switch]$SkipReadinessCheck,
    [switch]$SkipPytest,
    [switch]$SkipOperatorStatus
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONIOENCODING = "utf-8"

if ([System.IO.Path]::IsPathRooted($VenvPath)) {
    $venvRoot = $VenvPath
}
else {
    $venvRoot = Join-Path $projectRoot $VenvPath
}
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Output "Creating virtual environment: $venvRoot"
    & $PythonExe -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "venv creation failed with exit code $LASTEXITCODE"
    }
}
else {
    Write-Output "Using existing virtual environment: $venvRoot"
}

Write-Output "Upgrading pip."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE"
}

Write-Output "Installing project in editable dev mode."
& $venvPython -m pip install -e .[dev]
if ($LASTEXITCODE -ne 0) {
    throw "project install failed with exit code $LASTEXITCODE"
}

if (-not $SkipPlaywrightInstall) {
    Write-Output "Installing Playwright Chromium browser."
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) {
        throw "playwright chromium install failed with exit code $LASTEXITCODE"
    }
}

if (-not $SkipReadinessCheck) {
    $readinessArgs = @{
        PythonExe = $venvPython
        SkipOperatorStatus = $true
        SkipBackupRequirement = $true
        SkipEnvRequirement = $true
    }
    if ($SkipPytest) {
        $readinessArgs.SkipPytest = $true
    }
    if ($SkipOperatorStatus) {
        Write-Output "Skipping operator-status readiness check was requested; this is already the setup default before scheduler registration."
    }
    if ($SkipPlaywrightInstall) {
        Write-Output "Skipping Playwright install was requested; readiness still checks DB/API/view state only."
    }
    & (Join-Path $projectRoot "scripts\verify_mini_pc_readiness.ps1") @readinessArgs
    if (-not $?) {
        throw "readiness verification failed"
    }
}

Write-Output "Mini PC Python environment setup completed."
Write-Output "- venv_python: $venvPython"
Write-Output "- scheduler_registration: .\scripts\register_mini_pc_scheduler_tasks.ps1 -PythonExe `"$venvPython`""
Write-Output "- scheduler_verification: .\scripts\verify_task_scheduler_registration.ps1 -PythonExe `"$venvPython`""
Write-Output "- web_view_restart: .\scripts\restart_web_view.ps1 -PythonExe `"$venvPython`""
