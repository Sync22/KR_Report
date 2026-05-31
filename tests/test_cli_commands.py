import json
import sqlite3
from argparse import Namespace
from datetime import date, datetime, timedelta

import stock_monitor.cli as cli_module
from stock_monitor.cli import (
    _build_check_command_response,
    _build_help_command_response,
    _build_memo_command_response,
    _build_stock_code_command_response,
    _build_stock_lookup_command_response,
    _build_stock_selection_followup_response,
    _build_mini_pc_preflight_snapshot,
    _run_db_backup,
    _run_db_backup_prune,
    _run_db_cleanup,
    _run_db_migrate,
    _run_db_restore_smoke,
    _run_db_vacuum,
    _run_inspect_page,
    _run_db_verify,
    _run_observation_feature_audit,
    _run_observation_feature_comparison,
    _run_observation_hidden_holdout_validation,
    _run_observation_hidden_holdout_sweep,
    _run_observation_hidden_score_prototype,
    _run_observation_reaction_distribution,
    _run_observation_summary_audit,
    _run_observation_summary_preview,
    _run_observation_weight_draft,
    _run_rotation_mapping_audit,
    _run_krx_backfill_missing,
    _run_krx_baseline_analysis,
    _run_category_catalog,
    _run_krx_mentioned_flow_latest_anchor_backfill,
    _run_scheduled_krx_mentioned_flow_backfill,
    _run_naver_fixture_validate,
    _run_market_briefing,
    _run_web_view_value_qa,
    _collect_market_briefing_message_issues,
    _collect_web_view_value_qa_issues,
    _resolve_web_view_value_qa_dates,
    _fill_daily_summary_quote_metadata_fallbacks,
    _prepare_repository_for_command,
    _uses_read_only_schema_current_check,
)
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.fetch.naver_stock_quote import StockQuoteSnapshot
from stock_monitor.notify.control import PendingStockSelectionCandidate, TelegramControlState
from stock_monitor.fetch.naver_stock_search import StockCodeLookupEntry
from stock_monitor.models import (
    AppSetting,
    CategoryCatalogItem,
    DailyStockSummary,
    DeliveryLog,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    Opinion,
    OperationEvent,
    Report,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
    StockMetadata,
    WorkerState,
    EtfDailySnapshot,
    InvestorNetBuyTopDaily,
    KrxStockMetadataSnapshot,
)


class _KrxReminderAllowedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 8, 16, 45, 0, tzinfo=tz)


class _KrxReminderLateDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 8, 16, 51, 0, tzinfo=tz)


class _KrxReminderHolidayDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 1, 16, 45, 0, tzinfo=tz)


class _KrxDailyBackfillAllowedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 12, 8, 10, 0, tzinfo=tz)


class _KrxDailyBackfillHolidayDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 25, 8, 10, 0, tzinfo=tz)


class _KrxBaselineFridayLateDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 29, 22, 0, 0, tzinfo=tz)


class _KrxMentionedFlowAllowedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 12, 16, 0, 0, tzinfo=tz)


class _MarketBriefingAllowedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 12, 16, 10, 0, tzinfo=tz)


class _MarketBriefingFlowBackfillWindowDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 12, 16, 0, 0, tzinfo=tz)


def _upsert_test_krx_stock_metadata(
    repository: StockMonitorRepository,
    business_date: date,
    stock_codes: list[str],
) -> None:
    stock_names = {
        "000660": "SK하이닉스",
        "005930": "삼성전자",
    }
    standard_codes = {
        "000660": "KR7000660001",
        "005930": "KR7005930003",
    }
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=business_date,
                standard_code=standard_codes[stock_code],
                stock_code=stock_code,
                stock_name=stock_names[stock_code],
                market="KOSPI",
                fetched_at=datetime(
                    business_date.year,
                    business_date.month,
                    business_date.day,
                    16,
                    0,
                    0,
                ),
            )
            for stock_code in stock_codes
        ]
    )


class _KrxMentionedFlowTooEarlyDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 12, 14, 0, 0, tzinfo=tz)


def test_db_migrate_dry_run_prints_schema_status(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")

    exit_code = _run_db_migrate(repository, dry_run=True)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would apply database schema migrations." in output
    assert "Current schema version: 0" in output
    assert "Target schema version: 5" in output
    assert "Pending migration versions: (none)" in output
    assert not repository.db_path.exists()


def test_db_verify_prints_integrity_and_table_counts(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_db_verify(repository, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Database verification" in output
    assert "- integrity_check: ok" in output
    assert "- schema: 5/5" in output
    assert "- foreign key violations: 0" in output
    assert "- orphan intraday batch reports: 0" in output
    assert "- partial KRX daily snapshot dates: 0" in output
    assert "- investor-flow quality issues: 0" in output
    assert "- category snapshot coverage:" in output
    assert "reports:" in output


def test_prepare_repository_for_read_only_command_skips_initialize_when_schema_current(tmp_path) -> None:
    db_path = tmp_path / "stock_monitor.db"
    StockMonitorRepository(db_path).initialize()

    class InitializeGuardRepository(StockMonitorRepository):
        def initialize(self) -> None:
            raise AssertionError("read-only command should not initialize an existing current schema")

    repository = InitializeGuardRepository(db_path)
    _prepare_repository_for_command(repository, Namespace(command="operator-status"))


def test_prepare_repository_for_read_only_command_initializes_missing_db(tmp_path) -> None:
    class CountingInitializeRepository(StockMonitorRepository):
        def __init__(self, db_path):
            super().__init__(db_path)
            self.initialize_count = 0

        def initialize(self) -> None:
            self.initialize_count += 1
            super().initialize()

    repository = CountingInitializeRepository(tmp_path / "stock_monitor.db")
    _prepare_repository_for_command(repository, Namespace(command="operator-status"))

    assert repository.initialize_count == 1
    assert repository.db_path.exists()


def test_prepare_repository_for_read_only_command_rejects_stale_schema(tmp_path) -> None:
    db_path = tmp_path / "stock_monitor.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA user_version = 4")

    repository = StockMonitorRepository(db_path)

    try:
        _prepare_repository_for_command(repository, Namespace(command="operator-status"))
    except RuntimeError as exc:
        assert "db-migrate" in str(exc)
    else:
        raise AssertionError("stale schema should be rejected before read-only command")


def test_schema_current_check_only_applies_to_read_only_variants() -> None:
    assert _uses_read_only_schema_current_check(Namespace(command="operator-status"))
    assert _uses_read_only_schema_current_check(
        Namespace(command="scheduled-krx-daily-backfill", dry_run=True)
    )
    assert not _uses_read_only_schema_current_check(
        Namespace(command="scheduled-krx-daily-backfill", dry_run=False)
    )
    assert _uses_read_only_schema_current_check(Namespace(command="access-code", access_code_action="status"))
    assert not _uses_read_only_schema_current_check(Namespace(command="access-code", access_code_action="set"))


def test_observation_cli_parsers_accept_read_only_analysis_commands() -> None:
    parser = cli_module.build_parser()

    audit_args = parser.parse_args(
        [
            "observation-feature-audit",
            "--from-date",
            "2026-05-01",
            "--to-date",
            "2026-05-12",
            "--json",
        ]
    )
    summary_audit_args = parser.parse_args(
        [
            "observation-summary-audit",
            "--limit",
            "7",
            "--to-date",
            "2026-05-12",
            "--mention-threshold",
            "1",
            "--json",
        ]
    )
    summary_audit_alias_args = parser.parse_args(
        [
            "observation-summary-audit",
            "--recent-report-dates",
            "8",
            "--json",
        ]
    )
    summary_preview_args = parser.parse_args(
        [
            "observation-summary-preview",
            "--date",
            "2026-05-12",
            "--limit",
            "3",
            "--json",
        ]
    )
    candidate_readiness_args = parser.parse_args(
        [
            "candidate-evidence-readiness",
            "--recent-business-days",
            "4",
            "--limit",
            "3",
            "--json",
        ]
    )
    candidate_readiness_alias_args = parser.parse_args(
        [
            "candidate-evidence-readiness",
            "--recent-report-dates",
            "5",
            "--stock-limit",
            "20",
            "--json",
        ]
    )
    distribution_default_args = parser.parse_args(
        [
            "observation-reaction-distribution",
            "--json",
        ]
    )
    hidden_args = parser.parse_args(
        [
            "observation-hidden-prototype",
            "--train-from-date",
            "2026-01-02",
            "--train-to-date",
            "2026-05-07",
            "--from-date",
            "2026-05-08",
            "--to-date",
            "2026-05-12",
            "--horizon-days",
            "20",
            "--exclude-feature",
            "target_progress_caution",
            "--json",
        ]
    )
    holdout_args = parser.parse_args(
        [
            "observation-hidden-holdout",
            "--train-from-date",
            "2026-01-02",
            "--train-to-date",
            "2026-05-07",
            "--holdout-from-date",
            "2026-05-08",
            "--holdout-to-date",
            "2026-05-12",
            "--horizon-days",
            "20",
            "--exclude-feature",
            "target_progress_caution",
            "--json",
        ]
    )
    sweep_args = parser.parse_args(
        [
            "observation-hidden-holdout-sweep",
            "--train-from-date",
            "2026-01-02",
            "--train-to-date",
            "2026-04-30",
            "--holdout-from-date",
            "2026-05-01",
            "--holdout-to-date",
            "2026-05-12",
            "--horizon-days",
            "5",
            "--horizon-days",
            "20",
            "--window-days",
            "5",
            "--exclude-feature",
            "target_progress_caution",
            "--json",
        ]
    )

    assert audit_args.command == "observation-feature-audit"
    assert audit_args.from_date == date(2026, 5, 1)
    assert audit_args.to_date == date(2026, 5, 12)
    assert audit_args.json is True
    assert summary_audit_args.command == "observation-summary-audit"
    assert summary_audit_args.limit == 7
    assert summary_audit_args.to_date == date(2026, 5, 12)
    assert summary_audit_args.mention_threshold == 1
    assert summary_audit_args.json is True
    assert summary_audit_alias_args.command == "observation-summary-audit"
    assert summary_audit_alias_args.limit == 8
    assert summary_audit_alias_args.json is True
    assert summary_preview_args.command == "observation-summary-preview"
    assert summary_preview_args.date == date(2026, 5, 12)
    assert summary_preview_args.limit == 3
    assert summary_preview_args.json is True
    assert candidate_readiness_args.command == "candidate-evidence-readiness"
    assert candidate_readiness_args.recent_business_days == 4
    assert candidate_readiness_args.limit == 3
    assert candidate_readiness_args.json is True
    assert candidate_readiness_alias_args.command == "candidate-evidence-readiness"
    assert candidate_readiness_alias_args.recent_business_days == 5
    assert candidate_readiness_alias_args.limit == 20
    assert candidate_readiness_alias_args.json is True
    assert distribution_default_args.command == "observation-reaction-distribution"
    assert distribution_default_args.from_date is None
    assert distribution_default_args.to_date is None
    assert distribution_default_args.json is True
    assert hidden_args.command == "observation-hidden-prototype"
    assert hidden_args.train_from_date == date(2026, 1, 2)
    assert hidden_args.train_to_date == date(2026, 5, 7)
    assert hidden_args.from_date == date(2026, 5, 8)
    assert hidden_args.to_date == date(2026, 5, 12)
    assert hidden_args.horizon_days == 20
    assert hidden_args.exclude_feature == ["target_progress_caution"]
    assert hidden_args.json is True
    assert holdout_args.command == "observation-hidden-holdout"
    assert holdout_args.train_from_date == date(2026, 1, 2)
    assert holdout_args.train_to_date == date(2026, 5, 7)
    assert holdout_args.holdout_from_date == date(2026, 5, 8)
    assert holdout_args.holdout_to_date == date(2026, 5, 12)
    assert holdout_args.horizon_days == 20
    assert holdout_args.exclude_feature == ["target_progress_caution"]
    assert holdout_args.json is True
    assert sweep_args.command == "observation-hidden-holdout-sweep"
    assert sweep_args.horizon_days == [5, 20]
    assert sweep_args.window_days == 5
    assert sweep_args.exclude_feature == ["target_progress_caution"]


def test_inspect_page_parser_accepts_drift_fixture_output_path(tmp_path) -> None:
    parser = cli_module.build_parser()
    fixture_path = tmp_path / "naver_live_fixture.json"

    args = parser.parse_args(["inspect-page", "--limit", "5", "--save-fixture", str(fixture_path)])

    assert args.command == "inspect-page"
    assert args.limit == 5
    assert args.save_fixture == fixture_path


def test_inspect_page_parser_accepts_required_parsed_fixture_check(tmp_path) -> None:
    parser = cli_module.build_parser()
    fixture_path = tmp_path / "naver_live_fixture.json"

    args = parser.parse_args(
        ["inspect-page", "--limit", "5", "--save-fixture", str(fixture_path), "--require-parsed-reports"]
    )

    assert args.command == "inspect-page"
    assert args.save_fixture == fixture_path
    assert args.require_parsed_reports is True


def test_inspect_page_required_parsed_fixture_check_fails_on_empty_snapshot(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    fixture_path = tmp_path / "naver_empty_fixture.json"

    class _EmptyInspection:
        url = "https://stock.naver.com/research/company"
        title = "Naver Research"
        tab_clicked = True
        network_urls = ()
        api_pages_fetched = 1
        api_items = ()
        candidate_rows = ()

    monkeypatch.setattr(cli_module, "inspect_company_page", lambda *args, **kwargs: _EmptyInspection())

    try:
        _run_inspect_page(
            config,
            5,
            headless=True,
            save_fixture=fixture_path,
            require_parsed_reports=True,
        )
    except RuntimeError as exc:
        assert "Saved parser drift fixture parsed 0 reports" in str(exc)
    else:
        raise AssertionError("empty parser drift fixture should fail when parsed reports are required")
    assert fixture_path.exists()


def test_inspect_page_required_parsed_fixture_check_requires_saved_fixture(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    class _EmptyInspection:
        url = "https://stock.naver.com/research/company"
        title = "Naver Research"
        tab_clicked = True
        network_urls = ()
        api_pages_fetched = 1
        api_items = ()
        candidate_rows = ()

    monkeypatch.setattr(cli_module, "inspect_company_page", lambda *args, **kwargs: _EmptyInspection())

    try:
        _run_inspect_page(config, 5, headless=True, require_parsed_reports=True)
    except ValueError as exc:
        assert "--require-parsed-reports requires --save-fixture" in str(exc)
    else:
        raise AssertionError("--require-parsed-reports without --save-fixture should fail")


def test_naver_fixture_validate_parser_accepts_path_and_json(tmp_path) -> None:
    parser = cli_module.build_parser()
    fixture_path = tmp_path / "naver_live_fixture.json"

    args = parser.parse_args(["naver-fixture-validate", str(fixture_path), "--json"])

    assert args.command == "naver-fixture-validate"
    assert args.fixture_path == fixture_path
    assert args.json is True


def test_naver_fixture_validate_reports_parsed_count(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "naver_live_fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "collected_at": "2026-04-25T08:00:00+09:00",
                "timezone": "Asia/Seoul",
                "api_items": [
                    {
                        "itemName": "삼성전자",
                        "itemCode": "005930",
                        "researchId": "91999",
                        "title": "업황 회복 가시화",
                        "brokerName": "NH투자증권",
                        "writeDate": "2026-04-24",
                        "opinion": "Buy",
                        "goalPrice": "92000",
                    }
                ],
                "candidate_rows": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = _run_naver_fixture_validate(fixture_path, as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "naver-fixture-validate"
    assert payload["parsed_report_count"] == 1
    assert payload["source_ids"] == ["91999"]


def test_naver_fixture_validate_fails_empty_fixture(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "naver_empty_fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "collected_at": "2026-04-25T08:00:00+09:00",
                "timezone": "Asia/Seoul",
                "api_items": [],
                "candidate_rows": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = _run_naver_fixture_validate(fixture_path, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "parsed reports: 0" in output


def test_web_view_value_qa_parser_accepts_dates_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "web-view-value-qa",
            "--date",
            "2026-05-11",
            "--date",
            "2026-05-08",
            "--stock-limit",
            "3",
            "--json",
        ]
    )

    assert args.command == "web-view-value-qa"
    assert args.dates == [date(2026, 5, 11), date(2026, 5, 8)]
    assert args.stock_limit == 3
    assert args.json is True


def test_web_view_value_qa_parser_accepts_recent_business_days_without_dates() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "web-view-value-qa",
            "--recent-business-days",
            "4",
            "--stock-limit",
            "20",
        ]
    )

    assert args.command == "web-view-value-qa"
    assert args.dates is None
    assert args.recent_business_days == 4
    assert args.stock_limit == 20


def test_krx_daily_backfill_parsers_accept_json_dry_run() -> None:
    parser = cli_module.build_parser()

    backfill_args = parser.parse_args(
        [
            "krx-backfill-missing",
            "daily",
            "--to-date",
            "2026-05-15",
            "--max-dates",
            "1",
            "--dry-run",
            "--json",
        ]
    )
    scheduled_args = parser.parse_args(["scheduled-krx-daily-backfill", "--dry-run", "--json"])

    assert backfill_args.command == "krx-backfill-missing"
    assert backfill_args.endpoint == "daily"
    assert backfill_args.to_date == date(2026, 5, 15)
    assert backfill_args.max_dates == 1
    assert backfill_args.dry_run is True
    assert backfill_args.json is True
    assert scheduled_args.command == "scheduled-krx-daily-backfill"
    assert scheduled_args.dry_run is True
    assert scheduled_args.json is True


def test_krx_openapi_availability_probe_parser_accepts_latest_json_and_dry_run() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "krx-openapi-availability-probe",
            "--date",
            "latest",
            "--endpoint",
            "daily",
            "--dry-run",
            "--json",
        ]
    )

    assert args.command == "krx-openapi-availability-probe"
    assert args.date is None
    assert args.endpoint == "daily"
    assert args.dry_run is True
    assert args.json is True


def test_krx_openapi_probe_summary_parser_accepts_date_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "krx-openapi-probe-summary",
            "--date",
            "2026-05-20",
            "--json",
        ]
    )

    assert args.command == "krx-openapi-probe-summary"
    assert args.date == date(2026, 5, 20)
    assert args.json is True


def test_ops_readiness_parser_accepts_recent_days_stock_limit_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "ops-readiness",
            "--recent-business-days",
            "3",
            "--stock-limit",
            "10",
            "--json",
        ]
    )

    assert args.command == "ops-readiness"
    assert args.recent_business_days == 3
    assert args.stock_limit == 10
    assert args.json is True


def test_web_view_browser_smoke_parser_accepts_date_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "web-view-browser-smoke",
            "--date",
            "2026-05-11",
            "--stock-limit",
            "12",
            "--respect-access-code",
            "--json",
        ]
    )

    assert args.command == "web-view-browser-smoke"
    assert args.date == date(2026, 5, 11)
    assert args.stock_limit == 12
    assert args.respect_access_code is True
    assert args.json is True


def test_web_view_browser_smoke_parser_accepts_latest_date_alias() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["web-view-browser-smoke", "--date", "latest", "--json"])

    assert args.command == "web-view-browser-smoke"
    assert args.date is None
    assert args.json is True


def test_web_view_browser_api_smoke_checks_intraday_market_top_route(monkeypatch) -> None:
    calls: list[str] = []

    def fake_request(url: str, *, method: str = "GET", data=None):  # noqa: ARG001
        path = url.split("http://127.0.0.1:8780", 1)[1]
        calls.append(f"{method} {path}")
        if path == "/api/daily/2026-05-20" and method == "POST":
            return 405, b"", "text/plain"
        if path == "/api/daily/2026-05-20":
            return 200, json.dumps({"business_date": "2026-05-20", "stocks": []}).encode("utf-8"), "application/json"
        if path == "/api/daily/2026-05-20?intraday_market_top=1&market_top_limit=100&market_top_page_size=20":
            return (
                200,
                json.dumps(
                    {
                        "business_date": "2026-05-20",
                        "market_commentary": {
                            "live_fetch": True,
                            "intraday_market_top_reference": {
                                "live_fetch": True,
                                "writes_snapshot_tables": False,
                            },
                        },
                    }
                ).encode("utf-8"),
                "application/json",
            )
        if path == "/api/candidate-evidence?date=2026-05-20&limit=5":
            return 200, b'{"rows":[]}', "application/json"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        return 404, b"not found", "text/plain"

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)
    issues: list[dict[str, object]] = []
    api_checks: list[dict[str, object]] = []

    cli_module._collect_web_view_browser_api_smoke_issues(
        "http://127.0.0.1:8780",
        business_date=date(2026, 5, 20),
        stock_limit=5,
        issues=issues,
        api_checks=api_checks,
    )

    assert issues == []
    assert "GET /api/daily/2026-05-20?intraday_market_top=1&market_top_limit=100&market_top_page_size=20" in calls
    assert {
        "path": "/api/daily/{date}?intraday_market_top=1",
        "method": "GET",
        "status": 200,
    } in api_checks


def test_web_view_browser_api_smoke_flags_candidate_json_operator_keys(monkeypatch) -> None:
    def fake_request(url: str, *, method: str = "GET", data=None):  # noqa: ARG001
        path = url.split("http://127.0.0.1:8780", 1)[1]
        if path == "/api/daily/2026-05-20" and method == "POST":
            return 405, b"", "text/plain"
        if path == "/api/daily/2026-05-20":
            return 200, json.dumps({"business_date": "2026-05-20", "stocks": []}).encode("utf-8"), "application/json"
        if path == "/api/daily/2026-05-20?intraday_market_top=1&market_top_limit=100&market_top_page_size=20":
            return (
                200,
                json.dumps(
                    {
                        "business_date": "2026-05-20",
                        "market_commentary": {
                            "intraday_market_top_reference": {
                                "live_fetch": True,
                                "writes_snapshot_tables": False,
                            },
                        },
                    }
                ).encode("utf-8"),
                "application/json",
            )
        if path == "/api/candidate-evidence?date=2026-05-20&limit=5":
            return (
                200,
                b'{"rows":[{"report_intensity":{"five_business_day_broker_count":2},'
                b'"target_price_revision":{"previous_broker_count":1}}]}',
                "application/json",
            )
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        return 404, b"not found", "text/plain"

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)
    issues: list[dict[str, object]] = []

    cli_module._collect_web_view_browser_api_smoke_issues(
        "http://127.0.0.1:8780",
        business_date=date(2026, 5, 20),
        stock_limit=5,
        issues=issues,
        api_checks=[],
    )

    assert [issue["code"] for issue in issues] == ["candidate_json_exposes_operator_keys"]
    assert "five_business_day_broker_count" in issues[0]["message"]
    assert "previous_broker_count" in issues[0]["message"]


def test_market_commentary_practice_parser_accepts_intraday_market_top_options() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "market-commentary-practice",
            "--date",
            "2026-05-20",
            "--intraday-market-top",
            "--market-top-limit",
            "80",
            "--market-top-page-size",
            "20",
            "--market-top-delay-seconds",
            "0.25",
            "--json",
        ]
    )

    assert args.command == "market-commentary-practice"
    assert args.date == date(2026, 5, 20)
    assert args.intraday_market_top is True
    assert args.market_top_limit == 80
    assert args.market_top_page_size == 20
    assert args.market_top_delay_seconds == 0.25
    assert args.json is True


def test_intraday_market_top_reference_clamps_call_burden(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    business_date = date(2026, 5, 20)
    summaries = [
        DailyStockSummary(
            business_date=business_date,
            stock_code="000001",
            stock_name="부담가드",
            mention_count=1,
            broker_display="테스트증권",
            target_price_min=None,
            target_price_max=None,
            dominant_opinion="N/A",
            generated_at=datetime(2026, 5, 20, 9, 0, 0),
        )
    ]
    calls: list[tuple[str, int, int]] = []

    def fake_market_top(market: str, *, page: int, page_size: int, **_kwargs):
        calls.append((market, page, page_size))
        return [
            cli_module.NaverMarketTopStock(
                market=market,
                sort_type="PRICE_TOP",
                stock_code=f"{page:03d}{index:03d}",
                stock_name=f"비언급{index}",
                stock_end_type="stock",
                trade_amount=1_000_000_000,
            )
            for index in range(page_size)
        ]

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)

    reference = cli_module._build_intraday_market_top_reference(
        config,
        summaries,
        limit=1_000,
        page_size=200,
        delay_seconds=0,
    )

    assert reference["limit"] == 100
    assert reference["page_size"] == 20
    assert 0 < len(calls) <= 10
    assert all(page_size == 20 for _market, _page, page_size in calls)


def test_external_web_view_smoke_parser_accepts_url_date_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "external-web-view-smoke",
            "--url",
            "https://stock.example.test",
            "--date",
            "2026-05-15",
            "--record-success",
            "--json",
        ]
    )

    assert args.command == "external-web-view-smoke"
    assert args.url == "https://stock.example.test"
    assert args.date == date(2026, 5, 15)
    assert args.allow_http is False
    assert args.record_success is True
    assert args.json is True


def test_external_web_view_sharing_plan_parser_accepts_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["external-web-view-sharing-plan", "--json"])

    assert args.command == "external-web-view-sharing-plan"
    assert args.json is True
    assert _uses_read_only_schema_current_check(args) is True


def test_web_view_startup_fallback_check_parser_accepts_record_success_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["web-view-startup-fallback-check", "--record-success", "--json"])

    assert args.command == "web-view-startup-fallback-check"
    assert args.record_success is True
    assert args.json is True


def test_external_web_view_sharing_plan_payload_is_read_only(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    payload = cli_module._build_external_web_view_sharing_plan_payload(repository)

    assert payload["surface"] == "external-web-view-sharing-plan"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is False
    assert payload["writes_database"] is False
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["candidate_surface"] == "web-view"
    assert payload["forbidden_surface"] == "admin-gui"
    assert payload["local_tunnel_target"] == "http://127.0.0.1:8780"
    assert payload["provider_setup_done"] is False
    assert payload["provider_smoke"]["ready"] is False
    assert [step["step"] for step in payload["cloudflare_connection_sequence"]] == [
        "confirm_access_code",
        "run_local_external_readiness",
        "start_local_web_view",
        "configure_cloudflare_hostname",
        "confirm_forbidden_routes_absent",
        "enable_provider_access_control",
        "run_provider_wrapper",
        "share_after_success",
    ]
    assert any("Cloudflare Access" in control for control in payload["required_provider_controls"])
    assert any("run_web_view.ps1" in command for command in payload["next_commands"])
    assert any("verify_cloudflare_web_view_tunnel.ps1" in command for command in payload["next_commands"])
    assert "secrets" in payload["note"]


def test_web_view_browser_smoke_json_reports_read_only_contract(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    captured = {}

    def fake_probe(
        config_arg,
        repository_arg,
        *,
        business_date,
        stock_limit,
        respect_access_code,
    ):
        captured["config"] = config_arg
        captured["repository"] = repository_arg
        captured["business_date"] = business_date
        captured["stock_limit"] = stock_limit
        captured["respect_access_code"] = respect_access_code
        return {
            "surface": "web-view-browser-smoke",
            "read_only": True,
            "sends_telegram": False,
            "registers_scheduler": False,
            "host": "127.0.0.1",
            "business_date": business_date.isoformat(),
            "stock_limit": stock_limit,
            "access_code_mode": "temporary_disabled_for_local_smoke",
            "issue_count": 0,
            "issues": [],
            "viewports": [
                {
                    "name": "mobile",
                    "width": 390,
                    "height": 844,
                    "tab_count": 4,
                    "search_input": True,
                    "candidate_panel": True,
                    "watch_panel_clickable": True,
                    "horizontal_overflow_px": 0,
                }
            ],
            "api_checks": [
                {"path": "/api/daily/2026-05-11", "method": "POST", "status": 405},
                {"path": "/api/status", "method": "GET", "status": 404},
            ],
        }

    monkeypatch.setattr(cli_module, "_probe_web_view_browser_smoke", fake_probe)

    exit_code = cli_module._run_web_view_browser_smoke(
        config,
        repository,
        business_date=date(2026, 5, 11),
        stock_limit=12,
        respect_access_code=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "web-view-browser-smoke"
    assert payload["read_only"] is True
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["host"] == "127.0.0.1"
    assert payload["issue_count"] == 0
    assert captured["business_date"] == date(2026, 5, 11)
    assert captured["stock_limit"] == 12
    assert captured["respect_access_code"] is False


def test_external_web_view_smoke_accepts_access_gate_and_blocks_admin(monkeypatch) -> None:
    calls = []

    def fake_request(url, *, method="GET", data=None):
        calls.append((url, method, data))
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/status":
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test/",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["surface"] == "external-web-view-smoke"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is True
    assert payload["writes_database"] is False
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["base_url"] == "https://stock.example.test"
    assert payload["issue_count"] == 0
    assert payload["public_json_routes_checked"] == [
        "/api/archive?limit=1",
        "/api/daily/2026-05-15",
        "/api/candidate-evidence?date=2026-05-15&limit=5",
        "/api/flow-trend?date=2026-05-15&limit=5",
        "/api/etf-trend?date=2026-05-15&limit=5",
    ]
    assert [call[1] for call in calls] == [
        "GET",
        "GET",
        "GET",
        "GET",
        "GET",
        "GET",
        "GET",
        "POST",
        "GET",
        "POST",
        "POST",
        "POST",
        "POST",
    ]


def test_external_web_view_smoke_accepts_cloudflare_access_html_gate(monkeypatch) -> None:
    cloudflare_access_body = (
        b"<html><title>Cloudflare Access</title>"
        b"<form action=\"/cdn-cgi/access/login/example\"></form></html>"
    )

    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path in {
            "/health",
            "/",
            "/api/archive?limit=1",
            "/api/daily/2026-05-15",
            "/api/candidate-evidence?date=2026-05-15&limit=5",
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
            "/api/status",
        }:
            return 200, cloudflare_access_body, "text/html; charset=utf-8"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 200, cloudflare_access_body, "text/html; charset=utf-8"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test/",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 0


def test_external_web_view_smoke_rejects_admin_page_even_with_cloudflare_access_text(monkeypatch) -> None:
    admin_body = (
        b"<html><title>Stock Monitor Admin</title>"
        b"<p>Cloudflare Access is configured</p>"
        b"<button data-api=\"/api/scheduler/run-now\"></button></html>"
    )

    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, admin_body, "text/html; charset=utf-8"
        if path in {
            "/api/archive?limit=1",
            "/api/daily/2026-05-15",
            "/api/candidate-evidence?date=2026-05-15&limit=5",
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        if path == "/api/status":
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test/",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "root_looks_like_admin_gui"


def test_external_web_view_smoke_records_success_when_requested(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/api/archive?limit=1",
            "/api/daily/2026-05-15",
            "/api/candidate-evidence?date=2026-05-15&limit=5",
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
            "/api/status",
        }:
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    exit_code = cli_module._run_external_web_view_smoke(
        config,
        repository,
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
        record_success=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["record_success_requested"] is True
    assert payload["recorded_success"] is True
    assert payload["read_only"] is False
    assert payload["writes_database"] is True
    events = repository.list_recent_operation_events(limit=1)
    assert len(events) == 1
    assert events[0].component == "external-web-view"
    assert events[0].event_type == "provider-smoke"
    assert events[0].status == "success"
    assert events[0].business_date == date(2026, 5, 15)
    assert "url_origin=https://stock.example.test" in (events[0].detail or "")


def test_external_web_view_smoke_record_success_rejects_local_http(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_request(url, *, method="GET", data=None):
        path = url.split("127.0.0.1:8780", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b"{}", "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    exit_code = cli_module._run_external_web_view_smoke(
        config,
        repository,
        base_url="http://127.0.0.1:8780",
        business_date=date(2026, 5, 15),
        allow_http=True,
        record_success=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["record_success_requested"] is True
    assert payload["recorded_success"] is False
    assert payload["read_only"] is True
    assert payload["writes_database"] is False
    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "record_success_requires_https_provider_url"
    assert repository.list_recent_operation_events(limit=1) == []


def test_external_web_view_smoke_record_success_rejects_url_path_or_query(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/shared?code=secret/health":
            return 200, b"ok", "text/plain"
        if path == "/shared?code=secret/":
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/shared?code=secret/api/archive?limit=1",
            "/shared?code=secret/api/daily/2026-05-15",
            "/shared?code=secret/api/candidate-evidence?date=2026-05-15&limit=5",
            "/shared?code=secret/api/flow-trend?date=2026-05-15&limit=5",
            "/shared?code=secret/api/etf-trend?date=2026-05-15&limit=5",
            "/shared?code=secret/api/status",
        }:
            return 401, b"<html>login</html>", "text/html"
        if path in {
            "/shared?code=secret/api/scheduler/run-now",
            "/shared?code=secret/api/scheduler/set-enabled",
            "/shared?code=secret/api/operator/pause",
            "/shared?code=secret/api/settings/set",
        } and method == "POST":
            return 401, b"<html>login</html>", "text/html"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    exit_code = cli_module._run_external_web_view_smoke(
        config,
        repository,
        base_url="https://stock.example.test/shared?code=secret",
        business_date=date(2026, 5, 15),
        allow_http=False,
        record_success=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["record_success_requested"] is True
    assert payload["recorded_success"] is False
    assert payload["read_only"] is True
    assert payload["writes_database"] is False
    assert payload["issues"][0]["code"] == "record_success_requires_provider_origin"
    assert repository.list_recent_operation_events(limit=1) == []


def test_external_web_view_smoke_flags_public_admin_status(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b"{}", "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 200, b"{}", "application/json"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "admin_status_exposed"


def test_external_web_view_smoke_flags_admin_root_and_control_posts(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>Stock Monitor Admin /api/scheduler/run-now</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 404, b"not found", "text/plain"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 404, b"not found", "text/plain"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 400, b"bad request", "application/json"
        if path == "/api/status":
            return 200, b"{}", "application/json"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 400, b"bad request", "application/json"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    issue_codes = [issue["code"] for issue in payload["issues"]]
    assert "root_looks_like_admin_gui" in issue_codes
    assert "admin_status_exposed" in issue_codes
    assert "write_method_not_blocked" in issue_codes
    assert issue_codes.count("admin_control_route_exposed") == 4


def test_external_web_view_smoke_flags_operator_keys_in_daily_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15","scheduler_tasks":[]}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "daily_json_exposes_operator_keys"
    assert "scheduler_tasks" in payload["issues"][0]["message"]


def test_external_web_view_smoke_flags_operator_keys_in_archive_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b'{"dates":[{"business_date":"2026-05-15","safe_settings":{}}]}', "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15"}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "archive_json_exposes_operator_keys"
    assert "safe_settings" in payload["issues"][0]["message"]


def test_external_web_view_smoke_flags_operator_keys_in_candidate_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15"}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, (
                b'{"rows":[{"internal_candidate_signals":["debug"],"_sort_signal":1,'
                b'"report_intensity":{"five_business_day_broker_count":2},'
                b'"target_price_revision":{"previous_broker_count":1}}]}'
            ), "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "candidate_json_exposes_operator_keys"
    assert "internal_candidate_signals" in payload["issues"][0]["message"]
    assert "_sort_signal" in payload["issues"][0]["message"]
    assert "five_business_day_broker_count" in payload["issues"][0]["message"]
    assert "previous_broker_count" in payload["issues"][0]["message"]


def test_external_web_view_smoke_flags_operator_keys_in_stock_detail_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15","stocks":[{"stock_code":"005930"}]}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15/stocks/005930":
            return 200, b'{"stock_code":"005930","operation_profile":"mini-pc"}', "application/json"
        if path in {
            "/api/flow-trend?date=2026-05-15&limit=5",
            "/api/etf-trend?date=2026-05-15&limit=5",
        }:
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "stock_detail_json_exposes_operator_keys"
    assert "operation_profile" in payload["issues"][0]["message"]
    assert "/api/daily/2026-05-15/stocks/005930" in payload["public_json_routes_checked"]


def test_external_web_view_smoke_flags_operator_keys_in_flow_trend_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15"}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/flow-trend?date=2026-05-15&limit=5":
            return 200, b'{"safe_settings":{}}', "application/json"
        if path == "/api/etf-trend?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "flow_trend_json_exposes_operator_keys"
    assert "safe_settings" in payload["issues"][0]["message"]


def test_external_web_view_smoke_flags_operator_keys_in_etf_trend_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return 200, b'{"business_date":"2026-05-15"}', "application/json"
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/flow-trend?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/etf-trend?date=2026-05-15&limit=5":
            return 200, b'{"scheduler_tasks":[]}', "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "etf_trend_json_exposes_operator_keys"
    assert "scheduler_tasks" in payload["issues"][0]["message"]


def test_external_web_view_smoke_flags_operator_keys_in_category_trend_json(monkeypatch) -> None:
    def fake_request(url, *, method="GET", data=None):
        path = url.split("stock.example.test", 1)[1]
        if path == "/health":
            return 200, b"ok", "text/plain"
        if path == "/":
            return 200, b"<html>web-view</html>", "text/html"
        if path == "/api/archive?limit=1":
            return 200, b"{}", "application/json"
        if path == "/api/daily/2026-05-15" and method == "GET":
            return (
                200,
                b'{"business_date":"2026-05-15","sector_rollups":[{"category_type":"sector","display_name":"\xeb\xb0\x98\xeb\x8f\x84\xec\xb2\xb4"}]}',
                "application/json",
            )
        if path == "/api/candidate-evidence?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/flow-trend?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/etf-trend?date=2026-05-15&limit=5":
            return 200, b"{}", "application/json"
        if path == "/api/category-trend?type=sector&display_name=%EB%B0%98%EB%8F%84%EC%B2%B4":
            return 200, b'{"operation_profile":"mini-pc"}', "application/json"
        if path == "/api/daily/2026-05-15" and method == "POST":
            return 405, b"method not allowed", "text/plain"
        if path == "/api/status":
            return 404, b"not found", "text/plain"
        if path in {
            "/api/scheduler/run-now",
            "/api/scheduler/set-enabled",
            "/api/operator/pause",
            "/api/settings/set",
        } and method == "POST":
            return 404, b"not found", "text/plain"
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_web_view_smoke_http_request", fake_request)

    payload = cli_module._probe_external_web_view_smoke(
        base_url="https://stock.example.test",
        business_date=date(2026, 5, 15),
        allow_http=False,
    )

    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "category_trend_json_exposes_operator_keys"
    assert "operation_profile" in payload["issues"][0]["message"]
    assert (
        "/api/category-trend?type=sector&display_name=%EB%B0%98%EB%8F%84%EC%B2%B4"
        in payload["public_json_routes_checked"]
    )


def test_access_cookie_security_suffix_honors_https_proxy_headers() -> None:
    class FakeHeaders(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class FakeHandler:
        def __init__(self, headers):
            self.headers = FakeHeaders(headers)

    assert cli_module._access_cookie_security_suffix(FakeHandler({})) == ""
    assert cli_module._access_cookie_security_suffix(FakeHandler({"X-Forwarded-Proto": "https"})) == "; Secure"
    assert cli_module._access_cookie_security_suffix(FakeHandler({"X-Forwarded-Proto": "https,http"})) == "; Secure"
    assert cli_module._access_cookie_security_suffix(FakeHandler({"Forwarded": "for=1.2.3.4;proto=https"})) == "; Secure"
    assert cli_module._access_cookie_security_suffix(FakeHandler({"X-Forwarded-Ssl": "on"})) == "; Secure"


def test_rotation_mapping_audit_parser_accepts_date_limit_and_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["rotation-mapping-audit", "--date", "2026-05-08", "--limit", "2", "--json"])

    assert args.command == "rotation-mapping-audit"
    assert args.date == date(2026, 5, 8)
    assert args.limit == 2
    assert args.json is True


def test_web_view_parser_accepts_explicit_non_loopback_override() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["web-view", "--host", "0.0.0.0", "--allow-non-loopback"])

    assert args.command == "web-view"
    assert args.host == "0.0.0.0"
    assert args.allow_non_loopback is True


def test_mini_pc_preflight_parser_accepts_json_and_requirements() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "mini-pc-preflight",
            "--json",
            "--require-access-code",
            "--require-backup",
            "--require-env",
            "--require-mini-pc-profile",
        ]
    )

    assert args.command == "mini-pc-preflight"
    assert args.json is True
    assert args.require_access_code is True
    assert args.require_backup is True
    assert args.require_env is True
    assert args.require_mini_pc_profile is True


def test_mini_pc_preflight_snapshot_reports_db_and_access_gate_state(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=True,
    )

    assert snapshot["surface"] == "mini-pc-preflight"
    assert snapshot["db"]["ready"] is True
    assert snapshot["access_code"]["enabled"] is False
    assert snapshot["external_sharing_ready"] is False
    assert snapshot["environment"]["ready"] is False
    assert snapshot["environment"]["telegram_configured"] is False
    assert snapshot["environment"]["krx_open_api_configured"] is False
    assert snapshot["operation_profile"]["effective_value"] == "desktop-validation"
    assert snapshot["operation_profile"]["ready"] is False
    assert snapshot["operation_profile"]["required"] is False
    assert any(check["name"] == "operation_profile" and check["status"] == "warn" for check in snapshot["checks"])
    assert snapshot["project_files"]["ready"] is False
    assert "AGENTS.md" in snapshot["project_files"]["missing_required_files"]
    assert snapshot["web_view_assets"]["ready"] is False
    assert "example/Cycle.jpg" in snapshot["web_view_assets"]["missing_required_assets"]
    assert snapshot["scheduler_scripts"]["ready"] is False
    assert snapshot["runtime"]["python_executable"]
    assert "-PythonExe" in snapshot["runtime"]["scheduler_register_command"]
    assert "register_mini_pc_scheduler_tasks.ps1" in snapshot["runtime"]["scheduler_register_command"]
    assert snapshot["scheduler_scripts"]["missing_required_scripts"]
    assert "StockMonitor-KrxDailyBackfill" in snapshot["expected_scheduler_tasks"]
    assert "StockMonitor-KrxMentionedFlowBackfill" in snapshot["expected_scheduler_tasks"]
    assert "StockMonitor-WebViewHourlyRestart" in snapshot["expected_scheduler_tasks"]
    assert "StockMonitor-Shutdown" not in snapshot["expected_scheduler_tasks"]
    assert "StockMonitor-KrxFlowLoginReminder" not in snapshot["expected_scheduler_tasks"]
    assert "StockMonitor-KrxFlowLoginReminder" in snapshot["optional_scheduler_tasks"]
    assert "StockMonitor-Shutdown" in snapshot["desktop_validation_scheduler_tasks"]
    assert any(check["name"] == "access_code" and check["status"] == "fail" for check in snapshot["checks"])
    assert any(check["name"] == "latest_backup" and check["status"] == "warn" for check in snapshot["checks"])
    assert "python -m stock_monitor access-code set" in snapshot["recommended_commands"]
    assert "python -m stock_monitor access-code status" in snapshot["recommended_commands"]
    assert any("operator-settings set operation_profile mini-pc" in command for command in snapshot["recommended_commands"])
    assert "python -m stock_monitor web-view-browser-smoke --stock-limit 20" in snapshot["recommended_commands"]
    assert "python -m stock_monitor db-backup --tag before_operational_change" in snapshot["recommended_commands"]


def test_operator_status_scheduler_task_names_include_web_view_hourly_restart() -> None:
    task_names = cli_module._scheduler_task_names("StockMonitor")

    assert "StockMonitor-WebViewHourlyRestart" in task_names
    assert cli_module._scheduler_task_key("StockMonitor", "StockMonitor-WebViewHourlyRestart") == "web-view-hourly-restart"


def test_mini_pc_preflight_snapshot_warns_external_manual_verification_when_access_required(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    cli_module._write_access_code_record(config, "12345678")
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=True,
    )

    assert snapshot["access_code"]["enabled"] is True
    assert snapshot["external_sharing_ready"] is True
    assert snapshot["external_sharing"]["app_prerequisites_ready"] is True
    assert snapshot["external_sharing"]["cloudflare_access_or_allowlist_required"] is True
    assert "Tunnel target is exactly http://127.0.0.1:8780." in snapshot["external_sharing"]["manual_checks"]
    assert any(check["name"] == "external_surface" and check["status"] == "warn" for check in snapshot["checks"])


def test_mini_pc_preflight_snapshot_can_require_mini_pc_profile(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
        require_mini_pc_profile=True,
    )

    assert snapshot["operation_profile"]["ready"] is False
    assert snapshot["operation_profile"]["required"] is True
    assert snapshot["operation_profile"]["effective_value"] == "desktop-validation"
    assert "operation_profile=desktop-validation" in snapshot["operation_profile"]["detail"]
    assert any(check["name"] == "operation_profile" and check["status"] == "fail" for check in snapshot["checks"])
    assert "operation_profile" in snapshot["failing_checks"]
    assert snapshot["exit_ready"] is False


def test_mini_pc_preflight_snapshot_reports_required_project_files(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    for relative_path in (
        "AGENTS.md",
        "README.md",
        "CHANGELOG.md",
        "pyproject.toml",
        ".env.example",
        "scripts/create_migration_archive.ps1",
        "scripts/disable_source_desktop_scheduler_tasks.ps1",
        "scripts/register_mini_pc_scheduler_tasks.ps1",
        "scripts/restart_web_view.ps1",
        "scripts/setup_mini_pc_environment.ps1",
        "scripts/verify_cloudflare_web_view_tunnel.ps1",
        "scripts/verify_external_web_view_readiness.ps1",
        "scripts/verify_migration_archive.ps1",
        "scripts/verify_mini_pc_readiness.ps1",
        "scripts/verify_market_day_observation.ps1",
        "scripts/verify_task_scheduler_registration.ps1",
        "stock_research_monitor_mvp.md",
        "docs/codex/documentation-index.md",
        "docs/codex/current-work.md",
        "docs/codex/execution-roadmap.md",
        "docs/codex/surface-contract.md",
        "docs/codex/data-quality-checklist.md",
    ):
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok\n", encoding="utf-8")

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
    )

    assert snapshot["project_files"]["ready"] is True
    assert snapshot["project_files"]["missing_required_files"] == []
    assert "scripts/create_migration_archive.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/disable_source_desktop_scheduler_tasks.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/register_mini_pc_scheduler_tasks.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/restart_web_view.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/setup_mini_pc_environment.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_cloudflare_web_view_tunnel.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_external_web_view_readiness.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_migration_archive.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_mini_pc_readiness.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_market_day_observation.ps1" in snapshot["project_files"]["required_files"]
    assert "scripts/verify_task_scheduler_registration.ps1" in snapshot["project_files"]["required_files"]
    assert any(check["name"] == "project_files" and check["status"] == "ok" for check in snapshot["checks"])


def test_mini_pc_preflight_snapshot_reports_web_view_assets(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    for relative_path in (
        "example/Cycle.jpg",
        "data/rotation_overlay_coordinates.json",
        "data/rotation_image_aliases.json",
        "data/rotation_etf_candidates.json",
    ):
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok\n", encoding="utf-8")

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
    )

    assert snapshot["web_view_assets"]["ready"] is True
    assert snapshot["web_view_assets"]["missing_required_assets"] == []
    assert any(check["name"] == "web_view_assets" and check["status"] == "ok" for check in snapshot["checks"])


def test_mini_pc_preflight_snapshot_can_require_environment(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
        require_env=True,
    )

    assert snapshot["environment"]["ready"] is False
    assert snapshot["exit_ready"] is False
    assert "environment" in snapshot["failing_checks"]


def test_mini_pc_preflight_snapshot_reports_environment_without_secret_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret-krx")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "secret-id")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "secret-password")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
        require_env=True,
    )

    assert snapshot["environment"]["ready"] is True
    dumped = json.dumps(snapshot, ensure_ascii=False)
    assert "secret-token" not in dumped
    assert "secret-krx" not in dumped
    assert "secret-password" not in dumped


def test_mini_pc_preflight_snapshot_reports_scheduler_scripts(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    scripts_dir = config.root_dir / "scripts"
    scripts_dir.mkdir()
    for script_name in (
        "register_task_scheduler_tasks.ps1",
        "run_scheduled_krx_daily_backfill.ps1",
        "run_scheduled_notify.ps1",
        "run_scheduled_poll.ps1",
        "run_scheduled_krx_mentioned_flow_backfill.ps1",
        "run_process_telegram_commands.ps1",
        "restart_web_view.ps1",
        "run_scheduled_shutdown.ps1",
    ):
        (scripts_dir / script_name).write_text("# test script\n", encoding="utf-8")

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
    )

    assert snapshot["scheduler_scripts"]["ready"] is True
    assert snapshot["scheduler_scripts"]["missing_required_scripts"] == []
    assert "run_krx_flow_login_reminder.ps1" in snapshot["scheduler_scripts"]["optional_scripts"]
    assert any(check["name"] == "scheduler_scripts" and check["status"] == "ok" for check in snapshot["checks"])


def test_mini_pc_preflight_snapshot_uses_configured_task_prefix(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TASK_PREFIX", "MyMonitor")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
    )

    assert "MyMonitor-KrxDailyBackfill" in snapshot["expected_scheduler_tasks"]
    assert "MyMonitor-KrxFlowLoginReminder" in snapshot["optional_scheduler_tasks"]
    assert "StockMonitor-KrxDailyBackfill" not in snapshot["expected_scheduler_tasks"]


def test_mini_pc_preflight_snapshot_can_require_backup(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
        require_backup=True,
    )

    assert snapshot["backup"]["exists"] is False
    assert snapshot["exit_ready"] is False
    assert "latest_backup" in snapshot["failing_checks"]


def test_mini_pc_preflight_snapshot_reports_latest_backup(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    backup_dir = config.data_dir / "backups"
    backup_dir.mkdir(parents=True)
    backup_path = backup_dir / "stock_monitor_20260515_2100_before_mini_pc_migration.db"
    backup_path.write_bytes(b"backup")

    snapshot = _build_mini_pc_preflight_snapshot(
        config,
        repository,
        require_access_code=False,
        require_backup=True,
    )

    assert snapshot["backup"]["exists"] is True
    assert snapshot["backup"]["latest_backup"] == str(backup_path)
    assert not any(check["name"] == "latest_backup" and check["status"] == "fail" for check in snapshot["checks"])


def test_refresh_industry_parser_accepts_dry_run() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["refresh-industry", "1", "--snapshot-date", "2026-05-07", "--dry-run"])

    assert args.command == "refresh-industry"
    assert args.industry_code == "1"
    assert args.snapshot_date == date(2026, 5, 7)
    assert args.dry_run is True


def test_category_catalog_parser_accepts_discover_industries() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["category-catalog", "discover-industries", "--limit", "5", "--json"])

    assert args.command == "category-catalog"
    assert args.category_catalog_command == "discover-industries"
    assert args.limit == 5
    assert args.json is True


def test_category_catalog_discover_industries_prints_add_commands(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem(
                "sector",
                "12",
                "광고",
                "naver_quote",
                True,
                datetime(2026, 5, 10, 9, 0, 0),
            )
        ]
    )

    class _Item:
        def __init__(self, industry_code: str, industry_name: str, stock_count: int) -> None:
            self.industry_code = industry_code
            self.industry_name = industry_name
            self.stock_count = stock_count

    monkeypatch.setattr(
        cli_module,
        "fetch_stock_industry_catalog",
        lambda **_kwargs: [_Item("310", "광고", 18), _Item("307", "전자제품", 16)],
    )

    exit_code = _run_category_catalog(
        config,
        repository,
        Namespace(
            category_catalog_command="discover-industries",
            limit=1,
            json=False,
            page_size=100,
            max_pages=1,
        ),
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Naver industry catalog candidates" in output
    assert "310 | 광고 | stocks=18 | existing=Y(12/naver_quote)" in output
    assert 'python -m stock_monitor category-catalog add sector 310 --name "광고" --source naver_industry' in output
    assert "307" not in output


def test_category_catalog_discover_industries_json_marks_existing_display_matches(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem(
                "sector",
                "12",
                "광고",
                "naver_quote",
                True,
                datetime(2026, 5, 10, 9, 0, 0),
            )
        ]
    )

    class _Item:
        def __init__(self, industry_code: str, industry_name: str, stock_count: int) -> None:
            self.industry_code = industry_code
            self.industry_name = industry_name
            self.stock_count = stock_count

    monkeypatch.setattr(
        cli_module,
        "fetch_stock_industry_catalog",
        lambda **_kwargs: [_Item("310", "광고", 18), _Item("307", "전자제품", 16)],
    )

    exit_code = _run_category_catalog(
        config,
        repository,
        Namespace(
            category_catalog_command="discover-industries",
            limit=2,
            json=True,
            page_size=100,
            max_pages=1,
        ),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload[0]["existing_display_match"] is True
    assert payload[0]["existing_matches"] == [
        {"category_key": "12", "display_name": "광고", "source": "naver_quote", "refreshable": False}
    ]
    assert payload[1]["existing_display_match"] is False
    assert payload[1]["existing_matches"] == []


def test_resolve_web_view_value_qa_dates_includes_recent_business_days_and_dedupes(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    resolved = _resolve_web_view_value_qa_dates(
        config,
        explicit_dates=(date(2026, 5, 14),),
        recent_business_days=4,
        today=date(2026, 5, 15),
    )

    assert resolved == (
        date(2026, 5, 14),
        date(2026, 5, 15),
        date(2026, 5, 13),
        date(2026, 5, 12),
        date(2026, 5, 11),
    )


def test_resolve_web_view_value_qa_dates_uses_previous_business_day_on_weekend(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    resolved = _resolve_web_view_value_qa_dates(
        config,
        explicit_dates=(),
        recent_business_days=3,
        today=date(2026, 5, 17),
    )

    assert resolved == (
        date(2026, 5, 15),
        date(2026, 5, 14),
        date(2026, 5, 13),
    )


def test_notification_parsers_accept_briefing_format() -> None:
    parser = cli_module.build_parser()

    test_args = parser.parse_args(["send-test-notification", "--format", "briefing", "--dry-run"])
    scheduled_args = parser.parse_args(["scheduled-notify", "--format", "briefing", "--dry-run"])

    assert test_args.command == "send-test-notification"
    assert test_args.notification_format == "briefing"
    assert scheduled_args.command == "scheduled-notify"
    assert scheduled_args.notification_format == "briefing"


def test_scheduled_notify_defaults_to_briefing_while_test_notification_keeps_summary() -> None:
    parser = cli_module.build_parser()

    test_args = parser.parse_args(["send-test-notification", "--dry-run"])
    scheduled_args = parser.parse_args(["scheduled-notify", "--dry-run"])

    assert test_args.notification_format == "summary"
    assert scheduled_args.notification_format == "briefing"


def test_market_briefing_parser_defaults_to_preview_only() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["market-briefing", "--date", "2026-05-14", "--limit", "3"])

    assert args.command == "market-briefing"
    assert args.date == date(2026, 5, 14)
    assert args.limit == 3
    assert args.send is False


def test_scheduled_market_briefing_parser_defaults_to_guarded_dry_run_off() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["scheduled-market-briefing", "--dry-run", "--limit", "4"])

    assert args.command == "scheduled-market-briefing"
    assert args.dry_run is True
    assert args.allow_repeat is False
    assert args.allow_late is False
    assert args.limit == 4


def test_market_briefing_readiness_parser_defaults_to_read_only_json() -> None:
    parser = cli_module.build_parser()

    args = parser.parse_args(["market-briefing-readiness", "--recent-business-days", "3", "--json"])
    alias_args = parser.parse_args(["market-briefing-readiness", "--recent-report-dates", "4", "--json"])
    next_phase_args = parser.parse_args(
        [
            "next-phase-readiness",
            "--recent-report-dates",
            "4",
            "--stock-limit",
            "12",
            "--min-manual-reviews",
            "2",
            "--json",
        ]
    )
    market_day_observation_args = parser.parse_args(["market-day-observation", "--date", "2026-05-18", "--json"])

    assert args.command == "market-briefing-readiness"
    assert args.recent_business_days == 3
    assert args.limit == 5
    assert args.min_manual_reviews == 3
    assert args.json is True
    assert alias_args.command == "market-briefing-readiness"
    assert alias_args.recent_business_days == 4
    assert alias_args.json is True
    assert next_phase_args.command == "next-phase-readiness"
    assert next_phase_args.recent_report_dates == 4
    assert next_phase_args.stock_limit == 12
    assert next_phase_args.min_manual_reviews == 2
    assert next_phase_args.json is True
    assert market_day_observation_args.command == "market-day-observation"
    assert market_day_observation_args.date == date(2026, 5, 18)
    assert market_day_observation_args.json is True


def test_scheduled_market_briefing_requires_phone_review_acceptance(tmp_path, capsys, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    monkeypatch.setattr(cli_module, "datetime", _MarketBriefingAllowedDateTime)
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("send should be guarded")),
    )

    exit_code = cli_module._run_scheduled_market_briefing(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
        allow_late=False,
        limit=5,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "market_briefing_phone_review_accepted is false" in output
    assert repository.list_recent_deliveries(limit=10) == []


def test_scheduled_market_briefing_requires_recorded_manual_review_sends(tmp_path, capsys, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.set_app_setting(
        AppSetting(
            setting_key=cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
            setting_value="true",
            value_type="bool",
            updated_at=datetime(2026, 5, 12, 15, 0, 0),
            updated_by="operator-cli",
            detail="legacy_phone_acceptance",
            restart_required=False,
        ),
        audit_actor="operator-cli",
        audit_detail="legacy_phone_acceptance",
    )
    monkeypatch.setattr(cli_module, "datetime", _MarketBriefingAllowedDateTime)
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("send should be guarded")),
    )

    exit_code = cli_module._run_scheduled_market_briefing(
        config,
        repository,
        dry_run=False,
        allow_repeat=False,
        allow_late=False,
        limit=5,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "requires 3 recorded manual Telegram review sends" in output
    assert repository.list_recent_deliveries(limit=10) == []


def test_scheduled_market_briefing_waits_until_after_flow_backfill_window(tmp_path, capsys, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    monkeypatch.setattr(cli_module, "datetime", _MarketBriefingFlowBackfillWindowDateTime)

    exit_code = cli_module._run_scheduled_market_briefing(
        config,
        repository,
        dry_run=True,
        allow_repeat=False,
        allow_late=False,
        limit=5,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "16:00 is before the configured market briefing window 16:10~16:45" in output


def test_market_briefing_preview_includes_turnover_reference(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                volume=1000,
                turnover=2_300_000_000_000,
                fetched_at=datetime(2026, 5, 14, 16, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="035420",
                stock_name="NAVER",
                market="KOSDAQ",
                close_price=200_000,
                change_percent=-0.5,
                volume=800,
                turnover=500_000_000_000,
                fetched_at=datetime(2026, 5, 14, 16, 0, 0),
            ),
        ]
    )
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="삼성전자",
                title=f"삼성전자 점검 {index}",
                broker_name="NH투자증권" if index < 2 else "KB증권",
                published_at=datetime(2026, 5, 14, 9 + index, 0, 0),
                collected_at=datetime(2026, 5, 14, 16, 0, 0),
                stock_code="005930",
                target_price_raw="320000",
                target_price_value=320_000,
                opinion_raw="매수",
                opinion_normalized="buy",
                source_id=f"market-briefing-{index}",
                identity_key=f"market-briefing-{index}",
            )
            for index in range(3)
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    exit_code = _run_market_briefing(
        config,
        repository,
        explicit_date=business_date,
        limit=5,
        send=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "오늘의 시장 분위기 · 26.05.14" in output
    assert "거래대금 참고 · 26.05.14 KRX 저장값" in output
    assert "KOSPI: 삼성전자 2.3조" in output
    assert "추천" not in output
    assert "점수" not in output


def test_market_briefing_uses_stock_flow_reference_when_market_flow_missing(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    fetched_at = datetime(2026, 5, 14, 16, 0, 0)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="삼성전자",
                title=f"삼성전자 점검 {index}",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 14, 9 + index, 0, 0),
                collected_at=fetched_at,
                stock_code="005930",
                target_price_raw="100000",
                target_price_value=100_000,
                opinion_raw="매수",
                opinion_normalized="buy",
                source_id=f"market-stock-flow-{index}",
                identity_key=f"market-stock-flow-{index}",
            )
            for index in range(2)
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                net_buy_amount=1_500_000_000,
                fetched_at=fetched_at,
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="기관합계",
                net_buy_amount=-600_000_000,
                fetched_at=fetched_at,
            ),
        ]
    )

    exit_code = cli_module._run_market_briefing_readiness(
        config,
        repository,
        recent_business_days=3,
        limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["dates"][0]["has_flow_reference"] is True
    assert "missing_flow_reference" not in payload["dates"][0]["data_warnings"]

    assert _run_market_briefing(config, repository, explicit_date=business_date, limit=5, send=False) == 0
    output = capsys.readouterr().out
    assert "수급 참고" in output
    assert "삼성전자" in output
    assert "점수" not in output
    assert "등급" not in output


def test_market_briefing_readiness_reports_preview_and_manual_review_gate(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    fetched_at = datetime(2026, 5, 14, 16, 0, 0)
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=business_date,
                index_series="KOSPI",
                index_class="대표지수",
                index_name="코스피",
                close_index=2700.0,
                change_percent=0.8,
                fetched_at=fetched_at,
            ),
            MarketIndexDailySnapshot(
                business_date=business_date,
                index_series="KOSDAQ",
                index_class="대표지수",
                index_name="코스닥",
                close_index=900.0,
                change_percent=-0.2,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.2,
                volume=1000,
                turnover=2_300_000_000_000,
                fetched_at=fetched_at,
            )
        ]
    )
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=business_date,
                market="STK",
                investor_type="개인",
                fetched_at=fetched_at,
                net_buy_amount=1000,
                amount_unit="원",
            )
        ]
    )
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="삼성전자",
                title=f"삼성전자 점검 {index}",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 14, 9 + index, 0, 0),
                collected_at=fetched_at,
                stock_code="005930",
                target_price_raw="320000",
                target_price_value=320_000,
                opinion_raw="매수",
                opinion_normalized="buy",
                source_id=f"market-readiness-{index}",
                identity_key=f"market-readiness-{index}",
            )
            for index in range(2)
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    exit_code = cli_module._run_market_briefing_readiness(
        config,
        repository,
        recent_business_days=3,
        limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["recent_report_dates"] == 3
    assert payload["requested_min_manual_reviews"] == 1
    assert payload["enforced_min_manual_reviews"] == 3
    assert payload["min_manual_reviews"] == 3
    assert payload["preview_ready_count"] == 1
    assert payload["manual_review_send_count"] == 0
    assert payload["phone_review_gate"]["required_manual_review_sends"] == 3
    assert payload["phone_review_gate"]["recorded_manual_review_sends"] == 0
    assert payload["phone_review_gate"]["recorded_review_ready"] is False
    assert payload["phone_review_gate"]["phone_review_accepted"] is False
    assert payload["phone_review_gate"]["operator_settings_cli_enforced"] is True
    assert payload["phone_review_gate"]["admin_gui_settings_api_enforced"] is True
    assert payload["phone_review_gate"]["scheduled_live_send_enforced"] is True
    assert payload["phone_review_gate"]["ready"] is False
    assert payload["schedule_candidate_ready"] is False
    assert payload["schedule_candidate_window"]["earliest_time"] == "16:10"
    assert payload["schedule_candidate_window"]["latest_time"] == "16:45"
    assert payload["schedule_candidate_window"]["flow_backfill_time"] == "16:00"
    assert "flow backfill" in payload["schedule_candidate_window"]["flow_backfill_conflict_guard"]
    assert payload["schedule_block_reasons"] == ["manual Telegram review sends 0/3"]
    assert payload["manual_review_next_commands"] == [
        "python -m stock_monitor market-briefing --date 2026-05-14 --limit 5 --send"
    ]
    assert payload["dates"][0]["business_date"] == "2026-05-14"
    assert payload["dates"][0]["preview_ready"] is True
    assert payload["dates"][0]["has_market_reference"] is True
    assert payload["dates"][0]["has_turnover_reference"] is True
    assert payload["dates"][0]["has_flow_reference"] is True
    assert payload["dates"][0]["notable_stock_count"] == 1
    assert payload["dates"][0]["public_safe_issue_count"] == 0
    mood_card = payload["dates"][0]["time_slot_mood_card"]
    assert mood_card["source"] == "stored_report_krx_market_mood_card"
    assert mood_card["manual_review_candidate"] is True
    assert mood_card["live_fetch"] is False
    assert mood_card["scoring"] is False
    assert mood_card["recommendation"] is False
    assert "삼성전자" in mood_card["headline"]
    assert payload["dates"][0]["time_slot_mood_source_gap_count"] == 0


def test_next_phase_readiness_summarizes_read_only_blockers(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="?쇱꽦?꾩옄",
                title="?쇱꽦?꾩옄 ?먭?",
                broker_name="NH?ъ옄利앷텒",
                published_at=datetime(2026, 5, 14, 9, 0, 0),
                collected_at=datetime(2026, 5, 14, 9, 5, 0),
                stock_code="005930",
                target_price_raw="100000",
                target_price_value=100_000,
                opinion_raw="留ㅼ닔",
                opinion_normalized="buy",
                source_id="next-phase-readiness-1",
                identity_key="next-phase-readiness-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    assert _run_db_backup(
        config,
        repository,
        tag="next-phase",
        output_dir=config.data_dir / "backups",
        verify=True,
    ) == 0
    backup_path = next((config.data_dir / "backups").glob("stock_monitor_*_next-phase.db"))
    capsys.readouterr()
    assert _run_db_restore_smoke(
        config,
        backup_path=backup_path,
        work_dir=config.data_dir / "restore-smoke",
        keep_copy=False,
        audit_repository=repository,
    ) == 0
    capsys.readouterr()

    exit_code = cli_module._run_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "next-phase-readiness"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is False
    assert payload["writes_database"] is False
    assert payload["sends_telegram"] is False
    assert payload["registers_scheduler"] is False
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["recent_report_dates"] == 3
    assert payload["stock_limit"] == 5
    assert payload["latest_report"]["business_date"] == "2026-05-14"
    assert payload["latest_report"]["report_count"] == 1
    assert payload["candidate_evidence"]["inspected_date_count"] == 1
    assert payload["db_safety"]["latest_backup_exists"] is True
    assert payload["db_safety"]["latest_backup"] == backup_path.name
    assert payload["db_safety"]["latest_backup_restore_smoked"] is True
    assert payload["db_safety"]["latest_restore_smoke"]["backup"] == backup_path.name
    assert payload["db_safety"]["restore_smoke_command"] is None
    assert payload["db_safety"]["db_verify"]["ready"] is True
    assert payload["db_safety"]["db_verify"]["integrity_check"] == "ok"
    assert payload["db_safety"]["db_verify"]["foreign_key_violations"] == 0
    assert payload["db_safety"]["db_verify"]["investor_flow_quality_issue_total"] == 0
    assert payload["db_safety"]["db_verify"]["category_quality_issue_total"] == 0
    assert "db-verify --json" in payload["db_safety"]["db_verify"]["command"]
    assert payload["db_safety"]["cleanup_dry_run"]["read_only"] is True
    assert payload["db_safety"]["cleanup_dry_run"]["writes_database"] is False
    assert (
        payload["db_safety"]["cleanup_dry_run"]["retention_days"]
        == cli_module.DB_CLEANUP_DEFAULT_RETENTION_DAYS
    )
    assert "db-cleanup --dry-run" in payload["db_safety"]["cleanup_dry_run"]["command"]
    assert payload["category_snapshots"]["read_only"] is True
    assert payload["category_snapshots"]["writes_database"] is False
    assert payload["category_snapshots"]["limit"] == cli_module.CATEGORY_SNAPSHOT_READINESS_LIMIT
    assert payload["category_snapshots"]["status_summary"]["summary_date_count"] == 1
    assert payload["category_snapshots"]["status_summary"]["fallback_count"] == 1
    assert "category-snapshot-status --mode fallback" in payload["category_snapshots"]["status_command"]
    assert "category-snapshot-plan" in payload["category_snapshots"]["plan_command"]
    assert payload["rotation_mapping"]["read_only"] is True
    assert payload["rotation_mapping"]["writes_database"] is False
    assert payload["rotation_mapping"]["business_date"] == "2026-05-14"
    assert "rotation-mapping-audit --date 2026-05-14 --json" in payload["rotation_mapping"]["command"]
    assert payload["observation_reaction"]["read_only"] is True
    assert payload["observation_reaction"]["writes_database"] is False
    assert payload["observation_reaction"]["scoring"] is False
    assert payload["observation_reaction"]["recommendation"] is False
    assert payload["observation_reaction"]["internal_only"] is True
    assert payload["observation_reaction"]["public_surface_ready"] is False
    assert payload["observation_reaction"]["from_date"] == "2026-05-14"
    assert payload["observation_reaction"]["to_date"] == "2026-05-14"
    assert payload["observation_reaction"]["mention_threshold"] == 2
    assert payload["observation_reaction"]["candidate_count"] == 0
    assert payload["observation_reaction"]["horizon_coverage"] == []
    assert payload["observation_reaction"]["interpretation_status"] == "internal_review_only"
    assert "observation-reaction-distribution --from-date 2026-05-14" in payload["observation_reaction"][
        "command"
    ]
    assert payload["market_holiday_coverage"]["default_max_date"] == "2026-12-31"
    assert payload["market_holiday_coverage"]["configured_max_date"] == "2026-12-31"
    assert payload["market_holiday_coverage"]["renewal_required"] is False
    assert payload["market_day_observation"]["observation_business_date"]
    assert [task["task_name"] for task in payload["market_day_observation"]["expected_tasks"]] == [
        "StockMonitor-TelegramCommands",
        "StockMonitor-KrxDailyBackfill",
        "StockMonitor-Notify",
        "StockMonitor-Poll",
        "StockMonitor-KrxMentionedFlowBackfill",
    ]
    assert "StockMonitor-Shutdown" in payload["market_day_observation"]["note"]
    assert any(
        "verify_market_day_observation.ps1" in command
        for command in payload["market_day_observation"]["verification_commands"]
    )
    assert any(
        "-Date " in command and "verify_market_day_observation.ps1" in command
        for command in payload["market_day_observation"]["verification_commands"]
    )
    assert any("verify_next_phase_closeout.ps1" in command for command in payload["next_commands"])
    assert payload["market_day_observation_audit"]["surface"] == "market-day-observation"
    assert payload["market_day_observation_audit"]["observed_enough_for_scheduler"] is False
    assert payload["web_view_startup_fallback"]["read_only"] is True
    assert payload["web_view_startup_fallback"]["startup_shortcut_name"] == "StockMonitor-WebView.lnk"
    assert "create_web_view_startup_shortcut.ps1" in payload["web_view_startup_fallback"]["setup_command"]
    assert "create_web_view_startup_shortcut.ps1" in payload["web_view_startup_fallback"]["next_command"]
    assert payload["external_web_view_sharing"]["status"] == "manual_provider_setup_required"
    assert payload["external_web_view_sharing"]["candidate_surface"] == "web-view"
    assert payload["external_web_view_sharing"]["forbidden_surface"] == "admin-gui"
    assert payload["external_web_view_sharing"]["local_tunnel_target"] == "http://127.0.0.1:8780"
    assert "verify_external_web_view_readiness.ps1" in payload["external_web_view_sharing"]["preflight_command"]
    assert "verify_cloudflare_web_view_tunnel.ps1" in payload["external_web_view_sharing"]["provider_verification_command"]
    assert "external-web-view-smoke" in payload["external_web_view_sharing"]["provider_smoke_command"]
    local_preflight_checks = {
        check["name"]: check for check in payload["external_web_view_sharing"]["local_preflight_checks"]
    }
    assert "verify_external_web_view_readiness.ps1" in local_preflight_checks[
        "mini_pc_profile_and_access_gate"
    ]["command"]
    assert "web-view-value-qa --recent-business-days 4" in local_preflight_checks["public_value_qa"]["command"]
    assert "issue_count is 0" in local_preflight_checks["public_value_qa"]["expectation"]
    assert "latest-KRX availability" not in local_preflight_checks["public_value_qa"]["expectation"]
    assert "web-view-browser-smoke --stock-limit 20" in local_preflight_checks[
        "local_browser_mobile_smoke"
    ]["command"]
    assert "POST 405" in local_preflight_checks["local_browser_mobile_smoke"]["expectation"]
    assert "access-code enabled" in payload["external_web_view_sharing"]["required_local_checks"]
    assert "admin control POST routes unavailable from web-view" in payload["external_web_view_sharing"]["required_local_checks"]
    cloudflare_sequence = payload["external_web_view_sharing"]["cloudflare_connection_sequence"]
    assert [step["step"] for step in cloudflare_sequence] == [
        "confirm_access_code",
        "run_local_external_readiness",
        "start_local_web_view",
        "configure_cloudflare_hostname",
        "confirm_forbidden_routes_absent",
        "enable_provider_access_control",
        "run_provider_wrapper",
        "share_after_success",
    ]
    assert "access-code status" in cloudflare_sequence[0]["command"]
    assert "verify_external_web_view_readiness.ps1" in cloudflare_sequence[1]["command"]
    assert "scripts\\run_web_view.ps1" in cloudflare_sequence[2]["command"]
    assert "-HostAddress 127.0.0.1 -Port 8780" in cloudflare_sequence[2]["command"]
    assert cloudflare_sequence[3]["provider_target"] == "http://127.0.0.1:8780"
    assert "admin-gui" in cloudflare_sequence[4]["forbidden_targets"]
    assert "Cloudflare Access" in cloudflare_sequence[5]["expectation"]
    assert "verify_cloudflare_web_view_tunnel.ps1" in cloudflare_sequence[6]["command"]
    assert cloudflare_sequence[7]["requires_provider_smoke_success"] is True
    provider_smoke_routes = {
        (check["method"], check["route"])
        for check in payload["external_web_view_sharing"]["provider_smoke_checks"]
    }
    assert ("GET", "/api/flow-trend?date={date}&limit=5") in provider_smoke_routes
    assert ("GET", "/api/etf-trend?date={date}&limit=5") in provider_smoke_routes
    assert ("GET", "/api/category-trend?type={type}&display_name={display_name}") in provider_smoke_routes
    assert ("POST", "/api/settings/set") in provider_smoke_routes
    assert any(
        "Cloudflare Access HTML" in check["expectation"]
        for check in payload["external_web_view_sharing"]["provider_smoke_checks"]
    )
    assert any(
        "Cloudflare Access" in control
        for control in payload["external_web_view_sharing"]["required_provider_controls"]
    )
    assert any(
        "keep admin-gui private" in step
        for step in payload["external_web_view_sharing"]["manual_steps"]
    )
    assert payload["external_web_view_provider_smoke"]["ready"] is False
    assert "verify_cloudflare_web_view_tunnel.ps1" in payload["external_web_view_provider_smoke"]["next_command"]
    completion_gates = {item["key"]: item for item in payload["completion_gates"]}
    assert completion_gates["market_day_scheduled_run_observation"]["ready"] is False
    assert "verify_market_day_observation.ps1" in completion_gates[
        "market_day_scheduled_run_observation"
    ]["next_command"]
    assert "-Date " in completion_gates["market_day_scheduled_run_observation"]["next_command"]
    assert completion_gates["external_web_view_provider_smoke"]["ready"] is False
    assert "verify_cloudflare_web_view_tunnel.ps1" in completion_gates["external_web_view_provider_smoke"][
        "next_command"
    ]
    assert completion_gates["web_view_startup_fallback"]["ready"] is False
    assert "create_web_view_startup_shortcut.ps1" in completion_gates["web_view_startup_fallback"][
        "next_command"
    ]
    assert payload["market_briefing"]["manual_review_send_count"] == 0
    assert payload["market_briefing"]["requested_min_manual_reviews"] == 1
    assert payload["market_briefing"]["enforced_min_manual_reviews"] == 3
    assert payload["market_briefing"]["min_manual_reviews"] == 3
    assert payload["market_briefing"]["phone_review_gate"]["required_manual_review_sends"] == 3
    assert payload["market_briefing"]["phone_review_gate"]["recorded_manual_review_sends"] == 0
    assert payload["market_briefing"]["phone_review_gate"]["recorded_review_ready"] is False
    assert payload["market_briefing"]["phone_review_gate"]["phone_review_accepted"] is False
    assert payload["market_briefing"]["phone_review_gate"]["operator_settings_cli_enforced"] is True
    assert payload["market_briefing"]["phone_review_gate"]["admin_gui_settings_api_enforced"] is True
    assert payload["market_briefing"]["phone_review_gate"]["scheduled_live_send_enforced"] is True
    assert payload["market_briefing"]["phone_review_gate"]["ready"] is False
    assert payload["market_briefing"]["schedule_candidate_ready"] is False
    assert payload["market_briefing"]["schedule_candidate_window"]["earliest_time"] == "16:10"
    assert payload["market_briefing"]["schedule_candidate_window"]["flow_backfill_time"] == "16:00"
    assert payload["market_briefing"]["manual_review_next_commands"] == [
        "python -m stock_monitor market-briefing --date 2026-05-14 --limit 5 --send"
    ]
    assert "python -m stock_monitor operator-status --json --health-exit" in payload["next_commands"]
    assert any("verify_market_day_observation.ps1" in command for command in payload["next_commands"])
    assert any("verify_task_scheduler_registration.ps1" in command for command in payload["next_commands"])
    assert any("market-day-observation" in command for command in payload["next_commands"])
    assert "python -m stock_monitor external-web-view-sharing-plan --json" in payload["next_commands"]
    assert any("verify_external_web_view_readiness.ps1" in command for command in payload["next_commands"])
    assert any("verify_cloudflare_web_view_tunnel.ps1" in command for command in payload["next_commands"])
    assert any("external-web-view-smoke" in command for command in payload["next_commands"])
    assert (
        "python -m stock_monitor candidate-evidence-readiness --recent-report-dates 5 --stock-limit 20 --json"
        in payload["next_commands"]
    )
    assert "python -m stock_monitor category-snapshot-status --mode fallback --limit 100 --json" in payload[
        "next_commands"
    ]
    assert "python -m stock_monitor category-snapshot-plan --limit 100 --json" in payload["next_commands"]
    assert "python -m stock_monitor rotation-mapping-audit --date 2026-05-14 --json" in payload["next_commands"]
    assert (
        "python -m stock_monitor observation-reaction-distribution --from-date 2026-05-14 --to-date 2026-05-14 --mention-threshold 2 --json"
        in payload["next_commands"]
    )
    assert "python -m stock_monitor market-briefing --date 2026-05-14 --limit 5 --send" in payload["next_commands"]
    assert "manual Telegram review sends 0/3" in payload["blocking_items"]
    assert "manual Telegram phone readability review sends" in payload["non_code_dependencies"]
    assert "manual Telegram phone readability review sends" not in payload["completion_blockers"]
    assert "manual Telegram review sends 0/3" in payload["completion_blockers"]
    assert "web-view Startup fallback configuration" in payload["completion_blockers"]
    assert payload["completion_ready"] is False
    dev_env = payload["development_environment"]
    assert dev_env["mode"] == "development"
    assert dev_env["read_only"] is True
    assert "development environment" in dev_env["interpretation"]
    assert "python -m stock_monitor market-briefing-readiness --recent-report-dates 5 --json" in dev_env[
        "dev_safe_next_commands"
    ]
    assert "python -m stock_monitor krx-baseline-analysis --json" in dev_env["dev_safe_next_commands"]
    assert "python -m stock_monitor operator-status --json --health-exit" not in dev_env[
        "dev_safe_next_commands"
    ]
    assert "python -m stock_monitor operator-status --json --health-exit" in dev_env[
        "operator_or_live_next_commands"
    ]
    assert any("market-briefing --date 2026-05-14 --limit 5 --send" in command for command in dev_env[
        "operator_or_live_next_commands"
    ])
    assert any("create_web_view_startup_shortcut.ps1" in command for command in dev_env[
        "operator_or_live_next_commands"
    ])
    assert any("verify_cloudflare_web_view_tunnel.ps1" in command for command in dev_env[
        "operator_or_live_next_commands"
    ])
    assert not any("--send" in command for command in dev_env["dev_safe_next_commands"])
    assert "manual Telegram review sends 0/3" in dev_env["live_ops_blockers_deferred"]
    assert "web-view Startup fallback configuration" in dev_env["live_ops_blockers_deferred"]

    repository.record_delivery(
        DeliveryLog(
            business_date=business_date,
            channel=cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL,
            status="sent",
            delivered_at=datetime(2026, 5, 14, 16, 30, 0),
            message_id="manual-review-1",
            detail="source=manual; review send",
        )
    )

    exit_code = cli_module._run_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    reviewed_payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert reviewed_payload["market_briefing"]["manual_review_send_count"] == 1
    assert reviewed_payload["market_briefing"]["phone_review_accepted"] is False
    assert reviewed_payload["market_briefing"]["phone_review_gate"]["recorded_review_ready"] is False
    assert reviewed_payload["market_briefing"]["phone_review_gate"]["ready"] is False
    assert reviewed_payload["market_briefing"]["schedule_candidate_ready"] is False
    assert reviewed_payload["market_briefing"]["manual_review_next_commands"] == []
    assert "manual Telegram review sends 1/3" in reviewed_payload["blocking_items"]
    assert "operator phone readability acceptance missing" not in reviewed_payload["blocking_items"]
    assert "manual Telegram review sends 1/3" in reviewed_payload["completion_blockers"]
    assert "manual Telegram phone readability review sends" in reviewed_payload["non_code_dependencies"]
    assert not any(
        "operator-settings set market_briefing_phone_review_accepted true" in command
        for command in reviewed_payload["next_commands"]
    )

    for index, review_date in enumerate((date(2026, 5, 13), date(2026, 5, 12)), start=2):
        repository.record_delivery(
            DeliveryLog(
                business_date=review_date,
                channel=cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL,
                status="sent",
                delivered_at=datetime(2026, 5, 14, 16, 30 + index, 0),
                message_id=f"manual-review-{index}",
                detail="source=manual; review send",
            )
        )

    repository.set_app_setting(
        AppSetting(
            setting_key=cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
            setting_value="true",
            value_type="bool",
            updated_at=datetime(2026, 5, 14, 16, 35, 0),
            updated_by="operator-cli",
            detail="phone_readability_accepted",
            restart_required=False,
        ),
        audit_actor="operator-cli",
        audit_detail="phone_readability_accepted",
    )

    exit_code = cli_module._run_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    accepted_payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert accepted_payload["market_briefing"]["phone_review_accepted"] is True
    assert accepted_payload["market_briefing"]["phone_review_gate"]["ready"] is True
    assert accepted_payload["market_briefing"]["schedule_candidate_ready"] is True
    assert "operator phone readability acceptance missing" not in accepted_payload["blocking_items"]
    assert "operator phone-readability acceptance after recorded manual Telegram review sends" not in accepted_payload[
        "completion_blockers"
    ]
    assert "real market-day scheduled-run observation" in accepted_payload["completion_blockers"]
    assert "external web-view tunnel/provider setup while keeping admin-gui private" in accepted_payload[
        "completion_blockers"
    ]
    assert accepted_payload["completion_ready"] is False

    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 14, 16, 40, 0),
            component="external-web-view",
            event_type="provider-smoke",
            status="success",
            business_date=business_date,
            detail="url_origin=https://stock.example.test; business_date=2026-05-14",
        )
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 14, 17, 10, 0),
            component="krx",
            event_type="openapi-availability-probe",
            status="available",
            business_date=business_date,
            detail=json.dumps(
                {
                    "endpoint": "stock-kospi-daily",
                    "raw_row_count": 932,
                    "parsed_row_count": 932,
                    "reference_date": "2026-05-14",
                    "stored": False,
                },
                ensure_ascii=False,
            ),
        )
    )

    exit_code = cli_module._run_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=1,
        as_json=True,
    )

    smoked_payload = json.loads(capsys.readouterr().out)
    smoked_gates = {item["key"]: item for item in smoked_payload["completion_gates"]}
    assert exit_code == 0
    assert smoked_payload["krx_openapi_availability_probe"]["latest_status"] == "available"
    assert smoked_payload["krx_openapi_availability_probe"]["latest_endpoint"] == "stock-kospi-daily"
    assert smoked_payload["krx_openapi_availability_probe"]["latest_raw_row_count"] == 932
    assert smoked_payload["krx_openapi_availability_probe"]["latest_parsed_row_count"] == 932
    assert smoked_payload["krx_openapi_availability_probe"]["writes_snapshot_tables"] is False
    assert (
        "python -m stock_monitor krx-openapi-availability-probe --date latest --endpoint daily --json"
        in smoked_payload["next_commands"]
    )
    assert smoked_payload["external_web_view_provider_smoke"]["ready"] is True
    assert smoked_payload["external_web_view_sharing"]["status"] == "provider_smoke_ready"
    assert smoked_gates["external_web_view_provider_smoke"]["ready"] is True
    assert not any(
        "verify_cloudflare_web_view_tunnel.ps1" in command
        for command in smoked_payload["next_commands"]
    )
    assert not any(
        "external-web-view-smoke --url https://YOUR-WEB-VIEW-URL" in command
        for command in smoked_payload["next_commands"]
    )
    assert "external web-view tunnel/provider setup while keeping admin-gui private" not in smoked_payload[
        "completion_blockers"
    ]
    assert "real market-day scheduled-run observation" in smoked_payload["completion_blockers"]
    assert smoked_payload["completion_ready"] is False


def test_next_phase_readiness_blocks_unverified_latest_backup(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="Samsung Electronics",
                title="Samsung Electronics note",
                broker_name="NH Investment",
                published_at=datetime(2026, 5, 14, 9, 0, 0),
                collected_at=datetime(2026, 5, 14, 9, 5, 0),
                stock_code="005930",
                target_price_raw="100000",
                target_price_value=100_000,
                opinion_raw="Buy",
                opinion_normalized="buy",
                source_id="next-phase-readiness-unverified-backup",
                identity_key="next-phase-readiness-unverified-backup",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    assert _run_db_backup(
        config,
        repository,
        tag="next-phase-unverified",
        output_dir=config.data_dir / "backups",
        verify=True,
    ) == 0
    backup_path = next((config.data_dir / "backups").glob("stock_monitor_*_next-phase-unverified.db"))
    capsys.readouterr()

    exit_code = cli_module._run_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=0,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["db_safety"]["latest_backup_exists"] is True
    assert payload["db_safety"]["latest_backup"] == backup_path.name
    assert payload["db_safety"]["latest_backup_restore_smoked"] is False
    assert "db-restore-smoke" in payload["db_safety"]["restore_smoke_command"]
    assert payload["db_safety"]["db_verify"]["ready"] is True
    assert payload["db_safety"]["cleanup_dry_run"]["read_only"] is True
    assert payload["db_safety"]["cleanup_dry_run"]["writes_database"] is False
    assert "latest DB backup restore-smoke missing" in payload["blocking_items"]
    assert "latest DB backup restore-smoke missing" in payload["completion_blockers"]
    assert payload["completion_ready"] is False


def test_next_phase_readiness_blocks_missing_latest_backup(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    payload = cli_module._build_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=0,
    )

    assert payload["db_safety"]["latest_backup_exists"] is False
    assert payload["db_safety"]["restore_smoke_command"] is None
    assert payload["db_safety"]["db_verify"]["ready"] is True
    assert payload["db_safety"]["cleanup_dry_run"]["read_only"] is True
    assert payload["db_safety"]["cleanup_dry_run"]["writes_database"] is False
    assert "latest DB backup missing" in payload["blocking_items"]
    assert "latest DB backup missing" in payload["completion_blockers"]
    assert payload["completion_ready"] is False


def test_next_phase_readiness_surfaces_market_holiday_coverage_expiry(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    payload = cli_module._build_next_phase_readiness(
        config,
        repository,
        recent_report_dates=3,
        stock_limit=5,
        min_manual_reviews=0,
        now=datetime(2026, 10, 1, 17, 0, 0),
    )

    assert payload["market_holiday_coverage"]["default_max_date"] == "2026-12-31"
    assert payload["market_holiday_coverage"]["configured_max_date"] == "2026-12-31"
    assert payload["market_holiday_coverage"]["renewal_required"] is True
    assert "market holiday coverage needs verified future-year dates" in payload["blocking_items"]
    assert "verified future-year KRX holiday dates" in payload["non_code_dependencies"]
    assert "market holiday coverage needs verified future-year dates" in payload["completion_blockers"]


def test_operator_settings_blocks_phone_review_acceptance_without_manual_sends(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    args = Namespace(
        settings_action="set",
        key=cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
        value="true",
        actor="operator-cli",
        reason="phone_readability_accepted",
        confirm=True,
    )

    try:
        cli_module._run_operator_settings(config, repository, args)
    except ValueError as exc:
        assert "requires 3 recorded manual Telegram review sends" in str(exc)
    else:
        raise AssertionError("phone review acceptance should require recorded manual sends")

    assert repository.get_app_setting(cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING) is None
    audit_rows = repository.list_admin_audit_logs(limit=1)
    assert audit_rows[0].status == "validation_failed"
    assert audit_rows[0].setting_key == cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING


def test_operator_settings_allows_phone_review_acceptance_after_manual_sends(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    for index, business_date in enumerate((date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)), start=1):
        repository.record_delivery(
            DeliveryLog(
                business_date=business_date,
                channel=cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL,
                status="sent",
                delivered_at=datetime(2026, 5, 15, 16, 20 + index, 0),
                message_id=f"manual-review-{index}",
                detail="source=manual; review send",
            )
        )

    args = Namespace(
        settings_action="set",
        key=cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
        value="true",
        actor="operator-cli",
        reason="phone_readability_accepted",
        confirm=True,
    )

    exit_code = cli_module._run_operator_settings(config, repository, args)

    assert exit_code == 0
    setting = repository.get_app_setting(cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING)
    assert setting is not None
    assert setting.setting_value == "true"


def test_admin_gui_settings_blocks_phone_review_acceptance_without_manual_sends(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    request = {
        "key": cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
        "value": "true",
        "reason": "phone_readability_accepted",
        "confirm_text": "변경",
    }

    try:
        cli_module._handle_admin_gui_post(config, repository, "/api/settings/set", request)
    except ValueError as exc:
        assert "requires 3 recorded manual Telegram review sends" in str(exc)
    else:
        raise AssertionError("admin GUI phone review acceptance should require recorded manual sends")

    assert repository.get_app_setting(cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING) is None
    audit_rows = repository.list_admin_audit_logs(limit=1)
    assert audit_rows[0].actor == "admin-gui"
    assert audit_rows[0].status == "validation_failed"
    assert audit_rows[0].setting_key == cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING


def test_admin_gui_settings_allows_phone_review_acceptance_after_manual_sends(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    for index, business_date in enumerate((date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)), start=1):
        repository.record_delivery(
            DeliveryLog(
                business_date=business_date,
                channel=cli_module.MARKET_BRIEFING_DELIVERY_CHANNEL,
                status="sent",
                delivered_at=datetime(2026, 5, 15, 16, 30 + index, 0),
                message_id=f"admin-manual-review-{index}",
                detail="source=manual; review send",
            )
        )

    status, payload = cli_module._handle_admin_gui_post(
        config,
        repository,
        "/api/settings/set",
        {
            "key": cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING,
            "value": "true",
            "reason": "phone_readability_accepted",
            "confirm_text": "변경",
        },
    )

    assert int(status) == 200
    assert payload["ok"] is True
    assert payload["changed"] is True
    setting = repository.get_app_setting(cli_module.MARKET_BRIEFING_PHONE_REVIEW_SETTING)
    assert setting is not None
    assert setting.setting_value == "true"


def test_market_day_observation_audit_classifies_scheduler_evidence(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    observation_date = date(2026, 5, 18)
    repository.upsert_worker_state(
        WorkerState(
            worker_name=cli_module.TELEGRAM_COMMAND_LOOP_WORKER,
            status="stopped",
            updated_at=datetime(2026, 5, 18, 16, 30, 0),
            last_started_at=datetime(2026, 5, 18, 8, 0, 0),
            last_success_at=datetime(2026, 5, 18, 16, 30, 0),
            last_error_at=None,
            last_error=None,
            interval_seconds=60,
            end_time="16:30",
        )
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 18, 8, 20, 0),
            component="krx",
            event_type="backfill-missing",
            status="empty",
            business_date=date(2026, 5, 15),
            detail="endpoint=daily; dates=1; endpoints=6; incomplete_endpoints=6",
        )
    )
    repository.record_delivery(
        DeliveryLog(
            business_date=date(2026, 5, 15),
            channel=cli_module.PRODUCTION_DELIVERY_CHANNEL,
            status="sent",
            delivered_at=datetime(2026, 5, 18, 8, 25, 0),
            message_id="scheduled-1",
            detail="source=scheduled; format=briefing",
        )
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 18, 9, 0, 0),
            component="poll",
            event_type="time-window",
            status="success",
            business_date=observation_date,
            detail="scheduled poll observed",
        )
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 18, 16, 5, 0),
            component="krx-flow",
            event_type="scheduled-mentioned-flow-backfill",
            status="success",
            business_date=observation_date,
            detail="calls=12; stored_rows=120",
        )
    )

    payload = cli_module._build_market_day_observation_audit(
        config,
        repository,
        business_date=observation_date,
        now=datetime(2026, 5, 18, 16, 20, 0),
    )

    by_key = {item["key"]: item for item in payload["checks"]}
    assert payload["surface"] == "market-day-observation"
    assert payload["read_only"] is True
    assert payload["status"] == "attention"
    assert payload["observed_enough_for_scheduler"] is True
    assert payload["next_due_check"] is None
    assert by_key["telegram_command_loop"]["evidence_status"] == "observed"
    assert by_key["telegram_command_loop"]["verify_after_at"].startswith("2026-05-18T08:05:00")
    assert by_key["krx_daily_backfill"]["evidence_status"] == "attention"
    assert by_key["notify"]["evidence_status"] == "observed"
    assert by_key["poll"]["evidence_status"] == "observed"
    assert by_key["krx_mentioned_flow_backfill"]["evidence_status"] == "observed"
    assert (
        "python -m stock_monitor market-day-observation --date 2026-05-18 --json"
        in payload["next_commands"]
    )


def test_market_day_observation_audit_keeps_future_date_pending(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    payload = cli_module._build_market_day_observation_audit(
        config,
        repository,
        business_date=date(2026, 5, 18),
        now=datetime(2026, 5, 17, 16, 20, 0),
    )

    assert payload["status"] == "pending"
    assert payload["observed_enough_for_scheduler"] is False
    assert {item["evidence_status"] for item in payload["checks"]} == {"pending"}
    assert payload["next_due_check"] == {
        "key": "telegram_command_loop",
        "task_name": "StockMonitor-TelegramCommands",
        "scheduled_time": "08:00",
        "verify_after": "08:05",
        "verify_after_at": "2026-05-18T08:05:00+09:00",
    }
    assert payload["next_commands"][0] == "python -m stock_monitor market-day-observation --date 2026-05-18 --json"
    assert {item["verify_after_at"] for item in payload["checks"]} == {
        "2026-05-18T08:05:00+09:00",
        "2026-05-18T08:20:00+09:00",
        "2026-05-18T08:30:00+09:00",
        "2026-05-18T09:00:00+09:00",
        "2026-05-18T16:10:00+09:00",
    }


def test_candidate_evidence_readiness_reports_visible_review_coverage(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 14)
    fetched_at = datetime(2026, 5, 14, 16, 0, 0)
    repository.insert_reports(
        [
            Report(
                business_date=business_date,
                stock_name="삼성전자",
                title=f"삼성전자 점검 {index}",
                broker_name="NH투자증권" if index == 0 else "KB증권",
                published_at=datetime(2026, 5, 14, 9 + index, 0, 0),
                collected_at=fetched_at,
                stock_code="005930",
                target_price_raw="100000",
                target_price_value=100_000,
                opinion_raw="매수",
                opinion_normalized="buy",
                source_id=f"candidate-readiness-{index}",
                identity_key=f"candidate-readiness-{index}",
            )
            for index in range(2)
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=90_000,
                change_percent=1.2,
                volume=1000,
                turnover=2_300_000_000_000,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 15),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=105_000,
                change_percent=2.1,
                volume=1000,
                turnover=2_500_000_000_000,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=fetched_at,
                net_buy_volume=500,
                volume_unit="주",
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="STK",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                fetched_at=fetched_at,
                net_buy_volume=500,
            )
        ]
    )

    exit_code = cli_module._run_candidate_evidence_readiness(
        config,
        repository,
        recent_business_days=3,
        limit=6,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["recent_report_dates"] == 3
    assert payload["review_ready_count"] == 1
    assert payload["interpretation_blocked"] is True
    assert payload["dates"][0]["business_date"] == "2026-05-14"
    assert payload["dates"][0]["eligible_summary_count"] == 1
    assert payload["dates"][0]["visible_row_count"] == 1
    assert payload["dates"][0]["target_progress_available_count"] == 1
    assert payload["dates"][0]["target_validation_available_count"] == 1
    assert payload["dates"][0]["target_hit_count"] == 1
    assert payload["dates"][0]["market_reference_available_count"] == 1
    assert payload["dates"][0]["stock_flow_available_count"] == 1
    assert payload["dates"][0]["foreign_rank_available_count"] == 1
    assert payload["observation_priority_counts"] == {"우선 확인": 1}
    assert payload["visible_observation_priority_counts"] == {"우선 확인": 1}
    assert payload["why_notable_counts"] == {
        "리포트 집중": 1,
        "외국인 순매수 상위": 1,
    }
    assert payload["visible_why_notable_counts"] == payload["why_notable_counts"]
    assert payload["internal_candidate_signal_counts"] == {
        "가격/거래량 위치": 1,
        "거래대금 참고": 1,
        "리포트 집중": 1,
        "목표가 범위": 1,
        "브로커 폭": 1,
        "외국인 순매수 상위": 1,
        "종목별 수급": 1,
    }
    assert payload["missing_information_counts"] == {}
    assert payload["visible_missing_information_counts"] == {}
    assert payload["internal_missing_information_counts"] == {}
    assert payload["dates"][0]["observation_priority_counts"] == {"우선 확인": 1}
    assert payload["dates"][0]["visible_observation_priority_counts"] == {"우선 확인": 1}
    assert payload["dates"][0]["why_notable_counts"] == {
        "리포트 집중": 1,
        "외국인 순매수 상위": 1,
    }
    assert payload["dates"][0]["visible_why_notable_counts"] == payload["dates"][0]["why_notable_counts"]
    assert payload["dates"][0]["internal_candidate_signal_counts"] == {
        "가격/거래량 위치": 1,
        "거래대금 참고": 1,
        "리포트 집중": 1,
        "목표가 범위": 1,
        "브로커 폭": 1,
        "외국인 순매수 상위": 1,
        "종목별 수급": 1,
    }
    assert payload["dates"][0]["missing_information_counts"] == {}
    assert payload["dates"][0]["visible_missing_information_counts"] == {}
    assert payload["dates"][0]["internal_missing_information_counts"] == {}
    assert payload["dates"][0]["qa_issue_count"] == 0
    assert payload["dates"][0]["top_rows"][0]["stock_code"] == "005930"
    assert payload["dates"][0]["top_rows"][0]["observation_priority"] == "우선 확인"
    assert payload["dates"][0]["top_rows"][0]["why_notable"] == [
        "리포트 집중",
        "외국인 순매수 상위",
    ]
    assert payload["dates"][0]["top_rows"][0]["internal_candidate_signals"] == [
        "리포트 집중",
        "브로커 폭",
        "목표가 범위",
        "거래대금 참고",
        "종목별 수급",
        "가격/거래량 위치",
        "외국인 순매수 상위",
    ]
    assert payload["dates"][0]["top_rows"][0]["missing_information"] == []
    assert payload["dates"][0]["top_rows"][0]["internal_missing_information"] == []


def test_market_briefing_message_qa_blocks_decision_and_raw_missing_copy() -> None:
    issues = _collect_market_briefing_message_issues(
        "\n".join(
            [
                "오늘의 시장 분위기 · 26.05.14",
                "확인 포인트",
                "- 반도체 추가 하락 시 매수 기회 포착",
                "- 수급 참고 N/A",
                "- 전략 제안",
            ]
        )
    )

    assert {issue["code"] for issue in issues} == {
        "market_briefing_decision_wording",
        "market_briefing_raw_missing_marker",
    }


def test_market_briefing_message_qa_allows_flow_buy_dominance_wording() -> None:
    issues = _collect_market_briefing_message_issues(
        "\n".join(
            [
                "오늘의 시장 분위기 · 26.05.14",
                "수급 참고 · 26.05.14 KOSPI 저장값",
                "- 개인 매수 우위 / 외국인 매도 우위 / 기관 매수 우위",
            ]
        )
    )

    assert issues == []


def test_market_briefing_check_points_use_latest_stored_krx_index_date(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    index_date = date(2026, 5, 13)
    briefing_date = date(2026, 5, 14)
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=index_date,
                index_series="KOSPI",
                index_class="대표지수",
                index_name="코스피",
                close_index=7844.01,
                change_percent=2.63,
                fetched_at=datetime(2026, 5, 14, 8, 10, 0),
            ),
            MarketIndexDailySnapshot(
                business_date=index_date,
                index_series="KOSDAQ",
                index_class="대표지수",
                index_name="코스닥",
                close_index=1176.93,
                change_percent=-0.20,
                fetched_at=datetime(2026, 5, 14, 8, 10, 0),
            ),
        ]
    )

    exit_code = _run_market_briefing(
        config,
        repository,
        explicit_date=briefing_date,
        limit=5,
        send=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "26.05.13 기준 KOSPI 상승, KOSDAQ 보합권 흐름" in output
    assert "추천" not in output
    assert "점수" not in output


def test_web_view_value_qa_collects_invalid_display_values() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "stock_display_name": "N/A",
            "raw_value": "N/A",
            "invalid_number": float("nan"),
        },
        path="daily",
        issues=issues,
        warnings=warnings,
    )

    assert {issue["code"] for issue in issues} == {"display_na", "invalid_number"}
    assert not any(issue["path"] == "daily.raw_value" for issue in issues)


def test_fill_daily_summary_quote_metadata_fallbacks_uses_stored_sector_when_quote_missing(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="24",
            sector_name="반도체와반도체장비",
            updated_at=datetime(2026, 5, 13, 16, 0, 0),
        )
    )
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 5, 13),
            stock_name="삼성전자",
            stock_code="005930",
            mention_count=4,
            broker_display="NH투자증권(4)",
            target_price_min=280_000,
            target_price_max=320_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 13, 16, 0, 0),
        )
    ]

    quotes = _fill_daily_summary_quote_metadata_fallbacks(repository, summaries, {})

    assert quotes["005930"].stock_name == "삼성전자"
    assert quotes["005930"].sector_name == "반도체와반도체장비"
    assert quotes["005930"].current_price is None


def test_web_view_value_qa_flags_missing_display_markers_beyond_na() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "sector_display_name": "NULL",
            "theme_display": "NA",
            "stock_display_name": "NONE",
            "price_display": "-",
            "title_display": " ",
        },
        path="daily",
        issues=issues,
        warnings=warnings,
    )

    assert [issue["path"] for issue in issues] == [
        "daily.sector_display_name",
        "daily.theme_display",
        "daily.stock_display_name",
        "daily.price_display",
        "daily.title_display",
    ]


def test_web_view_value_qa_flags_placeholder_time_in_display_fields() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "published_label": "2026-05-08 00:00",
            "published_at": "2026-05-08T00:00:00",
        },
        path="stock.reports[0]",
        issues=issues,
        warnings=warnings,
    )

    assert [issue["code"] for issue in issues] == ["display_placeholder_time"]
    assert [issue["path"] for issue in issues] == ["stock.reports[0].published_label"]


def test_web_view_value_qa_flags_public_observation_internal_or_decision_terms() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "rows": [
                {
                    "evidence_notes": ["리포트 2건", "prototype_value=3"],
                    "visible_label": "추천 후보",
                    "notice": "추천 판단은 포함하지 않습니다.",
                    "score_notice": "점수와 추천은 포함하지 않습니다.",
                    "grade_notice": "등급 아님",
                    "entry_notice": "entry price and conviction",
                }
            ]
        },
        path="observation",
        issues=issues,
        warnings=warnings,
    )

    assert [issue["code"] for issue in issues] == [
        "public_observation_internal_value",
        "public_observation_decision_wording",
        "public_observation_decision_wording",
        "public_observation_decision_wording",
        "public_observation_decision_wording",
        "public_observation_decision_wording",
    ]
    assert [issue["path"] for issue in issues] == [
        "observation.rows[0].evidence_notes[1]",
        "observation.rows[0].visible_label",
        "observation.rows[0].notice",
        "observation.rows[0].score_notice",
        "observation.rows[0].grade_notice",
        "observation.rows[0].entry_notice",
    ]


def test_web_view_value_qa_flags_public_dto_admin_keys() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "surface": "web-view",
            "read_only": True,
            "scheduler_tasks": [],
            "worker_states": {},
            "nested": {
                "db_path": "data/stock_monitor.db",
                "safe_settings": {},
                "operation_profile": "desktop-validation",
            },
        },
        path="daily",
        issues=issues,
        warnings=warnings,
    )

    assert [issue["code"] for issue in issues] == [
        "public_dto_admin_key",
        "public_dto_admin_key",
        "public_dto_admin_key",
        "public_dto_admin_key",
        "public_dto_admin_key",
    ]
    assert [issue["path"] for issue in issues] == [
        "daily.scheduler_tasks",
        "daily.worker_states",
        "daily.nested.db_path",
        "daily.nested.safe_settings",
        "daily.nested.operation_profile",
    ]


def test_web_view_value_qa_flags_static_html_public_copy_regressions() -> None:
    issues: list[dict] = []

    cli_module._collect_web_view_static_html_copy_issues(
        """
        <span>read-only</span>
        <section>관찰 후보 근거</section>
        <section>리포트 후 반응 관찰</section>
        <section>선택 상태</section>
        <table><thead><tr><th>D+1</th><th>D+5</th><th>D+10</th><th>D+20</th></tr></thead></table>
        <td colspan="8">검증표</td>
        <p>선택 날짜 KRX 마감값 없음</p>
        <p>추천/점수 아님</p>
        <p>추천 순위</p>
        <p>추천이나 매수/매도</p>
        """,
        issues=issues,
    )

    assert [issue["code"] for issue in issues] == [
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_internal_copy",
        "public_html_decision_wording",
        "public_html_decision_wording",
        "public_html_decision_wording",
    ]
    assert [issue["path"] for issue in issues] == [
        "web_view_html.read-only",
        "web_view_html.관찰 후보 근거",
        "web_view_html.리포트 후 반응 관찰",
        "web_view_html.선택 상태",
        "web_view_html.D+ reaction columns",
        "web_view_html.8-column observation table",
        "web_view_html.선택 날짜 KRX 마감값 없음",
        "web_view_html.추천/점수 아님",
        "web_view_html.추천 순위",
        "web_view_html.추천이나 매수/매도",
    ]


def test_web_view_value_qa_flags_static_html_generic_decision_wording() -> None:
    issues: list[dict] = []

    cli_module._collect_web_view_static_html_copy_issues(
        """
        <p>추천 판단은 포함하지 않습니다.</p>
        <p>점수 없이 참고하세요.</p>
        <p>등급 없음.</p>
        <p>매수 후보가 아닙니다.</p>
        <p>매도 신호가 아닙니다.</p>
        """,
        issues=issues,
    )

    assert [issue["code"] for issue in issues] == [
        "public_html_decision_wording",
        "public_html_decision_wording",
        "public_html_decision_wording",
        "public_html_decision_wording",
        "public_html_decision_wording",
    ]
    assert [issue["path"] for issue in issues] == [
        "web_view_html.추천",
        "web_view_html.점수",
        "web_view_html.등급",
        "web_view_html.매수 후보",
        "web_view_html.매도 신호",
    ]


def test_web_view_value_qa_flags_static_html_admin_surface_leaks() -> None:
    issues: list[dict] = []

    cli_module._collect_web_view_static_html_copy_issues(
        """
        <a href="/api/status">status</a>
        <a href="/api/scheduler">scheduler</a>
        <span>operator-settings</span>
        <span>admin-gui</span>
        <span>db_path</span>
        <span>.env</span>
        <span>Telegram token</span>
        <button>shutdown</button>
        """,
        issues=issues,
    )

    assert [issue["code"] for issue in issues] == [
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
        "public_html_admin_surface_leak",
    ]
    assert [issue["path"] for issue in issues] == [
        "web_view_html./api/status",
        "web_view_html./api/scheduler",
        "web_view_html.operator-settings",
        "web_view_html.admin-gui",
        "web_view_html.db_path",
        "web_view_html..env",
        "web_view_html.Telegram token",
        "web_view_html.shutdown",
    ]


def test_web_view_value_qa_static_html_current_template_is_public_safe() -> None:
    issues: list[dict] = []

    cli_module._collect_web_view_static_html_copy_issues(
        cli_module._render_web_view_html(),
        issues=issues,
    )

    assert issues == []


def test_web_view_value_qa_allows_source_report_title_decision_words() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "reports": [
                {
                    "title": "배당 매력 추천 구간",
                    "title_display": "배당 매력 추천 구간",
                }
            ]
        },
        path="stock[2026-05-14:030200]",
        issues=issues,
        warnings=warnings,
    )

    assert issues == []


def test_web_view_value_qa_blocks_raw_won_turnover_display_in_market_briefing() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "market_briefing": {
                "turnover_summary": {
                    "markets": [
                        {
                            "market": "KOSPI",
                            "items": [
                                {
                                    "stock_name": "SK하이닉스",
                                    "turnover": 11_875_492_405_612,
                                    "turnover_display": "11,875,492,405,612원",
                                }
                            ],
                        }
                    ]
                }
            }
        },
        path="daily[2026-05-14]",
        issues=issues,
        warnings=warnings,
    )

    assert [issue["code"] for issue in issues] == ["public_market_briefing_raw_turnover_display"]


def test_web_view_value_qa_warns_on_category_mapping_fallback() -> None:
    issues: list[dict] = []
    warnings: list[dict] = []

    _collect_web_view_value_qa_issues(
        {
            "category_contract": {
                "mapping_basis": "latest_mapping_fallback",
                "notice": "선택 날짜 이전의 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다.",
            }
        },
        path="daily[2026-05-07]",
        issues=issues,
        warnings=warnings,
    )

    assert issues == []
    assert warnings == [
        {
            "code": "category_mapping_fallback",
            "path": "daily[2026-05-07].category_contract.mapping_basis",
            "message": "selected date uses latest stored category classification instead of a source-date snapshot",
        }
    ]


def test_web_view_value_qa_json_is_read_only(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 8),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "web-view-value-qa"
    assert payload["read_only"] is True
    assert payload["dates"] == ["2026-05-08"]
    assert payload["scanned_surfaces"] == [
        "static_html",
        "archive",
        "market",
        "rotation_alias_mapping",
        "rotation_etf_mapping",
        "daily",
        "candidate_evidence",
        "backtest_observation",
        "intraday",
        "category",
        "category_trend",
        "flow_trend",
        "etf_trend",
        "rotation_overlay",
        "stock_detail",
    ]
    assert "issues" in payload
    assert "warnings" in payload


def test_web_view_value_qa_fails_when_active_rotation_etf_mapping_has_no_snapshot(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.rotation_overlay_coordinates_path.parent.mkdir(parents=True, exist_ok=True)
    (config.rotation_overlay_coordinates_path.parent / "rotation_etf_candidates.json").write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "category_type": "sector",
                        "category_display_name": "반도체와반도체장비",
                        "status": "active",
                        "etf_codes": ["396500", "999999"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="396500",
                etf_name="TIGER 반도체TOP10",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
                close_price=20_000,
            )
        ]
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 8),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert "rotation_etf_mapping" in payload["scanned_surfaces"]
    assert {
        "code": "rotation_etf_mapping_missing_snapshot",
        "path": "rotation_etf_candidates[sector:반도체와반도체장비].999999",
        "message": "active rotation ETF mapping code has no stored ETF snapshot on 2026-05-08",
    } in payload["issues"]


def test_web_view_value_qa_fails_when_active_rotation_etf_mapping_is_unreachable(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.rotation_overlay_coordinates_path.parent.mkdir(parents=True, exist_ok=True)
    config.rotation_overlay_coordinates_path.write_text(
        json.dumps(
            {
                "image": {"path": "example/Cycle.jpg", "width": 1376, "height": 768},
                "coordinates": [
                    {"display_name": "반도체와반도체장비", "x": 490, "y": 210, "radius": 58, "label": "반도체"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_etf_candidates.json").write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "category_type": "sector",
                        "category_display_name": "바이오",
                        "status": "active",
                        "etf_codes": ["396500"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="396500",
                etf_name="TIGER 반도체TOP10",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
                close_price=20_000,
            )
        ]
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 8),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert {
        "code": "rotation_etf_mapping_unreachable_category",
        "path": "rotation_etf_candidates[sector:바이오]",
        "message": "active rotation ETF mapping has no overlay coordinate or active alias for this category",
    } in payload["issues"]


def test_web_view_value_qa_fails_when_active_rotation_alias_has_no_coordinate(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.rotation_overlay_coordinates_path.parent.mkdir(parents=True, exist_ok=True)
    config.rotation_overlay_coordinates_path.write_text(
        json.dumps(
            {
                "image": {"path": "example/Cycle.jpg", "width": 1376, "height": 768},
                "coordinates": [
                    {"display_name": "반도체와반도체장비", "x": 490, "y": 210, "radius": 58, "label": "반도체"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_image_aliases.json").write_text(
        json.dumps(
            {
                "aliases": [
                    {
                        "rotation_label": "우주항공",
                        "category_type": "sector",
                        "category_display_name": "우주항공과국방",
                        "coordinate_display_name": "없는좌표",
                        "status": "active",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 8),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert {
        "code": "rotation_alias_missing_coordinate",
        "path": "rotation_image_aliases[sector:우주항공과국방].coordinate_display_name",
        "message": "active rotation alias points to a missing overlay coordinate: 없는좌표",
    } in payload["issues"]


def test_rotation_mapping_audit_reports_alias_etf_and_stored_evidence(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.rotation_overlay_coordinates_path.parent.mkdir(parents=True, exist_ok=True)
    cycle_path = tmp_path / "example" / "Cycle.jpg"
    cycle_path.parent.mkdir(parents=True, exist_ok=True)
    cycle_path.write_bytes(b"fake-image")
    config.rotation_overlay_coordinates_path.write_text(
        json.dumps(
            {
                "image": {"path": "example/Cycle.jpg", "width": 1376, "height": 768},
                "coordinates": [
                    {"display_name": "반도체와반도체장비", "x": 490, "y": 210, "radius": 58, "label": "반도체"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_image_aliases.json").write_text(
        json.dumps(
            {
                "aliases": [
                    {
                        "rotation_label": "반도체",
                        "category_type": "sector",
                        "category_display_name": "반도체와반도체장비",
                        "coordinate_display_name": "반도체와반도체장비",
                        "status": "active",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config.rotation_overlay_coordinates_path.parent / "rotation_etf_candidates.json").write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "category_type": "sector",
                        "category_display_name": "반도체와반도체장비",
                        "status": "active",
                        "etf_codes": ["396500"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 8),
                etf_code="396500",
                etf_name="TIGER 반도체TOP10",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
                close_price=20_000,
            )
        ]
    )

    exit_code = _run_rotation_mapping_audit(
        config,
        repository,
        business_date=date(2026, 5, 8),
        limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "rotation-mapping-audit"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is False
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["coordinate_count"] == 1
    assert payload["active_alias_count"] == 1
    assert payload["active_etf_mapping_count"] == 1
    assert payload["issue_count"] == 0
    row = payload["coordinates"][0]
    assert row["coordinate_display_name"] == "반도체와반도체장비"
    assert row["review_status"] == "mapped_with_etf"
    assert row["category_keys"] == ["sector:반도체와반도체장비"]
    assert row["etf_codes"] == ["396500"]
    assert row["stored_etf_count"] == 1


def test_web_view_value_qa_scans_all_public_web_view_surfaces(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(cli_module, "_render_web_view_html", lambda: "<html></html>")
    monkeypatch.setattr(
        cli_module,
        "build_web_view_archive_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "scheduler_tasks": []},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_daily_snapshot",
        lambda *_args, **_kwargs: {
            "surface": "web-view",
            "report_count": 0,
            "stocks": [],
            "sector_rollups": [{"category_type": "sector", "display_name": "반도체"}],
            "theme_rollups": [{"category_type": "theme", "display_name": "AI"}],
        },
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_candidate_evidence_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "rows": []},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_backtest_observation_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "rows": []},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_intraday_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "health": {}},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_category_detail_snapshot",
        lambda *_args, category_type, **_kwargs: {
            "surface": "web-view",
            "category_type": category_type,
            "recent_admin_audit_logs": [],
        },
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_category_trend_snapshot",
        lambda *_args, category_type, **_kwargs: {
            "surface": "web-view",
            "category_type": category_type,
            "notification_default_limit": 7,
        },
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_market_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "worker_states": {}},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_flow_trend_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "db_path": "data/stock_monitor.db"},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_etf_trend_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "safe_settings": {}},
    )
    monkeypatch.setattr(
        cli_module,
        "build_web_view_rotation_overlay_snapshot",
        lambda *_args, **_kwargs: {"surface": "web-view", "operation_profile": "desktop-validation"},
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 8),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert [issue["path"] for issue in payload["issues"]] == [
        "archive.scheduler_tasks",
        "market.worker_states",
        "intraday[2026-05-08].health",
        "category[2026-05-08:sector:반도체].recent_admin_audit_logs",
        "category_trend[sector:반도체].notification_default_limit",
        "category[2026-05-08:theme:AI].recent_admin_audit_logs",
        "category_trend[theme:AI].notification_default_limit",
        "flow_trend[2026-05-08].db_path",
        "etf_trend[2026-05-08].safe_settings",
        "rotation_overlay[2026-05-08].operation_profile",
    ]


def test_web_view_value_qa_collapses_future_krx_missing_market_reference_warnings(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 13, 9, 0, 0),
                business_date=date(2026, 5, 13),
                collected_at=datetime(2026, 5, 13, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-future-1",
                identity_key="qa-future-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="리포트2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 13, 10, 0, 0),
                business_date=date(2026, 5, 13),
                collected_at=datetime(2026, 5, 13, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-future-2",
                identity_key="qa-future-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 13))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 12),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=90_000,
                fetched_at=datetime(2026, 5, 12, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 13),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["warning_count"] == 2
    assert {warning["code"] for warning in payload["warnings"]} == {
        "category_mapping_fallback",
        "krx_snapshot_not_yet_available",
    }
    assert not any(warning["code"] == "missing_market_reference" for warning in payload["warnings"])


def test_web_view_value_qa_fails_on_same_date_missing_market_reference(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-same-date-1",
                identity_key="qa-same-date-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="리포트2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 12, 10, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-same-date-2",
                identity_key="qa-same-date-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 12))
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=date(2026, 5, 12),
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="?쇱꽦?꾩옄",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 12, 20, 0, 0),
            )
        ]
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 12),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                close_price=90_000,
                fetched_at=datetime(2026, 5, 12, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 12),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["issues"][0]["code"] == "missing_market_reference"


def test_web_view_value_qa_warns_on_unresolved_stock_market_reference(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="UnresolvedCo",
                stock_code="351020",
                title="Unresolved report",
                broker_name="NH Investment",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-unresolved-1",
                identity_key="qa-unresolved-1",
            ),
            Report(
                stock_name="UnresolvedCo",
                stock_code="351020",
                title="Unresolved report",
                broker_name="KB Securities",
                published_at=datetime(2026, 5, 12, 10, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="qa-unresolved-2",
                identity_key="qa-unresolved-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 12))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 12),
                stock_code="005930",
                stock_name="?쇱꽦?꾩옄",
                market="KOSPI",
                close_price=90_000,
                fetched_at=datetime(2026, 5, 12, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_web_view_value_qa(
        config,
        repository,
        dates=(date(2026, 5, 12),),
        stock_limit=3,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["issue_count"] == 0
    assert any(warning["code"] == "unresolved_stock_market_reference" for warning in payload["warnings"])


def test_db_verify_fails_on_investor_flow_quality_issue(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    with repository.connect() as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO stock_investor_flow_daily (
                    business_date,
                    stock_code,
                    investor_type,
                    fetched_at,
                    source
                ) VALUES (
                    '2026-05-08',
                    'BAD',
                    '외국인',
                    '2026-05-08T16:50:00',
                    'krx_data_market'
                )
                """
            )

    exit_code = _run_db_verify(repository, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- investor-flow quality issues: 3" in output
    assert "stock_invalid_code: 1" in output
    assert "stock_missing_units: 1" in output
    assert "stock_no_numeric_flow: 1" in output


def test_observation_feature_audit_prints_read_only_coverage(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="audit-1",
                identity_key="audit-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="audit-2",
                identity_key="audit-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_feature_audit(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation feature availability audit" in output
    assert "- candidate rows: 1" in output
    assert "- base_market: 1/1" in output
    assert "- target_observation: 1/1" in output
    assert "- D+1 reaction: 1/1" in output
    assert "score" not in output.lower()


def test_observation_feature_audit_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_feature_audit(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["candidate_count"] == 0
    assert payload["feature_counts"]["base_market"] == 0


def test_observation_summary_audit_prints_recent_read_only_coverage(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="summary-audit-1",
                identity_key="summary-audit-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="summary-audit-2",
                identity_key="summary-audit-2",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="전회 목표가",
                broker_name="하나증권",
                published_at=datetime(2026, 5, 7, 10, 0, 0),
                business_date=date(2026, 5, 7),
                collected_at=datetime(2026, 5, 7, 10, 5, 0),
                target_price_value=90_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="summary-audit-previous",
                identity_key="summary-audit-previous",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8) - timedelta(days=index),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000 - index * 100,
                volume=10_000 - min(index, 19) * 10,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
            for index in range(130)
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_amount=1_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_amount=500,
                fetched_at=datetime(2026, 5, 7, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_summary_audit(
        repository,
        limit=5,
        to_date=date(2026, 5, 8),
        mention_threshold=1,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation summary feature coverage audit" in output
    assert "- 2026-05-08 | reports=2 stocks=1" in output
    assert "intensity=1/1" in output
    assert "target_revision=1/1" in output
    assert "flow=1/1" in output
    assert "persistence=1/1" in output
    assert "price_volume=1/1" in output
    assert "52w=1/1" in output
    assert "score" not in output.lower()


def test_observation_summary_audit_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_summary_audit(
        repository,
        limit=5,
        to_date=date(2026, 5, 8),
        mention_threshold=1,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["source"] == "stored_report_krx_observation_summary"
    assert payload["read_only"] is True
    assert payload["recommendation"] is False
    assert payload["recent_report_dates"] == 5
    assert payload["rows"] == []


def test_observation_summary_preview_prints_phone_readable_public_safe_message(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="summary-preview-1",
                identity_key="summary-preview-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="summary-preview-2",
                identity_key="summary-preview-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                volume=10_000,
                turnover=500_000_000_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_amount=1_000_000_000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_observation_summary_preview(
        config,
        repository,
        explicit_date=date(2026, 5, 8),
        limit=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "국장 관찰 요약 · 26.05.08" in output
    assert "시장 분위기" in output
    assert "리포트 집중" in output
    assert "수급 참고" in output
    assert "과열 참고" in output
    assert "삼성전자 / 리포트 2건" in output
    assert "외국인 순유입 10억" in output
    assert "추천" not in output
    assert "점수" not in output
    assert "등급" not in output


def test_observation_summary_preview_json_uses_latest_report_date(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                source_id="summary-preview-json-1",
                identity_key="summary-preview-json-1",
            )
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))

    exit_code = _run_observation_summary_preview(
        config,
        repository,
        explicit_date=None,
        limit=2,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["business_date"] == "2026-05-08"
    assert payload["read_only"] is True
    assert payload["live_fetch"] is False
    assert payload["recommendation"] is False
    assert "국장 관찰 요약" in payload["message"]


def test_observation_reaction_distribution_prints_grouped_read_only_distribution(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="dist-1",
                identity_key="dist-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="dist-2",
                identity_key="dist-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_reaction_distribution(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation reaction distribution" in output
    assert "- candidate rows: 1" in output
    assert "coverage D+1: available=1/1 missing=0 (100.0%) | complete_window | no missing D+1 window" in output
    assert "coverage D+5: available=0/1 missing=1 (0.0%) | no_completed_window | 1 missing D+5 window(s)" in output
    assert "D+1 | mention=2 | target=yes | flow=no" in output
    assert "avg=10.0%" in output
    assert "score" not in output.lower()


def test_observation_reaction_distribution_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_reaction_distribution(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["candidate_count"] == 0
    assert payload["horizon_coverage"] == []
    assert payload["groups"] == []
    assert payload["read_only"] is True


def test_observation_reaction_distribution_defaults_to_stored_summary_range(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="default-dist-1",
                identity_key="default-dist-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 12, 10, 0, 0),
                business_date=date(2026, 5, 12),
                collected_at=datetime(2026, 5, 12, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="default-dist-2",
                identity_key="default-dist-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.rebuild_daily_summaries(date(2026, 5, 12))

    exit_code = _run_observation_reaction_distribution(
        repository,
        from_date=None,
        to_date=None,
        mention_threshold=1,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["from_date"] == "2026-05-08"
    assert payload["to_date"] == "2026-05-12"
    assert payload["read_only"] is True
    assert payload["scoring"] is False
    assert payload["recommendation"] is False


def test_observation_feature_comparison_prints_read_only_feature_groups(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="cmp-1",
                identity_key="cmp-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="cmp-2",
                identity_key="cmp-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_feature_comparison(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation feature comparison" in output
    assert "- candidate rows: 1" in output
    assert "D+1 | target_available=yes" in output
    assert "avg=10.0%" in output
    assert "score" not in output.lower()


def test_observation_feature_comparison_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_feature_comparison(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["candidate_count"] == 0
    assert payload["groups"] == []
    assert payload["read_only"] is True


def test_observation_weight_draft_prints_internal_only_proposals(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="weight-1",
                identity_key="weight-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="weight-2",
                identity_key="weight-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_weight_draft(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        min_sample_size=1,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation internal weight draft" in output
    assert "- internal-only: true" in output
    assert "- public decision: false" in output
    assert "D+1 | target_available=yes" in output
    assert "draft_weight=0" in output
    assert "recommend" not in output.lower()


def test_observation_weight_draft_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_weight_draft(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        min_sample_size=20,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["internal_only"] is True
    assert payload["public_decision"] is False
    assert payload["proposals"] == []


def test_observation_hidden_score_prototype_prints_internal_values_without_ranking(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 9, 5, 0),
                target_price_value=100_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="hidden-1",
                identity_key="hidden-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="업황 회복 2",
                broker_name="KB증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                business_date=date(2026, 5, 8),
                collected_at=datetime(2026, 5, 8, 10, 5, 0),
                target_price_value=110_000,
                opinion_normalized=Opinion.BUY.value,
                source_id="hidden-2",
                identity_key="hidden-2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 11),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=110_000,
                turnover=700,
                fetched_at=datetime(2026, 5, 11, 20, 0, 0),
            ),
        ]
    )

    exit_code = _run_observation_hidden_score_prototype(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        horizon_days=1,
        min_sample_size=1,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Observation hidden internal prototype" in output
    assert "- internal-only: true" in output
    assert "- public decision: false" in output
    assert "prototype_value=" in output
    assert "rank=" not in output
    assert "recommend" not in output.lower()


def test_observation_hidden_score_prototype_json_is_machine_readable(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_hidden_score_prototype(
        repository,
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        horizon_days=20,
        min_sample_size=20,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["internal_only"] is True
    assert payload["public_decision"] is False
    assert payload["rows"] == []


def test_observation_hidden_score_prototype_accepts_train_apply_ranges(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_hidden_score_prototype(
        repository,
        train_from_date=date(2026, 1, 2),
        train_to_date=date(2026, 5, 7),
        from_date=date(2026, 5, 8),
        to_date=date(2026, 5, 8),
        mention_threshold=2,
        horizon_days=20,
        min_sample_size=20,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["train_from_date"] == "2026-01-02"
    assert payload["train_to_date"] == "2026-05-07"
    assert payload["from_date"] == "2026-05-08"
    assert payload["to_date"] == "2026-05-08"


def test_observation_hidden_holdout_validation_json_is_internal_only(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_hidden_holdout_validation(
        repository,
        train_from_date=date(2026, 1, 2),
        train_to_date=date(2026, 5, 7),
        holdout_from_date=date(2026, 5, 8),
        holdout_to_date=date(2026, 5, 12),
        mention_threshold=2,
        horizon_days=20,
        min_sample_size=20,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["internal_only"] is True
    assert payload["public_decision"] is False
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["buckets"] == []


def test_observation_hidden_holdout_rejects_overlapping_train_and_holdout_ranges(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    try:
        _run_observation_hidden_holdout_validation(
            repository,
            train_from_date=date(2026, 1, 2),
            train_to_date=date(2026, 5, 8),
            holdout_from_date=date(2026, 5, 8),
            holdout_to_date=date(2026, 5, 12),
            mention_threshold=2,
            horizon_days=20,
            min_sample_size=20,
            as_json=True,
        )
    except ValueError as exc:
        assert "holdout range must start after train range" in str(exc)
    else:
        raise AssertionError("overlapping train/holdout ranges should fail")


def test_observation_hidden_rejects_unknown_excluded_feature(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    try:
        _run_observation_hidden_score_prototype(
            repository,
            from_date=date(2026, 5, 8),
            to_date=date(2026, 5, 8),
            mention_threshold=2,
            horizon_days=20,
            min_sample_size=20,
            excluded_features=("typo_feature",),
            as_json=True,
        )
    except ValueError as exc:
        assert "Unknown exclude feature" in str(exc)
    else:
        raise AssertionError("unknown exclude feature should fail")


def test_observation_hidden_holdout_sweep_json_is_internal_only(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    exit_code = _run_observation_hidden_holdout_sweep(
        repository,
        train_from_date=date(2026, 1, 2),
        train_to_date=date(2026, 4, 30),
        holdout_from_date=date(2026, 5, 1),
        holdout_to_date=date(2026, 5, 12),
        mention_threshold=2,
        horizon_days=(5, 20),
        min_sample_size=20,
        window_days=5,
        excluded_features=("target_progress_caution",),
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["internal_only"] is True
    assert payload["public_decision"] is False
    assert payload["scoring"] is False
    assert payload["recommendation"] is False
    assert payload["horizon_days"] == [5, 20]
    assert payload["excluded_features"] == ["target_progress_caution"]


def test_db_verify_fails_on_orphan_category_snapshot(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    with repository.connect() as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO category_membership_snapshots (
                    snapshot_date,
                    category_type,
                    category_key,
                    display_name,
                    stock_code,
                    stock_name,
                    fetched_at,
                    source
                ) VALUES (
                    '2026-05-08',
                    'theme',
                    'missing-theme',
                    '미등록테마',
                    '005930',
                    '삼성전자',
                    '2026-05-08T16:50:00',
                    'test'
                )
                """
            )

    exit_code = _run_db_verify(repository, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- category quality issues: 1" in output
    assert "orphan_membership_snapshots: 1" in output


def test_db_verify_reports_category_snapshot_refreshability_warning(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, Report

    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    business_date = date(2026, 5, 7)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체",
                broker_name="A증권",
                published_at=datetime.combine(business_date, fetched_at.time()),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [CategoryCatalogItem("sector", "31", "IT서비스", "naver_quote", True, fetched_at)]
    )

    exit_code = _run_db_verify(repository, as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["category_snapshot_refreshability"]["fallback_date_count"] == 1
    assert payload["category_snapshot_refreshability"]["refreshable_sector_catalog_count"] == 0
    assert payload["category_snapshot_refreshability"]["warnings"] == [
        {
            "code": "sector_catalog_not_refreshable",
            "message": "sector fallback dates exist but no enabled sector catalog entry is verified as a Naver upjong source",
        }
    ]


def test_db_verify_fails_on_intraday_batch_report_orphan(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    with repository.connect() as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO intraday_alert_batch_reports (batch_id, report_identity_key)
                VALUES ('missing-batch', 'missing-report')
                """
            )

    exit_code = _run_db_verify(repository, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- orphan intraday batch reports: 1" in output


def test_db_verify_fails_on_partial_krx_daily_snapshot(tmp_path, capsys) -> None:
    from stock_monitor.models import EtfDailySnapshot

    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=datetime(2026, 5, 8).date(),
                etf_code="069500",
                etf_name="KODEX 200",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            )
        ]
    )

    exit_code = _run_db_verify(repository, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- partial KRX daily snapshot dates: 1" in output
    assert "2026-05-08: missing etf-daily, stock-kospi-daily" in output


def test_db_backup_creates_consistent_sqlite_copy(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_db_backup(
        config,
        repository,
        tag="pre-test",
        output_dir=tmp_path / "backups",
        verify=True,
    )

    output = capsys.readouterr().out
    backups = list((tmp_path / "backups").glob("stock_monitor_*_pre-test.db"))
    assert exit_code == 0
    assert len(backups) == 1
    assert backups[0].stat().st_size > 0
    assert "Database backup created:" in output
    assert "- integrity_check: ok" in output


def test_db_restore_smoke_verifies_backup_copy_without_retaining_it(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    assert _run_db_backup(
        config,
        repository,
        tag="restore-source",
        output_dir=tmp_path / "backups",
        verify=True,
    ) == 0
    backup_path = next((tmp_path / "backups").glob("stock_monitor_*_restore-source.db"))
    capsys.readouterr()

    exit_code = _run_db_restore_smoke(
        config,
        backup_path=backup_path,
        work_dir=tmp_path / "restore-smoke",
        keep_copy=False,
        audit_repository=repository,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Database restore smoke" in output
    assert "- integrity_check: ok" in output
    assert "- copy_retained: N" in output
    assert list((tmp_path / "restore-smoke").glob("restore_smoke_*.db")) == []
    events = repository.list_recent_operation_events(limit=1)
    assert events[0].component == "db"
    assert events[0].event_type == "restore-smoke"
    assert events[0].status == "success"
    assert f"backup={backup_path.name}" in str(events[0].detail)


def test_run_api_perf_summary_reads_jsonl_log(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_path = log_dir / "api_perf.log"
    log_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-05-20T10:00:00+09:00","method":"GET","path":"/api/daily/2026-05-19","status":200,"total_ms":120,"db_ms":70,"build_ms":100,"json_ms":12,"bytes":2000,"cache":"miss","gzip":true}',
                '{"ts":"2026-05-20T10:00:01+09:00","method":"GET","path":"/api/daily/2026-05-19","status":200,"total_ms":8,"db_ms":0,"build_ms":0,"json_ms":0,"bytes":600,"cache":"hit","gzip":true}',
            ]
        ),
        encoding="utf-8",
    )

    assert cli_module._run_api_perf_summary(config, log_path=log_path, as_json=True) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "api-perf-summary"
    assert payload["record_count"] == 2
    assert payload["endpoints"][0]["path"] == "/api/daily/2026-05-19"
    assert payload["endpoints"][0]["cache_hits"] == 1
    assert payload["endpoints"][0]["cache_misses"] == 1


def test_db_vacuum_dry_run_previews_without_confirm(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_db_vacuum(config, repository, dry_run=True, confirm=False)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would run SQLite VACUUM." in output
    assert "- allocated:" in output
    assert "- reclaimable:" in output


def test_db_vacuum_requires_confirm_for_real_run(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_db_vacuum(config, repository, dry_run=False, confirm=False)

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to run VACUUM without --confirm" in output


def test_db_vacuum_confirm_records_operation_event(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_db_vacuum(config, repository, dry_run=False, confirm=True)

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert "SQLite VACUUM completed." in output
    assert events[0].component == "db-vacuum"
    assert events[0].event_type == "vacuum"
    assert events[0].status == "success"


def test_db_backup_prune_requires_confirm_for_delete(tmp_path, capsys) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for index in range(3):
        path = backup_dir / f"stock_monitor_2026050{index}_1600_test.db"
        path.write_text("backup", encoding="utf-8")

    exit_code = _run_db_backup_prune(
        RuntimeConfig.from_env(root_dir=tmp_path),
        keep=1,
        dry_run=False,
        confirm=False,
        backup_dir=backup_dir,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to prune backups without --confirm" in output
    assert len(list(backup_dir.glob("stock_monitor_*.db"))) == 3


def test_db_backup_prune_dry_run_lists_delete_targets(tmp_path, capsys) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for index in range(3):
        path = backup_dir / f"stock_monitor_2026050{index}_1600_test.db"
        path.write_text("backup", encoding="utf-8")

    exit_code = _run_db_backup_prune(
        RuntimeConfig.from_env(root_dir=tmp_path),
        keep=1,
        dry_run=True,
        confirm=False,
        backup_dir=backup_dir,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would delete 2 backup file(s)." in output
    assert len(list(backup_dir.glob("stock_monitor_*.db"))) == 3


def test_db_cleanup_dry_run_lists_krx_snapshot_delete_targets(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import StockMarketDailySnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=datetime(2026, 1, 1).date(),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_db_cleanup(
        config,
        repository,
        retention_days=90,
        today=datetime(2026, 5, 9).date(),
        dry_run=True,
        confirm=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would delete 1 KRX snapshot row(s)." in output
    assert "- cutoff: business_date < 2026-02-08" in output
    assert "reports, daily_stock_summaries" in output
    assert repository.count_krx_snapshots_before(datetime(2026, 2, 8).date())["stock_market_daily"] == 1


def test_db_cleanup_dry_run_can_emit_json_payload(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import StockMarketDailySnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=datetime(2026, 1, 1).date(),
                stock_code="005930",
                stock_name="?쇱꽦?꾩옄",
                market="KOSPI",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_db_cleanup(
        config,
        repository,
        retention_days=90,
        today=datetime(2026, 5, 9).date(),
        dry_run=True,
        confirm=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["writes_database"] is False
    assert payload["mode"] == "dry_run"
    assert payload["cutoff_date"] == "2026-02-08"
    assert payload["total_row_count"] == 1
    assert payload["affected_tables"]["stock_market_daily"] == 1
    assert "reports" in payload["protected_tables"]


def test_db_cleanup_requires_confirm_for_delete(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import StockMarketDailySnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=datetime(2026, 1, 1).date(),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            )
        ]
    )

    exit_code = _run_db_cleanup(
        config,
        repository,
        retention_days=90,
        today=datetime(2026, 5, 9).date(),
        dry_run=False,
        confirm=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to cleanup KRX snapshots without --confirm" in output
    assert repository.count_krx_snapshots_before(datetime(2026, 2, 8).date())["stock_market_daily"] == 1


def test_krx_dry_run_prints_endpoint_summary(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=1,
            field_keys=("BAS_DD", "ISU_CD"),
            rows=({"BAS_DD": "20260507", "ISU_CD": "005930"},),
            first_row={"BAS_DD": "20260507", "ISU_CD": "005930"},
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = cli_module._run_krx_dry_run(
        config,
        endpoint_selector="stock-kospi-daily",
        business_date=datetime(2026, 5, 7).date(),
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX dry-run date: 2026-05-07" in output
    assert "stock-kospi-daily | 유가증권 일별매매정보 | rows=1" in output
    assert "fields=BAS_DD, ISU_CD" in output


def test_krx_fetch_snapshot_dry_run_prints_parsed_counts(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints
    from stock_monitor.db.repository import StockMonitorRepository

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=1,
            field_keys=("BAS_DD", "ISU_CD", "ISU_NM", "MKT_NM"),
            rows=(
                {
                    "BAS_DD": "20260507",
                    "ISU_CD": "005930",
                    "ISU_NM": "삼성전자",
                    "MKT_NM": "KOSPI",
                    "TDD_CLSPRC": "100000",
                },
            ),
            first_row={"BAS_DD": "20260507", "ISU_CD": "005930"},
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = cli_module._run_krx_fetch_snapshot(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        business_date=datetime(2026, 5, 7).date(),
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would upsert KRX snapshots for 2026-05-07." in output
    assert "- stock_market_daily: 1" in output
    assert "- etf_daily_snapshots: 0" in output


def test_krx_fetch_snapshot_records_empty_status_when_no_rows(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=0,
            field_keys=(),
            rows=(),
            first_row=None,
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = cli_module._run_krx_fetch_snapshot(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        business_date=datetime(2026, 5, 15).date(),
        dry_run=False,
    )

    output = capsys.readouterr().out
    event = repository.list_recent_operation_events(limit=1)[0]
    assert exit_code == 0
    assert "No parsed KRX rows were stored for 2026-05-15." in output
    assert event.component == "krx"
    assert event.event_type == "fetch-snapshot"
    assert event.status == "empty"
    assert "endpoint=stock-kospi-daily" in event.detail
    assert "rows=0" in event.detail


def test_krx_backfill_missing_records_empty_when_endpoints_still_incomplete(
    tmp_path, monkeypatch, capsys
) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=0,
            field_keys=(),
            rows=(),
            first_row=None,
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=1,
        to_date=datetime(2026, 5, 15).date(),
        max_dates=1,
        sleep_seconds=0,
        confirm=True,
        backup_confirmed=True,
        allow_large_batch=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=2)
    assert exit_code == 0
    assert "Completed KRX backfill: dates=1, endpoints=1, incomplete_endpoints=1." in output
    assert events[0].event_type == "backfill-missing"
    assert events[0].status == "empty"
    assert "incomplete_endpoints=1" in events[0].detail
    assert events[1].event_type == "fetch-snapshot"
    assert events[1].status == "empty"


def test_krx_openapi_availability_probe_records_endpoint_evidence_and_previous_delta(
    tmp_path, monkeypatch, capsys
) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    business_date = date(2026, 5, 15)
    fetched_at = datetime(2026, 5, 15, 1, 10, 0)
    repository.record_operation_event(
        cli_module._operation_event(
            config,
            component="krx",
            event_type="openapi-availability-probe",
            status="empty_rows",
            business_date=business_date,
            detail=json.dumps(
                {
                    "endpoint": "stock-kospi-daily",
                    "raw_row_count": 0,
                    "parsed_row_count": 0,
                    "stored": False,
                },
                ensure_ascii=False,
            ),
        )
    )

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=1,
            field_keys=("BAS_DD", "ISU_CD", "ISU_NM", "ISU_ABBRV", "MKT_NM"),
            rows=(
                {
                    "BAS_DD": "20260515",
                    "ISU_CD": "005930",
                    "ISU_NM": "삼성전자",
                    "ISU_ABBRV": "삼성전자",
                    "MKT_NM": "KOSPI",
                    "TDD_CLSPRC": "70000",
                    "ACC_TRDVOL": "1000",
                    "ACC_TRDVAL": "70000000",
                },
            ),
            first_row={
                "BAS_DD": "20260515",
                "ISU_CD": "005930",
                "ISU_NM": "삼성전자",
                "ISU_ABBRV": "삼성전자",
                "MKT_NM": "KOSPI",
            },
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)
    monkeypatch.setattr(cli_module, "datetime", _KrxDailyBackfillAllowedDateTime)

    exit_code = cli_module._run_krx_openapi_availability_probe(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        business_date=business_date,
        dry_run=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    events = [
        event
        for event in repository.list_recent_operation_events(limit=5)
        if event.event_type == "openapi-availability-probe" and event.status == "available"
    ]
    event_detail = json.loads(events[0].detail or "{}")
    assert exit_code == 0
    assert payload["surface"] == "krx-openapi-availability-probe"
    assert payload["writes_snapshot_tables"] is False
    assert payload["records_operation_event"] is True
    assert payload["target_business_date"] == "2026-05-15"
    assert payload["summary"]["available_count"] == 1
    assert payload["endpoints"][0]["endpoint"] == "stock-kospi-daily"
    assert payload["endpoints"][0]["raw_row_count"] == 1
    assert payload["endpoints"][0]["parsed_row_count"] == 1
    assert payload["endpoints"][0]["status"] == "available"
    assert payload["endpoints"][0]["reference_date"] == "2026-05-15"
    assert payload["endpoints"][0]["previous_probe"]["raw_row_count"] == 0
    assert payload["endpoints"][0]["previous_probe"]["raw_row_delta"] == 1
    assert events[0].component == "krx"
    assert events[0].event_type == "openapi-availability-probe"
    assert events[0].status == "available"
    assert event_detail["endpoint"] == "stock-kospi-daily"
    assert event_detail["stored"] is False
    assert event_detail["previous_probe"]["raw_row_delta"] == 1


def test_krx_openapi_availability_probe_dry_run_does_not_record_event(
    tmp_path, monkeypatch, capsys
) -> None:
    from stock_monitor.fetch.krx_api import KrxDryRunResult, resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    def fake_fetch(**kwargs) -> KrxDryRunResult:
        endpoint = kwargs["endpoint"]
        return KrxDryRunResult(
            endpoint=endpoint,
            business_date=kwargs["business_date"],
            row_count=0,
            field_keys=(),
            rows=(),
            first_row=None,
        )

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = cli_module._run_krx_openapi_availability_probe(
        config,
        repository,
        endpoint_selector="index-kospi-daily",
        business_date=date(2026, 5, 15),
        dry_run=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["records_operation_event"] is False
    assert payload["endpoints"][0]["status"] in {"empty_rows", "not_published"}
    assert repository.list_recent_operation_events(limit=1) == []


def test_krx_openapi_availability_probe_does_not_record_local_transport_block(
    tmp_path, monkeypatch, capsys
) -> None:
    from stock_monitor.fetch.krx_api import resolve_krx_endpoints

    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    def fake_fetch(**_kwargs):
        raise OSError("[WinError 10013] 액세스 권한에 의해 숨겨진 소켓에 액세스를 시도했습니다")

    monkeypatch.setattr(cli_module, "fetch_krx_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_endpoints", resolve_krx_endpoints)

    exit_code = cli_module._run_krx_openapi_availability_probe(
        config,
        repository,
        endpoint_selector="index-kospi-daily",
        business_date=date(2026, 5, 20),
        dry_run=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["records_operation_event"] is False
    assert payload["summary"]["transport_blocked_count"] == 1
    assert payload["summary"]["error_count"] == 0
    assert payload["endpoints"][0]["status"] == "transport_blocked"
    assert payload["endpoints"][0]["operation_event_stored"] is False
    assert payload["endpoints"][0]["excluded_from_provider_timeline"] is True
    assert repository.list_recent_operation_events(limit=1) == []


def test_krx_openapi_probe_summary_reports_first_available_slot(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    target_date = date(2026, 5, 20)

    rows = [
        ("2026-05-20T14:00:00+09:00", "stock-kospi-daily", "not_published", 0, 0, None),
        ("2026-05-20T14:00:00+09:00", "index-kospi-daily", "not_published", 0, 0, None),
        ("2026-05-20T16:00:00+09:00", "stock-kospi-daily", "partial", 100, 80, "2026-05-20"),
        ("2026-05-20T16:00:00+09:00", "index-kospi-daily", "available", 50, 50, "2026-05-20"),
        ("2026-05-20T16:01:00+09:00", "etf-daily", "error", 0, 0, None),
    ]
    for called_at, endpoint, status, raw_count, parsed_count, reference_date in rows:
        repository.record_operation_event(
            OperationEvent(
                event_time=datetime.fromisoformat(called_at),
                component="krx",
                event_type="openapi-availability-probe",
                status=status,
                business_date=target_date,
                detail=json.dumps(
                    {
                        "called_at": called_at,
                        "endpoint": endpoint,
                        "raw_row_count": raw_count,
                        "parsed_row_count": parsed_count,
                        "reference_date": reference_date,
                        "stored": False,
                        "error": (
                            "[WinError 10013] 액세스 권한에 의해 숨겨진 소켓에 액세스를 시도했습니다"
                            if status == "error"
                            else None
                        ),
                    },
                    ensure_ascii=False,
                ),
            )
        )

    payload = cli_module._build_krx_openapi_probe_summary(repository, business_date=target_date)

    assert payload["surface"] == "krx-openapi-probe-summary"
    assert payload["business_date"] == "2026-05-20"
    assert payload["slot_count"] == 2
    assert payload["ignored_status_counts"] == {"transport_blocked": 1}
    assert payload["first_data_slot_kst"] == "2026-05-20T16:00:00+09:00"
    assert payload["latest_slot"]["status_counts"] == {"partial": 1, "available": 1}
    assert payload["latest_slot"]["raw_row_count"] == 150
    assert payload["latest_slot"]["parsed_row_count"] == 130
    assert payload["not_published_until_kst"] == "2026-05-20T14:00:00+09:00"
    assert payload["writes_snapshot_tables"] is False


def test_krx_openapi_probe_summary_uses_filtered_events_beyond_recent_limit(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    target_date = date(2026, 5, 20)
    called_at = "2026-05-20T08:00:00+09:00"
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 20, 8, 0, 1),
            component="krx",
            event_type="openapi-availability-probe",
            status="not_published",
            business_date=target_date,
            detail=json.dumps(
                {
                    "called_at": called_at,
                    "endpoint": "stock-kospi-daily",
                    "raw_row_count": 0,
                    "parsed_row_count": 0,
                    "reference_date": None,
                    "stored": False,
                },
                ensure_ascii=False,
            ),
        )
    )
    for index in range(2100):
        repository.record_operation_event(
            OperationEvent(
                event_time=datetime(2026, 5, 21, 9, 0, 0),
                component="poll",
                event_type="manual-poll",
                status="success",
                business_date=date(2026, 5, 21),
                detail=f"noise={index}",
            )
        )

    payload = cli_module._build_krx_openapi_probe_summary(repository, business_date=target_date)

    assert payload["slot_count"] == 1
    assert payload["latest_slot"]["called_at"] == called_at
    assert payload["latest_slot"]["status_counts"] == {"not_published": 1}


def test_krx_probe_deltas_are_unavailable_for_transport_or_error_status() -> None:
    previous = {
        "called_at": "2026-05-20T10:10:00+09:00",
        "status": "not_published",
        "raw_row_count": 120,
        "parsed_row_count": 100,
        "reference_date": "2026-05-20",
    }

    enriched = cli_module._with_krx_probe_deltas(
        previous,
        raw_row_count=0,
        parsed_row_count=0,
        status="transport_blocked",
    )

    assert enriched is not None
    assert enriched["delta_unavailable"] is True
    assert enriched["raw_row_delta"] is None
    assert enriched["parsed_row_delta"] is None
    assert enriched["changed"] is False


def test_krx_openapi_availability_probe_text_reports_actual_recorded_events(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "dummy")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_endpoint(*_args, **_kwargs):
        return {
            "called_at": "2026-05-20T11:55:00+09:00",
            "target_business_date": "2026-05-20",
            "endpoint": "index-kospi-daily",
            "http_api_success": False,
            "raw_row_count": 0,
            "parsed_row_count": 0,
            "reference_date": None,
            "response_business_date": None,
            "stored": False,
            "operation_event_stored": False,
            "status": "transport_blocked",
            "transport_error": True,
            "excluded_from_provider_timeline": True,
            "previous_probe": None,
        }

    monkeypatch.setattr(cli_module, "_build_krx_openapi_availability_probe_endpoint", fake_endpoint)

    exit_code = cli_module._run_krx_openapi_availability_probe(
        config,
        repository,
        endpoint_selector="index-kospi-daily",
        business_date=date(2026, 5, 20),
        dry_run=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "- records_operation_event: false" in output
    assert "- operation_events_stored_count: 0" in output
    assert repository.list_recent_operation_events(limit=1) == []


def test_krx_openapi_availability_probe_recommends_current_backfill_window(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "dummy")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_endpoint(*_args, **_kwargs):
        return {
            "called_at": "2026-05-20T11:55:00+09:00",
            "target_business_date": "2026-05-20",
            "endpoint": "index-kospi-daily",
            "http_api_success": True,
            "raw_row_count": 0,
            "parsed_row_count": 0,
            "reference_date": None,
            "response_business_date": None,
            "stored": False,
            "operation_event_stored": False,
            "status": "not_published",
            "previous_probe": None,
        }

    monkeypatch.setattr(cli_module, "_build_krx_openapi_availability_probe_endpoint", fake_endpoint)

    assert (
        cli_module._run_krx_openapi_availability_probe(
            config,
            repository,
            endpoint_selector="index-kospi-daily",
            business_date=date(2026, 5, 20),
            dry_run=True,
            as_json=True,
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["scheduler_candidate"]["recommended_slots_kst"][0] == (
        "official next-business-day 08:00 KST publication"
    )
    assert payload["scheduler_candidate"]["registration_allowed"] is False


def test_run_ops_readiness_aggregates_operational_checks(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "_build_db_verify_payload",
        lambda _repository: {"integrity_check": "ok", "pending_migrations": [], "partial_krx_daily_snapshot_dates": []},
    )
    monkeypatch.setattr(cli_module, "_db_verify_payload_ready", lambda _payload: True)
    monkeypatch.setattr(
        cli_module,
        "_latest_krx_openapi_availability_probe",
        lambda _repository: {
            "ready": True,
            "latest_probe_at": "2026-05-20T17:09:54+09:00",
            "latest_status": "not_published",
            "latest_status_counts": {"not_published": 6},
            "latest_endpoint_count": 6,
            "latest_raw_row_count": 0,
            "latest_parsed_row_count": 0,
            "latest_reference_date": None,
        },
    )
    monkeypatch.setattr(
        cli_module,
        "_build_web_view_value_qa_payload",
        lambda *_args, **_kwargs: {
            "surface": "web-view-value-qa",
            "issue_count": 0,
            "warning_count": 1,
            "issues": [],
            "warnings": [{"code": "krx_snapshot_not_yet_available"}],
        },
    )
    monkeypatch.setattr(
        cli_module,
        "summarize_api_perf_log",
        lambda _path: {
            "surface": "api-perf-summary",
            "record_count": 2,
            "endpoint_count": 1,
            "endpoints": [{"path": "/api/daily/2026-05-20", "p95_total_ms": 120.0}],
        },
    )

    assert (
        cli_module._run_ops_readiness(
            config,
            repository,
            recent_business_days=4,
            stock_limit=20,
            api_perf_log_path=None,
            as_json=True,
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "ops-readiness"
    assert payload["ready"] is True
    assert payload["db_verify"]["ready"] is True
    assert payload["krx_openapi_probe"]["latest_status"] == "not_published"
    assert payload["web_view_value_qa"]["issue_count"] == 0
    assert payload["api_perf"]["record_count"] == 2
    assert payload["recommended_actions"]


def test_next_phase_readiness_groups_latest_krx_openapi_probe_batch(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    called_at = "2026-05-20T01:20:46+09:00"
    for endpoint in ("stock-kospi-daily", "index-kospi-daily"):
        repository.record_operation_event(
            OperationEvent(
                event_time=datetime(2026, 5, 20, 1, 20, 47),
                component="krx",
                event_type="openapi-availability-probe",
                status="not_published",
                business_date=date(2026, 5, 19),
                detail=json.dumps(
                    {
                        "called_at": called_at,
                        "endpoint": endpoint,
                        "raw_row_count": 0,
                        "parsed_row_count": 0,
                        "reference_date": None,
                        "stored": False,
                    },
                    ensure_ascii=False,
                ),
            )
        )

    payload = cli_module._latest_krx_openapi_availability_probe(repository)

    assert payload["latest_probe_at"] == called_at
    assert payload["latest_endpoint"] == "daily"
    assert payload["latest_status"] == "not_published"
    assert payload["latest_status_counts"] == {"not_published": 2}
    assert payload["latest_endpoint_count"] == 2
    assert payload["latest_endpoints"][0]["stored"] is False


def test_latest_publishable_krx_openapi_date_uses_next_business_day_0800_rule() -> None:
    assert cli_module._latest_publishable_krx_openapi_date(
        datetime(2026, 5, 29, 22, 0, 0),
        set(),
    ) == date(2026, 5, 28)
    assert cli_module._latest_publishable_krx_openapi_date(
        datetime(2026, 6, 1, 7, 59, 0),
        set(),
    ) == date(2026, 5, 28)
    assert cli_module._latest_publishable_krx_openapi_date(
        datetime(2026, 6, 1, 8, 0, 0),
        set(),
    ) == date(2026, 5, 29)


def test_krx_baseline_analysis_omits_unpublished_current_business_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "datetime", _KrxBaselineFridayLateDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    payload = cli_module._build_krx_baseline_analysis(
        config,
        repository,
        lookback_days=3,
        to_date=None,
        max_missing_dates=3,
    )

    assert payload["window"]["to_date"] == "2026-05-28"
    missing_dates = [row["business_date"] for row in payload["missing_daily_snapshots"]["next"]]
    assert missing_dates == ["2026-05-28", "2026-05-27", "2026-05-26"]
    assert "2026-05-29" not in missing_dates


def test_krx_flow_dry_run_resolves_isu_cd_from_metadata(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDataMarketDryRunResult, resolve_krx_data_market_endpoint
    from stock_monitor.models import KrxStockMetadataSnapshot

    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "user")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=datetime(2026, 5, 8).date(),
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            )
        ]
    )

    def fake_fetch(**kwargs) -> KrxDataMarketDryRunResult:
        endpoint = kwargs["endpoint"]
        assert kwargs["base_url"] == "https://data.krx.co.kr"
        assert kwargs["params"]["isuCd"] == "KR7005930003"
        assert kwargs["params"]["inqTpCd"] == "1"
        return KrxDataMarketDryRunResult(
            endpoint=endpoint,
            params=kwargs["params"],
            row_count=1,
            field_keys=("INVST_TP_NM", "NETBID_TRDVOL"),
            rows=({"INVST_TP_NM": "개인", "NETBID_TRDVOL": "1,000"},),
            first_row={"INVST_TP_NM": "개인", "NETBID_TRDVOL": "1,000"},
        )

    monkeypatch.setattr(cli_module, "fetch_krx_data_market_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_data_market_endpoint", resolve_krx_data_market_endpoint)

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="005930",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX Data Marketplace flow dry-run: 2026-05-08" in output
    assert "bld=dbms/MDC/STAT/standard/MDCSTAT02301" in output
    assert "isuCd=KR7005930003" in output
    assert "No DB rows were written." in output


def test_krx_flow_dry_run_requires_isu_mapping(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="005930",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Cannot resolve KRX isuCd for stock_code=005930" in output
    assert "krx-fetch-snapshot stock-kospi-basic" in output


def test_krx_flow_dry_run_requires_login_after_input_validation(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import KrxStockMetadataSnapshot

    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=datetime(2026, 5, 8).date(),
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            )
        ]
    )
    normalized_output = tmp_path / "normalized" / "12008_market_20260508.normalized.local.json"

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="005930",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing KRX Data Marketplace dry-run without login configuration." in output
    assert "Use --request-only to validate resolved request params without login." in output


def test_krx_flow_request_only_prints_resolved_params_without_login(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import KrxStockMetadataSnapshot

    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=datetime(2026, 5, 8).date(),
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            )
        ]
    )

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="005930",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=True,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX Data Marketplace flow request preview: 2026-05-08" in output
    assert "bld=dbms/MDC/STAT/standard/MDCSTAT02301" in output
    assert "stock_code=005930" in output
    assert "stock_name=삼성전자" in output
    assert "isuCd=KR7005930003" in output
    assert '"isuCd": "KR7005930003"' in output
    assert "No login, network call, or DB write was performed." in output


def test_krx_flow_login_check_requires_login_config(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    exit_code = cli_module._run_krx_flow_login_check(
        config,
        business_date=datetime(2026, 5, 8).date(),
        market="STK",
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "KRX Data Marketplace login check failed." in output
    assert "reason=missing_login_configuration" in output
    assert "No DB rows were written." in output


def test_krx_flow_login_check_reports_success(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDataMarketDryRunResult, resolve_krx_data_market_endpoint

    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "user")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    def fake_fetch(**kwargs) -> KrxDataMarketDryRunResult:
        assert kwargs["base_url"] == "https://data.krx.co.kr"
        assert kwargs["login_id"] == "user"
        assert kwargs["login_password"] == "pw"
        assert kwargs["params"]["mktId"] == "STK"
        assert kwargs["params"]["etf"] == ""
        assert kwargs["params"]["etn"] == ""
        assert kwargs["params"]["elw"] == ""
        assert kwargs["params"]["trdVolVal"] == "2"
        assert kwargs["params"]["askBid"] == "3"
        endpoint = kwargs["endpoint"]
        return KrxDataMarketDryRunResult(
            endpoint=endpoint,
            params=kwargs["params"],
            row_count=1,
            field_keys=("INVST_TP_NM", "NETBID_TRDVAL"),
            rows=({"INVST_TP_NM": "외국인", "NETBID_TRDVAL": "1,000"},),
            first_row={"INVST_TP_NM": "외국인", "NETBID_TRDVAL": "1,000"},
        )

    monkeypatch.setattr(cli_module, "fetch_krx_data_market_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_data_market_endpoint", resolve_krx_data_market_endpoint)

    exit_code = cli_module._run_krx_flow_login_check(
        config,
        business_date=datetime(2026, 5, 8).date(),
        market="STK",
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX Data Marketplace login check passed." in output
    assert "endpoint=investor-flow-market-period" in output
    assert "rows=1" in output
    assert "No DB rows were written." in output


def test_krx_flow_login_check_classifies_auth_rejection(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDataMarketAuthError

    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "user")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    def fake_fetch(**_kwargs) -> None:
        raise KrxDataMarketAuthError("KRX Data Marketplace login is required or rejected.")

    monkeypatch.setattr(cli_module, "fetch_krx_data_market_endpoint", fake_fetch)

    exit_code = cli_module._run_krx_flow_login_check(
        config,
        business_date=datetime(2026, 5, 8).date(),
        market="STK",
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "KRX Data Marketplace login check failed." in output
    assert "reason=auth_rejected" in output
    assert "No DB rows were written." in output


def test_krx_flow_dry_run_writes_manifest_scaffold_without_network(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_output = tmp_path / "krx_samples" / "12009_329180_20260508.manifest.local.json"

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="329180",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=manifest_output,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    manifest = json.loads(manifest_output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "KRX flow sample manifest scaffold written" in output
    assert manifest["sample_file"] == "12009_329180_20260508.local.json"
    assert manifest["view"] == "stock"
    assert manifest["stock_code"] == "329180"
    assert manifest["expected_min_rows"] == 1
    assert manifest["expected_investors"] == ["외국인", "기관합계", "개인"]


def test_krx_flow_dry_run_normalizes_sample_file_without_login(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import KrxStockMetadataSnapshot

    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=datetime(2026, 5, 8).date(),
                standard_code="KR7329180004",
                stock_code="329180",
                stock_name="HD현대중공업",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            )
        ]
    )
    sample_path = tmp_path / "krx_12009_sample.json"
    sample_path.write_text(
        json.dumps(
            {
                "output": [
                    {
                        "INVST_TP_NM": "외국인",
                        "ASK_TRDVOL": "100",
                        "BID_TRDVOL": "130",
                        "NETBID_TRDVOL": "30",
                        "ASK_TRDVAL": "1,000",
                        "BID_TRDVAL": "1,400",
                        "NETBID_TRDVAL": "400",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="stock",
        stock_code="329180",
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="천주",
        amount_unit="백만원",
        request_only=False,
        sample_file=sample_path,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX Data Marketplace flow sample normalization: 2026-05-08" in output
    assert "- rows=1" in output
    assert "- normalized_rows=1" in output
    assert "- units=volume:천주, amount:백만원" in output
    assert '"investor_type": "외국인"' in output
    assert '"volume_unit": "천주"' in output
    assert '"amount_unit": "백만원"' in output
    assert '"net_buy_amount": 400' in output
    assert "No login, network call, or DB write was performed." in output


def test_krx_flow_dry_run_warns_on_poor_sample_quality(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    sample_path = tmp_path / "empty_output.json"
    sample_path.write_text('{"output":[]}', encoding="utf-8")

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="market",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="STK",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=sample_path,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=True,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "- quality=warn" in output
    assert "warning=raw_row_count is 0" in output


def test_krx_flow_dry_run_warns_on_missing_expected_investor(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    sample_path = tmp_path / "market_output.json"
    sample_path.write_text(
        json.dumps(
            {
                "output": [
                    {
                        "INVST_TP_NM": "개인",
                        "NETBID_TRDVOL": "1",
                        "NETBID_TRDVAL": "2",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="market",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="STK",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=sample_path,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=True,
        expected_min_rows=1,
        expected_min_normalized_rows=1,
        expected_investors=["외국인", "기관합계"],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "- quality=warn" in output
    assert "missing expected investor rows: 외국인, 기관합계" in output


def test_krx_flow_dry_run_normalizes_sample_manifest_without_login(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    sample_path = tmp_path / "12008_market_20260508.local.json"
    manifest_path = tmp_path / "12008_market_20260508.manifest.local.json"
    sample_path.write_text(
        json.dumps(
            {
                "output": [
                    {
                        "INVST_TP_NM": "기관합계",
                        "ASK_TRDVOL": "1,000",
                        "BID_TRDVOL": "1,500",
                        "NETBID_TRDVOL": "500",
                        "ASK_TRDVAL": "10,000",
                        "BID_TRDVAL": "15,000",
                        "NETBID_TRDVAL": "5,000",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "value": "amount",
                "side": "net-buy",
                "volume_unit": "천주",
                "amount_unit": "백만원",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
                "expected_investors": ["기관합계"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    normalized_output = tmp_path / "normalized" / "12008_market_20260508.normalized.local.json"

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 1, 1).date(),
        view="stock",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=manifest_path,
        manifest_output=None,
        normalized_output=normalized_output,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=True,
    )

    output = capsys.readouterr().out
    normalized_payload = json.loads(normalized_output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "KRX Data Marketplace flow sample normalization: 2026-05-08" in output
    assert "- view=market" in output
    assert "- market=STK" in output
    assert f"- manifest={manifest_path}" in output
    assert f"- normalized_output={normalized_output}" in output
    assert "- units=volume:천주, amount:백만원" in output
    assert '"investor_type": "기관합계"' in output
    assert '"net_buy_amount": 5000' in output
    assert normalized_payload["view"] == "market"
    assert normalized_payload["expected_min_rows"] == 1
    assert normalized_payload["expected_investors"] == ["기관합계"]
    assert normalized_payload["normalized_rows"][0]["investor_type"] == "기관합계"
    assert normalized_payload["normalized_rows"][0]["amount_unit"] == "백만원"


def test_krx_flow_dry_run_rejects_invalid_sample_manifest(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    sample_path = tmp_path / "sample.json"
    manifest_path = tmp_path / "bad.manifest.local.json"
    sample_path.write_text('{"output":[]}', encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "bad-view",
                "business_date": "2026-05-08",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 1, 1).date(),
        view="stock",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="ALL",
        investor="all",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=manifest_path,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Invalid KRX flow view" in output


def test_krx_flow_validate_samples_fails_on_strict_warning(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    good_sample = manifest_dir / "12008_market_good.local.json"
    good_manifest = manifest_dir / "12008_market_good.manifest.local.json"
    bad_sample = manifest_dir / "12008_market_bad.local.json"
    bad_manifest = manifest_dir / "12008_market_bad.manifest.local.json"
    good_sample.write_text(
        json.dumps(
            {
                "output": [
                    {
                        "INVST_TP_NM": "외국인",
                        "NETBID_TRDVOL": "10",
                        "NETBID_TRDVAL": "20",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bad_sample.write_text('{"output":[]}', encoding="utf-8")
    good_manifest.write_text(
        json.dumps(
            {
                "sample_file": good_sample.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "volume_unit": "주",
                "amount_unit": "원",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
                "expected_investors": ["외국인"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    bad_manifest.write_text(
        json.dumps(
            {
                "sample_file": bad_sample.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "volume_unit": "주",
                "amount_unit": "원",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_validate_samples(
        config,
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        allow_warnings=False,
        normalized_dir=None,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "KRX flow sample batch validation" in output
    assert "- total: 2" in output
    assert "- passed: 1" in output
    assert "- failed: 1" in output
    assert str(bad_manifest) in output


def test_krx_flow_validate_samples_can_allow_warnings(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    sample_path = manifest_dir / "12008_market_empty.local.json"
    manifest_path = manifest_dir / "12008_market_empty.manifest.local.json"
    sample_path.write_text('{"output":[]}', encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "volume_unit": "주",
                "amount_unit": "원",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_validate_samples(
        config,
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        allow_warnings=True,
        normalized_dir=None,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "- allow_warnings: Y" in output
    assert "- quality=warn" in output
    assert "- failed: 0" in output


def test_krx_flow_validate_samples_writes_normalized_artifacts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", raising=False)
    monkeypatch.delenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    normalized_dir = tmp_path / "normalized"
    manifest_dir.mkdir()
    sample_path = manifest_dir / "12008_market_STK_20260508.local.json"
    manifest_path = manifest_dir / "12008_market_STK_20260508.manifest.local.json"
    sample_path.write_text(
        json.dumps(
            {
                "output": [
                    {
                        "INVST_TP_NM": "외국인",
                        "NETBID_TRDVOL": "10",
                        "NETBID_TRDVAL": "20",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "volume_unit": "주",
                "amount_unit": "원",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
                "expected_investors": ["외국인"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_validate_samples(
        config,
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        allow_warnings=False,
        normalized_dir=normalized_dir,
    )

    output = capsys.readouterr().out
    artifact_path = normalized_dir / "12008_market_STK_20260508.normalized.local.json"
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert f"- normalized_dir: {normalized_dir}" in output
    assert artifact_path.exists()
    assert payload["quality_status"] == "ok"
    assert payload["normalized_rows"][0]["investor_type"] == "외국인"


def test_krx_flow_sample_status_reports_missing_views_and_samples(tmp_path, capsys) -> None:
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "12009_005930_20260508.manifest.local.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": "12009_005930_20260508.local.json",
                "view": "stock",
                "business_date": "2026-05-08",
                "stock_code": "005930",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_sample_status(
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "KRX flow sample manifest status" in output
    assert "- ready_for_batch_validation: N" in output
    assert "stock: 1" in output
    assert "market: 0" in output
    assert "top: 0" in output
    assert "- missing views: market, top" in output
    assert "12009_005930_20260508.local.json" in output
    assert "- next capture files:" in output


def test_krx_flow_sample_status_json_ready_when_all_views_have_samples(tmp_path, capsys) -> None:
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    entries = [
        ("12009_005930_20260508", "stock", {"stock_code": "005930"}),
        ("12008_market_20260508", "market", {"market": "STK"}),
        ("12010_top_20260508_foreign", "top", {"market": "STK", "investor": "foreign"}),
    ]
    for stem, view, extra in entries:
        sample_path = manifest_dir / f"{stem}.local.json"
        manifest_path = manifest_dir / f"{stem}.manifest.local.json"
        sample_path.write_text('{"output":[]}', encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "sample_file": sample_path.name,
                    "view": view,
                    "business_date": "2026-05-08",
                    **extra,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_sample_status(
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ready_for_batch_validation"] is True
    assert payload["view_counts"] == {"stock": 1, "market": 1, "top": 1}
    assert payload["missing_views"] == []
    assert payload["missing_sample_file_count"] == 0
    assert payload["next_capture_files"] == []


def test_krx_flow_sample_scaffold_writes_capture_set(tmp_path, capsys) -> None:
    output_dir = tmp_path / "krx_samples"

    exit_code = cli_module._run_krx_flow_sample_scaffold(
        business_date=datetime(2026, 5, 8).date(),
        output_dir=output_dir,
        stock_codes=["005930", "005930", "329180"],
        from_candidates=False,
        candidate_limit=10,
        min_reasons=2,
        markets=["STK"],
        top_investors=["foreign"],
        overwrite=False,
    )

    output = capsys.readouterr().out
    manifests = sorted(output_dir.glob("*.manifest.local.json"))
    assert exit_code == 0
    assert "KRX flow sample manifest scaffolds written" in output
    assert "- stock manifests: 2" in output
    assert "- market manifests: 1" in output
    assert "- top manifests: 1" in output
    assert len(manifests) == 4
    stock_manifest = json.loads((output_dir / "12009_005930_20260508.manifest.local.json").read_text(encoding="utf-8"))
    market_manifest = json.loads((output_dir / "12008_market_STK_20260508.manifest.local.json").read_text(encoding="utf-8"))
    top_manifest = json.loads((output_dir / "12010_top_STK_20260508_foreign.manifest.local.json").read_text(encoding="utf-8"))
    assert stock_manifest["view"] == "stock"
    assert stock_manifest["stock_code"] == "005930"
    assert stock_manifest["expected_investors"] == ["외국인", "기관합계", "개인"]
    assert market_manifest["view"] == "market"
    assert market_manifest["market"] == "STK"
    assert market_manifest["value"] == "amount"
    assert top_manifest["view"] == "top"
    assert top_manifest["investor"] == "foreign"


def test_krx_flow_sample_scaffold_refuses_overwrite(tmp_path, capsys) -> None:
    output_dir = tmp_path / "krx_samples"
    assert cli_module._run_krx_flow_sample_scaffold(
        business_date=datetime(2026, 5, 8).date(),
        output_dir=output_dir,
        stock_codes=["005930"],
        from_candidates=False,
        candidate_limit=10,
        min_reasons=2,
        markets=[],
        top_investors=[],
        overwrite=False,
    ) == 0
    capsys.readouterr()

    exit_code = cli_module._run_krx_flow_sample_scaffold(
        business_date=datetime(2026, 5, 8).date(),
        output_dir=output_dir,
        stock_codes=["005930"],
        from_candidates=False,
        candidate_limit=10,
        min_reasons=2,
        markets=[],
        top_investors=[],
        overwrite=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to overwrite existing KRX flow sample manifest" in output


def test_krx_flow_sample_scaffold_can_use_local_candidates(tmp_path, capsys) -> None:
    from datetime import date

    from stock_monitor.models import Report, StockMarketDailySnapshot

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 18, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="A증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="메모리 가격",
                broker_name="B증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="110,000",
                target_price_value=110000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=80000,
                change_percent=3.5,
                volume=1000000,
                turnover=900000000000,
                fetched_at=fetched_at,
            )
        ]
    )
    output_dir = tmp_path / "krx_samples"

    exit_code = cli_module._run_krx_flow_sample_scaffold(
        config=config,
        repository=repository,
        business_date=business_date,
        output_dir=output_dir,
        stock_codes=[],
        from_candidates=True,
        candidate_limit=5,
        min_reasons=2,
        markets=["STK"],
        top_investors=["foreign"],
        overwrite=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "- from_candidates: Y" in output
    assert "- stock manifests: 1" in output
    manifest = json.loads((output_dir / "12009_005930_20260508.manifest.local.json").read_text(encoding="utf-8"))
    assert manifest["stock_code"] == "005930"


def test_krx_flow_capture_checklist_prints_manifest_tasks(tmp_path, capsys) -> None:
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    stock_sample = manifest_dir / "12009_005930_20260508.local.json"
    stock_manifest = manifest_dir / "12009_005930_20260508.manifest.local.json"
    market_sample = manifest_dir / "12008_market_STK_20260508.local.json"
    market_manifest = manifest_dir / "12008_market_STK_20260508.manifest.local.json"
    stock_sample.write_text('{"output":[]}', encoding="utf-8")
    market_sample.write_text('{"output":[]}', encoding="utf-8")
    stock_manifest.write_text(
        json.dumps(
            {
                "sample_file": stock_sample.name,
                "view": "stock",
                "business_date": "2026-05-08",
                "stock_code": "005930",
                "query": "period",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    market_manifest.write_text(
        json.dumps(
            {
                "sample_file": market_sample.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "value": "amount",
                "side": "net-buy",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_capture_checklist(
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX flow capture checklist" in output
    assert "[12009] 투자자별 거래실적(개별종목)" in output
    assert "[12008] 투자자별 거래실적" in output
    assert f"raw_file: {stock_sample}" in output
    assert "--sample-manifest" in output
    assert "krx-flow-validate-samples" in output


def test_krx_flow_capture_checklist_json_handles_no_manifests(tmp_path, capsys) -> None:
    manifest_dir = tmp_path / "krx_samples"

    exit_code = cli_module._run_krx_flow_capture_checklist(
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["item_count"] == 0
    assert payload["items"] == []
    assert payload["next_step"] == "Run krx-flow-sample-scaffold first."


def test_krx_flow_import_preview_counts_target_tables(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    stock_sample = manifest_dir / "12009_005930_20260508.local.json"
    market_sample = manifest_dir / "12008_market_STK_20260508.local.json"
    top_sample = manifest_dir / "12010_top_STK_20260508_foreign.local.json"
    stock_sample.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": "2"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    market_sample.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "기관합계", "NETBID_TRDVOL": "3", "NETBID_TRDVAL": "4"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    top_sample.write_text(
        json.dumps({"output": [{"RANK": "1", "ISU_SRT_CD": "005930", "ISU_ABBRV": "삼성전자", "NETBID_TRDVAL": "5"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    for sample_path, payload in [
        (stock_sample, {"view": "stock", "stock_code": "005930", "market": "ALL", "expected_investors": ["외국인"]}),
        (market_sample, {"view": "market", "market": "STK", "expected_investors": ["기관합계"]}),
        (top_sample, {"view": "top", "market": "STK", "investor": "foreign"}),
    ]:
        manifest_path = sample_path.with_name(sample_path.name.replace(".local.json", ".manifest.local.json"))
        manifest_path.write_text(
            json.dumps(
                {
                    "sample_file": sample_path.name,
                    "business_date": "2026-05-08",
                    "volume_unit": "주",
                    "amount_unit": "원",
                    "expected_min_rows": 1,
                    "expected_min_normalized_rows": 1,
                    **payload,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_import_preview(
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX flow import preview" in output
    assert "stock_investor_flow_daily: 1" in output
    assert "market_investor_flow_daily: 1" in output
    assert "investor_net_buy_top_daily: 1" in output
    assert "No SQLite rows were written." in output
    assert repository.list_stock_investor_flow_daily(datetime(2026, 5, 8).date(), stock_code="005930") == []


def test_krx_flow_import_preview_json_reports_warnings(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    sample_path = manifest_dir / "12008_market_STK_20260508.local.json"
    manifest_path = manifest_dir / "12008_market_STK_20260508.manifest.local.json"
    sample_path.write_text('{"output":[]}', encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_import_preview(
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["target_table_counts"]["market_investor_flow_daily"] == 0
    assert payload["warning_count"] == 1
    assert payload["warnings"][0]["warnings"] == [
        "raw_row_count is 0",
        "raw_row_count 0 is below expected_min_rows 1",
        "normalized_row_count 0 is below expected_min_normalized_rows 1",
    ]
    assert payload["db_write"] is False


def test_krx_flow_compare_samples_passes_matching_manifest_sets(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    left_dir = tmp_path / "visible_grid"
    right_dir = tmp_path / "raw_network"
    left_dir.mkdir()
    right_dir.mkdir()
    sample_payload = {"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": "2"}]}
    manifest_payload = {
        "sample_file": "12008_market_STK_20260508.local.json",
        "view": "market",
        "business_date": "2026-05-08",
        "market": "STK",
        "volume_unit": "주",
        "amount_unit": "원",
        "expected_min_rows": 1,
        "expected_min_normalized_rows": 1,
        "expected_investors": ["외국인"],
    }
    for directory in (left_dir, right_dir):
        (directory / manifest_payload["sample_file"]).write_text(
            json.dumps(sample_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "12008_market_STK_20260508.manifest.local.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_compare_samples(
        repository,
        left_manifest_dir=left_dir,
        right_manifest_dir=right_dir,
        pattern="*.manifest.local.json",
        allow_right_extra_top_rows=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX flow sample parity comparison" in output
    assert "- matched: 1" in output
    assert "- mismatched: 0" in output
    assert "- DB write: N" in output
    assert "- network call: N" in output


def test_krx_flow_compare_samples_reports_normalized_mismatch(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    left_dir = tmp_path / "visible_grid"
    right_dir = tmp_path / "raw_network"
    left_dir.mkdir()
    right_dir.mkdir()
    manifest_payload = {
        "sample_file": "12008_market_STK_20260508.local.json",
        "view": "market",
        "business_date": "2026-05-08",
        "market": "STK",
        "volume_unit": "주",
        "amount_unit": "원",
        "expected_min_rows": 1,
        "expected_min_normalized_rows": 1,
        "expected_investors": ["외국인"],
    }
    for directory, net_buy_amount in ((left_dir, "2"), (right_dir, "999")):
        (directory / manifest_payload["sample_file"]).write_text(
            json.dumps(
                {"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": net_buy_amount}]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (directory / "12008_market_STK_20260508.manifest.local.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_compare_samples(
        repository,
        left_manifest_dir=left_dir,
        right_manifest_dir=right_dir,
        pattern="*.manifest.local.json",
        allow_right_extra_top_rows=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["mismatch_count"] == 1
    assert payload["matched_count"] == 0
    assert payload["mismatches"][0]["key"] == "market|2026-05-08|STK"
    assert "net_buy_amount" in payload["mismatches"][0]["details"][0]
    assert payload["db_write"] is False
    assert payload["network_call"] is False


def test_krx_flow_compare_samples_reports_missing_right_manifest(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    left_dir = tmp_path / "visible_grid"
    right_dir = tmp_path / "raw_network"
    left_dir.mkdir()
    right_dir.mkdir()
    sample_path = left_dir / "12008_market_STK_20260508.local.json"
    sample_path.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": "2"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (left_dir / "12008_market_STK_20260508.manifest.local.json").write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "expected_min_rows": 1,
                "expected_min_normalized_rows": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_compare_samples(
        repository,
        left_manifest_dir=left_dir,
        right_manifest_dir=right_dir,
        pattern="*.manifest.local.json",
        allow_right_extra_top_rows=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "- missing_right: 1" in output
    assert "market|2026-05-08|STK" in output


def test_krx_flow_compare_samples_allows_right_extra_top_rows(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    left_dir = tmp_path / "visible_grid"
    right_dir = tmp_path / "raw_network"
    left_dir.mkdir()
    right_dir.mkdir()
    manifest_payload = {
        "sample_file": "12010_top_STK_20260508_foreign.local.json",
        "view": "top",
        "business_date": "2026-05-08",
        "market": "STK",
        "investor": "foreign",
        "expected_min_rows": 1,
        "expected_min_normalized_rows": 1,
    }
    left_rows = [{"RANK": "1", "ISU_SRT_CD": "005930", "ISU_ABBRV": "삼성전자", "NETBID_TRDVAL": "5"}]
    right_rows = [
        {"RANK": "1", "ISU_SRT_CD": "005930", "ISU_ABBRV": "삼성전자", "NETBID_TRDVAL": "5"},
        {"RANK": "2", "ISU_SRT_CD": "000660", "ISU_ABBRV": "SK하이닉스", "NETBID_TRDVAL": "4"},
    ]
    for directory, rows in ((left_dir, left_rows), (right_dir, right_rows)):
        (directory / manifest_payload["sample_file"]).write_text(
            json.dumps({"output": rows}, ensure_ascii=False),
            encoding="utf-8",
        )
        (directory / "12010_top_STK_20260508_foreign.manifest.local.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_compare_samples(
        repository,
        left_manifest_dir=left_dir,
        right_manifest_dir=right_dir,
        pattern="*.manifest.local.json",
        allow_right_extra_top_rows=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mismatch_count"] == 0
    assert payload["compatible_superset_count"] == 1
    assert payload["compatible_supersets"][0]["extra_right_rows"] == 1


def test_krx_flow_raw_sample_scaffold_writes_manifests_only(tmp_path, capsys) -> None:
    source_dir = tmp_path / "visible_grid"
    output_dir = tmp_path / "raw_network"
    source_dir.mkdir()
    sample_path = source_dir / "12008_market_STK_20260508.local.json"
    sample_path.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": "2"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (source_dir / "12008_market_STK_20260508.manifest.local.json").write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "expected_min_rows": 1,
                "capture_method": "visible_grid_dom",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_raw_sample_scaffold(
        source_manifest_dir=source_dir,
        output_dir=output_dir,
        pattern="*.manifest.local.json",
        overwrite=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    target_manifest = output_dir / "12008_market_STK_20260508.manifest.local.json"
    target_sample = output_dir / sample_path.name
    payload = json.loads(target_manifest.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "KRX raw-network sample manifest scaffolds written" in output
    assert target_manifest.exists()
    assert not target_sample.exists()
    assert payload["sample_file"] == sample_path.name
    assert payload["capture_method"] == "raw_network_response"
    assert payload["source_manifest"].endswith("12008_market_STK_20260508.manifest.local.json")
    assert "Do not store cookies" in payload["capture_note"]


def test_krx_flow_raw_sample_scaffold_refuses_existing_manifest(tmp_path, capsys) -> None:
    source_dir = tmp_path / "visible_grid"
    output_dir = tmp_path / "raw_network"
    source_dir.mkdir()
    output_dir.mkdir()
    manifest_payload = {
        "sample_file": "12008_market_STK_20260508.local.json",
        "view": "market",
        "business_date": "2026-05-08",
        "market": "STK",
    }
    for directory in (source_dir, output_dir):
        (directory / "12008_market_STK_20260508.manifest.local.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_raw_sample_scaffold(
        source_manifest_dir=source_dir,
        output_dir=output_dir,
        pattern="*.manifest.local.json",
        overwrite=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["written_count"] == 0
    assert payload["existing_count"] == 1
    assert payload["db_write"] is False
    assert payload["network_call"] is False


def test_krx_flow_import_samples_requires_confirmation(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = cli_module._run_krx_flow_import_samples(
        config,
        repository,
        manifest_dir=tmp_path / "krx_samples",
        pattern="*.manifest.local.json",
        confirm=False,
        i_validated=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to import KRX flow samples without --confirm --i-validated" in output


def test_krx_flow_import_samples_upserts_validated_rows(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    stock_sample = manifest_dir / "12009_005930_20260508.local.json"
    market_sample = manifest_dir / "12008_market_STK_20260508.local.json"
    top_sample = manifest_dir / "12010_top_STK_20260508_foreign.local.json"
    stock_sample.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "외국인", "NETBID_TRDVOL": "1", "NETBID_TRDVAL": "2"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    market_sample.write_text(
        json.dumps({"output": [{"INVST_TP_NM": "기관합계", "NETBID_TRDVOL": "3", "NETBID_TRDVAL": "4"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    top_sample.write_text(
        json.dumps({"output": [{"RANK": "1", "ISU_SRT_CD": "005930", "ISU_ABBRV": "삼성전자", "NETBID_TRDVAL": "5"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    for sample_path, payload in [
        (stock_sample, {"view": "stock", "stock_code": "005930", "market": "ALL", "expected_investors": ["외국인"]}),
        (market_sample, {"view": "market", "market": "STK", "expected_investors": ["기관합계"]}),
        (top_sample, {"view": "top", "market": "STK", "investor": "foreign"}),
    ]:
        sample_path.with_name(sample_path.name.replace(".local.json", ".manifest.local.json")).write_text(
            json.dumps(
                {
                    "sample_file": sample_path.name,
                    "business_date": "2026-05-08",
                    "volume_unit": "주",
                    "amount_unit": "원",
                    "expected_min_rows": 1,
                    "expected_min_normalized_rows": 1,
                    **payload,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    exit_code = cli_module._run_krx_flow_import_samples(
        config,
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        confirm=True,
        i_validated=True,
    )

    output = capsys.readouterr().out
    business_date = datetime(2026, 5, 8).date()
    assert exit_code == 0
    assert "KRX flow sample import completed." in output
    assert "stock_investor_flow_daily: 1" in output
    assert repository.list_stock_investor_flow_daily(business_date, stock_code="005930")[0].investor_type == "외국인"
    assert repository.list_market_investor_flow_daily(business_date, market="STK")[0].investor_type == "기관합계"
    assert repository.list_investor_net_buy_top_daily(business_date, market="STK", investor_type="foreign")[0].stock_code == "005930"
    events = repository.list_recent_operation_events(limit=1)
    assert events[0].component == "krx-flow"
    assert events[0].event_type == "sample-import"


def test_krx_flow_import_samples_refuses_warning_rows(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    manifest_dir = tmp_path / "krx_samples"
    manifest_dir.mkdir()
    sample_path = manifest_dir / "12008_market_STK_20260508.local.json"
    manifest_path = manifest_dir / "12008_market_STK_20260508.manifest.local.json"
    sample_path.write_text('{"output":[]}', encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "sample_file": sample_path.name,
                "view": "market",
                "business_date": "2026-05-08",
                "market": "STK",
                "expected_min_rows": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = cli_module._run_krx_flow_import_samples(
        config,
        repository,
        manifest_dir=manifest_dir,
        pattern="*.manifest.local.json",
        confirm=True,
        i_validated=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing to import KRX flow samples because validation issues remain." in output
    assert repository.list_market_investor_flow_daily(datetime(2026, 5, 8).date(), market="STK") == []


def test_krx_flow_candidates_preview_uses_filtered_leadership_signals(tmp_path, capsys) -> None:
    from datetime import date

    from stock_monitor.models import Report, StockMarketDailySnapshot, StockMetadata

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 18, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="A증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="메모리 가격",
                broker_name="B증권",
                published_at=datetime(2026, 5, 8, 10, 0, 0),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="110,000",
                target_price_value=110000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
            Report(
                stock_name="한건종목",
                stock_code="000001",
                title="단건",
                broker_name="C증권",
                published_at=datetime(2026, 5, 8, 11, 0, 0),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="10,000",
                target_price_value=10000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="semi",
            sector_name="반도체",
            updated_at=fetched_at,
        )
    )
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=80000,
                change_percent=3.5,
                volume=1000000,
                turnover=900000000000,
                fetched_at=fetched_at,
            )
        ]
    )

    exit_code = cli_module._run_krx_flow_candidates(
        config,
        repository,
        business_date=business_date,
        limit=10,
        min_reasons=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX [12009] leadership candidate preview: 2026-05-08" in output
    assert "삼성전자(005930)" in output
    assert "리포트 2건" in output
    assert "목표가 있음" in output
    assert "거래대금 상위 1위" in output
    assert "한건종목" not in output
    assert "--stock-code 005930 --request-only" in output


def test_krx_flow_backfill_can_select_report_mention_threshold(tmp_path, capsys) -> None:
    from stock_monitor.models import Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="첫 리포트",
                broker_name="A증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=business_date,
                source_id="threshold-1",
                identity_key="threshold-1",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="두 번째 리포트",
                broker_name="B증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=business_date,
                source_id="threshold-2",
                identity_key="threshold-2",
            ),
            Report(
                stock_name="한건종목",
                stock_code="000660",
                title="한 건 리포트",
                broker_name="C증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=business_date,
                source_id="threshold-3",
                identity_key="threshold-3",
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    exit_code = cli_module._run_krx_flow_backfill_manual(
        config,
        repository,
        from_date=business_date,
        to_date=business_date,
        candidate_limit=0,
        min_reasons=2,
        report_mention_threshold=2,
        stock_codes=[],
        markets=["STK"],
        top_investors=["foreign"],
        sleep_seconds=0,
        dry_run=True,
        confirm=False,
        i_backed_up=False,
        allow_warnings=False,
        skip_existing=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["report_mention_threshold"] == 2
    assert payload["planned_call_count"] == 3
    assert payload["dates"][0]["candidate_count"] == 0
    assert payload["dates"][0]["report_mention_count"] == 1
    assert payload["dates"][0]["report_mention_stock_codes"] == ["005930"]
    assert payload["dates"][0]["stock_codes"] == ["005930"]


def test_krx_flow_dry_run_supports_market_and_top_views(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.fetch.krx_api import KrxDataMarketDryRunResult, resolve_krx_data_market_endpoint

    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "user")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    seen_endpoints: list[str] = []

    def fake_fetch(**kwargs) -> KrxDataMarketDryRunResult:
        endpoint = kwargs["endpoint"]
        seen_endpoints.append(endpoint.key)
        return KrxDataMarketDryRunResult(
            endpoint=endpoint,
            params=kwargs["params"],
            row_count=1,
            field_keys=("INVST_TP_NM",),
            rows=({"INVST_TP_NM": "외국인"},),
            first_row={"INVST_TP_NM": "외국인"},
        )

    monkeypatch.setattr(cli_module, "fetch_krx_data_market_endpoint", fake_fetch)
    monkeypatch.setattr(cli_module, "resolve_krx_data_market_endpoint", resolve_krx_data_market_endpoint)

    market_exit = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="market",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="STK",
        investor="all",
        value="amount",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )
    top_exit = cli_module._run_krx_flow_dry_run(
        config,
        repository,
        business_date=datetime(2026, 5, 8).date(),
        view="top",
        stock_code=None,
        isu_cd=None,
        query="period",
        market="KSQ",
        investor="foreign",
        value="volume",
        side="net-buy",
        volume_unit="주",
        amount_unit="원",
        request_only=False,
        sample_file=None,
        sample_manifest=None,
        manifest_output=None,
        normalized_output=None,
        strict_sample=False,
        expected_min_rows=0,
        expected_min_normalized_rows=0,
        expected_investors=[],
        as_json=False,
        show_first_row=False,
    )

    output = capsys.readouterr().out
    assert market_exit == 0
    assert top_exit == 0
    assert seen_endpoints == ["investor-flow-market-period", "investor-net-buy-top"]
    assert "market=STK; value=amount; side=net-buy" in output
    assert "market=KSQ; investor=foreign" in output


def test_krx_flow_login_reminder_dry_run_prints_message(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=True,
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX Data Marketplace 연결이 필요합니다" in output
    assert "5분 후 16:50 기준" in output
    assert "Would open browser: https://data.krx.co.kr" in output


def test_krx_flow_login_reminder_sends_telegram_and_records_delivery(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(cli_module, "datetime", _KrxReminderAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    sent_messages: list[str] = []

    def fake_send(*_args, **kwargs) -> str:  # noqa: ANN002, ANN003
        sent_messages.append(str(_args[2]))
        assert kwargs["timeout_seconds"] == config.telegram_timeout_seconds
        return "m-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    exit_code = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX flow login reminder sent with message_id=m-1" in output
    assert "원격 프로그램으로 이 PC의 Chrome에 열린 KRX Data Marketplace 탭에서" in sent_messages[0]
    assert "LOGOUT 응답이면 DB 저장 없이 건너뜁니다" in sent_messages[0]
    with repository.connect() as connection:
        row = connection.execute(
            "SELECT channel, status, message_id FROM delivery_log WHERE channel LIKE ?",
            ("telegram_krx_flow_login_reminder:%",),
        ).fetchone()
    assert dict(row) == {
        "channel": "telegram_krx_flow_login_reminder:m-1",
        "status": "sent",
        "message_id": "m-1",
    }


def test_krx_flow_login_reminder_allows_repeat_sends_same_day(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(cli_module, "datetime", _KrxReminderAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    message_ids = iter(["m-1", "m-2"])

    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: next(message_ids))

    first = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=False,
        dry_run=False,
    )
    second = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=False,
        dry_run=False,
    )

    with repository.connect() as connection:
        rows = connection.execute(
            "SELECT channel, message_id FROM delivery_log WHERE channel LIKE ? ORDER BY message_id",
            ("telegram_krx_flow_login_reminder:%",),
        ).fetchall()
    assert first == 0
    assert second == 0
    assert [dict(row) for row in rows] == [
        {"channel": "telegram_krx_flow_login_reminder:m-1", "message_id": "m-1"},
        {"channel": "telegram_krx_flow_login_reminder:m-2", "message_id": "m-2"},
    ]


def test_krx_flow_login_reminder_requires_telegram_config(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_module, "datetime", _KrxReminderAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time=None,
        open_browser=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing KRX flow login reminder without Telegram configuration" in output


def test_krx_flow_login_reminder_skips_market_holiday(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(cli_module, "datetime", _KrxReminderHolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    called = False

    def fake_send(*_args, **_kwargs) -> str:
        nonlocal called
        called = True
        return "m-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    exit_code = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert called is False
    assert "Skipping KRX flow login reminder" in output
    assert events[0].event_type == "login-reminder-guard"
    assert events[0].status == "skipped"


def test_krx_flow_login_reminder_skips_late_run(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(cli_module, "datetime", _KrxReminderLateDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    called = False

    def fake_send(*_args, **_kwargs) -> str:
        nonlocal called
        called = True
        return "m-1"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)

    exit_code = cli_module._run_krx_flow_login_reminder(
        config,
        repository,
        minutes_before=5,
        planned_time="16:50",
        open_browser=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert called is False
    assert "planned_time=16:50" in output
    assert events[0].event_type == "late_login_reminder"
    assert events[0].status == "skipped"


def test_scheduled_krx_daily_backfill_targets_previous_business_day(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxDailyBackfillAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    calls: list[dict] = []

    def fake_backfill(_config, _repository, **kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(cli_module, "_run_krx_backfill_missing", fake_backfill)

    exit_code = cli_module._run_scheduled_krx_daily_backfill(
        config,
        repository,
        lookback_days=7,
        max_dates=3,
        sleep_seconds=3,
        dry_run=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Scheduled KRX daily backfill target: <= 2026-05-11" in output
    assert calls == [
        {
            "endpoint_selector": "daily",
            "lookback_days": 7,
            "to_date": datetime(2026, 5, 11).date(),
            "max_dates": 3,
            "sleep_seconds": 3,
            "confirm": True,
            "backup_confirmed": True,
            "allow_large_batch": False,
            "dry_run": False,
            "as_json": False,
        }
    ]


def test_scheduled_krx_daily_backfill_json_skips_market_holiday(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxDailyBackfillHolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = cli_module._run_scheduled_krx_daily_backfill(
        config,
        repository,
        lookback_days=7,
        max_dates=3,
        sleep_seconds=3,
        dry_run=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert payload["surface"] == "scheduled-krx-daily-backfill"
    assert payload["read_only"] is True
    assert payload["skipped"] is True
    assert payload["business_date"] == "2026-05-25"
    assert "not a configured market business day" in payload["skip_reason"]
    assert events[0].event_type == "scheduled-daily-backfill"
    assert events[0].status == "skipped"


def test_scheduled_krx_daily_backfill_skips_market_holiday(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxDailyBackfillHolidayDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    called = False

    def fake_backfill(*_args, **_kwargs):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli_module, "_run_krx_backfill_missing", fake_backfill)

    exit_code = cli_module._run_scheduled_krx_daily_backfill(
        config,
        repository,
        lookback_days=7,
        max_dates=3,
        sleep_seconds=3,
        dry_run=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert called is False
    assert "Skipping scheduled KRX daily backfill" in output
    assert events[0].component == "krx"
    assert events[0].event_type == "scheduled-daily-backfill"
    assert events[0].status == "skipped"


def test_scheduled_krx_mentioned_flow_backfill_dry_run_uses_anchor_date_mentions(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxMentionedFlowAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    anchor_date = date(2026, 5, 12)
    previous_date = date(2026, 5, 11)
    _upsert_test_krx_stock_metadata(repository, anchor_date, ["000660", "005930"])
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="90000",
                target_price_value=90_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/1",
                source_id="1",
                identity_key="1",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="메모리 강세",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 30, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="300000",
                target_price_value=300_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/2",
                source_id="2",
                identity_key="2",
            ),
        ]
    )
    repository.rebuild_daily_summaries(anchor_date)
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=previous_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=datetime(2026, 5, 11, 16, 0, 0),
            ),
            StockInvestorFlowDaily(
                business_date=previous_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="기관합계",
                fetched_at=datetime(2026, 5, 11, 16, 0, 0),
            ),
            StockInvestorFlowDaily(
                business_date=previous_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="개인",
                fetched_at=datetime(2026, 5, 11, 16, 0, 0),
            )
        ]
    )

    exit_code = _run_scheduled_krx_mentioned_flow_backfill(
        config,
        repository,
        anchor_date=anchor_date,
        lookback_days=2,
        mention_threshold=1,
        max_calls=0,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mentioned_stock_codes"] == ["000660", "005930"]
    assert payload["business_date_count"] == 2
    assert payload["planned_call_count"] == 3
    assert payload["dates"][0]["business_date"] == "2026-05-12"
    assert payload["dates"][0]["stock_codes"] == ["000660", "005930"]
    assert payload["dates"][1]["business_date"] == "2026-05-11"
    assert payload["dates"][1]["stock_codes"] == ["000660"]


def test_scheduled_krx_mentioned_flow_backfill_does_not_skip_partial_stock_flow_rows(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxMentionedFlowAllowedDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    anchor_date = date(2026, 5, 12)
    _upsert_test_krx_stock_metadata(repository, anchor_date, ["005930"])
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="90000",
                target_price_value=90_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/partial",
                source_id="partial",
                identity_key="partial",
            )
        ]
    )
    repository.rebuild_daily_summaries(anchor_date)
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=anchor_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=datetime(2026, 5, 12, 16, 0, 0),
            )
        ]
    )

    exit_code = _run_scheduled_krx_mentioned_flow_backfill(
        config,
        repository,
        anchor_date=anchor_date,
        lookback_days=1,
        mention_threshold=1,
        max_calls=0,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["planned_call_count"] == 1
    assert payload["dates"][0]["stock_codes"] == ["005930"]


def test_scheduled_krx_mentioned_flow_backfill_writes_stock_only_rows(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "id")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    monkeypatch.setattr(cli_module, "datetime", _KrxMentionedFlowAllowedDateTime)
    monkeypatch.setattr(cli_module.time, "sleep", lambda *_args, **_kwargs: None)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    anchor_date = date(2026, 5, 12)
    _upsert_test_krx_stock_metadata(repository, anchor_date, ["005930"])
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="90000",
                target_price_value=90_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/3",
                source_id="3",
                identity_key="3",
            )
        ]
    )
    repository.rebuild_daily_summaries(anchor_date)
    calls: list[tuple[date, str]] = []

    def fake_fetch(_config, _repository, *, business_date, view, stock_code=None, **_kwargs):
        calls.append((business_date, stock_code))
        assert view == "stock"
        return [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code=str(stock_code),
                stock_name="삼성전자",
                investor_type="외국인",
                fetched_at=datetime(2026, 5, 12, 16, 0, 0),
            )
        ], 1, []

    monkeypatch.setattr(cli_module, "_fetch_krx_flow_rows_for_ingest", fake_fetch)

    exit_code = _run_scheduled_krx_mentioned_flow_backfill(
        config,
        repository,
        anchor_date=anchor_date,
        lookback_days=1,
        mention_threshold=1,
        max_calls=0,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert "Scheduled KRX mentioned-stock flow backfill completed" in output
    assert calls == [(anchor_date, "005930")]
    assert repository.list_stock_investor_flow_daily(anchor_date, "005930")
    assert repository.list_market_investor_flow_daily(anchor_date, "STK") == []
    assert events[0].component == "krx-flow"
    assert events[0].event_type == "scheduled-mentioned-flow-backfill"
    assert events[0].status == "completed"


def test_scheduled_krx_mentioned_flow_backfill_skips_unresolved_stock_metadata(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    from stock_monitor.fetch.krx_api import KrxDataMarketDryRunResult
    from stock_monitor.models import KrxStockMetadataSnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "id")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    monkeypatch.setattr(cli_module, "datetime", _KrxMentionedFlowAllowedDateTime)
    monkeypatch.setattr(cli_module.time, "sleep", lambda *_args, **_kwargs: None)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    anchor_date = date(2026, 5, 12)
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=anchor_date,
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 12, 16, 0, 0),
            )
        ]
    )
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 회복",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="90000",
                target_price_value=90_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/resolved",
                source_id="resolved",
                identity_key="resolved",
            ),
            Report(
                stock_name="매핑없는종목",
                stock_code="351020",
                title="KRX 메타데이터 없음",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 30, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=anchor_date,
                target_price_raw="10000",
                target_price_value=10_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/unresolved",
                source_id="unresolved",
                identity_key="unresolved",
            ),
        ]
    )
    repository.rebuild_daily_summaries(anchor_date)
    requested_isu_codes: list[str] = []

    def fake_fetch(**kwargs) -> KrxDataMarketDryRunResult:
        requested_isu_codes.append(kwargs["params"]["isuCd"])
        return KrxDataMarketDryRunResult(
            endpoint=kwargs["endpoint"],
            params=kwargs["params"],
            row_count=1,
            field_keys=("INVST_TP_NM", "NETBID_TRDVOL", "NETBID_TRDVAL"),
            rows=(
                {
                    "INVST_TP_NM": "외국인",
                    "NETBID_TRDVOL": "1",
                    "NETBID_TRDVAL": "2",
                },
            ),
            first_row={
                "INVST_TP_NM": "외국인",
                "NETBID_TRDVOL": "1",
                "NETBID_TRDVAL": "2",
            },
        )

    monkeypatch.setattr(cli_module, "fetch_krx_data_market_endpoint", fake_fetch)

    exit_code = _run_scheduled_krx_mentioned_flow_backfill(
        config,
        repository,
        anchor_date=anchor_date,
        lookback_days=1,
        mention_threshold=1,
        max_calls=0,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert requested_isu_codes == ["KR7005930003"]
    assert payload["plan"]["unresolved_stock_codes"] == ["351020"]
    assert payload["plan"]["dates"][0]["stock_codes"] == ["005930"]
    assert payload["result"]["skipped_unresolved_stock_count"] == 1
    assert repository.list_stock_investor_flow_daily(anchor_date, "005930")
    assert repository.list_stock_investor_flow_daily(anchor_date, "351020") == []
    assert events[0].event_type == "scheduled-mentioned-flow-backfill"
    assert events[0].status == "completed_with_warnings"
    assert "unresolved_stock_codes=351020" in events[0].detail


def test_scheduled_krx_mentioned_flow_backfill_skips_before_market_close(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _KrxMentionedFlowTooEarlyDateTime)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = _run_scheduled_krx_mentioned_flow_backfill(
        config,
        repository,
        anchor_date=None,
        lookback_days=31,
        mention_threshold=1,
        max_calls=300,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=False,
        as_json=False,
    )

    output = capsys.readouterr().out
    events = repository.list_recent_operation_events(limit=1)
    assert exit_code == 0
    assert "too_early" in output
    assert events[0].event_type == "scheduled-mentioned-flow-backfill"
    assert events[0].status == "skipped"


def test_krx_mentioned_flow_latest_anchor_dry_run_uses_each_stocks_last_report_date(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()
    _upsert_test_krx_stock_metadata(repository, date(2026, 5, 12), ["000660", "005930"])
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="이전 리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 8, 9, 0, 0),
                collected_at=datetime(2026, 5, 8, 16, 0, 0),
                business_date=date(2026, 5, 8),
                target_price_raw="90000",
                target_price_value=90_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/latest-anchor-old",
                source_id="latest-anchor-old",
                identity_key="latest-anchor-old",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="최신 리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 12, 9, 0, 0),
                collected_at=datetime(2026, 5, 12, 16, 0, 0),
                business_date=date(2026, 5, 12),
                target_price_raw="92000",
                target_price_value=92_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/latest-anchor-new",
                source_id="latest-anchor-new",
                identity_key="latest-anchor-new",
            ),
            Report(
                stock_name="SK하이닉스",
                stock_code="000660",
                title="다른 종목 리포트",
                broker_name="NH투자증권",
                published_at=datetime(2026, 5, 11, 9, 0, 0),
                collected_at=datetime(2026, 5, 11, 16, 0, 0),
                business_date=date(2026, 5, 11),
                target_price_raw="300000",
                target_price_value=300_000,
                opinion_raw="Buy",
                opinion_normalized=Opinion.BUY.value,
                source_url="https://stock.naver.com/research/company/latest-anchor-other",
                source_id="latest-anchor-other",
                identity_key="latest-anchor-other",
            ),
        ]
    )

    exit_code = _run_krx_mentioned_flow_latest_anchor_backfill(
        config,
        repository,
        from_date=None,
        to_date=None,
        lookback_days=4,
        max_calls=0,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=True,
        confirm=False,
        i_backed_up=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    calls = [(item["business_date"], item["stock_code"], item["anchor_date"]) for item in payload["calls"]]
    assert exit_code == 0
    assert ("2026-05-12", "005930", "2026-05-12") in calls
    assert ("2026-05-11", "005930", "2026-05-12") in calls
    assert ("2026-05-08", "005930", "2026-05-08") not in calls
    assert ("2026-05-11", "000660", "2026-05-11") in calls
    assert ("2026-05-08", "000660", "2026-05-11") in calls


def test_krx_mentioned_flow_latest_anchor_requires_backup_confirmation_for_live_run(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_ID", "id")
    monkeypatch.setenv("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD", "pw")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    exit_code = _run_krx_mentioned_flow_latest_anchor_backfill(
        config,
        repository,
        from_date=None,
        to_date=None,
        lookback_days=31,
        max_calls=300,
        sleep_seconds=0,
        allow_warnings=False,
        skip_existing=True,
        dry_run=False,
        confirm=False,
        i_backed_up=False,
        as_json=False,
    )

    assert exit_code == 2
    assert "db-backup" in capsys.readouterr().out


def test_krx_backfill_missing_dry_run_lists_only_missing_business_dates(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import StockMarketDailySnapshot

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=datetime(2026, 5, 7).date(),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 7, 18, 0, 0),
            )
        ]
    )

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=2,
        to_date=datetime(2026, 5, 7).date(),
        max_dates=None,
        sleep_seconds=0,
        confirm=False,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would fetch 2 missing KRX endpoint snapshot(s)." in output
    assert "- 2026-05-06: stock-kospi-daily" in output
    assert "- 2026-05-07: stock-kospi-daily" in output


def test_krx_backfill_missing_dry_run_json_reports_plan(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=2,
        to_date=datetime(2026, 5, 7).date(),
        max_dates=1,
        sleep_seconds=0,
        confirm=False,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=True,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["surface"] == "krx-backfill-missing-plan"
    assert payload["read_only"] is True
    assert payload["dry_run"] is True
    assert payload["endpoint_selector"] == "stock-kospi-daily"
    assert payload["missing_endpoint_count"] == 1
    assert payload["business_dates_with_missing_data"] == 1
    assert payload["plan"] == [
        {
            "business_date": "2026-05-07",
            "missing_endpoints": ["stock-kospi-daily"],
        }
    ]


def test_krx_backfill_missing_json_rejects_live_run_before_fetch(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=1,
        to_date=datetime(2026, 5, 8).date(),
        max_dates=1,
        sleep_seconds=0,
        confirm=True,
        backup_confirmed=True,
        allow_large_batch=False,
        dry_run=False,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["surface"] == "krx-backfill-missing-plan"
    assert "--dry-run" in payload["error"]
    assert repository.list_recent_operation_events(limit=1) == []


def test_krx_backfill_missing_skips_2025_year_end_market_holidays(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="daily",
        lookback_days=7,
        to_date=date(2026, 1, 2),
        max_dates=3,
        sleep_seconds=0,
        confirm=False,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "- 2026-01-02:" in output
    assert "- 2025-12-30:" in output
    assert "- 2025-12-29:" in output
    assert "2025-12-31" not in output
    assert "2026-01-01" not in output


def test_krx_backfill_missing_fetches_only_missing_endpoints(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    calls: list[tuple[str, str]] = []

    def fake_fetch_snapshot(*_args, **kwargs) -> int:
        calls.append((kwargs["endpoint_selector"], kwargs["business_date"].isoformat()))
        return 0

    monkeypatch.setattr(cli_module, "_run_krx_fetch_snapshot", fake_fetch_snapshot)

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="daily",
        lookback_days=1,
        to_date=datetime(2026, 5, 8).date(),
        max_dates=None,
        sleep_seconds=0,
        confirm=True,
        backup_confirmed=True,
        allow_large_batch=False,
        dry_run=False,
    )

    assert exit_code == 0
    assert calls == [
        ("etf-daily", "2026-05-08"),
        ("stock-kospi-daily", "2026-05-08"),
        ("stock-kosdaq-daily", "2026-05-08"),
        ("index-krx-daily", "2026-05-08"),
        ("index-kospi-daily", "2026-05-08"),
        ("index-kosdaq-daily", "2026-05-08"),
    ]
    output = capsys.readouterr().out
    event = repository.list_recent_operation_events(limit=1)[0]
    assert "Prepared to fetch 6 missing KRX endpoint snapshot(s)." in output
    assert "Completed KRX backfill: dates=1, endpoints=6, incomplete_endpoints=6." in output
    assert event.event_type == "backfill-missing"
    assert event.status == "empty"
    assert "incomplete_endpoints=6" in event.detail


def test_krx_backfill_missing_requires_confirm_for_real_calls(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=1,
        to_date=datetime(2026, 5, 8).date(),
        max_dates=1,
        sleep_seconds=0,
        confirm=False,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing KRX backfill without --confirm" in output


def test_krx_backfill_missing_requires_backup_confirmation_for_real_calls(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("STOCK_MONITOR_KRX_AUTH_KEY", "secret")
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="stock-kospi-daily",
        lookback_days=1,
        to_date=datetime(2026, 5, 8).date(),
        max_dates=1,
        sleep_seconds=0,
        confirm=True,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing KRX backfill without --i-backed-up" in output


def test_krx_backfill_missing_refuses_large_batches_without_override(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = _run_krx_backfill_missing(
        config,
        repository,
        endpoint_selector="daily",
        lookback_days=20,
        to_date=datetime(2026, 5, 8).date(),
        max_dates=6,
        sleep_seconds=0,
        confirm=False,
        backup_confirmed=False,
        allow_large_batch=False,
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Refusing KRX backfill above 5 business dates" in output


def test_krx_baseline_analysis_reports_coverage_and_source_lanes(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2025, 12, 4, 9, 0, 0),
            component="krx",
            event_type="backfill-missing",
            status="empty",
            business_date=date(2025, 12, 4),
            detail="endpoint=daily; dates=1; endpoints=6; incomplete_endpoints=6",
        )
    )

    exit_code = _run_krx_baseline_analysis(
        config,
        repository,
        lookback_days=3,
        to_date=date(2025, 12, 4),
        max_missing_dates=2,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX baseline analysis" in output
    assert "stock_market_daily" in output
    assert "KRX OpenAPI" in output
    assert "KRX Data Marketplace" in output
    assert "broad scheduled ingest disabled; narrow [12009] mentioned-stock 31-day backfill is the only automatic exception" in output
    assert "anchor-date report-mentioned stocks only" in output
    assert "Botasaurus/browser probe" in output
    assert "retention-days 550" in output
    assert "Recent KRX backfill observations" in output
    assert "backfill-missing | empty | 2025-12-04" in output


def test_krx_baseline_analysis_json_includes_recent_backfill_observations(tmp_path, capsys) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2025, 12, 4, 9, 0, 0),
            component="krx",
            event_type="fetch-snapshot",
            status="empty",
            business_date=date(2025, 12, 4),
            detail="endpoint=stock-kospi-daily; rows=0",
        )
    )

    exit_code = _run_krx_baseline_analysis(
        config,
        repository,
        lookback_days=3,
        to_date=date(2025, 12, 4),
        max_missing_dates=2,
        as_json=True,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["recent_backfill_observations"][0]["event_type"] == "fetch-snapshot"
    assert payload["recent_backfill_observations"][0]["status"] == "empty"
    assert payload["recent_backfill_observations"][0]["business_date"] == "2025-12-04"


def test_krx_query_snapshot_prints_stored_stock_rows(tmp_path, capsys) -> None:
    from stock_monitor.db.repository import StockMonitorRepository
    from stock_monitor.models import StockMarketDailySnapshot

    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=datetime(2026, 5, 7).date(),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100000,
                change_percent=1.25,
                volume=1000,
                turnover=2000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    exit_code = cli_module._run_krx_query_snapshot(
        repository,
        view="stocks",
        business_date=datetime(2026, 5, 7).date(),
        market="KOSPI",
        series=None,
        limit=10,
        as_json=False,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "KRX stock snapshots (2026-05-07)" in output
    assert "stock_code=005930" in output


def test_refresh_industry_caches_naver_industry_metadata(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_fetch_industry_memberships(*_args, **_kwargs):
        from stock_monitor.fetch.naver_stock_theme import NaverIndustryFetchResult
        from stock_monitor.models import StockMetadata

        return NaverIndustryFetchResult(
            industry_code="1",
            industry_name="반도체",
            metadata_items=(
                StockMetadata(
                    stock_code="005930",
                    stock_name="삼성전자",
                    sector_code="1",
                    sector_name="반도체",
                    updated_at=datetime(2026, 5, 8, 9, 0, 0),
                    source="naver_industry",
                ),
            ),
        )

    monkeypatch.setattr(cli_module, "fetch_stock_industry_memberships", fake_fetch_industry_memberships)

    result = cli_module._run_refresh_industry(
        config,
        repository,
        industry_code="1",
        page_size=50,
        max_pages=1,
    )

    output = capsys.readouterr().out
    metadata = repository.get_stock_metadata("005930")
    events = repository.list_recent_operation_events(limit=1)
    assert result == 0
    assert "Industry refreshed: 반도체 (1) / 1 stocks" in output
    assert metadata is not None
    assert metadata.sector_name == "반도체"
    assert metadata.source == "naver_industry"
    assert events[0].component == "industry"


def test_refresh_industry_dry_run_fetches_but_does_not_write(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    def fake_fetch_industry_memberships(*_args, **_kwargs):
        from stock_monitor.fetch.naver_stock_theme import NaverIndustryFetchResult
        from stock_monitor.models import StockMetadata

        return NaverIndustryFetchResult(
            industry_code="1",
            industry_name="반도체",
            metadata_items=(
                StockMetadata(
                    stock_code="005930",
                    stock_name="삼성전자",
                    sector_code="1",
                    sector_name="반도체",
                    updated_at=datetime(2026, 5, 8, 9, 0, 0),
                    source="naver_industry",
                ),
            ),
        )

    monkeypatch.setattr(cli_module, "fetch_stock_industry_memberships", fake_fetch_industry_memberships)

    result = cli_module._run_refresh_industry(
        config,
        repository,
        industry_code="1",
        page_size=50,
        max_pages=1,
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "Industry refresh preview: 반도체 (1) / 1 stocks" in output
    assert "database writes: 0" in output
    assert "next catalog command:" in output
    assert "category-catalog add sector 1 --name \"반도체\" --source naver_industry" in output
    assert repository.get_stock_metadata("005930") is None
    assert repository.list_recent_operation_events(limit=1) == []


def test_refresh_industries_refreshes_enabled_sector_catalog_entries(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "1", "반도체", "naver_industry", True, datetime(2026, 5, 8, 9, 0, 0)),
            CategoryCatalogItem("sector", "2", "비활성", "naver_industry", False, datetime(2026, 5, 8, 9, 0, 0)),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_industry(*_args, **kwargs):
        calls.append(kwargs["industry_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_industry", fake_run_refresh_industry)

    result = cli_module._run_refresh_industries(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=False,
        confirm=True,
        delay_seconds=0,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == ["1"]
    assert "Industry refresh batch completed: refreshed=1, failed=0" in output


def test_refresh_industries_requires_confirm_for_real_run(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "1", "반도체", "naver_industry", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_industry(*_args, **kwargs):
        calls.append(kwargs["industry_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_industry", fake_run_refresh_industry)

    result = cli_module._run_refresh_industries(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=False,
        confirm=False,
        delay_seconds=0,
    )

    output = capsys.readouterr().out
    assert result == 2
    assert calls == []
    assert "without --confirm" in output
    assert repository.count_category_membership_snapshots() == 0


def test_refresh_industries_dry_run_does_not_call_network_or_write(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "1", "반도체", "naver_industry", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_industry(*_args, **kwargs):
        calls.append(kwargs["industry_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_industry", fake_run_refresh_industry)

    result = cli_module._run_refresh_industries(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=True,
        confirm=False,
        delay_seconds=2.0,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == []
    assert "Industry refresh batch preview" in output
    assert "delay_seconds: 2" in output
    assert "network calls: 0" in output
    assert repository.count_category_membership_snapshots() == 0


def test_refresh_industries_skips_naver_quote_catalog_keys(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "31", "IT서비스", "naver_quote", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_industry(*_args, **kwargs):
        calls.append(kwargs["industry_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_industry", fake_run_refresh_industry)

    result = cli_module._run_refresh_industries(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=False,
        confirm=True,
        delay_seconds=0,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == []
    assert "not a Naver upjong API code" in output
    assert "No industry catalog entries to refresh." in output


def test_refresh_industries_skips_unverified_operator_sector_catalog_keys(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "31", "IT서비스", "operator", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_industry(*_args, **kwargs):
        calls.append(kwargs["industry_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_industry", fake_run_refresh_industry)

    result = cli_module._run_refresh_industries(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=False,
        confirm=True,
        delay_seconds=0,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == []
    assert "not verified as Naver upjong API sources" in output
    assert "No industry catalog entries to refresh." in output


def test_refresh_themes_requires_confirm_for_real_run(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_theme(*_args, **kwargs):
        calls.append(kwargs["theme_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_theme", fake_run_refresh_theme)

    result = cli_module._run_refresh_themes(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=False,
        confirm=False,
        delay_seconds=0,
    )

    output = capsys.readouterr().out
    assert result == 2
    assert calls == []
    assert "without --confirm" in output
    assert repository.count_category_membership_snapshots() == 0


def test_refresh_themes_dry_run_does_not_call_network_or_write(tmp_path, monkeypatch, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, datetime(2026, 5, 8, 9, 0, 0)),
        ]
    )
    calls: list[str] = []

    def fake_run_refresh_theme(*_args, **kwargs):
        calls.append(kwargs["theme_code"])
        return 0

    monkeypatch.setattr(cli_module, "_run_refresh_theme", fake_run_refresh_theme)

    result = cli_module._run_refresh_themes(
        config,
        repository,
        enabled_only=True,
        snapshot_date=datetime(2026, 5, 8).date(),
        page_size=50,
        max_pages=1,
        dry_run=True,
        confirm=False,
        delay_seconds=2.0,
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == []
    assert "Theme refresh batch preview" in output
    assert "delay_seconds: 2" in output
    assert "database writes: 0" in output
    assert repository.count_category_membership_snapshots() == 0


def test_help_command_response_includes_practical_usage() -> None:
    message = _build_help_command_response()
    lines = message.splitlines()

    assert lines[0] == "명령어 안내"
    assert lines[1] == ""
    assert "/메모 웹뷰에 섹터별 정리 추가" in message
    assert "/체크 로그인" in message
    assert "/종목코드 삼성전자" in message
    assert "/종목검색 삼성전자" in message
    assert "/종목검색 005930" in message
    assert "/다음, /전부, /처음" in message


def test_help_command_response_supports_help_title_variant() -> None:
    message = _build_help_command_response(title="도움말 안내")
    lines = message.splitlines()

    assert lines[0] == "도움말 안내"
    assert lines[1] == ""


def test_memo_command_response_appends_local_memo(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    now = datetime(2026, 4, 30, 12, 34, 0)

    message = _build_memo_command_response(
        config,
        memo_text="웹뷰에 섹터별 정리 추가",
        now=now,
    )

    memo_path = tmp_path / "data" / "operator_memos.md"
    assert message == "메모 완료"
    assert memo_path.exists()
    assert "- [ ] 26.04.30 12:34 | 웹뷰에 섹터별 정리 추가" in memo_path.read_text(encoding="utf-8")


def test_memo_command_response_is_idempotent_by_update_id(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    state = TelegramControlState()
    now = datetime(2026, 4, 30, 12, 34, 0)

    first = _build_memo_command_response(
        config,
        memo_text="웹뷰에 섹터별 정리 추가",
        now=now,
        update_id=101,
        state=state,
    )
    second = _build_memo_command_response(
        config,
        memo_text="웹뷰에 섹터별 정리 추가",
        now=now,
        update_id=101,
        state=state,
    )

    memo_path = tmp_path / "data" / "operator_memos.md"
    memo_text = memo_path.read_text(encoding="utf-8")
    assert first == "메모 완료"
    assert second == "메모 완료"
    assert memo_text.count("웹뷰에 섹터별 정리 추가") == 1
    assert state.memo_applied_update_ids == (101,)


def test_memo_command_response_returns_usage_when_missing_text(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)

    message = _build_memo_command_response(
        config,
        memo_text=None,
        now=datetime(2026, 4, 30, 12, 34, 0),
    )

    assert "사용법" in message
    assert "/메모 웹뷰에 섹터별 정리 추가" in message


def test_operator_memo_status_snapshot_parses_status_counts(tmp_path) -> None:
    memo_path = tmp_path / "data" / "operator_memos.md"
    memo_path.parent.mkdir(parents=True)
    memo_path.write_text(
        "\n".join(
            [
                "# Operator Memos",
                "",
                "- [O] 26.05.05 19:17 | 완료된 메모",
                "- [△] 26.05.07 13:56 | 부분 구현 메모",
                "- [ ] 26.05.18 12:01 | 값 정제하기",
            ]
        ),
        encoding="utf-8",
    )

    payload = cli_module._build_operator_memo_status_snapshot(memo_path)

    assert payload["read_only"] is True
    assert payload["status_counts"] == {"done": 1, "partial": 1, "open": 1, "other": 0}
    assert payload["memo_count"] == 3
    assert [item["status"] for item in payload["open_memos"]] == ["open"]
    assert payload["open_memos"][0]["text"] == "값 정제하기"


def test_market_commentary_practice_uses_stored_reports_and_indices(tmp_path) -> None:
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
                target_price_value=100000,
                opinion_normalized=Opinion.BUY.value,
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
                close_index=2750.12,
                change_percent=0.45,
            ),
            MarketIndexDailySnapshot(
                business_date=business_date,
                index_series="KOSDAQ",
                index_class="주가지수",
                index_name="코스닥",
                fetched_at=now,
                close_index=890.34,
                change_percent=-0.22,
            ),
        ]
    )

    payload = cli_module._build_market_commentary_practice_snapshot(config, repository, business_date)

    assert payload["read_only"] is True
    assert payload["business_date"] == "2026-05-18"
    assert [item["phase"] for item in payload["comments"]] == ["opening", "midday", "preclose"]
    assert all("매수" not in item["comment"] and "매도" not in item["comment"] for item in payload["comments"])
    assert payload["comments"][0]["comment"] == ""
    assert "테스트전자 리포트 집중" in payload["comments"][1]["comment"]
    assert "KOSPI +0.45%" in payload["market_reference"]


def test_market_commentary_practice_can_use_paced_naver_intraday_quotes(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 18, 9, 5, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="코드있음A",
                stock_code="000001",
                title="A 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
            Report(
                stock_name="코드있음A",
                stock_code="000001",
                title="A 리포트2",
                broker_name="테스트증권2",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
            Report(
                stock_name="코드없음B",
                stock_code=None,
                title="B 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    searched: list[str] = []
    fetched: list[str] = []
    sleeps: list[float] = []

    def fake_search(query: str, **_kwargs):
        searched.append(query)
        return [cli_module.StockCodeLookupEntry("000002", "코드없음B", "코스피", "https://stock.naver.com/item/000002")]

    def fake_quote(stock_code: str, **_kwargs):
        fetched.append(stock_code)
        if stock_code == "000001":
            return StockQuoteSnapshot(
                stock_code="000001",
                stock_name="코드있음A",
                sector_code="1",
                sector_name="테스트",
                current_price=10_500,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 18, 12, 1, 0),
                prev_close_price=10_000,
                prev_change_price=500,
                prev_change_rate=5.0,
                trade_amount=80_000_000_000,
                trade_volume=1_000_000,
            )
        return StockQuoteSnapshot(
            stock_code="000002",
            stock_name="코드없음B",
            sector_code="1",
            sector_name="테스트",
            current_price=20_000,
            market_status="OPEN",
            trade_time=datetime(2026, 5, 18, 12, 1, 1),
            prev_close_price=20_000,
            prev_change_price=0,
            prev_change_rate=0.0,
            trade_amount=10_000_000_000,
            trade_volume=500_000,
        )

    monkeypatch.setattr(cli_module, "fetch_stock_code_candidates", fake_search)
    monkeypatch.setattr(cli_module, "fetch_stock_quote_snapshot", fake_quote)
    monkeypatch.setattr(cli_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    payload = cli_module._build_market_commentary_practice_snapshot(
        config,
        repository,
        business_date,
        include_intraday_quotes=True,
        intraday_quote_limit=2,
        intraday_quote_delay_seconds=1.0,
    )

    assert searched == ["코드없음B"]
    assert fetched == ["000001", "000002"]
    assert sleeps == [1.0]
    assert payload["live_fetch"] is True
    quote_reference = payload["intraday_quote_reference"]
    assert quote_reference["live_fetch"] is True
    assert quote_reference["source"] == "naver_quote"
    assert quote_reference["limit"] == 2
    assert quote_reference["items"][0]["stock_code"] == "000001"
    assert quote_reference["items"][0]["trade_amount"] == 80_000_000_000
    assert quote_reference["items"][0]["change_percent"] == 5.0
    midday = payload["comments"][1]
    assert "Naver 장중 quote 기준" in midday["comment"]
    assert any("코드있음A 거래대금 800억" in detail for detail in midday["details"])


def test_market_commentary_practice_can_overlap_naver_market_top_with_mentions(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 18, 9, 5, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="거래대금겹침",
                stock_code="000001",
                title="A 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
            Report(
                stock_name="거래대금겹침",
                stock_code="000001",
                title="A 리포트2",
                broker_name="테스트증권2",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
            Report(
                stock_name="언급만있음",
                stock_code="000002",
                title="B 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    sleeps: list[float] = []

    market_rows = {
        "KOSPI": [
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="000001",
                stock_name="거래대금겹침",
                stock_end_type="stock",
                current_price=10_500,
                change_price=500,
                change_percent=5.0,
                trade_amount=90_000_000_000,
                trade_volume=1_200_000,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 18, 12, 1, 0),
            ),
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="122630",
                stock_name="KODEX 레버리지",
                stock_end_type="etf",
                current_price=20_000,
                change_price=-100,
                change_percent=-0.5,
                trade_amount=120_000_000_000,
                trade_volume=9_000_000,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 18, 12, 1, 0),
            ),
        ],
        "KOSDAQ": [],
    }

    def fake_market_top(market: str, **kwargs):
        if kwargs.get("page", 1) != 1:
            return []
        return market_rows[market]

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    payload = cli_module._build_market_commentary_practice_snapshot(
        config,
        repository,
        business_date,
        include_intraday_market_top=True,
        intraday_market_top_limit=20,
        intraday_market_top_page_size=10,
        intraday_market_top_delay_seconds=0.5,
    )

    assert sleeps == [0.5]
    assert payload["live_fetch"] is True
    reference = payload["intraday_market_top_reference"]
    assert reference["source"] == "naver_price_top"
    assert reference["live_fetch"] is True
    assert reference["markets"] == ["KOSPI", "KOSDAQ"]
    assert reference["items"][0]["stock_code"] == "000001"
    assert reference["items"][0]["mention_count"] == 2
    assert reference["items"][0]["trade_amount"] == 90_000_000_000
    assert all(item["stock_code"] != "122630" for item in reference["items"])
    midday = payload["comments"][1]
    assert "Naver 거래대금 상위 기준" in midday["comment"]
    assert any("거래대금겹침 거래대금 900억" in detail for detail in midday["details"])


def test_market_commentary_practice_reports_no_market_top_overlap_with_mentions(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 18, 9, 5, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="언급만있음",
                stock_code="000002",
                title="B 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_market_top(_market: str, **_kwargs):
        return [
            cli_module.NaverMarketTopStock(
                market="KOSPI",
                sort_type="PRICE_TOP",
                stock_code="000001",
                stock_name="거래대금만있음",
                stock_end_type="stock",
                current_price=10_500,
                change_price=500,
                change_percent=5.0,
                trade_amount=90_000_000_000,
                trade_volume=1_200_000,
                market_status="OPEN",
                trade_time=datetime(2026, 5, 18, 12, 1, 0),
            )
        ]

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)
    monkeypatch.setattr(cli_module.time, "sleep", lambda _seconds: None)

    payload = cli_module._build_market_commentary_practice_snapshot(
        config,
        repository,
        business_date,
        include_intraday_market_top=True,
        intraday_market_top_limit=20,
        intraday_market_top_page_size=20,
        intraday_market_top_delay_seconds=0,
    )

    reference = payload["intraday_market_top_reference"]
    assert reference["live_fetch"] is True
    assert reference["items"] == []
    assert reference["empty_reason"] == "거래대금 상위 20 안에는 언급 종목이 없습니다."
    assert "거래대금 상위 20 안에는 언급 종목이 없습니다." in payload["comments"][1]["details"]
    assert "Naver 거래대금 상위 기준" not in payload["comments"][1]["comment"]


def test_market_commentary_practice_reports_market_top_error_without_writes(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 18)
    now = datetime(2026, 5, 18, 9, 5, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="오류확인",
                stock_code="000002",
                title="오류 리포트",
                broker_name="테스트증권",
                published_at=now,
                collected_at=now,
                business_date=business_date,
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)

    def fake_market_top(_market: str, **_kwargs):
        raise RuntimeError("naver temporary failure")

    monkeypatch.setattr(cli_module, "fetch_market_top_stocks", fake_market_top)

    payload = cli_module._build_market_commentary_practice_snapshot(
        config,
        repository,
        business_date,
        include_intraday_market_top=True,
        intraday_market_top_limit=20,
        intraday_market_top_page_size=20,
        intraday_market_top_delay_seconds=0,
    )

    reference = payload["intraday_market_top_reference"]
    assert reference["writes_snapshot_tables"] is False
    assert reference["items"] == []
    assert reference["errors"]
    assert reference["empty_reason"] == "Naver 거래대금 상위 확인 중 오류가 발생했습니다."
    assert "Naver 거래대금 상위 확인 중 오류가 발생했습니다." in payload["comments"][1]["details"]
    assert payload["boundary"]["telegram_send"] is False
    assert payload["boundary"]["trading_recommendation"] is False


def test_operator_photo_inbox_status_lists_local_image_names_only(tmp_path) -> None:
    inbox = tmp_path / "data" / "operator_photo_inbox"
    inbox.mkdir(parents=True)
    (inbox / "sample.png").write_bytes(b"not a real image")
    (inbox / "ignore.txt").write_text("ignore", encoding="utf-8")

    payload = cli_module._build_operator_photo_inbox_status(inbox)

    assert payload["read_only"] is True
    assert payload["inbox_path"] == str(inbox)
    assert payload["image_file_count"] == 1
    assert payload["files"] == [{"name": "sample.png", "size_bytes": 16}]
    assert payload["uploads"] is False
    assert payload["external_sharing"] is False


def test_periodic_data_needs_audit_keeps_broad_flow_blocked(tmp_path) -> None:
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
                close_index=2750.12,
            )
        ]
    )

    payload = cli_module._build_periodic_data_needs_audit(config, repository, business_date)
    rows = {row["key"]: row for row in payload["items"]}

    assert payload["read_only"] is True
    assert payload["business_date"] == "2026-05-18"
    assert rows["krx_market_index_daily"]["current_status"] == "available"
    assert rows["krx_market_wide_flow_12008"]["policy"] == "blocked_for_automation"
    assert rows["krx_net_buy_top_12010"]["policy"] == "blocked_for_automation"
    assert rows["krx_mentioned_stock_flow_12009"]["policy"] == "allowed_for_report_mentioned_31d_only"


def test_check_command_response_records_krx_login_ack(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    message = _build_check_command_response(
        config,
        repository,
        check_text="로그인",
        now=datetime(2026, 5, 9, 16, 45, 0),
    )

    events = repository.list_recent_operation_events(limit=1)
    assert "KRX 로그인 확인 접수" in message
    assert "운영자 확인: 로그인" in message
    assert "16:50 수급 dry-run" in message
    assert events[0].component == "krx-flow"
    assert events[0].event_type == "login-ack"
    assert events[0].status == "acknowledged"


def test_check_command_response_returns_usage_for_unknown_check(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path)
    repository.initialize()

    message = _build_check_command_response(
        config,
        repository,
        check_text="다른값",
        now=datetime(2026, 5, 9, 16, 45, 0),
    )

    assert "체크 항목을 확인할 수 없습니다" in message
    assert "/체크 로그인" in message


def test_read_only_status_commands_do_not_mutate_operator_controls(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    message = cli_module._build_read_only_status_command_response(
        config,
        repository,
        command="today_status",
        now=datetime(2026, 5, 8, 9, 0, 0),
    )

    assert "오늘돌아? 안내" in message
    assert repository.list_operator_controls() == []


def test_status_command_explains_scheduler_access_denied_and_recent_poll_failure(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "build_operator_status_snapshot",
        lambda *_args, **_kwargs: {
            "health": {
                "level": "fail",
                "summary": "7 health check(s) need attention",
                "failing_checks": ["scheduler.poll.access_denied"],
            },
            "reports_by_date": [{"business_date": "2026-05-20", "count": 20}],
            "summaries_by_date": [{"business_date": "2026-05-20", "count": 20}],
            "db_path_exists": True,
            "live_observation": {
                "scheduler_metadata_status": "access_denied",
                "components": {
                    "poll": {
                        "evidence_status": "observed",
                        "last_event": {
                            "event_time": "2026-05-21T16:00:06+09:00",
                            "component": "scheduled-poll",
                            "status": "failed",
                            "detail": "Playwright is not installed.",
                        },
                    }
                },
            },
            "recent_events": [
                {
                    "event_time": "2026-05-21T16:00:06+09:00",
                    "component": "scheduled-poll",
                    "status": "failed",
                    "detail": "Playwright is not installed.",
                }
            ],
        },
    )

    message = cli_module._build_read_only_status_command_response(
        config,
        repository,
        command="operator_status",
        now=datetime(2026, 5, 21, 19, 40, 0),
    )

    assert "건강 상태: fail" in message
    assert "스케줄러 메타데이터 접근 거부" in message
    assert "최근 실패: scheduled-poll" in message
    assert "Playwright is not installed" in message


def test_progress_request_health_check_returns_immediate_diagnosis_without_queue(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    monkeypatch.setattr(
        cli_module,
        "build_operator_status_snapshot",
        lambda *_args, **_kwargs: {
            "health": {
                "level": "fail",
                "summary": "7 health check(s) need attention",
                "failing_checks": ["scheduler.poll.access_denied"],
            },
            "reports_by_date": [{"business_date": "2026-05-20", "count": 20}],
            "summaries_by_date": [{"business_date": "2026-05-20", "count": 20}],
            "live_observation": {
                "scheduler_metadata_status": "access_denied",
                "components": {
                    "poll": {
                        "evidence_status": "observed",
                        "last_event": {
                            "event_time": "2026-05-21T16:00:06+09:00",
                            "component": "scheduled-poll",
                            "status": "failed",
                            "detail": "Playwright is not installed.",
                        },
                    }
                },
            },
            "recent_events": [
                {
                    "event_time": "2026-05-21T16:00:06+09:00",
                    "component": "scheduled-poll",
                    "status": "failed",
                    "detail": "Playwright is not installed.",
                }
            ],
        },
    )

    message = cli_module._build_progress_request_command_response(
        config,
        repository=repository,
        request_text="건강상태 체크해서 왜 돌지않고있는지 리턴",
        now=datetime(2026, 5, 21, 19, 40, 0),
        update_id=123,
        state=TelegramControlState(),
    )

    assert "진행 진단" in message
    assert "오늘 리포트" in message
    assert "Playwright is not installed" in message
    assert not (tmp_path / "data" / "operator_progress_requests.jsonl").exists()


def test_progress_request_auto_runs_manual_poll_with_compact_result(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    state = TelegramControlState()
    calls = []

    def fake_run(config_arg, repository_arg, *, now, limit):
        calls.append((config_arg, repository_arg, now, limit))
        return {
            "title": "오늘 리포트 수집",
            "summary": "신규 2건 / 중복 3건 / 최신요약 2026-05-21 2개",
            "elapsed_seconds": 1.234,
            "status": "completed",
        }

    monkeypatch.setattr(cli_module, "_run_progress_manual_poll_recovery", fake_run, raising=False)

    message = cli_module._build_progress_request_command_response(
        config,
        repository=repository,
        request_text="오늘 리포트 수집해줘",
        now=datetime(2026, 5, 21, 21, 45, 0),
        update_id=124,
        state=state,
    )

    assert len(calls) == 1
    assert calls[0][3] == 200
    assert "진행 완료" in message
    assert "작업: 오늘 리포트 수집" in message
    assert "소요: 1.2초" in message
    assert "결과: 신규 2건 / 중복 3건 / 최신요약 2026-05-21 2개" in message
    assert state.has_applied_progress_update(124)
    assert not (tmp_path / "data" / "operator_progress_requests.jsonl").exists()


def test_category_catalog_cli_add_list_disable(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    add_code = cli_module._run_category_catalog(
        config,
        repository,
        Namespace(
            category_catalog_command="add",
            category_type="theme",
            category_key="505",
            name="AI반도체",
            source="test",
            group_name=None,
            priority=10,
            note=None,
            disabled=False,
        ),
    )
    list_code = cli_module._run_category_catalog(
        config,
        repository,
        Namespace(category_catalog_command="list", category_type="theme", enabled_only=True, json=False),
    )
    disable_code = cli_module._run_category_catalog(
        config,
        repository,
        Namespace(category_catalog_command="disable", category_type="theme", category_key="505"),
    )

    output = capsys.readouterr().out
    assert add_code == 0
    assert list_code == 0
    assert disable_code == 0
    assert "AI반도체" in output
    assert repository.list_category_catalog(category_type="theme", enabled_only=True) == []


def test_category_catalog_list_shows_source_and_refreshability(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    updated_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "31", "IT서비스", "naver_quote", True, updated_at),
            CategoryCatalogItem("sector", "upjong-101", "반도체", "naver_upjong", True, updated_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "naver_theme", True, updated_at),
        ]
    )

    exit_code = cli_module._run_category_catalog(
        config,
        repository,
        Namespace(category_catalog_command="list", category_type="sector", enabled_only=True, json=False),
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "source=naver_quote" in output
    assert "refreshable=N" in output
    assert "source=naver_upjong" in output
    assert "refreshable=Y" in output


def test_category_catalog_list_json_includes_refreshability(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    updated_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "31", "IT서비스", "naver_quote", True, updated_at),
            CategoryCatalogItem("sector", "upjong-101", "반도체", "naver_upjong", True, updated_at),
            CategoryCatalogItem("sector", "manual-1", "수동업종", "operator", True, updated_at),
        ]
    )

    exit_code = cli_module._run_category_catalog(
        config,
        repository,
        Namespace(category_catalog_command="list", category_type="sector", enabled_only=True, json=True),
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload[0]["source"] == "naver_quote"
    assert payload[0]["refreshable"] is False
    assert payload[0]["refresh_block_reason"] == "quote-derived sector label is not a Naver upjong API code"
    assert payload[1]["source"] == "naver_upjong"
    assert payload[1]["refreshable"] is True
    assert payload[1]["refresh_block_reason"] is None
    assert payload[2]["source"] == "operator"
    assert payload[2]["refreshable"] is False
    assert payload[2]["refresh_block_reason"] == "sector catalog source is not verified as a Naver upjong API code"


def test_category_snapshot_from_cache_promotes_existing_sector_and_theme_rows(tmp_path, capsys) -> None:
    from stock_monitor.models import StockMetadata, StockThemeMembership

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    updated_at = datetime(2026, 5, 8, 9, 0, 0)

    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="005930",
                stock_name="삼성전자",
                sector_code="G101",
                sector_name="반도체",
                updated_at=updated_at,
                source="test_sector",
            ),
            StockMetadata(
                stock_code="000000",
                stock_name="미분류",
                sector_code=None,
                sector_name="N/A",
                updated_at=updated_at,
                source="test_sector",
            ),
        ]
    )
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="AI반도체",
                stock_code="005930",
                stock_name="삼성전자",
                updated_at=updated_at,
                source="test_theme",
            )
        ]
    )

    exit_code = cli_module._run_category_snapshot_from_cache(
        config,
        repository,
        snapshot_date=datetime(2026, 5, 8).date(),
        category_type="all",
        dry_run=False,
    )

    output = capsys.readouterr().out
    catalog = repository.list_category_catalog(enabled_only=True)
    assert exit_code == 0
    assert "Created category snapshot from cache" in output
    assert repository.count_category_membership_snapshots() == 2
    assert sorted((item.category_type, item.category_key) for item in catalog) == [
        ("sector", "G101"),
        ("theme", "505"),
    ]


def test_category_snapshot_from_cache_dry_run_does_not_write(tmp_path, capsys) -> None:
    from stock_monitor.models import StockMetadata

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="005930",
                stock_name="삼성전자",
                sector_code="G101",
                sector_name="반도체",
                updated_at=datetime(2026, 5, 8, 9, 0, 0),
                source="test_sector",
            )
        ]
    )

    exit_code = cli_module._run_category_snapshot_from_cache(
        config,
        repository,
        snapshot_date=datetime(2026, 5, 8).date(),
        category_type="sector",
        dry_run=True,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Would create category snapshot from cache" in output
    assert repository.count_category_membership_snapshots() == 0
    assert repository.list_category_catalog() == []


def test_category_snapshot_status_reports_dated_snapshot_and_fallback(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, CategoryMembershipSnapshot, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체",
                broker_name="A증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=datetime(2026, 5, 8).date(),
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체 이전",
                broker_name="A증권",
                published_at=datetime(2026, 5, 7, 9, 0, 0),
                collected_at=fetched_at,
                business_date=datetime(2026, 5, 7).date(),
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            ),
        ]
    )
    repository.rebuild_daily_summaries(datetime(2026, 5, 8).date())
    repository.rebuild_daily_summaries(datetime(2026, 5, 7).date())
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem(
                category_type="sector",
                category_key="semi",
                display_name="반도체",
                source="test",
                enabled=True,
                updated_at=fetched_at,
            ),
            CategoryCatalogItem(
                category_type="theme",
                category_key="505",
                display_name="AI반도체",
                source="test",
                enabled=True,
                updated_at=fetched_at,
            ),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(
                snapshot_date=datetime(2026, 5, 8).date(),
                category_type="sector",
                category_key="semi",
                display_name="반도체",
                stock_code="005930",
                stock_name="삼성전자",
                fetched_at=fetched_at,
                source="test",
            )
        ]
    )

    exit_code = cli_module._run_category_snapshot_status(repository, limit=5, mode="all", as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "summary_dates=2 | dated=0 | sector_dated=1 | theme_dated=0 | partial=1 | fallback=2" in output
    assert "do not bulk-promote the current cache backward" in output
    assert "2026-05-08 | summaries=1 | sector=2026-05-08 | theme=fallback" in output
    assert "2026-05-07 | summaries=1 | sector=fallback | theme=fallback" in output


def test_category_snapshot_status_json_is_read_only(tmp_path, capsys) -> None:
    from stock_monitor.models import Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체",
                broker_name="A증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=datetime(2026, 5, 8).date(),
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            )
        ]
    )
    repository.rebuild_daily_summaries(datetime(2026, 5, 8).date())

    exit_code = cli_module._run_category_snapshot_status(repository, limit=5, mode="all", as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["summary"] == {
        "summary_date_count": 1,
        "dated_snapshot_count": 0,
        "sector_dated_count": 0,
        "theme_dated_count": 0,
        "partial_dated_snapshot_count": 0,
        "fallback_count": 1,
    }
    assert "source-date category snapshots" in payload["next_action"]
    assert payload["dates"][0]["business_date"] == "2026-05-08"
    assert payload["dates"][0]["sector_mapping_source"] == "latest_mapping_fallback"
    assert repository.count_category_membership_snapshots() == 0


def test_category_snapshot_status_can_filter_fallback_dates(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, CategoryMembershipSnapshot, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    for business_date in (datetime(2026, 5, 8).date(), datetime(2026, 5, 7).date()):
        repository.insert_reports(
            [
                Report(
                    stock_name="삼성전자",
                    stock_code="005930",
                    title=f"반도체 {business_date.isoformat()}",
                    broker_name="A증권",
                    published_at=datetime.combine(business_date, fetched_at.time()),
                    collected_at=fetched_at,
                    business_date=business_date,
                    target_price_raw="100,000",
                    target_price_value=100000,
                    opinion_raw="매수",
                    opinion_normalized="buy",
                )
            ]
        )
        repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "naver_industry", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    exit_code = cli_module._run_category_snapshot_status(repository, limit=5, mode="fallback", as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Category snapshot status (fallback)" in output
    assert "2026-05-07" in output
    assert "2026-05-08" not in output


def test_category_snapshot_plan_lists_fallback_dates_without_writing(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, CategoryMembershipSnapshot, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    for business_date in (datetime(2026, 5, 8).date(), datetime(2026, 5, 7).date()):
        repository.insert_reports(
            [
                Report(
                    stock_name="삼성전자",
                    stock_code="005930",
                    title=f"반도체 {business_date.isoformat()}",
                    broker_name="A증권",
                    published_at=datetime.combine(business_date, fetched_at.time()),
                    collected_at=fetched_at,
                    business_date=business_date,
                    target_price_raw="100,000",
                    target_price_value=100000,
                    opinion_raw="매수",
                    opinion_normalized="buy",
                )
            ]
        )
        repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "naver_industry", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    exit_code = cli_module._run_category_snapshot_plan(repository, limit=5, as_json=False)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Category snapshot plan" in output
    assert "fallback_date_count: 1" in output
    assert "refresh allowed dates for" in output
    assert "blocked fallback dates: 1" in output
    assert "missing snapshot types: sector=1, theme=1" in output
    assert "blocked snapshot types: sector=1, theme=1" in output
    assert "dated dry-run refresh commands: 0" in output
    assert "source-date refresh candidates: none for current source date" in output
    assert "2026-05-07" in output
    assert "source-date capture only" in output
    assert "snapshot date is not the current source date" in output
    assert "refresh-industries --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3" in output
    assert "refresh-themes --enabled --snapshot-date SOURCE_DATE --dry-run --delay-seconds 3" in output
    assert "refresh-themes --enabled --snapshot-date YYYY-MM-DD --confirm" not in output
    assert "web-view-value-qa --date YYYY-MM-DD --stock-limit 20" in output
    assert repository.count_category_membership_snapshots() == 2


def test_category_snapshot_plan_json_lists_missing_types_and_dated_dry_run_commands(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, CategoryMembershipSnapshot, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    for business_date in (datetime(2026, 5, 8).date(), datetime(2026, 5, 7).date()):
        repository.insert_reports(
            [
                Report(
                    stock_name="삼성전자",
                    stock_code="005930",
                    title=f"반도체 {business_date.isoformat()}",
                    broker_name="A증권",
                    published_at=datetime.combine(business_date, fetched_at.time()),
                    collected_at=fetched_at,
                    business_date=business_date,
                    target_price_raw="100,000",
                    target_price_value=100000,
                    opinion_raw="매수",
                    opinion_normalized="buy",
                )
            ]
        )
        repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "naver_industry", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "test", True, fetched_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(datetime(2026, 5, 7).date(), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "sector", "semi", "반도체", "005930", "삼성전자", fetched_at, "test"),
            CategoryMembershipSnapshot(datetime(2026, 5, 8).date(), "theme", "505", "AI반도체", "005930", "삼성전자", fetched_at, "test"),
        ]
    )

    exit_code = cli_module._run_category_snapshot_plan(repository, limit=5, as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["fallback_date_count"] == 1
    assert payload["plan_summary"]["source_date_capture_allowed_count"] == 0
    assert payload["plan_summary"]["source_date_capture_blocked_count"] == 1
    assert payload["plan_summary"]["source_date_capture_allowed_dates"] == []
    assert payload["plan_summary"]["missing_snapshot_type_counts"] == {"sector": 1}
    assert payload["plan_summary"]["blocked_snapshot_type_counts"] == {"sector": 1}
    assert payload["plan_summary"]["dry_run_refresh_command_count"] == 0
    assert payload["candidate_dates"] == ["2026-05-07"]
    assert payload["dates"][0]["business_date"] == "2026-05-07"
    assert payload["dates"][0]["missing_snapshot_types"] == ["sector"]
    assert payload["dates"][0]["source_date_capture_allowed"] is False
    assert payload["dates"][0]["capture_block_reasons"] == [
        "snapshot date is not the current source date; do not label current category membership as historical source-date data"
    ]
    assert payload["dates"][0]["blocked_snapshot_types"] == ["sector"]
    assert payload["dates"][0]["dry_run_commands"] == [
        "python -m stock_monitor web-view-value-qa --date 2026-05-07 --stock-limit 20",
    ]
    assert repository.count_category_membership_snapshots() == 3


def test_category_snapshot_plan_summary_counts_source_date_refresh_commands(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 5, 8)
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체",
                broker_name="A증권",
                published_at=fetched_at,
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "naver_industry", True, fetched_at),
            CategoryCatalogItem("theme", "505", "AI반도체", "naver_theme", True, fetched_at),
        ]
    )

    exit_code = cli_module._run_category_snapshot_plan(
        repository,
        limit=5,
        as_json=True,
        source_date=business_date,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["fallback_date_count"] == 1
    assert payload["plan_summary"]["source_date_capture_allowed_count"] == 1
    assert payload["plan_summary"]["source_date_capture_blocked_count"] == 0
    assert payload["plan_summary"]["source_date_capture_allowed_dates"] == ["2026-05-08"]
    assert payload["plan_summary"]["missing_snapshot_type_counts"] == {"sector": 1, "theme": 1}
    assert payload["plan_summary"]["blocked_snapshot_type_counts"] == {}
    assert payload["plan_summary"]["dry_run_refresh_command_count"] == 2
    assert payload["dates"][0]["dry_run_commands"] == [
        "python -m stock_monitor refresh-industries --enabled --snapshot-date 2026-05-08 --dry-run --delay-seconds 3",
        "python -m stock_monitor refresh-themes --enabled --snapshot-date 2026-05-08 --dry-run --delay-seconds 3",
        "python -m stock_monitor web-view-value-qa --date 2026-05-08 --stock-limit 20",
    ]


def test_category_snapshot_plan_marks_quote_based_sector_catalog_as_not_refreshable(tmp_path, capsys) -> None:
    from stock_monitor.models import CategoryCatalogItem, Report

    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 9, 0, 0)
    business_date = datetime(2026, 5, 7).date()
    repository.insert_reports(
        [
            Report(
                stock_name="삼성전자",
                stock_code="005930",
                title="반도체",
                broker_name="A증권",
                published_at=datetime.combine(business_date, fetched_at.time()),
                collected_at=fetched_at,
                business_date=business_date,
                target_price_raw="100,000",
                target_price_value=100000,
                opinion_raw="매수",
                opinion_normalized="buy",
            )
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_category_catalog_items(
        [CategoryCatalogItem("sector", "31", "IT서비스", "naver_quote", True, fetched_at)]
    )

    exit_code = cli_module._run_category_snapshot_plan(repository, limit=5, as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["enabled_sector_catalog_count"] == 1
    assert payload["refreshable_sector_catalog_count"] == 0
    assert payload["non_refreshable_sector_catalog_count"] == 1
    assert payload["warnings"] == [
        {
            "code": "sector_catalog_not_refreshable",
            "message": "enabled sector catalog entries are not verified Naver upjong sources and cannot be refreshed with refresh-industries",
        }
    ]
    assert payload["dates"][0]["missing_snapshot_types"] == ["sector", "theme"]
    assert payload["dates"][0]["source_date_capture_allowed"] is False
    assert payload["dates"][0]["blocked_snapshot_types"] == ["sector", "theme"]
    assert payload["dates"][0]["dry_run_commands"] == [
        "python -m stock_monitor web-view-value-qa --date 2026-05-07 --stock-limit 20"
    ]
    assert all("refresh-industries" not in command for command in payload["command_templates"])


def test_category_snapshot_plan_json_is_read_only(tmp_path, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    exit_code = cli_module._run_category_snapshot_plan(repository, limit=5, as_json=True)

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["read_only"] is True
    assert payload["writes_database"] is False
    assert payload["candidate_dates"] == []
    assert "python -m stock_monitor web-view-value-qa --date YYYY-MM-DD --stock-limit 20" in payload["command_templates"]


def test_webview_url_command_is_read_only_and_keeps_admin_private(tmp_path) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    message = cli_module._build_read_only_status_command_response(config, repository, command="webview_url")

    assert "http://127.0.0.1:8780" in message
    assert "관리자 화면은 Telegram으로 열지 않습니다." in message


def test_stock_lookup_command_response_returns_usage_when_missing_query() -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()

    message = _build_stock_lookup_command_response(
        config,
        state,
        query=None,
        now=datetime(2026, 4, 26, 8, 0, 0),
        lookback_days=15,
        entry_limit=5,
    )

    assert "사용법" in message
    assert "/종목검색 삼성전자" in message
    assert "/종목검색 005930" in message


def test_stock_code_command_response_returns_usage_when_missing_query() -> None:
    config = RuntimeConfig.from_env()

    message = _build_stock_code_command_response(
        config,
        query=None,
    )

    assert "사용법" in message
    assert "/종목코드 삼성전자" in message


def test_stock_selection_followup_response_requires_pending_state() -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()

    message = _build_stock_selection_followup_response(
        config,
        state,
        selection_text="1",
        now=datetime(2026, 4, 26, 8, 0, 0),
    )

    assert "선택 중인 종목이 없습니다." in message


def test_stock_selection_followup_response_reports_expired_selection() -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()
    state.set_pending_stock_selection(
        query="삼성",
        command_name="stock_lookup",
        candidates=[
            PendingStockSelectionCandidate(
                stock_code="005930",
                stock_name="삼성전자",
                market_type="코스피",
                source_url="https://stock.naver.com/domestic/stock/005930/total",
            )
        ],
        expires_at=datetime(2026, 4, 26, 8, 0, 0),
    )

    message = _build_stock_selection_followup_response(
        config,
        state,
        selection_text="1",
        now=datetime(2026, 4, 26, 8, 5, 0),
    )

    assert "종목 선택이 만료되었습니다." in message
    assert state.pending_stock_selection is None


def test_stock_lookup_command_response_prompts_for_selection_when_multiple_candidates(monkeypatch) -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()

    def fake_candidates(_query: str, *, timeout_seconds: float = 30, limit: int = 5) -> list[StockCodeLookupEntry]:  # noqa: ARG001
        return [
            StockCodeLookupEntry(
                stock_code="005930",
                stock_name="삼성전자",
                market_type="코스피",
                source_url="https://stock.naver.com/domestic/stock/005930/total",
            ),
            StockCodeLookupEntry(
                stock_code="016360",
                stock_name="삼성증권",
                market_type="코스피",
                source_url="https://stock.naver.com/domestic/stock/016360/total",
            ),
        ]

    monkeypatch.setattr(cli_module, "fetch_stock_code_candidates", fake_candidates)

    message = _build_stock_lookup_command_response(
        config,
        state,
        query="삼성",
        now=datetime(2026, 4, 26, 8, 0, 0),
        lookback_days=15,
        entry_limit=5,
    )

    assert "종목 선택 (삼성)" in message
    assert "1. 삼성전자(005930) | 코스피" in message
    assert state.pending_stock_selection is not None
    assert len(state.pending_stock_selection.candidates) == 2


def test_stock_lookup_command_response_keeps_prompt_even_for_exact_name_match(monkeypatch) -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()

    def fake_candidates(_query: str, *, timeout_seconds: float = 30, limit: int = 5) -> list[StockCodeLookupEntry]:  # noqa: ARG001
        return [
            StockCodeLookupEntry(
                stock_code="005930",
                stock_name="삼성전자",
                market_type="코스피",
                source_url="https://stock.naver.com/domestic/stock/005930/total",
            ),
            StockCodeLookupEntry(
                stock_code="016360",
                stock_name="삼성증권",
                market_type="코스피",
                source_url="https://stock.naver.com/domestic/stock/016360/total",
            ),
        ]

    monkeypatch.setattr(cli_module, "fetch_stock_code_candidates", fake_candidates)

    message = _build_stock_lookup_command_response(
        config,
        state,
        query="삼성전자",
        now=datetime(2026, 4, 26, 8, 0, 0),
        lookback_days=15,
        entry_limit=5,
    )

    assert "종목 선택 (삼성전자)" in message
    assert "1. 삼성전자(005930) | 코스피" in message
    assert state.pending_stock_selection is not None


def test_stock_lookup_command_response_does_not_treat_six_char_korean_name_as_code(monkeypatch) -> None:
    config = RuntimeConfig.from_env()
    state = TelegramControlState()

    def fake_candidates(_query: str, *, timeout_seconds: float = 30, limit: int = 5) -> list[StockCodeLookupEntry]:  # noqa: ARG001
        return [
            StockCodeLookupEntry(
                stock_code="376900",
                stock_name="로킷헬스케어",
                market_type="코스닥",
                source_url="https://stock.naver.com/domestic/stock/376900/total",
            )
        ]

    monkeypatch.setattr(cli_module, "fetch_stock_code_candidates", fake_candidates)

    message = _build_stock_lookup_command_response(
        config,
        state,
        query="로킷헬스케어",
        now=datetime(2026, 4, 26, 8, 0, 0),
        lookback_days=15,
        entry_limit=5,
    )

    assert "종목 선택 (로킷헬스케어)" in message
    assert "1. 로킷헬스케어(376900) | 코스닥" in message
    assert state.pending_stock_selection is not None
