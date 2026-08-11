from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from stock_monitor.db.schema import (
    SCHEMA_VERSION,
    SchemaMigrationStatus,
    get_schema_migration_status,
    initialize_schema,
)
from stock_monitor.web_perf import elapsed_ms, record_db_elapsed
from stock_monitor.models import (
    AdminAuditLog,
    AppSetting,
    CategoryCatalogItem,
    CategoryDailyRollup,
    CategoryMembershipSnapshot,
    CategoryTrendPoint,
    DailySummaryDeliveryFragment,
    DailySummaryDeliveryRun,
    DailyStockSummary,
    DeliveryLog,
    IntradayAlertBatch,
    IntradayAlertBatchSummary,
    InvestorNetBuyTopDaily,
    OperationEvent,
    OperatorControl,
    Report,
    SectorDailyRollup,
    EtfDailySnapshot,
    KrxStockMetadataSnapshot,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    NewsIntelligenceRun,
    StockMetadata,
    StockMarketDailySnapshot,
    StockInvestorFlowDaily,
    StockThemeMembership,
    ReportLinkedNewsEvidenceRecord,
    ThemeDailyRollup,
    TossMarketContextSnapshot,
    TossPriorityQuoteBaseline,
    WorkerState,
)
from stock_monitor.summary import build_daily_summaries


SQLITE_READ_CACHE_SIZE_PAGES = -32768


@dataclass(frozen=True)
class InsertResult:
    attempted: int
    inserted: int
    inserted_reports: tuple[Report, ...] = ()
    intraday_batch_ids: tuple[str, ...] = ()


class StockMonitorRepository:
    def __init__(self, db_path: Path, *, timezone: str = "Asia/Seoul") -> None:
        self.db_path = db_path
        self.timezone = timezone
        self._active_read_connection: ContextVar[sqlite3.Connection | None] = ContextVar(
            "active_read_connection",
            default=None,
        )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        active_connection = self._active_read_connection.get()
        if active_connection is not None:
            yield active_connection
            return

        connection = sqlite3.connect(self.db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute(f"PRAGMA cache_size = {SQLITE_READ_CACHE_SIZE_PAGES}")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.execute("PRAGMA synchronous = NORMAL")
        db_start = time.perf_counter()
        try:
            yield connection
        finally:
            record_db_elapsed(elapsed_ms(db_start))
            connection.close()

    @contextmanager
    def read_session(self) -> Iterator[None]:
        if self._active_read_connection.get() is not None:
            yield
            return

        with self.connect() as connection:
            token = self._active_read_connection.set(connection)
            try:
                yield
            finally:
                self._active_read_connection.reset(token)

    def enable_wal_mode(self) -> str:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            connection.execute("PRAGMA synchronous = NORMAL")
            return str(mode).lower()
        finally:
            connection.close()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            with connection:
                initialize_schema(connection)

    def migrate_schema(self, *, dry_run: bool = False) -> SchemaMigrationStatus:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if dry_run and not self.db_path.exists():
            return SchemaMigrationStatus(
                current_version=0,
                target_version=SCHEMA_VERSION,
                applied_versions=(),
                pending_versions=(),
            )
        with self.connect() as connection:
            if dry_run:
                return get_schema_migration_status(connection)
            with connection:
                return initialize_schema(connection)

    def get_schema_migration_status(self) -> SchemaMigrationStatus:
        with self.connect() as connection:
            return get_schema_migration_status(connection)

    def save_news_intelligence_observation(
        self,
        run: NewsIntelligenceRun,
        evidence_rows: list[ReportLinkedNewsEvidenceRecord],
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO news_intelligence_runs (
                        run_id,
                        target_date,
                        stock_name,
                        stock_code,
                        aliases_json,
                        source_mode,
                        page_limit,
                        full_day_complete,
                        live_fetch,
                        parsed_count,
                        deduped_count,
                        matched_count,
                        operator_summary_snapshot,
                        warnings_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.target_date.isoformat(),
                        run.stock_name,
                        run.stock_code,
                        self._encode_json_tuple(run.aliases),
                        run.source_mode,
                        run.page_limit,
                        int(run.full_day_complete),
                        int(run.live_fetch),
                        run.parsed_count,
                        run.deduped_count,
                        run.matched_count,
                        run.operator_summary_snapshot,
                        self._encode_json_tuple(run.warnings),
                        run.created_at.isoformat(),
                    ),
                )
                for evidence in evidence_rows:
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO report_linked_news_evidence (
                            run_id,
                            evidence_key,
                            target_date,
                            stock_code,
                            stock_name,
                            related_report_count,
                            related_report_source_ids_json,
                            daily_summary_presence,
                            candidate_priority_presence,
                            candidate_observation_priority,
                            krx_reference_presence,
                            krx_reference_date,
                            krx_turnover,
                            investor_flow_presence,
                            source_lane,
                            title,
                            summary,
                            source,
                            published_at,
                            url,
                            matched_alias,
                            match_reason,
                            match_scope,
                            relevance,
                            relevance_reason,
                            sentiment,
                            sentiment_score,
                            event_types_json,
                            stock_impact,
                            impact_explanation,
                            evidence_case,
                            operator_recommendation,
                            recommendation_reason,
                            operator_summary_snapshot,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evidence.run_id,
                            evidence.evidence_key,
                            evidence.target_date.isoformat(),
                            evidence.stock_code,
                            evidence.stock_name,
                            evidence.related_report_count,
                            self._encode_json_tuple(evidence.related_report_source_ids),
                            int(evidence.daily_summary_presence),
                            int(evidence.candidate_priority_presence),
                            evidence.candidate_observation_priority,
                            int(evidence.krx_reference_presence),
                            evidence.krx_reference_date.isoformat() if evidence.krx_reference_date else None,
                            evidence.krx_turnover,
                            int(evidence.investor_flow_presence),
                            evidence.source_lane,
                            evidence.title,
                            evidence.summary,
                            evidence.source,
                            evidence.published_at.isoformat(),
                            evidence.url,
                            evidence.matched_alias,
                            evidence.match_reason,
                            evidence.match_scope,
                            evidence.relevance,
                            evidence.relevance_reason,
                            evidence.sentiment,
                            evidence.sentiment_score,
                            self._encode_json_tuple(evidence.event_types),
                            evidence.stock_impact,
                            evidence.impact_explanation,
                            evidence.evidence_case,
                            evidence.operator_recommendation,
                            evidence.recommendation_reason,
                            evidence.operator_summary_snapshot,
                            evidence.created_at.isoformat(),
                        ),
                    )

    def list_news_intelligence_runs(
        self,
        *,
        target_date: date | None = None,
        stock_code: str | None = None,
        limit: int = 20,
    ) -> list[NewsIntelligenceRun]:
        conditions: list[str] = []
        params: list[object] = []
        if target_date is not None:
            conditions.append("target_date = ?")
            params.append(target_date.isoformat())
        if stock_code is not None:
            conditions.append("stock_code = ?")
            params.append(stock_code)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM news_intelligence_runs
                {where_clause}
                ORDER BY created_at DESC, run_id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_news_intelligence_run(row) for row in rows]

    def list_report_linked_news_evidence(
        self,
        *,
        run_id: str | None = None,
        target_date: date | None = None,
        stock_code: str | None = None,
        limit: int = 100,
    ) -> list[ReportLinkedNewsEvidenceRecord]:
        conditions: list[str] = []
        params: list[object] = []
        if run_id is not None:
            conditions.append("run_id = ?")
            params.append(run_id)
        if target_date is not None:
            conditions.append("target_date = ?")
            params.append(target_date.isoformat())
        if stock_code is not None:
            conditions.append("stock_code = ?")
            params.append(stock_code)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM report_linked_news_evidence
                {where_clause}
                ORDER BY target_date DESC, created_at DESC, evidence_key
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_report_linked_news_evidence(row) for row in rows]

    def list_report_linked_news_evidence_for_run_ids(
        self,
        run_ids: list[str] | tuple[str, ...],
        *,
        limit_per_run: int = 20,
    ) -> list[ReportLinkedNewsEvidenceRecord]:
        normalized_run_ids = tuple(run_id for run_id in run_ids if run_id)
        if not normalized_run_ids:
            return []
        placeholders = ", ".join("?" for _ in normalized_run_ids)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                WITH ranked_evidence AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY run_id
                            ORDER BY target_date DESC, created_at DESC, evidence_key
                        ) AS row_number
                    FROM report_linked_news_evidence
                    WHERE run_id IN ({placeholders})
                )
                SELECT *
                FROM ranked_evidence
                WHERE row_number <= ?
                ORDER BY target_date DESC, created_at DESC, evidence_key
                """,
                (*normalized_run_ids, limit_per_run),
            ).fetchall()
        return [self._row_to_report_linked_news_evidence(row) for row in rows]

    def save_toss_priority_quote_baselines(self, rows: list[TossPriorityQuoteBaseline]) -> None:
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO toss_priority_quote_baselines (
                        business_date,
                        stock_code,
                        stock_name,
                        baseline_time,
                        last_price,
                        currency,
                        source,
                        fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            row.business_date.isoformat(),
                            row.stock_code,
                            row.stock_name,
                            row.baseline_time,
                            row.last_price,
                            row.currency,
                            row.source,
                            row.fetched_at.isoformat(),
                        )
                        for row in rows
                    ],
                )

    def list_toss_priority_quote_baselines(
        self,
        *,
        business_date: date,
        stock_codes: list[str] | tuple[str, ...],
        baseline_time: str = "20:00",
    ) -> list[TossPriorityQuoteBaseline]:
        normalized_codes = [code.strip() for code in stock_codes if code and code.strip()]
        if not normalized_codes:
            return []
        placeholders = ",".join("?" for _ in normalized_codes)
        params: list[object] = [business_date.isoformat(), baseline_time, *normalized_codes]
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM toss_priority_quote_baselines
                WHERE business_date = ?
                  AND baseline_time = ?
                  AND stock_code IN ({placeholders})
                ORDER BY fetched_at DESC, stock_code ASC
                """,
                tuple(params),
            ).fetchall()
        latest_by_code: dict[str, TossPriorityQuoteBaseline] = {}
        for row in rows:
            baseline = self._row_to_toss_priority_quote_baseline(row)
            latest_by_code.setdefault(baseline.stock_code, baseline)
        return [latest_by_code[code] for code in normalized_codes if code in latest_by_code]

    def save_toss_market_context_snapshots(self, rows: list[TossMarketContextSnapshot]) -> None:
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO toss_market_context_snapshots (
                        business_date,
                        observed_at,
                        rank,
                        stock_code,
                        trading_amount,
                        trading_volume,
                        source,
                        checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            row.business_date.isoformat(),
                            row.observed_at.isoformat(),
                            row.rank,
                            row.stock_code,
                            row.trading_amount,
                            row.trading_volume,
                            row.source,
                            row.checked_at.isoformat(),
                        )
                        for row in rows
                    ],
                )

    def list_latest_toss_market_context_snapshot(
        self, *, business_date: date
    ) -> list[TossMarketContextSnapshot]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM toss_market_context_snapshots
                WHERE business_date = ?
                  AND observed_at = (
                      SELECT MAX(observed_at)
                      FROM toss_market_context_snapshots
                      WHERE business_date = ?
                  )
                ORDER BY rank ASC, stock_code ASC
                """,
                (business_date.isoformat(), business_date.isoformat()),
            ).fetchall()
        return [self._row_to_toss_market_context_snapshot(row) for row in rows]

    def insert_reports(self, reports: list[Report], *, queue_intraday_alerts: bool = False) -> InsertResult:
        normalized = [report.with_identity() for report in reports]
        inserted = 0
        inserted_reports: list[Report] = []
        intraday_batch_ids: list[str] = []
        reports_by_business_date: dict[date, list[Report]] = {}
        with self.connect() as connection:
            with connection:
                for report in normalized:
                    cursor = connection.execute(
                        """
                        INSERT OR IGNORE INTO reports (
                            identity_key,
                            stock_name,
                            stock_code,
                            title,
                            broker_name,
                            published_at,
                            business_date,
                            target_price_raw,
                            target_price_value,
                            opinion_raw,
                            opinion_normalized,
                            collected_at,
                            source_url,
                            source_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            report.identity_key,
                            report.stock_name,
                            report.stock_code,
                            report.title,
                            report.broker_name,
                            report.published_at.isoformat(),
                            report.business_date.isoformat(),
                            report.target_price_raw,
                            report.target_price_value,
                            report.opinion_raw,
                            report.opinion_normalized,
                            report.collected_at.isoformat(),
                            report.source_url,
                            report.source_id,
                        ),
                    )
                    inserted += cursor.rowcount
                    if cursor.rowcount:
                        inserted_reports.append(report)
                        if queue_intraday_alerts:
                            reports_by_business_date.setdefault(report.business_date, []).append(report)
                if queue_intraday_alerts:
                    for business_date, batch_reports in sorted(reports_by_business_date.items()):
                        intraday_batch_ids.append(
                            self._create_intraday_alert_batch(connection, business_date, batch_reports)
                        )
        return InsertResult(
            attempted=len(normalized),
            inserted=inserted,
            inserted_reports=tuple(inserted_reports),
            intraday_batch_ids=tuple(intraday_batch_ids),
        )

    def list_reports_for_business_date(self, business_date: date) -> list[Report]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    stock_name,
                    stock_code,
                    title,
                    broker_name,
                    published_at,
                    business_date,
                    target_price_raw,
                    target_price_value,
                    opinion_raw,
                    opinion_normalized,
                    collected_at,
                    source_url,
                    source_id,
                    identity_key
                FROM reports
                WHERE business_date = ?
                ORDER BY stock_name, published_at, broker_name, title
                """,
                (business_date.isoformat(),),
            ).fetchall()
        return [self._row_to_report(row) for row in rows]

    def list_reports_for_stock_on_business_date(self, business_date: date, stock_code: str) -> list[Report]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    stock_name,
                    stock_code,
                    title,
                    broker_name,
                    published_at,
                    business_date,
                    target_price_raw,
                    target_price_value,
                    opinion_raw,
                    opinion_normalized,
                    collected_at,
                    source_url,
                    source_id,
                    identity_key
                FROM reports
                WHERE business_date = ?
                  AND stock_code = ?
                ORDER BY published_at DESC, broker_name ASC, title ASC
                """,
                (business_date.isoformat(), stock_code),
            ).fetchall()
        return [self._row_to_report(row) for row in rows]

    def rebuild_daily_summaries(self, business_date: date) -> list[DailyStockSummary]:
        reports = self.list_reports_for_business_date(business_date)
        summaries = build_daily_summaries(reports, timezone=self.timezone)
        with self.connect() as connection:
            with connection:
                connection.execute(
                    "DELETE FROM daily_stock_summaries WHERE business_date = ?",
                    (business_date.isoformat(),),
                )
                connection.executemany(
                    """
                    INSERT INTO daily_stock_summaries (
                        business_date,
                        stock_name,
                        stock_code,
                        mention_count,
                        broker_display,
                        target_price_min,
                        target_price_max,
                        dominant_opinion,
                        generated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            summary.business_date.isoformat(),
                            summary.stock_name,
                            summary.stock_code,
                            summary.mention_count,
                            summary.broker_display,
                            summary.target_price_min,
                            summary.target_price_max,
                            summary.dominant_opinion,
                            summary.generated_at.isoformat(),
                        )
                        for summary in summaries
                    ],
                )
        return summaries

    def list_daily_summaries(self, business_date: date) -> list[DailyStockSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date,
                    stock_name,
                    stock_code,
                    mention_count,
                    broker_display,
                    target_price_min,
                    target_price_max,
                    dominant_opinion,
                    generated_at
                FROM daily_stock_summaries
                WHERE business_date = ?
                ORDER BY mention_count DESC, stock_name ASC
                """,
                (business_date.isoformat(),),
            ).fetchall()
        return [
            DailyStockSummary(
                business_date=date.fromisoformat(row["business_date"]),
                stock_name=row["stock_name"],
                stock_code=row["stock_code"],
                mention_count=row["mention_count"],
                broker_display=row["broker_display"],
                target_price_min=row["target_price_min"],
                target_price_max=row["target_price_max"],
                dominant_opinion=row["dominant_opinion"],
                generated_at=datetime.fromisoformat(row["generated_at"]),
            )
            for row in rows
        ]

    def list_daily_summaries_for_backtest_observation(
        self,
        business_date: date,
        *,
        min_mention_count: int = 2,
    ) -> list[DailyStockSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date,
                    stock_name,
                    stock_code,
                    mention_count,
                    broker_display,
                    target_price_min,
                    target_price_max,
                    dominant_opinion,
                    generated_at
                FROM daily_stock_summaries
                WHERE business_date = ?
                  AND stock_code IS NOT NULL
                  AND TRIM(stock_code) <> ''
                  AND mention_count >= ?
                ORDER BY mention_count DESC, stock_name ASC
                """,
                (business_date.isoformat(), min_mention_count),
            ).fetchall()
        return [
            DailyStockSummary(
                business_date=date.fromisoformat(row["business_date"]),
                stock_name=row["stock_name"],
                stock_code=row["stock_code"],
                mention_count=row["mention_count"],
                broker_display=row["broker_display"],
                target_price_min=row["target_price_min"],
                target_price_max=row["target_price_max"],
                dominant_opinion=row["dominant_opinion"],
                generated_at=datetime.fromisoformat(row["generated_at"]),
            )
            for row in rows
        ]

    def get_first_target_report_date(self, stock_code: str, *, on_or_before: date) -> date | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT MIN(business_date) AS business_date
                FROM reports
                WHERE stock_code = ?
                  AND business_date <= ?
                  AND target_price_value IS NOT NULL
                """,
                (stock_code, on_or_before.isoformat()),
            ).fetchone()
        raw = row["business_date"] if row else None
        return date.fromisoformat(raw) if raw else None

    def record_delivery(self, delivery: DeliveryLog) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO delivery_log (
                        business_date,
                        channel,
                        status,
                        delivered_at,
                        message_id,
                        detail
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        delivery.business_date.isoformat(),
                        delivery.channel,
                        delivery.status,
                        delivery.delivered_at.isoformat(),
                        delivery.message_id,
                        delivery.detail,
                    ),
                )

    def start_or_resume_daily_summary_run(
        self,
        *,
        business_date: date,
        channel: str,
        summary_signature: str,
        messages: list[str],
        started_at: datetime,
    ) -> DailySummaryDeliveryRun:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE daily_summary_delivery_runs
                    SET status = 'superseded',
                        finished_at = ?,
                        last_error = 'superseded by new summary signature'
                    WHERE business_date = ?
                      AND channel = ?
                      AND status IN ('pending', 'failed')
                      AND summary_signature <> ?
                    """,
                    (
                        started_at.isoformat(),
                        business_date.isoformat(),
                        channel,
                        summary_signature,
                    ),
                )
                row = connection.execute(
                    """
                    SELECT
                        run_id,
                        business_date,
                        channel,
                        status,
                        summary_signature,
                        total_fragments,
                        started_at,
                        finished_at,
                        last_error
                    FROM daily_summary_delivery_runs
                    WHERE business_date = ?
                      AND channel = ?
                      AND summary_signature = ?
                      AND status IN ('pending', 'failed')
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (
                        business_date.isoformat(),
                        channel,
                        summary_signature,
                    ),
                ).fetchone()
                if row:
                    connection.execute(
                    """
                        UPDATE daily_summary_delivery_runs
                        SET status = 'pending',
                            finished_at = NULL,
                            last_error = NULL
                        WHERE run_id = ?
                        """,
                        (row["run_id"],),
                    )
                    return self._row_to_daily_summary_delivery_run(
                        {
                            **dict(row),
                            "status": "pending",
                            "finished_at": None,
                            "last_error": None,
                        }
                    )

                run_id = uuid4().hex
                connection.execute(
                    """
                    INSERT INTO daily_summary_delivery_runs (
                        run_id,
                        business_date,
                        channel,
                        status,
                        summary_signature,
                        total_fragments,
                        started_at
                    ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
                    """,
                    (
                        run_id,
                        business_date.isoformat(),
                        channel,
                        summary_signature,
                        len(messages),
                        started_at.isoformat(),
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO daily_summary_delivery_fragments (
                        run_id,
                        fragment_index,
                        status,
                        message_text,
                        message_hash
                    ) VALUES (?, ?, 'pending', ?, ?)
                    """,
                    [
                        (
                            run_id,
                            index,
                            message,
                            _hash_text(message),
                        )
                        for index, message in enumerate(messages)
                    ],
                )
                return DailySummaryDeliveryRun(
                    run_id=run_id,
                    business_date=business_date,
                    channel=channel,
                    status="pending",
                    summary_signature=summary_signature,
                    total_fragments=len(messages),
                    started_at=started_at,
                )

    def list_pending_daily_summary_fragments(self, run_id: str) -> list[DailySummaryDeliveryFragment]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    fragment_index,
                    status,
                    message_text,
                    message_hash,
                    message_id,
                    sent_at,
                    last_error
                FROM daily_summary_delivery_fragments
                WHERE run_id = ?
                  AND status IN ('pending', 'failed')
                ORDER BY fragment_index ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_daily_summary_delivery_fragment(row) for row in rows]

    def list_daily_summary_fragments(self, run_id: str) -> list[DailySummaryDeliveryFragment]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    fragment_index,
                    status,
                    message_text,
                    message_hash,
                    message_id,
                    sent_at,
                    last_error
                FROM daily_summary_delivery_fragments
                WHERE run_id = ?
                ORDER BY fragment_index ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_daily_summary_delivery_fragment(row) for row in rows]

    def mark_daily_summary_fragment_sent(
        self,
        run_id: str,
        fragment_index: int,
        *,
        message_id: str,
        sent_at: datetime,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE daily_summary_delivery_fragments
                    SET status = 'sent',
                        message_id = ?,
                        sent_at = ?,
                        last_error = NULL
                    WHERE run_id = ?
                      AND fragment_index = ?
                    """,
                    (
                        message_id,
                        sent_at.isoformat(),
                        run_id,
                        fragment_index,
                    ),
                )

    def mark_daily_summary_fragment_failed(
        self,
        run_id: str,
        fragment_index: int,
        *,
        error_detail: str,
        failed_at: datetime,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE daily_summary_delivery_fragments
                    SET status = 'failed',
                        last_error = ?
                    WHERE run_id = ?
                      AND fragment_index = ?
                    """,
                    (
                        error_detail,
                        run_id,
                        fragment_index,
                    ),
                )
                connection.execute(
                    """
                    UPDATE daily_summary_delivery_runs
                    SET status = 'failed',
                        last_error = ?,
                        finished_at = ?
                    WHERE run_id = ?
                    """,
                    (
                        error_detail,
                        failed_at.isoformat(),
                        run_id,
                    ),
                )

    def complete_daily_summary_run(
        self,
        run_id: str,
        *,
        finished_at: datetime,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE daily_summary_delivery_runs
                    SET status = 'sent',
                        finished_at = ?,
                        last_error = NULL
                    WHERE run_id = ?
                    """,
                    (finished_at.isoformat(), run_id),
                )

    def record_operation_event(self, event: OperationEvent) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO operation_events (
                        event_time,
                        component,
                        event_type,
                        status,
                        business_date,
                        detail
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_time.isoformat(),
                        event.component,
                        event.event_type,
                        event.status,
                        event.business_date.isoformat() if event.business_date else None,
                        event.detail,
                    ),
                )

    def list_recent_operation_events(self, *, limit: int = 20) -> list[OperationEvent]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT event_time, component, event_type, status, business_date, detail
                FROM operation_events
                ORDER BY event_time DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            OperationEvent(
                event_time=datetime.fromisoformat(row["event_time"]),
                component=row["component"],
                event_type=row["event_type"],
                status=row["status"],
                business_date=date.fromisoformat(row["business_date"]) if row["business_date"] else None,
                detail=row["detail"],
            )
            for row in rows
        ]

    def list_operation_events(
        self,
        *,
        component: str | None = None,
        event_type: str | None = None,
        business_date: date | None = None,
        status: str | None = None,
        limit: int | None = 20,
        ascending: bool = False,
    ) -> list[OperationEvent]:
        where: list[str] = []
        params: list[object] = []
        if component is not None:
            where.append("component = ?")
            params.append(component)
        if event_type is not None:
            where.append("event_type = ?")
            params.append(event_type)
        if business_date is not None:
            where.append("business_date = ?")
            params.append(business_date.isoformat())
        if status is not None:
            where.append("status = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        order_sql = "ASC" if ascending else "DESC"
        limit_sql = ""
        if limit is not None:
            if limit < 1:
                return []
            limit_sql = "LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT event_time, component, event_type, status, business_date, detail
                FROM operation_events
                {where_sql}
                ORDER BY event_time {order_sql}, id {order_sql}
                {limit_sql}
                """,
                tuple(params),
            ).fetchall()
        return [
            OperationEvent(
                event_time=datetime.fromisoformat(row["event_time"]),
                component=row["component"],
                event_type=row["event_type"],
                status=row["status"],
                business_date=date.fromisoformat(row["business_date"]) if row["business_date"] else None,
                detail=row["detail"],
            )
            for row in rows
        ]

    def set_operator_control(
        self,
        control_key: str,
        control_value: str,
        *,
        updated_at: datetime,
        detail: str | None = None,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO operator_controls (
                        control_key,
                        control_value,
                        updated_at,
                        detail
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(control_key) DO UPDATE SET
                        control_value = excluded.control_value,
                        updated_at = excluded.updated_at,
                        detail = excluded.detail
                    """,
                    (control_key, control_value, updated_at.isoformat(), detail),
                )

    def delete_operator_control(self, control_key: str) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute("DELETE FROM operator_controls WHERE control_key = ?", (control_key,))

    def get_operator_control(self, control_key: str) -> OperatorControl | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT control_key, control_value, updated_at, detail
                FROM operator_controls
                WHERE control_key = ?
                """,
                (control_key,),
            ).fetchone()
        return self._row_to_operator_control(row) if row else None

    def list_operator_controls(self, *, prefix: str | None = None) -> list[OperatorControl]:
        query = """
            SELECT control_key, control_value, updated_at, detail
            FROM operator_controls
        """
        params: tuple[str, ...] = ()
        if prefix is not None:
            query += " WHERE control_key LIKE ?"
            params = (f"{prefix}%",)
        query += " ORDER BY control_key ASC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_operator_control(row) for row in rows]

    def is_operator_paused(self) -> bool:
        control = self.get_operator_control("schedule_pause")
        return control is not None and control.control_value == "true"

    def set_operator_pause(self, *, paused: bool, updated_at: datetime, detail: str | None = None) -> None:
        if paused:
            self.set_operator_control("schedule_pause", "true", updated_at=updated_at, detail=detail)
            return
        self.delete_operator_control("schedule_pause")

    def add_run_suppressed_date(self, target: date, *, updated_at: datetime, detail: str | None = None) -> None:
        self.set_operator_control(
            _run_suppressed_date_key(target),
            "true",
            updated_at=updated_at,
            detail=detail,
        )

    def remove_run_suppressed_date(self, target: date) -> None:
        self.delete_operator_control(_run_suppressed_date_key(target))

    def list_db_run_suppressed_dates(self) -> list[date]:
        dates: list[date] = []
        for control in self.list_operator_controls(prefix="run_suppressed_date:"):
            _, raw_date = control.control_key.split(":", 1)
            dates.append(date.fromisoformat(raw_date))
        return sorted(dates)

    def is_db_run_suppressed_date(self, target: date) -> bool:
        control = self.get_operator_control(_run_suppressed_date_key(target))
        return control is not None and control.control_value == "true"

    def upsert_worker_state(self, state: WorkerState) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO worker_state (
                        worker_name,
                        status,
                        updated_at,
                        last_started_at,
                        last_success_at,
                        last_error_at,
                        last_error,
                        interval_seconds,
                        end_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(worker_name) DO UPDATE SET
                        status = excluded.status,
                        updated_at = excluded.updated_at,
                        last_started_at = COALESCE(excluded.last_started_at, worker_state.last_started_at),
                        last_success_at = COALESCE(excluded.last_success_at, worker_state.last_success_at),
                        last_error_at = CASE
                            WHEN excluded.status IN ('starting', 'ok', 'stopped') THEN NULL
                            ELSE COALESCE(excluded.last_error_at, worker_state.last_error_at)
                        END,
                        last_error = CASE
                            WHEN excluded.status IN ('starting', 'ok', 'stopped') THEN NULL
                            ELSE COALESCE(excluded.last_error, worker_state.last_error)
                        END,
                        interval_seconds = COALESCE(excluded.interval_seconds, worker_state.interval_seconds),
                        end_time = COALESCE(excluded.end_time, worker_state.end_time)
                    """,
                    (
                        state.worker_name,
                        state.status,
                        state.updated_at.isoformat(),
                        state.last_started_at.isoformat() if state.last_started_at else None,
                        state.last_success_at.isoformat() if state.last_success_at else None,
                        state.last_error_at.isoformat() if state.last_error_at else None,
                        state.last_error,
                        state.interval_seconds,
                        state.end_time,
                    ),
                )

    def get_worker_state(self, worker_name: str) -> WorkerState | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    worker_name,
                    status,
                    updated_at,
                    last_started_at,
                    last_success_at,
                    last_error_at,
                    last_error,
                    interval_seconds,
                    end_time
                FROM worker_state
                WHERE worker_name = ?
                """,
                (worker_name,),
            ).fetchone()
        return self._row_to_worker_state(row) if row else None

    def list_worker_states(self) -> list[WorkerState]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    worker_name,
                    status,
                    updated_at,
                    last_started_at,
                    last_success_at,
                    last_error_at,
                    last_error,
                    interval_seconds,
                    end_time
                FROM worker_state
                ORDER BY worker_name ASC
                """
            ).fetchall()
        return [self._row_to_worker_state(row) for row in rows]

    def get_app_setting(self, setting_key: str) -> AppSetting | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    setting_key,
                    setting_value,
                    value_type,
                    updated_at,
                    updated_by,
                    detail,
                    restart_required
                FROM app_settings
                WHERE setting_key = ?
                """,
                (setting_key,),
            ).fetchone()
        return self._row_to_app_setting(row) if row else None

    def list_app_settings(self) -> list[AppSetting]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    setting_key,
                    setting_value,
                    value_type,
                    updated_at,
                    updated_by,
                    detail,
                    restart_required
                FROM app_settings
                ORDER BY setting_key ASC
                """
            ).fetchall()
        return [self._row_to_app_setting(row) for row in rows]

    def set_app_setting(
        self,
        setting: AppSetting,
        *,
        audit_actor: str,
        audit_detail: str | None = None,
    ) -> None:
        with self.connect() as connection:
            with connection:
                old_row = connection.execute(
                    "SELECT setting_value FROM app_settings WHERE setting_key = ?",
                    (setting.setting_key,),
                ).fetchone()
                old_value = old_row["setting_value"] if old_row else None
                if old_value == setting.setting_value:
                    return
                connection.execute(
                    """
                    INSERT INTO app_settings (
                        setting_key,
                        setting_value,
                        value_type,
                        updated_at,
                        updated_by,
                        detail,
                        restart_required
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET
                        setting_value = excluded.setting_value,
                        value_type = excluded.value_type,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by,
                        detail = excluded.detail,
                        restart_required = excluded.restart_required
                    """,
                    (
                        setting.setting_key,
                        setting.setting_value,
                        setting.value_type,
                        setting.updated_at.isoformat(),
                        setting.updated_by,
                        setting.detail,
                        1 if setting.restart_required else 0,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO admin_audit_log (
                        event_time,
                        actor,
                        action,
                        setting_key,
                        old_value,
                        new_value,
                        status,
                        detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        setting.updated_at.isoformat(),
                        audit_actor,
                        "set_app_setting",
                        setting.setting_key,
                        old_value,
                        setting.setting_value,
                        "success",
                        audit_detail,
                    ),
                )

    def record_admin_audit_log(self, event: AdminAuditLog) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO admin_audit_log (
                        event_time,
                        actor,
                        action,
                        setting_key,
                        old_value,
                        new_value,
                        status,
                        detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_time.isoformat(),
                        event.actor,
                        event.action,
                        event.setting_key,
                        event.old_value,
                        event.new_value,
                        event.status,
                        event.detail,
                    ),
                )

    def list_admin_audit_logs(self, *, limit: int = 20) -> list[AdminAuditLog]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    event_time,
                    actor,
                    action,
                    setting_key,
                    old_value,
                    new_value,
                    status,
                    detail
                FROM admin_audit_log
                ORDER BY event_time DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_admin_audit_log(row) for row in rows]

    def upsert_stock_metadata(self, metadata: StockMetadata) -> None:
        self.upsert_stock_metadata_many([metadata])

    def upsert_stock_metadata_many(self, metadata_items: list[StockMetadata]) -> None:
        if not metadata_items:
            return
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO stock_metadata (
                        stock_code,
                        stock_name,
                        sector_code,
                        sector_name,
                        updated_at,
                        source
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(stock_code) DO UPDATE SET
                        stock_name = COALESCE(excluded.stock_name, stock_metadata.stock_name),
                        sector_code = COALESCE(excluded.sector_code, stock_metadata.sector_code),
                        sector_name = COALESCE(excluded.sector_name, stock_metadata.sector_name),
                        updated_at = excluded.updated_at,
                        source = excluded.source
                    """,
                    [
                        (
                            item.stock_code,
                            item.stock_name,
                            item.sector_code,
                            item.sector_name,
                            item.updated_at.isoformat(),
                            item.source,
                        )
                        for item in metadata_items
                    ],
                )

    def get_stock_metadata(self, stock_code: str) -> StockMetadata | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT stock_code, stock_name, sector_code, sector_name, updated_at, source
                FROM stock_metadata
                WHERE stock_code = ?
                """,
                (stock_code,),
            ).fetchone()
        return self._row_to_stock_metadata(row) if row else None

    def count_stock_metadata(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM stock_metadata").fetchone()
        return int(row["count"])

    def list_stock_metadata(self) -> list[StockMetadata]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stock_code, stock_name, sector_code, sector_name, updated_at, source
                FROM stock_metadata
                ORDER BY sector_name ASC, stock_code ASC
                """
            ).fetchall()
        return [self._row_to_stock_metadata(row) for row in rows]

    def list_sector_rollups_for_business_date(self, business_date: date) -> list[SectorDailyRollup]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH summary_with_sector AS (
                    SELECT
                        COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS sector_name,
                        NULLIF(TRIM(sm.sector_code), '') AS sector_code,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        dss.mention_count AS mention_count
                    FROM daily_stock_summaries dss
                    LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
                    WHERE dss.business_date = ?
                )
                SELECT
                    sector_name,
                    MIN(sector_code) AS sector_code,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM summary_with_sector
                GROUP BY sector_name
                ORDER BY report_count DESC, stock_count DESC, sector_name ASC
                """,
                (business_date.isoformat(),),
            ).fetchall()
        return [
            SectorDailyRollup(
                business_date=business_date,
                sector_name=row["sector_name"],
                sector_code=row["sector_code"],
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
            )
            for row in rows
        ]

    def list_daily_summaries_for_sector(self, business_date: date, sector_name: str) -> list[DailyStockSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    dss.business_date,
                    dss.stock_name,
                    dss.stock_code,
                    dss.mention_count,
                    dss.broker_display,
                    dss.target_price_min,
                    dss.target_price_max,
                    dss.dominant_opinion,
                    dss.generated_at
                FROM daily_stock_summaries dss
                LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
                WHERE dss.business_date = ?
                  AND COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') = ?
                ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
                """,
                (business_date.isoformat(), sector_name),
            ).fetchall()
        return [self._row_to_daily_summary(row) for row in rows]

    def list_sector_trend(self, sector_name: str, *, limit: int = 20) -> list[CategoryTrendPoint]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH summary_with_sector AS (
                    SELECT
                        dss.business_date AS business_date,
                        COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS sector_name,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        dss.mention_count AS mention_count
                    FROM daily_stock_summaries dss
                    LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
                )
                SELECT
                    business_date,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM summary_with_sector
                WHERE sector_name = ?
                GROUP BY business_date
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (sector_name, limit),
            ).fetchall()
        return [
            CategoryTrendPoint(
                business_date=date.fromisoformat(row["business_date"]),
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
            )
            for row in rows
        ]

    def upsert_stock_theme_memberships(self, memberships: list[StockThemeMembership]) -> None:
        if not memberships:
            return
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO stock_theme_memberships (
                        theme_code,
                        theme_name,
                        stock_code,
                        stock_name,
                        updated_at,
                        source
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_code, stock_code) DO UPDATE SET
                        theme_name = excluded.theme_name,
                        stock_name = COALESCE(excluded.stock_name, stock_theme_memberships.stock_name),
                        updated_at = excluded.updated_at,
                        source = excluded.source
                    """,
                    [
                        (
                            item.theme_code,
                            item.theme_name,
                            item.stock_code,
                            item.stock_name,
                            item.updated_at.isoformat(),
                            item.source,
                        )
                        for item in memberships
                    ],
                )

    def count_stock_theme_memberships(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM stock_theme_memberships").fetchone()
        return int(row["count"])

    def list_stock_theme_memberships(self) -> list[StockThemeMembership]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT theme_code, theme_name, stock_code, stock_name, updated_at, source
                FROM stock_theme_memberships
                ORDER BY theme_name ASC, theme_code ASC, stock_code ASC
                """
            ).fetchall()
        return [self._row_to_stock_theme_membership(row) for row in rows]

    def list_theme_rollups_for_business_date(self, business_date: date) -> list[ThemeDailyRollup]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH theme_stock_rows AS (
                    SELECT
                        COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS theme_name,
                        stm.theme_code AS theme_code,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        MAX(dss.mention_count) AS mention_count
                    FROM daily_stock_summaries dss
                    JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
                    WHERE dss.business_date = ?
                    GROUP BY
                        COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code),
                        COALESCE(dss.stock_code, dss.stock_name)
                )
                SELECT
                    MIN(theme_code) AS theme_code,
                    theme_name,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM theme_stock_rows
                GROUP BY theme_name
                ORDER BY report_count DESC, stock_count DESC, theme_name ASC
                """,
                (business_date.isoformat(),),
            ).fetchall()
        return [
            ThemeDailyRollup(
                business_date=business_date,
                theme_code=row["theme_code"],
                theme_name=row["theme_name"],
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
            )
            for row in rows
        ]

    def list_daily_summaries_for_theme(self, business_date: date, theme_name: str) -> list[DailyStockSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    dss.business_date,
                    dss.stock_name,
                    dss.stock_code,
                    dss.mention_count,
                    dss.broker_display,
                    dss.target_price_min,
                    dss.target_price_max,
                    dss.dominant_opinion,
                    dss.generated_at
                FROM daily_stock_summaries dss
                JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
                WHERE dss.business_date = ?
                  AND COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) = ?
                ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
                """,
                (business_date.isoformat(), theme_name),
            ).fetchall()
        return [self._row_to_daily_summary(row) for row in rows]

    def list_theme_trend(self, theme_name: str, *, limit: int = 20) -> list[CategoryTrendPoint]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH theme_stock_rows AS (
                    SELECT
                        dss.business_date AS business_date,
                        COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS theme_name,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        MAX(dss.mention_count) AS mention_count
                    FROM daily_stock_summaries dss
                    JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
                    GROUP BY
                        dss.business_date,
                        COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code),
                        COALESCE(dss.stock_code, dss.stock_name)
                )
                SELECT
                    business_date,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM theme_stock_rows
                WHERE theme_name = ?
                GROUP BY business_date
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (theme_name, limit),
            ).fetchall()
        return [
            CategoryTrendPoint(
                business_date=date.fromisoformat(row["business_date"]),
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
            )
            for row in rows
        ]

    def upsert_category_catalog_items(self, items: list[CategoryCatalogItem]) -> int:
        if not items:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO category_master (
                        category_type,
                        category_key,
                        display_name,
                        source,
                        enabled,
                        group_name,
                        priority,
                        note,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(category_type, category_key) DO UPDATE SET
                        display_name = excluded.display_name,
                        source = excluded.source,
                        enabled = excluded.enabled,
                        group_name = excluded.group_name,
                        priority = excluded.priority,
                        note = excluded.note,
                        updated_at = excluded.updated_at
                    """,
                    [
                        (
                            item.category_type,
                            item.category_key,
                            item.display_name,
                            item.source,
                            1 if item.enabled else 0,
                            item.group_name,
                            item.priority,
                            item.note,
                            item.updated_at.isoformat(),
                        )
                        for item in items
                    ],
                )
        return len(items)

    def list_category_catalog(
        self,
        *,
        category_type: str | None = None,
        enabled_only: bool = False,
    ) -> list[CategoryCatalogItem]:
        clauses: list[str] = []
        params: list[object] = []
        if category_type:
            clauses.append("category_type = ?")
            params.append(category_type)
        if enabled_only:
            clauses.append("enabled = 1")
        where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    category_type,
                    category_key,
                    display_name,
                    source,
                    enabled,
                    group_name,
                    priority,
                    note,
                    updated_at
                FROM category_master
                {where_sql}
                ORDER BY category_type ASC, priority ASC, display_name ASC, category_key ASC
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_category_catalog_item(row) for row in rows]

    def set_category_catalog_enabled(
        self,
        *,
        category_type: str,
        category_key: str,
        enabled: bool,
        updated_at: datetime,
    ) -> int:
        with self.connect() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE category_master
                    SET enabled = ?, updated_at = ?
                    WHERE category_type = ? AND category_key = ?
                    """,
                    (1 if enabled else 0, updated_at.isoformat(), category_type, category_key),
                )
        return int(cursor.rowcount)

    def upsert_category_membership_snapshots(self, snapshots: list[CategoryMembershipSnapshot]) -> int:
        if not snapshots:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(snapshot_date, category_type, category_key, stock_code, source) DO UPDATE SET
                        display_name = excluded.display_name,
                        stock_name = COALESCE(excluded.stock_name, category_membership_snapshots.stock_name),
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.snapshot_date.isoformat(),
                            item.category_type,
                            item.category_key,
                            item.display_name,
                            item.stock_code,
                            item.stock_name,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in snapshots
                    ],
                )
        return len(snapshots)

    def count_category_membership_snapshots(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM category_membership_snapshots").fetchone()
        return int(row["count"])

    def latest_category_snapshot_date(
        self,
        *,
        category_type: str,
        business_date: date,
        category_key: str | None = None,
        enabled_only: bool = False,
    ) -> date | None:
        key_filter = "AND cms.category_key = ?" if category_key else ""
        enabled_join = ""
        enabled_filter = ""
        params: list[object] = [category_type, business_date.isoformat()]
        if category_key:
            params.append(category_key)
        if enabled_only:
            enabled_join = """
                JOIN category_master cm
                  ON cm.category_type = cms.category_type
                 AND cm.category_key = cms.category_key
            """
            enabled_filter = "AND cm.enabled = 1"
        with self.connect() as connection:
            row = connection.execute(
                f"""
                SELECT MAX(snapshot_date) AS snapshot_date
                FROM category_membership_snapshots cms
                {enabled_join}
                WHERE cms.category_type = ?
                  AND cms.snapshot_date <= ?
                  {key_filter}
                  {enabled_filter}
                """,
                tuple(params),
            ).fetchone()
        raw = row["snapshot_date"] if row else None
        return date.fromisoformat(raw) if raw else None

    def _category_catalog_enabled_status(self, *, category_type: str, category_key: str) -> bool | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT enabled
                FROM category_master
                WHERE category_type = ?
                  AND category_key = ?
                """,
                (category_type, category_key),
            ).fetchone()
        if row is None:
            return None
        return bool(row["enabled"])

    def list_category_rollups_for_business_date(
        self,
        business_date: date,
        category_type: str,
    ) -> list[CategoryDailyRollup]:
        if self.latest_category_snapshot_date(category_type=category_type, business_date=business_date) is None:
            return self._list_category_rollup_fallback(business_date, category_type)
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH latest_snapshots AS (
                    SELECT
                        cms.category_key AS category_key,
                        MAX(cms.snapshot_date) AS snapshot_date
                    FROM category_membership_snapshots cms
                    JOIN category_master cm
                      ON cm.category_type = cms.category_type
                     AND cm.category_key = cms.category_key
                    WHERE cms.category_type = ?
                      AND cms.snapshot_date <= ?
                      AND cm.enabled = 1
                    GROUP BY cms.category_key
                ),
                category_stock_rows AS (
                    SELECT
                        cms.category_key AS category_key,
                        cms.display_name AS display_name,
                        cms.snapshot_date AS snapshot_date,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        MAX(dss.mention_count) AS mention_count
                    FROM daily_stock_summaries dss
                    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
                    JOIN latest_snapshots latest
                      ON latest.category_key = cms.category_key
                     AND latest.snapshot_date = cms.snapshot_date
                    WHERE dss.business_date = ?
                      AND cms.category_type = ?
                    GROUP BY cms.category_key, cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
                )
                SELECT
                    category_key,
                    display_name,
                    snapshot_date,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM category_stock_rows
                GROUP BY category_key, display_name, snapshot_date
                ORDER BY report_count DESC, stock_count DESC, display_name ASC, category_key ASC
                """,
                (category_type, business_date.isoformat(), business_date.isoformat(), category_type),
            ).fetchall()
        return [
            CategoryDailyRollup(
                business_date=business_date,
                category_type=category_type,
                category_key=row["category_key"],
                display_name=row["display_name"],
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
                snapshot_date=date.fromisoformat(row["snapshot_date"]),
                mapping_source="dated_snapshot",
            )
            for row in rows
        ]

    def list_category_rollups_by_display_name_for_business_date(
        self,
        business_date: date,
        category_type: str,
    ) -> list[CategoryDailyRollup]:
        if self.latest_category_snapshot_date(category_type=category_type, business_date=business_date) is None:
            fallback = self._list_category_rollup_fallback(business_date, category_type)
            grouped: dict[str, dict[str, int]] = {}
            for item in fallback:
                current = grouped.setdefault(item.display_name, {"stock_count": 0, "report_count": 0})
                current["stock_count"] += item.stock_count
                current["report_count"] += item.report_count
            return [
                CategoryDailyRollup(
                    business_date=business_date,
                    category_type=category_type,
                    category_key=display_name,
                    display_name=display_name,
                    stock_count=values["stock_count"],
                    report_count=values["report_count"],
                    snapshot_date=None,
                    mapping_source="latest_mapping_fallback",
                )
                for display_name, values in sorted(
                    grouped.items(),
                    key=lambda item: (-item[1]["report_count"], -item[1]["stock_count"], item[0]),
                )
            ]
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH latest_snapshots AS (
                    SELECT
                        cms.display_name AS display_name,
                        MAX(cms.snapshot_date) AS snapshot_date
                    FROM category_membership_snapshots cms
                    JOIN category_master cm
                      ON cm.category_type = cms.category_type
                     AND cm.category_key = cms.category_key
                    WHERE cms.category_type = ?
                      AND cms.snapshot_date <= ?
                      AND cm.enabled = 1
                    GROUP BY cms.display_name
                ),
                category_stock_rows AS (
                    SELECT
                        cms.display_name AS display_name,
                        cms.snapshot_date AS snapshot_date,
                        COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
                        MAX(dss.mention_count) AS mention_count
                    FROM daily_stock_summaries dss
                    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
                    JOIN latest_snapshots latest
                      ON latest.display_name = cms.display_name
                     AND latest.snapshot_date = cms.snapshot_date
                    WHERE dss.business_date = ?
                      AND cms.category_type = ?
                    GROUP BY cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
                )
                SELECT
                    display_name,
                    snapshot_date,
                    COUNT(DISTINCT stock_identity) AS stock_count,
                    COALESCE(SUM(mention_count), 0) AS report_count
                FROM category_stock_rows
                GROUP BY display_name, snapshot_date
                ORDER BY report_count DESC, stock_count DESC, display_name ASC
                """,
                (category_type, business_date.isoformat(), business_date.isoformat(), category_type),
            ).fetchall()
        return [
            CategoryDailyRollup(
                business_date=business_date,
                category_type=category_type,
                category_key=row["display_name"],
                display_name=row["display_name"],
                stock_count=int(row["stock_count"]),
                report_count=int(row["report_count"]),
                snapshot_date=date.fromisoformat(row["snapshot_date"]),
                mapping_source="dated_snapshot",
            )
            for row in rows
        ]

    def list_daily_summaries_for_category(
        self,
        business_date: date,
        category_type: str,
        category_key: str,
    ) -> list[DailyStockSummary]:
        if self._category_catalog_enabled_status(category_type=category_type, category_key=category_key) is False:
            return []
        snapshot_date = self.latest_category_snapshot_date(
            category_type=category_type,
            business_date=business_date,
            category_key=category_key,
            enabled_only=True,
        )
        if snapshot_date is None:
            if category_type == "sector":
                return self.list_daily_summaries_for_sector(business_date, category_key)
            if category_type == "theme":
                return self.list_daily_summaries_for_theme(business_date, category_key)
            return []
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    dss.business_date,
                    dss.stock_name,
                    dss.stock_code,
                    dss.mention_count,
                    dss.broker_display,
                    dss.target_price_min,
                    dss.target_price_max,
                    dss.dominant_opinion,
                    dss.generated_at
                FROM daily_stock_summaries dss
                JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
                WHERE dss.business_date = ?
                  AND cms.snapshot_date = ?
                  AND cms.category_type = ?
                  AND cms.category_key = ?
                ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
                """,
                (business_date.isoformat(), snapshot_date.isoformat(), category_type, category_key),
            ).fetchall()
        return [self._row_to_daily_summary(row) for row in rows]

    def list_daily_summaries_for_category_display_name(
        self,
        business_date: date,
        category_type: str,
        display_name: str,
    ) -> list[DailyStockSummary]:
        snapshot_date = self.latest_category_snapshot_date(category_type=category_type, business_date=business_date)
        if snapshot_date is None:
            if category_type == "sector":
                return self.list_daily_summaries_for_sector(business_date, display_name)
            if category_type == "theme":
                return self.list_daily_summaries_for_theme(business_date, display_name)
            return []
        with self.connect() as connection:
            rows = connection.execute(
                """
                WITH latest_snapshot AS (
                    SELECT MAX(cms.snapshot_date) AS snapshot_date
                    FROM category_membership_snapshots cms
                    JOIN category_master cm
                      ON cm.category_type = cms.category_type
                     AND cm.category_key = cms.category_key
                    WHERE cms.category_type = ?
                      AND cms.display_name = ?
                      AND cms.snapshot_date <= ?
                      AND cm.enabled = 1
                )
                SELECT DISTINCT
                    dss.business_date,
                    dss.stock_name,
                    dss.stock_code,
                    dss.mention_count,
                    dss.broker_display,
                    dss.target_price_min,
                    dss.target_price_max,
                    dss.dominant_opinion,
                    dss.generated_at
                FROM daily_stock_summaries dss
                JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
                JOIN latest_snapshot latest ON latest.snapshot_date = cms.snapshot_date
                WHERE dss.business_date = ?
                  AND cms.category_type = ?
                  AND cms.display_name = ?
                ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
                """,
                (
                    category_type,
                    display_name,
                    business_date.isoformat(),
                    business_date.isoformat(),
                    category_type,
                    display_name,
                ),
            ).fetchall()
        return [self._row_to_daily_summary(row) for row in rows]

    def list_category_trend(
        self,
        category_type: str,
        category_key: str,
        *,
        limit: int = 20,
    ) -> list[CategoryTrendPoint]:
        if category_type not in {"sector", "theme"}:
            return []
        points: list[CategoryTrendPoint] = []
        for business_date, _summary_count in self.count_summaries_by_business_date(limit=max(limit * 4, limit)):
            summaries = self.list_daily_summaries_for_category(business_date, category_type, category_key)
            if not summaries:
                continue
            stock_identities = {summary.stock_code or summary.stock_name for summary in summaries}
            points.append(
                CategoryTrendPoint(
                    business_date=business_date,
                    stock_count=len(stock_identities),
                    report_count=sum(summary.mention_count for summary in summaries),
                )
            )
            if len(points) >= limit:
                break
        return points

    def list_category_trend_by_display_name(
        self,
        category_type: str,
        display_name: str,
        *,
        limit: int = 20,
    ) -> list[CategoryTrendPoint]:
        if category_type not in {"sector", "theme"}:
            return []
        points: list[CategoryTrendPoint] = []
        for business_date, _summary_count in self.count_summaries_by_business_date(limit=max(limit * 4, limit)):
            summaries = self.list_daily_summaries_for_category_display_name(business_date, category_type, display_name)
            if not summaries:
                continue
            stock_identities = {summary.stock_code or summary.stock_name for summary in summaries}
            points.append(
                CategoryTrendPoint(
                    business_date=business_date,
                    stock_count=len(stock_identities),
                    report_count=sum(summary.mention_count for summary in summaries),
                )
            )
            if len(points) >= limit:
                break
        return points

    def _list_category_rollup_fallback(self, business_date: date, category_type: str) -> list[CategoryDailyRollup]:
        disabled = self._disabled_category_identifiers(category_type=category_type)
        if category_type == "sector":
            return [
                CategoryDailyRollup(
                    business_date=item.business_date,
                    category_type="sector",
                    category_key=item.sector_name,
                    display_name=item.sector_name,
                    stock_count=item.stock_count,
                    report_count=item.report_count,
                    snapshot_date=None,
                    mapping_source="latest_mapping_fallback",
                )
                for item in self.list_sector_rollups_for_business_date(business_date)
                if item.sector_name not in disabled and (item.sector_code or "") not in disabled
            ]
        if category_type == "theme":
            return [
                CategoryDailyRollup(
                    business_date=item.business_date,
                    category_type="theme",
                    category_key=item.theme_name,
                    display_name=item.theme_name,
                    stock_count=item.stock_count,
                    report_count=item.report_count,
                    snapshot_date=None,
                    mapping_source="latest_mapping_fallback",
                )
                for item in self.list_theme_rollups_for_business_date(business_date)
                if item.theme_name not in disabled and item.theme_code not in disabled
            ]
        return []

    def _disabled_category_identifiers(self, *, category_type: str) -> set[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT category_key, display_name
                FROM category_master
                WHERE category_type = ?
                  AND enabled = 0
                """,
                (category_type,),
            ).fetchall()
        identifiers: set[str] = set()
        for row in rows:
            identifiers.add(str(row["category_key"]))
            identifiers.add(str(row["display_name"]))
        return identifiers

    def upsert_stock_market_daily(self, snapshots: list[StockMarketDailySnapshot]) -> int:
        if not snapshots:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO stock_market_daily (
                        business_date, stock_code, stock_name, market, section_name,
                        close_price, change_amount, change_percent, open_price, high_price,
                        low_price, volume, turnover, market_cap, listed_shares,
                        fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, stock_code, source) DO UPDATE SET
                        stock_name = excluded.stock_name,
                        market = excluded.market,
                        section_name = excluded.section_name,
                        close_price = excluded.close_price,
                        change_amount = excluded.change_amount,
                        change_percent = excluded.change_percent,
                        open_price = excluded.open_price,
                        high_price = excluded.high_price,
                        low_price = excluded.low_price,
                        volume = excluded.volume,
                        turnover = excluded.turnover,
                        market_cap = excluded.market_cap,
                        listed_shares = excluded.listed_shares,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.stock_code,
                            item.stock_name,
                            item.market,
                            item.section_name,
                            item.close_price,
                            item.change_amount,
                            item.change_percent,
                            item.open_price,
                            item.high_price,
                            item.low_price,
                            item.volume,
                            item.turnover,
                            item.market_cap,
                            item.listed_shares,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in snapshots
                    ],
                )
        return len(snapshots)

    def upsert_etf_daily_snapshots(self, snapshots: list[EtfDailySnapshot]) -> int:
        if not snapshots:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO etf_daily_snapshots (
                        business_date, etf_code, etf_name, close_price, change_amount,
                        change_percent, nav, open_price, high_price, low_price,
                        volume, turnover, market_cap, net_assets_total, listed_shares,
                        underlying_index_name, underlying_index_close,
                        underlying_index_change_amount, underlying_index_change_percent,
                        fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, etf_code, source) DO UPDATE SET
                        etf_name = excluded.etf_name,
                        close_price = excluded.close_price,
                        change_amount = excluded.change_amount,
                        change_percent = excluded.change_percent,
                        nav = excluded.nav,
                        open_price = excluded.open_price,
                        high_price = excluded.high_price,
                        low_price = excluded.low_price,
                        volume = excluded.volume,
                        turnover = excluded.turnover,
                        market_cap = excluded.market_cap,
                        net_assets_total = excluded.net_assets_total,
                        listed_shares = excluded.listed_shares,
                        underlying_index_name = excluded.underlying_index_name,
                        underlying_index_close = excluded.underlying_index_close,
                        underlying_index_change_amount = excluded.underlying_index_change_amount,
                        underlying_index_change_percent = excluded.underlying_index_change_percent,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.etf_code,
                            item.etf_name,
                            item.close_price,
                            item.change_amount,
                            item.change_percent,
                            item.nav,
                            item.open_price,
                            item.high_price,
                            item.low_price,
                            item.volume,
                            item.turnover,
                            item.market_cap,
                            item.net_assets_total,
                            item.listed_shares,
                            item.underlying_index_name,
                            item.underlying_index_close,
                            item.underlying_index_change_amount,
                            item.underlying_index_change_percent,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in snapshots
                    ],
                )
        return len(snapshots)

    def upsert_krx_stock_metadata(self, snapshots: list[KrxStockMetadataSnapshot]) -> int:
        if not snapshots:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO krx_stock_metadata (
                        business_date, standard_code, stock_code, stock_name,
                        stock_short_name, stock_english_name, listed_date, market,
                        security_group, section_name, stock_certificate_type,
                        par_value, listed_shares, fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, stock_code, source) DO UPDATE SET
                        standard_code = excluded.standard_code,
                        stock_name = excluded.stock_name,
                        stock_short_name = excluded.stock_short_name,
                        stock_english_name = excluded.stock_english_name,
                        listed_date = excluded.listed_date,
                        market = excluded.market,
                        security_group = excluded.security_group,
                        section_name = excluded.section_name,
                        stock_certificate_type = excluded.stock_certificate_type,
                        par_value = excluded.par_value,
                        listed_shares = excluded.listed_shares,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.standard_code,
                            item.stock_code,
                            item.stock_name,
                            item.stock_short_name,
                            item.stock_english_name,
                            item.listed_date.isoformat() if item.listed_date else None,
                            item.market,
                            item.security_group,
                            item.section_name,
                            item.stock_certificate_type,
                            item.par_value,
                            item.listed_shares,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in snapshots
                    ],
                )
        return len(snapshots)

    def get_latest_krx_stock_metadata(self, stock_code: str) -> KrxStockMetadataSnapshot | None:
        normalized_code = stock_code.strip()
        if not normalized_code:
            return None
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    business_date, standard_code, stock_code, stock_name,
                    stock_short_name, stock_english_name, listed_date, market,
                    security_group, section_name, stock_certificate_type,
                    par_value, listed_shares, fetched_at, source
                FROM krx_stock_metadata
                WHERE stock_code = ?
                ORDER BY business_date DESC, fetched_at DESC
                LIMIT 1
                """,
                (normalized_code,),
            ).fetchone()
        if row is None:
            return None
        return KrxStockMetadataSnapshot(
            business_date=date.fromisoformat(row["business_date"]),
            standard_code=row["standard_code"],
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            stock_short_name=row["stock_short_name"],
            stock_english_name=row["stock_english_name"],
            listed_date=date.fromisoformat(row["listed_date"]) if row["listed_date"] else None,
            market=row["market"],
            security_group=row["security_group"],
            section_name=row["section_name"],
            stock_certificate_type=row["stock_certificate_type"],
            par_value=row["par_value"],
            listed_shares=row["listed_shares"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    def upsert_market_index_daily(self, snapshots: list[MarketIndexDailySnapshot]) -> int:
        if not snapshots:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO market_index_daily (
                        business_date, index_series, index_class, index_name,
                        close_index, change_amount, change_percent, open_index,
                        high_index, low_index, volume, turnover, market_cap,
                        fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, index_series, index_name, source) DO UPDATE SET
                        index_class = excluded.index_class,
                        close_index = excluded.close_index,
                        change_amount = excluded.change_amount,
                        change_percent = excluded.change_percent,
                        open_index = excluded.open_index,
                        high_index = excluded.high_index,
                        low_index = excluded.low_index,
                        volume = excluded.volume,
                        turnover = excluded.turnover,
                        market_cap = excluded.market_cap,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.index_series,
                            item.index_class,
                            item.index_name,
                            item.close_index,
                            item.change_amount,
                            item.change_percent,
                            item.open_index,
                            item.high_index,
                            item.low_index,
                            item.volume,
                            item.turnover,
                            item.market_cap,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in snapshots
                    ],
                )
        return len(snapshots)

    def list_stock_market_daily_by_turnover(
        self,
        business_date: date,
        *,
        market: str | None = None,
        limit: int = 10,
    ) -> list[StockMarketDailySnapshot]:
        params: list[object] = [business_date.isoformat()]
        market_clause = ""
        if market:
            market_clause = "AND market = ?"
            params.append(market)
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    business_date, stock_code, stock_name, market, section_name,
                    close_price, change_amount, change_percent, open_price, high_price,
                    low_price, volume, turnover, market_cap, listed_shares,
                    fetched_at, source
                FROM stock_market_daily
                WHERE business_date = ?
                  {market_clause}
                ORDER BY COALESCE(turnover, 0) DESC, stock_code ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_stock_market_daily_snapshot(row) for row in rows]

    def list_stock_market_daily_for_codes(
        self,
        business_date: date,
        stock_codes: list[str],
        *,
        source: str = "krx",
    ) -> list[StockMarketDailySnapshot]:
        normalized_codes = sorted({code.strip() for code in stock_codes if code and code.strip()})
        if not normalized_codes:
            return []
        placeholders = ", ".join("?" for _ in normalized_codes)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    business_date, stock_code, stock_name, market, section_name,
                    close_price, change_amount, change_percent, open_price, high_price,
                    low_price, volume, turnover, market_cap, listed_shares,
                    fetched_at, source
                FROM stock_market_daily
                WHERE business_date = ?
                  AND source = ?
                  AND stock_code IN ({placeholders})
                ORDER BY stock_code ASC
                """,
                (business_date.isoformat(), source, *normalized_codes),
            ).fetchall()
        return [self._row_to_stock_market_daily_snapshot(row) for row in rows]

    def list_stock_market_daily_for_code_on_or_before(
        self,
        business_date: date,
        stock_code: str,
        *,
        limit: int = 5,
        source: str = "krx",
    ) -> list[StockMarketDailySnapshot]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, stock_code, stock_name, market, section_name,
                    close_price, change_amount, change_percent, open_price, high_price,
                    low_price, volume, turnover, market_cap, listed_shares,
                    fetched_at, source
                FROM stock_market_daily
                WHERE business_date <= ?
                  AND stock_code = ?
                  AND source = ?
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (business_date.isoformat(), stock_code, source, limit),
            ).fetchall()
        return [self._row_to_stock_market_daily_snapshot(row) for row in rows]

    def list_stock_market_daily_for_code_on_or_after(
        self,
        business_date: date,
        stock_code: str,
        *,
        limit: int = 21,
        source: str = "krx",
    ) -> list[StockMarketDailySnapshot]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, stock_code, stock_name, market, section_name,
                    close_price, change_amount, change_percent, open_price, high_price,
                    low_price, volume, turnover, market_cap, listed_shares,
                    fetched_at, source
                FROM stock_market_daily
                WHERE business_date >= ?
                  AND stock_code = ?
                  AND source = ?
                ORDER BY business_date ASC
                LIMIT ?
                """,
                (business_date.isoformat(), stock_code, source, limit),
            ).fetchall()
        return [self._row_to_stock_market_daily_snapshot(row) for row in rows]

    def upsert_stock_investor_flow_daily(self, rows: list[StockInvestorFlowDaily]) -> int:
        if not rows:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO stock_investor_flow_daily (
                        business_date, stock_code, stock_name, market, investor_type,
                        sell_volume, buy_volume, net_buy_volume,
                        sell_amount, buy_amount, net_buy_amount,
                        volume_unit, amount_unit, candidate_score, candidate_reasons,
                        fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, stock_code, investor_type, source) DO UPDATE SET
                        stock_name = excluded.stock_name,
                        market = excluded.market,
                        sell_volume = excluded.sell_volume,
                        buy_volume = excluded.buy_volume,
                        net_buy_volume = excluded.net_buy_volume,
                        sell_amount = excluded.sell_amount,
                        buy_amount = excluded.buy_amount,
                        net_buy_amount = excluded.net_buy_amount,
                        volume_unit = excluded.volume_unit,
                        amount_unit = excluded.amount_unit,
                        candidate_score = excluded.candidate_score,
                        candidate_reasons = excluded.candidate_reasons,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.stock_code,
                            item.stock_name,
                            item.market,
                            item.investor_type,
                            item.sell_volume,
                            item.buy_volume,
                            item.net_buy_volume,
                            item.sell_amount,
                            item.buy_amount,
                            item.net_buy_amount,
                            item.volume_unit,
                            item.amount_unit,
                            item.candidate_score,
                            item.candidate_reasons,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in rows
                    ],
                )
        return len(rows)

    def list_stock_investor_flow_daily(
        self,
        business_date: date,
        stock_code: str,
        *,
        source: str = "krx_data_market",
    ) -> list[StockInvestorFlowDaily]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, stock_code, stock_name, market, investor_type,
                    sell_volume, buy_volume, net_buy_volume,
                    sell_amount, buy_amount, net_buy_amount,
                    volume_unit, amount_unit, candidate_score, candidate_reasons,
                    fetched_at, source
                FROM stock_investor_flow_daily
                WHERE business_date = ?
                  AND stock_code = ?
                  AND source = ?
                ORDER BY investor_type ASC
                """,
                (business_date.isoformat(), stock_code, source),
            ).fetchall()
        return [self._row_to_stock_investor_flow_daily(row) for row in rows]

    def upsert_market_investor_flow_daily(self, rows: list[MarketInvestorFlowDaily]) -> int:
        if not rows:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO market_investor_flow_daily (
                        business_date, market, investor_type,
                        sell_volume, buy_volume, net_buy_volume,
                        sell_amount, buy_amount, net_buy_amount,
                        volume_unit, amount_unit, fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, market, investor_type, source) DO UPDATE SET
                        sell_volume = excluded.sell_volume,
                        buy_volume = excluded.buy_volume,
                        net_buy_volume = excluded.net_buy_volume,
                        sell_amount = excluded.sell_amount,
                        buy_amount = excluded.buy_amount,
                        net_buy_amount = excluded.net_buy_amount,
                        volume_unit = excluded.volume_unit,
                        amount_unit = excluded.amount_unit,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.market,
                            item.investor_type,
                            item.sell_volume,
                            item.buy_volume,
                            item.net_buy_volume,
                            item.sell_amount,
                            item.buy_amount,
                            item.net_buy_amount,
                            item.volume_unit,
                            item.amount_unit,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in rows
                    ],
                )
        return len(rows)

    def upsert_investor_net_buy_top_daily(self, rows: list[InvestorNetBuyTopDaily]) -> int:
        if not rows:
            return 0
        with self.connect() as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO investor_net_buy_top_daily (
                        business_date, market, investor_type, rank,
                        stock_code, stock_name, net_buy_volume, net_buy_amount,
                        fetched_at, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(business_date, market, investor_type, rank, source) DO UPDATE SET
                        stock_code = excluded.stock_code,
                        stock_name = excluded.stock_name,
                        net_buy_volume = excluded.net_buy_volume,
                        net_buy_amount = excluded.net_buy_amount,
                        fetched_at = excluded.fetched_at
                    """,
                    [
                        (
                            item.business_date.isoformat(),
                            item.market,
                            item.investor_type,
                            item.rank,
                            item.stock_code,
                            item.stock_name,
                            item.net_buy_volume,
                            item.net_buy_amount,
                            item.fetched_at.isoformat(),
                            item.source,
                        )
                        for item in rows
                    ],
                )
        return len(rows)

    def list_market_investor_flow_daily(
        self,
        business_date: date,
        market: str,
        *,
        source: str = "krx_data_market",
    ) -> list[MarketInvestorFlowDaily]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, market, investor_type,
                    sell_volume, buy_volume, net_buy_volume,
                    sell_amount, buy_amount, net_buy_amount,
                    volume_unit, amount_unit, fetched_at, source
                FROM market_investor_flow_daily
                WHERE business_date = ?
                  AND market = ?
                  AND source = ?
                ORDER BY investor_type ASC
                """,
                (business_date.isoformat(), market, source),
            ).fetchall()
        return [self._row_to_market_investor_flow_daily(row) for row in rows]

    def list_investor_net_buy_top_daily(
        self,
        business_date: date,
        market: str,
        investor_type: str,
        *,
        source: str = "krx_data_market",
        limit: int = 20,
    ) -> list[InvestorNetBuyTopDaily]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, market, investor_type, rank,
                    stock_code, stock_name, net_buy_volume, net_buy_amount,
                    fetched_at, source
                FROM investor_net_buy_top_daily
                WHERE business_date = ?
                  AND market = ?
                  AND investor_type = ?
                  AND source = ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (business_date.isoformat(), market, investor_type, source, limit),
            ).fetchall()
        return [self._row_to_investor_net_buy_top_daily(row) for row in rows]

    def find_investor_net_buy_top_for_stock(
        self,
        business_date: date,
        stock_code: str,
        investor_type: str,
        *,
        source: str = "krx_data_market",
    ) -> InvestorNetBuyTopDaily | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    business_date, market, investor_type, rank,
                    stock_code, stock_name, net_buy_volume, net_buy_amount,
                    fetched_at, source
                FROM investor_net_buy_top_daily
                WHERE business_date = ?
                  AND stock_code = ?
                  AND investor_type = ?
                  AND source = ?
                ORDER BY rank ASC, market ASC
                LIMIT 1
                """,
                (business_date.isoformat(), stock_code, investor_type, source),
            ).fetchone()
        return self._row_to_investor_net_buy_top_daily(row) if row else None

    def list_etf_daily_by_turnover(
        self,
        business_date: date,
        *,
        limit: int = 10,
    ) -> list[EtfDailySnapshot]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    business_date, etf_code, etf_name, close_price, change_amount,
                    change_percent, nav, open_price, high_price, low_price,
                    volume, turnover, market_cap, net_assets_total, listed_shares,
                    underlying_index_name, underlying_index_close,
                    underlying_index_change_amount, underlying_index_change_percent,
                    fetched_at, source
                FROM etf_daily_snapshots
                WHERE business_date = ?
                ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
                LIMIT ?
                """,
                (business_date.isoformat(), limit),
            ).fetchall()
        return [self._row_to_etf_daily_snapshot(row) for row in rows]

    def list_etf_daily_for_codes(
        self,
        business_date: date,
        etf_codes: list[str],
    ) -> list[EtfDailySnapshot]:
        normalized_codes = sorted({code.strip() for code in etf_codes if code and code.strip()})
        if not normalized_codes:
            return []
        placeholders = ", ".join("?" for _ in normalized_codes)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    business_date, etf_code, etf_name, close_price, change_amount,
                    change_percent, nav, open_price, high_price, low_price,
                    volume, turnover, market_cap, net_assets_total, listed_shares,
                    underlying_index_name, underlying_index_close,
                    underlying_index_change_amount, underlying_index_change_percent,
                    fetched_at, source
                FROM etf_daily_snapshots
                WHERE business_date = ?
                  AND etf_code IN ({placeholders})
                ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
                """,
                (business_date.isoformat(), *normalized_codes),
            ).fetchall()
        return [self._row_to_etf_daily_snapshot(row) for row in rows]

    def list_market_index_daily(
        self,
        business_date: date,
        *,
        index_series: str | None = None,
        limit: int = 20,
    ) -> list[MarketIndexDailySnapshot]:
        params: list[object] = [business_date.isoformat()]
        series_clause = ""
        if index_series:
            series_clause = "AND index_series = ?"
            params.append(index_series)
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    business_date, index_series, index_class, index_name,
                    close_index, change_amount, change_percent, open_index,
                    high_index, low_index, volume, turnover, market_cap,
                    fetched_at, source
                FROM market_index_daily
                WHERE business_date = ?
                  {series_clause}
                ORDER BY index_series ASC, index_name ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_market_index_daily_snapshot(row) for row in rows]

    def latest_krx_snapshot_date(self) -> date | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT MAX(business_date) AS business_date
                FROM (
                    SELECT business_date FROM stock_market_daily
                    UNION ALL
                    SELECT business_date FROM etf_daily_snapshots
                    UNION ALL
                    SELECT business_date FROM market_index_daily
                )
                """
            ).fetchone()
        return date.fromisoformat(row["business_date"]) if row and row["business_date"] else None

    def list_recent_krx_snapshot_dates(self, *, on_or_before: date, limit: int = 5) -> list[date]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT business_date
                FROM (
                    SELECT business_date FROM stock_market_daily WHERE business_date <= ? GROUP BY business_date
                    UNION
                    SELECT business_date FROM etf_daily_snapshots WHERE business_date <= ? GROUP BY business_date
                    UNION
                    SELECT business_date FROM market_index_daily WHERE business_date <= ? GROUP BY business_date
                )
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (
                    on_or_before.isoformat(),
                    on_or_before.isoformat(),
                    on_or_before.isoformat(),
                    limit,
                ),
            ).fetchall()
        return [date.fromisoformat(row["business_date"]) for row in rows]

    def list_recent_investor_flow_dates(
        self,
        *,
        on_or_before: date,
        source: str = "krx_data_market",
        limit: int = 5,
    ) -> list[date]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT business_date
                FROM (
                    SELECT business_date FROM stock_investor_flow_daily
                    WHERE business_date <= ? AND source = ?
                    UNION
                    SELECT business_date FROM market_investor_flow_daily
                    WHERE business_date <= ? AND source = ?
                    UNION
                    SELECT business_date FROM investor_net_buy_top_daily
                    WHERE business_date <= ? AND source = ?
                )
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (
                    on_or_before.isoformat(),
                    source,
                    on_or_before.isoformat(),
                    source,
                    on_or_before.isoformat(),
                    source,
                    limit,
                ),
            ).fetchall()
        return [date.fromisoformat(row["business_date"]) for row in rows]

    def list_recent_market_investor_flow_dates(
        self,
        *,
        on_or_before: date,
        source: str = "krx_data_market",
        limit: int = 5,
    ) -> list[date]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT business_date
                FROM market_investor_flow_daily
                WHERE business_date <= ? AND source = ?
                GROUP BY business_date
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (on_or_before.isoformat(), source, limit),
            ).fetchall()
        return [date.fromisoformat(row["business_date"]) for row in rows]

    def count_krx_snapshot_rows_for_date(self, business_date: date) -> dict[str, int]:
        target = business_date.isoformat()
        with self.connect() as connection:
            return {
                "etf-daily": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM etf_daily_snapshots WHERE business_date = ?",
                        (target,),
                    ).fetchone()[0]
                ),
                "stock-kospi-daily": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM stock_market_daily
                        WHERE business_date = ?
                          AND market = 'KOSPI'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "stock-kosdaq-daily": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM stock_market_daily
                        WHERE business_date = ?
                          AND market = 'KOSDAQ'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "stock-kospi-basic": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM krx_stock_metadata
                        WHERE business_date = ?
                          AND market = 'KOSPI'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "stock-kosdaq-basic": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM krx_stock_metadata
                        WHERE business_date = ?
                          AND market = 'KOSDAQ'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "index-krx-daily": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM market_index_daily
                        WHERE business_date = ?
                          AND index_series = 'KRX'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "index-kospi-daily": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM market_index_daily
                        WHERE business_date = ?
                          AND index_series = 'KOSPI'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
                "index-kosdaq-daily": int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM market_index_daily
                        WHERE business_date = ?
                          AND index_series = 'KOSDAQ'
                        """,
                        (target,),
                    ).fetchone()[0]
                ),
            }

    def count_krx_snapshots_before(self, cutoff_date: date) -> dict[str, int]:
        cutoff = cutoff_date.isoformat()
        with self.connect() as connection:
            return {
                "stock_market_daily": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM stock_market_daily WHERE business_date < ?",
                        (cutoff,),
                    ).fetchone()[0]
                ),
                "etf_daily_snapshots": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM etf_daily_snapshots WHERE business_date < ?",
                        (cutoff,),
                    ).fetchone()[0]
                ),
                "market_index_daily": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM market_index_daily WHERE business_date < ?",
                        (cutoff,),
                    ).fetchone()[0]
                ),
            }

    def delete_krx_snapshots_before(self, cutoff_date: date) -> dict[str, int]:
        cutoff = cutoff_date.isoformat()
        with self.connect() as connection:
            with connection:
                stock_count = connection.execute(
                    "DELETE FROM stock_market_daily WHERE business_date < ?",
                    (cutoff,),
                ).rowcount
                etf_count = connection.execute(
                    "DELETE FROM etf_daily_snapshots WHERE business_date < ?",
                    (cutoff,),
                ).rowcount
                index_count = connection.execute(
                    "DELETE FROM market_index_daily WHERE business_date < ?",
                    (cutoff,),
                ).rowcount
        return {
            "stock_market_daily": int(stock_count),
            "etf_daily_snapshots": int(etf_count),
            "market_index_daily": int(index_count),
        }

    def list_recent_deliveries(self, *, limit: int = 10) -> list[DeliveryLog]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT business_date, channel, status, delivered_at, message_id, detail
                FROM delivery_log
                ORDER BY delivered_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            DeliveryLog(
                business_date=date.fromisoformat(row["business_date"]),
                channel=row["channel"],
                status=row["status"],
                delivered_at=datetime.fromisoformat(row["delivered_at"]),
                message_id=row["message_id"],
                detail=row["detail"],
            )
            for row in rows
        ]

    def count_reports_by_business_date(self, *, limit: int = 5) -> list[tuple[date, int]]:
        return self._count_by_business_date("reports", limit=limit)

    def count_summaries_by_business_date(self, *, limit: int = 5) -> list[tuple[date, int]]:
        return self._count_by_business_date("daily_stock_summaries", limit=limit)

    def count_pending_intraday_alert_batches(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM intraday_alert_batches WHERE status IN ('pending', 'failed')"
            ).fetchone()
        return int(row["count"])

    def list_pending_intraday_alert_batches(self) -> list[IntradayAlertBatch]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    batch_id,
                    business_date,
                    created_at,
                    status,
                    last_attempt_at,
                    sent_at,
                    message_id,
                    error_detail
                FROM intraday_alert_batches
                WHERE status IN ('pending', 'failed')
                ORDER BY created_at ASC, batch_id ASC
                """
            ).fetchall()
        return [self._row_to_intraday_batch(row) for row in rows]

    def list_reports_for_intraday_batch(self, batch_id: str) -> list[Report]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    r.stock_name,
                    r.stock_code,
                    r.title,
                    r.broker_name,
                    r.published_at,
                    r.business_date,
                    r.target_price_raw,
                    r.target_price_value,
                    r.opinion_raw,
                    r.opinion_normalized,
                    r.collected_at,
                    r.source_url,
                    r.source_id,
                    r.identity_key
                FROM intraday_alert_batch_reports abr
                JOIN reports r ON r.identity_key = abr.report_identity_key
                WHERE abr.batch_id = ?
                ORDER BY r.stock_name ASC, r.broker_name ASC, r.title ASC
                """,
                (batch_id,),
            ).fetchall()
        return [self._row_to_report(row) for row in rows]

    def list_intraday_alert_batch_summaries(self, business_date: date) -> list[IntradayAlertBatchSummary]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    b.business_date,
                    b.created_at,
                    b.status,
                    COUNT(abr.report_identity_key) AS report_count,
                    COUNT(
                        DISTINCT COALESCE(NULLIF(TRIM(r.stock_code), ''), r.stock_name)
                    ) AS stock_count
                FROM intraday_alert_batches b
                LEFT JOIN intraday_alert_batch_reports abr ON abr.batch_id = b.batch_id
                LEFT JOIN reports r ON r.identity_key = abr.report_identity_key
                WHERE b.business_date = ?
                GROUP BY b.batch_id, b.business_date, b.created_at, b.status
                ORDER BY b.created_at ASC, b.batch_id ASC
                """,
                (business_date.isoformat(),),
            ).fetchall()
        return [
            IntradayAlertBatchSummary(
                business_date=date.fromisoformat(row["business_date"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                status=row["status"],
                report_count=int(row["report_count"]),
                stock_count=int(row["stock_count"]),
            )
            for row in rows
        ]

    def mark_intraday_alert_batch_sent(
        self,
        batch_id: str,
        *,
        sent_at: datetime,
        message_id: str,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE intraday_alert_batches
                    SET status = 'sent',
                        last_attempt_at = ?,
                        sent_at = ?,
                        message_id = ?,
                        error_detail = NULL
                    WHERE batch_id = ?
                    """,
                    (
                        sent_at.isoformat(),
                        sent_at.isoformat(),
                        message_id,
                        batch_id,
                    ),
                )

    def mark_intraday_alert_batches_sent(
        self,
        batch_ids: tuple[str, ...],
        *,
        sent_at: datetime,
        message_id: str,
    ) -> None:
        if not batch_ids:
            return
        placeholders = ", ".join("?" for _ in batch_ids)
        with self.connect() as connection:
            with connection:
                connection.execute(
                    f"""
                    UPDATE intraday_alert_batches
                    SET status = 'sent',
                        last_attempt_at = ?,
                        sent_at = ?,
                        message_id = ?,
                        error_detail = NULL
                    WHERE batch_id IN ({placeholders})
                    """,
                    (
                        sent_at.isoformat(),
                        sent_at.isoformat(),
                        message_id,
                        *batch_ids,
                    ),
                )

    def mark_intraday_alert_batch_failed(
        self,
        batch_id: str,
        *,
        attempted_at: datetime,
        error_detail: str,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE intraday_alert_batches
                    SET status = 'failed',
                        last_attempt_at = ?,
                        error_detail = ?
                    WHERE batch_id = ?
                    """,
                    (
                        attempted_at.isoformat(),
                        error_detail,
                        batch_id,
                    ),
                )

    def has_successful_delivery(self, business_date: date, channel: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM delivery_log
                WHERE business_date = ?
                  AND channel = ?
                  AND status = 'sent'
                LIMIT 1
                """,
                (business_date.isoformat(), channel),
            ).fetchone()
        return row is not None

    @staticmethod
    def _encode_json_tuple(values: tuple[str, ...]) -> str:
        return json.dumps(list(values), ensure_ascii=False)

    @staticmethod
    def _decode_json_tuple(value: str) -> tuple[str, ...]:
        parsed = json.loads(value or "[]")
        return tuple(str(item) for item in parsed)

    @staticmethod
    def _row_to_news_intelligence_run(row: sqlite3.Row) -> NewsIntelligenceRun:
        return NewsIntelligenceRun(
            run_id=row["run_id"],
            target_date=date.fromisoformat(row["target_date"]),
            stock_name=row["stock_name"],
            stock_code=row["stock_code"],
            aliases=StockMonitorRepository._decode_json_tuple(row["aliases_json"]),
            source_mode=row["source_mode"],
            page_limit=int(row["page_limit"]),
            full_day_complete=bool(row["full_day_complete"]),
            live_fetch=bool(row["live_fetch"]),
            parsed_count=int(row["parsed_count"]),
            deduped_count=int(row["deduped_count"]),
            matched_count=int(row["matched_count"]),
            operator_summary_snapshot=row["operator_summary_snapshot"],
            warnings=StockMonitorRepository._decode_json_tuple(row["warnings_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_report_linked_news_evidence(row: sqlite3.Row) -> ReportLinkedNewsEvidenceRecord:
        return ReportLinkedNewsEvidenceRecord(
            run_id=row["run_id"],
            evidence_key=row["evidence_key"],
            target_date=date.fromisoformat(row["target_date"]),
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            related_report_count=int(row["related_report_count"]),
            related_report_source_ids=StockMonitorRepository._decode_json_tuple(
                row["related_report_source_ids_json"]
            ),
            daily_summary_presence=bool(row["daily_summary_presence"]),
            candidate_priority_presence=bool(row["candidate_priority_presence"]),
            candidate_observation_priority=row["candidate_observation_priority"],
            krx_reference_presence=bool(row["krx_reference_presence"]),
            krx_reference_date=date.fromisoformat(row["krx_reference_date"]) if row["krx_reference_date"] else None,
            krx_turnover=row["krx_turnover"],
            investor_flow_presence=bool(row["investor_flow_presence"]),
            source_lane=row["source_lane"],
            title=row["title"],
            summary=row["summary"],
            source=row["source"],
            published_at=datetime.fromisoformat(row["published_at"]),
            url=row["url"],
            matched_alias=row["matched_alias"],
            match_reason=row["match_reason"],
            match_scope=row["match_scope"],
            relevance=row["relevance"],
            relevance_reason=row["relevance_reason"],
            sentiment=row["sentiment"],
            sentiment_score=int(row["sentiment_score"]),
            event_types=StockMonitorRepository._decode_json_tuple(row["event_types_json"]),
            stock_impact=row["stock_impact"],
            impact_explanation=row["impact_explanation"],
            evidence_case=row["evidence_case"],
            operator_recommendation=row["operator_recommendation"],
            recommendation_reason=row["recommendation_reason"],
            operator_summary_snapshot=row["operator_summary_snapshot"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_toss_priority_quote_baseline(row: sqlite3.Row) -> TossPriorityQuoteBaseline:
        return TossPriorityQuoteBaseline(
            business_date=date.fromisoformat(row["business_date"]),
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            baseline_time=row["baseline_time"],
            last_price=int(row["last_price"]) if row["last_price"] is not None else None,
            currency=row["currency"],
            source=row["source"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
        )

    @staticmethod
    def _row_to_toss_market_context_snapshot(row: sqlite3.Row) -> TossMarketContextSnapshot:
        return TossMarketContextSnapshot(
            business_date=date.fromisoformat(row["business_date"]),
            observed_at=datetime.fromisoformat(row["observed_at"]),
            rank=int(row["rank"]),
            stock_code=row["stock_code"],
            trading_amount=int(row["trading_amount"]) if row["trading_amount"] is not None else None,
            trading_volume=int(row["trading_volume"]) if row["trading_volume"] is not None else None,
            source=row["source"],
            checked_at=datetime.fromisoformat(row["checked_at"]),
        )

    @staticmethod
    def _row_to_report(row: sqlite3.Row) -> Report:
        return Report(
            stock_name=row["stock_name"],
            stock_code=row["stock_code"],
            title=row["title"],
            broker_name=row["broker_name"],
            published_at=datetime.fromisoformat(row["published_at"]),
            business_date=date.fromisoformat(row["business_date"]),
            target_price_raw=row["target_price_raw"],
            target_price_value=row["target_price_value"],
            opinion_raw=row["opinion_raw"],
            opinion_normalized=row["opinion_normalized"],
            collected_at=datetime.fromisoformat(row["collected_at"]),
            source_url=row["source_url"],
            source_id=row["source_id"],
            identity_key=row["identity_key"],
        )

    @staticmethod
    def _row_to_daily_summary(row: sqlite3.Row) -> DailyStockSummary:
        return DailyStockSummary(
            business_date=date.fromisoformat(row["business_date"]),
            stock_name=row["stock_name"],
            stock_code=row["stock_code"],
            mention_count=row["mention_count"],
            broker_display=row["broker_display"],
            target_price_min=row["target_price_min"],
            target_price_max=row["target_price_max"],
            dominant_opinion=row["dominant_opinion"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
        )

    @staticmethod
    def _row_to_intraday_batch(row: sqlite3.Row) -> IntradayAlertBatch:
        return IntradayAlertBatch(
            batch_id=row["batch_id"],
            business_date=date.fromisoformat(row["business_date"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=row["status"],
            last_attempt_at=datetime.fromisoformat(row["last_attempt_at"]) if row["last_attempt_at"] else None,
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
            message_id=row["message_id"],
            error_detail=row["error_detail"],
        )

    @staticmethod
    def _row_to_operator_control(row: sqlite3.Row) -> OperatorControl:
        return OperatorControl(
            control_key=row["control_key"],
            control_value=row["control_value"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            detail=row["detail"],
        )

    @staticmethod
    def _row_to_daily_summary_delivery_run(row: sqlite3.Row | dict) -> DailySummaryDeliveryRun:
        return DailySummaryDeliveryRun(
            run_id=row["run_id"],
            business_date=date.fromisoformat(row["business_date"]),
            channel=row["channel"],
            status=row["status"],
            summary_signature=row["summary_signature"],
            total_fragments=int(row["total_fragments"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            last_error=row["last_error"],
        )

    @staticmethod
    def _row_to_daily_summary_delivery_fragment(row: sqlite3.Row) -> DailySummaryDeliveryFragment:
        return DailySummaryDeliveryFragment(
            run_id=row["run_id"],
            fragment_index=int(row["fragment_index"]),
            status=row["status"],
            message_text=row["message_text"],
            message_hash=row["message_hash"],
            message_id=row["message_id"],
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
            last_error=row["last_error"],
        )

    @staticmethod
    def _row_to_worker_state(row: sqlite3.Row) -> WorkerState:
        return WorkerState(
            worker_name=row["worker_name"],
            status=row["status"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_started_at=datetime.fromisoformat(row["last_started_at"]) if row["last_started_at"] else None,
            last_success_at=datetime.fromisoformat(row["last_success_at"]) if row["last_success_at"] else None,
            last_error_at=datetime.fromisoformat(row["last_error_at"]) if row["last_error_at"] else None,
            last_error=row["last_error"],
            interval_seconds=row["interval_seconds"],
            end_time=row["end_time"],
        )

    @staticmethod
    def _row_to_app_setting(row: sqlite3.Row) -> AppSetting:
        return AppSetting(
            setting_key=row["setting_key"],
            setting_value=row["setting_value"],
            value_type=row["value_type"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            updated_by=row["updated_by"],
            detail=row["detail"],
            restart_required=bool(row["restart_required"]),
        )

    @staticmethod
    def _row_to_admin_audit_log(row: sqlite3.Row) -> AdminAuditLog:
        return AdminAuditLog(
            id=int(row["id"]),
            event_time=datetime.fromisoformat(row["event_time"]),
            actor=row["actor"],
            action=row["action"],
            setting_key=row["setting_key"],
            old_value=row["old_value"],
            new_value=row["new_value"],
            status=row["status"],
            detail=row["detail"],
        )

    @staticmethod
    def _row_to_stock_metadata(row: sqlite3.Row) -> StockMetadata:
        return StockMetadata(
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            sector_code=row["sector_code"],
            sector_name=row["sector_name"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_stock_theme_membership(row: sqlite3.Row) -> StockThemeMembership:
        return StockThemeMembership(
            theme_code=row["theme_code"],
            theme_name=row["theme_name"],
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_category_catalog_item(row: sqlite3.Row) -> CategoryCatalogItem:
        return CategoryCatalogItem(
            category_type=row["category_type"],
            category_key=row["category_key"],
            display_name=row["display_name"],
            source=row["source"],
            enabled=bool(row["enabled"]),
            group_name=row["group_name"],
            priority=int(row["priority"]),
            note=row["note"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_stock_market_daily_snapshot(row: sqlite3.Row) -> StockMarketDailySnapshot:
        return StockMarketDailySnapshot(
            business_date=date.fromisoformat(row["business_date"]),
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            market=row["market"],
            section_name=row["section_name"],
            close_price=row["close_price"],
            change_amount=row["change_amount"],
            change_percent=row["change_percent"],
            open_price=row["open_price"],
            high_price=row["high_price"],
            low_price=row["low_price"],
            volume=row["volume"],
            turnover=row["turnover"],
            market_cap=row["market_cap"],
            listed_shares=row["listed_shares"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_stock_investor_flow_daily(row: sqlite3.Row) -> StockInvestorFlowDaily:
        return StockInvestorFlowDaily(
            business_date=date.fromisoformat(row["business_date"]),
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            market=row["market"],
            investor_type=row["investor_type"],
            sell_volume=row["sell_volume"],
            buy_volume=row["buy_volume"],
            net_buy_volume=row["net_buy_volume"],
            sell_amount=row["sell_amount"],
            buy_amount=row["buy_amount"],
            net_buy_amount=row["net_buy_amount"],
            volume_unit=row["volume_unit"],
            amount_unit=row["amount_unit"],
            candidate_score=row["candidate_score"],
            candidate_reasons=row["candidate_reasons"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_market_investor_flow_daily(row: sqlite3.Row) -> MarketInvestorFlowDaily:
        return MarketInvestorFlowDaily(
            business_date=date.fromisoformat(row["business_date"]),
            market=row["market"],
            investor_type=row["investor_type"],
            sell_volume=row["sell_volume"],
            buy_volume=row["buy_volume"],
            net_buy_volume=row["net_buy_volume"],
            sell_amount=row["sell_amount"],
            buy_amount=row["buy_amount"],
            net_buy_amount=row["net_buy_amount"],
            volume_unit=row["volume_unit"],
            amount_unit=row["amount_unit"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_investor_net_buy_top_daily(row: sqlite3.Row) -> InvestorNetBuyTopDaily:
        return InvestorNetBuyTopDaily(
            business_date=date.fromisoformat(row["business_date"]),
            market=row["market"],
            investor_type=row["investor_type"],
            rank=row["rank"],
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            net_buy_volume=row["net_buy_volume"],
            net_buy_amount=row["net_buy_amount"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_etf_daily_snapshot(row: sqlite3.Row) -> EtfDailySnapshot:
        return EtfDailySnapshot(
            business_date=date.fromisoformat(row["business_date"]),
            etf_code=row["etf_code"],
            etf_name=row["etf_name"],
            close_price=row["close_price"],
            change_amount=row["change_amount"],
            change_percent=row["change_percent"],
            nav=row["nav"],
            open_price=row["open_price"],
            high_price=row["high_price"],
            low_price=row["low_price"],
            volume=row["volume"],
            turnover=row["turnover"],
            market_cap=row["market_cap"],
            net_assets_total=row["net_assets_total"],
            listed_shares=row["listed_shares"],
            underlying_index_name=row["underlying_index_name"],
            underlying_index_close=row["underlying_index_close"],
            underlying_index_change_amount=row["underlying_index_change_amount"],
            underlying_index_change_percent=row["underlying_index_change_percent"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _row_to_market_index_daily_snapshot(row: sqlite3.Row) -> MarketIndexDailySnapshot:
        return MarketIndexDailySnapshot(
            business_date=date.fromisoformat(row["business_date"]),
            index_series=row["index_series"],
            index_class=row["index_class"],
            index_name=row["index_name"],
            close_index=row["close_index"],
            change_amount=row["change_amount"],
            change_percent=row["change_percent"],
            open_index=row["open_index"],
            high_index=row["high_index"],
            low_index=row["low_index"],
            volume=row["volume"],
            turnover=row["turnover"],
            market_cap=row["market_cap"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            source=row["source"],
        )

    @staticmethod
    def _create_intraday_alert_batch(
        connection: sqlite3.Connection,
        business_date: date,
        reports: list[Report],
    ) -> str:
        batch_id = uuid4().hex
        created_at = max(report.collected_at for report in reports).isoformat()
        connection.execute(
            """
            INSERT INTO intraday_alert_batches (
                batch_id,
                business_date,
                created_at,
                status
            ) VALUES (?, ?, ?, 'pending')
            """,
            (
                batch_id,
                business_date.isoformat(),
                created_at,
            ),
        )
        connection.executemany(
            """
            INSERT INTO intraday_alert_batch_reports (
                batch_id,
                report_identity_key
            ) VALUES (?, ?)
            """,
            [
                (
                    batch_id,
                    report.identity_key,
                )
                for report in reports
                if report.identity_key
            ],
        )
        return batch_id

    def _count_by_business_date(self, table_name: str, *, limit: int) -> list[tuple[date, int]]:
        if table_name not in {"reports", "daily_stock_summaries"}:
            raise ValueError(f"Unsupported table for business-date counts: {table_name}")
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT business_date, COUNT(*) AS count
                FROM {table_name}
                GROUP BY business_date
                ORDER BY business_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(date.fromisoformat(row["business_date"]), int(row["count"])) for row in rows]

    @staticmethod
    def _report_exists(connection: sqlite3.Connection, report: Report) -> bool:
        if report.source_id:
            by_source_id = connection.execute(
                "SELECT 1 FROM reports WHERE source_id = ? LIMIT 1",
                (report.source_id,),
            ).fetchone()
            if by_source_id is not None:
                return True

        by_legacy_key = connection.execute(
            """
            SELECT 1
            FROM reports
            WHERE stock_name = ?
              AND title = ?
              AND broker_name = ?
              AND published_at = ?
            LIMIT 1
            """,
            (
                report.stock_name,
                report.title,
                report.broker_name,
                report.published_at.isoformat(),
            ),
        ).fetchone()
        return by_legacy_key is not None


def _run_suppressed_date_key(target: date) -> str:
    return f"run_suppressed_date:{target.isoformat()}"


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
