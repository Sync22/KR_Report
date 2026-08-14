from dataclasses import replace
from datetime import date, datetime

import pytest

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import Opinion, Report, StockMetadata


def _report(
    *,
    title: str = "recovery visible",
    broker_name: str = "NH",
    source_id: str = "91999",
    identity_key: str = "identity-1",
    target_price_value: int = 92_000,
) -> Report:
    return Report(
        stock_name="Samsung Electronics",
        stock_code="005930",
        title=title,
        broker_name=broker_name,
        published_at=datetime(2026, 4, 24, 9, 0, 0),
        collected_at=datetime(2026, 4, 24, 9, 30, 0),
        business_date=date(2026, 4, 24),
        target_price_raw=str(target_price_value),
        target_price_value=target_price_value,
        opinion_raw="Buy",
        opinion_normalized=Opinion.BUY.value,
        source_url=f"https://stock.naver.com/research/company/{source_id}",
        source_id=source_id,
        identity_key=identity_key,
    )


def _inspection(row_count: int) -> object:
    return type(
        "Inspection",
        (),
        {
            "api_pages_fetched": 1,
            "api_items": [{} for _ in range(row_count)],
            "candidate_rows": [object() for _ in range(row_count)],
        },
    )()


def _config_and_repository(tmp_path, monkeypatch) -> tuple[RuntimeConfig, StockMonitorRepository]:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat-1")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    return config, repository


def test_manual_poll_sends_intraday_empty_notification_when_no_new_reports(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=False)

    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))

    empty_calls: list[datetime | None] = []
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda _config, _repository, *, polled_at=None, dry_run=False: empty_calls.append(polled_at) or 0,
    )
    process_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda *_args, **_kwargs: process_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=True,
    )

    assert result == 0
    assert len(process_calls) == 1
    assert len(empty_calls) == 1


def test_manual_poll_retries_pending_intraday_batches_before_empty_notification(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=True)

    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))

    process_calls: list[object] = []
    empty_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda _config, _repository, **_kwargs: process_calls.append(_kwargs) or 1,
    )
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda *_args, **_kwargs: empty_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=True,
    )

    assert result == 0
    assert len(process_calls) == 1
    assert not empty_calls


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (8, True),
        (9, True),
        (15, True),
        (16, False),
    ],
)
def test_scheduled_intraday_briefing_time_allows_only_0830_through_1530(hour: int, expected: bool) -> None:
    scheduled_at = datetime(2026, 4, 24, hour, 30, tzinfo=cli_module.ZoneInfo("Asia/Seoul"))

    assert cli_module._is_scheduled_intraday_briefing_time(scheduled_at) is expected


def test_scheduled_poll_outside_hourly_delivery_window_collects_without_telegram_delivery(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))
    process_calls: list[object] = []
    empty_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda *_args, **_kwargs: process_calls.append(_kwargs) or 0,
    )
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda *_args, **_kwargs: empty_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=True,
        scheduled_run_at=datetime(2026, 4, 24, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone)),
    )

    assert result == 0
    assert not process_calls
    assert not empty_calls
    assert repository.count_pending_intraday_alert_batches() == 1


def test_scheduled_manual_poll_collects_news_after_summary_with_canonical_scrapling(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report()], _inspection(1)))
    canonical_scrapling = tmp_path / "scrapling.exe"
    canonical_scrapling.touch()
    monkeypatch.setattr(cli_module, "_resolve_web_view_scrapling_exe", lambda _config: canonical_scrapling)
    captured: dict[str, object] = {}

    def fake_collect(_config, collected_repository, **kwargs):
        captured.update(kwargs)
        assert collected_repository.list_daily_summaries(date(2026, 4, 24))
        return 0

    monkeypatch.setattr(cli_module, "_run_news_intelligence_collect_top_candidates", fake_collect)

    result = cli_module._run_manual_poll(
        config,
        repository,
        limit=50,
        dry_run=False,
        inspect_only=False,
        headless=True,
        send_intraday_alert=False,
        collect_top_candidate_news=True,
        scheduled_run_at=datetime(2026, 4, 24, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone)),
    )

    assert result == 0
    assert captured["business_date"] == date(2026, 4, 24)
    assert captured["candidate_limit"] == 2
    assert captured["top_n"] == 2
    assert captured["scrapling_exe"] == canonical_scrapling


def test_process_intraday_alerts_returns_processed_batch_count(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=True)
    sent_messages: list[str] = []

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_send(_token, _chat_id, message, **_kwargs):
        sent_messages.append(message)
        return "message-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    result = cli_module._run_process_intraday_alerts(
        config,
        repository,
        dry_run=False,
        batch_ids=None,
    )

    assert result == 1
    assert len(sent_messages) == 1


def test_scheduled_intraday_briefing_merges_current_day_pending_batches_once(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    first = _report()
    second = _report(
        title="memory rebound",
        broker_name="Meritz",
        source_id="92000",
        identity_key="identity-2",
        target_price_value=100_000,
    )
    repository.insert_reports([first], queue_intraday_alerts=True)
    repository.insert_reports([second], queue_intraday_alerts=True)
    sent_messages: list[str] = []

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        cli_module,
        "_build_market_briefing_toss_priority_context",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("08:30 must not fetch Toss context")),
    )
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda _token, _chat_id, message, **_kwargs: sent_messages.append(message) or "message-1",
    )

    result = cli_module._run_scheduled_intraday_briefing(
        config,
        repository,
        scheduled_run_at=datetime(2026, 4, 24, 8, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
        dry_run=False,
    )

    assert result == 2
    assert len(sent_messages) == 1
    assert "Meritz(1), NH(1)" in sent_messages[0]
    assert "92,000원 ~ 100,000원" in sent_messages[0]
    assert repository.count_pending_intraday_alert_batches() == 0


def test_scheduled_intraday_briefing_adds_available_toss_context_after_0930(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=True)
    sent_messages: list[str] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})

    def fake_toss_context(*_args, **kwargs):
        captured.update(kwargs)
        return {
            "names_by_symbol": {"005930": "Samsung Electronics", "000660": "SK hynix"},
            "payload": {
                "live_fetch": True,
                "fetched_at": "2026-04-24T09:30:00+09:00",
                "quotes": [{"symbol": "005930", "lastPrice": 72_000, "timestamp": "2026-04-24T09:29:00+09:00"}],
                "investor_trading": {
                    "available": True,
                    "items": [
                        {
                            "symbol": "005930",
                            "updated_at": "2026-04-24T09:28:00+09:00",
                            "foreigner_net_buy_volume": 60,
                            "institution_net_buy_volume": -20,
                        }
                    ],
                },
            },
            "market_context": {
                "live_fetch": True,
                "ranked_at": "2026-04-24T09:30:00+09:00",
                "rankings": [{"symbol": "005930"}, {"symbol": "000660"}],
                "etf_symbols": ["000660"],
                "priority_overlap_symbols": ["005930"],
                "market_prices": [{"symbol": "KOSPI", "lastPrice": "6913.85"}],
                "investor_flow": {
                    "KOSPI": {
                        "updatedAt": "2026-04-24T09:30:00+09:00",
                        "foreigner": {"buyAmount": "100", "sellAmount": "40"},
                        "institution": {"buyAmount": "30", "sellAmount": "50"},
                    }
                },
            },
        }

    monkeypatch.setattr(cli_module, "_build_market_briefing_toss_priority_context", fake_toss_context)
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda _token, _chat_id, message, **_kwargs: sent_messages.append(message) or "message-1",
    )

    result = cli_module._run_scheduled_intraday_briefing(
        config,
        repository,
        scheduled_run_at=datetime(2026, 4, 24, 9, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
        dry_run=False,
    )

    assert result == 1
    assert captured["include_investor_trading"] is True
    assert "우선 확인 · Toss · 기준 09:29" in sent_messages[0]
    assert "- Samsung Electronics | 현재가 72,000원 | 외국인 순매수 60주 · 기관 순매도 20주" in sent_messages[0]
    assert "Toss 거래대금 상위 개별종목 10 · 집계 09:30" in sent_messages[0]
    assert "- Samsung Electronics" in sent_messages[0]
    assert "- SK hynix" in sent_messages[0]
    assert "· 조회 09:29" not in sent_messages[0]
    assert "· 수급 09:28" not in sent_messages[0]
    assert "\n- 당일 시장 수급 잠정\n" in sent_messages[0]
    assert sent_messages[0].index("KOSPI 6913.85") < sent_messages[0].index("우선 확인 · Toss · 기준 09:29")
    assert sent_messages[0].index("우선 확인 · Toss · 기준 09:29") < sent_messages[0].index("- 우선 확인 겹침: Samsung Electronics")
    assert sent_messages[0].index("- 우선 확인 겹침: Samsung Electronics") < sent_messages[0].index("Toss 거래대금 상위 개별종목 10")
    assert sent_messages[0].index("Toss 거래대금 ETF 5") < sent_messages[0].index("장중 신규 리포트")
    assert "Toss 우선확인 현재가" not in sent_messages[0]
    assert "Toss 우선확인 당일 수급" not in sent_messages[0]
    assert "Toss 거래대금 상위 개별종목 10" in sent_messages[0]
    assert "Toss 거래대금 ETF 5" in sent_messages[0]


def test_market_briefing_toss_context_resolves_ranked_stock_names_from_metadata(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="000660",
            stock_name="SK hynix",
            sector_code=None,
            sector_name=None,
            updated_at=datetime(2026, 4, 24, 9, 30, 0),
        )
    )

    class FakeTossProvider:
        configured = True

        def get_quotes(self, **_kwargs) -> dict[str, object]:
            return {"configured": True, "live_fetch": True, "quotes": []}

        def get_market_context(self, **_kwargs) -> dict[str, object]:
            return {"live_fetch": True, "rankings": [{"symbol": "000660"}]}

    context = cli_module._build_market_briefing_toss_priority_context(
        config,
        repository,
        business_date=date(2026, 4, 24),
        candidate_rows=[{"stock_code": "005930", "stock_name": "Samsung Electronics"}],
        toss_quote_provider=FakeTossProvider(),
    )

    assert context["names_by_symbol"] == {"005930": "Samsung Electronics", "000660": "SK hynix"}


def test_scheduled_intraday_briefing_does_not_send_empty_when_prior_day_batch_is_pending(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    prior_day_report = replace(
        _report(),
        business_date=date(2026, 4, 23),
        published_at=datetime(2026, 4, 23, 15, 30, 0),
        collected_at=datetime(2026, 4, 23, 16, 0, 0),
    )
    repository.insert_reports([prior_day_report], queue_intraday_alerts=True)
    empty_calls: list[object] = []
    monkeypatch.setattr(
        cli_module,
        "_send_intraday_empty_notification",
        lambda *_args, **_kwargs: empty_calls.append(_kwargs) or 0,
    )

    result = cli_module._run_scheduled_intraday_briefing(
        config,
        repository,
        scheduled_run_at=datetime(2026, 4, 24, 8, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
        dry_run=False,
    )

    assert result == 0
    assert not empty_calls
    assert repository.count_pending_intraday_alert_batches() == 1


def test_scheduled_intraday_briefing_limits_stock_blocks_without_paging_prompt(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    first = _report()
    second = replace(
        _report(
            title="memory rebound",
            broker_name="Meritz",
            source_id="92000",
            identity_key="identity-2",
            target_price_value=100_000,
        ),
        stock_name="SK hynix",
        stock_code="000660",
    )
    repository.insert_reports([first], queue_intraday_alerts=True)
    repository.insert_reports([second], queue_intraday_alerts=True)
    sent_messages: list[str] = []
    monkeypatch.setattr(cli_module, "_fetch_intraday_quotes_by_stock_code", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cli_module, "_effective_int_setting", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda _token, _chat_id, message, **_kwargs: sent_messages.append(message) or "message-1",
    )

    cli_module._run_scheduled_intraday_briefing(
        config,
        repository,
        scheduled_run_at=datetime(2026, 4, 24, 8, 30, tzinfo=cli_module.ZoneInfo(config.timezone)),
        dry_run=False,
    )

    assert "나머지 1개 종목 있음" in sent_messages[0]
    assert "다음, 전부, 처음" not in sent_messages[0]


def test_manual_poll_rebuilds_summaries_before_intraday_alert_delivery_failure(tmp_path, monkeypatch) -> None:
    config, repository = _config_and_repository(tmp_path, monkeypatch)
    repository.insert_reports([_report()], queue_intraday_alerts=False)
    repository.rebuild_daily_summaries(date(2026, 4, 24))

    second = _report(
        title="memory rebound",
        broker_name="Meritz",
        source_id="92000",
        identity_key="identity-2",
        target_price_value=100_000,
    )
    monkeypatch.setattr(cli_module, "fetch_reports", lambda *_args, **_kwargs: ([_report(), second], _inspection(2)))
    monkeypatch.setattr(
        cli_module,
        "_run_process_intraday_alerts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("send failed")),
    )

    with pytest.raises(RuntimeError, match="send failed"):
        cli_module._run_manual_poll(
            config,
            repository,
            limit=50,
            dry_run=False,
            inspect_only=False,
            headless=True,
            send_intraday_alert=True,
        )

    summaries = repository.list_daily_summaries(date(2026, 4, 24))
    assert len(summaries) == 1
    assert summaries[0].mention_count == 2
    assert "NH" in summaries[0].broker_display
    assert "Meritz" in summaries[0].broker_display
