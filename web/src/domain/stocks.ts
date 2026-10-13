import { isBusinessDate } from "./daily.ts";

export type StockSearchItem = {
  stock_code: string;
  stock_name: string;
  market: string | null;
  market_source: "stored_toss_stock_universe" | "stored_krx_stock_metadata" | null;
  market_reference_date: string | null;
  has_selected_date_report: boolean;
  has_selected_date_toss: boolean;
  has_news_observation: boolean;
  display_status: string;
};

export type StockSearchSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  source: "stored_stock_universe";
  stock_universe_reference_date: string | null;
  live_fetch: false;
  available: boolean;
  query: string;
  items: StockSearchItem[];
  empty_state: string | null;
};

export type StockReport = {
  stock_name: string;
  stock_code: string;
  title: string;
  report_title?: string;
  title_display: string;
  broker_name: string;
  published_at: string;
  target_price_value: number | null;
  target_price_display: string;
  opinion_normalized: string | null;
  opinion_display: string;
  source_url: string | null;
};

type NullableNumber = number | null;

type StockValueContext = {
  report_reference_date: string | null;
  toss_reference_date: string | null;
  current_price_reference_time: string | null;
  current_price_basis: string | null;
  turnover_reference_date: string | null;
  investor_flow_reference_date: string | null;
  news_collection_status: string;
  missing_labels: string[];
};

type StockTargetJourneyItem = {
  report_date: string;
  broker_name: string;
  target_price_value: number;
  target_price_display: string;
  revision_direction_label: string | null;
  status: "hit" | "in_progress" | "no_market_data";
  hit_date: string | null;
  hit_trading_days: number | null;
  current_attainment_percent: NullableNumber;
  max_attainment_percent: NullableNumber;
  observed_through: string | null;
};

type StockRelatedCategory = {
  category_type: string;
  category_label: string;
  category_display_name: string;
  public_category_id: string;
  display: string;
  etf_notice: string;
  related_etfs: { etf_code: string; etf_name: string; evidence_label: string }[];
};

type StockVolumeDay = {
  business_date: string;
  close_price: NullableNumber;
  change_percent: NullableNumber;
  volume: NullableNumber;
  volume_unit: string;
};

type StockInvestorFlowDay = {
  business_date: string;
  individual: NullableNumber;
  foreign: NullableNumber;
  institution: NullableNumber;
};

type StockNewsDigestItem = {
  date: string;
  stock_name: string;
  label: string;
  evidence_label: string;
  lineage_label: string;
};

export type StockDetailSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  stock_code: string;
  stock_name: string | null;
  has_selected_date_report: boolean;
  report_empty_state: string | null;
  market_reference: {
    business_date: string;
    market: string | null;
    close_price: number | null;
    change_percent: number | null;
    volume: number | null;
    turnover: number | null;
    fetched_at: string;
  } | null;
  value_context: StockValueContext;
  target_price_progress: {
    validation_available: boolean;
    hit_min_horizon_days: number | null;
    hit_max_horizon_days: number | null;
    validation_notice: string;
  };
  target_price_trail: {
    available: boolean;
    live_fetch: false;
    scoring: false;
    recommendation: false;
    business_date: string;
    stock_code: string;
    summary: string;
    current_price: NullableNumber;
    current_target_price: NullableNumber;
    attainment_percent: NullableNumber;
    notice: string;
  };
  target_journey: {
    available: boolean;
    live_fetch: false;
    scoring: false;
    recommendation: false;
    business_date: string;
    stock_code: string;
    price_basis: string;
    items: StockTargetJourneyItem[];
    notice: string;
  };
  related_context: {
    available: boolean;
    etf_source: string;
    live_fetch: false;
    scoring: false;
    recommendation: false;
    business_date: string;
    stock_code: string;
    categories: StockRelatedCategory[];
    notice: string;
  };
  news_observation_detail: {
    source: "stored_news_intelligence_observation";
    read_only: true;
    live_fetch: false;
    available: boolean;
    display_label: string;
    reason: string;
    top_title?: string | null;
    connection_label?: string;
    connection_reason?: string;
    direct_count?: number;
    caution_count?: number;
    market_context_count?: number;
    krx_reference_status?: string;
    missing_context?: string[];
    top_titles?: string[];
    news_digest?: StockNewsDigestItem[];
  };
  recent_volume_days: {
    available: boolean;
    source: string | null;
    live_fetch: false;
    business_date: string;
    reference_date: string | null;
    exact_date_available: boolean;
    items: StockVolumeDay[];
    notice: string;
  };
  investor_flow: {
    available: boolean;
    source: string | null;
    data_scope: "stored_toss_close_priority_flow";
    live_fetch: false;
    scoring: false;
    snapshot_date: string | null;
    notice: string;
  };
  investor_flow_tabs: {
    available: boolean;
    source: string | null;
    live_fetch: false;
    business_date: string;
    reference_date: string | null;
    exact_date_available: boolean;
    volume_unit: string;
    retail_foreign_institution: StockInvestorFlowDay[];
    notice: string;
  };
  reports: StockReport[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isNumberOrNull(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isDateOrNull(value: unknown): value is string | null {
  return value === null || isBusinessDate(value);
}

function isSafeStockCode(value: unknown): value is string {
  return typeof value === "string" && /^\d{6}$/.test(value);
}

export function isStockSearchSnapshot(value: unknown, expectedDate: string, expectedQuery: string): value is StockSearchSnapshot {
  if (!isRecord(value) || !Array.isArray(value.items)) return false;
  return (
    typeof value.now === "string" &&
    Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" &&
    value.timezone.length > 0 &&
    value.surface === "web-view" &&
    value.read_only === true &&
    value.business_date === expectedDate &&
    isBusinessDate(value.business_date) &&
    value.source === "stored_stock_universe" &&
    (value.stock_universe_reference_date === null || isBusinessDate(value.stock_universe_reference_date)) &&
    value.live_fetch === false &&
    typeof value.available === "boolean" &&
    value.query === expectedQuery.trim() &&
    (value.empty_state === null || typeof value.empty_state === "string") &&
    value.items.every(
      (item: unknown) =>
        isRecord(item) &&
        isSafeStockCode(item.stock_code) &&
        typeof item.stock_name === "string" &&
        (item.market === null || typeof item.market === "string") &&
        (item.market === null
          ? item.market_source === null && item.market_reference_date === null
          : (item.market_source === "stored_toss_stock_universe" || item.market_source === "stored_krx_stock_metadata") &&
            isBusinessDate(item.market_reference_date)) &&
        typeof item.has_selected_date_report === "boolean" &&
        typeof item.has_selected_date_toss === "boolean" &&
        typeof item.has_news_observation === "boolean" &&
        typeof item.display_status === "string",
    )
  );
}

function isStockReport(value: unknown, stockCode: string): value is StockReport {
  return (
    isRecord(value) &&
    typeof value.stock_name === "string" &&
    value.stock_code === stockCode &&
    typeof value.title === "string" &&
    (value.report_title === undefined || typeof value.report_title === "string") &&
    typeof value.title_display === "string" &&
    typeof value.broker_name === "string" &&
    typeof value.published_at === "string" &&
    Number.isFinite(Date.parse(value.published_at)) &&
    (value.target_price_value === null || (typeof value.target_price_value === "number" && Number.isInteger(value.target_price_value))) &&
    typeof value.target_price_display === "string" &&
    (value.opinion_normalized === null || typeof value.opinion_normalized === "string") &&
    typeof value.opinion_display === "string" &&
    (value.source_url === null || typeof value.source_url === "string")
  );
}

function isMarketReference(value: unknown, expectedDate: string): boolean {
  return (
    value === null ||
    (isRecord(value) &&
      value.business_date === expectedDate &&
      (value.market === null || typeof value.market === "string") &&
      isNumberOrNull(value.close_price) &&
      isNumberOrNull(value.change_percent) &&
      isNumberOrNull(value.volume) &&
      isNumberOrNull(value.turnover) &&
      typeof value.fetched_at === "string" &&
      Number.isFinite(Date.parse(value.fetched_at)))
  );
}

function isTargetJourneyItem(value: unknown): value is StockTargetJourneyItem {
  return (
    isRecord(value) &&
    isBusinessDate(value.report_date) &&
    typeof value.broker_name === "string" &&
    typeof value.target_price_value === "number" &&
    Number.isInteger(value.target_price_value) &&
    typeof value.target_price_display === "string" &&
    (value.revision_direction_label === null || typeof value.revision_direction_label === "string") &&
    ["hit", "in_progress", "no_market_data"].includes(String(value.status)) &&
    isDateOrNull(value.hit_date) &&
    (value.hit_trading_days === null || (typeof value.hit_trading_days === "number" && Number.isInteger(value.hit_trading_days))) &&
    isNumberOrNull(value.current_attainment_percent) &&
    isNumberOrNull(value.max_attainment_percent) &&
    isDateOrNull(value.observed_through)
  );
}

function isStockVolumeDay(value: unknown): value is StockVolumeDay {
  return (
    isRecord(value) &&
    isBusinessDate(value.business_date) &&
    isNumberOrNull(value.close_price) &&
    isNumberOrNull(value.change_percent) &&
    isNumberOrNull(value.volume) &&
    typeof value.volume_unit === "string"
  );
}

function isStockInvestorFlowDay(value: unknown): value is StockInvestorFlowDay {
  return (
    isRecord(value) &&
    isBusinessDate(value.business_date) &&
    isNumberOrNull(value.individual) &&
    isNumberOrNull(value.foreign) &&
    isNumberOrNull(value.institution)
  );
}

function isStockRelatedCategory(value: unknown): value is StockRelatedCategory {
  return (
    isRecord(value) &&
    (value.category_type === "sector" || value.category_type === "theme") &&
    typeof value.category_label === "string" &&
    typeof value.category_display_name === "string" &&
    typeof value.public_category_id === "string" &&
    typeof value.display === "string" &&
    typeof value.etf_notice === "string" &&
    Array.isArray(value.related_etfs) &&
    value.related_etfs.every(
      (etf: unknown) =>
        isRecord(etf) &&
        typeof etf.etf_code === "string" &&
        typeof etf.etf_name === "string" &&
        typeof etf.evidence_label === "string",
    )
  );
}

function isNewsDigestItem(value: unknown): value is StockNewsDigestItem {
  return (
    isRecord(value) &&
    isBusinessDate(value.date) &&
    typeof value.stock_name === "string" &&
    typeof value.label === "string" &&
    typeof value.evidence_label === "string" &&
    typeof value.lineage_label === "string"
  );
}

export function isStockDetailSnapshot(
  value: unknown,
  expectedDate: string,
  expectedStockCode: string,
): value is StockDetailSnapshot {
  if (!isRecord(value) || !Array.isArray(value.reports) || !isSafeStockCode(expectedStockCode)) return false;
  const context = value.value_context;
  const progress = value.target_price_progress;
  const trail = value.target_price_trail;
  const journey = value.target_journey;
  const related = value.related_context;
  const news = value.news_observation_detail;
  const volume = value.recent_volume_days;
  const flow = value.investor_flow;
  const flowTabs = value.investor_flow_tabs;
  return (
    typeof value.now === "string" &&
    Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" &&
    value.timezone.length > 0 &&
    value.surface === "web-view" &&
    value.read_only === true &&
    value.business_date === expectedDate &&
    isBusinessDate(value.business_date) &&
    value.stock_code === expectedStockCode &&
    (value.stock_name === null || typeof value.stock_name === "string") &&
    typeof value.has_selected_date_report === "boolean" &&
    (value.report_empty_state === null || typeof value.report_empty_state === "string") &&
    isMarketReference(value.market_reference, expectedDate) &&
    isRecord(context) &&
    isDateOrNull(context.report_reference_date) &&
    isDateOrNull(context.toss_reference_date) &&
    (context.current_price_reference_time === null || typeof context.current_price_reference_time === "string") &&
    (context.current_price_basis === null || typeof context.current_price_basis === "string") &&
    isDateOrNull(context.turnover_reference_date) &&
    isDateOrNull(context.investor_flow_reference_date) &&
    typeof context.news_collection_status === "string" &&
    Array.isArray(context.missing_labels) &&
    context.missing_labels.every((item: unknown) => typeof item === "string") &&
    isRecord(progress) &&
    typeof progress.validation_available === "boolean" &&
    (progress.hit_min_horizon_days === null || (typeof progress.hit_min_horizon_days === "number" && Number.isInteger(progress.hit_min_horizon_days))) &&
    (progress.hit_max_horizon_days === null || (typeof progress.hit_max_horizon_days === "number" && Number.isInteger(progress.hit_max_horizon_days))) &&
    typeof progress.validation_notice === "string" &&
    isRecord(trail) &&
    typeof trail.available === "boolean" &&
    trail.source === "stored_reports" &&
    trail.live_fetch === false &&
    trail.scoring === false &&
    trail.recommendation === false &&
    trail.business_date === expectedDate &&
    trail.stock_code === expectedStockCode &&
    typeof trail.summary === "string" &&
    isNumberOrNull(trail.current_price) &&
    isNumberOrNull(trail.current_target_price) &&
    isNumberOrNull(trail.attainment_percent) &&
    typeof trail.notice === "string" &&
    isRecord(journey) &&
    typeof journey.available === "boolean" &&
    journey.source === "stored_reports_and_stock_market_daily" &&
    journey.live_fetch === false &&
    journey.scoring === false &&
    journey.recommendation === false &&
    journey.business_date === expectedDate &&
    journey.stock_code === expectedStockCode &&
    typeof journey.price_basis === "string" &&
    typeof journey.notice === "string" &&
    Array.isArray(journey.items) &&
    journey.items.every(isTargetJourneyItem) &&
    isRecord(related) &&
    typeof related.available === "boolean" &&
    related.source === "stored_category_rollup" &&
    related.etf_source === "manual_mapping_stored_toss_etf_snapshot" &&
    related.live_fetch === false &&
    related.scoring === false &&
    related.recommendation === false &&
    related.business_date === expectedDate &&
    related.stock_code === expectedStockCode &&
    typeof related.notice === "string" &&
    Array.isArray(related.categories) &&
    related.categories.every(isStockRelatedCategory) &&
    isRecord(news) &&
    news.source === "stored_news_intelligence_observation" &&
    news.read_only === true &&
    news.live_fetch === false &&
    typeof news.available === "boolean" &&
    typeof news.display_label === "string" &&
    typeof news.reason === "string" &&
    (news.connection_label === undefined || typeof news.connection_label === "string") &&
    (news.connection_reason === undefined || typeof news.connection_reason === "string") &&
    (news.top_title === undefined || news.top_title === null || typeof news.top_title === "string") &&
    (news.direct_count === undefined || (typeof news.direct_count === "number" && Number.isInteger(news.direct_count))) &&
    (news.caution_count === undefined || (typeof news.caution_count === "number" && Number.isInteger(news.caution_count))) &&
    (news.market_context_count === undefined || (typeof news.market_context_count === "number" && Number.isInteger(news.market_context_count))) &&
    (news.krx_reference_status === undefined || typeof news.krx_reference_status === "string") &&
    (news.missing_context === undefined ||
      (Array.isArray(news.missing_context) && news.missing_context.every((item: unknown) => typeof item === "string"))) &&
    (news.top_titles === undefined || (Array.isArray(news.top_titles) && news.top_titles.every((item: unknown) => typeof item === "string"))) &&
    (news.news_digest === undefined || (Array.isArray(news.news_digest) && news.news_digest.every(isNewsDigestItem))) &&
    isRecord(volume) &&
    typeof volume.available === "boolean" &&
    (volume.source === null || volume.source === "toss_openapi") &&
    volume.live_fetch === false &&
    volume.business_date === expectedDate &&
    isDateOrNull(volume.reference_date) &&
    typeof volume.exact_date_available === "boolean" &&
    typeof volume.notice === "string" &&
    Array.isArray(volume.items) &&
    volume.items.every(isStockVolumeDay) &&
    isRecord(flow) &&
    typeof flow.available === "boolean" &&
    (flow.source === null || flow.source === "toss_openapi") &&
    flow.data_scope === "stored_toss_close_priority_flow" &&
    flow.live_fetch === false &&
    flow.scoring === false &&
    isDateOrNull(flow.snapshot_date) &&
    typeof flow.notice === "string" &&
    isRecord(flowTabs) &&
    typeof flowTabs.available === "boolean" &&
    (flowTabs.source === null || flowTabs.source === "toss_openapi") &&
    flowTabs.live_fetch === false &&
    flowTabs.business_date === expectedDate &&
    isDateOrNull(flowTabs.reference_date) &&
    typeof flowTabs.exact_date_available === "boolean" &&
    typeof flowTabs.volume_unit === "string" &&
    typeof flowTabs.notice === "string" &&
    Array.isArray(flowTabs.retail_foreign_institution) &&
    flowTabs.retail_foreign_institution.every(isStockInvestorFlowDay) &&
    value.reports.every((report: unknown) => isStockReport(report, expectedStockCode))
  );
}
