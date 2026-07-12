import hashlib
import subprocess
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MIGRATION_ENTRIES = [
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
    "docs/codex/operating-guide.md",
    "docs/codex/architecture-guide.md",
    "docs/codex/surface-guide.md",
    "docs/codex/data-governance.md",
    "docs/codex/market-data-runbook.md",
    "docs/codex/candidate-evidence.md",
    "docs/codex/news-intelligence.md",
    "docs/codex/decision-journal.md",
    "docs/codex/toss-openapi-lab.md",
    "docs/codex/mini-pc-runbook.md",
    "scripts/register_task_scheduler_tasks.ps1",
    "scripts/create_migration_archive.ps1",
    "scripts/disable_source_desktop_scheduler_tasks.ps1",
    "scripts/setup_mini_pc_environment.ps1",
    "scripts/register_mini_pc_scheduler_tasks.ps1",
    "scripts/verify_external_web_view_readiness.ps1",
    "scripts/verify_cloudflare_web_view_tunnel.ps1",
    "scripts/verify_migration_archive.ps1",
    "scripts/verify_mini_pc_readiness.ps1",
    "scripts/verify_market_day_observation.ps1",
    "scripts/verify_next_phase_closeout.ps1",
    "scripts/verify_task_scheduler_registration.ps1",
    "scripts/restart_web_view.ps1",
    "scripts/run_scheduled_krx_daily_backfill.ps1",
    "scripts/run_scheduled_notify.ps1",
    "scripts/run_scheduled_poll.ps1",
    "scripts/run_scheduled_krx_mentioned_flow_backfill.ps1",
    "scripts/run_scheduled_market_briefing_slot.ps1",
    "scripts/run_scheduled_toss_priority_baseline.ps1",
    "scripts/run_process_telegram_commands.ps1",
    "scripts/run_scheduled_shutdown.ps1",
]


def _write_required_migration_entries(archive: zipfile.ZipFile) -> None:
    for entry in REQUIRED_MIGRATION_ENTRIES:
        archive.writestr(f"02.Stock_Moniter/{entry}", "required\n")


def test_register_task_scheduler_keeps_krx_flow_reminder_opt_in() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert "[switch]$IncludeKrxFlowReminder" in script
    assert "if ($IncludeKrxFlowReminder)" in script
    assert "[switch]$SkipKrxFlowReminder" not in script


def test_krx_openapi_availability_probe_is_not_registered_by_default() -> None:
    script_paths = [
        PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1",
        PROJECT_ROOT / "scripts" / "register_mini_pc_scheduler_tasks.ps1",
        PROJECT_ROOT / "scripts" / "verify_task_scheduler_registration.ps1",
        PROJECT_ROOT / "scripts" / "verify_mini_pc_readiness.ps1",
    ]

    for script_path in script_paths:
        script = script_path.read_text(encoding="utf-8")
        assert "krx-openapi-availability-probe" not in script
        assert "run_krx_openapi_availability_probe.ps1" not in script


def test_krx_daily_backfill_defaults_to_next_business_day_official_window() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert '[string]$KrxDailyBackfillTime = "08:10"' in script
    assert '[string]$KrxDailyBackfillEnd = "08:10"' in script
    assert '[string]$KrxDailyBackfillTime = "00:10"' not in script
    assert '[string]$KrxDailyBackfillEnd = "12:10"' not in script


def test_create_migration_archive_excludes_secrets_and_transient_files_by_default() -> None:
    script = (PROJECT_ROOT / "scripts" / "create_migration_archive.ps1").read_text(encoding="utf-8")

    assert "[switch]$IncludeEnv" in script
    assert "[switch]$IncludeBackups" in script
    assert "mini-pc-preflight --require-backup --require-env" in script
    assert '$relative -eq ".env"' in script
    assert '$relative -eq "data/access_code.json"' in script
    assert "scripts/experimental/.venv-botasaurus" in script
    assert "scripts/experimental/.venv-kronos" in script
    assert "data/backups" in script
    assert "access_code: always excluded" in script
    assert "Compress-Archive" in script
    assert "Stock_Moniter_migration_*.zip" in script
    assert "Stock_Moniter_migration_*.zip.sha256" in script
    assert "*.log" in script
    assert "data/*.log" in script
    assert "Get-FileHash" in script
    assert ".sha256" in script


def test_verify_migration_archive_checks_sha256_sidecar() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1").read_text(encoding="utf-8")

    assert "[string]$ArchivePath" in script
    assert "[switch]$FailOnSensitiveEntries" in script
    assert "Get-FileHash" in script
    assert ".sha256" in script
    assert "SHA256 verified" in script
    assert "Archive hash mismatch" in script
    assert ".env" in script
    assert "data/access_code.json" in script
    assert "data/backups" in script
    assert "data/restore-smoke" in script
    assert "Stock_Moniter_migration_*.zip" in script
    assert "*.log" in script
    assert "Sensitive migration entries detected" in script
    assert "Archive entry listing failed" in script
    assert "$LASTEXITCODE" in script
    assert 'EndsWith("/.env")' in script
    assert 'EndsWith("/data/access_code.json")' in script
    assert "$foundSensitiveEntries += $normalizedEntry" in script
    assert "archive_entries_checked" in script
    assert "Sensitive migration entries are not allowed" in script
    assert "$requiredEntries" in script
    assert "AGENTS.md" in script
    assert "CHANGELOG.md" in script
    assert ".env.example" in script
    assert "stock_research_monitor_mvp.md" in script
    assert "data/stock_monitor.db" in script
    assert "example/Cycle.jpg" in script
    assert "data/rotation_overlay_coordinates.json" in script
    assert "data/rotation_image_aliases.json" in script
    assert "data/rotation_etf_candidates.json" in script
    assert "docs/codex/documentation-index.md" in script
    assert "docs/codex/operating-guide.md" in script
    assert "docs/codex/architecture-guide.md" in script
    assert "docs/codex/surface-guide.md" in script
    assert "docs/codex/data-governance.md" in script
    assert "docs/codex/market-data-runbook.md" in script
    assert "docs/codex/candidate-evidence.md" in script
    assert "docs/codex/news-intelligence.md" in script
    assert "docs/codex/decision-journal.md" in script
    assert "docs/codex/toss-openapi-lab.md" in script
    assert "docs/codex/mini-pc-runbook.md" in script
    assert "scripts/register_task_scheduler_tasks.ps1" in script
    assert "scripts/create_migration_archive.ps1" in script
    assert "scripts/disable_source_desktop_scheduler_tasks.ps1" in script
    assert "scripts/verify_external_web_view_readiness.ps1" in script
    assert "scripts/verify_cloudflare_web_view_tunnel.ps1" in script
    assert "scripts/verify_migration_archive.ps1" in script
    assert "scripts/verify_next_phase_closeout.ps1" in script
    assert "scripts/run_scheduled_notify.ps1" in script
    assert "scripts/run_scheduled_krx_daily_backfill.ps1" in script
    assert "scripts/run_scheduled_krx_mentioned_flow_backfill.ps1" in script
    assert "scripts/run_scheduled_market_briefing_slot.ps1" in script
    assert "Missing required migration entries" in script
    assert "required_entries: ok" in script


def test_verify_migration_archive_warns_for_sensitive_entries_inside_zip(tmp_path) -> None:
    archive_path = tmp_path / "manual_sensitive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/.env", "TOKEN=secret\n")
        archive.writestr("02.Stock_Moniter/data/access_code.json", "{}\n")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="ascii",
    )

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1"),
            "-ArchivePath",
            str(archive_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "SHA256 verified" in output
    assert "Sensitive migration entries detected" in output
    assert "02.Stock_Moniter/.env" in output
    assert "02.Stock_Moniter/data/access_code.json" in output


def test_verify_migration_archive_can_fail_for_sensitive_entries_inside_zip(tmp_path) -> None:
    archive_path = tmp_path / "manual_sensitive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/.env", "TOKEN=secret\n")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="ascii",
    )

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1"),
            "-ArchivePath",
            str(archive_path),
            "-FailOnSensitiveEntries",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Sensitive migration entries are not allowed" in output
    assert "02.Stock_Moniter/.env" in output


def test_verify_migration_archive_can_fail_for_transient_entries_inside_zip(tmp_path) -> None:
    archive_path = tmp_path / "manual_transient.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/data/backups/stock_monitor_old.db", "backup\n")
        archive.writestr("02.Stock_Moniter/data/web_view_server.log", "log\n")
        archive.writestr("02.Stock_Moniter/data/Stock_Moniter_migration_old.zip", "nested\n")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="ascii",
    )

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1"),
            "-ArchivePath",
            str(archive_path),
            "-FailOnSensitiveEntries",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Sensitive migration entries are not allowed" in output
    assert "02.Stock_Moniter/data/backups/stock_monitor_old.db" in output
    assert "02.Stock_Moniter/data/web_view_server.log" in output
    assert "02.Stock_Moniter/data/Stock_Moniter_migration_old.zip" in output


def test_verify_migration_archive_fails_when_required_project_entries_are_missing(tmp_path) -> None:
    archive_path = tmp_path / "wrong_project.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("README.md", "not enough\n")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="ascii",
    )

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1"),
            "-ArchivePath",
            str(archive_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Missing required migration entries" in output
    assert "AGENTS.md" in output
    assert "data/stock_monitor.db" in output


def test_setup_mini_pc_environment_creates_venv_and_installs_project() -> None:
    script = (PROJECT_ROOT / "scripts" / "setup_mini_pc_environment.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[switch]$SkipPlaywrightInstall" in script
    assert "-m venv" in script
    assert "-m pip install --upgrade pip" in script
    assert "-m pip install -e .[dev]" in script
    assert "-m playwright install chromium" in script
    assert "verify_mini_pc_readiness.ps1" in script
    assert "$readinessArgs = @{" in script
    assert "PythonExe = $venvPython" in script
    assert "SkipOperatorStatus = $true" in script
    assert "SkipBackupRequirement = $true" in script
    assert "SkipEnvRequirement = $true" in script
    assert "register_mini_pc_scheduler_tasks.ps1 -PythonExe" in script


def test_run_web_view_requires_explicit_non_loopback_override() -> None:
    script = (PROJECT_ROOT / "scripts" / "run_web_view.ps1").read_text(encoding="utf-8")

    assert '[string]$HostAddress = "127.0.0.1"' in script
    assert "[switch]$AllowNonLoopback" in script
    assert '"--no-open"' in script
    assert "--allow-non-loopback" in script
    assert "Starting read-only web-view" in script
    assert "Cloudflare Tunnel target candidate" in script
    assert "Do not expose admin-gui" in script
    assert "configured loopback web-view target" in script


def test_python_entrypoint_wrappers_bootstrap_src_pythonpath() -> None:
    script_names = [
        "run_web_view.ps1",
        "restart_web_view.ps1",
        "run_scheduled_poll.ps1",
        "run_scheduled_notify.ps1",
        "run_scheduled_krx_daily_backfill.ps1",
        "run_scheduled_krx_mentioned_flow_backfill.ps1",
        "run_scheduled_market_briefing_slot.ps1",
        "run_scheduled_toss_priority_baseline.ps1",
        "run_process_telegram_commands.ps1",
        "run_krx_flow_login_reminder.ps1",
        "run_scheduled_shutdown.ps1",
        "verify_external_web_view_readiness.ps1",
        "verify_cloudflare_web_view_tunnel.ps1",
    ]

    for script_name in script_names:
        script = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert 'Join-Path $projectRoot "src"' in script, script_name
        assert "$env:PYTHONPATH" in script, script_name


def test_verify_mini_pc_readiness_runs_core_checks() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_mini_pc_readiness.ps1").read_text(encoding="utf-8")

    assert '"pytest", "-q"' in script
    assert '"stock_monitor", "db-verify"' in script
    assert "[switch]$SkipRestoreSmoke" in script
    assert "[switch]$SkipBackupRequirement" in script
    assert "[switch]$SkipEnvRequirement" in script
    assert "[switch]$RequireMiniPcProfile" in script
    assert "stock_monitor_*.db" in script
    assert '"stock_monitor",' in script
    assert '"db-restore-smoke",' in script
    assert '"stock_monitor", "mini-pc-preflight"' in script
    assert '$preflightArgs += "--require-env"' in script
    assert '$preflightArgs += "--require-backup"' in script
    assert "--require-access-code" in script
    assert "--require-mini-pc-profile" in script
    assert '"stock_monitor",' in script
    assert '"web-view-value-qa",' in script
    assert '"web-view-browser-smoke",' in script
    assert '"--recent-business-days",' in script
    assert '"operator-status",' in script
    assert '"--health-exit"' in script
    assert "[switch]$SkipWebViewBrowserSmoke" in script
    assert "[switch]$SkipOperatorStatus" in script


def test_verify_market_day_observation_runs_closeout_checks() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_market_day_observation.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[string]$Date" in script
    assert "operator-status" in script
    assert "--health-exit" in script
    assert "verify_task_scheduler_registration.ps1" in script
    assert "market-day-observation" in script
    assert "db-verify" in script
    assert "next-phase-readiness" in script
    assert "--recent-report-dates" in script
    assert "--stock-limit" in script
    assert "StockMonitor-Shutdown" in script
    assert "elevated local PowerShell" in script


def test_verify_next_phase_closeout_runs_final_readiness_checks() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_next_phase_closeout.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[string]$Date" in script
    assert "[switch]$RecordStartupFallbackSuccess" in script
    assert "[switch]$SkipOperatorStatus" in script
    assert "[switch]$SkipSchedulerRegistration" in script
    assert "db-verify" in script
    assert "web-view-startup-fallback-check" in script
    assert "--record-success" in script
    assert "operator-status" in script
    assert "--health-exit" in script
    assert "verify_task_scheduler_registration.ps1" in script
    assert "market-day-observation" in script
    assert "observation-summary-audit" in script
    assert "observation-reaction-distribution" in script
    assert "candidate-evidence-readiness" in script
    assert "--recent-report-dates" in script
    assert "--stock-limit" in script
    assert "market-briefing-readiness" in script
    assert "web-view-value-qa" in script
    assert "web-view-browser-smoke" in script
    assert "external-web-view-sharing-plan" in script
    assert "category-snapshot-status" in script
    assert "category-snapshot-plan" in script
    assert "rotation-mapping-audit" in script
    assert '$rotationMappingArgs += @("--date", $Date)' not in script
    assert "krx-baseline-analysis" in script
    assert "next-phase-readiness" in script
    assert "--recent-report-dates" in script
    assert "--stock-limit" in script
    assert "StockMonitor-Shutdown" in script
    assert "admin-gui" in script
    assert "access-code" in script
    assert "elevated local PowerShell" in script


def test_verify_external_web_view_readiness_requires_access_code_and_public_safe_checks() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_external_web_view_readiness.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "mini-pc-preflight" in script
    assert "--require-access-code" in script
    assert "--require-backup" in script
    assert "--require-env" in script
    assert "--require-mini-pc-profile" in script
    assert "web-view-value-qa" in script
    assert "web-view-browser-smoke" in script
    assert "[switch]$SkipBrowserSmoke" in script
    assert "--recent-business-days" in script
    assert "configured loopback web-view target" in script
    assert "admin-gui" in script
    assert "Cloudflare Access" in script
    assert "External readiness step failed" in script
    assert "If access-code is disabled" in script
    assert "python -m stock_monitor access-code set" in script
    assert "exit $LASTEXITCODE" in script


def test_verify_cloudflare_web_view_tunnel_requires_external_https_origin_and_records_success() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_cloudflare_web_view_tunnel.ps1").read_text(encoding="utf-8")

    assert "[Parameter(Mandatory = $true)]" in script
    assert "[string]$Url" in script
    assert "$uri.Scheme -ne \"https\"" in script
    assert "$uri.IsLoopback" in script
    assert "$uri.AbsolutePath -ne \"/\"" in script
    assert "$uri.Query" in script
    assert "$uri.Fragment" in script
    assert "configured loopback web-view target" in script
    assert "admin-gui" in script
    assert "Cloudflare Access" in script
    assert "access-code" in script
    assert "provider prerequisite gate" in script
    assert "mini-pc-preflight" in script
    assert "--require-access-code" in script
    assert "--require-backup" in script
    assert "--require-env" in script
    assert "--require-mini-pc-profile" in script
    assert "verify_external_web_view_readiness.ps1" in script
    assert "external-web-view-smoke" in script
    assert "--record-success" in script
    assert "next-phase-readiness" in script
    assert "phone readability acceptance" in script
    assert "market-day observation" in script


def test_create_web_view_startup_shortcut_targets_loopback_web_view_only() -> None:
    script = (PROJECT_ROOT / "scripts" / "create_web_view_startup_shortcut.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[string]$HostAddress = \"127.0.0.1\"" in script
    assert "[int]$Port = (87 * 100 + 80)" in script
    assert "run_web_view.ps1" in script
    assert "Startup" in script
    assert "StockMonitor-WebView.lnk" in script
    assert "-HostAddress" in script
    assert "-Port" in script
    assert "configured loopback web-view target" in script
    assert "admin-gui" in script
    assert "Cloudflare" in script


def test_restart_web_view_script_restarts_loopback_web_view_only() -> None:
    script = (PROJECT_ROOT / "scripts" / "restart_web_view.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[string]$HostAddress = \"127.0.0.1\"" in script
    assert "[int]$Port = (87 * 100 + 80)" in script
    assert "run_web_view.ps1" in script
    assert "netstat -ano" in script
    assert "Stop-Process" in script
    assert "Invoke-WebRequest" in script
    assert 'Join-Path $projectRoot ".venv\\Scripts\\python.exe"' in script
    assert '$PythonExe -eq "python"' in script
    assert "/health" in script
    assert "admin-gui" in script
    assert "Cloudflare" in script


def test_disable_source_desktop_scheduler_tasks_requires_explicit_confirm() -> None:
    script = (PROJECT_ROOT / "scripts" / "disable_source_desktop_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert "[switch]$ConfirmDisable" in script
    assert "[switch]$DryRun" in script
    assert "scheduler-control" in script
    assert '"disable"' in script
    assert '"--task"' in script
    assert '"all"' in script
    assert '"--confirm"' in script
    assert '"--dry-run"' in script
    assert "ConfirmDisable" in script
    assert "source desktop" in script


def test_register_task_scheduler_tasks_registers_market_briefing_slots() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert '[string]$MarketBriefingMoodTime = "09:15"' in script
    assert '[string]$MarketBriefingLunchTime = "12:00"' in script
    assert '[string]$MarketBriefingPrecloseTime = "15:15"' in script
    assert "[switch]$SkipMarketBriefing" in script
    assert "run_scheduled_market_briefing_slot.ps1" in script
    assert "$TaskPrefix-MarketBriefingMood" in script
    assert "$TaskPrefix-MarketBriefingLunch" in script
    assert "$TaskPrefix-MarketBriefingPreclose" in script
    assert "-Slot mood" in script
    assert "-Slot lunch" in script
    assert "-Slot preclose" in script
    assert "-StartWhenAvailable $false" in script


def test_register_task_scheduler_tasks_registers_toss_priority_baseline_at_2000() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert '[string]$TossPriorityBaselineTime = "20:00"' in script
    assert "[switch]$SkipTossPriorityBaseline" in script
    assert "run_scheduled_toss_priority_baseline.ps1" in script
    assert "$TaskPrefix-TossPriorityBaseline" in script
    assert "-StartWhenAvailable $false" in script


def test_verify_task_scheduler_registration_checks_expected_tasks_and_actions() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_task_scheduler_registration.ps1").read_text(encoding="utf-8")

    assert '[string]$TaskPrefix = "StockMonitor"' in script
    assert "[string]$PythonExe" in script
    assert "[switch]$IncludeShutdown" in script
    assert "[switch]$IncludeKrxFlowReminder" in script
    assert "Get-ScheduledTask" in script
    assert "Get-ScheduledTaskInfo" in script
    assert "Task Scheduler metadata access denied" in script
    assert "elevated local PowerShell session" in script
    assert "액세스가 거부" in script
    assert "0x80070005" in script
    assert "0x80041003" in script
    assert "PermissionDenied" in script
    assert "Get-ExpectedScheduledTask" in script
    assert "StockMonitor-KrxDailyBackfill" in script
    assert "StockMonitor-Notify" in script
    assert "StockMonitor-Poll" in script
    assert "StockMonitor-KrxMentionedFlowBackfill" in script
    assert "StockMonitor-MarketBriefingMood" in script
    assert "StockMonitor-MarketBriefingLunch" in script
    assert "StockMonitor-MarketBriefingPreclose" in script
    assert "StockMonitor-TelegramCommands" in script
    assert "StockMonitor-WebViewHourlyRestart" in script
    assert "StockMonitor-TossPriorityBaseline" in script
    assert "StockMonitor-KrxFlowLoginReminder" in script
    assert "StockMonitor-Shutdown" in script
    assert "run_scheduled_krx_daily_backfill.ps1" in script
    assert "run_scheduled_notify.ps1" in script
    assert "run_scheduled_poll.ps1" in script
    assert "run_scheduled_krx_mentioned_flow_backfill.ps1" in script
    assert "run_scheduled_market_briefing_slot.ps1" in script
    assert "run_scheduled_toss_priority_baseline.ps1" in script
    assert "run_process_telegram_commands.ps1" in script
    assert "restart_web_view.ps1" in script
    assert "run_krx_flow_login_reminder.ps1" in script
    assert "run_scheduled_shutdown.ps1" in script
    assert "if ($IncludeShutdown)" in script
    assert "if ($IncludeKrxFlowReminder)" in script
    assert "$unexpectedShutdownTaskName" in script
    assert "Unexpected desktop validation shutdown task is registered" in script
    assert "Task scheduler registration verified" in script


def test_register_mini_pc_scheduler_tasks_skips_shutdown_by_default() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_mini_pc_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[switch]$IncludeKrxFlowReminder" in script
    assert "register_task_scheduler_tasks.ps1" in script
    assert "IncludeKrxFlowReminder = $true" in script
    assert "SkipShutdown = $true" in script
    assert "verify_task_scheduler_registration.ps1" in script
    assert "$verifyArgs.IncludeKrxFlowReminder = $true" in script
    assert "StockMonitor-Shutdown is intentionally not registered" in script
    assert "StockMonitor-WebViewHourlyRestart" in script
    assert "StockMonitor-TossPriorityBaseline" in script
    assert "web_view_hourly_restart" in script
