import json
import sqlite3
from datetime import date, datetime

from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.db.schema import SCHEMA_STATEMENTS, SCHEMA_VERSION
from stock_monitor.models import (
    AppSetting,
    CategoryCatalogItem,
    CategoryMembershipSnapshot,
    EtfDailySnapshot,
    InvestorNetBuyTopDaily,
    KrxStockMetadataSnapshot,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    NewsIntelligenceRun,
    OperationEvent,
    Opinion,
    Report,
    ReportLinkedNewsEvidenceRecord,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
    StockMetadata,
    StockThemeMembership,
    WorkerState,
)


def _report(
    *,
    identity_key: str | None = None,
    source_id: str | None = "91999",
    stock_name: str = "삼성전자",
    stock_code: str | None = "005930",
    business_date: date = date(2026, 4, 24),
    collected_at: datetime = datetime(2026, 4, 25, 8, 0, 0),
    published_at: datetime = datetime(2026, 4, 24, 0, 0, 0),
    title: str = "업황 회복 가시화",
    source_url: str = "https://stock.naver.com/research/company/91999",
) -> Report:
    return Report(
        stock_name=stock_name,
        stock_code=stock_code,
        title=title,
        broker_name="NH투자증권",
        published_at=published_at,
        collected_at=collected_at,
        business_date=business_date,
        target_price_raw="92000",
        target_price_value=92000,
        opinion_raw="Buy",
        opinion_normalized=Opinion.BUY.value,
        source_url=source_url,
        source_id=source_id,
        identity_key=identity_key,
    )


def test_insert_reports_skips_existing_source_id_even_if_identity_scheme_changed(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    legacy_report = _report(identity_key="legacy-identity")
    current_report = _report()

    first = repository.insert_reports([legacy_report])
    second = repository.insert_reports([current_report])

    assert first.inserted == 1
    assert second.inserted == 0
    assert len(repository.list_reports_for_business_date(date(2026, 4, 24))) == 1


def test_repository_initializes_fk_and_schema_version(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    with repository.connect() as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
        cache_size = connection.execute("PRAGMA cache_size").fetchone()[0]
        temp_store = connection.execute("PRAGMA temp_store").fetchone()[0]
        synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        migration_rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        snapshot_tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name IN (
                      'stock_market_daily',
                      'etf_daily_snapshots',
                      'krx_stock_metadata',
                      'market_index_daily',
                      'app_settings',
                      'admin_audit_log',
                      'stock_investor_flow_daily',
                      'market_investor_flow_daily',
                      'investor_net_buy_top_daily',
                      'category_master',
                      'category_membership_snapshots'
                  )
                """
            ).fetchall()
        }

    assert foreign_keys == 1
    assert busy_timeout == 30_000
    assert cache_size == -32768
    assert temp_store == 2
    assert synchronous == 1
    assert user_version == SCHEMA_VERSION
    assert [(row["version"], row["name"]) for row in migration_rows] == [
        (1, "baseline_schema"),
        (2, "krx_market_snapshots"),
        (3, "app_settings_and_audit_log"),
        (4, "krx_investor_flow_tables"),
        (5, "category_snapshots"),
        (6, "news_intelligence_observation"),
        (7, "news_intelligence_reference_dates"),
    ]
    assert snapshot_tables == {
        "stock_market_daily",
        "etf_daily_snapshots",
        "krx_stock_metadata",
        "market_index_daily",
        "app_settings",
        "admin_audit_log",
        "stock_investor_flow_daily",
        "market_investor_flow_daily",
        "investor_net_buy_top_daily",
        "category_master",
        "category_membership_snapshots",
    }


def test_repository_initializes_news_intelligence_observation_tables(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    with repository.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert user_version == SCHEMA_VERSION
    assert "news_intelligence_runs" in tables
    assert "report_linked_news_evidence" in tables
    assert "idx_news_intelligence_runs_target_stock" in indexes
    assert "idx_report_linked_news_target_stock" in indexes
    assert "idx_report_linked_news_report_context" in indexes
    assert "idx_report_linked_news_url" in indexes


def test_repository_saves_and_lists_report_linked_news_evidence(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    repository.save_news_intelligence_observation(
        _news_intelligence_run(),
        [_news_evidence()],
    )

    runs = repository.list_news_intelligence_runs(target_date=date(2026, 6, 1), stock_code="005930")
    rows = repository.list_report_linked_news_evidence(run_id="news-run-1")

    assert len(runs) == 1
    assert runs[0].aliases == ("삼전",)
    assert runs[0].warnings == ()
    assert runs[0].live_fetch is True
    assert len(rows) == 1
    assert rows[0].evidence_case == "report_direct_positive_news"
    assert rows[0].related_report_source_ids == ("91999", "92000")
    assert rows[0].event_types == ("Contract", "Earnings")
    assert rows[0].krx_reference_date == date(2026, 5, 29)
    assert rows[0].krx_turnover == 1_200_000_000


def test_repository_news_intelligence_save_is_idempotent_within_run(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    run = _news_intelligence_run()
    evidence = _news_evidence()
    repository.save_news_intelligence_observation(run, [evidence])
    repository.save_news_intelligence_observation(run, [evidence])

    rows = repository.list_report_linked_news_evidence(run_id=run.run_id)

    assert len(rows) == 1


def test_repository_news_intelligence_preserves_repeated_runs(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    repository.save_news_intelligence_observation(
        _news_intelligence_run("news-run-1"),
        [_news_evidence(run_id="news-run-1", evidence_key="article-key")],
    )
    repository.save_news_intelligence_observation(
        _news_intelligence_run("news-run-2"),
        [_news_evidence(run_id="news-run-2", evidence_key="article-key")],
    )

    runs = repository.list_news_intelligence_runs(target_date=date(2026, 6, 1), stock_code="005930")
    rows = repository.list_report_linked_news_evidence(target_date=date(2026, 6, 1), stock_code="005930")

    assert {run.run_id for run in runs} == {"news-run-1", "news-run-2"}
    assert len(rows) == 2
    assert {row.run_id for row in rows} == {"news-run-1", "news-run-2"}


def test_repository_news_intelligence_stores_json_fields_without_public_surface(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    repository.save_news_intelligence_observation(
        _news_intelligence_run(),
        [_news_evidence()],
    )

    with repository.connect() as connection:
        run_row = connection.execute("SELECT aliases_json, warnings_json FROM news_intelligence_runs").fetchone()
        evidence_row = connection.execute(
            "SELECT related_report_source_ids_json, event_types_json FROM report_linked_news_evidence"
        ).fetchone()

    assert json.loads(run_row["aliases_json"]) == ["삼전"]
    assert json.loads(run_row["warnings_json"]) == []
    assert json.loads(evidence_row["related_report_source_ids_json"]) == ["91999", "92000"]
    assert json.loads(evidence_row["event_types_json"]) == ["Contract", "Earnings"]


def test_repository_enable_wal_mode_sets_file_database_to_wal(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    mode = repository.enable_wal_mode()

    with repository.connect() as connection:
        current_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert mode == "wal"
    assert current_mode == "wal"


def test_repository_migrate_schema_dry_run_does_not_create_database(tmp_path) -> None:
    db_path = tmp_path / "stock_monitor.db"
    repository = StockMonitorRepository(db_path)

    status = repository.migrate_schema(dry_run=True)

    assert status.current_version == 0
    assert status.target_version == SCHEMA_VERSION
    assert status.applied_versions == ()
    assert status.pending_versions == ()
    assert not db_path.exists()


def test_repository_migrate_schema_reports_existing_status(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    status = repository.migrate_schema(dry_run=True)

    assert status.current_version == SCHEMA_VERSION
    assert status.target_version == SCHEMA_VERSION
    assert status.applied_versions == (1, 2, 3, 4, 5, 6, 7)
    assert status.pending_versions == ()


def test_repository_initialize_seeds_migration_history_for_existing_v1_database(tmp_path) -> None:
    db_path = tmp_path / "stock_monitor.db"
    with sqlite3.connect(db_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            """
            INSERT INTO reports (
                identity_key,
                stock_name,
                stock_code,
                title,
                broker_name,
                published_at,
                business_date,
                opinion_normalized,
                collected_at
            ) VALUES (
                'legacy-row',
                '삼성전자',
                '005930',
                '업황 회복 가시화',
                'NH투자증권',
                '2026-04-24T00:00:00',
                '2026-04-24',
                '매수',
                '2026-04-25T08:00:00'
            )
            """
        )

    repository = StockMonitorRepository(db_path)
    repository.initialize()

    with repository.connect() as connection:
        report_count = connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        migration_rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()

    assert report_count == 1
    assert [(row["version"], row["name"]) for row in migration_rows] == [
        (1, "baseline_schema"),
        (2, "krx_market_snapshots"),
        (3, "app_settings_and_audit_log"),
        (4, "krx_investor_flow_tables"),
        (5, "category_snapshots"),
        (6, "news_intelligence_observation"),
        (7, "news_intelligence_reference_dates"),
    ]


def test_repository_initialize_is_noop_after_migration_history_seed(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.initialize()

    with repository.connect() as connection:
        migration_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    assert migration_count == 7


def test_krx_snapshot_tables_enforce_daily_source_keys(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    with repository.connect() as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO stock_market_daily (
                    business_date,
                    stock_code,
                    stock_name,
                    market,
                    close_price,
                    fetched_at,
                    source
                ) VALUES (
                    '2026-05-07',
                    '005930',
                    '삼성전자',
                    'KOSPI',
                    100000,
                    '2026-05-08T20:00:00',
                    'krx'
                )
                """
            )
            try:
                connection.execute(
                    """
                    INSERT INTO stock_market_daily (
                        business_date,
                        stock_code,
                        stock_name,
                        market,
                        close_price,
                        fetched_at,
                        source
                    ) VALUES (
                        '2026-05-07',
                        '005930',
                        '삼성전자',
                        'KOSPI',
                        100000,
                        '2026-05-08T20:01:00',
                        'krx'
                    )
                    """
                )
            except sqlite3.IntegrityError as exc:
                assert "UNIQUE" in str(exc)
            else:
                raise AssertionError("stock_market_daily should be unique by date, stock, and source")


def test_repository_upserts_stock_market_daily_snapshot(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    first = StockMarketDailySnapshot(
        business_date=date(2026, 5, 7),
        stock_code="005930",
        stock_name="삼성전자",
        market="KOSPI",
        close_price=100000,
        fetched_at=datetime(2026, 5, 8, 20, 0, 0),
    )
    second = StockMarketDailySnapshot(
        business_date=date(2026, 5, 7),
        stock_code="005930",
        stock_name="삼성전자",
        market="KOSPI",
        close_price=101000,
        fetched_at=datetime(2026, 5, 8, 20, 1, 0),
    )

    assert repository.upsert_stock_market_daily([first]) == 1
    assert repository.upsert_stock_market_daily([second]) == 1

    with repository.connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count, close_price FROM stock_market_daily WHERE stock_code = '005930'"
        ).fetchone()

    assert row["count"] == 1
    assert row["close_price"] == 101000


def test_repository_lists_stock_market_daily_by_turnover(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                turnover=10,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                turnover=30,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
        ]
    )

    rows = repository.list_stock_market_daily_by_turnover(date(2026, 5, 7), market="KOSPI", limit=1)

    assert len(rows) == 1
    assert rows[0].stock_code == "000660"


def test_repository_lists_stock_market_daily_for_codes_by_exact_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100000,
                change_percent=1.2,
                turnover=10,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                close_price=200000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=101000,
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
        ]
    )

    rows = repository.list_stock_market_daily_for_codes(date(2026, 5, 7), ["005930", "005930", ""])

    assert len(rows) == 1
    assert rows[0].stock_code == "005930"
    assert rows[0].close_price == 100000
    assert rows[0].change_percent == 1.2


def test_repository_upserts_stock_investor_flow_daily(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    first = StockInvestorFlowDaily(
        business_date=date(2026, 5, 8),
        stock_code="329180",
        stock_name="HD현대중공업",
        market="KOSPI",
        investor_type="외국인",
        sell_volume=100,
        buy_volume=130,
        net_buy_volume=30,
        sell_amount=1_000_000,
        buy_amount=1_400_000,
        net_buy_amount=400_000,
        volume_unit="주",
        amount_unit="원",
        candidate_score=80,
        candidate_reasons="report;turnover",
        fetched_at=datetime(2026, 5, 8, 16, 50, 0),
    )
    updated = StockInvestorFlowDaily(
        business_date=date(2026, 5, 8),
        stock_code="329180",
        stock_name="HD현대중공업",
        market="KOSPI",
        investor_type="외국인",
        sell_volume=120,
        buy_volume=160,
        net_buy_volume=40,
        sell_amount=1_200_000,
        buy_amount=1_700_000,
        net_buy_amount=500_000,
        volume_unit="주",
        amount_unit="원",
        candidate_score=90,
        candidate_reasons="report;turnover;theme",
        fetched_at=datetime(2026, 5, 8, 16, 55, 0),
    )

    assert repository.upsert_stock_investor_flow_daily([first]) == 1
    assert repository.upsert_stock_investor_flow_daily([updated]) == 1

    rows = repository.list_stock_investor_flow_daily(date(2026, 5, 8), "329180")

    assert len(rows) == 1
    assert rows[0].investor_type == "외국인"
    assert rows[0].net_buy_volume == 40
    assert rows[0].net_buy_amount == 500_000
    assert rows[0].candidate_score == 90
    assert rows[0].candidate_reasons == "report;turnover;theme"


def test_repository_upserts_market_flow_and_net_buy_top_tables(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 16, 50, 0)

    assert repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="KOSPI",
                investor_type="기관합계",
                sell_volume=1_000,
                buy_volume=1_300,
                net_buy_volume=300,
                sell_amount=10_000_000,
                buy_amount=13_000_000,
                net_buy_amount=3_000_000,
                volume_unit="주",
                amount_unit="원",
                fetched_at=fetched_at,
            )
        ]
    ) == 1
    assert repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 8),
                market="KOSPI",
                investor_type="외국인",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_volume=2_000,
                net_buy_amount=20_000_000,
                fetched_at=fetched_at,
            )
        ]
    ) == 1

    market_rows = repository.list_market_investor_flow_daily(date(2026, 5, 8), "KOSPI")
    top_rows = repository.list_investor_net_buy_top_daily(date(2026, 5, 8), "KOSPI", "외국인")

    assert [(row.investor_type, row.net_buy_amount) for row in market_rows] == [("기관합계", 3_000_000)]
    assert [(row.rank, row.stock_code, row.net_buy_amount) for row in top_rows] == [
        (1, "005930", 20_000_000)
    ]


def test_repository_lists_recent_investor_flow_dates(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 16, 50, 0)
    repository.upsert_market_investor_flow_daily(
        [
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 8),
                market="STK",
                investor_type="외국인",
                net_buy_amount=1_000,
                fetched_at=fetched_at,
            ),
            MarketInvestorFlowDaily(
                business_date=date(2026, 5, 7),
                market="STK",
                investor_type="외국인",
                net_buy_amount=900,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=date(2026, 5, 6),
                stock_code="005930",
                stock_name="삼성전자",
                market="STK",
                investor_type="외국인",
                net_buy_amount=800,
                fetched_at=fetched_at,
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 9),
                market="STK",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_amount=2_000,
                fetched_at=fetched_at,
            )
        ]
    )

    dates = repository.list_recent_investor_flow_dates(on_or_before=date(2026, 5, 8), limit=3)

    assert dates == [date(2026, 5, 8), date(2026, 5, 7), date(2026, 5, 6)]


def test_repository_lists_reports_for_stock_on_business_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    first = _report(identity_key="identity-a", source_id="91999")
    second = _report(
        identity_key="identity-b",
        source_id="92000",
        published_at=datetime(2026, 4, 24, 1, 0, 0),
    )
    other_stock = _report(
        identity_key="identity-c",
        source_id="92001",
        stock_name="SK하이닉스",
        stock_code="000660",
    )
    other_date = _report(
        identity_key="identity-d",
        source_id="92002",
        business_date=date(2026, 4, 25),
        published_at=datetime(2026, 4, 25, 1, 0, 0),
    )
    repository.insert_reports([first, second, other_stock, other_date])

    reports = repository.list_reports_for_stock_on_business_date(date(2026, 4, 24), "005930")

    assert [report.identity_key for report in reports] == ["identity-b", "identity-a"]


def test_repository_returns_latest_krx_snapshot_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    assert repository.latest_krx_snapshot_date() is None

    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    assert repository.latest_krx_snapshot_date() == date(2026, 5, 7)


def test_repository_counts_and_deletes_old_krx_snapshots_only(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 1, 1),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            ),
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 1, 1),
                etf_code="069500",
                etf_name="KODEX 200",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 1, 1),
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                fetched_at=datetime(2026, 1, 2, 20, 0, 0),
            )
        ]
    )
    repository.insert_reports([_report(business_date=date(2026, 1, 1), source_id="old-report")])

    counts = repository.count_krx_snapshots_before(date(2026, 2, 1))
    deleted = repository.delete_krx_snapshots_before(date(2026, 2, 1))

    assert counts == {
        "stock_market_daily": 1,
        "etf_daily_snapshots": 1,
        "market_index_daily": 1,
    }
    assert deleted == counts
    assert repository.count_krx_snapshots_before(date(2026, 2, 1)) == {
        "stock_market_daily": 0,
        "etf_daily_snapshots": 0,
        "market_index_daily": 0,
    }
    assert len(repository.list_stock_market_daily_by_turnover(date(2026, 5, 7), market="KOSPI")) == 1
    with repository.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1


def test_repository_counts_krx_snapshot_rows_for_date_by_endpoint(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 7),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )
    repository.upsert_etf_daily_snapshots(
        [
            EtfDailySnapshot(
                business_date=date(2026, 5, 7),
                etf_code="069500",
                etf_name="KODEX 200",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 5, 7),
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                fetched_at=datetime(2026, 5, 8, 20, 0, 0),
            )
        ]
    )

    counts = repository.count_krx_snapshot_rows_for_date(date(2026, 5, 7))

    assert counts["stock-kospi-daily"] == 1
    assert counts["stock-kosdaq-daily"] == 0
    assert counts["etf-daily"] == 1
    assert counts["index-kospi-daily"] == 1
    assert counts["index-kosdaq-daily"] == 0


def test_repository_initialize_fails_for_newer_database_version(tmp_path) -> None:
    db_path = tmp_path / "stock_monitor.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA user_version = 999")

    repository = StockMonitorRepository(db_path)

    try:
        repository.initialize()
    except RuntimeError as exc:
        assert "newer than supported version" in str(exc)
    else:
        raise AssertionError("initialize should reject a database newer than this code supports")


def test_repository_enforces_fragment_parent_run_fk(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    with repository.connect() as connection:
        with connection:
            try:
                connection.execute(
                    """
                    INSERT INTO daily_summary_delivery_fragments (
                        run_id,
                        fragment_index,
                        status,
                        message_text,
                        message_hash
                    ) VALUES ('missing-run', 0, 'pending', 'message', 'hash')
                    """
                )
            except sqlite3.IntegrityError as exc:
                assert "FOREIGN KEY" in str(exc)
            else:
                raise AssertionError("foreign key constraint should reject orphan fragments")


def test_insert_reports_uses_database_unique_indexes_for_legacy_duplicates(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    first = _report(identity_key="identity-a", source_id=None)
    second = _report(identity_key="identity-b", source_id=None)

    result = repository.insert_reports([first, second])

    assert result.attempted == 2
    assert result.inserted == 1
    assert len(repository.list_reports_for_business_date(date(2026, 4, 24))) == 1


def test_insert_reports_can_queue_intraday_batches_by_business_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    first = _report(identity_key="identity-a", source_id="91999")
    second = _report(
        identity_key="identity-b",
        source_id="92000",
        business_date=date(2026, 4, 25),
        collected_at=datetime(2026, 4, 25, 8, 30, 0),
        published_at=datetime(2026, 4, 25, 0, 0, 0),
    )

    result = repository.insert_reports([first, second], queue_intraday_alerts=True)

    assert result.inserted == 2
    assert len(result.intraday_batch_ids) == 2

    batches = repository.list_pending_intraday_alert_batches()
    assert len(batches) == 2
    assert [batch.business_date.isoformat() for batch in batches] == ["2026-04-24", "2026-04-25"]

    queued_reports = repository.list_reports_for_intraday_batch(batches[0].batch_id)
    assert len(queued_reports) == 1
    assert queued_reports[0].identity_key == "identity-a"


def test_insert_reports_skips_source_id_duplicates_before_intraday_queueing(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    api_report = _report(identity_key="api-identity", source_id="91999")
    dom_report = _report(
        identity_key="dom-identity",
        source_id="91999",
        source_url="https://m.stock.naver.com/research/company/91999?foo=bar",
        title="DOM fallback duplicate",
    )

    result = repository.insert_reports([api_report, dom_report], queue_intraday_alerts=True)

    assert result.attempted == 2
    assert result.inserted == 1
    assert len(result.intraday_batch_ids) == 1
    assert len(repository.list_reports_for_business_date(date(2026, 4, 24))) == 1

    queued_reports = repository.list_reports_for_intraday_batch(result.intraday_batch_ids[0])
    assert len(queued_reports) == 1
    assert queued_reports[0].identity_key == "api-identity"

    with repository.connect() as connection:
        queued_count = connection.execute("SELECT COUNT(*) FROM intraday_alert_batch_reports").fetchone()[0]
    assert queued_count == 1


def test_repository_lists_intraday_batch_summaries_by_business_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    first = _report(identity_key="identity-a", source_id="91999")
    second = _report(
        identity_key="identity-b",
        source_id="92000",
        published_at=datetime(2026, 4, 24, 1, 0, 0),
    )
    third = _report(identity_key="identity-c", source_id="92001", stock_name="SK하이닉스", stock_code="000660")
    result = repository.insert_reports([first, second, third], queue_intraday_alerts=True)
    batch_id = result.intraday_batch_ids[0]
    repository.mark_intraday_alert_batch_sent(
        batch_id,
        sent_at=datetime(2026, 4, 24, 8, 35, 0),
        message_id="telegram-message-id",
    )
    with repository.connect() as connection:
        with connection:
            connection.execute(
                "UPDATE intraday_alert_batches SET created_at = ? WHERE batch_id = ?",
                ("2026-04-24T08:30:00", batch_id),
            )

    fourth = _report(identity_key="identity-d", source_id="92002", stock_name="LG전자", stock_code="066570")
    second_result = repository.insert_reports([fourth], queue_intraday_alerts=True)
    second_batch_id = second_result.intraday_batch_ids[0]
    repository.mark_intraday_alert_batch_failed(
        second_batch_id,
        attempted_at=datetime(2026, 4, 24, 9, 5, 0),
        error_detail="network timeout",
    )
    with repository.connect() as connection:
        with connection:
            connection.execute(
                "UPDATE intraday_alert_batches SET created_at = ? WHERE batch_id = ?",
                ("2026-04-24T09:00:00", second_batch_id),
            )

    summaries = repository.list_intraday_alert_batch_summaries(date(2026, 4, 24))

    assert [item.created_at.isoformat() for item in summaries] == [
        "2026-04-24T08:30:00",
        "2026-04-24T09:00:00",
    ]
    assert summaries[0].status == "sent"
    assert summaries[0].report_count == 3
    assert summaries[0].stock_count == 2
    assert summaries[1].status == "failed"
    assert summaries[1].report_count == 1
    assert summaries[1].stock_count == 1


def test_repository_records_recent_operation_events(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    event_time = datetime(2026, 5, 6, 8, 30, 0)

    repository.record_operation_event(
        OperationEvent(
            event_time=event_time,
            component="poll",
            event_type="manual-poll",
            status="success",
            business_date=date(2026, 5, 6),
            detail="inserted=3",
        )
    )

    events = repository.list_recent_operation_events(limit=1)
    assert len(events) == 1
    assert events[0].component == "poll"
    assert events[0].event_type == "manual-poll"
    assert events[0].business_date == date(2026, 5, 6)


def test_repository_filters_operation_events_without_recent_limit_truncation(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    target_date = date(2026, 5, 20)
    target_time = datetime(2026, 5, 20, 0, 10, 0)
    repository.record_operation_event(
        OperationEvent(
            event_time=target_time,
            component="krx",
            event_type="openapi-availability-probe",
            status="not_published",
            business_date=target_date,
            detail='{"endpoint":"stock-kospi-daily","called_at":"2026-05-20T08:00:00+09:00"}',
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

    events = repository.list_operation_events(
        component="krx",
        event_type="openapi-availability-probe",
        business_date=target_date,
        limit=None,
        ascending=True,
    )

    assert len(events) == 1
    assert events[0].component == "krx"
    assert events[0].event_type == "openapi-availability-probe"
    assert events[0].business_date == target_date
    assert events[0].detail and "stock-kospi-daily" in events[0].detail


def test_repository_manages_operator_pause_and_no_run_dates(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 6, 9, 0, 0)

    repository.set_operator_pause(paused=True, updated_at=updated_at, detail="test pause")
    repository.add_run_suppressed_date(date(2026, 6, 2), updated_at=updated_at, detail="personal off")

    assert repository.is_operator_paused() is True
    assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is True
    assert repository.list_db_run_suppressed_dates() == [date(2026, 6, 2)]

    repository.set_operator_pause(paused=False, updated_at=updated_at)
    repository.remove_run_suppressed_date(date(2026, 6, 2))

    assert repository.is_operator_paused() is False
    assert repository.is_db_run_suppressed_date(date(2026, 6, 2)) is False
    assert repository.list_db_run_suppressed_dates() == []


def test_repository_upserts_worker_state_without_mixing_operator_controls(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    repository.upsert_worker_state(
        WorkerState(
            worker_name="telegram_command_loop",
            status="starting",
            updated_at=datetime(2026, 5, 6, 8, 0, 0),
            last_started_at=datetime(2026, 5, 6, 8, 0, 0),
            interval_seconds=60,
            end_time="16:30",
        )
    )
    repository.upsert_worker_state(
        WorkerState(
            worker_name="telegram_command_loop",
            status="ok",
            updated_at=datetime(2026, 5, 6, 8, 1, 0),
            last_success_at=datetime(2026, 5, 6, 8, 1, 0),
            interval_seconds=60,
            end_time="16:30",
        )
    )

    state = repository.get_worker_state("telegram_command_loop")

    assert state is not None
    assert state.status == "ok"
    assert state.last_started_at == datetime(2026, 5, 6, 8, 0, 0)
    assert state.last_success_at == datetime(2026, 5, 6, 8, 1, 0)
    assert state.interval_seconds == 60
    assert state.end_time == "16:30"
    assert repository.list_operator_controls() == []


def test_repository_clears_worker_error_on_recovery_state(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()

    repository.upsert_worker_state(
        WorkerState(
            worker_name="telegram_command_loop",
            status="error",
            updated_at=datetime(2026, 5, 6, 8, 0, 0),
            last_error_at=datetime(2026, 5, 6, 8, 0, 0),
            last_error="telegram timeout",
        )
    )
    repository.upsert_worker_state(
        WorkerState(
            worker_name="telegram_command_loop",
            status="ok",
            updated_at=datetime(2026, 5, 6, 8, 1, 0),
            last_success_at=datetime(2026, 5, 6, 8, 1, 0),
        )
    )

    state = repository.get_worker_state("telegram_command_loop")

    assert state is not None
    assert state.status == "ok"
    assert state.last_error_at is None
    assert state.last_error is None


def test_repository_stores_app_setting_and_audit_log(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 9, 10, 0, 0)

    repository.set_app_setting(
        AppSetting(
            setting_key="daily_summary_min_mention_count",
            setting_value="3",
            value_type="int",
            updated_at=updated_at,
            updated_by="test",
            detail="noise reduction",
            restart_required=False,
        ),
        audit_actor="test",
        audit_detail="noise reduction",
    )

    setting = repository.get_app_setting("daily_summary_min_mention_count")
    logs = repository.list_admin_audit_logs()

    assert setting is not None
    assert setting.setting_value == "3"
    assert setting.value_type == "int"
    assert setting.updated_by == "test"
    assert setting.detail == "noise reduction"
    assert setting.restart_required is False
    assert len(logs) == 1
    assert logs[0].setting_key == "daily_summary_min_mention_count"
    assert logs[0].old_value is None
    assert logs[0].new_value == "3"
    assert logs[0].status == "success"


def test_repository_skips_duplicate_app_setting_audit_rows(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    setting = AppSetting(
        setting_key="notification_default_limit",
        setting_value="7",
        value_type="int",
        updated_at=datetime(2026, 5, 9, 10, 0, 0),
        updated_by="test",
        detail="same value",
        restart_required=False,
    )

    repository.set_app_setting(setting, audit_actor="test", audit_detail="first")
    repository.set_app_setting(setting, audit_actor="test", audit_detail="second")

    assert len(repository.list_admin_audit_logs()) == 1


def test_repository_resumes_daily_summary_delivery_fragments(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    business_date = date(2026, 4, 24)
    started_at = datetime(2026, 4, 25, 8, 0, 0)

    run = repository.start_or_resume_daily_summary_run(
        business_date=business_date,
        channel="telegram",
        summary_signature="signature-a",
        messages=["fragment 1", "fragment 2"],
        started_at=started_at,
    )
    assert run.total_fragments == 2
    assert [fragment.fragment_index for fragment in repository.list_pending_daily_summary_fragments(run.run_id)] == [0, 1]

    repository.mark_daily_summary_fragment_sent(
        run.run_id,
        0,
        message_id="message-1",
        sent_at=datetime(2026, 4, 25, 8, 1, 0),
    )
    repository.mark_daily_summary_fragment_failed(
        run.run_id,
        1,
        error_detail="network",
        failed_at=datetime(2026, 4, 25, 8, 2, 0),
    )

    resumed = repository.start_or_resume_daily_summary_run(
        business_date=business_date,
        channel="telegram",
        summary_signature="signature-a",
        messages=["fragment 1", "fragment 2"],
        started_at=datetime(2026, 4, 25, 8, 3, 0),
    )
    pending = repository.list_pending_daily_summary_fragments(resumed.run_id)

    assert resumed.run_id == run.run_id
    assert resumed.finished_at is None
    assert resumed.last_error is None
    assert [fragment.fragment_index for fragment in pending] == [1]
    assert pending[0].message_text == "fragment 2"

    repository.mark_daily_summary_fragment_sent(
        resumed.run_id,
        1,
        message_id="message-2",
        sent_at=datetime(2026, 4, 25, 8, 4, 0),
    )
    repository.complete_daily_summary_run(resumed.run_id, finished_at=datetime(2026, 4, 25, 8, 5, 0))

    fragments = repository.list_daily_summary_fragments(resumed.run_id)
    assert [fragment.status for fragment in fragments] == ["sent", "sent"]
    assert [fragment.message_id for fragment in fragments] == ["message-1", "message-2"]


def test_repository_supersedes_pending_daily_summary_run_when_signature_changes(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    business_date = date(2026, 4, 24)

    first = repository.start_or_resume_daily_summary_run(
        business_date=business_date,
        channel="telegram",
        summary_signature="signature-a",
        messages=["old"],
        started_at=datetime(2026, 4, 25, 8, 0, 0),
    )
    second = repository.start_or_resume_daily_summary_run(
        business_date=business_date,
        channel="telegram",
        summary_signature="signature-b",
        messages=["new"],
        started_at=datetime(2026, 4, 25, 8, 5, 0),
    )

    with repository.connect() as connection:
        rows = connection.execute(
            """
            SELECT run_id, status
            FROM daily_summary_delivery_runs
            ORDER BY started_at ASC
            """
        ).fetchall()

    assert first.run_id != second.run_id
    assert [(row["run_id"], row["status"]) for row in rows] == [
        (first.run_id, "superseded"),
        (second.run_id, "pending"),
    ]


def test_repository_upserts_stock_metadata_and_builds_sector_rollup(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="1010",
            sector_name="반도체",
            updated_at=updated_at,
        )
    )

    metadata = repository.get_stock_metadata("005930")
    rollups = repository.list_sector_rollups_for_business_date(date(2026, 4, 24))

    assert repository.count_stock_metadata() == 1
    assert metadata is not None
    assert metadata.sector_name == "반도체"
    assert len(rollups) == 1
    assert rollups[0].sector_name == "반도체"
    assert rollups[0].stock_count == 1
    assert rollups[0].report_count == 2


def test_repository_sector_rollup_merges_same_sector_name_with_different_codes(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="HD현대중공업", stock_code="329180"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="한화오션",
                stock_code="042660",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="329180",
                stock_name="HD현대중공업",
                sector_code="21",
                sector_name="조선",
                updated_at=updated_at,
            ),
            StockMetadata(
                stock_code="042660",
                stock_name="한화오션",
                sector_code="27",
                sector_name="조선",
                updated_at=updated_at,
            ),
        ]
    )

    rollups = repository.list_sector_rollups_for_business_date(date(2026, 4, 24))

    assert len(rollups) == 1
    assert rollups[0].sector_name == "조선"
    assert rollups[0].stock_count == 2
    assert rollups[0].report_count == 2


def test_repository_category_catalog_and_snapshot_rollup_uses_latest_snapshot_before_date(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="삼성전자", stock_code="005930"),
            _report(identity_key="identity-b", source_id="91002", stock_name="SK하이닉스", stock_code="000660"),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem(
                category_type="sector",
                category_key="semi",
                display_name="반도체",
                source="test",
                enabled=True,
                updated_at=updated_at,
            )
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(
                snapshot_date=date(2026, 4, 20),
                category_type="sector",
                category_key="semi",
                display_name="반도체",
                stock_code="005930",
                stock_name="삼성전자",
                fetched_at=updated_at,
                source="test",
            ),
            CategoryMembershipSnapshot(
                snapshot_date=date(2026, 4, 26),
                category_type="sector",
                category_key="future",
                display_name="미래반영금지",
                stock_code="000660",
                stock_name="SK하이닉스",
                fetched_at=updated_at,
                source="test",
            ),
        ]
    )

    catalog = repository.list_category_catalog(category_type="sector", enabled_only=True)
    rollups = repository.list_category_rollups_for_business_date(date(2026, 4, 24), "sector")
    summaries = repository.list_daily_summaries_for_category(date(2026, 4, 24), "sector", "semi")

    assert catalog[0].category_key == "semi"
    assert repository.count_category_membership_snapshots() == 2
    assert [item.category_key for item in rollups] == ["semi"]
    assert rollups[0].snapshot_date == date(2026, 4, 20)
    assert rollups[0].mapping_source == "dated_snapshot"
    assert [summary.stock_code for summary in summaries] == ["005930"]


def test_repository_category_snapshot_uses_latest_snapshot_per_category_key(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="삼성전자", stock_code="005930"),
            _report(identity_key="identity-b", source_id="91002", stock_name="한화오션", stock_code="042660"),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "semi", "반도체", "test", True, updated_at),
            CategoryCatalogItem("sector", "ship", "조선", "test", True, updated_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(date(2026, 4, 20), "sector", "semi", "반도체", "005930", "삼성전자", updated_at, "test"),
            CategoryMembershipSnapshot(date(2026, 4, 21), "sector", "ship", "조선", "042660", "한화오션", updated_at, "test"),
            CategoryMembershipSnapshot(date(2026, 4, 24), "sector", "semi", "반도체", "005930", "삼성전자", updated_at, "test"),
        ]
    )

    rollups = repository.list_category_rollups_for_business_date(date(2026, 4, 24), "sector")

    assert sorted((item.category_key, item.snapshot_date) for item in rollups) == [
        ("semi", date(2026, 4, 24)),
        ("ship", date(2026, 4, 21)),
    ]


def test_repository_web_view_category_display_name_does_not_mix_conflicting_keys(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 8, 9, 0, 0)

    repository.insert_reports(
        [
            _report(
                identity_key="space-a",
                source_id="93001",
                stock_name="한화에어로스페이스",
                stock_code="012450",
                business_date=date(2026, 5, 8),
                collected_at=updated_at,
                published_at=updated_at,
            ),
            _report(
                identity_key="ship-a",
                source_id="93002",
                stock_name="한화오션",
                stock_code="042660",
                business_date=date(2026, 5, 8),
                collected_at=updated_at,
                published_at=updated_at,
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 5, 8))
    repository.upsert_category_catalog_items(
        [
            CategoryCatalogItem("sector", "27", "우주항공과국방", "test", True, updated_at),
            CategoryCatalogItem("sector", "24", "조선", "test", True, updated_at),
        ]
    )
    repository.upsert_category_membership_snapshots(
        [
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "27", "우주항공과국방", "012450", "한화에어로스페이스", updated_at, "test"),
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "27", "조선", "042660", "한화오션", updated_at, "test"),
            CategoryMembershipSnapshot(date(2026, 5, 8), "sector", "24", "우주항공과국방", "012450", "한화에어로스페이스", updated_at, "test"),
        ]
    )

    rollups = repository.list_category_rollups_by_display_name_for_business_date(date(2026, 5, 8), "sector")
    summaries = repository.list_daily_summaries_for_category_display_name(date(2026, 5, 8), "sector", "우주항공과국방")

    assert [item.display_name for item in rollups] == ["우주항공과국방", "조선"]
    assert [summary.stock_code for summary in summaries] == ["012450"]


def test_repository_lists_recent_stock_market_daily_for_single_code(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 20, 0, 0)

    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(date(2026, 5, 6), "005930", "삼성전자", "KOSPI", fetched_at, volume=100),
            StockMarketDailySnapshot(date(2026, 5, 7), "005930", "삼성전자", "KOSPI", fetched_at, volume=200),
            StockMarketDailySnapshot(date(2026, 5, 8), "005930", "삼성전자", "KOSPI", fetched_at, volume=300),
            StockMarketDailySnapshot(date(2026, 5, 8), "000660", "SK하이닉스", "KOSPI", fetched_at, volume=999),
        ]
    )

    rows = repository.list_stock_market_daily_for_code_on_or_before(date(2026, 5, 8), "005930", limit=2)

    assert [(item.business_date, item.volume) for item in rows] == [
        (date(2026, 5, 8), 300),
        (date(2026, 5, 7), 200),
    ]


def test_repository_disabled_category_is_hidden_from_snapshot_and_fallback_reads(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports([_report(identity_key="identity-a", source_id="91001")])
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="semi",
            sector_name="반도체",
            updated_at=updated_at,
        )
    )
    repository.upsert_category_catalog_items(
        [CategoryCatalogItem("sector", "반도체", "반도체", "test", False, updated_at)]
    )

    rollups = repository.list_category_rollups_for_business_date(date(2026, 4, 24), "sector")
    summaries = repository.list_daily_summaries_for_category(date(2026, 4, 24), "sector", "반도체")

    assert rollups == []
    assert summaries == []


def test_repository_category_snapshot_falls_back_to_latest_mapping_when_no_snapshot(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports([_report(identity_key="identity-a", source_id="91001")])
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_metadata(
        StockMetadata(
            stock_code="005930",
            stock_name="삼성전자",
            sector_code="1010",
            sector_name="반도체",
            updated_at=updated_at,
        )
    )

    rollups = repository.list_category_rollups_for_business_date(date(2026, 4, 24), "sector")

    assert len(rollups) == 1
    assert rollups[0].category_key == "반도체"
    assert rollups[0].mapping_source == "latest_mapping_fallback"
    assert rollups[0].snapshot_date is None


def test_repository_lists_daily_summaries_for_sector(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="HD현대중공업", stock_code="329180"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="한화오션",
                stock_code="042660",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
            _report(identity_key="identity-c", source_id="91003", stock_name="삼성전자", stock_code="005930"),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="329180",
                stock_name="HD현대중공업",
                sector_code="21",
                sector_name="조선",
                updated_at=updated_at,
            ),
            StockMetadata(
                stock_code="042660",
                stock_name="한화오션",
                sector_code="27",
                sector_name="조선",
                updated_at=updated_at,
            ),
            StockMetadata(
                stock_code="005930",
                stock_name="삼성전자",
                sector_code="1010",
                sector_name="반도체",
                updated_at=updated_at,
            ),
        ]
    )

    summaries = repository.list_daily_summaries_for_sector(date(2026, 4, 24), "조선")

    assert [summary.stock_code for summary in summaries] == ["329180", "042660"]


def test_repository_lists_sector_trend(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="HD현대중공업", stock_code="329180"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="한화오션",
                stock_code="042660",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
            _report(
                identity_key="identity-c",
                source_id="91003",
                stock_name="HD현대중공업",
                stock_code="329180",
                business_date=date(2026, 4, 25),
                published_at=datetime(2026, 4, 25, 9, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.rebuild_daily_summaries(date(2026, 4, 25))
    repository.upsert_stock_metadata_many(
        [
            StockMetadata(
                stock_code="329180",
                stock_name="HD현대중공업",
                sector_code="21",
                sector_name="조선",
                updated_at=updated_at,
            ),
            StockMetadata(
                stock_code="042660",
                stock_name="한화오션",
                sector_code="27",
                sector_name="조선",
                updated_at=updated_at,
            ),
        ]
    )

    trend = repository.list_sector_trend("조선")

    assert [(item.business_date, item.report_count, item.stock_count) for item in trend] == [
        (date(2026, 4, 25), 1, 1),
        (date(2026, 4, 24), 2, 2),
    ]


def test_repository_upserts_theme_memberships_and_builds_theme_rollup(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="로봇",
                stock_code="005930",
                stock_name="삼성전자",
                updated_at=updated_at,
            )
        ]
    )

    rollups = repository.list_theme_rollups_for_business_date(date(2026, 4, 24))

    assert repository.count_stock_theme_memberships() == 1
    assert len(rollups) == 1
    assert rollups[0].theme_code == "505"
    assert rollups[0].theme_name == "로봇"
    assert rollups[0].stock_count == 1
    assert rollups[0].report_count == 2


def test_repository_theme_rollup_merges_same_theme_name_with_different_codes(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="로봇A", stock_code="111111"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="로봇B",
                stock_code="222222",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="로봇",
                stock_code="111111",
                stock_name="로봇A",
                updated_at=updated_at,
            ),
            StockThemeMembership(
                theme_code="999",
                theme_name="로봇",
                stock_code="222222",
                stock_name="로봇B",
                updated_at=updated_at,
            ),
        ]
    )

    rollups = repository.list_theme_rollups_for_business_date(date(2026, 4, 24))

    assert len(rollups) == 1
    assert rollups[0].theme_name == "로봇"
    assert rollups[0].stock_count == 2
    assert rollups[0].report_count == 2


def test_repository_lists_daily_summaries_for_theme(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="로봇A", stock_code="111111"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="로봇B",
                stock_code="222222",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
            _report(identity_key="identity-c", source_id="91003", stock_name="반도체A", stock_code="333333"),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="로봇",
                stock_code="111111",
                stock_name="로봇A",
                updated_at=updated_at,
            ),
            StockThemeMembership(
                theme_code="999",
                theme_name="로봇",
                stock_code="222222",
                stock_name="로봇B",
                updated_at=updated_at,
            ),
            StockThemeMembership(
                theme_code="777",
                theme_name="반도체",
                stock_code="333333",
                stock_name="반도체A",
                updated_at=updated_at,
            ),
        ]
    )

    summaries = repository.list_daily_summaries_for_theme(date(2026, 4, 24), "로봇")

    assert [summary.stock_code for summary in summaries] == ["111111", "222222"]


def test_repository_lists_theme_trend_deduped_by_visible_name(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    updated_at = datetime(2026, 5, 7, 9, 0, 0)

    repository.insert_reports(
        [
            _report(identity_key="identity-a", source_id="91001", stock_name="로봇A", stock_code="111111"),
            _report(
                identity_key="identity-b",
                source_id="91002",
                stock_name="로봇B",
                stock_code="222222",
                published_at=datetime(2026, 4, 24, 10, 0, 0),
            ),
            _report(
                identity_key="identity-c",
                source_id="91003",
                stock_name="로봇A",
                stock_code="111111",
                business_date=date(2026, 4, 25),
                published_at=datetime(2026, 4, 25, 9, 0, 0),
            ),
        ]
    )
    repository.rebuild_daily_summaries(date(2026, 4, 24))
    repository.rebuild_daily_summaries(date(2026, 4, 25))
    repository.upsert_stock_theme_memberships(
        [
            StockThemeMembership(
                theme_code="505",
                theme_name="로봇",
                stock_code="111111",
                stock_name="로봇A",
                updated_at=updated_at,
            ),
            StockThemeMembership(
                theme_code="999",
                theme_name="로봇",
                stock_code="222222",
                stock_name="로봇B",
                updated_at=updated_at,
            ),
        ]
    )

    trend = repository.list_theme_trend("로봇")

    assert [(item.business_date, item.report_count, item.stock_count) for item in trend] == [
        (date(2026, 4, 25), 1, 1),
        (date(2026, 4, 24), 2, 2),
    ]


def test_repository_lists_recent_krx_snapshot_dates_from_all_snapshot_tables(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    fetched_at = datetime(2026, 5, 8, 20, 0, 0)

    repository.upsert_stock_market_daily(
        [
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 8),
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                close_price=100_000,
                turnover=500,
                fetched_at=fetched_at,
            ),
            StockMarketDailySnapshot(
                business_date=date(2026, 5, 6),
                stock_code="000660",
                stock_name="SK하이닉스",
                market="KOSPI",
                close_price=200_000,
                turnover=800,
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
                turnover=300,
                fetched_at=fetched_at,
            ),
        ]
    )
    repository.upsert_market_index_daily(
        [
            MarketIndexDailySnapshot(
                business_date=date(2026, 5, 5),
                index_series="KOSPI",
                index_class="대표",
                index_name="코스피",
                close_index=3000.1,
                turnover=1000,
                fetched_at=fetched_at,
            )
        ]
    )

    dates = repository.list_recent_krx_snapshot_dates(on_or_before=date(2026, 5, 8), limit=3)

    assert dates == [date(2026, 5, 8), date(2026, 5, 7), date(2026, 5, 6)]


def test_repository_returns_latest_krx_stock_metadata_by_stock_code(tmp_path) -> None:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    repository.upsert_krx_stock_metadata(
        [
            KrxStockMetadataSnapshot(
                business_date=date(2026, 5, 7),
                standard_code="OLD",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 7, 18, 0, 0),
            ),
            KrxStockMetadataSnapshot(
                business_date=date(2026, 5, 8),
                standard_code="KR7005930003",
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                fetched_at=datetime(2026, 5, 8, 18, 0, 0),
            ),
        ]
    )

    metadata = repository.get_latest_krx_stock_metadata("005930")

    assert metadata is not None
    assert metadata.standard_code == "KR7005930003"
    assert metadata.stock_code == "005930"


def _news_intelligence_run(run_id: str = "news-run-1") -> NewsIntelligenceRun:
    return NewsIntelligenceRun(
        run_id=run_id,
        target_date=date(2026, 6, 1),
        stock_name="삼성전자",
        stock_code="005930",
        aliases=("삼전",),
        source_mode="naver_5_lane_preview",
        page_limit=1,
        full_day_complete=False,
        live_fetch=True,
        parsed_count=99,
        deduped_count=64,
        matched_count=15,
        operator_summary_snapshot="삼성전자 운영자 전용 뉴스 판단입니다.",
        warnings=(),
        created_at=datetime(2026, 6, 1, 10, 0, 0),
    )


def _news_evidence(
    *,
    run_id: str = "news-run-1",
    evidence_key: str = "ev-1",
    url: str = "https://n.news.naver.com/article/015/0000001",
    evidence_case: str = "report_direct_positive_news",
) -> ReportLinkedNewsEvidenceRecord:
    return ReportLinkedNewsEvidenceRecord(
        run_id=run_id,
        evidence_key=evidence_key,
        target_date=date(2026, 6, 1),
        stock_code="005930",
        stock_name="삼성전자",
        related_report_count=2,
        related_report_source_ids=("91999", "92000"),
        daily_summary_presence=True,
        candidate_priority_presence=True,
        candidate_observation_priority="우선 확인",
        krx_reference_presence=True,
        krx_reference_date=date(2026, 5, 29),
        krx_turnover=1_200_000_000,
        investor_flow_presence=False,
        source_lane="mainnews",
        title="삼성전자, 대규모 공급 계약 체결",
        summary="AI 반도체 수주 증가와 장기공급계약 확대가 실적 기대를 높였다.",
        source="한국경제",
        published_at=datetime(2026, 6, 1, 9, 30, 0),
        url=url,
        matched_alias="삼성전자",
        match_reason="stock_name",
        match_scope="both",
        relevance="direct",
        relevance_reason="삼성전자가 제목과 요약에 함께 등장합니다.",
        sentiment="Positive",
        sentiment_score=100,
        event_types=("Contract", "Earnings"),
        stock_impact="Strong Positive",
        impact_explanation="리포트 근거와 직접 긍정 뉴스가 겹칩니다.",
        evidence_case=evidence_case,
        operator_recommendation="strengthen_report_candidate",
        recommendation_reason="리포트와 뉴스가 같은 방향이라 우선 확인 근거를 강화합니다.",
        operator_summary_snapshot="삼성전자 운영자 전용 뉴스 판단입니다.",
        created_at=datetime(2026, 6, 1, 10, 0, 0),
    )
