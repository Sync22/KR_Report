import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";

const SOURCE = "toss_openapi";
const ALLOWED_MISSING_DOMAINS = new Set([
  "top20",
  "security_metadata",
  "market_indices",
  "market_flow",
  "candidate_close_reassessment",
]);

type SummaryRow = {
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
};

type FreshnessItem = Record<string, unknown>;

type CaptureState = {
  status: string;
  business_date: string | null;
  missing_domains: string[];
} | null;

type DailyFreshnessOptions = {
  reportCount: number;
  candidateStockCodes: readonly string[];
  tossOpenApiReady: boolean;
  tossMarketReferenceDate?: string | null;
};

function status(referenceDate: string | null, businessDate: string): string {
  if (referenceDate === businessDate) return "exact";
  return referenceDate ? "stale" : "missing";
}

function freshnessItem(
  key: string,
  label: string,
  source: string,
  referenceDate: string | null,
  businessDate: string,
  available: boolean,
  dataScope: string,
  notice: string,
  count?: number,
): FreshnessItem {
  const item: FreshnessItem = {
    key,
    label,
    source,
    status: status(referenceDate, businessDate),
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    available,
    data_scope: dataScope,
    live_fetch: false,
    notice,
  };
  if (count !== undefined) item.count = count;
  return item;
}

function latestTossMarketDate(database: DatabaseSync, businessDate: string): string | null {
  const row = database.prepare(`
    SELECT business_date FROM (
      SELECT business_date FROM toss_market_context_snapshots
      WHERE business_date <= ? AND source = ?
      UNION
      SELECT business_date FROM stock_market_daily
      WHERE business_date <= ? AND source = ?
        AND (change_amount IS NOT NULL OR change_percent IS NOT NULL OR volume IS NOT NULL
             OR turnover IS NOT NULL OR market_cap IS NOT NULL OR listed_shares IS NOT NULL
             OR open_price IS NOT NULL OR high_price IS NOT NULL OR low_price IS NOT NULL)
      UNION
      SELECT business_date FROM etf_daily_snapshots
      WHERE business_date <= ? AND source = ?
      UNION
      SELECT business_date FROM market_index_daily
      WHERE business_date <= ? AND source = ?
    )
    ORDER BY business_date DESC
    LIMIT 1
  `).get(businessDate, SOURCE, businessDate, SOURCE, businessDate, SOURCE, businessDate, SOURCE) as
    | { business_date: string }
    | undefined;
  return row?.business_date ?? null;
}

function latestTossEtfDate(database: DatabaseSync, businessDate: string): string | null {
  const row = database.prepare(`
    SELECT business_date
    FROM etf_daily_snapshots
    WHERE business_date <= ? AND source = ?
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT 1
  `).get(businessDate, SOURCE) as { business_date: string } | undefined;
  return row?.business_date ?? null;
}

function latestTossFlowDate(database: DatabaseSync, businessDate: string): string | null {
  const row = database.prepare(`
    SELECT business_date FROM (
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
    LIMIT 1
  `).get(businessDate, SOURCE, businessDate, SOURCE, businessDate, SOURCE) as
    | { business_date: string }
    | undefined;
  return row?.business_date ?? null;
}

function tossCaptureState(database: DatabaseSync, businessDate: string): CaptureState {
  const row = database.prepare(`
    SELECT status, business_date, detail
    FROM operation_events
    WHERE component = ? AND event_type = ? AND business_date = ?
    ORDER BY event_time DESC, id DESC
    LIMIT 1
  `).get("toss-market-context", "capture", businessDate) as
    | { status: string; business_date: string | null; detail: string | null }
    | undefined;
  if (!row) return null;

  const detail = row.detail ?? "";
  const missingPart = detail.split(";").find((part) => part.trim().startsWith("missing_domains="));
  const separator = missingPart?.indexOf("=") ?? -1;
  const missingRaw = missingPart && separator >= 0 ? missingPart.slice(separator + 1).trim() : "";
  return {
    status: row.status,
    business_date: row.business_date,
    missing_domains: missingRaw.split(",").filter((value) => ALLOWED_MISSING_DOMAINS.has(value)),
  };
}

function candidateFlowItem(
  database: DatabaseSync,
  businessDate: string,
  candidateStockCodes: readonly string[],
): FreshnessItem | null {
  const summaries = database.prepare(`
    SELECT stock_name, stock_code, mention_count
    FROM daily_stock_summaries
    WHERE business_date = ?
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as SummaryRow[];
  const ordered = summaries.filter((summary) => summary.stock_code);
  const requestedCodes = candidateStockCodes.map((code) => String(code).trim()).filter(Boolean);
  const byCode = new Map<string, SummaryRow>();
  for (const summary of ordered) byCode.set(String(summary.stock_code).trim(), summary);
  const preferred = requestedCodes.flatMap((code) => {
    const summary = byCode.get(code);
    return summary ? [summary] : [];
  });
  const preferredCodes = new Set(preferred.map((summary) => String(summary.stock_code).trim()));
  const orderedCandidates = [
    ...preferred,
    ...ordered.filter((summary) => !preferredCodes.has(String(summary.stock_code).trim())),
  ];
  const selected = requestedCodes.length
    ? orderedCandidates.slice(0, requestedCodes.length)
    : orderedCandidates.slice(0, 3);
  const expectedCount = requestedCodes.length || selected.length;
  if (!selected.length) return null;

  const fromDate = new Date(`${businessDate}T00:00:00.000Z`);
  fromDate.setUTCDate(fromDate.getUTCDate() - 60);
  const flowDatesByCode = new Map<string, string[]>();
  const flowRows = database.prepare(`
    SELECT business_date
    FROM stock_investor_flow_daily
    WHERE business_date BETWEEN ? AND ?
      AND stock_code = ?
      AND source = ?
    ORDER BY business_date DESC, investor_type ASC
  `);
  const availableDates: string[] = [];
  for (const summary of selected) {
    const stockCode = summary.stock_code as string;
    let dates = flowDatesByCode.get(stockCode);
    if (!dates) {
      dates = [...new Set((flowRows.all(
        fromDate.toISOString().slice(0, 10),
        businessDate,
        stockCode,
        SOURCE,
      ) as unknown as Array<{ business_date: string }>).map((row) => row.business_date))].sort().reverse();
      flowDatesByCode.set(stockCode, dates);
    }
    if (dates.length) availableDates.push(dates[0]!);
  }
  if (!availableDates.length) return null;

  const exactCount = availableDates.filter((referenceDate) => referenceDate === businessDate).length;
  const freshnessStatus = expectedCount && exactCount === expectedCount
    ? "exact"
    : exactCount
      ? "partial"
      : "stale";
  return {
    key: "investor_flow",
    label: "Investor flow",
    display_label: "후보 수급",
    source: SOURCE,
    status: freshnessStatus,
    reference_date: [...availableDates].sort().reverse()[0]!,
    reference_dates: [...new Set(availableDates)].sort().reverse(),
    exact_date_available: freshnessStatus === "exact",
    available: true,
    data_scope: "stored_toss_close_priority_flow",
    coverage_count: availableDates.length,
    candidate_count: expectedCount,
    live_fetch: false,
    notice: "Selected candidates with stored Toss close investor-flow references.",
  };
}

function applyCaptureState(item: FreshnessItem, captureState: CaptureState): void {
  if (!captureState) return;
  item.capture_status = captureState.status;
  item.capture_date = captureState.business_date;
  item.missing_domains = captureState.missing_domains;
  if (["partial", "empty", "failed"].includes(captureState.status) && item.reference_date === captureState.business_date) {
    item.status = captureState.status === "empty" ? "missing" : "partial";
    item.exact_date_available = false;
  }
}

export function buildDailySourceFreshnessFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  options: DailyFreshnessOptions,
): Record<string, unknown> {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily source freshness date");

  const tossReferenceDate = options.tossMarketReferenceDate === undefined
    ? latestTossMarketDate(database, businessDate)
    : options.tossMarketReferenceDate;
  const tossEtfReferenceDate = latestTossEtfDate(database, businessDate);
  const flowReferenceDate = latestTossFlowDate(database, businessDate);
  const reportReferenceDate = options.reportCount > 0 ? businessDate : null;
  const investorFlowItem = candidateFlowItem(database, businessDate, options.candidateStockCodes);
  const items = [
    freshnessItem(
      "reports",
      "Naver reports",
      "naver_research",
      reportReferenceDate,
      businessDate,
      options.reportCount > 0,
      "stored_daily_summaries",
      "Stored Naver research reports for the selected date.",
      options.reportCount,
    ),
    freshnessItem(
      "toss_market",
      "Toss market",
      SOURCE,
      tossReferenceDate,
      businessDate,
      tossReferenceDate !== null,
      "stored_toss_close_market_snapshot",
      "Stored Toss close snapshot for market, turnover, and indices.",
    ),
    freshnessItem(
      "toss_etf",
      "Toss ETF",
      SOURCE,
      tossEtfReferenceDate,
      businessDate,
      tossEtfReferenceDate !== null,
      "stored_toss_close_etf_snapshot",
      "Stored Toss Top20 ETF turnover reference; constituents are not loaded.",
    ),
    investorFlowItem ?? freshnessItem(
      "investor_flow",
      "Investor flow",
      SOURCE,
      flowReferenceDate,
      businessDate,
      flowReferenceDate !== null,
      "stored_toss_close_market_flow",
      "Stored Toss close market flow reference.",
    ),
    {
      key: "toss_openapi",
      label: "Toss OpenAPI",
      source: SOURCE,
      status: options.tossOpenApiReady ? "configured" : "disabled",
      reference_date: null,
      exact_date_available: false,
      available: false,
      configured: options.tossOpenApiReady,
      data_scope: options.tossOpenApiReady ? "web_view_priority_top_2_prices_on_demand" : "not_configured",
      live_fetch: false,
      affects_ordering: false,
      notice: options.tossOpenApiReady
        ? "Toss OpenAPI is configured; current prices are fetched only on an explicit top-two request."
        : "Toss OpenAPI web-view current prices require .env.toss-openapi credentials and live opt-in.",
    },
  ];
  applyCaptureState(items[1]!, tossCaptureState(database, businessDate));

  return {
    source: "stored_source_freshness",
    read_only: true,
    business_date: businessDate,
    live_fetch: false,
    scoring: false,
    recommendation: false,
    items,
  };
}
