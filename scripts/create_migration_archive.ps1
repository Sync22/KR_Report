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

$databaseSidecarPaths = @(
    (Join-Path $projectRoot "data/stock_monitor.db-wal"),
    (Join-Path $projectRoot "data/stock_monitor.db-shm"),
    (Join-Path $projectRoot "data/stock_monitor.db-journal")
)
$existingDatabaseSidecars = @($databaseSidecarPaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
if ($existingDatabaseSidecars.Count -gt 0) {
    $sidecarNames = @($existingDatabaseSidecars | ForEach-Object { Split-Path -Leaf $_ })
    throw "Cannot create a migration archive while SQLite sidecar files exist: $($sidecarNames -join ', '). Stop all DB readers and writers, create a consistent DB snapshot, then retry. Do not delete sidecars manually."
}

$excludedDirectories = @(
    ".git",
    ".codegraph",
    ".codex",
    ".codex-remote-attachments",
    ".playwright-mcp",
    ".vscode",
    ".idea",
    ".pytest_cache",
    ".tmp_pytest",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
    "build",
    "dist",
    "error_logs",
    "output",
    "playwright-report",
    "test-results",
    "_tmp_webview",
    "snapshots",
    "*_snapshot",
    "*.egg-info",
    "operator_photo_inbox",
    "docs/codex/operations",
    "scripts/experimental/.venv-botasaurus",
    "scripts/experimental/.venv-scrapling",
    "scripts/experimental/.venv-kronos",
    "scripts/experimental/.hf-kronos",
    "scripts/experimental/.codegraph",
    "scripts/experimental/codex_home_probe",
    "scripts/experimental/node_tooling"
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
    "*.zip",
    "*.zip.sha256",
    "*.7z",
    "*.log",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
    "*.der",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "*.sqlite-wal",
    "*.sqlite-shm",
    "*.sqlite-journal",
    "*.sqlite3-wal",
    "*.sqlite3-shm",
    "*.sqlite3-journal",
    "*.db-wal",
    "*.db-shm",
    "*.db-journal",
    "*.tsbuildinfo",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    '*$py.class',
    "*.code-workspace",
    ".tmp_admin_gui.*",
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
    $leaf = Split-Path -Leaf $relative
    if ($leaf -eq ".env.toss-openapi" -or ($leaf -like ".env.*" -and $leaf -notlike "*.example")) {
        return $true
    }
    if ($relative -eq ".env" -and -not $IncludeEnv) {
        return $true
    }
    if ($leaf -eq ".env" -and $relative -ne ".env") {
        return $true
    }
    if ($leaf -like "*.env" -and $leaf -ne ".env") {
        return $true
    }
    if ($relative -eq "data/access_code.json") {
        return $true
    }
    foreach ($directory in $excludedDirectories) {
        if ($relative -eq $directory -or $relative.StartsWith("$directory/") -or $relative.Contains("/$directory/") -or ($relative.Split("/") | Where-Object { $_ -like $directory })) {
            return $true
        }
    }
    foreach ($file in $excludedFiles) {
        if ($relative -eq $file) {
            return $true
        }
    }
    foreach ($filePattern in $excludedFilePatterns) {
        if ($relative -eq "data/stock_monitor.db" -and $filePattern -eq "*.db") {
            continue
        }
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
