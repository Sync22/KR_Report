param(
    [string]$DestinationPath = "",
    [switch]$IncludeEnv,
    [switch]$IncludeBackups,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$parentDir = Split-Path -Parent $projectRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmm"

if (-not $DestinationPath) {
    $DestinationPath = Join-Path $parentDir "Stock_Moniter_migration_$timestamp.zip"
}

if (-not $SkipPreflight) {
    Push-Location $projectRoot
    try {
        python -m stock_monitor mini-pc-preflight --require-backup --require-env
    }
    finally {
        Pop-Location
    }
}

$excludedDirectories = @(
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "_tmp_webview",
    "playwright-report",
    "scripts/experimental/.venv-botasaurus",
    "scripts/experimental/.venv-kronos"
)

if (-not $IncludeBackups) {
    $excludedDirectories += "data/backups"
    $excludedDirectories += "data/restore-smoke"
}

$excludedFiles = @(
    "webview_stdout.log",
    "webview_stderr.log"
)

$excludedFilePatterns = @(
    "Stock_Moniter_migration_*.zip",
    "Stock_Moniter_migration_*.zip.sha256",
    "*.log",
    "data/*.log"
)

if (-not $IncludeEnv) {
    $excludedFiles += ".env"
}

function Convert-ToRelativePath([string]$Path) {
    $relative = Resolve-Path -LiteralPath $Path -Relative
    $relative = $relative -replace "^[.][\\/]", ""
    $relative = $relative -replace "\\", "/"
    return $relative
}

function Test-ExcludedPath([string]$Path) {
    $relative = Convert-ToRelativePath $Path
    if (-not $IncludeEnv -and $relative -eq ".env") {
        return $true
    }
    if ($relative -eq "data/access_code.json") {
        return $true
    }
    foreach ($directory in $excludedDirectories) {
        if ($relative -eq $directory -or $relative.StartsWith("$directory/")) {
            return $true
        }
    }
    foreach ($file in $excludedFiles) {
        if ($relative -eq $file) {
            return $true
        }
    }
    foreach ($filePattern in $excludedFilePatterns) {
        if ($relative -like $filePattern -or (Split-Path -Leaf $relative) -like $filePattern) {
            return $true
        }
    }
    if ($relative -like "*.pyc") {
        return $true
    }
    return $false
}

$files = Get-ChildItem -LiteralPath $projectRoot -Recurse -File -Force |
    Where-Object { -not (Test-ExcludedPath $_.FullName) }

if (-not $files) {
    throw "No files selected for migration archive."
}

if (Test-Path -LiteralPath $DestinationPath) {
    Remove-Item -LiteralPath $DestinationPath -Force
}

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) "stock_monitor_migration_$timestamp"
if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingRoot | Out-Null

try {
    foreach ($file in $files) {
        $relative = Convert-ToRelativePath $file.FullName
        $target = Join-Path $stagingRoot $relative
        $targetDir = Split-Path -Parent $target
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    }

    Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $DestinationPath -CompressionLevel Optimal
    $hash = Get-FileHash -LiteralPath $DestinationPath -Algorithm SHA256
    $hashPath = "$DestinationPath.sha256"
    "$($hash.Hash)  $(Split-Path -Leaf $DestinationPath)" | Out-File -LiteralPath $hashPath -Encoding ascii -Force
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

Write-Output "Migration archive created: $DestinationPath"
Write-Output "SHA256 checksum: $hashPath"
Write-Output "- project: $projectRoot"
Write-Output "- files: $($files.Count)"
Write-Output "- include_env: $IncludeEnv"
Write-Output "- access_code: always excluded"
Write-Output "- include_backups: $IncludeBackups"
