from datetime import date, datetime
import json

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


def test_scheduled_poll_news_uses_one_top_two_target_list_and_records_run_time(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 6, 2)
    run_at = datetime(2026, 6, 2, 10, 0, tzinfo=cli_module.ZoneInfo(config.timezone))
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli_module,
        "_news_intelligence_top_candidate_targets",
        lambda *_args, **_kwargs: [
            {"rank": 1, "stock_code": "005930", "stock_name": "삼성전자"},
            {"rank": 2, "stock_code": "000660", "stock_name": "SK하이닉스"},
        ],
    )

    def fake_collect(args, **_kwargs):
        captured["date"] = args.date
        captured["stock_code"] = args.stock_code
        print(json.dumps({"saved_observation_count": 2, "saved_evidence_count": 3}, ensure_ascii=False))
        return 0

    monkeypatch.setattr(cli_module, "_run_news_intelligence_briefing_collect", fake_collect)

    result = cli_module._run_news_intelligence_collect_top_candidates(
        config,
        repository,
        business_date=business_date,
        candidate_limit=2,
        top_n=2,
        dry_run=False,
        confirm_collect=True,
        scrapling_exe=None,
        as_json=True,
        scheduled_run_at=run_at,
    )

    assert result == 0
    assert captured == {"date": business_date, "stock_code": ["005930", "000660"]}
    payload = json.loads(capsys.readouterr().out)
    assert payload["targets"] == [
        {"rank": 1, "stock_code": "005930", "stock_name": "삼성전자"},
        {"rank": 2, "stock_code": "000660", "stock_name": "SK하이닉스"},
    ]
    event = repository.list_recent_operation_events(limit=1)[0]
    assert event.component == "poll-news"
    assert "scheduled_run_at=2026-06-02T10:00:00+09:00" in (event.detail or "")
    assert "target_stock_codes=005930,000660" in (event.detail or "")
