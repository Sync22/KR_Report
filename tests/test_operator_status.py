import json
import subprocess
from datetime import date, datetime

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    CategoryCatalogItem,
    DailyStockSummary,
    EtfDailySnapshot,
    MarketIndexDailySnapshot,
    OperationEvent,
    Report,
    SectorDailyRollup,
    StockMarketDailySnapshot,
    WorkerState,
)


class _RunSuppressedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 6, 2, 10, 0, 0, tzinfo=tz)


class _HealthFailDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 6, 10, 0, 0, tzinfo=tz)


class _AfterHoursDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 5, 6, 17, 0, 0, tzinfo=tz)


def test_operator_status_outputs_recent_health_snapshot(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 30, 0),
            component="poll",
            event_type="manual-poll",
            status="success",
            business_date=date(2026, 5, 6),
            detail="inserted=1",
        )
    )

    result = cli_module._run_operator_status(config, repository, as_json=False, limit=3)

    output = capsys.readouterr().out
    assert result == 0
    assert "운영 상태" in output
    assert "pending 장중 batch" in output
    assert "poll | manual-poll | success" in output


def test_operator_status_snapshot_is_gui_reusable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(
        cli_module,
        "_load_scheduler_task_statuses",
        lambda _prefix="StockMonitor": [
            {
                "task_name": "StockMonitor-Poll",
                "available": True,
                "exists": True,
                "state": "Ready",
                "enabled": True,
                "next_run_time": "2026-05-06T15:30:00",
                "last_run_time": "2026-05-06T15:00:00",
                "last_task_result": 0,
                "detail": None,
            }
        ],
    )
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.set_operator_pause(paused=True, updated_at=datetime(2026, 5, 6, 9, 0, 0), detail="test")
    repository.add_run_suppressed_date(date(2026, 6, 2), updated_at=datetime(2026, 5, 6, 9, 0, 0), detail="personal off")

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=3,
        now=datetime(2026, 5, 6, 15, 0, 0),
    )

    assert snapshot["today"] == "2026-05-06"
    assert snapshot["is_operator_paused"] is True
    assert snapshot["run_skip_reason"] == "Stock Monitor is paused by operator control."
    assert "2026-05-01" in snapshot["market_holidays"]
    assert snapshot["market_holiday_coverage"]["default_max_date"] == "2026-12-31"
    assert snapshot["market_holiday_coverage"]["configured_max_date"] == "2026-12-31"
    assert snapshot["market_holiday_coverage"]["renewal_required"] is False
    assert snapshot["backup"]["exists"] is False
    assert "no stock_monitor_*.db backup found" in snapshot["backup"]["detail"]
    assert "db-verify" in snapshot["data_safety_reminders"][0]
    assert any(action["key"] == "create_db_backup" for action in snapshot["recovery_actions"])
    assert snapshot["db_run_suppressed_date_details"]["2026-06-02"] == "personal off"
    assert snapshot["scheduler_tasks"][0]["task_name"] == "StockMonitor-Poll"
    assert snapshot["stock_metadata_count"] == 0
    assert snapshot["theme_membership_count"] == 0
    assert snapshot["sector_rollups"] == []
    assert snapshot["theme_rollups"] == []
    assert snapshot["market_mood"]["total_reports"] == 0
    assert snapshot["krx_snapshot_date"] is None
    assert snapshot["krx_top_kospi_stocks"] == []
    assert snapshot["krx_top_kosdaq_stocks"] == []
    assert snapshot["krx_top_etfs"] == []
    assert snapshot["krx_market_indices"] == []


def test_operator_status_snapshot_exposes_category_snapshot_refreshability_warning(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
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

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=3,
        now=datetime(2026, 5, 7, 10, 0, 0),
    )

    assert snapshot["category_snapshot_refreshability"]["fallback_date_count"] == 1
    assert snapshot["category_snapshot_refreshability"]["refreshable_sector_catalog_count"] == 0
    assert snapshot["category_snapshot_refreshability"]["warnings"] == [
        {
            "code": "sector_catalog_not_refreshable",
            "message": "sector fallback dates exist but no enabled sector catalog entry is verified as a Naver upjong source",
        }
    ]


def test_operator_status_builds_market_mood_snapshot() -> None:
    summaries = [
        DailyStockSummary(
            business_date=date(2026, 5, 6),
            stock_name="A",
            stock_code="000001",
            mention_count=3,
            broker_display="NH(3)",
            target_price_min=10_000,
            target_price_max=12_000,
            dominant_opinion="buy",
            generated_at=datetime(2026, 5, 6, 16, 0, 0),
        ),
        DailyStockSummary(
            business_date=date(2026, 5, 6),
            stock_name="B",
            stock_code="000002",
            mention_count=1,
            broker_display="KB(1)",
            target_price_min=None,
            target_price_max=None,
            dominant_opinion="neutral",
            generated_at=datetime(2026, 5, 6, 16, 0, 0),
        ),
    ]
    rollups = [
        SectorDailyRollup(
            business_date=date(2026, 5, 6),
            sector_name="반도체",
            sector_code="1010",
            stock_count=1,
            report_count=3,
        ),
        SectorDailyRollup(
            business_date=date(2026, 5, 6),
            sector_name="N/A",
            sector_code=None,
            stock_count=1,
            report_count=1,
        ),
    ]

    mood = cli_module._build_market_mood_snapshot(date(2026, 5, 6), summaries, rollups)

    assert mood["business_date"] == "2026-05-06"
    assert mood["total_reports"] == 4
    assert mood["stock_count"] == 2
    assert mood["active_sector_count"] == 1
    assert mood["top_sector_name"] == "반도체"
    assert mood["multi_report_stock_count"] == 1
    assert mood["target_price_stock_count"] == 1
    assert "buy_opinion_count" not in mood


def test_operator_status_snapshot_includes_krx_market_data(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 20, 0, 0)
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                change_percent=1.5,
                turnover=100,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="091990",
                stock_name="셀트리온헬스케어",
                market="KOSDAQ",
                close_price=80_000,
                change_percent=-0.5,
                turnover=90,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 7),
                etf_code="069500",
                etf_name="KODEX 200",
                close_price=40_000,
                change_percent=0.8,
                turnover=80,
                underlying_index_name="코스피 200",
                fetched_at=fetched_at,
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 5, 7),
                index_series="KOSPI",
                index_class="주가지수",
                index_name="코스피",
                close_index=3000.5,
                change_percent=0.3,
                turnover=70,
                fetched_at=fetched_at,
            )
        ]
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=3,
        now=datetime(2026, 5, 8, 15, 0, 0),
    )

    assert snapshot["krx_snapshot_date"] == "2026-05-07"
    assert snapshot["krx_top_kospi_stocks"][0]["stock_code"] == "005930"
    assert snapshot["krx_top_kosdaq_stocks"][0]["stock_code"] == "091990"
    assert snapshot["krx_top_etfs"][0]["etf_code"] == "069500"
    assert snapshot["krx_market_indices"][0]["index_name"] == "코스피"


def test_operator_status_snapshot_includes_periodic_data_needs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
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

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=3,
        now=datetime(2026, 5, 18, 15, 0, 0),
    )

    periodic = snapshot["periodic_data_needs"]
    assert periodic["read_only"] is True
    assert periodic["business_date"] == "2026-05-18"
    assert periodic["items_by_key"]["krx_market_index_daily"]["current_status"] == "available"
    assert periodic["items_by_key"]["krx_market_wide_flow_12008"]["policy"] == "blocked_for_automation"
    assert periodic["items_by_key"]["krx_net_buy_top_12010"]["policy"] == "blocked_for_automation"


def test_operator_status_json_exposes_run_guard_state(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    monkeypatch.setattr(cli_module, "datetime", _RunSuppressedDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    result = cli_module._run_operator_status(config, repository, as_json=True, limit=3)

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["is_business_day"] is True
    assert payload["is_run_suppressed"] is True
    assert payload["run_skip_reason"] == "2026-06-02 is configured as an env no-run date."


def test_operator_status_includes_scheduler_task_statuses(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(
        cli_module,
        "_load_scheduler_task_statuses",
        lambda _prefix="StockMonitor": [
            {
                "task_name": "StockMonitor-Notify",
                "available": True,
                "exists": True,
                "state": "Ready",
                "enabled": True,
                "next_run_time": "2026-05-07T08:00:00",
                "last_run_time": "2026-05-06T08:00:00",
                "last_task_result": 0,
                "detail": None,
            }
        ],
    )
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    result = cli_module._run_operator_status(config, repository, as_json=True, limit=3)

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["scheduler_tasks"][0]["task_name"] == "StockMonitor-Notify"
    assert payload["scheduler_tasks"][0]["state"] == "Ready"
    assert payload["scheduler_tasks"][0]["status_class"] in {"healthy", "stale"}


def test_operator_status_classifies_scheduler_task_statuses(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-Missing",
            "available": True,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": None,
        },
        {
            "task_name": "StockMonitor-Disabled",
            "available": True,
            "exists": True,
            "state": "Ready",
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": 0,
            "detail": None,
        },
        {
            "task_name": "StockMonitor-Notify",
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "Access denied",
        },
        {
            "task_name": "StockMonitor-Failed",
            "available": True,
            "exists": True,
            "state": "Ready",
            "enabled": True,
            "next_run_time": None,
            "last_run_time": "2026-05-06T09:00:00",
            "last_task_result": 1,
            "detail": None,
        },
        {
            "task_name": "StockMonitor-Running",
            "available": True,
            "exists": True,
            "state": "Running",
            "enabled": True,
            "next_run_time": None,
            "last_run_time": "2026-05-06T09:59:00",
            "last_task_result": 0,
            "detail": None,
        },
        {
            "task_name": "StockMonitor-Poll",
            "available": True,
            "exists": True,
            "state": "Ready",
            "enabled": True,
            "next_run_time": None,
            "last_run_time": "2026-05-06T08:00:00",
            "last_task_result": 0,
            "detail": None,
        },
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 10, 0, 0),
        scheduler_tasks=tasks,
    )

    classes = {task["task_name"]: task["status_class"] for task in snapshot["scheduler_tasks"]}
    assert classes["StockMonitor-Missing"] == "missing"
    assert classes["StockMonitor-Disabled"] == "disabled"
    assert classes["StockMonitor-Notify"] == "access_denied"
    assert classes["StockMonitor-Failed"] == "failed"
    assert classes["StockMonitor-Running"] == "running"
    assert classes["StockMonitor-Poll"] == "stale"


def test_operator_status_treats_never_run_future_task_as_healthy(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-KrxFlowLoginReminder",
            "available": True,
            "exists": True,
            "state": "Ready",
            "enabled": True,
            "next_run_time": "2026-05-11T16:45:00",
            "last_run_time": "1999-11-30T00:00:00",
            "last_task_result": 267011,
            "detail": None,
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 10, 11, 0, 0),
        scheduler_tasks=tasks,
    )

    task = snapshot["scheduler_tasks"][0]
    assert task["status_class"] == "healthy"
    assert snapshot["health"]["level"] == "ok"


def test_operator_status_health_allows_disabled_krx_login_reminder(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-KrxFlowLoginReminder",
            "available": True,
            "exists": True,
            "state": "Disabled",
            "enabled": False,
            "next_run_time": None,
            "last_run_time": "2026-05-11T16:45:00",
            "last_task_result": 0,
            "detail": None,
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 12, 17, 0, 0),
        scheduler_tasks=tasks,
    )

    assert snapshot["scheduler_tasks"][0]["status_class"] == "disabled"
    assert snapshot["health"]["level"] == "ok"
    assert "scheduler.krx-flow-login-reminder.disabled" not in snapshot["health"]["warning_checks"]


def test_operator_status_health_allows_unavailable_krx_login_reminder(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-KrxFlowLoginReminder",
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "Task not found",
            "status_class": "unavailable",
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 12, 17, 0, 0),
        scheduler_tasks=tasks,
    )

    assert snapshot["scheduler_tasks"][0]["status_class"] == "unavailable"
    assert snapshot["health"]["level"] == "ok"
    assert "scheduler.krx-flow-login-reminder.unavailable" not in snapshot["health"]["warning_checks"]


def test_operator_status_health_warns_on_optional_krx_login_reminder_access_denied(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-KrxFlowLoginReminder",
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "Access denied",
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 12, 17, 0, 0),
        scheduler_tasks=tasks,
    )

    assert snapshot["scheduler_tasks"][0]["status_class"] == "access_denied"
    assert snapshot["health"]["level"] == "warn"
    assert "scheduler.krx-flow-login-reminder.access_denied" not in snapshot["health"]["failing_checks"]
    assert "scheduler.krx-flow-login-reminder.access_denied" in snapshot["health"]["warning_checks"]


def test_operator_status_health_tracks_worker_heartbeat_stale_only_in_window(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.upsert_worker_state(
        WorkerState(
            worker_name=cli_module.TELEGRAM_COMMAND_LOOP_WORKER,
            status="ok",
            updated_at=datetime(2026, 5, 6, 8, 0, 0),
            last_success_at=datetime(2026, 5, 6, 8, 0, 0),
            interval_seconds=60,
            end_time="16:30",
        )
    )

    intraday_snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 10, 0, 0),
        scheduler_tasks=[],
    )
    after_hours_snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 17, 0, 0),
        scheduler_tasks=[],
    )

    assert intraday_snapshot["worker_states"]["telegram_command_loop"]["is_stale"] is True
    assert "telegram_worker.heartbeat_stale" in intraday_snapshot["health"]["failing_checks"]
    assert after_hours_snapshot["worker_states"]["telegram_command_loop"]["is_stale"] is False
    assert after_hours_snapshot["health"]["level"] == "ok"


def test_operator_status_does_not_mark_scheduler_stale_on_suppressed_date(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setenv("STOCK_MONITOR_RUN_SUPPRESSED_DATES", "2026-06-02")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-Poll",
            "available": True,
            "exists": True,
            "state": "Ready",
            "enabled": True,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": 0,
            "detail": None,
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 6, 2, 10, 0, 0),
        scheduler_tasks=tasks,
    )

    assert snapshot["scheduler_tasks"][0]["status_class"] == "healthy"
    assert snapshot["health"]["level"] == "ok"


def test_operator_status_health_excludes_shutdown_task_failures(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    tasks = [
        {
            "task_name": "StockMonitor-Shutdown",
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "Access denied",
        }
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 17, 0, 0),
        scheduler_tasks=tasks,
    )

    assert snapshot["scheduler_tasks"][0]["status_class"] == "access_denied"
    assert snapshot["health"]["level"] == "ok"
    assert snapshot["health"]["failing_checks"] == []


def test_operator_status_live_observation_uses_operation_events_when_scheduler_access_denied(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    for event in (
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 1, 0),
            component="notify",
            event_type="send",
            status="sent",
            business_date=date(2026, 5, 5),
            detail="source=scheduled",
        ),
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 12, 0),
            component="krx",
            event_type="backfill-missing",
            status="success",
            business_date=date(2026, 5, 5),
            detail="endpoint=daily",
        ),
        OperationEvent(
            event_time=datetime(2026, 5, 6, 10, 0, 0),
            component="poll",
            event_type="manual-poll",
            status="success",
            business_date=None,
            detail="attempted=50; inserted=0",
        ),
        OperationEvent(
            event_time=datetime(2026, 5, 6, 16, 30, 0),
            component="poll",
            event_type="time-window",
            status="skipped",
            business_date=date(2026, 5, 6),
            detail="16:30 is outside the configured polling window.",
        ),
        OperationEvent(
            event_time=datetime(2026, 5, 6, 16, 30, 0),
            component="telegram-command-loop",
            event_type="time-window",
            status="stopped",
            business_date=date(2026, 5, 6),
            detail="16:30 is after 16:30.",
        ),
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 3, 0),
            component="notify",
            event_type="fragment",
            status="failed",
            business_date=date(2026, 5, 5),
            detail="source=scheduled; run_id=run-1; fragment=2/3; message_hash=abc123; ambiguous_send=true; timed out",
        ),
    ):
        repository.record_operation_event(event)

    scheduler_tasks = [
        {
            "task_name": task_name,
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "액세스가 거부되었습니다.",
        }
        for task_name in (
            "StockMonitor-Notify",
            "StockMonitor-Poll",
            "StockMonitor-KrxDailyBackfill",
            "StockMonitor-TelegramCommands",
        )
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 17, 0, 0),
        scheduler_tasks=scheduler_tasks,
    )

    observation = snapshot["live_observation"]
    assert observation["scheduler_metadata_status"] == "access_denied"
    assert observation["components"]["notify"]["evidence_status"] == "observed"
    assert observation["components"]["poll"]["evidence_status"] == "observed"
    assert observation["components"]["poll"]["last_event"]["event_type"] == "manual-poll"
    assert observation["components"]["krx_daily_backfill"]["evidence_status"] == "attention"
    assert observation["components"]["telegram_command_loop"]["evidence_status"] == "observed"
    assert observation["telegram_timeout_trace"]["ambiguous_failure_count"] == 1
    assert observation["telegram_timeout_trace"]["latest"]["message_hash"] == "abc123"
    assert observation["telegram_timeout_trace"]["latest"]["fragment"] == "2/3"
    assert snapshot["health"]["level"] == "fail"
    assert "scheduler.notify.access_denied" in snapshot["health"]["failing_checks"]
    assert "scheduler.poll.access_denied" in snapshot["health"]["failing_checks"]
    assert "live_observation.krx_daily_backfill.incomplete_snapshot" in snapshot["health"]["warning_checks"]
    assert "telegram.timeout_trace.ambiguous_send" in snapshot["health"]["warning_checks"]
    assert observation["operator_action"] == "Run operator-status from an elevated local shell to verify Task Scheduler metadata."


def test_operator_status_live_observation_marks_future_scheduled_components_pending(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    scheduler_tasks = [
        {
            "task_name": task_name,
            "available": False,
            "exists": False,
            "state": None,
            "enabled": False,
            "next_run_time": None,
            "last_run_time": None,
            "last_task_result": None,
            "detail": "액세스가 거부되었습니다.",
        }
        for task_name in (
            "StockMonitor-Notify",
            "StockMonitor-Poll",
            "StockMonitor-KrxDailyBackfill",
            "StockMonitor-KrxMentionedFlowBackfill",
            "StockMonitor-TelegramCommands",
        )
    ]

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 13, 0, 0),
        scheduler_tasks=scheduler_tasks,
    )

    components = snapshot["live_observation"]["components"]
    assert components["krx_mentioned_flow_backfill"]["evidence_status"] == "pending"
    assert components["krx_mentioned_flow_backfill"]["last_event"] is None


def test_operator_status_warns_on_empty_krx_daily_backfill_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="backfill-missing",
            status="empty",
            business_date=date(2026, 5, 6),
            detail="endpoint=daily; dates=1; endpoints=6; incomplete_endpoints=6",
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 9, 0, 0),
        scheduler_tasks=[],
    )

    component = snapshot["live_observation"]["components"]["krx_daily_backfill"]
    assert component["evidence_status"] == "attention"
    assert component["last_event"]["status"] == "empty"
    assert "live_observation.krx_daily_backfill.empty" in snapshot["health"]["warning_checks"]


def test_operator_status_live_observation_prefers_latest_krx_event(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="backfill-missing",
            status="empty",
            business_date=date(2026, 5, 6),
            detail="endpoint=daily; dates=1; endpoints=6; incomplete_endpoints=6",
        )
    )
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 30, 0),
            component="krx",
            event_type="scheduled-daily-backfill",
            status="success",
            business_date=date(2026, 5, 6),
            detail="target=previous-business-day",
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=2,
        now=datetime(2026, 5, 6, 9, 0, 0),
        scheduler_tasks=[],
    )

    component = snapshot["live_observation"]["components"]["krx_daily_backfill"]
    assert component["evidence_status"] == "observed"
    assert component["last_event"]["status"] == "success"
    assert component["last_event"]["event_type"] == "scheduled-daily-backfill"
    assert not any(check.startswith("live_observation.krx_daily_backfill") for check in snapshot["health"]["warning_checks"])


def test_operator_status_warns_when_successful_krx_backfill_left_snapshots_incomplete(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="backfill-missing",
            status="success",
            business_date=date(2026, 5, 6),
            detail="endpoint=daily; dates=1; endpoints=6",
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 9, 0, 0),
        scheduler_tasks=[],
    )

    component = snapshot["live_observation"]["components"]["krx_daily_backfill"]
    assert component["evidence_status"] == "attention"
    assert component["last_event"]["status"] == "success"
    assert "live_observation.krx_daily_backfill.incomplete_snapshot" in snapshot["health"]["warning_checks"]


def test_operator_status_text_prints_telegram_timeout_trace(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 3, 0),
            component="notify",
            event_type="fragment",
            status="failed",
            business_date=date(2026, 5, 5),
            detail="source=scheduled; run_id=run-1; fragment=2/3; message_hash=abc123; ambiguous_send=true; timed out",
        )
    )

    result = cli_module._run_operator_status(config, repository, as_json=False, limit=5)

    output = capsys.readouterr().out
    assert result == 0
    assert "Telegram timeout trace: 1 ambiguous fragment failure" in output
    assert "fragment=2/3" in output
    assert "message_hash=abc123" in output


def test_operator_status_text_explains_strict_health_when_scheduler_access_denied(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(
        cli_module,
        "_load_scheduler_task_statuses",
        lambda _prefix="StockMonitor": [
            {
                "task_name": "StockMonitor-Notify",
                "available": False,
                "exists": False,
                "state": None,
                "enabled": False,
                "next_run_time": None,
                "last_run_time": None,
                "last_task_result": None,
                "detail": "액세스가 거부되었습니다.",
            }
        ],
    )
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 1, 0),
            component="notify",
            event_type="send",
            status="sent",
            business_date=date(2026, 5, 5),
            detail="source=scheduled",
        )
    )

    result = cli_module._run_operator_status(config, repository, as_json=False, limit=3)

    output = capsys.readouterr().out
    assert result == 0
    assert "strict health: 스케줄러 메타데이터 검증 불가" in output
    assert "당일 실행 흔적은 보조 증거" in output
    assert "실패 항목: scheduler.notify.access_denied" in output


def test_operator_status_text_prints_live_observation_attention_reason(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="backfill-missing",
            status="success",
            business_date=date(2026, 5, 6),
            detail="endpoint=daily; dates=1; endpoints=6",
        )
    )

    result = cli_module._run_operator_status(config, repository, as_json=False, limit=3)

    output = capsys.readouterr().out
    assert result == 0
    assert "krx_daily_backfill: attention(incomplete_snapshot)" in output
    assert "확인 항목: live_observation.krx_daily_backfill.incomplete_snapshot" in output


def test_operator_status_recent_events_show_krx_snapshot_attention_status(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="backfill-missing",
            status="success",
            business_date=date(2026, 5, 6),
            detail="endpoint=daily; dates=1; endpoints=6",
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 10, 0, 0),
        scheduler_tasks=[],
    )
    result = cli_module._run_operator_status(config, repository, as_json=False, limit=1)

    output = capsys.readouterr().out
    assert snapshot["recent_events"][0]["status"] == "success"
    assert snapshot["recent_events"][0]["status_display"] == "success(attention:incomplete_snapshot)"
    assert snapshot["recent_events"][0]["detail_display"] == "daily 보강: 날짜 1개, endpoint 6개"
    assert any(action["key"] == "krx_latest_snapshot_retry_later" for action in snapshot["recovery_actions"])
    assert result == 0
    assert "krx | backfill-missing | success(attention:incomplete_snapshot) | daily 보강: 날짜 1개, endpoint 6개" in output


def test_operator_status_recent_events_show_empty_krx_fetch_snapshot_attention(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 8, 15, 0),
            component="krx",
            event_type="fetch-snapshot",
            status="success",
            business_date=date(2026, 5, 6),
            detail="endpoint=stock-kospi-daily; stock_market=0; etf=0; metadata=0; index=0",
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 10, 0, 0),
        scheduler_tasks=[],
    )
    result = cli_module._run_operator_status(config, repository, as_json=False, limit=1)

    output = capsys.readouterr().out
    assert snapshot["recent_events"][0]["status"] == "success"
    assert snapshot["recent_events"][0]["status_display"] == "success(attention:empty_rows)"
    assert snapshot["recent_events"][0]["detail_display"] == "stock-kospi-daily: 저장 주식 0 / ETF 0 / 메타 0 / 지수 0"
    assert result == 0
    assert "krx | fetch-snapshot | success(attention:empty_rows)" in output


def test_operator_status_recent_events_add_readable_flow_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 6, 16, 5, 0),
            component="krx-flow",
            event_type="scheduled-mentioned-flow-backfill",
            status="completed_with_warnings",
            business_date=date(2026, 5, 6),
            detail=(
                "anchor_date=2026-05-06; lookback_days=31; stocks=7; calls=300; "
                "raw_calls=410; dropped_calls=110; stock_rows=295; warnings=0; "
                "skipped_unresolved_stock_count=2; unresolved_stock_codes=123456,234567"
            ),
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 6, 17, 0, 0),
        scheduler_tasks=[],
    )

    assert snapshot["recent_events"][0]["detail_display"] == "종목 7개, 호출 300회, 저장 295행, 잔여 110회, 미해결 코드 2개"


def test_operator_status_recent_events_add_readable_restore_smoke_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    repository.record_operation_event(
        OperationEvent(
            event_time=datetime(2026, 5, 17, 4, 33, 0),
            component="db",
            event_type="restore-smoke",
            status="success",
            business_date=None,
            detail=(
                "backup=stock_monitor_20260517_0118_test.db; "
                "copied=restore_smoke_20260517_043326.db; copy_retained=N; exit_code=0"
            ),
        )
    )

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 5, 17, 4, 40, 0),
        scheduler_tasks=[],
    )

    assert (
        snapshot["recent_events"][0]["detail_display"]
        == "restore-smoke: backup stock_monitor_20260517_0118_test.db, exit 0, copy_retained N"
    )


def test_operator_status_health_exit_returns_3_for_warn_or_fail(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _HealthFailDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    result = cli_module._run_operator_status(config, repository, as_json=True, limit=1, health_exit=True)

    payload = json.loads(capsys.readouterr().out)
    assert result == 3
    assert payload["health"]["level"] == "fail"


def test_operator_status_health_exit_returns_0_for_ok(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    monkeypatch.setattr(cli_module, "datetime", _AfterHoursDateTime)
    monkeypatch.setattr(cli_module, "_load_scheduler_task_statuses", lambda _prefix="StockMonitor": [])
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    result = cli_module._run_operator_status(config, repository, as_json=True, limit=1, health_exit=True)

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["health"]["level"] == "ok"


def test_operator_status_warns_when_default_market_holiday_coverage_nears_expiry(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("STOCK_MONITOR_DB_PATH", raising=False)
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()

    snapshot = cli_module.build_operator_status_snapshot(
        config,
        repository,
        limit=1,
        now=datetime(2026, 10, 1, 17, 0, 0),
        scheduler_tasks=[],
    )

    assert snapshot["market_holiday_coverage"]["default_max_date"] == "2026-12-31"
    assert snapshot["market_holiday_coverage"]["configured_max_date"] == "2026-12-31"
    assert snapshot["market_holiday_coverage"]["renewal_required"] is True
    assert "market_holidays.default_coverage_expiring" in snapshot["health"]["warning_checks"]
    assert snapshot["health"]["level"] == "warn"


def test_scheduler_task_status_loader_parses_powershell_json(monkeypatch) -> None:
    monkeypatch.setattr(cli_module.sys, "platform", "win32")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "task_name": "StockMonitor-Notify",
                        "available": True,
                        "exists": True,
                        "state": "Ready",
                        "enabled": True,
                        "next_run_time": "2026-05-07T08:00:00",
                        "last_run_time": "2026-05-06T08:00:00",
                        "last_task_result": 0,
                        "detail": None,
                    }
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    statuses = cli_module._load_scheduler_task_statuses("StockMonitor")

    assert statuses[0]["task_name"] == "StockMonitor-Notify"
    assert statuses[0]["exists"] is True
    assert statuses[0]["state"] == "Ready"
    assert statuses[1]["task_name"] == "StockMonitor-Poll"
    assert statuses[1]["exists"] is False


def test_scheduler_task_status_loader_uses_configured_task_prefix(monkeypatch) -> None:
    monkeypatch.setattr(cli_module.sys, "platform", "win32")

    def fake_run(command, **_kwargs):
        script = command[-1]
        assert "MyMonitor-Notify" in script
        assert "MyMonitor-Poll" in script
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    statuses = cli_module._load_scheduler_task_statuses("MyMonitor")

    assert statuses[0]["task_name"] == "MyMonitor-Notify"
    assert statuses[1]["task_name"] == "MyMonitor-Poll"
