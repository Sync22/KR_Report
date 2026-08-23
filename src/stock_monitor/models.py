from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class Opinion(str, Enum):
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    NA = "N/A"


_OPINION_ALIASES = {
    "buy": Opinion.BUY.value,
    "strongbuy": Opinion.BUY.value,
    "outperform": Opinion.BUY.value,
    "overweight": Opinion.BUY.value,
    "tradingbuy": Opinion.BUY.value,
    "매수": Opinion.BUY.value,
    "hold": Opinion.NEUTRAL.value,
    "neutral": Opinion.NEUTRAL.value,
    "marketperform": Opinion.NEUTRAL.value,
    "보유": Opinion.NEUTRAL.value,
    "중립": Opinion.NEUTRAL.value,
    "sell": Opinion.SELL.value,
    "reduce": Opinion.SELL.value,
    "underperform": Opinion.SELL.value,
    "비중축소": Opinion.SELL.value,
    "매도": Opinion.SELL.value,
}

OPINION_PRIORITY = {
    Opinion.BUY.value: 3,
    Opinion.NEUTRAL.value: 2,
    Opinion.SELL.value: 1,
    Opinion.NA.value: 0,
}


def collapse_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_opinion(raw: str | None) -> str:
    text = collapse_whitespace(raw)
    if not text:
        return Opinion.NA.value
    key = re.sub(r"[\s\-_/]+", "", text).lower()
    return _OPINION_ALIASES.get(key, Opinion.NA.value)


def parse_target_price(raw: str | None) -> int | None:
    text = collapse_whitespace(raw)
    if not text:
        return None
    man_match = re.search(r"(\d+(?:\.\d+)?)\s*만", text)
    if man_match:
        return int(float(man_match.group(1)) * 10_000)
    digits = re.findall(r"\d[\d,]*", text)
    if not digits:
        return None
    return int(digits[0].replace(",", ""))


def build_report_identity(
    stock_name: str,
    title: str,
    broker_name: str,
    published_at: datetime,
    source_id: str | None = None,
) -> str:
    normalized_source_id = collapse_whitespace(source_id)
    if normalized_source_id:
        joined = "||".join(["naver_research", normalized_source_id])
    else:
        joined = "||".join(
            [
                collapse_whitespace(stock_name),
                collapse_whitespace(title),
                collapse_whitespace(broker_name),
                published_at.isoformat(),
            ]
        )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Report:
    stock_name: str
    title: str
    broker_name: str
    published_at: datetime
    collected_at: datetime
    business_date: date
    stock_code: str | None = None
    target_price_raw: str | None = None
    target_price_value: int | None = None
    opinion_raw: str | None = None
    opinion_normalized: str = Opinion.NA.value
    source_url: str | None = None
    source_id: str | None = None
    identity_key: str | None = None

    def with_identity(self) -> "Report":
        identity_key = self.identity_key or build_report_identity(
            self.stock_name,
            self.title,
            self.broker_name,
            self.published_at,
            self.source_id,
        )
        return Report(
            stock_name=self.stock_name,
            title=self.title,
            broker_name=self.broker_name,
            published_at=self.published_at,
            collected_at=self.collected_at,
            business_date=self.business_date,
            stock_code=self.stock_code,
            target_price_raw=self.target_price_raw,
            target_price_value=self.target_price_value,
            opinion_raw=self.opinion_raw,
            opinion_normalized=self.opinion_normalized,
            source_url=self.source_url,
            source_id=self.source_id,
            identity_key=identity_key,
        )


@dataclass(frozen=True)
class DailyStockSummary:
    business_date: date
    stock_name: str
    stock_code: str | None
    mention_count: int
    broker_display: str
    target_price_min: int | None
    target_price_max: int | None
    dominant_opinion: str
    generated_at: datetime


@dataclass(frozen=True)
class DeliveryLog:
    business_date: date
    channel: str
    status: str
    delivered_at: datetime
    message_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class DailySummaryDeliveryRun:
    run_id: str
    business_date: date
    channel: str
    status: str
    summary_signature: str
    total_fragments: int
    started_at: datetime
    finished_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class DailySummaryDeliveryFragment:
    run_id: str
    fragment_index: int
    status: str
    message_text: str
    message_hash: str
    message_id: str | None = None
    sent_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class IntradayAlertBatch:
    batch_id: str
    business_date: date
    created_at: datetime
    status: str
    last_attempt_at: datetime | None = None
    sent_at: datetime | None = None
    message_id: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class IntradayAlertBatchSummary:
    business_date: date
    created_at: datetime
    status: str
    report_count: int
    stock_count: int


@dataclass(frozen=True)
class OperationEvent:
    event_time: datetime
    component: str
    event_type: str
    status: str
    business_date: date | None = None
    detail: str | None = None


@dataclass(frozen=True)
class OperatorControl:
    control_key: str
    control_value: str
    updated_at: datetime
    detail: str | None = None


@dataclass(frozen=True)
class WorkerState:
    worker_name: str
    status: str
    updated_at: datetime
    last_started_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    interval_seconds: int | None = None
    end_time: str | None = None


@dataclass(frozen=True)
class AppSetting:
    setting_key: str
    setting_value: str
    value_type: str
    updated_at: datetime
    updated_by: str
    detail: str | None = None
    restart_required: bool = False


@dataclass(frozen=True)
class AdminAuditLog:
    event_time: datetime
    actor: str
    action: str
    status: str
    setting_key: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    detail: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class CategoryCatalogItem:
    category_type: str
    category_key: str
    display_name: str
    source: str
    enabled: bool
    updated_at: datetime
    group_name: str | None = None
    priority: int = 100
    note: str | None = None


@dataclass(frozen=True)
class CategoryMembershipSnapshot:
    snapshot_date: date
    category_type: str
    category_key: str
    display_name: str
    stock_code: str
    stock_name: str | None
    fetched_at: datetime
    source: str


@dataclass(frozen=True)
class CategoryDailyRollup:
    business_date: date
    category_type: str
    category_key: str
    display_name: str
    stock_count: int
    report_count: int
    snapshot_date: date | None = None
    mapping_source: str = "latest_mapping_fallback"


@dataclass(frozen=True)
class StockMetadata:
    stock_code: str
    stock_name: str | None
    sector_code: str | None
    sector_name: str | None
    updated_at: datetime
    source: str = "naver_quote"


@dataclass(frozen=True)
class SectorDailyRollup:
    business_date: date
    sector_name: str
    sector_code: str | None
    stock_count: int
    report_count: int


@dataclass(frozen=True)
class StockThemeMembership:
    theme_code: str
    theme_name: str
    stock_code: str
    stock_name: str | None
    updated_at: datetime
    source: str = "naver_theme"


@dataclass(frozen=True)
class ThemeDailyRollup:
    business_date: date
    theme_code: str
    theme_name: str
    stock_count: int
    report_count: int


@dataclass(frozen=True)
class CategoryTrendPoint:
    business_date: date
    stock_count: int
    report_count: int


@dataclass(frozen=True)
class StockMarketDailySnapshot:
    business_date: date
    stock_code: str
    stock_name: str
    market: str
    fetched_at: datetime
    source: str = "krx"
    section_name: str | None = None
    close_price: int | None = None
    change_amount: int | None = None
    change_percent: float | None = None
    open_price: int | None = None
    high_price: int | None = None
    low_price: int | None = None
    volume: int | None = None
    turnover: int | None = None
    market_cap: int | None = None
    listed_shares: int | None = None


@dataclass(frozen=True)
class StockInvestorFlowDaily:
    business_date: date
    stock_code: str
    stock_name: str | None
    investor_type: str
    fetched_at: datetime
    market: str | None = None
    sell_volume: int | None = None
    buy_volume: int | None = None
    net_buy_volume: int | None = None
    sell_amount: int | None = None
    buy_amount: int | None = None
    net_buy_amount: int | None = None
    volume_unit: str | None = None
    amount_unit: str | None = None
    candidate_score: int | None = None
    candidate_reasons: str | None = None
    source: str = "krx_data_market"


@dataclass(frozen=True)
class MarketInvestorFlowDaily:
    business_date: date
    market: str
    investor_type: str
    fetched_at: datetime
    sell_volume: int | None = None
    buy_volume: int | None = None
    net_buy_volume: int | None = None
    sell_amount: int | None = None
    buy_amount: int | None = None
    net_buy_amount: int | None = None
    volume_unit: str | None = None
    amount_unit: str | None = None
    source: str = "krx_data_market"


@dataclass(frozen=True)
class InvestorNetBuyTopDaily:
    business_date: date
    market: str
    investor_type: str
    rank: int
    stock_code: str
    stock_name: str
    fetched_at: datetime
    net_buy_volume: int | None = None
    net_buy_amount: int | None = None
    source: str = "krx_data_market"


@dataclass(frozen=True)
class EtfDailySnapshot:
    business_date: date
    etf_code: str
    etf_name: str
    fetched_at: datetime
    source: str = "krx"
    close_price: int | None = None
    change_amount: int | None = None
    change_percent: float | None = None
    nav: float | None = None
    open_price: int | None = None
    high_price: int | None = None
    low_price: int | None = None
    volume: int | None = None
    turnover: int | None = None
    market_cap: int | None = None
    net_assets_total: int | None = None
    listed_shares: int | None = None
    underlying_index_name: str | None = None
    underlying_index_close: float | None = None
    underlying_index_change_amount: float | None = None
    underlying_index_change_percent: float | None = None


@dataclass(frozen=True)
class KrxStockMetadataSnapshot:
    business_date: date
    standard_code: str
    stock_code: str
    stock_name: str
    market: str
    fetched_at: datetime
    source: str = "krx"
    stock_short_name: str | None = None
    stock_english_name: str | None = None
    listed_date: date | None = None
    security_group: str | None = None
    section_name: str | None = None
    stock_certificate_type: str | None = None
    par_value: str | None = None
    listed_shares: int | None = None


@dataclass(frozen=True)
class MarketIndexDailySnapshot:
    business_date: date
    index_series: str
    index_class: str
    index_name: str
    fetched_at: datetime
    source: str = "krx"
    close_index: float | None = None
    change_amount: float | None = None
    change_percent: float | None = None
    open_index: float | None = None
    high_index: float | None = None
    low_index: float | None = None
    volume: int | None = None
    turnover: int | None = None
    market_cap: int | None = None


@dataclass(frozen=True)
class NewsIntelligenceRun:
    run_id: str
    target_date: date
    stock_name: str
    stock_code: str | None
    aliases: tuple[str, ...]
    source_mode: str
    page_limit: int
    full_day_complete: bool
    live_fetch: bool
    parsed_count: int
    deduped_count: int
    matched_count: int
    operator_summary_snapshot: str
    warnings: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True)
class ReportLinkedNewsEvidenceRecord:
    run_id: str
    evidence_key: str
    target_date: date
    stock_code: str | None
    stock_name: str
    related_report_count: int
    related_report_source_ids: tuple[str, ...]
    daily_summary_presence: bool
    candidate_priority_presence: bool
    candidate_observation_priority: str | None
    krx_reference_presence: bool
    krx_reference_date: date | None
    krx_turnover: int | None
    investor_flow_presence: bool
    source_lane: str
    title: str
    summary: str
    source: str
    published_at: datetime
    url: str
    matched_alias: str
    match_reason: str
    match_scope: str
    relevance: str
    relevance_reason: str
    sentiment: str
    sentiment_score: int
    event_types: tuple[str, ...]
    stock_impact: str
    impact_explanation: str
    evidence_case: str
    operator_recommendation: str
    recommendation_reason: str
    operator_summary_snapshot: str
    created_at: datetime
    canonical_url: str = ""
    lineage_type: str = "unknown"
    lineage_reason: str = "legacy_row_unverified"


@dataclass(frozen=True)
class TossPriorityQuoteBaseline:
    business_date: date
    stock_code: str
    stock_name: str | None
    baseline_time: str
    last_price: int | None
    currency: str | None
    source: str
    fetched_at: datetime


@dataclass(frozen=True)
class TossMarketContextSnapshot:
    business_date: date
    observed_at: datetime
    rank: int
    stock_code: str
    trading_amount: int | None
    trading_volume: int | None
    source: str
    checked_at: datetime


@dataclass(frozen=True)
class StockResearchEntry:
    stock_name: str
    stock_code: str
    broker_name: str
    title: str
    write_date: date
    target_price_value: int | None
    opinion_normalized: str
    source_url: str | None = None
    source_id: str | None = None
