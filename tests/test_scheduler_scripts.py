import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from stock_monitor.notify.delivery_lock import delivery_lock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_POWERSHELL = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
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
    "scripts/resolve_project_python.ps1",
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
    "scripts/run_scheduled_toss_market_context_capture.ps1",
    "scripts/run_scheduled_toss_priority_baseline.ps1",
    "scripts/run_process_telegram_commands.ps1",
    "scripts/run_scheduled_shutdown.ps1",
]


SCHEDULER_PYTHON_WRAPPERS = [
    "run_scheduled_poll.ps1",
    "run_scheduled_notify.ps1",
    "run_scheduled_krx_daily_backfill.ps1",
    "run_scheduled_krx_mentioned_flow_backfill.ps1",
    "run_scheduled_market_briefing_slot.ps1",
    "run_scheduled_toss_priority_baseline.ps1",
    "run_scheduled_toss_market_context_capture.ps1",
    "run_process_telegram_commands.ps1",
    "run_krx_flow_login_reminder.ps1",
    "run_scheduled_shutdown.ps1",
    "restart_web_view.ps1",
    "run_web_view.ps1",
]


def _write_required_migration_entries(archive: zipfile.ZipFile, database_path: Path | None = None) -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        test_database = Path(temporary_directory) / "stock_monitor.db"
        if database_path is None:
            connection = _create_archive_wal_database(test_database)
            connection.close()
            database_path = test_database
        for entry in REQUIRED_MIGRATION_ENTRIES:
            if entry == "data/stock_monitor.db":
                archive.write(database_path, f"02.Stock_Moniter/{entry}")
            else:
                archive.writestr(f"02.Stock_Moniter/{entry}", "required\n")


def _write_required_project_files(project_root: Path) -> None:
    for entry in REQUIRED_MIGRATION_ENTRIES:
        if entry == "data/stock_monitor.db":
            continue
        fixture_path = project_root / entry
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text("required\n", encoding="utf-8")


def _copy_migration_archive_scripts(project_root: Path) -> None:
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in ("create_migration_archive.ps1", "create_migration_archive_snapshot.py"):
        (scripts_dir / name).write_bytes((PROJECT_ROOT / "scripts" / name).read_bytes())
    source_package = PROJECT_ROOT / "src" / "stock_monitor"
    target_package = project_root / "src" / "stock_monitor"
    target_package.mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "config.py"):
        (target_package / name).write_bytes((source_package / name).read_bytes())


def _create_archive_wal_database(path: Path, row_count: int = 1000) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA wal_autocheckpoint = 0")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE child (parent_id INTEGER NOT NULL REFERENCES parent(id))")
    connection.executemany("INSERT INTO parent VALUES (?)", ((index,) for index in range(1, row_count + 1)))
    connection.executemany("INSERT INTO child VALUES (?)", ((index,) for index in range(1, row_count + 1)))
    connection.commit()
    return connection


def _archive_powershell_environment(temp_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join((str(Path(sys.executable).parent), environment["PATH"]))
    environment.pop("STOCK_MONITOR_DB_PATH", None)
    environment["TEMP"] = str(temp_dir)
    environment["TMP"] = str(temp_dir)
    system_modules = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "Modules"
    environment["PSModulePath"] = os.pathsep.join((str(system_modules), environment.get("PSModulePath", "")))
    return environment


def _archive_barrier_python(temp_dir: Path) -> tuple[Path, Path]:
    barrier = temp_dir / "snapshot-barrier"
    barrier.mkdir()
    wrapper_script = temp_dir / "snapshot-barrier.py"
    wrapper_script.write_text(
        "import os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "if sys.argv[2] == 'snapshot':\n"
        "    barrier = Path(os.environ['ARCHIVE_SNAPSHOT_BARRIER'])\n"
        "    (barrier / f'{os.getpid()}.ready').touch()\n"
        "    deadline = time.monotonic() + 30\n"
        "    while len(list(barrier.glob('*.ready'))) < 2 and time.monotonic() < deadline:\n"
        "        time.sleep(0.01)\n"
        "    if len(list(Path(os.environ['TEMP']).glob('stock_monitor_migration_*'))) < 2:\n"
        "        raise SystemExit(97)\n"
        "raise SystemExit(subprocess.call([sys.executable, *sys.argv[1:]]))\n",
        encoding="utf-8",
    )
    command = temp_dir / "snapshot-python.cmd"
    command.write_bytes(
        f'@echo off\r\n"{sys.executable}" "{wrapper_script}" %*\r\nexit /b %ERRORLEVEL%\r\n'.encode("utf-8")
    )
    return command, barrier


def test_register_task_scheduler_removes_legacy_krx_tasks() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert 'Remove-LegacyTask -TaskName "$TaskPrefix-KrxDailyBackfill"' in script
    assert 'Remove-LegacyTask -TaskName "$TaskPrefix-KrxMentionedFlowBackfill"' in script
    assert 'Remove-LegacyTask -TaskName "$TaskPrefix-KrxFlowLoginReminder"' in script
    assert 'Remove-LegacyTask -TaskName "$TaskPrefix-TossPriorityBaseline"' in script


def test_scheduler_wrappers_require_project_venv_python() -> None:
    resolver = (PROJECT_ROOT / "scripts" / "resolve_project_python.ps1").read_text(encoding="utf-8")

    assert "function Resolve-StockMonitorPython" in resolver
    assert ".venv\\Scripts\\python.exe" in resolver
    assert "setup_mini_pc_environment.ps1" in resolver
    assert "PATH fallback is disabled" in resolver

    for script_name in SCHEDULER_PYTHON_WRAPPERS:
        script = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "resolve_project_python.ps1" in script
        assert "Resolve-StockMonitorPython" in script


def test_scheduler_registration_resolves_project_venv_before_creating_tasks() -> None:
    for script_name in [
        "register_task_scheduler_tasks.ps1",
        "register_mini_pc_scheduler_tasks.ps1",
    ]:
        script = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "resolve_project_python.ps1" in script
        assert "Resolve-StockMonitorPython" in script


def test_register_task_scheduler_runs_toss_close_snapshot_after_2000_close() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert '[string]$TossPriorityBaselineTime = "20:05"' in script
    assert "run_scheduled_toss_priority_baseline.ps1" in script
    assert "TossMarketContextCaptureTime" not in script


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


def test_register_task_scheduler_does_not_register_krx_daily_backfill() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert "KrxDailyBackfillTime" not in script
    assert "run_scheduled_krx_daily_backfill.ps1" not in script


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


def test_create_migration_archive_excludes_secret_environment_files_and_generated_artifacts(tmp_path) -> None:
    project_root = tmp_path / "project"
    secret_files = {
        ".env": "BOT_TOKEN=fake\n",
        ".env.local": "TOKEN=fake\n",
        ".env.toss-openapi": "CLIENT_SECRET=fake\n",
        "config/.env.production": "PASSWORD=fake\n",
        "config/telegram.env": "BOT_TOKEN=fake\n",
    }
    safe_examples = {
        ".env.example": "BOT_TOKEN=replace-me\n",
        ".env.toss-openapi.example": "CLIENT_SECRET=replace-me\n",
    }
    artifacts = {
        ".codegraph/index.sqlite": "local index\n",
        "web/node_modules/example/module.js": "generated dependency\n",
        "web/.next/cache/build": "generated build\n",
        "data/custom.db-wal": "unselected SQLite WAL\n",
        "data/cache.sqlite-shm": "unselected SQLite shared memory\n",
        "data/archive.sqlite3-journal": "unselected SQLite journal\n",
        "data/pending.zip.publication.lock": "lock\n",
        ".git/objects/pack/keep": "repository history\n",
    }
    for relative_path, contents in {**secret_files, **safe_examples, **artifacts}.items():
        fixture_path = project_root / relative_path
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(contents, encoding="utf-8")
    database = _create_archive_wal_database(project_root / "data" / "stock_monitor.db")
    database.close()
    _copy_migration_archive_scripts(project_root)
    script_path = project_root / "scripts" / "create_migration_archive.ps1"

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    environment = os.environ.copy()
    environment["TEMP"] = str(temp_dir)
    environment["TMP"] = str(temp_dir)
    system_modules = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "Modules"
    environment["PSModulePath"] = os.pathsep.join((str(system_modules), environment.get("PSModulePath", "")))
    command = [
        str(WINDOWS_POWERSHELL),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]

    for include_env in (False, True):
        archive_path = tmp_path / ("with-env.zip" if include_env else "default.zip")
        result = subprocess.run(
            [
                *command,
                "-DestinationPath",
                str(archive_path),
                "-PythonExe",
                sys.executable,
                "-SkipPreflight",
                *(["-IncludeEnv"] if include_env else []),
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert archive_path.exists(), result.stdout + result.stderr
        with zipfile.ZipFile(archive_path) as archive:
            archived_paths = set(archive.namelist())

        excluded_secrets = set(secret_files) - ({".env"} if include_env else set())
        assert archived_paths.isdisjoint(excluded_secrets)
        assert set(safe_examples) <= archived_paths
        assert not any(path.startswith((".codegraph/", "web/node_modules/", "web/.next/")) for path in archived_paths)
        assert not any(path.endswith(("custom.db-wal", "cache.sqlite-shm", "archive.sqlite3-journal")) for path in archived_paths)
        assert "data/pending.zip.publication.lock" not in archived_paths
        assert ".git/objects/pack/keep" in archived_paths
        assert (".env" in archived_paths) is include_env


def test_create_migration_archive_aborts_when_preflight_fails(tmp_path) -> None:
    project_root = tmp_path / "project"
    scripts_dir = project_root / "scripts"
    fake_bin_dir = tmp_path / "bin"
    scripts_dir.mkdir(parents=True)
    fake_bin_dir.mkdir()
    _copy_migration_archive_scripts(project_root)
    script_path = scripts_dir / "create_migration_archive.ps1"
    (project_root / "README.md").write_text("fixture\n", encoding="utf-8")
    marker_path = tmp_path / "preflight-called"
    (fake_bin_dir / "python.cmd").write_bytes(b'@echo off\r\necho called > "%FAKE_PYTHON_MARKER%"\r\nexit /b 7\r\n')

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join((str(fake_bin_dir), environment["PATH"]))
    environment["TEMP"] = str(temp_dir)
    environment["TMP"] = str(temp_dir)
    environment["FAKE_PYTHON_MARKER"] = str(marker_path)
    system_modules = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "Modules"
    environment["PSModulePath"] = os.pathsep.join((str(system_modules), environment.get("PSModulePath", "")))
    archive_path = tmp_path / "must-not-exist.zip"

    result = subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-DestinationPath",
            str(archive_path),
            "-PythonExe",
            str(fake_bin_dir / "python.cmd"),
        ],
        cwd=project_root,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert marker_path.read_text(encoding="utf-8").strip() == "called"
    assert result.returncode != 0
    assert "preflight failed with exit code 7" in (result.stdout + result.stderr)
    assert not archive_path.exists()


def test_create_migration_archive_omits_active_delivery_lock(tmp_path) -> None:
    project_root = tmp_path / "project"
    _write_required_project_files(project_root)
    _copy_migration_archive_scripts(project_root)
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    archive_path = tmp_path / "snapshot.zip"
    source_database = project_root / "data/stock_monitor.db"
    with closing(_create_archive_wal_database(source_database)), delivery_lock(source_database):
        result = subprocess.run(
            [
                str(WINDOWS_POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(project_root / "scripts/create_migration_archive.ps1"),
                "-DestinationPath", str(archive_path), "-PythonExe", sys.executable, "-SkipPreflight",
            ],
            cwd=project_root,
            env=_archive_powershell_environment(temp_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    with zipfile.ZipFile(archive_path) as archive:
        assert "data/stock_monitor.db.delivery.lock" not in archive.namelist()


def test_create_migration_archive_snapshots_wal_database_with_active_writer(tmp_path) -> None:
    project_root = tmp_path / "project"
    _write_required_project_files(project_root)
    _copy_migration_archive_scripts(project_root)
    script_path = project_root / "scripts" / "create_migration_archive.ps1"
    source_database = project_root / "data" / "stock_monitor.db"
    writer = _create_archive_wal_database(source_database)
    wal_path = Path(f"{source_database}-wal")
    assert wal_path.exists() and wal_path.stat().st_size > 0

    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO parent VALUES (999999)")
    assert writer.in_transaction
    committed_count = 1000
    source_database_before = hashlib.sha256(source_database.read_bytes()).digest()
    wal_before = hashlib.sha256(wal_path.read_bytes()).digest()
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    environment = _archive_powershell_environment(temp_dir)
    python_wrapper, barrier = _archive_barrier_python(temp_dir)
    environment["ARCHIVE_SNAPSHOT_BARRIER"] = str(barrier)
    archive_path = tmp_path / "snapshot.zip"
    archive_paths = [archive_path, archive_path]

    try:
        commands = [
            [
                str(WINDOWS_POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-DestinationPath",
                str(archive_path),
                "-PythonExe",
                str(python_wrapper),
                "-SkipPreflight",
            ]
            for archive_path in archive_paths
        ]
        processes = [
            subprocess.Popen(
                command,
                cwd=project_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for command in commands
        ]
        try:
            completed = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=30)
                completed.append((process.returncode, stdout, stderr))
            assert any(returncode == 0 for returncode, _, _ in completed)
            for returncode, stdout, stderr in completed:
                if returncode != 0:
                        assert "archive publisher" in (stdout + stderr).lower()
            assert archive_path.exists()
            lock_path = Path(f"{archive_path}.publication.lock")
            assert lock_path.exists()
            with zipfile.ZipFile(archive_path) as archive:
                entries = set(archive.namelist())
                assert "data/stock_monitor.db" in entries
                assert "scripts/create_migration_archive_snapshot.py" in entries
                assert not any(
                    entry.endswith(("stock_monitor.db-wal", "stock_monitor.db-shm", "stock_monitor.db-journal"))
                    for entry in entries
                )
                restored_path = tmp_path / "restored.db"
                restored_path.write_bytes(archive.read("data/stock_monitor.db"))

            with sqlite3.connect(restored_path) as restored:
                assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert restored.execute("PRAGMA foreign_key_check").fetchall() == []
                assert restored.execute("SELECT COUNT(*) FROM parent").fetchone()[0] == committed_count
                assert restored.execute("SELECT COUNT(*) FROM child").fetchone()[0] == committed_count
                assert restored.execute("SELECT COUNT(*) FROM parent WHERE id = 999999").fetchone()[0] == 0
            expected_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
            assert expected_hash in Path(f"{archive_path}.sha256").read_text(encoding="ascii")
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

        assert writer.in_transaction
        assert hashlib.sha256(source_database.read_bytes()).digest() == source_database_before
        assert hashlib.sha256(wal_path.read_bytes()).digest() == wal_before
    finally:
        writer.rollback()
        writer.close()


def test_create_migration_archive_snapshots_configured_relative_and_absolute_database_paths(tmp_path) -> None:
    for mode in ("relative", "absolute"):
        project_root = tmp_path / mode / "project"
        _write_required_project_files(project_root)
        _copy_migration_archive_scripts(project_root)
        default_database = _create_archive_wal_database(project_root / "data" / "stock_monitor.db", row_count=2)
        default_database.close()
        source_database = (
            project_root / "data" / "custom.db"
            if mode == "relative"
            else tmp_path / mode / "external.db"
        )
        row_count = 7 if mode == "relative" else 11
        writer = _create_archive_wal_database(source_database, row_count=row_count)
        database_setting = "data/custom.db" if mode == "relative" else str(source_database.resolve())
        (project_root / ".env").write_text(f"STOCK_MONITOR_DB_PATH={database_setting}\n", encoding="utf-8")
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO parent VALUES (999999)")
        source_before = hashlib.sha256(source_database.read_bytes()).digest()
        wal_path = Path(f"{source_database}-wal")
        wal_before = hashlib.sha256(wal_path.read_bytes()).digest()
        temp_dir = tmp_path / mode / "temp"
        temp_dir.mkdir()
        environment = _archive_powershell_environment(temp_dir)
        archive_path = tmp_path / f"{mode}.zip"

        try:
            result = subprocess.run(
                [
                    str(WINDOWS_POWERSHELL),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(project_root / "scripts" / "create_migration_archive.ps1"),
                    "-DestinationPath",
                    str(archive_path),
                    "-PythonExe",
                    sys.executable,
                    "-SkipPreflight",
                ],
                cwd=project_root,
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            with zipfile.ZipFile(archive_path) as archive:
                archive_names = archive.namelist()
                entries = set(archive_names)
                assert archive_names.count("data/stock_monitor.db") == 1
                assert ".env" not in entries
                assert "data/custom.db" not in entries
                assert not any(
                    entry.endswith((
                        "stock_monitor.db-wal", "stock_monitor.db-shm", "stock_monitor.db-journal",
                        "custom.db-wal", "custom.db-shm", "custom.db-journal",
                    ))
                    for entry in entries
                )
                restored_path = tmp_path / f"{mode}-restored.db"
                restored_path.write_bytes(archive.read("data/stock_monitor.db"))
            with sqlite3.connect(restored_path) as restored:
                assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert restored.execute("PRAGMA foreign_key_check").fetchall() == []
                assert restored.execute("SELECT COUNT(*) FROM parent").fetchone()[0] == row_count
                assert restored.execute("SELECT COUNT(*) FROM parent WHERE id = 999999").fetchone()[0] == 0
            assert writer.in_transaction
            assert hashlib.sha256(source_database.read_bytes()).digest() == source_before
            assert hashlib.sha256(wal_path.read_bytes()).digest() == wal_before
        finally:
            writer.rollback()
            writer.close()


def test_create_migration_archive_preserves_previous_zip_when_database_is_invalid(tmp_path) -> None:
    project_root = tmp_path / "project"
    _write_required_project_files(project_root)
    _copy_migration_archive_scripts(project_root)
    script_path = project_root / "scripts" / "create_migration_archive.ps1"
    source_database = project_root / "data" / "stock_monitor.db"
    source = _create_archive_wal_database(source_database)
    source.close()
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    environment = _archive_powershell_environment(temp_dir)
    archive_path = tmp_path / "existing.zip"
    command = [
        str(WINDOWS_POWERSHELL),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-DestinationPath",
        str(archive_path),
        "-PythonExe",
        sys.executable,
        "-SkipPreflight",
    ]

    first = subprocess.run(command, cwd=project_root, env=environment, capture_output=True, check=False, text=True)
    assert first.returncode == 0, first.stdout + first.stderr
    archive_before = archive_path.read_bytes()
    checksum_path = Path(f"{archive_path}.sha256")
    checksum_before = checksum_path.read_bytes()
    source = sqlite3.connect(source_database)
    source.execute("PRAGMA foreign_keys = OFF")
    source.execute("INSERT INTO child VALUES (999999)")
    source.commit()
    source.close()

    second = subprocess.run(command, cwd=project_root, env=environment, capture_output=True, check=False, text=True)

    assert second.returncode != 0
    assert "foreign_key_check" in (second.stdout + second.stderr)
    assert archive_path.read_bytes() == archive_before
    assert checksum_path.read_bytes() == checksum_before


def test_verify_migration_archive_rejects_database_with_foreign_key_violation(tmp_path) -> None:
    database_path = tmp_path / "invalid.db"
    connection = _create_archive_wal_database(database_path)
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("INSERT INTO child VALUES (999999)")
    connection.commit()
    connection.close()
    archive_path = tmp_path / "invalid_database.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive, database_path)
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
            "-PythonExe",
            sys.executable,
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert "foreign_key_check" in (result.stdout + result.stderr)


def test_verify_migration_archive_rejects_live_database_sidecars(tmp_path) -> None:
    archive_path = tmp_path / "database_sidecar.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/data/custom.db-wal", "live WAL\n")
        archive.writestr("02.Stock_Moniter/data/cache.sqlite-shm", "live shared memory\n")
        archive.writestr("02.Stock_Moniter/data/archive.sqlite3-journal", "live journal\n")
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
            "-PythonExe",
            sys.executable,
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert "SQLite sidecar" in (result.stdout + result.stderr)


def test_verify_migration_archive_checks_sha256_sidecar() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_migration_archive.ps1").read_text(encoding="utf-8")

    assert "[string]$ArchivePath" in script
    assert "[string]$PythonExe" in script
    assert "[switch]$FailOnSensitiveEntries" in script
    assert "System.Security.Cryptography.SHA256" in script
    assert "ComputeHash($archiveStream)" in script
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
    assert "create_migration_archive_snapshot.py" in script
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
    assert "scripts/resolve_project_python.ps1" in script
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
    assert "scripts/run_scheduled_toss_market_context_capture.ps1" in script
    assert "scripts/run_scheduled_toss_priority_baseline.ps1" in script
    assert "Missing required migration entries" in script
    assert "required_entries: ok" in script


def test_verify_migration_archive_warns_for_sensitive_entries_inside_zip(tmp_path) -> None:
    archive_path = tmp_path / "manual_sensitive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/.env", "TOKEN=secret\n")
        archive.writestr("02.Stock_Moniter/.env.toss-openapi", "CLIENT_SECRET=fake\n")
        archive.writestr("02.Stock_Moniter/web/.env.local", "TOKEN=fake\n")
        archive.writestr("02.Stock_Moniter/config/telegram.env", "BOT_TOKEN=fake\n")
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
            "-PythonExe",
            sys.executable,
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
    assert "02.Stock_Moniter/.env.toss-openapi" in output
    assert "02.Stock_Moniter/web/.env.local" in output
    assert "02.Stock_Moniter/config/telegram.env" in output
    assert "02.Stock_Moniter/data/access_code.json" in output


def test_verify_migration_archive_can_fail_for_sensitive_entries_inside_zip(tmp_path) -> None:
    archive_path = tmp_path / "manual_sensitive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        _write_required_migration_entries(archive)
        archive.writestr("02.Stock_Moniter/.env.toss-openapi", "CLIENT_SECRET=fake\n")
        archive.writestr("02.Stock_Moniter/config/telegram.env", "BOT_TOKEN=fake\n")
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
            "-PythonExe",
            sys.executable,
            "-FailOnSensitiveEntries",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Sensitive migration entries are not allowed" in output
    assert "02.Stock_Moniter/.env.toss-openapi" in output
    assert "02.Stock_Moniter/config/telegram.env" in output


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
            "-PythonExe",
            sys.executable,
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
            "-PythonExe",
            sys.executable,
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


def test_verify_external_web_view_readiness_checks_next_without_requiring_python_access_code() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_external_web_view_readiness.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "mini-pc-preflight" in script
    assert "--require-access-code" not in script
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
    assert "Next intentionally has no app access-code" in script
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
    assert "Next intentionally has no app access-code" in script
    assert "provider prerequisite gate" in script
    assert "mini-pc-preflight" in script
    assert "--require-access-code" not in script
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

    assert "[switch]$UsePython" in script
    assert "[string]$HostAddress = \"127.0.0.1\"" in script
    assert "[int]$Port = 8780" in script
    assert "ensure_next_web_view.ps1" in script
    assert "run_web_view.ps1" in script
    assert "Startup" in script
    assert "StockMonitor-WebView.lnk" in script
    assert "-HostAddress" in script
    assert "-Port" in script
    assert "configured loopback web-view target" in script
    assert "admin-gui" in script
    assert "Cloudflare" in script


def test_next_web_view_ensure_is_loopback_only_and_never_stops_unknown_listeners() -> None:
    script = (PROJECT_ROOT / "scripts" / "ensure_next_web_view.ps1").read_text(encoding="utf-8")
    launcher = (PROJECT_ROOT / "scripts" / "start_next_web_view.ps1").read_text(encoding="utf-8")

    assert "LocalAddress" in script
    assert "127.0.0.1" in script
    assert "--hostname\\s+" in script
    assert "127\\.0\\.0\\.1" in script
    assert "x-stock-monitor-service" in script
    assert "next-web-view" in script
    assert "unverified listener" in script
    assert "Stop-Process" not in script
    assert "Start-Process" in script
    assert "LocalAddress" in launcher
    assert "--hostname\\s+\"?127\\.0\\.0\\.1" in launcher
    assert "non-loopback listener" in launcher


def test_restart_web_view_script_restarts_loopback_web_view_only() -> None:
    script = (PROJECT_ROOT / "scripts" / "restart_web_view.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "[string]$HostAddress = \"127.0.0.1\"" in script
    assert "[int]$Port = (87 * 100 + 80)" in script
    assert "run_web_view.ps1" in script
    assert "netstat -ano" in script
    assert "Stop-Process" in script
    assert "Invoke-WebRequest" in script
    assert "resolve_project_python.ps1" in script
    assert "Resolve-StockMonitorPython" in script
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


def test_market_briefing_slot_only_runs_its_requested_briefing() -> None:
    script = (PROJECT_ROOT / "scripts" / "run_scheduled_market_briefing_slot.ps1").read_text(encoding="utf-8")

    assert "scheduled-market-briefing-slot" in script
    assert "realtime-first-review-snapshot" not in script
    assert "market-research-note" not in script


def test_register_task_scheduler_tasks_registers_toss_priority_baseline_after_2000_close() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_task_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert '[string]$TossPriorityBaselineTime = "20:05"' in script
    assert "[switch]$SkipTossPriorityBaseline" in script
    assert "run_scheduled_toss_priority_baseline.ps1" in script
    assert "$TaskPrefix-TossCloseSnapshot" in script
    assert "-StartWhenAvailable $false" in script


def test_verify_task_scheduler_registration_checks_expected_tasks_and_actions() -> None:
    script = (PROJECT_ROOT / "scripts" / "verify_task_scheduler_registration.ps1").read_text(encoding="utf-8")

    assert '[string]$TaskPrefix = "StockMonitor"' in script
    assert "[string]$PythonExe" in script
    assert "[switch]$IncludeShutdown" in script
    assert "Get-ScheduledTask" in script
    assert "Get-ScheduledTaskInfo" in script
    assert "Task Scheduler metadata access denied" in script
    assert "elevated local PowerShell session" in script
    assert "액세스가 거부" in script
    assert "0x80070005" in script
    assert "0x80041003" in script
    assert "PermissionDenied" in script
    assert "Get-ExpectedScheduledTask" in script
    assert "StockMonitor-Notify" in script
    assert "StockMonitor-Poll" in script
    assert "StockMonitor-MarketBriefingMood" in script
    assert "StockMonitor-MarketBriefingLunch" in script
    assert "StockMonitor-MarketBriefingPreclose" in script
    assert "StockMonitor-TelegramCommands" in script
    assert "StockMonitor-WebViewHourlyRestart" in script
    assert "StockMonitor-TossCloseSnapshot" in script
    assert "StockMonitor-Shutdown" in script
    assert "run_scheduled_notify.ps1" in script
    assert "run_scheduled_poll.ps1" in script
    assert "run_scheduled_market_briefing_slot.ps1" in script
    assert "run_scheduled_toss_priority_baseline.ps1" in script
    assert "run_process_telegram_commands.ps1" in script
    assert "ensure_next_web_view.ps1" in script
    assert "run_scheduled_shutdown.ps1" in script
    assert "if ($IncludeShutdown)" in script
    assert "Legacy KRX or duplicate Toss task is registered" in script
    assert "$unexpectedShutdownTaskName" in script
    assert "Unexpected desktop validation shutdown task is registered" in script
    assert "Task scheduler registration verified" in script


def test_register_mini_pc_scheduler_tasks_skips_shutdown_by_default() -> None:
    script = (PROJECT_ROOT / "scripts" / "register_mini_pc_scheduler_tasks.ps1").read_text(encoding="utf-8")

    assert "[string]$PythonExe" in script
    assert "register_task_scheduler_tasks.ps1" in script
    assert "SkipShutdown = $true" in script
    assert "verify_task_scheduler_registration.ps1" in script
    assert "StockMonitor-Shutdown is intentionally not registered" in script
    assert "StockMonitor-WebViewHourlyRestart" in script
    assert "StockMonitor-TossCloseSnapshot" in script
    assert "web_view_hourly_restart" in script
