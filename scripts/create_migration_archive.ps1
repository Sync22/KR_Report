param(
    [string]$DestinationPath = "",
    [string]$PythonExe = "",
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
$DestinationPath = [System.IO.Path]::GetFullPath($DestinationPath)
if ([System.IO.Path]::GetExtension($DestinationPath) -ine ".zip") {
    throw "DestinationPath must end in .zip."
}
$destinationDirectory = Split-Path -Parent $DestinationPath
if (-not (Test-Path -LiteralPath $destinationDirectory -PathType Container)) {
    throw "Destination directory does not exist: $destinationDirectory"
}

if (-not $PythonExe) {
    $projectVenvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    $PythonExe = if (Test-Path -LiteralPath $projectVenvPython) {
        (Resolve-Path -LiteralPath $projectVenvPython).Path
    }
    else {
        (Get-Command python -ErrorAction Stop).Source
    }
}
$snapshotHelper = Join-Path $PSScriptRoot "create_migration_archive_snapshot.py"
if (-not (Test-Path -LiteralPath $snapshotHelper -PathType Leaf)) {
    throw "Missing migration archive snapshot helper: $snapshotHelper"
}

if (-not $SkipPreflight) {
    Push-Location $projectRoot
    try {
        & $PythonExe -m stock_monitor mini-pc-preflight --require-backup --require-env
        if ($LASTEXITCODE -ne 0) {
            throw "Migration archive preflight failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

$resolvedDatabasePath = & $PythonExe $snapshotHelper resolve-db-path $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw "Migration archive database path resolution failed with exit code $LASTEXITCODE"
}
$sourceDatabasePath = [System.IO.Path]::GetFullPath(($resolvedDatabasePath | Out-String).Trim())
$excludedDatabasePaths = @(
    $sourceDatabasePath,
    "$sourceDatabasePath-wal",
    "$sourceDatabasePath-shm",
    "$sourceDatabasePath-journal"
) | ForEach-Object { [System.IO.Path]::GetFullPath($_) }

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
    "web/node_modules",
    "web/.next",
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
    "*.delivery.lock",
    "*.zip.publication.lock",
    "telegram_control_state.json.lock",
    "telegram_control_state.json.write.lock",
    ".telegram_control_state.json.*.tmp",
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
        if ($IncludeBackups -and $filePattern -in @("*.db", "*.sqlite", "*.sqlite3") -and
            ($relative -like "data/backups/*" -or $relative -like "data/restore-smoke/*")) {
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

$hashPath = "$DestinationPath.sha256"
$files = Get-ChildItem -LiteralPath $projectRoot -Recurse -File -Force |
    Where-Object {
        $_.FullName -ne $DestinationPath -and
        $_.FullName -ne $hashPath -and
        $_.FullName -notin $excludedDatabasePaths -and
        -not (Test-ExcludedPath $_.FullName)
    }

if (-not $files) {
    throw "No files selected for migration archive."
}

$stagingId = [guid]::NewGuid().ToString("N")
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) "stock_monitor_migration_$stagingId"
$stagingArchivePath = Join-Path $destinationDirectory "Stock_Moniter_migration_stage_$stagingId.zip"
$stagingChecksumPath = "$stagingArchivePath.sha256"
$previousArchivePath = Join-Path $destinationDirectory "Stock_Moniter_migration_previous_$stagingId.zip"
$previousChecksumPath = "$previousArchivePath.sha256"
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

    $stagingDatabasePath = Join-Path $stagingRoot "data\stock_monitor.db"
    & $PythonExe $snapshotHelper snapshot $sourceDatabasePath $stagingDatabasePath
    if ($LASTEXITCODE -ne 0) {
        throw "Migration archive SQLite snapshot failed with exit code $LASTEXITCODE"
    }

    Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $stagingArchivePath -CompressionLevel Optimal
    if (-not (Test-Path -LiteralPath $stagingArchivePath -PathType Leaf)) {
        throw "Migration archive ZIP was not created: $stagingArchivePath"
    }
    & $PythonExe $snapshotHelper verify-archive $stagingArchivePath
    if ($LASTEXITCODE -ne 0) {
        throw "Migration archive ZIP SQLite verification failed with exit code $LASTEXITCODE"
    }

    $hash = Get-FileHash -LiteralPath $stagingArchivePath -Algorithm SHA256
    "$($hash.Hash)  $(Split-Path -Leaf $DestinationPath)" | Out-File -LiteralPath $stagingChecksumPath -Encoding ascii -Force

    $publicationLockStream = $null
    try {
        try {
            $publicationLockStream = [System.IO.File]::Open(
                "$DestinationPath.publication.lock",
                [System.IO.FileMode]::OpenOrCreate,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
        }
        catch [System.IO.IOException] {
            throw "Another archive publisher is active for $DestinationPath"
        }

        $hadArchive = Test-Path -LiteralPath $DestinationPath -PathType Leaf
        $hadChecksum = Test-Path -LiteralPath $hashPath -PathType Leaf
        $archiveBackedUp = $false
        $checksumBackedUp = $false
        try {
            if ($hadArchive) {
                Move-Item -LiteralPath $DestinationPath -Destination $previousArchivePath
                $archiveBackedUp = $true
            }
            if ($hadChecksum) {
                Move-Item -LiteralPath $hashPath -Destination $previousChecksumPath
                $checksumBackedUp = $true
            }
            Move-Item -LiteralPath $stagingArchivePath -Destination $DestinationPath
            Move-Item -LiteralPath $stagingChecksumPath -Destination $hashPath
        }
        catch {
            if (($archiveBackedUp -or -not $hadArchive) -and (Test-Path -LiteralPath $DestinationPath)) {
                Remove-Item -LiteralPath $DestinationPath -Force
            }
            if (($checksumBackedUp -or -not $hadChecksum) -and (Test-Path -LiteralPath $hashPath)) {
                Remove-Item -LiteralPath $hashPath -Force
            }
            if ($archiveBackedUp -and (Test-Path -LiteralPath $previousArchivePath)) {
                Move-Item -LiteralPath $previousArchivePath -Destination $DestinationPath -Force
            }
            if ($checksumBackedUp -and (Test-Path -LiteralPath $previousChecksumPath)) {
                Move-Item -LiteralPath $previousChecksumPath -Destination $hashPath -Force
            }
            throw
        }

        if ($archiveBackedUp) { Remove-Item -LiteralPath $previousArchivePath -Force }
        if ($checksumBackedUp) { Remove-Item -LiteralPath $previousChecksumPath -Force }
    }
    finally {
        if ($null -ne $publicationLockStream) {
            $publicationLockStream.Dispose()
        }
    }
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
    foreach ($path in @($stagingArchivePath, $stagingChecksumPath)) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
}

Write-Output "Migration archive created: $DestinationPath"
Write-Output "SHA256 checksum: $hashPath"
Write-Output "- project: $projectRoot"
Write-Output "- files: $($files.Count)"
Write-Output "- include_env: $IncludeEnv"
Write-Output "- access_code: always excluded"
Write-Output "- include_backups: $IncludeBackups"
