from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import time
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock

from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import DeliveryLog
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


def _configure_market_briefing_fakes(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "_scheduled_skip_reason", lambda *_args: None)
    monkeypatch.setattr(cli_module, "_operation_profile_skip_reason", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_effective_bool_setting", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_module, "_market_briefing_manual_review_dates", lambda _repository: [
        "2026-10-01", "2026-10-02", "2026-10-05",
    ])
    monkeypatch.setattr(cli_module, "_market_briefing_slot_window", lambda _slot: (time(0), time(23, 59)))
    monkeypatch.setattr(
        cli_module,
        "_collect_scheduled_market_briefing_news_observations",
        lambda *_args, **_kwargs: {
            "target_stock_codes": [], "ok": True, "saved_observation_count": 0, "saved_evidence_count": 0,
        },
    )
    monkeypatch.setattr(cli_module, "_build_market_briefing_message", lambda *_args, **_kwargs: "시장 참고 브리핑")


def _scheduled_slot(config: RuntimeConfig, repository: StockMonitorRepository, *, allow_repeat: bool = False, dry_run: bool = False) -> int:
    return cli_module._run_scheduled_market_briefing_slot(
        config,
        repository,
        slot="mood",
        dry_run=dry_run,
        allow_repeat=allow_repeat,
        allow_late=True,
        limit=5,
    )


def _crash_scheduled_slot_after_accept(root: Path, marker: Path) -> None:
    child_code = "\n".join(
        (
            "import os, sys",
            "from datetime import time",
            "from pathlib import Path",
            "sys.path.insert(0, sys.argv[2])",
            "from stock_monitor.config import RuntimeConfig",
            "from stock_monitor.db.repository import StockMonitorRepository",
            "import stock_monitor.cli as cli",
            "root = Path(sys.argv[1])",
            "config = RuntimeConfig.from_env(root_dir=root)",
            "repository = StockMonitorRepository(config.db_path, timezone=config.timezone)",
            "cli._scheduled_skip_reason = lambda *_args: None",
            "cli._operation_profile_skip_reason = lambda *_args, **_kwargs: None",
            "cli._effective_bool_setting = lambda *_args, **_kwargs: True",
            "cli._market_briefing_manual_review_dates = lambda _repository: ['2026-10-01','2026-10-02','2026-10-05']",
            "cli._market_briefing_slot_window = lambda _slot: (time(0), time(23, 59))",
            "cli._collect_scheduled_market_briefing_news_observations = lambda *_args, **_kwargs: {'target_stock_codes': [], 'ok': True, 'saved_observation_count': 0, 'saved_evidence_count': 0}",
            "cli._build_market_briefing_message = lambda *_args, **_kwargs: '시장 참고 브리핑'",
            "def accepted_then_crash(_token, _chat, _message, **_kwargs):",
            "    Path(sys.argv[3]).write_text('accepted', encoding='utf-8')",
            "    os._exit(73)",
            "cli.send_telegram_message = accepted_then_crash",
            "cli._run_scheduled_market_briefing_slot(config, repository, slot='mood', dry_run=False, allow_repeat=False, allow_late=True, limit=5)",
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", child_code, str(root), str(Path(__file__).resolve().parents[1] / "src"), str(marker)],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert result.returncode == 73, result.stdout + result.stderr
    assert marker.read_text(encoding="utf-8") == "accepted"


def test_scheduled_slot_crash_after_accept_is_ambiguous_until_explicit_repeat(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    _configure_market_briefing_fakes(monkeypatch)
    marker = tmp_path / "market-sender-accepted"
    _crash_scheduled_slot_after_accept(tmp_path, marker)
    base_channel = f"{cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL}_mood"

    with repository.connect() as connection:
        row = connection.execute(
            "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ?",
            (cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date().isoformat(), base_channel),
        ).fetchone()
    assert row["status"] == "sending"

    retry_sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: retry_sends.append("send") or "retry-id")
    assert _scheduled_slot(config, repository) == 0
    assert retry_sends == []
    assert repository.has_latest_delivery_status(
        cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date(), base_channel, status="ambiguous",
    )

    assert _scheduled_slot(config, repository, allow_repeat=True) == 0
    assert retry_sends == ["send"]


def test_scheduled_slot_rechecks_date_channel_guard_after_lock_wait(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    _configure_market_briefing_fakes(monkeypatch)
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

    monkeypatch.setattr(cli_module, "send_telegram_message", sender)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_scheduled_slot, config, repository)
        assert first_send_started.wait(5)
        second_started = Event()

        def run_second() -> int:
            second_started.set()
            return _scheduled_slot(config, repository)

        second = pool.submit(run_second)
        assert second_started.wait(5)
        try:
            assert not second_send_started.wait(0.2)
        finally:
            release_first_send.set()
        assert (first.result(timeout=5), second.result(timeout=5)) == (0, 0)

    assert calls == ["시장 참고 브리핑"]


def test_scheduled_slot_recovers_repeat_attempt_before_base_channel_skip(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    _configure_market_briefing_fakes(monkeypatch)
    business_date = cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date()
    base_channel = f"{cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL}_mood"
    repeat_channel = f"{base_channel}:repeat:20261115123456789012"
    attempted_at = cli_module.datetime.now(cli_module.ZoneInfo(config.timezone))
    repository.record_delivery(
        DeliveryLog(
            business_date=business_date,
            channel=base_channel,
            status="sent",
            delivered_at=attempted_at,
            message_id="base-message",
        )
    )
    repository.record_delivery(
        DeliveryLog(
            business_date=business_date,
            channel=repeat_channel,
            status="sending",
            delivered_at=attempted_at,
        )
    )
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("send") or "new-message")

    assert _scheduled_slot(config, repository, allow_repeat=False) == 0

    assert sends == []
    with repository.connect() as connection:
        rows = connection.execute(
            "SELECT channel, status FROM delivery_log ORDER BY id",
        ).fetchall()
    assert [tuple(row) for row in rows] == [
        (base_channel, "sent"),
        (repeat_channel, "ambiguous"),
    ]


def test_scheduled_slot_allow_repeat_uses_a_separate_channel(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    _configure_market_briefing_fakes(monkeypatch)
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("send") or f"message-{len(sends)}")

    assert _scheduled_slot(config, repository) == 0
    assert _scheduled_slot(config, repository, allow_repeat=True) == 0

    assert sends == ["send", "send"]
    with repository.connect() as connection:
        rows = connection.execute(
            "SELECT status, channel FROM delivery_log ORDER BY id",
        ).fetchall()
    assert tuple(rows[0]) == ("sent", f"{cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL}_mood")
    assert rows[1]["status"] == "sent"
    assert rows[1]["channel"].startswith(f"{cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL}_mood:repeat:")


def test_same_day_manual_market_briefing_repeat_uses_sent_repeat_status(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_module, "_build_market_briefing_toss_priority_context", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "_build_market_briefing_message", lambda *_args, **_kwargs: "시장 참고 브리핑")
    monkeypatch.setattr(cli_module, "_ensure_market_briefing_message_public_safe", lambda _message: None)
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("send") or f"manual-{len(sends)}")

    for _ in range(2):
        assert cli_module._run_market_briefing(
            config,
            repository,
            explicit_date=cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date(),
            limit=5,
            send=True,
        ) == 0

    assert sends == ["send", "send"]
    with repository.connect() as connection:
        rows = connection.execute(
            "SELECT status, message_id FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id",
            (cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date().isoformat(), cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL),
        ).fetchall()
    assert [tuple(row) for row in rows] == [("sent", "manual-1"), ("sent_repeat", "manual-2")]


def test_market_briefing_dry_run_does_not_write_attempt_or_lock(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    _configure_market_briefing_fakes(monkeypatch)
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("send") or "id")
    business_date = cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)).date()
    repository.record_delivery(cli_module.DeliveryLog(
        business_date=business_date,
        channel=f"{cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL}_mood",
        status="sending",
        delivered_at=cli_module.datetime.now(cli_module.ZoneInfo(config.timezone)),
    ))

    assert _scheduled_slot(config, repository, dry_run=True) == 0

    assert sends == []
    with repository.connect() as connection:
        status = connection.execute("SELECT status FROM delivery_log").fetchone()[0]
    assert status == "sending"
    assert not repository.db_path.with_name(f"{repository.db_path.name}.delivery.lock").exists()
