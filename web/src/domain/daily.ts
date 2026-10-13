export type DailyStock = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min?: number | null;
  target_price_max?: number | null;
  dominant_opinion: string;
  market_reference?: DailyStockMarketReference | null;
};

export type DailyStockMarketReference = {
  business_date: string;
  market: string;
  close_price?: number | null;
  change_percent?: number | null;
  volume?: number | null;
  turnover?: number | null;
  fetched_at: string;
};

export function defaultIncludeSingleReportStocks(
  stocks: readonly Pick<DailyStock, "mention_count">[],
  requestedIncludeSingle: boolean,
): boolean {
  return requestedIncludeSingle || !stocks.some((stock) => stock.mention_count > 1);
}

export function parseDailyStockLimit(value: string | null): number {
  if (value === null || !/^\d+$/.test(value.trim())) return 6;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? Math.min(100, Math.max(6, parsed)) : 6;
}

export type DailyStoredMarketItem = {
  business_date: string;
  stock_code?: string | null;
  stock_name?: string | null;
  market?: string | null;
  close_price?: number | null;
  change_percent?: number | null;
  volume?: number | null;
  turnover?: number | null;
  fetched_at?: string | null;
  index_series?: string | null;
  index_name?: string | null;
  close_index?: number | null;
  etf_code?: string | null;
  etf_name?: string | null;
  nav?: number | null;
  evidence_label?: string | null;
};

export type DailyTossMarketFlow = {
  business_date: string;
  market: string;
  market_label: string;
  investor_type: string;
  investor_label: string;
  net_buy_volume?: number | null;
  net_buy_amount?: number | null;
  volume_unit?: string | null;
  amount_unit?: string | null;
};

export type DailyTossContext = {
  available: boolean;
  source: string | null;
  snapshot_date: string | null;
  capture_status: string | null;
  missing_domains: string[];
  notice: string;
  indices: DailyStoredMarketItem[];
  top_kospi_by_turnover: DailyStoredMarketItem[];
  top_kosdaq_by_turnover: DailyStoredMarketItem[];
  top_etfs_by_turnover: DailyStoredMarketItem[];
};

export type DailyTossRecentFlow = {
  available: boolean;
  source: string | null;
  business_date: string;
  reference_date: string | null;
  exact_date_available: boolean;
  notice: string;
  items: {
    business_date: string;
    kospi_top_by_turnover: DailyStoredMarketItem | null;
    kosdaq_top_by_turnover: DailyStoredMarketItem | null;
    etf_top_by_turnover?: DailyStoredMarketItem | null;
  }[];
};

export type DailyTossInvestorFlow = {
  available: boolean;
  source: string | null;
  data_scope: "stored_toss_close_market_flow";
  live_fetch: false;
  scoring: false;
  snapshot_date: string | null;
  notice: string;
  market_flows: DailyTossMarketFlow[];
};

export type DailyFreshnessItem = {
  key: string;
  label: string;
  source: string;
  status: string;
  reference_date?: string | null;
  available: boolean;
  count?: number;
  coverage_count?: number;
  candidate_count?: number;
  notice?: string;
  exact_date_available?: boolean;
  capture_status?: string | null;
  missing_domains?: string[];
};

export type DailyNewsObservation = {
  source: "stored_news_intelligence_observation";
  read_only: true;
  live_fetch: false;
  available: boolean;
  business_date: string;
  display_label: string;
  reason: string;
  connection_note?: string;
  candidate_overlap_names?: string[];
  observed_at: string | null;
  missing_context: string[];
  top_titles?: string[];
  candidate_overlap_count?: number | null;
  direct_count?: number | null;
  caution_count?: number | null;
  market_context_count?: number | null;
  krx_reference_status?: string;
  independent_count?: number | null;
  report_recap_count?: number | null;
  unknown_count?: number | null;
  items?: DailyNewsObservationItem[];
};

export type DailyNewsObservationItem = {
  available: boolean;
  stock_name: string;
  stock_code: string | null;
  display_label: string;
  reason: string;
  direct_count: number;
  caution_count: number;
  market_context_count: number;
  krx_reference_status: string;
  observed_at: string;
  top_title?: string | null;
  connection_label: string;
  connection_reason: string;
  collection_run_count: number;
  latest_collection_at: string | null;
  latest_collection_status: string;
  daily_evidence_retained: boolean;
};

export type DailySnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  report_count: number;
  summary_stock_count: number;
  source_freshness_summary: {
    source: "stored_source_freshness";
    read_only: true;
    live_fetch: false;
    scoring: false;
    recommendation: false;
    business_date: string;
    items: DailyFreshnessItem[];
  };
  news_observation_summary: DailyNewsObservation;
  market_commentary?: {
    same_day_report_status?: {
      business_date: string;
      can_overlap_intraday_market_top: boolean;
      reason: string;
    };
  };
  market_briefing?: {
    source?: string;
    market_reference_lines?: string[];
    check_points?: string[];
    index_summary?: { reference_date?: string | null };
    time_slot_mood_card?: {
      headline?: string;
      sections?: { key: string; items: string[] }[];
    };
  };
  toss_context: DailyTossContext;
  toss_recent_flow: DailyTossRecentFlow;
  toss_investor_flow: DailyTossInvestorFlow;
  stocks: DailyStock[];
};

export type DailyStockSummarySnapshot = {
  surface: "web-view";
  read_only: true;
  live_fetch: false;
  business_date: string;
  stocks: DailyStock[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function isCount(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 0;
}

function isNullableCount(value: unknown): value is number | null {
  return value === null || isCount(value);
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isOptionalString(value: Record<string, unknown>, key: string): boolean {
  return value[key] === undefined || value[key] === null || typeof value[key] === "string";
}

function isOptionalNumber(value: Record<string, unknown>, key: string): boolean {
  return value[key] === undefined || isNullableNumber(value[key]);
}

function isDailyStoredMarketItem(value: unknown, throughDate: string): value is DailyStoredMarketItem {
  if (!isRecord(value) || !isBusinessDate(value.business_date) || value.business_date > throughDate) return false;
  if (!["stock_code", "stock_name", "market", "fetched_at", "index_series", "index_name", "etf_code", "etf_name", "evidence_label"]
    .every((key) => isOptionalString(value, key))) return false;
  if (!["close_price", "change_percent", "volume", "turnover", "close_index", "nav"]
    .every((key) => isOptionalNumber(value, key))) return false;
  return value.fetched_at == null || Number.isFinite(Date.parse(value.fetched_at as string));
}

function isDailyTossContext(value: unknown, expectedDate: string): value is DailyTossContext {
  if (!isRecord(value) || typeof value.available !== "boolean" ||
    !(value.source === null || typeof value.source === "string") ||
    !(value.snapshot_date === null || (isBusinessDate(value.snapshot_date) && value.snapshot_date <= expectedDate)) ||
    (value.available && value.snapshot_date !== expectedDate) ||
    !(value.capture_status === null || typeof value.capture_status === "string") ||
    typeof value.notice !== "string" || !Array.isArray(value.missing_domains) ||
    !value.missing_domains.every((item: unknown) => typeof item === "string")) return false;
  const keys = ["indices", "top_kospi_by_turnover", "top_kosdaq_by_turnover", "top_etfs_by_turnover"];
  if (!keys.every((key) => Array.isArray(value[key]) && value[key].every((item: unknown) =>
    isDailyStoredMarketItem(item, expectedDate) && item.business_date === expectedDate))) return false;
  return value.available === keys.some((key) => (value[key] as unknown[]).length > 0);
}

function isDailyTossRecentFlow(value: unknown, expectedDate: string): value is DailyTossRecentFlow {
  if (!isRecord(value) || typeof value.available !== "boolean" ||
    !(value.source === null || typeof value.source === "string") ||
    value.business_date !== expectedDate ||
    !(value.reference_date === null || (isBusinessDate(value.reference_date) && value.reference_date <= expectedDate)) ||
    value.exact_date_available !== (value.reference_date === expectedDate) ||
    typeof value.notice !== "string" || !Array.isArray(value.items)) return false;
  const validItems = value.items.every((item: unknown) => {
    if (!isRecord(item) || !isBusinessDate(item.business_date) || item.business_date > expectedDate) return false;
    return ["kospi_top_by_turnover", "kosdaq_top_by_turnover"].every((key) => {
      const marketItem = item[key];
      return marketItem === null || (isDailyStoredMarketItem(marketItem, expectedDate) && marketItem.business_date === item.business_date);
    }) && (item.etf_top_by_turnover === undefined || item.etf_top_by_turnover === null ||
      (isDailyStoredMarketItem(item.etf_top_by_turnover, expectedDate) && item.etf_top_by_turnover.business_date === item.business_date));
  });
  return validItems && value.available === (value.items.length > 0);
}

function isDailyTossInvestorFlow(value: unknown, expectedDate: string): value is DailyTossInvestorFlow {
  if (!isRecord(value) || typeof value.available !== "boolean" ||
    !(value.source === null || typeof value.source === "string") ||
    value.data_scope !== "stored_toss_close_market_flow" || value.live_fetch !== false || value.scoring !== false ||
    !(value.snapshot_date === null || value.snapshot_date === expectedDate) ||
    (value.available && value.snapshot_date !== expectedDate) ||
    typeof value.notice !== "string" || !Array.isArray(value.market_flows)) return false;
  const validFlows = value.market_flows.every((item: unknown) =>
    isRecord(item) && item.business_date === expectedDate &&
    typeof item.market === "string" && typeof item.market_label === "string" &&
    typeof item.investor_type === "string" && typeof item.investor_label === "string" &&
    ["net_buy_volume", "net_buy_amount"].every((key) => isOptionalNumber(item, key)) &&
    ["volume_unit", "amount_unit"].every((key) => isOptionalString(item, key)));
  return validFlows && value.available === (value.market_flows.length > 0);
}

export function isBusinessDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (year < 1) return false;
  const parsed = new Date(0);
  parsed.setUTCHours(0, 0, 0, 0);
  parsed.setUTCFullYear(year, month - 1, day);
  return parsed.toISOString().slice(0, 10) === value;
}

export function dailyStockDetailHref(businessDate: string, stockCode: string | null | undefined): string | undefined {
  return isBusinessDate(businessDate) && /^\d{6}$/.test(stockCode ?? "")
    ? `/daily/${businessDate}/stocks/${stockCode}`
    : undefined;
}

function isFreshnessItem(value: unknown): value is DailyFreshnessItem {
  return (
    isRecord(value) &&
    typeof value.key === "string" &&
    typeof value.label === "string" &&
    typeof value.source === "string" &&
    typeof value.status === "string" &&
    (value.reference_date === undefined || value.reference_date === null || isBusinessDate(value.reference_date)) &&
    typeof value.available === "boolean" &&
    (value.count === undefined || isCount(value.count)) &&
    ((value.coverage_count === undefined && value.candidate_count === undefined) ||
      (isCount(value.coverage_count) && isCount(value.candidate_count) && value.coverage_count <= value.candidate_count)) &&
    (value.notice === undefined || typeof value.notice === "string") &&
    (value.exact_date_available === undefined || typeof value.exact_date_available === "boolean") &&
    (value.capture_status === undefined || value.capture_status === null || typeof value.capture_status === "string") &&
    (value.missing_domains === undefined ||
      (Array.isArray(value.missing_domains) && value.missing_domains.every((item: unknown) => typeof item === "string")))
  );
}

function isDailyStockMarketReference(value: unknown, throughDate: string, requireExactReference = false): value is DailyStockMarketReference {
  return (
    isRecord(value) &&
    isBusinessDate(value.business_date) &&
    (requireExactReference ? value.business_date === throughDate : value.business_date <= throughDate) &&
    typeof value.market === "string" &&
    ["close_price", "change_percent", "volume", "turnover"].every((key) =>
      requireExactReference
        ? Object.hasOwn(value, key) && isNullableNumber(value[key])
        : value[key] === undefined || isNullableNumber(value[key])) &&
    typeof value.fetched_at === "string" &&
    Number.isFinite(Date.parse(value.fetched_at))
  );
}

function isDailyStock(value: unknown, requireExactMarketReference = false): value is DailyStock {
  return (
    isRecord(value) &&
    isBusinessDate(value.business_date) &&
    typeof value.stock_name === "string" &&
    (value.stock_code === null || typeof value.stock_code === "string") &&
    isCount(value.mention_count) &&
    typeof value.broker_display === "string" &&
    (value.target_price_min === undefined || isNullableCount(value.target_price_min)) &&
    (value.target_price_max === undefined || isNullableCount(value.target_price_max)) &&
    typeof value.dominant_opinion === "string" &&
    (value.market_reference === undefined || value.market_reference === null ||
      isDailyStockMarketReference(value.market_reference, value.business_date, requireExactMarketReference))
  );
}

export function isDailyStockSummarySnapshot(value: unknown, expectedDate: string): value is DailyStockSummarySnapshot {
  return isRecord(value) && value.surface === "web-view" && value.read_only === true && value.live_fetch === false &&
    isBusinessDate(expectedDate) && value.business_date === expectedDate && Array.isArray(value.stocks) &&
    value.stocks.every((stock: unknown) => isDailyStock(stock, true) && stock.business_date === expectedDate);
}

function isDailyNewsObservationItem(value: unknown): value is DailyNewsObservationItem {
  return isRecord(value) && typeof value.available === "boolean" &&
    typeof value.stock_name === "string" && (value.stock_code === null || typeof value.stock_code === "string") &&
    typeof value.display_label === "string" && typeof value.reason === "string" &&
    isCount(value.direct_count) && isCount(value.caution_count) && isCount(value.market_context_count) &&
    typeof value.krx_reference_status === "string" && typeof value.observed_at === "string" && Number.isFinite(Date.parse(value.observed_at)) &&
    (value.top_title === undefined || value.top_title === null || typeof value.top_title === "string") &&
    typeof value.connection_label === "string" && typeof value.connection_reason === "string" &&
    isCount(value.collection_run_count) &&
    (value.latest_collection_at === null || (typeof value.latest_collection_at === "string" && Number.isFinite(Date.parse(value.latest_collection_at)))) &&
    typeof value.latest_collection_status === "string" && typeof value.daily_evidence_retained === "boolean";
}

export function isDailySnapshot(value: unknown, expectedDate: string): value is DailySnapshot {
  if (!isRecord(value) || !Array.isArray(value.stocks)) return false;
  const freshness = value.source_freshness_summary;
  const tossContext = value.toss_context;
  const newsObservation = value.news_observation_summary;
  const validNewsObservationCounts = isRecord(newsObservation) && [
    "candidate_overlap_count", "direct_count", "caution_count", "market_context_count", "independent_count", "report_recap_count", "unknown_count",
  ].every((key) => newsObservation[key] === undefined || isNullableCount(newsObservation[key]));
  const validNewsObservationDetails = isRecord(newsObservation) &&
    (newsObservation.connection_note === undefined || typeof newsObservation.connection_note === "string") &&
    (newsObservation.krx_reference_status === undefined || typeof newsObservation.krx_reference_status === "string") &&
    ["candidate_overlap_names", "top_titles"].every((key) => newsObservation[key] === undefined ||
      (Array.isArray(newsObservation[key]) && newsObservation[key].every((item: unknown) => typeof item === "string"))) &&
    (newsObservation.items === undefined || (Array.isArray(newsObservation.items) && newsObservation.items.length <= 100 &&
      newsObservation.items.every(isDailyNewsObservationItem)));
  const marketCommentary = value.market_commentary;
  const marketBriefing = value.market_briefing;
  const timeSlotMoodCard = isRecord(marketBriefing) ? marketBriefing.time_slot_mood_card : undefined;
  const indexSummary = isRecord(marketBriefing) ? marketBriefing.index_summary : undefined;
  const briefingSections = isRecord(timeSlotMoodCard) ? timeSlotMoodCard.sections : undefined;
  const validBriefingLines = isRecord(marketBriefing) && ["market_reference_lines", "check_points"].every((key) =>
    marketBriefing[key] === undefined ||
      (Array.isArray(marketBriefing[key]) && marketBriefing[key].every((item: unknown) => typeof item === "string")));
  const validBriefingSections = briefingSections === undefined || (
    Array.isArray(briefingSections) && briefingSections.every((section: unknown) =>
      isRecord(section) && typeof section.key === "string" && Array.isArray(section.items) &&
      section.items.every((item: unknown) => typeof item === "string"))
  );
  const validBriefingIndex = indexSummary === undefined || (
    isRecord(indexSummary) && (indexSummary.reference_date === undefined || indexSummary.reference_date === null || isBusinessDate(indexSummary.reference_date))
  );
  const validMarketBriefing = marketBriefing === undefined || (
    isRecord(marketBriefing) &&
    (marketBriefing.source === undefined || typeof marketBriefing.source === "string") &&
    validBriefingLines && validBriefingIndex && (timeSlotMoodCard === undefined || (
      isRecord(timeSlotMoodCard) &&
      (timeSlotMoodCard.headline === undefined || typeof timeSlotMoodCard.headline === "string") &&
      validBriefingSections
    ))
  );
  const sameDayStatus = marketCommentary && typeof marketCommentary === "object" && !Array.isArray(marketCommentary)
    ? (marketCommentary as Record<string, unknown>).same_day_report_status
    : undefined;
  return (
    typeof value.now === "string" &&
    Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" &&
    value.timezone.length > 0 &&
    value.surface === "web-view" &&
    value.read_only === true &&
    value.business_date === expectedDate &&
    isBusinessDate(value.business_date) &&
    isCount(value.report_count) &&
    isCount(value.summary_stock_count) &&
    value.summary_stock_count === value.stocks.length &&
    isRecord(freshness) &&
    freshness.source === "stored_source_freshness" &&
    freshness.read_only === true &&
    freshness.live_fetch === false &&
    freshness.scoring === false &&
    freshness.recommendation === false &&
    freshness.business_date === expectedDate &&
    Array.isArray(freshness.items) &&
    freshness.items.every(isFreshnessItem) &&
    isRecord(value.news_observation_summary) &&
    validNewsObservationCounts &&
    validNewsObservationDetails &&
    value.news_observation_summary.source === "stored_news_intelligence_observation" &&
    value.news_observation_summary.read_only === true &&
    value.news_observation_summary.live_fetch === false &&
    typeof value.news_observation_summary.available === "boolean" &&
    value.news_observation_summary.business_date === expectedDate &&
    typeof value.news_observation_summary.display_label === "string" &&
    typeof value.news_observation_summary.reason === "string" &&
    (value.news_observation_summary.observed_at === null ||
      (typeof value.news_observation_summary.observed_at === "string" &&
        Number.isFinite(Date.parse(value.news_observation_summary.observed_at)))) &&
    Array.isArray(value.news_observation_summary.missing_context) &&
    value.news_observation_summary.missing_context.every((item: unknown) => typeof item === "string") &&
    isDailyTossContext(tossContext, expectedDate) &&
    isDailyTossRecentFlow(value.toss_recent_flow, expectedDate) &&
    isDailyTossInvestorFlow(value.toss_investor_flow, expectedDate) &&
    (marketCommentary === undefined || (
      !!marketCommentary && typeof marketCommentary === "object" && !Array.isArray(marketCommentary) &&
      !!sameDayStatus && typeof sameDayStatus === "object" && !Array.isArray(sameDayStatus) &&
      (sameDayStatus as Record<string, unknown>).business_date === expectedDate &&
      typeof (sameDayStatus as Record<string, unknown>).can_overlap_intraday_market_top === "boolean" &&
      typeof (sameDayStatus as Record<string, unknown>).reason === "string"
    )) &&
    validMarketBriefing &&
    value.stocks.every((stock: unknown) => isDailyStock(stock) && stock.business_date === expectedDate)
  );
}

export function dailyFreshnessLabel(item: DailyFreshnessItem, businessDate: string): string {
  if (item.status === "configured") return "요청 시 조회";
  if (item.status === "disabled") return "사용 안 함";
  if (item.status === "missing" || !item.available) {
    if (item.capture_status === "failed") return "캡처 실패 · 저장 자료 없음";
    if (item.capture_status === "partial") return "부분 캡처 · 저장 자료 없음";
    if (item.capture_status === "empty") return "빈 캡처 · 저장 자료 없음";
    return "저장 자료 없음";
  }
  if (item.status === "stale") {
    return item.capture_status === "failed" ? "이전 기준일 · 새 캡처 실패" : "이전 기준일";
  }
  if (item.status === "partial" || item.capture_status === "partial" || item.capture_status === "failed") {
    return "선택일 일부 누락";
  }
  if (item.reference_date !== businessDate) return "기준일 상이";
  return item.exact_date_available === false ? "선택일 일부 누락" : "선택일 기준";
}

export function dailyStoredTimeLabel(value: string): string {
  return /^\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})/.exec(value)?.[1] ?? "시각 없음";
}

export function dailyStoredMarketReference(stock: DailyStock): { price: string; detail: string } {
  const reference = stock.market_reference;
  if (!reference || typeof reference.close_price !== "number") return {
    price: "자료 없음",
    detail: reference ? `Toss 저장 가격 없음 · 기준 ${reference.business_date}` : "Toss 저장 참고 없음",
  };
  const change = typeof reference.change_percent !== "number"
    ? "등락 자료 없음"
    : `${reference.change_percent > 0 ? "+" : ""}${reference.change_percent.toFixed(1)}%`;
  return {
    price: `${new Intl.NumberFormat("ko-KR").format(reference.close_price)}원`,
    detail: `${change} · ${reference.market || "시장 자료 없음"} · ${dailyStoredTimeLabel(reference.fetched_at)} 저장 · 기준 ${reference.business_date}`,
  };
}

export function dailyBrokerDisplay(value: string): string {
  const brokers = value.split(",").map((item) => item.trim()).filter(Boolean);
  if (!brokers.length) return "자료 없음";
  if (brokers.length === 1) return brokers[0];
  return `${brokers[0].replace(/\(\d+\)$/, "")} 외 ${brokers.length - 1}곳`;
}

export function dailyReportOpinionLabel(value: string | null | undefined): string {
  if (!value) return "-";
  const labels: Record<string, string> = {
    buy: "매수",
    neutral: "중립",
    hold: "중립",
    sell: "매도",
    "n/a": "의견 없음",
  };
  const label = labels[value.toLowerCase()] ?? value;
  return label !== "의견 없음" ? `리포트 표기: ${label}` : label;
}
