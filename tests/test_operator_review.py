from __future__ import annotations

import sqlite3
from datetime import date
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from stock_monitor import cli
from stock_monitor.operator_review_server import (
    DEFAULT_NEWBBY_BASE_URL,
    _ReadOnlyStockMonitorRepository,
    _latest_stored_business_date,
    _news_collection_status,
    _route_operator_review_request,
    build_newbby_chart_url,
    build_operator_review_payload,
    create_operator_review_server,
    render_operator_review_html,
)


def test_operator_review_projects_selected_date_main_snapshot_without_raw_news(monkeypatch):
    business_date = date(2026, 10, 6)
    captured = {}

    def candidate_snapshot(config, repository, *, business_date, limit):
        captured.update(
            business_date=business_date,
            limit=limit,
        )
        return {
            "selection_basis": "stored_candidate_evidence",
            "rows": [
                    {
                        "stock_code": "000660",
                        "stock_name": "SK하이닉스",
                        "selected": True,
                        "observation_priority": "우선 확인",
                        "why_notable": ["리포트 근거"],
                        "missing_information": [],
                        "evidence_layers": {"primary": ["리포트 근거"], "support": [], "gap": []},
                        "report_summary": {"report_count": 2, "target_price_min": None, "target_price_max": None},
                        "market_reference": {"available": True, "close_price": 220000, "change_percent": 1.2},
                        "news_observation_badge": {
                            "available": True,
                            "display_label": "직접 근거 확인",
                            "direct_count": 1,
                            "caution_count": 0,
                            "market_context_count": 0,
                            "observed_at": "2026-10-06T18:00:00",
                            "latest_collection_status": "matched",
                            "collection_run_count": 1,
                            "latest_collection_at": "2026-10-06T18:00:00",
                            "title": "PRIVATE RAW HEADLINE MUST NOT ESCAPE",
                        },
                        "stock_flow_reference": {
                            "available": True,
                            "snapshot_date": "2026-10-06",
                            "foreign_net_buy_amount": 22000000,
                            "foreign_net_buy_volume": 100,
                            "amount_unit": "KRW",
                            "volume_unit": "shares",
                        },
                        "toss_baseline_reference": {"available": False},
                        "event_reaction": {"business_date": "2026-10-07", "raw": "future rows filtered"},
                        "sort_tuple": {"sort_value_signal": 99},
                    },
                    {
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                        "selected": True,
                        "observation_priority": "추가 확인",
                        "why_notable": [],
                        "missing_information": [],
                        "evidence_layers": {"primary": [], "support": [], "gap": []},
                        "report_summary": {"report_count": 0},
                        "market_reference": {"available": False},
                        "news_observation_badge": {"available": False, "latest_collection_status": "not_collected"},
                        "stock_flow_reference": {"available": False},
                        "toss_baseline_reference": {"available": False},
                    },
                    {"stock_code": "000001", "selected": False},
            ],
        }

    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", candidate_snapshot)
    monkeypatch.setattr(
        cli,
        "build_web_view_daily_snapshot",
        lambda *_args, **_kwargs: pytest.fail("operator-review must skip daily opening-context logic"),
    )
    config = SimpleNamespace(timezone="Asia/Seoul", db_path="unused.db")
    repository = SimpleNamespace(list_daily_summaries=lambda selected_date: [object()])

    payload = build_operator_review_payload(config, repository, business_date)

    assert captured == {
        "business_date": business_date,
        "limit": 2,
    }
    assert payload["business_date"] == business_date.isoformat()
    assert payload["selection_basis"] == "stored_candidate_evidence"
    assert [row["stock_code"] for row in payload["candidates"]] == ["000660", "005930"]
    first, second = payload["candidates"]
    assert first["news_evidence"]["status"] == "matched"
    assert first["news_evidence"]["direct_count"] == 1
    assert first["flow_reference"]["provisional"] is True
    assert second["news_evidence"]["status"] == "not_collected"
    assert "missing" in second["news_evidence"]["freshness"]
    assert "PRIVATE RAW HEADLINE MUST NOT ESCAPE" not in str(payload)
    assert "2026-10-07" not in str(payload)
    assert all("score" not in key and "sort" not in key for row in payload["candidates"] for key in row)


def test_missing_saved_main_summaries_return_empty_without_rebuilding(monkeypatch):
    business_date = date(2026, 10, 6)
    repository = SimpleNamespace(list_daily_summaries=lambda selected_date: [])
    config = SimpleNamespace(timezone="Asia/Seoul", db_path="unused.db")

    def unexpected_snapshot(*_args, **_kwargs):
        pytest.fail("read-only operator review must not invoke the Main candidate builder without stored summaries")

    monkeypatch.setattr(cli, "build_web_view_candidate_evidence_snapshot", unexpected_snapshot)

    payload = build_operator_review_payload(config, repository, business_date)

    assert payload["available"] is False
    assert payload["selection_basis"] == "stored_daily_summaries_missing"
    assert payload["candidates"] == []
    assert "재생성하지 않습니다" in payload["empty_state"]


def test_readonly_repository_rejects_writes_and_never_creates_database(tmp_path):
    database_path = tmp_path / "stored.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('stored')")

    repository = _ReadOnlyStockMonitorRepository(database_path)
    with repository.connect() as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "stored"
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("INSERT INTO sample VALUES ('blocked')")

    missing_path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        with _ReadOnlyStockMonitorRepository(missing_path).connect():
            pass
    assert not missing_path.exists()


def test_empty_install_shows_empty_state_without_creating_database(tmp_path):
    database_path = tmp_path / "missing.db"
    config = SimpleNamespace(db_path=database_path, timezone="Asia/Seoul")

    status, content_type, body = _route_operator_review_request("GET", "/", config)

    assert int(status) == 200
    assert content_type.startswith("text/html")
    assert "저장된 기준일이 없습니다" in body.decode("utf-8")
    assert not database_path.exists()


def test_newbby_chart_handoff_encodes_selected_code_and_date():
    url = build_newbby_chart_url("005930", date(2026, 10, 6))
    parsed = urlsplit(url)

    assert parsed.scheme == "http"
    assert parsed.netloc == "127.0.0.1:8734"
    assert parsed.path == "/chart-first.html"
    assert parse_qs(parsed.query) == {"symbol": ["005930"], "asOf": ["2026-10-06"]}
    assert build_newbby_chart_url("not-a-code", date(2026, 10, 6)) is None


def test_operator_review_server_hard_binds_loopback(monkeypatch):
    captured = {}

    class FakeServer:
        def __init__(self, address, handler):
            captured["address"] = address
            captured["handler"] = handler
            self.server_address = address

    from stock_monitor import operator_review_server

    monkeypatch.setattr(operator_review_server, "ThreadingHTTPServer", FakeServer)
    config = SimpleNamespace(db_path="unused.db", timezone="Asia/Seoul", holiday_overrides=())

    server = create_operator_review_server(config, port=8767)

    assert server.server_address == ("127.0.0.1", 8767)
    assert hasattr(captured["handler"], "do_GET")
    assert hasattr(captured["handler"], "do_POST")
    status, _, _ = _route_operator_review_request("POST", "/api/operator-review?date=2026-10-06", config)
    assert int(status) == 405
    status, _, _ = _route_operator_review_request("GET", "/api/operator-review", config)
    assert int(status) == 400
    assert "/api/operator-review" in render_operator_review_html()


def test_operator_review_cli_defaults_to_fixed_loopback_port_without_host_override(monkeypatch):
    args = cli.build_parser().parse_args(["operator-review"])
    assert args.command == "operator-review"
    assert args.port == 8767
    assert not hasattr(args, "host")
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["operator-review", "--host", "0.0.0.0"])

    captured = {}

    class Config:
        def ensure_runtime_dirs(self):
            raise AssertionError("operator-review must not create runtime directories")

    config = Config()
    monkeypatch.setattr(cli.RuntimeConfig, "from_env", classmethod(lambda cls, **_kwargs: config))
    monkeypatch.setattr(
        cli,
        "_run_operator_review",
        lambda passed_config, *, port, newbby_base_url: captured.update(
            config=passed_config,
            port=port,
            newbby_base_url=newbby_base_url,
        ) or 0,
    )

    assert cli.main(["operator-review"]) == 0
    assert captured["config"] is config
    assert captured["port"] == 8767
    assert captured["newbby_base_url"] == DEFAULT_NEWBBY_BASE_URL


def test_chart_handoff_default_is_the_documented_local_ui():
    assert DEFAULT_NEWBBY_BASE_URL == "http://127.0.0.1:8734"


def test_news_collection_states_remain_distinct():
    assert _news_collection_status({"latest_collection_status": "matched"}) == "matched"
    assert _news_collection_status({"latest_collection_status": "no_match", "available": True}) == "collected_no_match"
    assert (
        _news_collection_status({"latest_collection_status": "not_collected", "available": False})
        == "not_collected"
    )


def test_default_panel_date_comes_from_existing_archive_helper(monkeypatch, tmp_path):
    calls = {}

    def archive(_config, _repository, *, limit):
        calls["limit"] = limit
        return {"latest_business_date": "2026-10-06"}

    monkeypatch.setattr(cli, "build_web_view_archive_snapshot", archive)
    config = SimpleNamespace(db_path=tmp_path / "stored.db", timezone="Asia/Seoul")

    assert _latest_stored_business_date(config) == "2026-10-06"
    assert calls == {"limit": 1}


def test_admin_boundary_audit_reports_separate_panel_and_no_html_leaks(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_ops_sync_db_schema_status", lambda _repository: {"current": False, "status": "missing"})
    config = SimpleNamespace(db_path=tmp_path / "unused.db", timezone="Asia/Seoul")

    payload = cli._build_admin_boundary_audit_payload(config, object(), limit=2)
    review = payload["operator_review"]

    assert review["implemented"] is True
    assert review["separate_handler"] is True
    assert review["methods"] == ["GET"]
    assert review["sqlite_uri_mode"] == "ro"
    assert review["route_present_in_admin_html"] is False
    assert review["route_present_in_web_view_html"] is False
    assert review["route_present_in_web_view_handler"] is False
