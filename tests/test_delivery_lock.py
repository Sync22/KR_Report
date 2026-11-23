from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
import errno
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock, Thread

import pytest

from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import Opinion, Report
from stock_monitor.notify.control import load_control_state
from stock_monitor.notify.delivery_lock import delivery_lock
import stock_monitor.cli as cli_module


def _config_and_repository(tmp_path, monkeypatch) -> tuple[RuntimeConfig, StockMonitorRepository]:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "test-chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    return config, repository


def _report(
    business_date: date,
    identity: str,
    *,
    stock_name: str = "삼성전자",
    stock_code: str = "005930",
) -> Report:
    published_at = datetime.combine(business_date, time(9))
    return Report(
        stock_name=stock_name,
        stock_code=stock_code,
        title="실적 전망",
        broker_name="NH",
        published_at=published_at,
        collected_at=published_at + timedelta(minutes=30),
        business_date=business_date,
        target_price_raw="92000",
        target_price_value=92_000,
        opinion_raw="중립",
        opinion_normalized=Opinion.NEUTRAL.value,
        source_url=f"https://example.test/report/{identity}",
        source_id=identity,
        identity_key=identity,
    )


def _sender_gate():
    first_send_started = Event()
    second_send_started = Event()
    release_first_send = Event()
    count_lock = Lock()
    calls: list[str] = []

    def sender(_token, _chat, message, **_kwargs):
        with count_lock:
            calls.append(message)
            call_number = len(calls)
        if call_number == 1:
            first_send_started.set()
            assert release_first_send.wait(5)
        else:
            second_send_started.set()
        return str(call_number)

    return sender, first_send_started, second_send_started, release_first_send, calls


def _run_overlapping_deliveries(first_call, second_call, sender_gate):
    _, first_send_started, second_send_started, release_first_send, _calls = sender_gate
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_call)
        assert first_send_started.wait(5)
        second_started = Event()

        def run_second():
            second_started.set()
            return second_call()

        second = pool.submit(run_second)
        assert second_started.wait(5)
        try:
            assert not second_send_started.wait(0.2)
        finally:
            release_first_send.set()
        return first.result(timeout=5), second.result(timeout=5)


def _crash_after_sender_accept(root: Path, mode: str, marker: Path) -> None:
    child_code = "\n".join(
        (
            "import os, sys",
            "from datetime import datetime, time",
            "from pathlib import Path",
            "from zoneinfo import ZoneInfo",
            "sys.path.insert(0, sys.argv[2])",
            "from stock_monitor.config import RuntimeConfig",
            "from stock_monitor.db.repository import StockMonitorRepository",
            "import stock_monitor.cli as cli",
            "root = Path(sys.argv[1])",
            "config = RuntimeConfig.from_env(root_dir=root)",
            "repository = StockMonitorRepository(config.db_path, timezone=config.timezone)",
            "cli._fetch_intraday_quotes_by_stock_code = lambda *_args, **_kwargs: {}",
            "def accepted_then_crash(_token, _chat, _message, **_kwargs):",
            "    Path(sys.argv[3]).write_text('accepted', encoding='utf-8')",
            "    os._exit(73)",
            "cli.send_telegram_message = accepted_then_crash",
            "if sys.argv[4] == 'daily':",
            "    cli._scheduled_skip_reason = lambda *_args: None",
            "    cli._operation_profile_skip_reason = lambda *_args, **_kwargs: None",
            "    cli._fetch_daily_summary_quotes_by_stock_code = lambda *_args, **_kwargs: {}",
            "    cli.SCHEDULED_NOTIFY_EARLIEST_TIME = time(0)",
            "    cli.SCHEDULED_NOTIFY_LATEST_TIME = time.max",
            "    cli._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False)",
            "elif sys.argv[4] == 'worker':",
            "    cli._run_process_intraday_alerts(config, repository, dry_run=False)",
            "elif sys.argv[4] == 'daily_repeat_completed':",
            "    cli._scheduled_skip_reason = lambda *_args: None",
            "    cli._operation_profile_skip_reason = lambda *_args, **_kwargs: None",
            "    cli._fetch_daily_summary_quotes_by_stock_code = lambda *_args, **_kwargs: {}",
            "    cli.SCHEDULED_NOTIFY_EARLIEST_TIME = time(0)",
            "    cli.SCHEDULED_NOTIFY_LATEST_TIME = time.max",
            "    cli.send_telegram_message = lambda *_args, **_kwargs: 'second-message-id'",
            "    send_fragments = cli._send_production_daily_summary_fragments",
            "    def completed_then_crash(*args, **kwargs):",
            "        message_ids = send_fragments(*args, **kwargs)",
            "        Path(sys.argv[3]).write_text(','.join(message_ids), encoding='utf-8')",
            "        os._exit(74)",
            "    cli._send_production_daily_summary_fragments = completed_then_crash",
            "    cli._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=True)",
            "else:",
            "    scheduled = datetime(2026, 4, 24, 10, 0, tzinfo=ZoneInfo(config.timezone))",
            "    cli._run_scheduled_intraday_briefing(config, repository, scheduled_run_at=scheduled, dry_run=False)",
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", child_code, str(root), str(Path(__file__).resolve().parents[1] / "src"), str(marker), mode],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    expected_exit = 74 if mode == "daily_repeat_completed" else 73
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert marker.read_text(encoding="utf-8") == ("second-message-id" if mode == "daily_repeat_completed" else "accepted")


def _prepare_scheduled_daily_notification(config: RuntimeConfig, repository: StockMonitorRepository, monkeypatch) -> date:
    business_date = cli_module.previous_business_day(
        datetime.now(cli_module.ZoneInfo(config.timezone)).date(),
        config.holiday_overrides,
    )
    repository.insert_reports([_report(business_date, "delivery-state")])
    repository.rebuild_daily_summaries(business_date)
    monkeypatch.setattr(cli_module, "_scheduled_skip_reason", lambda *_args: None)
    monkeypatch.setattr(cli_module, "_operation_profile_skip_reason", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_EARLIEST_TIME", time(0))
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_LATEST_TIME", time.max)
    return business_date


def test_command_reloads_paging_state_after_daily_delivery_during_poll(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = _prepare_scheduled_daily_notification(config, repository, monkeypatch)
    poll_started = Event()
    resume_poll = Event()

    def get_updates(*_args, **_kwargs):
        poll_started.set()
        assert resume_poll.wait(5)
        return {"ok": True, "result": [
            {"update_id": 7, "message": {"chat": {"id": "test-chat"}, "text": "/help"}}
        ]}

    monkeypatch.setattr(cli_module, "get_telegram_updates", get_updates)
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")
    with ThreadPoolExecutor(max_workers=2) as executor:
        command = executor.submit(cli_module._run_process_telegram_commands, config, repository)
        try:
            assert poll_started.wait(5)
            delivery = executor.submit(
                cli_module._run_scheduled_notify, config, repository, dry_run=False, allow_repeat=False,
                min_mentions=1,
            )
            assert delivery.result(timeout=5) == 0
            assert load_control_state(config.telegram_control_state_path).delivered_for(business_date) == 1
        finally:
            resume_poll.set()
        assert command.result(timeout=5) == 0

    state = load_control_state(config.telegram_control_state_path)
    assert state.last_update_id == 7
    assert state.active_message_kind == "daily"
    assert state.delivered_for(business_date) == 1


def test_daily_fragment_is_claimed_before_telegram_call(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    statuses: list[str] = []

    def sender(*_args, **_kwargs):
        with repository.connect() as connection:
            row = connection.execute(
                "SELECT status FROM daily_summary_delivery_fragments"
            ).fetchone()
        statuses.append(row["status"])
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", sender)
    message_ids = cli_module._send_production_daily_summary_fragments(
        config,
        repository,
        business_date=date(2026, 4, 24),
        messages=["daily fragment"],
        effective_min_mentions=1,
        require_target_price=False,
    )

    assert message_ids == ["message-1"]
    assert statuses == ["sending"]


def test_intraday_worker_claims_batch_before_telegram_call(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    repository.insert_reports([_report(business_date, "intraday-claim")], queue_intraday_alerts=True)
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    statuses: list[str] = []

    def sender(*_args, **_kwargs):
        with repository.connect() as connection:
            row = connection.execute("SELECT status FROM intraday_alert_batches").fetchone()
        statuses.append(row["status"])
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", sender)
    assert cli_module._run_process_intraday_alerts(config, repository, dry_run=False) == 1

    assert statuses == ["sending"]


def test_definitely_failed_intraday_batch_can_be_retried(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    repository.insert_reports([_report(business_date, "definite-failure")], queue_intraday_alerts=True)
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    calls: list[str] = []

    def sender(*_args, **_kwargs):
        calls.append("send")
        if len(calls) == 1:
            raise RuntimeError("Telegram rejected the request")
        return "retry-message"

    monkeypatch.setattr(cli_module, "send_telegram_message", sender)
    with pytest.raises(RuntimeError, match="delivery failed"):
        cli_module._run_process_intraday_alerts(config, repository, dry_run=False)

    with repository.connect() as connection:
        status = connection.execute("SELECT status FROM intraday_alert_batches").fetchone()[0]
    assert status == "failed"
    assert cli_module._run_process_intraday_alerts(config, repository, dry_run=False) == 1
    assert calls == ["send", "send"]


def test_scheduled_intraday_claims_every_batch_before_combined_message(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    for index, (stock_name, stock_code) in enumerate((("삼성전자", "005930"), ("SK하이닉스", "000660"))):
        repository.insert_reports(
            [_report(business_date, f"hourly-claim-{index}", stock_name=stock_name, stock_code=stock_code)],
            queue_intraday_alerts=True,
        )
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    statuses: list[str] = []

    def sender(*_args, **_kwargs):
        with repository.connect() as connection:
            rows = connection.execute("SELECT status FROM intraday_alert_batches ORDER BY batch_id").fetchall()
        statuses.extend(row["status"] for row in rows)
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", sender)
    scheduled_run_at = datetime(2026, 4, 24, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone))
    assert cli_module._run_scheduled_intraday_briefing(
        config, repository, scheduled_run_at=scheduled_run_at, dry_run=False,
    ) == 2

    assert statuses == ["sending", "sending"]


def test_scheduled_daily_reuses_completed_date_channel_run_and_repairs_log(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = _prepare_scheduled_daily_notification(config, repository, monkeypatch)
    previous_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: previous_sends.append("sent") or "old-message")
    cli_module._send_production_daily_summary_fragments(
        config,
        repository,
        business_date=business_date,
        messages=["summary with old quote"],
        effective_min_mentions=1,
        require_target_price=False,
    )
    assert repository.has_successful_delivery(business_date, cli_module.PRODUCTION_DELIVERY_CHANNEL) is False

    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("sent") or "new-message")
    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False) == 0

    assert previous_sends == ["sent"]
    assert retry_sends == []
    assert repository.has_successful_delivery(business_date, cli_module.PRODUCTION_DELIVERY_CHANNEL)
    with repository.connect() as connection:
        run_count = connection.execute(
            "SELECT COUNT(*) FROM daily_summary_delivery_runs WHERE business_date = ? AND channel = ?",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()[0]
        delivery = connection.execute(
            "SELECT status, message_id FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id DESC LIMIT 1",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()
    assert run_count == 1
    assert tuple(delivery) == ("sent", "old-message")

    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=True) == 0
    assert retry_sends == ["sent"]
    with repository.connect() as connection:
        run_count = connection.execute(
            "SELECT COUNT(*) FROM daily_summary_delivery_runs WHERE business_date = ? AND channel = ?",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()[0]
        delivery = connection.execute(
            "SELECT status, message_id FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id DESC LIMIT 1",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()
    assert run_count == 2
    assert tuple(delivery) == ("sent_repeat", "new-message")


def test_scheduled_daily_completes_all_sent_fragments_before_restoring_log(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = _prepare_scheduled_daily_notification(config, repository, monkeypatch)
    run = repository.start_or_resume_daily_summary_run(
        business_date=business_date,
        channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
        summary_signature="completed-before-log",
        messages=["already delivered"],
        started_at=datetime.now(cli_module.ZoneInfo(config.timezone)),
    )
    attempted_at = datetime.now(cli_module.ZoneInfo(config.timezone))
    assert repository.claim_daily_summary_fragment(run.run_id, 0, attempted_at=attempted_at)
    repository.mark_daily_summary_fragment_sent(
        run.run_id,
        0,
        attempted_at=attempted_at,
        message_id="old-message",
        sent_at=datetime.now(cli_module.ZoneInfo(config.timezone)),
    )
    assert repository.has_successful_delivery(business_date, cli_module.PRODUCTION_DELIVERY_CHANNEL) is False
    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("send") or "new-message")

    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False) == 0

    assert retry_sends == []
    with repository.connect() as connection:
        run_status = connection.execute(
            "SELECT status FROM daily_summary_delivery_runs WHERE run_id = ?",
            (run.run_id,),
        ).fetchone()[0]
        delivery = connection.execute(
            "SELECT status, message_id FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id DESC LIMIT 1",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()
    assert run_status == "sent"
    assert tuple(delivery) == ("sent", "old-message")


def test_explicit_repeat_completion_restores_its_exact_delivery_log(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = _prepare_scheduled_daily_notification(config, repository, monkeypatch)
    first_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: first_sends.append("send") or "first-message-id")
    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False) == 0
    assert first_sends == ["send"]

    marker = tmp_path / "repeat-run-completed"
    _crash_after_sender_accept(tmp_path, "daily_repeat_completed", marker)
    assert marker.read_text(encoding="utf-8") == "second-message-id"

    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("send") or "third-message-id")
    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False) == 0

    assert retry_sends == []
    with repository.connect() as connection:
        rows = connection.execute(
            "SELECT status, message_id FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("sent", "first-message-id"),
        ("sent_repeat", "second-message-id"),
    ]


def test_daily_crash_after_accepted_send_is_ambiguous_until_explicit_repeat(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = _prepare_scheduled_daily_notification(config, repository, monkeypatch)
    marker = tmp_path / "sender-accepted"
    _crash_after_sender_accept(tmp_path, "daily", marker)

    with repository.connect() as connection:
        row = connection.execute(
            "SELECT r.status AS run_status, f.status AS fragment_status "
            "FROM daily_summary_delivery_runs r JOIN daily_summary_delivery_fragments f USING (run_id) "
            "WHERE r.business_date = ? AND r.channel = ?",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()
    assert tuple(row) == ("sending", "sending")

    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("send") or "retry-id")
    with pytest.raises(RuntimeError, match="operator review is required"):
        cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=False)

    assert retry_sends == []
    with repository.connect() as connection:
        row = connection.execute(
            "SELECT r.status AS run_status, f.status AS fragment_status "
            "FROM daily_summary_delivery_runs r JOIN daily_summary_delivery_fragments f USING (run_id) "
            "WHERE r.business_date = ? AND r.channel = ?",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()
        delivery_status = connection.execute(
            "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id DESC LIMIT 1",
            (business_date.isoformat(), cli_module.PRODUCTION_DELIVERY_CHANNEL),
        ).fetchone()[0]
    assert tuple(row) == ("ambiguous", "ambiguous")
    assert delivery_status == "ambiguous"

    assert cli_module._run_scheduled_notify(config, repository, dry_run=False, allow_repeat=True) == 0
    assert retry_sends == ["send"]


@pytest.mark.parametrize(("mode", "batch_count"), [("worker", 1), ("scheduled", 2)])
def test_intraday_crash_after_accepted_send_is_ambiguous_until_explicit_retry(
    tmp_path, monkeypatch, mode: str, batch_count: int,
) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    for index, (stock_name, stock_code) in enumerate((("삼성전자", "005930"), ("SK하이닉스", "000660"))[:batch_count]):
        repository.insert_reports(
            [_report(business_date, f"intraday-crash-{index}", stock_name=stock_name, stock_code=stock_code)],
            queue_intraday_alerts=True,
        )
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    marker = tmp_path / f"{mode}-sender-accepted"
    _crash_after_sender_accept(tmp_path, mode, marker)

    with repository.connect() as connection:
        rows = connection.execute("SELECT status FROM intraday_alert_batches ORDER BY batch_id").fetchall()
    assert [row["status"] for row in rows] == ["sending"] * batch_count

    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("send") or f"retry-{len(retry_sends)}")
    if mode == "worker":
        assert cli_module._run_process_intraday_alerts(config, repository, dry_run=False) == 0
    else:
        scheduled_run_at = datetime(2026, 4, 24, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone))
        assert cli_module._run_scheduled_intraday_briefing(
            config, repository, scheduled_run_at=scheduled_run_at, dry_run=False,
        ) == 0

    assert retry_sends == []
    with repository.connect() as connection:
        rows = connection.execute("SELECT status FROM intraday_alert_batches ORDER BY batch_id").fetchall()
        delivery_status = connection.execute(
            "SELECT status FROM delivery_log WHERE business_date = ? AND channel = 'telegram_intraday' ORDER BY id DESC LIMIT 1",
            (business_date.isoformat(),),
        ).fetchone()[0]
    assert [row["status"] for row in rows] == ["ambiguous"] * batch_count
    assert delivery_status == "ambiguous"

    assert cli_module._run_process_intraday_alerts(
        config, repository, dry_run=False, retry_ambiguous=True,
    ) == batch_count
    assert len(retry_sends) == batch_count


def test_delivery_lock_excludes_another_process_and_releases_on_exception(tmp_path) -> None:
    db_path = tmp_path / "stock-monitor.db"
    acquired = Event()
    child_code = "\n".join(
        (
            "import sys",
            "sys.path.insert(0, sys.argv[1])",
            "from pathlib import Path",
            "from stock_monitor.notify.delivery_lock import delivery_lock",
            "print('waiting', flush=True)",
            "with delivery_lock(Path(sys.argv[2])):",
            "    print('acquired', flush=True)",
        )
    )
    process = None
    reader = None
    with pytest.raises(RuntimeError, match="release the lock"):
        with delivery_lock(db_path):
            process = subprocess.Popen(
                [sys.executable, "-c", child_code, str(Path(__file__).resolve().parents[1] / "src"), str(db_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert process.stdout is not None
            assert process.stdout.readline().strip() == "waiting"

            def read_acquired() -> None:
                if process is not None and process.stdout is not None and process.stdout.readline().strip() == "acquired":
                    acquired.set()

            reader = Thread(target=read_acquired)
            reader.start()
            assert not acquired.wait(0.2)
            raise RuntimeError("release the lock")

    try:
        assert acquired.wait(5)
        assert process is not None
        assert process.wait(timeout=5) == 0
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
        if reader is not None:
            reader.join(timeout=5)


def test_windows_delivery_lock_retries_after_lock_timeout_and_unlocks_on_error(tmp_path, monkeypatch) -> None:
    if os.name != "nt":
        pytest.skip("Windows CRT file locks are platform-specific")
    import msvcrt

    calls = []

    def fake_locking(_file_descriptor, mode, _length):
        calls.append(mode)
        if len(calls) == 1:
            raise OSError(errno.EDEADLK, "lock wait timed out")

    monkeypatch.setattr(msvcrt, "locking", fake_locking)
    with pytest.raises(RuntimeError, match="release the lock"):
        with delivery_lock(tmp_path / "stock-monitor.db"):
            raise RuntimeError("release the lock")

    assert calls == [msvcrt.LK_LOCK, msvcrt.LK_LOCK, msvcrt.LK_UNLCK]


def test_scheduled_daily_delivery_serializes_duplicate_entries(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = cli_module.previous_business_day(
        datetime.now(cli_module.ZoneInfo(config.timezone)).date(),
        config.holiday_overrides,
    )
    repository.insert_reports([_report(business_date, "daily-lock")])
    repository.rebuild_daily_summaries(business_date)
    monkeypatch.setattr(cli_module, "_scheduled_skip_reason", lambda *_args: None)
    monkeypatch.setattr(cli_module, "_operation_profile_skip_reason", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_EARLIEST_TIME", time(0))
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_LATEST_TIME", time.max)
    sender_gate = _sender_gate()
    monkeypatch.setattr(cli_module, "send_telegram_message", sender_gate[0])

    results = _run_overlapping_deliveries(
        lambda: cli_module._run_scheduled_notify(
            config, repository, dry_run=False, allow_repeat=False,
        ),
        lambda: cli_module._run_scheduled_notify(
            config, repository, dry_run=False, allow_repeat=False,
        ),
        sender_gate,
    )

    assert results == (0, 0)
    assert len(sender_gate[4]) == 1


def test_intraday_batch_worker_serializes_duplicate_entries(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    repository.insert_reports([_report(business_date, "intraday-lock")], queue_intraday_alerts=True)
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    sender_gate = _sender_gate()
    monkeypatch.setattr(cli_module, "send_telegram_message", sender_gate[0])

    results = _run_overlapping_deliveries(
        lambda: cli_module._run_process_intraday_alerts(config, repository, dry_run=False),
        lambda: cli_module._run_process_intraday_alerts(config, repository, dry_run=False),
        sender_gate,
    )

    assert sorted(results) == [0, 1]
    assert len(sender_gate[4]) == 1


def test_scheduled_intraday_briefing_serializes_duplicate_entries(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = date(2026, 4, 24)
    repository.insert_reports([_report(business_date, "hourly-lock")], queue_intraday_alerts=True)
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    sender_gate = _sender_gate()
    monkeypatch.setattr(cli_module, "send_telegram_message", sender_gate[0])
    scheduled_run_at = datetime(2026, 4, 24, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone))

    results = _run_overlapping_deliveries(
        lambda: cli_module._run_scheduled_intraday_briefing(
            config, repository, scheduled_run_at=scheduled_run_at, dry_run=False,
        ),
        lambda: cli_module._run_scheduled_intraday_briefing(
            config, repository, scheduled_run_at=scheduled_run_at, dry_run=False,
        ),
        sender_gate,
    )

    assert sorted(results) == [0, 1]
    assert len(sender_gate[4]) == 1


def test_delivery_dry_runs_do_not_create_lock_or_send(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    business_date = cli_module.previous_business_day(
        datetime.now(cli_module.ZoneInfo(config.timezone)).date(),
        config.holiday_overrides,
    )
    repository.insert_reports([_report(business_date, "dry-run-lock")], queue_intraday_alerts=True)
    repository.rebuild_daily_summaries(business_date)
    monkeypatch.setattr(cli_module, "_scheduled_skip_reason", lambda *_args: None)
    monkeypatch.setattr(cli_module, "_operation_profile_skip_reason", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_EARLIEST_TIME", time(0))
    monkeypatch.setattr(cli_module, "SCHEDULED_NOTIFY_LATEST_TIME", time.max)
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("send"))
    scheduled_run_at = datetime.combine(business_date, time(10), tzinfo=cli_module.ZoneInfo(config.timezone))

    assert cli_module._run_scheduled_notify(
        config, repository, dry_run=True, allow_repeat=False,
    ) == 0
    assert cli_module._run_process_intraday_alerts(config, repository, dry_run=True) == 1
    assert cli_module._run_scheduled_intraday_briefing(
        config, repository, scheduled_run_at=scheduled_run_at, dry_run=True,
    ) == 1

    assert sends == []
    assert not repository.db_path.with_name(f"{repository.db_path.name}.delivery.lock").exists()
    state_path = config.telegram_control_state_path
    assert not state_path.exists()
    assert not state_path.with_name(f"{state_path.name}.write.lock").exists()
