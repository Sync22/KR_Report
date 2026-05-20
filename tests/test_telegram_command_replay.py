from datetime import date, datetime

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.notify.control import TelegramControlState, load_control_state, save_control_state
from stock_monitor.models import MarketIndexDailySnapshot, Report


def test_process_telegram_commands_persists_progress_after_each_successful_update(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"chat": {"id": "chat-1"}, "text": "/help"}},
                {"update_id": 2, "message": {"chat": {"id": "chat-1"}, "text": "/help"}},
            ],
        },
    )

    send_count = 0

    def fake_send(*_args, **_kwargs) -> str:
        nonlocal send_count
        send_count += 1
        if send_count == 2:
            raise RuntimeError("temporary telegram failure")
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    with pytest.raises(RuntimeError, match="temporary telegram failure"):
        cli_module._run_process_telegram_commands(config, repository)

    state = load_control_state(config.telegram_control_state_path)
    assert state.last_update_id == 1
    assert send_count == 2


def test_process_telegram_commands_does_not_duplicate_memo_when_ack_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 10, "message": {"chat": {"id": "chat-1"}, "text": "/메모 KRX 수급 확인"}}],
        },
    )

    send_count = 0

    def flaky_send(*_args, **_kwargs) -> str:
        nonlocal send_count
        send_count += 1
        if send_count == 1:
            raise RuntimeError("temporary telegram failure")
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", flaky_send)

    with pytest.raises(RuntimeError, match="temporary telegram failure"):
        cli_module._run_process_telegram_commands(config, repository)

    state_after_failure = load_control_state(config.telegram_control_state_path)
    memo_path = tmp_path / "data" / "operator_memos.md"
    assert state_after_failure.last_update_id == 0
    assert state_after_failure.memo_applied_update_ids == (10,)
    assert memo_path.read_text(encoding="utf-8").count("KRX 수급 확인") == 1

    result = cli_module._run_process_telegram_commands(config, repository)

    state_after_retry = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert send_count == 2
    assert state_after_retry.last_update_id == 10
    assert state_after_retry.memo_applied_update_ids == (10,)
    assert memo_path.read_text(encoding="utf-8").count("KRX 수급 확인") == 1


def test_process_telegram_commands_queues_progress_request_without_duplicate_on_retry(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 31, "message": {"chat": {"id": "chat-1"}, "text": "/진행 KRX OpenAPI 상태 확인"}}],
        },
    )

    send_count = 0

    def flaky_send(*_args, **_kwargs) -> str:
        nonlocal send_count
        send_count += 1
        if send_count == 1:
            raise RuntimeError("temporary telegram failure")
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", flaky_send)

    with pytest.raises(RuntimeError, match="temporary telegram failure"):
        cli_module._run_process_telegram_commands(config, repository)

    queue_path = tmp_path / "data" / "operator_progress_requests.jsonl"
    state_after_failure = load_control_state(config.telegram_control_state_path)
    assert state_after_failure.last_update_id == 0
    assert state_after_failure.progress_applied_update_ids == (31,)
    assert queue_path.read_text(encoding="utf-8").count("KRX OpenAPI 상태 확인") == 1

    result = cli_module._run_process_telegram_commands(config, repository)

    state_after_retry = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert send_count == 2
    assert state_after_retry.last_update_id == 31
    assert state_after_retry.progress_applied_update_ids == (31,)
    assert queue_path.read_text(encoding="utf-8").count("KRX OpenAPI 상태 확인") == 1


def test_process_telegram_commands_accepts_krx_login_check_ack(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 11, "message": {"chat": {"id": "chat-1"}, "text": "/체크 로그인"}}],
        },
    )
    sent_messages: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sent_messages.append(str(_args[2])) or "message-1")

    result = cli_module._run_process_telegram_commands(config, repository)

    state = load_control_state(config.telegram_control_state_path)
    events = repository.list_recent_operation_events(limit=1)
    assert result == 0
    assert state.last_update_id == 11
    assert "KRX 로그인 확인 접수" in sent_messages[0]
    assert events[0].component == "krx-flow"
    assert events[0].event_type == "login-ack"


def test_process_telegram_commands_replies_with_market_commentary(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 18, 9, 5, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="테스트전자",
                stock_code="005930",
                title="테스트 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=business_date,
                index_series="KOSPI",
                index_class="주가지수",
                index_name="코스피",
                fetched_at=now,
                change_percent=0.4,
            )
        ]
    )
    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 12, "message": {"chat": {"id": "chat-1"}, "text": "/한줄 2026-05-18"}}],
        },
    )
    sent_messages: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sent_messages.append(str(_args[2])) or "message-1")

    assert cli_module._run_process_telegram_commands(config, repository) == 0

    assert len(sent_messages) == 1
    assert "한줄 코멘트" in sent_messages[0]
    assert "장초반" in sent_messages[0]
    assert "점심" in sent_messages[0]
    assert "장 마감 전" in sent_messages[0]
    assert "매수 추천" not in sent_messages[0]


def test_process_telegram_commands_saves_captioned_photo_to_local_inbox(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [
                {
                    "update_id": 13,
                    "message": {
                        "chat": {"id": "chat-1"},
                        "caption": "/사진 리포트 예시",
                        "photo": [
                            {"file_id": "small", "file_unique_id": "s", "file_size": 10},
                            {"file_id": "large", "file_unique_id": "l", "file_size": 20},
                        ],
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(cli_module, "get_telegram_file_path", lambda *_args, **_kwargs: "photos/example.jpg")
    monkeypatch.setattr(cli_module, "download_telegram_file", lambda *_args, **_kwargs: b"image-bytes")
    sent_messages: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sent_messages.append(str(_args[2])) or "message-1")

    assert cli_module._run_process_telegram_commands(config, repository) == 0

    files = list((tmp_path / "data" / "operator_photo_inbox").glob("*.jpg"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"image-bytes"
    assert (tmp_path / "data" / "operator_photo_inbox" / f"{files[0].stem}.json").exists()
    assert "사진 저장 완료" in sent_messages[0]


def test_process_telegram_commands_uses_pending_photo_caption_for_next_photo(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [
                {"update_id": 14, "message": {"chat": {"id": "chat-1"}, "text": "/사진 장마감 예시"}},
                {
                    "update_id": 15,
                    "message": {
                        "chat": {"id": "chat-1"},
                        "photo": [{"file_id": "large", "file_unique_id": "l", "file_size": 20}],
                    },
                },
            ],
        },
    )
    monkeypatch.setattr(cli_module, "get_telegram_file_path", lambda *_args, **_kwargs: "photos/example.png")
    monkeypatch.setattr(cli_module, "download_telegram_file", lambda *_args, **_kwargs: b"image-bytes")
    sent_messages: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sent_messages.append(str(_args[2])) or "message-1")

    assert cli_module._run_process_telegram_commands(config, repository) == 0

    files = list((tmp_path / "data" / "operator_photo_inbox").glob("*.png"))
    assert len(files) == 1
    metadata = (tmp_path / "data" / "operator_photo_inbox" / f"{files[0].stem}.json").read_text(encoding="utf-8")
    assert "장마감 예시" in metadata
    assert any("다음 사진을 저장합니다" in message for message in sent_messages)
    assert any("사진 저장 완료" in message for message in sent_messages)


def test_process_telegram_commands_does_not_duplicate_krx_login_check_ack_when_send_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 12, "message": {"chat": {"id": "chat-1"}, "text": "/체크 로그인"}}],
        },
    )
    send_count = 0

    def flaky_send(*_args, **_kwargs) -> str:
        nonlocal send_count
        send_count += 1
        if send_count == 1:
            raise RuntimeError("temporary telegram failure")
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", flaky_send)

    with pytest.raises(RuntimeError, match="temporary telegram failure"):
        cli_module._run_process_telegram_commands(config, repository)

    state_after_failure = load_control_state(config.telegram_control_state_path)
    assert state_after_failure.last_update_id == 0
    assert state_after_failure.check_applied_update_ids == (12,)
    assert len(repository.list_recent_operation_events(limit=10)) == 1

    result = cli_module._run_process_telegram_commands(config, repository)

    state_after_retry = load_control_state(config.telegram_control_state_path)
    events = repository.list_recent_operation_events(limit=10)
    assert result == 0
    assert send_count == 2
    assert state_after_retry.last_update_id == 12
    assert state_after_retry.check_applied_update_ids == (12,)
    assert len(events) == 1
    assert events[0].event_type == "login-ack"


def test_lookup_stock_research_cli_passes_quote_to_formatter(tmp_path, monkeypatch) -> None:
    from stock_monitor.fetch.naver_stock_quote import StockQuoteSnapshot
    from stock_monitor.fetch.naver_stock_research import StockResearchLookupResult
    from stock_monitor.models import StockResearchEntry

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    quote = StockQuoteSnapshot(
        stock_code="017670",
        stock_name="SK Telecom",
        sector_code="5010",
        sector_name="Wireless Telecom",
        current_price=219_500,
        market_status="OPEN",
        trade_time=datetime(2026, 4, 28, 10, 0, 0),
        prev_close_price=218_000,
    )

    monkeypatch.setattr(
        cli_module,
        "fetch_stock_research_entries",
        lambda *_args, **_kwargs: StockResearchLookupResult(
            stock_code="017670",
            stock_name="SK Telecom",
            as_of_date=date(2026, 4, 28),
            lookback_days=15,
            entries=(
                StockResearchEntry(
                    stock_name="SK Telecom",
                    stock_code="017670",
                    broker_name="Test Securities",
                    title="steady cash flow",
                    write_date=date(2026, 4, 27),
                    target_price_value=140_000,
                    opinion_normalized="buy",
                ),
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "fetch_stock_quote_snapshot", lambda *_args, **_kwargs: quote)

    seen: dict[str, object] = {}

    def fake_format(*_args, **kwargs) -> str:
        seen["quote"] = kwargs.get("quote")
        return "formatted"

    monkeypatch.setattr(cli_module, "format_stock_research_lookup_message", fake_format)

    result = cli_module._run_lookup_stock_research(
        config,
        stock_code="017670",
        lookback_days=15,
        entry_limit=5,
    )

    assert result == 0
    assert seen["quote"] is quote


def test_send_test_notification_does_not_advance_production_paging_state(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        repository,
        "list_daily_summaries",
        lambda _business_date: [
            DailyStockSummary(
                business_date=date(2026, 4, 24),
            stock_name="Samsung Electronics",
            stock_code="005930",
            mention_count=2,
                broker_display="NH(1)",
                target_price_min=92_000,
                target_price_max=92_000,
                dominant_opinion="buy",
                generated_at=datetime(2026, 4, 24, 16, 0, 0),
            )
        ],
    )
    monkeypatch.setattr(repository, "has_successful_delivery", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(repository, "record_delivery", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")

    result = cli_module._run_send_test_notification(
        config,
        repository,
        explicit_date=date(2026, 4, 24),
        custom_message=None,
        dry_run=False,
        allow_repeat=False,
        limit=None,
    )

    state = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert state.active_message_kind is None
    assert state.delivered_for(date(2026, 4, 24)) == 0


def test_production_daily_notification_sends_all_summaries_by_default(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name=f"Stock {index}",
            stock_code=f"{index:06d}",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=92_000,
            target_price_max=92_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        )
        for index in range(10)
    ]

    seen: dict[str, object] = {}
    sent_messages: list[str] = []
    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(repository, "has_successful_delivery", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(repository, "record_delivery", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_format_messages(_business_date, _summaries, **kwargs) -> list[str]:
        seen["summary_count"] = len(_summaries)
        seen["quotes"] = kwargs.get("quotes_by_stock_code")
        return ["daily all 1", "daily all 2"]

    def fake_send(_token, _chat_id, message, **_kwargs) -> str:
        sent_messages.append(message)
        return f"message-{len(sent_messages)}"

    monkeypatch.setattr(cli_module, "format_daily_summary_messages", fake_format_messages)
    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    result = cli_module._run_send_test_notification(
        config,
        repository,
        explicit_date=date(2026, 4, 24),
        custom_message=None,
        dry_run=False,
        allow_repeat=False,
        limit=None,
        delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
    )

    state = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert seen["summary_count"] == len(summaries)
    assert sent_messages == ["daily all 1", "daily all 2"]
    assert state.delivered_for(date(2026, 4, 24)) == len(summaries)


def test_production_daily_notification_resumes_after_fragment_failure(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name=f"Stock {index}",
            stock_code=f"{index:06d}",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=92_000,
            target_price_max=92_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        )
        for index in range(3)
    ]
    sent_messages: list[str] = []
    attempts = {"count": 0}
    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        cli_module,
        "format_daily_summary_messages",
        lambda *_args, **_kwargs: ["daily all 1", "daily all 2"],
    )

    def fake_send(_token, _chat_id, message, **_kwargs) -> str:
        attempts["count"] += 1
        sent_messages.append(message)
        if attempts["count"] == 2:
            raise RuntimeError("temporary telegram failure")
        return f"message-{attempts['count']}"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    with pytest.raises(RuntimeError, match="temporary telegram failure"):
        cli_module._run_send_test_notification(
            config,
            repository,
            explicit_date=date(2026, 4, 24),
            custom_message=None,
            dry_run=False,
            allow_repeat=False,
            limit=None,
            delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
        )

    state = load_control_state(config.telegram_control_state_path)
    assert state.delivered_for(date(2026, 4, 24)) == 0
    assert sent_messages == ["daily all 1", "daily all 2"]

    result = cli_module._run_send_test_notification(
        config,
        repository,
        explicit_date=date(2026, 4, 24),
        custom_message=None,
        dry_run=False,
        allow_repeat=False,
        limit=None,
        delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
    )

    state = load_control_state(config.telegram_control_state_path)
    assert result == 0
    assert sent_messages == ["daily all 1", "daily all 2", "daily all 2"]
    assert state.delivered_for(date(2026, 4, 24)) == len(summaries)


def test_production_daily_fragment_timeout_failure_records_ambiguous_send_trace(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="Timeout Stock",
            stock_code="000001",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=92_000,
            target_price_max=92_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        )
    ]
    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        cli_module,
        "format_daily_summary_messages",
        lambda *_args, **_kwargs: ["daily fragment maybe sent"],
    )

    def timeout_send(*_args, **_kwargs) -> str:
        raise TimeoutError("timed out after sendMessage request")

    monkeypatch.setattr(cli_module, "send_telegram_message", timeout_send)

    with pytest.raises(TimeoutError, match="timed out"):
        cli_module._run_send_test_notification(
            config,
            repository,
            explicit_date=date(2026, 4, 24),
            custom_message=None,
            dry_run=False,
            allow_repeat=False,
            limit=None,
            delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
        )

    events = repository.list_recent_operation_events(limit=1)
    assert events[0].component == "notify"
    assert events[0].event_type == "fragment"
    assert events[0].status == "failed"
    assert "ambiguous_send=true" in events[0].detail
    assert f"message_hash={cli_module._hash_text('daily fragment maybe sent')[:16]}" in events[0].detail


def test_daily_notification_can_filter_single_report_summaries(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="Single",
            stock_code="000001",
            mention_count=1,
            broker_display="NH(1)",
            target_price_min=92_000,
            target_price_max=92_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="Multiple",
            stock_code="000002",
            mention_count=2,
            broker_display="NH(2)",
            target_price_min=92_000,
            target_price_max=93_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
    ]
    seen: dict[str, object] = {}
    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(repository, "has_successful_delivery", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(repository, "record_delivery", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "record_operation_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_format_messages(_business_date, filtered_summaries, **_kwargs) -> list[str]:
        seen["stock_names"] = [summary.stock_name for summary in filtered_summaries]
        return ["filtered"]

    monkeypatch.setattr(cli_module, "format_daily_summary_messages", fake_format_messages)
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")

    result = cli_module._run_send_test_notification(
        config,
        repository,
        explicit_date=date(2026, 4, 24),
        custom_message=None,
        dry_run=False,
        allow_repeat=False,
        limit=None,
        min_mentions=2,
        delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
    )

    assert result == 0
    assert seen["stock_names"] == ["Multiple"]


def test_daily_notification_filters_summaries_without_target_price_by_default(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="No Target",
            stock_code="000001",
            mention_count=3,
            broker_display="NH(3)",
            target_price_min=None,
            target_price_max=None,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="Has Target",
            stock_code="000002",
            mention_count=2,
            broker_display="NH(2)",
            target_price_min=92_000,
            target_price_max=93_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
    ]
    seen: dict[str, object] = {}
    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(repository, "has_successful_delivery", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(repository, "record_delivery", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(repository, "record_operation_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_format_messages(_business_date, filtered_summaries, **_kwargs) -> list[str]:
        seen["stock_names"] = [summary.stock_name for summary in filtered_summaries]
        return ["filtered"]

    monkeypatch.setattr(cli_module, "format_daily_summary_messages", fake_format_messages)
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")

    result = cli_module._run_send_test_notification(
        config,
        repository,
        explicit_date=date(2026, 4, 24),
        custom_message=None,
        dry_run=False,
        allow_repeat=False,
        limit=None,
        delivery_channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
    )

    assert result == 0
    assert seen["stock_names"] == ["Has Target"]


def test_daily_paging_reuses_current_summary_filters(tmp_path, monkeypatch) -> None:
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 4, 24)
    summaries = [
        DailyStockSummary(
            business_date=business_date,
            stock_name="Keep One",
            stock_code="000001",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=92_000,
            target_price_max=92_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=business_date,
            stock_name="Keep Two",
            stock_code="000002",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=102_000,
            target_price_max=102_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=business_date,
            stock_name="Filtered Single",
            stock_code="000003",
            mention_count=1,
            broker_display="NH(1)",
            target_price_min=80_000,
            target_price_max=80_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=business_date,
            stock_name="Filtered No Target",
            stock_code="000004",
            mention_count=2,
            broker_display="NH(1)",
            target_price_min=None,
            target_price_max=None,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        ),
    ]
    state = TelegramControlState()
    state.set_delivered_for(business_date, 1)
    save_control_state(config.telegram_control_state_path, state)

    monkeypatch.setattr(repository, "list_daily_summaries", lambda _business_date: summaries)
    monkeypatch.setattr(
        cli_module,
        "get_telegram_updates",
        lambda *_args, **_kwargs: {
            "ok": True,
            "result": [{"update_id": 1, "message": {"chat": {"id": "chat-1"}, "text": "다음"}}],
        },
    )
    monkeypatch.setattr(cli_module, "_fetch_daily_summary_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    seen: dict[str, object] = {}

    def fake_format(_business_date, filtered_summaries, **kwargs) -> str:
        seen["names"] = [summary.stock_name for summary in filtered_summaries]
        seen["offset"] = kwargs.get("offset")
        return "filtered next page"

    monkeypatch.setattr(cli_module, "format_daily_summary_message", fake_format)
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "message-1")

    result = cli_module._run_process_telegram_commands(config, repository)

    assert result == 0
    assert seen["names"] == ["Keep One", "Keep Two"]
    assert seen["offset"] == 1


def test_daily_quote_fetch_caches_stock_metadata(tmp_path, monkeypatch) -> None:
    from stock_monitor.fetch.naver_stock_quote import StockQuoteSnapshot
    from stock_monitor.models import DailyStockSummary

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 4, 24),
            stock_name="Samsung Electronics",
            stock_code="005930",
            mention_count=2,
            broker_display="NH(2)",
            target_price_min=92_000,
            target_price_max=93_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 4, 24, 16, 0, 0),
        )
    ]
    quote = StockQuoteSnapshot(
        stock_code="005930",
        stock_name="삼성전자",
        sector_code="1010",
        sector_name="반도체",
        current_price=85_000,
        market_status="OPEN",
        trade_time=datetime(2026, 5, 7, 9, 0, 0),
        prev_close_price=84_000,
    )
    monkeypatch.setattr(cli_module, "fetch_stock_quote_snapshot", lambda *_args, **_kwargs: quote)

    quotes = cli_module._fetch_daily_summary_quotes_by_stock_code(config, summaries, repository=repository)

    metadata = repository.get_stock_metadata("005930")
    assert quotes["005930"] is quote
    assert metadata is not None
    assert metadata.stock_name == "삼성전자"
    assert metadata.sector_name == "반도체"
