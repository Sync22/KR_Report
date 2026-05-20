param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [string]$ChecksumPath = "",
    [switch]$FailOnSensitiveEntries
)

$ErrorActionPreference = "Stop"

$resolvedArchive = Resolve-Path -LiteralPath $ArchivePath
if (-not $ChecksumPath) {
    $ChecksumPath = "$($resolvedArchive.Path).sha256"
}
$resolvedChecksum = Resolve-Path -LiteralPath $ChecksumPath

$checksumLine = (Get-Content -LiteralPath $resolvedChecksum.Path -Encoding ascii | Select-Object -First 1).Trim()
if (-not $checksumLine) {
    throw "Checksum file is empty: $($resolvedChecksum.Path)"
}

$expectedHash = ($checksumLine -split "\s+", 2)[0].Trim().ToUpperInvariant()
if (-not ($expectedHash -match "^[0-9A-F]{64}$")) {
    throw "Checksum file does not start with a SHA256 hash: $($resolvedChecksum.Path)"
}

$actualHash = (Get-FileHash -LiteralPath $resolvedArchive.Path -Algorithm SHA256).Hash.ToUpperInvariant()
if ($actualHash -ne $expectedHash) {
    throw "Archive hash mismatch: expected=$expectedHash actual=$actualHash archive=$($resolvedArchive.Path)"
}

Write-Output "SHA256 verified: $($resolvedArchive.Path)"
Write-Output "- sha256: $actualHash"
Write-Output "- checksum_file: $($resolvedChecksum.Path)"

$sensitiveEntries = @(
    ".env",
    "data/access_code.json",
    "data/backups",
    "data/restore-smoke",
    "Stock_Moniter_migration_*.zip",
    "Stock_Moniter_migration_*.zip.sha256",
    "*.log"
)
$archiveEntries = tar -tf $resolvedArchive.Path
if ($LASTEXITCODE -ne 0) {
    throw "Archive entry listing failed with exit code $LASTEXITCODE archive=$($resolvedArchive.Path)"
}
Write-Output "- archive_entries_checked: $($archiveEntries.Count)"
$normalizedArchiveEntries = @($archiveEntries | ForEach-Object { $_ -replace "\\", "/" })

$requiredEntries = @(
    "AGENTS.md",
    "README.md",
    "CHANGELOG.md",
    ".env.example",
    "pyproject.toml",
    "stock_research_monitor_mvp.md",
    "src/stock_monitor/cli.py",
    "data/stock_monitor.db",
    "example/Cycle.jpg",
    "data/rotation_overlay_coordinates.json",
    "data/rotation_image_aliases.json",
    "data/rotation_etf_candidates.json",
    "docs/codex/documentation-index.md",
    "docs/codex/current-work.md",
    "docs/codex/next-phase.md",
    "docs/codex/execution-roadmap.md",
    "docs/codex/project-map.md",
    "docs/codex/surface-contract.md",
    "docs/codex/data-quality-checklist.md",
    "docs/codex/data-source-policy.md",
    "docs/codex/krx-market-data-runbook.md",
    "docs/codex/krx-18m-backfill-analysis.md",
    "docs/codex/data-rebaseline-plan.md",
    "docs/codex/admin-gui-plan.md",
    "docs/codex/agent-guide.md",
    "docs/codex/module-ownership.md",
    "docs/codex/agent-reassessment.md",
    "docs/codex/rotation-overlay-plan.md",
    "docs/codex/mini-pc-migration-handoff.md",
    "scripts/register_task_scheduler_tasks.ps1",
    "scripts/create_migration_archive.ps1",
    "scripts/disable_source_desktop_scheduler_tasks.ps1",
    "scripts/setup_mini_pc_environment.ps1",
    "scripts/register_mini_pc_scheduler_tasks.ps1",
    "scripts/restart_web_view.ps1",
    "scripts/verify_external_web_view_readiness.ps1",
    "scripts/verify_cloudflare_web_view_tunnel.ps1",
    "scripts/verify_migration_archive.ps1",
    "scripts/verify_mini_pc_readiness.ps1",
    "scripts/verify_market_day_observation.ps1",
    "scripts/verify_next_phase_closeout.ps1",
    "scripts/verify_task_scheduler_registration.ps1",
    "scripts/run_scheduled_krx_daily_backfill.ps1",
    "scripts/run_scheduled_notify.ps1",
    "scripts/run_scheduled_poll.ps1",
    "scripts/run_scheduled_krx_mentioned_flow_backfill.ps1",
    "scripts/run_process_telegram_commands.ps1",
    "scripts/restart_web_view.ps1",
    "scripts/run_scheduled_shutdown.ps1"
)

function Test-RequiredArchiveEntry([string[]]$NormalizedEntries, [string]$RequiredEntry) {
    foreach ($normalizedEntry in $NormalizedEntries) {
        if ($normalizedEntry -eq $RequiredEntry) {
            return $true
        }
        if ($normalizedEntry.EndsWith("/$RequiredEntry")) {
            return $true
        }
    }
    return $false
}

$missingRequiredEntries = @()
foreach ($requiredEntry in $requiredEntries) {
    if (-not (Test-RequiredArchiveEntry -NormalizedEntries $normalizedArchiveEntries -RequiredEntry $requiredEntry)) {
        $missingRequiredEntries += $requiredEntry
    }
}
if ($missingRequiredEntries.Count -gt 0) {
    throw "Missing required migration entries: $($missingRequiredEntries -join ', ')"
}
Write-Output "- required_entries: ok"

function Test-SensitiveArchiveEntry([string]$NormalizedEntry, [string]$SensitiveEntry) {
    if ($NormalizedEntry -eq $SensitiveEntry) {
        return $true
    }
    if ($SensitiveEntry -eq ".env" -and $NormalizedEntry.EndsWith("/.env")) {
        return $true
    }
    if ($SensitiveEntry -eq "data/access_code.json" -and $NormalizedEntry.EndsWith("/data/access_code.json")) {
        return $true
    }
    if ($SensitiveEntry -eq "data/backups" -and ($NormalizedEntry -eq "data/backups" -or $NormalizedEntry.Contains("/data/backups/"))) {
        return $true
    }
    if ($SensitiveEntry -eq "data/restore-smoke" -and ($NormalizedEntry -eq "data/restore-smoke" -or $NormalizedEntry.Contains("/data/restore-smoke/"))) {
        return $true
    }
    if ($SensitiveEntry -eq "*.log" -and $NormalizedEntry.EndsWith(".log")) {
        return $true
    }
    if ($SensitiveEntry -like "Stock_Moniter_migration_*") {
        $leaf = Split-Path -Leaf $NormalizedEntry
        if ($leaf -like $SensitiveEntry) {
            return $true
        }
    }
    return $false
}

$foundSensitiveEntries = @()
foreach ($normalizedEntry in $normalizedArchiveEntries) {
    foreach ($sensitiveEntry in $sensitiveEntries) {
        if (Test-SensitiveArchiveEntry -NormalizedEntry $normalizedEntry -SensitiveEntry $sensitiveEntry) {
            $foundSensitiveEntries += $normalizedEntry
        }
    }
}

if ($foundSensitiveEntries.Count -gt 0) {
    Write-Warning "Sensitive migration entries detected: $($foundSensitiveEntries -join ', ')"
    Write-Warning "Treat this archive as sensitive and prefer setting access-code/.env directly on the target host."
    if ($FailOnSensitiveEntries) {
        throw "Sensitive migration entries are not allowed: $($foundSensitiveEntries -join ', ')"
    }
}
else {
    Write-Output "- sensitive_entries: none"
}
