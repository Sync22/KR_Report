from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


SCHEMA_VERSION = 9


@dataclass(frozen=True)
class SchemaMigration:
    version: int
    name: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class SchemaMigrationStatus:
    current_version: int
    target_version: int
    applied_versions: tuple[int, ...]
    pending_versions: tuple[int, ...]


BASELINE_MIGRATION_NAME = "baseline_schema"


KRX_MARKET_SNAPSHOT_MIGRATION = SchemaMigration(
    version=2,
    name="krx_market_snapshots",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS stock_market_daily (
            business_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            market TEXT NOT NULL,
            section_name TEXT,
            close_price INTEGER,
            change_amount INTEGER,
            change_percent REAL,
            open_price INTEGER,
            high_price INTEGER,
            low_price INTEGER,
            volume INTEGER,
            turnover INTEGER,
            market_cap INTEGER,
            listed_shares INTEGER,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, stock_code, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_stock_market_daily_market_date
        ON stock_market_daily (business_date, market, turnover DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_stock_market_daily_stock
        ON stock_market_daily (stock_code, business_date DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS etf_daily_snapshots (
            business_date TEXT NOT NULL,
            etf_code TEXT NOT NULL,
            etf_name TEXT NOT NULL,
            close_price INTEGER,
            change_amount INTEGER,
            change_percent REAL,
            nav REAL,
            open_price INTEGER,
            high_price INTEGER,
            low_price INTEGER,
            volume INTEGER,
            turnover INTEGER,
            market_cap INTEGER,
            net_assets_total INTEGER,
            listed_shares INTEGER,
            underlying_index_name TEXT,
            underlying_index_close REAL,
            underlying_index_change_amount REAL,
            underlying_index_change_percent REAL,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, etf_code, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_etf_daily_snapshots_turnover
        ON etf_daily_snapshots (business_date, turnover DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_etf_daily_snapshots_index
        ON etf_daily_snapshots (underlying_index_name, business_date DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS krx_stock_metadata (
            business_date TEXT NOT NULL,
            standard_code TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            stock_short_name TEXT,
            stock_english_name TEXT,
            listed_date TEXT,
            market TEXT NOT NULL,
            security_group TEXT,
            section_name TEXT,
            stock_certificate_type TEXT,
            par_value TEXT,
            listed_shares INTEGER,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, stock_code, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_krx_stock_metadata_standard_code
        ON krx_stock_metadata (standard_code)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_krx_stock_metadata_market
        ON krx_stock_metadata (market, stock_code)
        """,
        """
        CREATE TABLE IF NOT EXISTS market_index_daily (
            business_date TEXT NOT NULL,
            index_series TEXT NOT NULL,
            index_class TEXT NOT NULL,
            index_name TEXT NOT NULL,
            close_index REAL,
            change_amount REAL,
            change_percent REAL,
            open_index REAL,
            high_index REAL,
            low_index REAL,
            volume INTEGER,
            turnover INTEGER,
            market_cap INTEGER,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, index_series, index_name, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_market_index_daily_series
        ON market_index_daily (index_series, business_date DESC)
        """,
    ),
)


APP_SETTINGS_MIGRATION = SchemaMigration(
    version=3,
    name="app_settings_and_audit_log",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            value_type TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            detail TEXT,
            restart_required INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_app_settings_updated
        ON app_settings (updated_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            setting_key TEXT,
            old_value TEXT,
            new_value TEXT,
            status TEXT NOT NULL,
            detail TEXT
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_log_time
        ON admin_audit_log (event_time DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_admin_audit_log_setting
        ON admin_audit_log (setting_key, event_time DESC)
        """,
    ),
)


KRX_INVESTOR_FLOW_MIGRATION = SchemaMigration(
    version=4,
    name="krx_investor_flow_tables",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS stock_investor_flow_daily (
            business_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            market TEXT,
            investor_type TEXT NOT NULL,
            sell_volume INTEGER,
            buy_volume INTEGER,
            net_buy_volume INTEGER,
            sell_amount INTEGER,
            buy_amount INTEGER,
            net_buy_amount INTEGER,
            volume_unit TEXT,
            amount_unit TEXT,
            candidate_score INTEGER,
            candidate_reasons TEXT,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, stock_code, investor_type, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_stock_investor_flow_daily_stock
        ON stock_investor_flow_daily (stock_code, business_date DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_stock_investor_flow_daily_net_amount
        ON stock_investor_flow_daily (business_date, net_buy_amount DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS market_investor_flow_daily (
            business_date TEXT NOT NULL,
            market TEXT NOT NULL,
            investor_type TEXT NOT NULL,
            sell_volume INTEGER,
            buy_volume INTEGER,
            net_buy_volume INTEGER,
            sell_amount INTEGER,
            buy_amount INTEGER,
            net_buy_amount INTEGER,
            volume_unit TEXT,
            amount_unit TEXT,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, market, investor_type, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_market_investor_flow_daily_net_amount
        ON market_investor_flow_daily (business_date, market, net_buy_amount DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS investor_net_buy_top_daily (
            business_date TEXT NOT NULL,
            market TEXT NOT NULL,
            investor_type TEXT NOT NULL,
            rank INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            net_buy_volume INTEGER,
            net_buy_amount INTEGER,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (business_date, market, investor_type, rank, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_investor_net_buy_top_daily_stock
        ON investor_net_buy_top_daily (stock_code, business_date DESC)
        """,
    ),
)


CATEGORY_SNAPSHOT_MIGRATION = SchemaMigration(
    version=5,
    name="category_snapshots",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS category_master (
            category_type TEXT NOT NULL,
            category_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            source TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            group_name TEXT,
            priority INTEGER NOT NULL DEFAULT 100,
            note TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (category_type, category_key)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_category_master_enabled
        ON category_master (category_type, enabled, priority, display_name)
        """,
        """
        CREATE TABLE IF NOT EXISTS category_membership_snapshots (
            snapshot_date TEXT NOT NULL,
            category_type TEXT NOT NULL,
            category_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            fetched_at TEXT NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (snapshot_date, category_type, category_key, stock_code, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_category_membership_snapshots_lookup
        ON category_membership_snapshots (category_type, snapshot_date, category_key, stock_code)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_category_membership_snapshots_stock
        ON category_membership_snapshots (stock_code, category_type, snapshot_date DESC)
        """,
    ),
)


NEWS_INTELLIGENCE_OBSERVATION_MIGRATION = SchemaMigration(
    version=6,
    name="news_intelligence_observation",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS news_intelligence_runs (
            run_id TEXT PRIMARY KEY,
            target_date TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            stock_code TEXT,
            aliases_json TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            page_limit INTEGER NOT NULL,
            full_day_complete INTEGER NOT NULL,
            live_fetch INTEGER NOT NULL,
            parsed_count INTEGER NOT NULL,
            deduped_count INTEGER NOT NULL,
            matched_count INTEGER NOT NULL,
            operator_summary_snapshot TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_news_intelligence_runs_target_stock
        ON news_intelligence_runs (target_date, stock_code, stock_name, created_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS report_linked_news_evidence (
            run_id TEXT NOT NULL,
            evidence_key TEXT NOT NULL,
            target_date TEXT NOT NULL,
            stock_code TEXT,
            stock_name TEXT NOT NULL,
            related_report_count INTEGER NOT NULL,
            related_report_source_ids_json TEXT NOT NULL,
            daily_summary_presence INTEGER NOT NULL,
            candidate_priority_presence INTEGER NOT NULL,
            candidate_observation_priority TEXT,
            krx_reference_presence INTEGER NOT NULL,
            krx_turnover INTEGER,
            investor_flow_presence INTEGER NOT NULL,
            source_lane TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            source TEXT NOT NULL,
            published_at TEXT NOT NULL,
            url TEXT NOT NULL,
            matched_alias TEXT NOT NULL,
            match_reason TEXT NOT NULL,
            match_scope TEXT NOT NULL,
            relevance TEXT NOT NULL,
            relevance_reason TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            sentiment_score INTEGER NOT NULL,
            event_types_json TEXT NOT NULL,
            stock_impact TEXT NOT NULL,
            impact_explanation TEXT NOT NULL,
            evidence_case TEXT NOT NULL,
            operator_recommendation TEXT NOT NULL,
            recommendation_reason TEXT NOT NULL,
            operator_summary_snapshot TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (run_id, evidence_key),
            FOREIGN KEY (run_id) REFERENCES news_intelligence_runs(run_id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_report_linked_news_target_stock
        ON report_linked_news_evidence (target_date, stock_code, evidence_case)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_report_linked_news_report_context
        ON report_linked_news_evidence (target_date, related_report_count, relevance, stock_impact)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_report_linked_news_url
        ON report_linked_news_evidence (url, target_date, stock_code)
        """,
    ),
)


NEWS_INTELLIGENCE_REFERENCE_DATES_MIGRATION = SchemaMigration(
    version=7,
    name="news_intelligence_reference_dates",
    statements=(
        """
        ALTER TABLE report_linked_news_evidence
        ADD COLUMN krx_reference_date TEXT
        """,
    ),
)


TOSS_PRIORITY_QUOTE_BASELINE_MIGRATION = SchemaMigration(
    version=8,
    name="toss_priority_quote_baselines",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS toss_priority_quote_baselines (
            business_date TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            baseline_time TEXT NOT NULL,
            last_price INTEGER,
            currency TEXT,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (business_date, stock_code, baseline_time, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toss_priority_quote_baselines_lookup
        ON toss_priority_quote_baselines (business_date, stock_code, baseline_time)
        """,
    ),
)


TOSS_MARKET_CONTEXT_SNAPSHOT_MIGRATION = SchemaMigration(
    version=9,
    name="toss_market_context_snapshots",
    statements=(
        """
        CREATE TABLE IF NOT EXISTS toss_market_context_snapshots (
            business_date TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            rank INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            trading_amount INTEGER,
            trading_volume INTEGER,
            source TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            PRIMARY KEY (business_date, observed_at, stock_code, source)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_toss_market_context_snapshots_replay
        ON toss_market_context_snapshots (business_date, observed_at DESC, rank ASC)
        """,
    ),
)


SCHEMA_MIGRATIONS: tuple[SchemaMigration, ...] = (
    KRX_MARKET_SNAPSHOT_MIGRATION,
    APP_SETTINGS_MIGRATION,
    KRX_INVESTOR_FLOW_MIGRATION,
    CATEGORY_SNAPSHOT_MIGRATION,
    NEWS_INTELLIGENCE_OBSERVATION_MIGRATION,
    NEWS_INTELLIGENCE_REFERENCE_DATES_MIGRATION,
    TOSS_PRIORITY_QUOTE_BASELINE_MIGRATION,
    TOSS_MARKET_CONTEXT_SNAPSHOT_MIGRATION,
)


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identity_key TEXT NOT NULL UNIQUE,
        stock_name TEXT NOT NULL,
        stock_code TEXT,
        title TEXT NOT NULL,
        broker_name TEXT NOT NULL,
        published_at TEXT NOT NULL,
        business_date TEXT NOT NULL,
        target_price_raw TEXT,
        target_price_value INTEGER,
        opinion_raw TEXT,
        opinion_normalized TEXT NOT NULL,
        collected_at TEXT NOT NULL,
        source_url TEXT,
        source_id TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reports_business_date
    ON reports (business_date, stock_name)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reports_source_id
    ON reports (source_id)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_source_id
    ON reports (source_id)
    WHERE source_id IS NOT NULL AND source_id <> ''
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_reports_legacy_identity
    ON reports (stock_name, title, broker_name, published_at)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_legacy_identity
    ON reports (stock_name, title, broker_name, published_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_stock_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_date TEXT NOT NULL,
        stock_name TEXT NOT NULL,
        stock_code TEXT,
        mention_count INTEGER NOT NULL,
        broker_display TEXT NOT NULL,
        target_price_min INTEGER,
        target_price_max INTEGER,
        dominant_opinion TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        UNIQUE (business_date, stock_name, stock_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS delivery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_date TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT NOT NULL,
        delivered_at TEXT NOT NULL,
        message_id TEXT,
        detail TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_delivery_log_business_date
    ON delivery_log (business_date, channel)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_log_success
    ON delivery_log (business_date, channel)
    WHERE status = 'sent'
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_summary_delivery_runs (
        run_id TEXT PRIMARY KEY,
        business_date TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT NOT NULL,
        summary_signature TEXT NOT NULL,
        total_fragments INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        last_error TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_daily_summary_delivery_runs_lookup
    ON daily_summary_delivery_runs (business_date, channel, summary_signature, status)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_daily_summary_delivery_runs_status
    ON daily_summary_delivery_runs (business_date, channel, status)
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_summary_delivery_fragments (
        run_id TEXT NOT NULL,
        fragment_index INTEGER NOT NULL,
        status TEXT NOT NULL,
        message_text TEXT NOT NULL,
        message_hash TEXT NOT NULL,
        message_id TEXT,
        sent_at TEXT,
        last_error TEXT,
        PRIMARY KEY (run_id, fragment_index),
        FOREIGN KEY (run_id) REFERENCES daily_summary_delivery_runs(run_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_daily_summary_delivery_fragments_status
    ON daily_summary_delivery_fragments (run_id, status, fragment_index)
    """,
    """
    CREATE TABLE IF NOT EXISTS operation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time TEXT NOT NULL,
        component TEXT NOT NULL,
        event_type TEXT NOT NULL,
        status TEXT NOT NULL,
        business_date TEXT,
        detail TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operation_events_time
    ON operation_events (event_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operation_events_component_status
    ON operation_events (component, status, event_time DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operation_events_component_type_date
    ON operation_events (component, event_type, business_date, event_time DESC, id DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS operator_controls (
        control_key TEXT PRIMARY KEY,
        control_value TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        detail TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_operator_controls_key
    ON operator_controls (control_key)
    """,
    """
    CREATE TABLE IF NOT EXISTS worker_state (
        worker_name TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_started_at TEXT,
        last_success_at TEXT,
        last_error_at TEXT,
        last_error TEXT,
        interval_seconds INTEGER,
        end_time TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_worker_state_updated
    ON worker_state (updated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_metadata (
        stock_code TEXT PRIMARY KEY,
        stock_name TEXT,
        sector_code TEXT,
        sector_name TEXT,
        updated_at TEXT NOT NULL,
        source TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_metadata_sector
    ON stock_metadata (sector_name, stock_code)
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_theme_memberships (
        theme_code TEXT NOT NULL,
        theme_name TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        updated_at TEXT NOT NULL,
        source TEXT NOT NULL,
        PRIMARY KEY (theme_code, stock_code)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_theme_memberships_stock
    ON stock_theme_memberships (stock_code, theme_code)
    """,
    """
    CREATE TABLE IF NOT EXISTS intraday_alert_batches (
        batch_id TEXT PRIMARY KEY,
        business_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        last_attempt_at TEXT,
        sent_at TEXT,
        message_id TEXT,
        error_detail TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_intraday_alert_batches_status_created_at
    ON intraday_alert_batches (status, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS intraday_alert_batch_reports (
        batch_id TEXT NOT NULL,
        report_identity_key TEXT NOT NULL,
        PRIMARY KEY (batch_id, report_identity_key)
    )
    """,
]


SCHEMA_MIGRATIONS_TABLE_STATEMENT = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
"""


def initialize_schema(connection: sqlite3.Connection) -> SchemaMigrationStatus:
    current_version = _get_user_version(connection)
    if current_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
        )
    if current_version == 0:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute(SCHEMA_MIGRATIONS_TABLE_STATEMENT)
        _set_user_version(connection, 1)
        _record_schema_migration(connection, 1, BASELINE_MIGRATION_NAME)
    else:
        connection.execute(SCHEMA_MIGRATIONS_TABLE_STATEMENT)
        _record_baseline_if_needed(connection)
    return apply_schema_migrations(connection)


def apply_schema_migrations(
    connection: sqlite3.Connection,
    *,
    dry_run: bool = False,
) -> SchemaMigrationStatus:
    if not dry_run:
        connection.execute(SCHEMA_MIGRATIONS_TABLE_STATEMENT)

    current_version = _get_user_version(connection)
    if current_version == 0:
        raise RuntimeError("Baseline schema has not been initialized.")
    if current_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
        )

    applied_versions = _list_applied_migration_versions(connection) if _schema_migrations_table_exists(connection) else ()
    pending = _pending_migrations(current_version)

    if dry_run:
        return SchemaMigrationStatus(
            current_version=current_version,
            target_version=SCHEMA_VERSION,
            applied_versions=applied_versions,
            pending_versions=tuple(migration.version for migration in pending),
        )

    _record_baseline_if_needed(connection)
    for migration in pending:
        for statement in migration.statements:
            connection.execute(statement)
        _set_user_version(connection, migration.version)
        _record_schema_migration(connection, migration.version, migration.name)

    if not pending and current_version < SCHEMA_VERSION:
        _set_user_version(connection, SCHEMA_VERSION)

    return SchemaMigrationStatus(
        current_version=_get_user_version(connection),
        target_version=SCHEMA_VERSION,
        applied_versions=_list_applied_migration_versions(connection),
        pending_versions=(),
    )


def get_schema_migration_status(connection: sqlite3.Connection) -> SchemaMigrationStatus:
    current_version = _get_user_version(connection)
    applied_versions = _list_applied_migration_versions(connection) if _schema_migrations_table_exists(connection) else ()
    pending = _pending_migrations(current_version)
    return SchemaMigrationStatus(
        current_version=current_version,
        target_version=SCHEMA_VERSION,
        applied_versions=applied_versions,
        pending_versions=tuple(migration.version for migration in pending),
    )


def _pending_migrations(current_version: int) -> tuple[SchemaMigration, ...]:
    migrations = tuple(migration for migration in SCHEMA_MIGRATIONS if migration.version > current_version)
    first_required_version = max(current_version + 1, 2)
    missing_versions = [
        version
        for version in range(first_required_version, SCHEMA_VERSION + 1)
        if version not in {migration.version for migration in migrations}
    ]
    if missing_versions:
        raise RuntimeError(f"Missing schema migration(s) for version(s): {missing_versions}")
    return migrations


def _record_baseline_if_needed(connection: sqlite3.Connection) -> None:
    user_version = _get_user_version(connection)
    if user_version == 0:
        _set_user_version(connection, SCHEMA_VERSION)
        user_version = SCHEMA_VERSION
    if user_version >= 1:
        _record_schema_migration(connection, 1, BASELINE_MIGRATION_NAME)


def _record_schema_migration(connection: sqlite3.Connection, version: int, name: str) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name, applied_at)
        VALUES (?, ?, ?)
        """,
        (version, name, datetime.now(timezone.utc).isoformat()),
    )


def _list_applied_migration_versions(connection: sqlite3.Connection) -> tuple[int, ...]:
    rows = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return tuple(int(row[0]) for row in rows)


def _schema_migrations_table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchone()
    return row is not None


def _get_user_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(connection: sqlite3.Connection, version: int) -> None:
    connection.execute(f"PRAGMA user_version = {version}")
