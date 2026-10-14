import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { CandidateEvidenceRow, CandidateEvidenceSnapshot } from "../domain/candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const DEFAULT_LIMIT = 5;
const MAX_LIMIT = 20;
const TURNOVER_SOURCE = "toss_openapi";
const FLOW_SOURCE = "toss_openapi";
const HISTORY_FLOW_SOURCE = "krx_data_market";
const MARKET_HISTORY_SOURCE = "krx";
const DEFAULT_HOLIDAYS = new Set([
  "2024-01-01", "2024-02-09", "2024-02-12", "2024-03-01", "2024-04-10", "2024-05-01",
  "2024-05-06", "2024-05-15", "2024-06-06", "2024-08-15", "2024-09-16", "2024-09-17",
  "2024-09-18", "2024-10-03", "2024-10-09", "2024-12-25", "2024-12-31",
  "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-03",
  "2025-05-01", "2025-05-05", "2025-05-06", "2025-06-03", "2025-06-06", "2025-08-15",
  "2025-10-03", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
  "2025-12-31",
  "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02", "2026-05-01",
  "2026-05-05", "2026-05-25", "2026-06-03", "2026-07-17", "2026-08-17", "2026-09-24",
  "2026-09-25", "2026-10-05", "2026-10-09", "2026-12-25", "2026-12-31",
]);

type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string | null;
};

type ReportRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  title: string;
  broker_name: string;
  published_at: string;
  target_price_value: number | null;
  source_url: string | null;
  source_id: string | null;
};

type StockMarketRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
  source: string;
  [key: string]: unknown;
};

type StockFlowRow = {
  business_date: string;
  stock_code: string;
  stock_name: string | null;
  market: string | null;
  investor_type: string;
  sell_volume: number | null;
  buy_volume: number | null;
  net_buy_volume: number | null;
  sell_amount: number | null;
  buy_amount: number | null;
  net_buy_amount: number | null;
  volume_unit: string | null;
  amount_unit: string | null;
  fetched_at: string;
  source: string;
};

type MarketFlowRow = {
  business_date: string;
  market: string;
  investor_type: string;
  sell_volume: number | null;
  buy_volume: number | null;
  net_buy_volume: number | null;
  sell_amount: number | null;
  buy_amount: number | null;
  net_buy_amount: number | null;
  volume_unit: string | null;
  amount_unit: string | null;
  fetched_at: string;
  source: string;
};

type MarketIndexRow = {
  business_date: string;
  index_series: string;
  close_index: number | null;
};

type TossBaselineRow = {
  stock_code: string;
  stock_name: string | null;
  last_price: number | null;
  currency: string | null;
  source: string;
  fetched_at: string;
};

type NewsRunRow = {
  run_id: string;
  target_date: string;
  stock_name: string;
  stock_code: string | null;
  matched_count: number;
  created_at: string;
};

type NewsEvidenceRow = {
  run_id: string;
  evidence_key: string;
  target_date: string;
  stock_code: string | null;
  stock_name: string;
  krx_reference_date: string | null;
  source_lane: string;
  title: string;
  summary: string;
  published_at: string;
  url: string;
  match_reason: string;
  match_scope: string;
  relevance: string;
  relevance_reason: string;
  sentiment: string;
  event_types_json: string;
  stock_impact: string;
  created_at: string;
  canonical_url: string;
  lineage_type: string;
};

type CandidateEvidenceResponse = Omit<CandidateEvidenceSnapshot, "rows"> & {
  close_reassessment: Record<string, unknown>;
  market_flow_context: Record<string, unknown>[];
  rows: CandidateEvidenceRow[];
};

function queryDate(value: string, days: number): string {
  const date = new Date(value + "T00:00:00.000Z");
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function isBusinessDay(value: string, holidays: Set<string>): boolean {
  const weekday = new Date(value + "T00:00:00.000Z").getUTCDay();
  return weekday !== 0 && weekday !== 6 && !holidays.has(value);
}

function holidayOverrides(): Set<string> {
  const holidays = new Set(DEFAULT_HOLIDAYS);
  for (const raw of (process.env.STOCK_MONITOR_HOLIDAYS ?? "").split(",")) {
    const value = raw.trim();
    if (isBusinessDate(value)) holidays.add(value);
  }
  return holidays;
}

function recentBusinessDates(reference: string, count: number, holidays: Set<string>): string[] {
  if (count <= 0) return [];
  const dates = [reference];
  let probe = reference;
  while (dates.length < count) {
    probe = queryDate(probe, -1);
    while (!isBusinessDay(probe, holidays)) probe = queryDate(probe, -1);
    dates.push(probe);
  }
  return dates;
}

function placeholders(count: number): string {
  return Array.from({ length: count }, () => "?").join(", ");
}

function uniqueStockCodes(summaries: SummaryRow[]): string[] {
  return [...new Set(summaries
    .map((summary) => summary.stock_code?.trim() ?? "")
    .filter(Boolean))].sort();
}

function readSummaries(database: DatabaseSync, businessDate: string): SummaryRow[] {
  return database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
           target_price_min, target_price_max, dominant_opinion
    FROM daily_stock_summaries
    WHERE business_date = ? AND stock_code IS NOT NULL AND stock_code <> ''
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as SummaryRow[];
}

function readReportsForDate(database: DatabaseSync, businessDate: string): ReportRow[] {
  return database.prepare(`
    SELECT business_date, stock_name, stock_code, title, broker_name, published_at,
           target_price_value, source_url, source_id
    FROM reports
    WHERE business_date = ?
    ORDER BY published_at DESC, broker_name ASC, title ASC
  `).all(businessDate) as unknown as ReportRow[];
}

function readMarketReferences(database: DatabaseSync, businessDate: string, stockCodes: string[]): Map<string, StockMarketRow> {
  if (!stockCodes.length) return new Map();
  const rows = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, section_name,
           close_price, change_amount, change_percent, open_price, high_price, low_price,
           volume, turnover, market_cap, listed_shares, fetched_at, source
    FROM stock_market_daily
    WHERE business_date = ? AND source = ? AND stock_code IN (${placeholders(stockCodes.length)})
    ORDER BY stock_code ASC
  `).all(businessDate, TURNOVER_SOURCE, ...stockCodes) as unknown as StockMarketRow[];
  return new Map(rows.map((row) => [row.stock_code, row]));
}

function readMarketFlows(database: DatabaseSync, businessDate: string): MarketFlowRow[] {
  return database.prepare(`
    SELECT business_date, market, investor_type, sell_volume, buy_volume, net_buy_volume,
           sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit, fetched_at, source
    FROM market_investor_flow_daily
    WHERE business_date = ? AND market IN ('KOSPI', 'KOSDAQ') AND source = ?
    ORDER BY market ASC, investor_type ASC
  `).all(businessDate, FLOW_SOURCE) as unknown as MarketFlowRow[];
}

function readReportContext(database: DatabaseSync, businessDate: string, stockCodes: string[], recentDates: string[], summaries: SummaryRow[]) {
  const intensity = new Map<string, { report_count: number; active_dates: number; broker_count: number }>();
  const previousTargets = new Map<string, { previous_date: string; previous_min: number; previous_max: number; previous_report_count: number; previous_broker_count: number }>();
  const firstTargetDates = new Map<string, string | null>();
  if (!stockCodes.length) return { intensity, previousTargets, firstTargetDates };
  const dateValues = recentDates.length ? recentDates : [businessDate];
  const reportRows = database.prepare(`
    SELECT stock_code, COUNT(*) AS report_count, COUNT(DISTINCT business_date) AS active_dates,
           COUNT(DISTINCT NULLIF(TRIM(broker_name), '')) AS broker_count
    FROM reports
    WHERE stock_code IN (${placeholders(stockCodes.length)})
      AND business_date IN (${placeholders(dateValues.length)})
    GROUP BY stock_code
  `).all(...stockCodes, ...dateValues) as unknown as { stock_code: string; report_count: number; active_dates: number; broker_count: number }[];
  for (const row of reportRows) intensity.set(row.stock_code, row);
  const previousRows = database.prepare(`
    WITH latest_previous AS (
      SELECT stock_code, MAX(business_date) AS business_date
      FROM reports
      WHERE stock_code IN (${placeholders(stockCodes.length)})
        AND business_date < ? AND target_price_value IS NOT NULL
      GROUP BY stock_code
    )
    SELECT r.stock_code, r.business_date, MIN(r.target_price_value) AS target_min,
           MAX(r.target_price_value) AS target_max, COUNT(*) AS report_count,
           COUNT(DISTINCT NULLIF(TRIM(r.broker_name), '')) AS broker_count
    FROM reports r
    JOIN latest_previous p ON p.stock_code = r.stock_code AND p.business_date = r.business_date
    WHERE r.target_price_value IS NOT NULL
    GROUP BY r.stock_code, r.business_date
  `).all(...stockCodes, businessDate) as unknown as { stock_code: string; business_date: string; target_min: number; target_max: number; report_count: number; broker_count: number }[];
  for (const row of previousRows) {
    previousTargets.set(row.stock_code, {
      previous_date: row.business_date,
      previous_min: row.target_min,
      previous_max: row.target_max,
      previous_report_count: row.report_count ?? 0,
      previous_broker_count: row.broker_count ?? 0,
    });
  }
  for (const summary of summaries) {
    if (summary.stock_code) firstTargetDates.set(summary.stock_code, summary.target_price_min !== null || summary.target_price_max !== null ? businessDate : null);
  }
  return { intensity, previousTargets, firstTargetDates };
}

function readStockFlows(database: DatabaseSync, businessDate: string, stockCodes: string[]): { sameDay: Map<string, StockFlowRow[]>; history: Map<string, StockFlowRow[]> } {
  const sameDay = new Map<string, StockFlowRow[]>();
  const history = new Map<string, StockFlowRow[]>();
  if (!stockCodes.length) return { sameDay, history };
  const fromDate = queryDate(businessDate, -60);
  const rows = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, investor_type, sell_volume, buy_volume,
           net_buy_volume, sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit,
           candidate_score, candidate_reasons, fetched_at, source
    FROM stock_investor_flow_daily
    WHERE stock_code IN (${placeholders(stockCodes.length)})
      AND ((source = ? AND business_date BETWEEN ? AND ?) OR (source = ? AND business_date = ?))
    ORDER BY stock_code ASC, business_date DESC, investor_type ASC
  `).all(...stockCodes, HISTORY_FLOW_SOURCE, fromDate, businessDate, FLOW_SOURCE, businessDate) as unknown as StockFlowRow[];
  for (const row of rows) {
    const target = row.source === HISTORY_FLOW_SOURCE ? history : sameDay;
    const list = target.get(row.stock_code) ?? [];
    list.push(row);
    target.set(row.stock_code, list);
  }
  return { sameDay, history };
}

function readMarketHistory(database: DatabaseSync, businessDate: string, stockCodes: string[]): Map<string, StockMarketRow[]> {
  const result = new Map<string, StockMarketRow[]>();
  if (!stockCodes.length) return result;
  const fromDate = queryDate(businessDate, -500);
  const toDate = queryDate(businessDate, 90);
  const rows = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, section_name, close_price, change_amount,
           change_percent, open_price, high_price, low_price, volume, turnover, market_cap,
           listed_shares, fetched_at, source
    FROM stock_market_daily
    WHERE business_date BETWEEN ? AND ? AND stock_code IN (${placeholders(stockCodes.length)})
      AND source = ?
    ORDER BY stock_code ASC, business_date DESC
  `).all(fromDate, toDate, ...stockCodes, MARKET_HISTORY_SOURCE) as unknown as StockMarketRow[];
  for (const row of rows) {
    const list = result.get(row.stock_code) ?? [];
    list.push(row);
    result.set(row.stock_code, list);
  }
  return result;
}

function readMarketIndexes(database: DatabaseSync, businessDate: string): Map<string, MarketIndexRow[]> {
  const result = new Map<string, MarketIndexRow[]>();
  const fromDate = queryDate(businessDate, -500);
  const toDate = queryDate(businessDate, 90);
  const rows = database.prepare(`
    SELECT business_date, index_series, close_index
    FROM market_index_daily
    WHERE business_date BETWEEN ? AND ? AND index_series IN ('KOSPI', 'KOSDAQ') AND source = ?
    ORDER BY index_series ASC, business_date ASC
  `).all(fromDate, toDate, MARKET_HISTORY_SOURCE) as unknown as MarketIndexRow[];
  for (const row of rows) {
    const list = result.get(row.index_series) ?? [];
    list.push(row);
    result.set(row.index_series, list);
  }
  return result;
}

function readTossBaselines(database: DatabaseSync, businessDate: string, stockCodes: string[]): Map<string, TossBaselineRow> {
  const result = new Map<string, TossBaselineRow>();
  if (!stockCodes.length) return result;
  const rows = database.prepare(`
    SELECT business_date, stock_code, stock_name, baseline_time, last_price, currency, source, fetched_at
    FROM toss_priority_quote_baselines
    WHERE business_date = ? AND baseline_time = '20:00' AND stock_code IN (${placeholders(stockCodes.length)})
    ORDER BY fetched_at DESC, stock_code ASC
  `).all(businessDate, ...stockCodes) as unknown as TossBaselineRow[];
  for (const row of rows) if (!result.has(row.stock_code)) result.set(row.stock_code, row);
  return result;
}

function readNews(database: DatabaseSync, businessDate: string, stockCodes: string[], nameByCode: Map<string, string>) {
  const runs = database.prepare(`
    SELECT run_id, target_date, stock_name, stock_code, matched_count, created_at
    FROM news_intelligence_runs
    WHERE target_date = ?
    ORDER BY created_at DESC, run_id DESC
    LIMIT 100
  `).all(businessDate) as unknown as NewsRunRow[];
  const selected = new Set(stockCodes);
  const normalizedName = (value: string | null | undefined) => (value ?? "").trim().toLowerCase();
  const codeByName = new Map([...nameByCode].map(([code, name]) => [normalizedName(name), code]));
  const runsByCode = new Map<string, NewsRunRow[]>();
  for (const run of runs) {
    const code = run.stock_code && selected.has(run.stock_code) ? run.stock_code : codeByName.get(normalizedName(run.stock_name));
    if (!code) continue;
    const list = runsByCode.get(code) ?? [];
    list.push(run);
    runsByCode.set(code, list);
  }
  const runIds = [...new Set([...runsByCode.values()].flat().map((run) => run.run_id))];
  const evidenceByRun = new Map<string, NewsEvidenceRow[]>();
  if (runIds.length) {
    const rows = database.prepare(`
      WITH ranked_evidence AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY target_date DESC, created_at DESC, evidence_key) AS row_number
        FROM report_linked_news_evidence WHERE run_id IN (${placeholders(runIds.length)})
      )
      SELECT run_id, evidence_key, target_date, stock_code, stock_name, krx_reference_date, source_lane,
             title, summary, published_at, url, match_reason, match_scope, relevance, relevance_reason,
             sentiment, event_types_json, stock_impact, created_at, canonical_url, lineage_type
      FROM ranked_evidence WHERE row_number <= 20
      ORDER BY target_date DESC, created_at DESC, evidence_key
    `).all(...runIds) as unknown as NewsEvidenceRow[];
    for (const row of rows) {
      const list = evidenceByRun.get(row.run_id) ?? [];
      list.push(row);
      evidenceByRun.set(row.run_id, list);
    }
  }
  const badges = new Map<string, Record<string, unknown>>();
  for (const stockCode of stockCodes) {
    const name = normalizedName(nameByCode.get(stockCode));
    const runRows = runsByCode.get(stockCode) ?? [];
    const rows = runRows.flatMap((run) => (evidenceByRun.get(run.run_id) ?? []).filter((row) =>
      row.stock_code === stockCode || (!!name && normalizedName(row.stock_name) === name),
    ));
    const badge = rows.length ? candidateNewsBadge(rows, businessDate) : runRows.length ? collectedEmptyCandidateNewsBadge() : emptyNewsBadge();
    if (runRows.length) {
      const latest = [...runRows].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.run_id.localeCompare(a.run_id))[0];
      const latestStatus = Number(latest.matched_count || 0) > 0 ? "matched" : "no_match";
      Object.assign(badge, {
        collection_run_count: runRows.length,
        latest_collection_at: latest.created_at,
        latest_collection_status: latestStatus,
        daily_evidence_retained: latestStatus === "no_match" && rows.length > 0,
      });
    }
    badges.set(stockCode, badge);
  }
  return badges;
}


function marketDisplay(value: string | null | undefined): string {
  const normalized = (value ?? "").trim().toUpperCase();
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[normalized] ?? "시장 미확인";
}

function investorDisplay(value: string | null | undefined): string {
  const normalized = (value ?? "").trim().toLowerCase();
  return ({
    foreign: "외국인", institution: "기관", individual: "개인",
    "외국인": "외국인", "기관": "기관", "기관합계": "기관합계", "개인": "개인", "전체": "전체",
  } as Record<string, string>)[normalized] ?? "투자자 미확인";
}

function marketSort(value: string): [number, string] {
  const label = marketDisplay(value);
  const order = { KOSPI: 0, KOSDAQ: 1, "전체": 2 } as Record<string, number>;
  return [order[label] ?? 99, label];
}

function investorSort(value: string): [number, string] {
  const label = investorDisplay(value);
  const order = { "외국인": 0, "기관합계": 1, "기관": 2, "개인": 3, "전체": 9 } as Record<string, number>;
  return [order[label] ?? 99, label];
}

function sortedMarketFlows(rows: MarketFlowRow[]): Record<string, unknown>[] {
  return [...rows]
    .sort((a, b) => {
      const ma = marketSort(a.market); const mb = marketSort(b.market);
      return ma[0] - mb[0] || ma[1].localeCompare(mb[1]) ||
        investorSort(a.investor_type)[0] - investorSort(b.investor_type)[0] ||
        investorSort(a.investor_type)[1].localeCompare(investorSort(b.investor_type)[1]);
    })
    .map((row) => ({
      business_date: row.business_date,
      market: row.market,
      market_label: marketDisplay(row.market),
      investor_type: row.investor_type,
      investor_label: investorDisplay(row.investor_type),
      sell_volume: row.sell_volume,
      buy_volume: row.buy_volume,
      net_buy_volume: row.net_buy_volume,
      sell_amount: row.sell_amount,
      buy_amount: row.buy_amount,
      net_buy_amount: row.net_buy_amount,
      volume_unit: row.volume_unit,
      amount_unit: row.amount_unit,
      source: row.source,
    }));
}

function sumByInvestor(rows: StockFlowRow[], types: Set<string>, field: "net_buy_volume" | "net_buy_amount"): number | null {
  let total = 0;
  let found = false;
  for (const row of rows) {
    if (types.has(investorDisplay(row.investor_type)) && row[field] !== null) {
      total += row[field] as number;
      found = true;
    }
  }
  return found ? total : null;
}

function stockFlowTotals(rows: StockFlowRow[]): Record<string, unknown> {
  return {
    individual_net_buy_volume: sumByInvestor(rows, new Set(["개인"]), "net_buy_volume"),
    foreign_net_buy_volume: sumByInvestor(rows, new Set(["외국인"]), "net_buy_volume"),
    institution_net_buy_volume: sumByInvestor(rows, new Set(["기관", "기관합계"]), "net_buy_volume"),
    individual_net_buy_amount: sumByInvestor(rows, new Set(["개인"]), "net_buy_amount"),
    foreign_net_buy_amount: sumByInvestor(rows, new Set(["외국인"]), "net_buy_amount"),
    institution_net_buy_amount: sumByInvestor(rows, new Set(["기관", "기관합계"]), "net_buy_amount"),
    volume_unit: rows[0]?.volume_unit ?? null,
    amount_unit: rows[0]?.amount_unit ?? null,
    snapshot_date: rows[0]?.business_date ?? null,
    available: rows.length > 0,
  };
}

function emptyNewsBadge(): Record<string, unknown> {
  return {
    available: false,
    display_label: "뉴스 근거 수집 전",
    reason: "저장 뉴스 근거를 아직 수집하지 않았습니다.",
    connection_label: "뉴스 근거 수집 전",
    connection_reason: "저장 뉴스 근거가 수집되면 후보와 연결됩니다.",
    direct_count: 0,
    caution_count: 0,
    market_context_count: 0,
    krx_reference_status: "missing",
    observed_at: null,
    top_title: null,
    digest_label: null,
    news_digest: [],
  };
}

function collectedEmptyCandidateNewsBadge(): Record<string, unknown> {
  return {
    available: true,
    display_label: "매칭 뉴스 없음",
    reason: "수집은 완료됐지만 이 후보와 직접 연결된 뉴스는 없었습니다.",
    connection_label: "매칭 뉴스 없음",
    connection_reason: "수집은 실행됐고, 선택 날짜의 후보와 직접 연결된 뉴스는 없었습니다.",
    direct_count: 0,
    caution_count: 0,
    market_context_count: 0,
    krx_reference_status: "missing",
    observed_at: null,
    top_title: null,
    digest_label: null,
    news_digest: [],
  };
}

function uniqueNewsRows(rows: NewsEvidenceRow[]): NewsEvidenceRow[] {
  const latest = new Map<string, NewsEvidenceRow>();
  for (const row of rows) {
    const key = row.canonical_url || row.evidence_key || row.url ||
      [row.stock_code ?? "", row.title, row.published_at].join(":");
    const previous = latest.get(key);
    if (!previous || Date.parse(row.created_at) > Date.parse(previous.created_at) ||
      (Date.parse(row.created_at) === Date.parse(previous.created_at) && row.run_id > previous.run_id)) {
      latest.set(key, row);
    }
  }
  return [...latest.values()];
}

function eventTypes(row: NewsEvidenceRow): string[] {
  return JSON.parse((row as NewsEvidenceRow & { event_types_json?: string }).event_types_json ?? "[]") as string[];
}

function cautionNews(row: NewsEvidenceRow): boolean {
  return ["Caution", "Negative", "Mixed"].includes(row.sentiment) ||
    ["Caution", "Negative", "Strong Negative"].includes(row.stock_impact) ||
    eventTypes(row).includes("Risk/Caution");
}

function positiveDirectNews(row: NewsEvidenceRow): boolean {
  if (row.source_lane === "top2_search" && row.lineage_type !== "independent") return false;
  return row.relevance === "direct" &&
    (row.sentiment === "Positive" || ["Positive", "Strong Positive"].includes(row.stock_impact));
}

function primaryCautionNews(row: NewsEvidenceRow): boolean {
  if (row.source_lane === "top2_search" && row.lineage_type !== "independent") return false;
  return row.relevance === "direct" && cautionNews(row);
}

function newsDirection(directCount: number, positiveCount: number, primaryCautionCount: number): [string, string] {
  if (positiveCount > 0 && primaryCautionCount > 0) {
    return ["직접 근거 상충", "직접 긍정 뉴스 " + positiveCount + "건과 직접 주의 뉴스 " + primaryCautionCount + "건이 함께 있습니다."];
  }
  if (positiveCount > 0) return ["상승 근거 우세", "직접 긍정 뉴스 " + positiveCount + "건이 직접 주의 뉴스보다 우세합니다."];
  if (primaryCautionCount > 0) return ["하방 위험 우세", "직접 주의 뉴스 " + primaryCautionCount + "건이 있어 리포트 근거를 다시 확인합니다."];
  if (directCount > 0) return ["직접 근거 중립", "직접 연결 뉴스 " + directCount + "건은 있으나 방향 근거가 분명하지 않습니다."];
  return ["직접 근거 부족", "후보와 직접 연결된 방향 근거가 아직 부족합니다."];
}

function newsConnection(directCount: number, cautionCount: number, positiveCount: number, primaryCautionCount: number, marketContextCount: number): [string, string] {
  if (primaryCautionCount > 0 && positiveCount <= 0) return ["주의 뉴스 매칭", "주의/혼합 성격의 뉴스가 후보와 직접 매칭됐습니다."];
  if (directCount > 0) return ["종목 뉴스 매칭", "후보와 직접 매칭된 뉴스 " + directCount + "건이 저장돼 있습니다."];
  if (cautionCount > 0) return ["주의 뉴스 매칭", "주의/혼합 성격의 뉴스가 후보와 매칭됐습니다."];
  if (marketContextCount > 0) return ["시장 맥락 참고", "업종/시장 맥락 뉴스라 종목 직접 근거로 과신하지 않습니다."];
  return ["관련 뉴스 매칭", "후보와 간접 연결된 저장 뉴스가 있습니다."];
}

function newsKind(row: NewsEvidenceRow): string {
  if (row.relevance === "direct") return "종목 직접 매칭";
  if (row.relevance === "market_context") return "시장 맥락";
  return "참고 뉴스";
}

function newsLineageLabel(row: NewsEvidenceRow): string {
  return row.lineage_type === "independent" ? "독립 확인" : row.lineage_type === "report_recap" ? "리포트 재인용" : "독립성 미확인";
}

function newsDigestLabel(row: NewsEvidenceRow, limit = 44): string {
  let text = (row.title || row.summary || "").replace(/\s+/g, " ").trim();
  const stockName = (row.stock_name || "").trim();
  if (stockName) text = text.replace(new RegExp("^" + stockName.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&") + "\\s*[,，:：·-]?\\s*"), "").trim();
  text = text.replace(/^[-:：,，·\s]+|[-:：,，·\s]+$/g, "");
  if (!text) text = row.relevance_reason || row.match_reason || newsKind(row);
  return text.length <= limit ? text : text.slice(0, Math.max(limit - 1, 1)).trimEnd() + "…";
}

function newsDigest(rows: NewsEvidenceRow[], limit: number): Record<string, unknown>[] {
  const result: Record<string, unknown>[] = [];
  const seen = new Set<string>();
  const priority = (row: NewsEvidenceRow) => (row.lineage_type === "independent" ? 0 : 10) +
    (row.relevance === "direct" ? 0 : row.relevance === "market_context" ? 1 : 2);
  const ordered = [...rows].sort((a, b) => priority(a) - priority(b) ||
    Date.parse(b.published_at) - Date.parse(a.published_at) || a.title.localeCompare(b.title));
  for (const row of ordered) {
    const label = newsDigestLabel(row);
    const key = [row.published_at.slice(0, 10), newsKind(row), label].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    result.push({
      date: row.published_at.slice(0, 10),
      stock_name: row.stock_name || row.stock_code || "-",
      label,
      evidence_label: newsKind(row),
      lineage_type: row.lineage_type,
      lineage_label: newsLineageLabel(row),
      relevance: row.relevance,
      source_lane: row.source_lane,
    });
    if (result.length >= Math.max(limit, 0)) break;
  }
  return result;
}

function candidateNewsBadge(rawRows: NewsEvidenceRow[], businessDate: string): Record<string, unknown> {
  const rows = uniqueNewsRows(rawRows);
  if (!rows.length) return emptyNewsBadge();
  const independentRows = rows.filter((row) => row.lineage_type === "independent");
  const directCount = rows.filter((row) => row.relevance === "direct").length;
  const cautionCount = rows.filter(cautionNews).length;
  const positiveCount = rows.filter(positiveDirectNews).length;
  const primaryCautionCount = rows.filter(primaryCautionNews).length;
  const marketContextCount = rows.filter((row) => row.relevance === "market_context").length;
  const independentCount = independentRows.length;
  const recapCount = rows.filter((row) => row.lineage_type === "report_recap").length;
  const unknownCount = rows.length - independentCount - recapCount;
  const referenceDates = rows.map((row) => row.krx_reference_date).filter((date): date is string => !!date);
  const krxStatus = referenceDates.includes(businessDate) ? "exact" : referenceDates.length ? "stale" : "missing";
  let [direction, directionReason] = newsDirection(directCount, positiveCount, primaryCautionCount);
  let [connectionLabel, connectionReason] = newsConnection(directCount, cautionCount, positiveCount, primaryCautionCount, marketContextCount);
  if (!independentRows.length && recapCount > 0) {
    connectionLabel = "리포트 재인용 매칭";
    connectionReason = "후보와 연결된 리포트 재인용 뉴스 " + recapCount + "건이 저장돼 있습니다.";
    direction = "리포트 재인용 흐름";
    directionReason = "리포트 내용을 재인용한 뉴스 흐름이며 별도 독립 근거로 중복 계산하지 않습니다.";
  } else if (!independentRows.length) {
    connectionLabel = "종목 뉴스 매칭";
    connectionReason = "후보와 직접 매칭된 뉴스 " + rows.length + "건이 저장돼 있으며 출처 계보는 확인 전입니다.";
    direction = "출처 계보 확인 전";
    directionReason = "종목 매칭은 확인됐고 독립 원출처 여부는 별도 메타데이터로 남깁니다.";
  }
  const orderedRows = [...rows].sort((a, b) => {
    const priority = (row: NewsEvidenceRow) => row.relevance === "direct" ? 0 : row.relevance === "indirect" ? 1 : 2;
    return priority(a) - priority(b) || Date.parse(a.created_at) - Date.parse(b.created_at) || a.title.localeCompare(b.title);
  });
  const topTitle = uniqueText(orderedRows.map((row) => row.title), 1)[0] ?? null;
  const digest = newsDigest(rows, 3);
  return {
    available: true,
    display_label: connectionLabel,
    reason: topTitle || "저장 뉴스 observation이 같은 후보와 연결됩니다.",
    direct_count: directCount,
    positive_direct_count: positiveCount,
    primary_caution_count: primaryCautionCount,
    caution_count: cautionCount,
    market_context_count: marketContextCount,
    independent_count: independentCount,
    report_recap_count: recapCount,
    unknown_count: unknownCount,
    krx_reference_status: krxStatus,
    observed_at: rows.map((row) => row.created_at).sort().at(-1) ?? null,
    evidence_direction: direction,
    evidence_direction_reason: directionReason,
    top_title: topTitle,
    digest_label: (digest[0]?.label as string | undefined) ?? null,
    news_digest: digest,
    connection_label: connectionLabel,
    connection_reason: connectionReason,
  };
}

function brokerCountFromDisplay(value: string | null): number {
  const brokers = (value ?? "").split(",")
    .map((part) => part.trim().replace(/\(\d+\)$/, "").trim())
    .filter(Boolean);
  return new Set(brokers).size;
}

function targetRange(summary: SummaryRow): { min: number | null; max: number | null; available: boolean } {
  return { min: summary.target_price_min, max: summary.target_price_max, available: summary.target_price_min !== null || summary.target_price_max !== null };
}

function emptyTargetRevision(currentMin: number | null, currentMax: number | null, reason: string): Record<string, unknown> {
  return {
    available: false, reason, current_min: currentMin, current_max: currentMax, previous_date: null,
    previous_min: null, previous_max: null, direction: null, direction_label: null,
  };
}

function targetRevision(
  previous: { previous_date: string; previous_min: number; previous_max: number; previous_report_count: number; previous_broker_count: number } | undefined,
  currentMin: number | null,
  currentMax: number | null,
): Record<string, unknown> {
  const low = currentMin ?? currentMax;
  const high = currentMax ?? currentMin;
  if (low === null || high === null) return emptyTargetRevision(currentMin, currentMax, "missing_current_target");
  if (!previous) return emptyTargetRevision(currentMin, currentMax, "no_previous_target");
  const currentMid = (Number(low) + Number(high)) / 2;
  const previousMid = (previous.previous_min + previous.previous_max) / 2;
  const direction = currentMid > previousMid ? "up" : currentMid < previousMid ? "down" : "flat";
  return {
    available: true,
    current_min: currentMin,
    current_max: currentMax,
    previous_date: previous.previous_date,
    previous_min: previous.previous_min,
    previous_max: previous.previous_max,
    previous_report_count: previous.previous_report_count,
    previous_broker_count: previous.previous_broker_count,
    direction,
    direction_label: direction === "up" ? "상향" : direction === "down" ? "하향" : "유지",
  };
}

function recentIntensity(summary: SummaryRow, aggregate: { report_count: number; active_dates: number; broker_count: number } | undefined, dates: string[]): Record<string, unknown> {
  if (!aggregate) return {
    available: false,
    one_day_report_count: summary.mention_count,
    five_business_day_report_count: summary.mention_count,
    five_business_day_active_dates: summary.mention_count ? 1 : 0,
    five_business_day_broker_count: 0,
    window_business_dates: dates,
  };
  return {
    available: aggregate.report_count > 0,
    one_day_report_count: summary.mention_count,
    five_business_day_report_count: aggregate.report_count,
    five_business_day_active_dates: aggregate.active_dates,
    five_business_day_broker_count: aggregate.broker_count,
    window_business_dates: dates,
  };
}

function roundHalfEven(value: number, digits = 2): number {
  if (!Number.isFinite(value)) return value;
  const scale = 10 ** digits;
  const scaled = Math.abs(value) * scale;
  const floor = Math.floor(scaled);
  const fraction = scaled - floor;
  const epsilon = Number.EPSILON * Math.max(1, scaled) * 2;
  const rounded = fraction > 0.5 + epsilon ? floor + 1
    : fraction < 0.5 - epsilon ? floor
      : floor % 2 === 0 ? floor : floor + 1;
  return Math.sign(value) * rounded / scale;
}

function percent(numerator: number, denominator: number): number | null {
  return denominator === 0 ? null : roundHalfEven((numerator / denominator) * 100, 2);
}

function formatAmount(value: number): string {
  const amount = Math.abs(value);
  if (amount >= 1_000_000_000_000) return new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1, roundingMode: "halfEven", useGrouping: false }).format(amount / 1_000_000_000_000) + "조";
  if (amount >= 100_000_000) return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, roundingMode: "halfEven", useGrouping: false }).format(amount / 100_000_000) + "억";
  return new Intl.NumberFormat("en-US").format(amount) + "원";
}

function flowVolume(value: number | null): string {
  if (value === null) return "-";
  if (value > 0) return "순매수 " + new Intl.NumberFormat("en-US").format(value) + "주";
  if (value < 0) return "순매도 " + new Intl.NumberFormat("en-US").format(Math.abs(value)) + "주";
  return "중립";
}

function sumFlowAmount(rows: StockFlowRow[], types: Set<string>): number | null {
  const values = rows.filter((row) => types.has(row.investor_type) && row.net_buy_amount !== null)
    .map((row) => row.net_buy_amount as number);
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function uniqueText(values: string[], limit: number): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const text = value.trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    result.push(text);
    if (result.length >= Math.max(limit, 0)) break;
  }
  return result;
}


function regularSessionCodes(database: DatabaseSync, businessDate: string): string[] {
  const events = database.prepare(`
    SELECT event_time, id, detail
    FROM operation_events
    WHERE component = 'poll-news' AND event_type = 'scheduled-collect'
      AND business_date = ? AND status = 'success'
    ORDER BY event_time DESC, id DESC
    LIMIT 20
  `).all(businessDate) as unknown as { detail: string | null }[];
  for (const event of events) {
    for (const part of String(event.detail ?? "").split(";")) {
      const separator = part.indexOf("=");
      if (separator < 0 || part.slice(0, separator).trim() !== "target_stock_codes") continue;
      const unique: string[] = [];
      const seen = new Set<string>();
      for (const raw of part.slice(separator + 1).split(",")) {
        const code = raw.trim();
        if (!code || seen.has(code)) continue;
        seen.add(code);
        unique.push(code);
      }
      if (unique.length) return unique.slice(0, 2);
    }
  }
  return [];
}

function eligibleCandidate(row: Record<string, unknown>): boolean {
  const report = row.report_summary as Record<string, unknown>;
  const news = row.news_observation_badge as Record<string, unknown>;
  const matched = ["direct_count", "caution_count", "market_context_count", "independent_count", "report_recap_count", "unknown_count"]
    .reduce((sum, key) => sum + Number(news[key] ?? 0), 0);
  const flow = row.stock_flow_reference as Record<string, unknown>;
  return Number(report.report_count ?? 0) >= 2 || matched > 0 || flow.available === true;
}

function intradayReferencePlaceholder(): Record<string, unknown> {
  return {
    available: false,
    source_configured: false,
    read_only: true,
    live_fetch: false,
    scope: "top_2_priority_candidates",
    cadence_minutes: 5,
    reference_time: null,
    price: null,
    change_percent: null,
    turnover: null,
    affects_ordering: false,
    notice: "장중 실시간 참고 소스가 아직 확정되지 않았습니다.",
  };
}

type KeywordRule = { aliases: string[]; canonical: string; kind: string; rank: number; types?: string[] };
const KEYWORD_RULES: KeywordRule[] = [
  { aliases: ["HBM4", "HBM 4"], canonical: "HBM4", kind: "product", rank: 10 },
  { aliases: ["K9 자주포"], canonical: "K9 자주포", kind: "product", rank: 10 },
  { aliases: ["로카모빌리티"], canonical: "로카모빌리티", kind: "counterparty", rank: 10 },
  { aliases: ["미국 반도체 수출 규제"], canonical: "미국 반도체 수출 규제", kind: "policy", rank: 10 },
  { aliases: ["염수 리튬"], canonical: "염수 리튬", kind: "product", rank: 10 },
  { aliases: ["북미 ESS"], canonical: "북미 ESS", kind: "industry", rank: 10 },
  { aliases: ["AI 반도체"], canonical: "AI 반도체", kind: "technology", rank: 10 },
  { aliases: ["LNG선"], canonical: "LNG선", kind: "product", rank: 10 },
  { aliases: ["엔비디아"], canonical: "엔비디아", kind: "counterparty", rank: 20 },
  { aliases: ["폴란드 군비청"], canonical: "폴란드 군비청", kind: "counterparty", rank: 20 },
  { aliases: ["로카모빌리티 인수"], canonical: "로카모빌리티 인수", kind: "event", rank: 20 },
  { aliases: ["중국 공장 장비 반입"], canonical: "중국 공장 장비 반입", kind: "event", rank: 20 },
  { aliases: ["아르헨티나 염수 리튬 상업 생산"], canonical: "아르헨티나 염수 리튬 상업 생산", kind: "event", rank: 20 },
  { aliases: ["하이퍼클로바X"], canonical: "하이퍼클로바X", kind: "product", rank: 20 },
  { aliases: ["메모리 업황 개선"], canonical: "메모리 업황 개선", kind: "market_theme", rank: 20 },
  { aliases: ["ESS 수요"], canonical: "ESS 수요", kind: "market_theme", rank: 20 },
  { aliases: ["고객 인증"], canonical: "고객 인증", kind: "event", rank: 20 },
  { aliases: ["메탄올 추진선"], canonical: "메탄올 추진선", kind: "technology", rank: 20 },
  { aliases: ["HBM4 공급 확대", "HBM 4 공급 확대"], canonical: "HBM4 공급 확대", kind: "event", rank: 30, types: ["news"] },
  { aliases: ["K9 자주포 추가 수주"], canonical: "K9 자주포 추가 수주", kind: "event", rank: 30 },
  { aliases: ["모빌리티 데이터"], canonical: "모빌리티 데이터", kind: "industry", rank: 30 },
  { aliases: ["첨단 반도체 장비"], canonical: "첨단 반도체 장비", kind: "technology", rank: 30 },
  { aliases: ["리튬 가격"], canonical: "리튬 가격", kind: "market_theme", rank: 30 },
  { aliases: ["기업용 서비스 출시"], canonical: "기업용 서비스 출시", kind: "event", rank: 30 },
  { aliases: ["AI 메모리"], canonical: "AI 메모리", kind: "technology", rank: 30, types: ["report"] },
  { aliases: ["기업 검색"], canonical: "기업 검색", kind: "product", rank: 30 },
  { aliases: ["카타르 LNG 프로젝트"], canonical: "카타르 LNG 프로젝트", kind: "event", rank: 30 },
  { aliases: ["친환경 선박 사이클"], canonical: "친환경 선박 사이클", kind: "market_theme", rank: 40 },
];

function normalizeIdentity(value: string): string {
  return value.replace(/\s+/g, "").toLowerCase();
}

function extractKeywords(title: string, type: "report" | "news"): KeywordRule[] {
  const normalized = normalizeIdentity(title.trim());
  const rules = KEYWORD_RULES.filter((rule) =>
    (!rule.types || rule.types.includes(type)) && rule.aliases.some((alias) => normalized.includes(normalizeIdentity(alias))),
  ).sort((a, b) => {
    const sourcePosition = (rule: KeywordRule) => Math.min(...rule.aliases
      .map((alias) => normalized.indexOf(normalizeIdentity(alias)))
      .filter((position) => position >= 0));
    return a.rank - b.rank || sourcePosition(a) - sourcePosition(b) || a.canonical.toLowerCase().localeCompare(b.canonical.toLowerCase());
  });
  return rules.slice(0, 5).filter((rule) => normalized.includes(normalizeIdentity(rule.canonical)));
}

function researchQueries(stockName: string, accepted: KeywordRule[]): string[] {
  const unique: KeywordRule[] = [];
  const seen = new Set<string>();
  for (const rule of accepted) {
    const key = normalizeIdentity(rule.canonical);
    if (key === normalizeIdentity(stockName) || seen.has(key)) continue;
    seen.add(key);
    unique.push(rule);
  }
  if (!unique.length) return [];
  const candidates = [stockName.trim() + " " + unique[0].canonical];
  let pairIndex: number | null = null;
  for (let index = 1; index < unique.length; index += 1) {
    if (unique[0].kind === "counterparty" && unique[index].kind === "event" &&
        normalizeIdentity(unique[index].canonical).includes(normalizeIdentity(unique[0].canonical))) continue;
    pairIndex = index;
    break;
  }
  if (pairIndex !== null) {
    let first = unique[0]; let second = unique[pairIndex];
    if (first.kind === "product" && second.kind === "counterparty") [first, second] = [second, first];
    candidates.push([stockName.trim(), first.canonical, second.canonical].join(" "));
  }
  if (unique.length >= 4) {
    const used = new Set([0, pairIndex]);
    const breadthIndex = unique.findIndex((_item, index) => index > 0 && !used.has(index));
    if (breadthIndex >= 0) candidates.push(stockName.trim() + " " + unique[breadthIndex].canonical);
  }
  const result: string[] = [];
  const identities = new Set<string>();
  for (const query of candidates) {
    const identity = normalizeIdentity(query);
    if (identities.has(identity)) continue;
    identities.add(identity);
    result.push(query);
    if (result.length === 3) break;
  }
  return result;
}

function candidateResearchFocus(stockName: string, stockCode: string, reports: ReportRow[], newsTitle: string | null): Record<string, unknown> {
  const documents: Array<{ type: "report" | "news"; title: string; sourceUrl: string | null }> = [];
  for (const report of reports) if (report.stock_code === stockCode) documents.push({ type: "report", title: report.title, sourceUrl: report.source_url });
  if (newsTitle) documents.push({ type: "news", title: newsTitle, sourceUrl: null });
  const items: Record<string, unknown>[] = [];
  const seen = new Set<string>();
  for (const document of documents) {
    const title = document.title.trim();
    if (!title || title.includes("�") || !stockName.trim()) continue;
    const keywords = extractKeywords(title, document.type);
    const queries = researchQueries(stockName, keywords);
    const candidates = queries.length ? queries : [stockName + " " + title];
    for (const query of candidates) {
      const identity = query.toLowerCase().replace(/\s+/g, "");
      if (seen.has(identity)) continue;
      seen.add(identity);
      const item: Record<string, unknown> = {
        topic: queries.length ? keywords.slice(0, 2).map((rule) => rule.canonical).join(" · ") : title,
        source_title: title,
        source_kind: document.type === "report" ? "리포트" : "저장 뉴스",
        basis: queries.length ? "keywords" : "source_title",
        query,
        search_url: "https://search.naver.com/search.naver?" + new URLSearchParams({ where: "news", query }).toString(),
      };
      if (document.type === "report" && document.sourceUrl) item.source_url = document.sourceUrl;
      items.push(item);
      if (items.length === 3) break;
    }
    if (items.length === 3) break;
  }
  return { available: items.length > 0, items, notice: "원문에서 뽑은 확인 주제입니다. 검색 결과는 별도로 확인하세요." };
}


function marketReferenceDto(row: StockMarketRow | undefined): Record<string, unknown> | null {
  if (!row) return null;
  return {
    business_date: row.business_date,
    market: row.market,
    close_price: row.close_price,
    change_percent: row.change_percent,
    volume: row.volume,
    turnover: row.turnover,
    fetched_at: row.fetched_at,
  };
}

function publicCandidateRow(
  summary: SummaryRow,
  brokerCount: number,
  target: { min: number | null; max: number | null; available: boolean },
  revision: Record<string, unknown>,
  intensity: Record<string, unknown>,
  targetProgress: Record<string, unknown>,
  market: StockMarketRow | undefined,
  stockFlow: StockFlowRow[],
  news: Record<string, unknown>,
  baseline: Record<string, unknown>,
  event: Record<string, unknown>,
  flowWindow: Record<string, unknown>,
  priceVolume: Record<string, unknown>,
  profile: Record<string, unknown>,
  value: Record<string, unknown>,
): Record<string, unknown> {
  const publicRevision = { ...revision };
  delete publicRevision.previous_broker_count;
  const publicIntensity = { ...intensity };
  delete publicIntensity.five_business_day_broker_count;
  const publicValue = { ...value };
  delete publicValue.rank_reference_available;
  delete publicValue.sort_value_signal;
  return {
    business_date: summary.business_date,
    stock_code: summary.stock_code ?? "",
    stock_name: summary.stock_name,
    observation_priority: value.observation_priority,
    value_profile: publicValue,
    why_notable: profile.why_notable,
    missing_information: profile.missing_information,
    evidence_layers: evidenceLayers(
      profile.why_notable,
      supportEvidence(market, priceVolume),
      profile.missing_information,
    ),
    report_summary: {
      report_count: summary.mention_count,
      target_price_min: summary.target_price_min,
      target_price_max: summary.target_price_max,
    },
    target_price_range: target,
    report_intensity: publicIntensity,
    target_price_revision: publicRevision,
    target_price_progress: targetProgress,
    market_reference: marketReferenceDto(market),
    stock_flow_reference: stockFlowTotals(stockFlow),
    value_context: valueContext(summary.business_date, market, stockFlowTotals(stockFlow), news, baseline),
    flow_window_reference: flowWindow,
    price_volume_reference: priceVolume,
    news_observation_badge: news,
    toss_baseline_reference: baseline,
    event_reaction: event,
    _candidate_profile: profile,
    _sort_value_signal: Number(value.sort_value_signal ?? 0),
    _sort_signal: Number(profile.sort_signal ?? 0),
    _sort_density: Number(profile.sort_density ?? 0),
    _broker_count: brokerCount,
  };
}

function sortCandidates(rows: Record<string, unknown>[]): void {
  rows.sort((a, b) => {
    const eligible = Number(eligibleCandidate(b)) - Number(eligibleCandidate(a));
    if (eligible) return eligible;
    const av = a.value_profile as Record<string, unknown>;
    const bv = b.value_profile as Record<string, unknown>;
    const fields: Array<[number, number]> = [
      [Number(bv.sort_value_signal ?? 0), Number(av.sort_value_signal ?? 0)],
      [Number(b._sort_signal ?? 0), Number(a._sort_signal ?? 0)],
      [Number(b._sort_density ?? 0), Number(a._sort_density ?? 0)],
      [Number((b.report_summary as Record<string, unknown>).report_count ?? 0), Number((a.report_summary as Record<string, unknown>).report_count ?? 0)],
      [Number(b._broker_count ?? 0), Number(a._broker_count ?? 0)],
      [Number(((b.market_reference as Record<string, unknown> | null)?.turnover) ?? 0), Number(((a.market_reference as Record<string, unknown> | null)?.turnover) ?? 0)],
    ];
    for (const [left, right] of fields) if (left !== right) return left - right;
    return String(b.stock_code ?? "").localeCompare(String(a.stock_code ?? ""));
  });
}

function buildCandidateEvidenceSnapshot(
  database: DatabaseSync,
  businessDate: string,
  limit: number,
  now: Date,
  timezone: string,
  holidays: Set<string>,
): CandidateEvidenceResponse {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid candidate evidence date");
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) throw new RangeError("Invalid candidate evidence limit");

  const summaries = readSummaries(database, businessDate);
  const stockCodes = uniqueStockCodes(summaries);
  const reports = readReportsForDate(database, businessDate);
  const reportsByCode = new Map<string, ReportRow[]>();
  for (const report of reports) {
    if (!report.stock_code) continue;
    const list = reportsByCode.get(report.stock_code) ?? [];
    list.push(report);
    reportsByCode.set(report.stock_code, list);
  }
  const namesByCode = new Map(summaries.filter((item) => item.stock_code).map((item) => [item.stock_code as string, item.stock_name]));
  const marketRefs = readMarketReferences(database, businessDate, stockCodes);
  const marketFlows = readMarketFlows(database, businessDate);
  const recentDates = recentBusinessDates(businessDate, 5, holidays);
  const reportContext = readReportContext(database, businessDate, stockCodes, recentDates, summaries);
  const flowRows = readStockFlows(database, businessDate, stockCodes);
  const marketHistory = readMarketHistory(database, businessDate, stockCodes);
  const marketIndexes = readMarketIndexes(database, businessDate);
  const tossBaselines = readTossBaselines(database, businessDate, stockCodes);
  const newsBadges = readNews(database, businessDate, stockCodes, namesByCode);
  const indexBySeries = marketIndexes;
  const rows: Record<string, unknown>[] = [];

  for (const summary of summaries) {
    const stockCode = summary.stock_code ?? "";
    const reportsForCode = reportsByCode.get(stockCode) ?? [];
    let brokerCount = new Set(reportsForCode.map((item) => item.broker_name.trim()).filter(Boolean)).size;
    if (brokerCount <= 0) brokerCount = brokerCountFromDisplay(summary.broker_display);
    const target = targetRange(summary);
    const market = marketRefs.get(stockCode);
    const sameDayFlow = flowRows.sameDay.get(stockCode) ?? [];
    const news = newsBadges.get(stockCode) ?? emptyNewsBadge();
    const baseline = tossBaselineReference(tossBaselines.get(stockCode));
    const revision = targetRevision(
      reportContext.previousTargets.get(stockCode),
      summary.target_price_min,
      summary.target_price_max,
    );
    const intensity = recentIntensity(summary, reportContext.intensity.get(stockCode), recentDates);
    const history = marketHistory.get(stockCode) ?? [];
    const marketSeries = [...history].filter((item) => item.business_date >= businessDate).sort((a, b) => a.business_date.localeCompare(b.business_date)).slice(0, 21);
    const priceHistory = [...history].filter((item) => item.business_date <= businessDate).sort((a, b) => b.business_date.localeCompare(a.business_date)).slice(0, 252);
    const firstTargetDate = reportContext.firstTargetDates.get(stockCode) ?? null;
    const baselineMarket = firstTargetDate ? history.find((item) => item.business_date === firstTargetDate) : undefined;
    const flowWindowRows = flowRows.history.get(stockCode) ?? [];
    const flowWindow = stockFlowWindow(summary, flowWindowRows);
    const priceVolume = priceVolumeReference(summary, priceHistory);
    const profile = candidateProfile(summary, brokerCount, target, market, sameDayFlow, revision, flowWindow, priceVolume);
    const value = valueProfile(profile, news, baseline, market, sameDayFlow, now, timezone, businessDate);
    const event = eventReaction(businessDate, history, indexBySeries.get(
      (history.find((item) => item.business_date === businessDate)?.market ?? "").toUpperCase().includes("KOSDAQ") ? "KOSDAQ" : "KOSPI",
    ) ?? []);
    const targetProgress = targetPriceProgress(summary, market, firstTargetDate, baselineMarket, marketSeries);
    const row = publicCandidateRow(
      summary, brokerCount, target, revision, intensity, targetProgress, market, sameDayFlow,
      news, baseline, event, flowWindow, priceVolume, profile, value,
    );
    rows.push(row);
  }

  sortCandidates(rows);
  const closeRanked = rows.filter(eligibleCandidate).slice(0, 2);
  const regularCodes = regularSessionCodes(database, businessDate);
  const rowsByCode = new Map(rows.map((row) => [String(row.stock_code ?? ""), row]));
  const regularRows = regularCodes.map((code) => rowsByCode.get(code)).filter((row): row is Record<string, unknown> => !!row);
  const selectedRows = regularRows.length ? regularRows : closeRanked;
  const selectionBasis = regularRows.length ? "regular_session_news_cohort" : "stored_candidate_evidence";
  const selected = new Set(selectedRows);
  const outputRows = [...selectedRows, ...rows.filter((row) => !selected.has(row))].slice(0, limit);
  const selectedCodes = selectedRows.map((row) => String(row.stock_code ?? ""));
  const closeCodes = closeRanked.map((row) => String(row.stock_code ?? ""));
  const hasCloseSnapshot = tossBaselines.size > 0;
  const closeReassessment = {
    available: hasCloseSnapshot && closeRanked.length > 0,
    changed: hasCloseSnapshot && regularRows.length > 0 &&
      (closeCodes.length !== selectedCodes.length || closeCodes.some((code, index) => code !== selectedCodes[index])),
    basis: "Toss 20:00 저장값",
    notice: "정규장 Top2는 유지하고 종가 기준 변화는 다음 영업일 참고로 분리합니다.",
    rows: closeRanked.map((row) => {
      const stockCode = String(row.stock_code ?? "");
      const baseline = row.toss_baseline_reference as Record<string, unknown>;
      const market = row.market_reference as Record<string, unknown> | null;
      const flow = row.stock_flow_reference as Record<string, unknown>;
      return {
        stock_code: stockCode,
        stock_name: String(row.stock_name ?? ""),
        observation_priority: row.observation_priority,
        why_notable: [...(row.why_notable as string[])],
        last_price: baseline.last_price,
        change_percent: market?.change_percent ?? null,
        stock_flow_available: flow.available === true,
      };
    }),
  };

  const picked: Record<string, unknown>[] = [];
  for (const row of outputRows) {
    const item: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(row)) {
      if (key.startsWith("_")) continue;
      item[key] = value;
    }
    const isSelected = selected.has(row);
    item.selected = isSelected;
    if (isSelected) {
      item.intraday_reference = intradayReferencePlaceholder();
      item.research_focus = candidateResearchFocus(
        String(item.stock_name),
        String(item.stock_code),
        reportsByCode.get(String(item.stock_code)) ?? [],
        String((item.news_observation_badge as Record<string, unknown>).top_title ?? "") || null,
      );
    }
    picked.push(item);
  }

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    available: picked.length > 0,
    data_scope: "stored_report_toss_evidence",
    live_fetch: false,
    scoring: false,
    recommendation: false,
    selection_basis: selectionBasis,
    close_reassessment: closeReassessment,
    display_policy: "관찰 후보는 저장된 리포트와 Toss 저장/수급 참고값을 확인용으로 묶어 보여줍니다.",
    notice: "오늘의 관찰 후보는 저장된 리포트와 Toss 저장 수급 참고값 기준입니다. 실시간 시세가 아닙니다.",
    market_flow_context: sortedMarketFlows(marketFlows),
    rows: picked as CandidateEvidenceRow[],
  };
}

export function parseCandidateEvidenceLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? DEFAULT_LIMIT : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, MAX_LIMIT)) : DEFAULT_LIMIT;
}

export function buildCandidateEvidenceSnapshotFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  limit = 8,
  now = new Date(),
): CandidateEvidenceResponse {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return buildCandidateEvidenceSnapshot(database, businessDate, limit, now, timezone, holidayOverrides());
}

export function getCandidateEvidenceSnapshot(businessDate: string, limit = 8, now = new Date()): CandidateEvidenceResponse {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      return buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, limit, now);
    } finally {
      database.exec("ROLLBACK");
    }
  });
}




function flowWindowPersistence(rows: StockFlowRow[], types: Set<string>): Record<string, unknown> {
  const byDate = new Map<string, number>();
  for (const row of rows) {
    if (!types.has(row.investor_type) || row.net_buy_amount === null) continue;
    byDate.set(row.business_date, (byDate.get(row.business_date) ?? 0) + row.net_buy_amount);
  }
  const ordered = [...byDate.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  const nonzero = ordered.map(([date, amount]) => ({ date, amount, direction: Math.sign(amount) })).filter((item) => item.direction !== 0);
  if (!nonzero.length) return {
    available: false, direction: null, direction_label: "중립", streak_days: 0, turn_date: null,
    turn_available: false, latest_amount: null,
  };
  const latest = nonzero[0];
  const streak = [latest];
  for (const item of nonzero.slice(1)) {
    if (item.direction !== latest.direction) break;
    streak.push(item);
  }
  const oldest = streak.reduce((date, item) => item.date < date ? item.date : date, streak[0].date);
  const priorOpposite = nonzero.some((item) => item.date < oldest && item.direction !== latest.direction);
  return {
    available: true,
    direction: latest.direction,
    direction_label: latest.direction > 0 ? "순유입" : "순유출",
    streak_days: streak.length,
    turn_date: priorOpposite ? oldest : null,
    turn_available: priorOpposite,
    latest_amount: latest.amount,
  };
}

function flowPersistenceText(items: Array<[string, Record<string, unknown>]>): string {
  const parts: string[] = [];
  for (const [label, item] of items) {
    if (item.available !== true) continue;
    const direction = String(item.direction_label || "중립");
    const days = Number(item.streak_days || 0);
    if (days < 2) continue;
    if (item.turn_date) parts.push(label + " " + direction + " 전환 " + String(item.turn_date).slice(5).replaceAll("-", ".") + "부터 " + days + "일");
    else parts.push(label + " " + direction + " 연속 " + days + "일");
  }
  return parts.length ? " · " + parts.join(" · ") : "";
}

function stockFlowWindow(summary: SummaryRow, rows: StockFlowRow[]): Record<string, unknown> {
  if (!summary.stock_code) return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code };
  const dates = [...new Set(rows.map((row) => row.business_date))].sort((a, b) => b.localeCompare(a));
  if (!dates.length) return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code, windows: [] };
  const windows = [5, 10, 20, 31].map((days) => {
    const picked = new Set(dates.slice(0, days));
    const selected = rows.filter((row) => picked.has(row.business_date));
    return {
      days,
      observed_days: picked.size,
      individual_net_buy_amount: sumFlowAmount(selected, new Set(["개인"])),
      foreign_net_buy_amount: sumFlowAmount(selected, new Set(["외국인"])),
      institution_net_buy_amount: sumFlowAmount(selected, new Set(["기관", "기관합계"])),
    };
  });
  const latest = windows[0];
  const persistence = {
    foreign: flowWindowPersistence(rows, new Set(["외국인"])),
    institution: flowWindowPersistence(rows, new Set(["기관", "기관합계"])),
  };
  return {
    available: true,
    stock_name: summary.stock_name,
    stock_code: summary.stock_code,
    reference_date: dates[0],
    observed_days: dates.length,
    windows,
    persistence,
    display: summary.stock_name + " 외국인 " + flowVolume(latest.foreign_net_buy_amount as number | null) +
      " · 기관 " + flowVolume(latest.institution_net_buy_amount as number | null) +
      flowPersistenceText([["외국인", persistence.foreign], ["기관", persistence.institution]]),
  };
}

function closePositionPercent(rows: StockMarketRow[], currentPrice: number): number | null {
  const closes = rows.map((row) => row.close_price).filter((value): value is number => value !== null);
  if (closes.length < 2) return null;
  const low = Math.min(...closes);
  const high = Math.max(...closes);
  if (high === low) return 50;
  return roundHalfEven(((currentPrice - low) / (high - low)) * 100, 1);
}

function returnPercent(rows: StockMarketRow[], currentPrice: number, offset: number): number | null {
  if (rows.length <= offset || rows[offset].close_price === null || rows[offset].close_price === 0) return null;
  return roundHalfEven(((currentPrice - (rows[offset].close_price as number)) / (rows[offset].close_price as number)) * 100, 2);
}

function volumeMultiple(rows: StockMarketRow[], currentVolume: number | null): number | null {
  const volumes = rows.map((row) => row.volume).filter((value): value is number => value !== null && value > 0);
  if (currentVolume === null || currentVolume <= 0 || !volumes.length) return null;
  const average = volumes.reduce((sum, value) => sum + value, 0) / volumes.length;
  return average > 0 ? roundHalfEven(currentVolume / average, 2) : null;
}

function formatOptionalPercent(value: number | null, digits = 1, signed = false): string {
  if (value === null) return "-";
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    roundingMode: "halfEven",
    signDisplay: signed && value > 0 ? "always" : "auto",
  }).format(value);
  return formatted + "%";
}

function formatOptionalMultiple(value: number | null): string {
  return value === null ? "-" : new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2, roundingMode: "halfEven" }).format(value) + "배";
}

function priceVolumeReference(summary: SummaryRow, rows: StockMarketRow[]): Record<string, unknown> {
  if (!summary.stock_code) return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code };
  const ordered = [...rows].filter((row) => row.business_date <= summary.business_date).sort((a, b) => b.business_date.localeCompare(a.business_date)).slice(0, 252);
  const current = ordered[0];
  if (!current || current.close_price === null) return { available: false, stock_name: summary.stock_name, stock_code: summary.stock_code };
  const position20 = closePositionPercent(ordered.slice(0, 20), current.close_price);
  const position60 = closePositionPercent(ordered.slice(0, 60), current.close_price);
  const position52w = ordered.length >= 120 ? closePositionPercent(ordered.slice(0, 252), current.close_price) : null;
  const return5d = returnPercent(ordered, current.close_price, 4);
  const return20d = returnPercent(ordered, current.close_price, 19);
  const volume20 = volumeMultiple(ordered.slice(0, 20), current.volume);
  const parts = [summary.stock_name + " 20일 위치 " + formatOptionalPercent(position20)];
  if (position52w !== null) parts.push("52주 위치 " + formatOptionalPercent(position52w));
  parts.push("5일 " + formatOptionalPercent(return5d, 2, true));
  parts.push("거래량 " + formatOptionalMultiple(volume20));
  return {
    available: true,
    stock_name: summary.stock_name,
    stock_code: summary.stock_code,
    reference_date: current.business_date,
    close_price: current.close_price,
    change_percent: current.change_percent,
    turnover: current.turnover,
    turnover_display: current.turnover === null ? "저장값 없음" : formatAmount(current.turnover),
    close_position_20d_percent: position20,
    close_position_60d_percent: position60,
    close_position_52w_percent: position52w,
    close_position_52w_observed_days: Math.min(ordered.length, 252),
    return_5d_percent: return5d,
    return_20d_percent: return20d,
    volume_multiple_20d: volume20,
    display: parts.join(" · "),
  };
}

function targetProgressPercent(currentPrice: number, baselinePrice: number, targetPrice: number): number | null {
  const denominator = targetPrice - baselinePrice;
  const numerator = currentPrice - baselinePrice;
  if (denominator === 0) return numerator === 0 ? 0 : null;
  return percent(numerator, denominator);
}

function targetProgressNotice(baselinePrice: number | null, targetMin: number, targetMax: number): string | null {
  if (baselinePrice === null) return null;
  if (baselinePrice < targetMin) return "baseline_below_target_range";
  if (baselinePrice > targetMax) return "baseline_above_target_range";
  return "baseline_inside_target_range";
}

function emptyTargetValidation(reason: string): Record<string, unknown> {
  return {
    validation_available: false,
    validation_window_days: null,
    max_progress_to_min_percent: null,
    max_progress_to_max_percent: null,
    hit_min_horizon_days: null,
    hit_max_horizon_days: null,
    validation_notice: reason,
  };
}

function targetValidation(
  marketSeries: StockMarketRow[],
  baselinePrice: number | null,
  targetMin: number,
  targetMax: number,
  progressNotice: string | null,
): Record<string, unknown> {
  if (baselinePrice === null) return emptyTargetValidation("missing_baseline_price");
  if (progressNotice !== "baseline_below_target_range") return emptyTargetValidation(progressNotice || "unsupported_target_direction");
  const observed = marketSeries.map((item, index) => ({ index, close: item.close_price })).filter((row) => row.close !== null);
  if (!observed.length) return emptyTargetValidation("missing_market_series");
  const progressMin = observed.map((row) => targetProgressPercent(row.close as number, baselinePrice, targetMin)).filter((value): value is number => value !== null);
  const progressMax = observed.map((row) => targetProgressPercent(row.close as number, baselinePrice, targetMax)).filter((value): value is number => value !== null);
  const hitMin = observed.find((row) => (row.close as number) >= targetMin)?.index ?? null;
  const hitMax = observed.find((row) => (row.close as number) >= targetMax)?.index ?? null;
  return {
    validation_available: !!(progressMin.length || progressMax.length || hitMin !== null || hitMax !== null),
    validation_window_days: Math.max(...observed.map((row) => row.index)),
    max_progress_to_min_percent: progressMin.length ? Math.max(...progressMin) : null,
    max_progress_to_max_percent: progressMax.length ? Math.max(...progressMax) : null,
    hit_min_horizon_days: hitMin,
    hit_max_horizon_days: hitMax,
    validation_notice: "stored_window_only",
  };
}

function targetPriceProgress(
  summary: SummaryRow,
  market: StockMarketRow | undefined,
  firstTargetDate: string | null | undefined,
  baselineMarket: StockMarketRow | undefined,
  marketSeries: StockMarketRow[],
): Record<string, unknown> {
  const targets = [summary.target_price_min, summary.target_price_max].filter((value): value is number => value !== null);
  if (!summary.stock_code || !targets.length || !market || market.close_price === null) {
    return {
      available: false,
      gap_available: false,
      progress_available: false,
      ...emptyTargetValidation("missing_target_or_market_reference"),
      policy: "range_only",
      notice: "목표가, 종목코드, 또는 선택일 Toss 저장 가격이 없어 계산하지 않습니다.",
    };
  }
  const targetMin = Math.min(...targets);
  const targetMax = Math.max(...targets);
  const currentPrice = market.close_price;
  const baselinePrice = baselineMarket?.close_price ?? null;
  const gapValues = [percent(targetMin - currentPrice, currentPrice), percent(targetMax - currentPrice, currentPrice)].filter((value): value is number => value !== null);
  const progressMin = baselinePrice === null ? null : targetProgressPercent(currentPrice, baselinePrice, targetMin);
  const progressMax = baselinePrice === null ? null : targetProgressPercent(currentPrice, baselinePrice, targetMax);
  const validProgress = [progressMin, progressMax].filter((value): value is number => value !== null);
  const notice = targetProgressNotice(baselinePrice, targetMin, targetMax);
  return {
    available: !!(gapValues.length || validProgress.length),
    gap_available: !!gapValues.length,
    progress_available: !!validProgress.length,
    ...targetValidation(marketSeries, baselinePrice, targetMin, targetMax, notice),
    policy: "range_only",
    baseline_date: firstTargetDate ?? null,
    baseline_price: baselinePrice,
    current_date: summary.business_date,
    current_price: currentPrice,
    target_price_min: targetMin,
    target_price_max: targetMax,
    target_gap_min_percent: gapValues.length ? Math.min(...gapValues) : null,
    target_gap_max_percent: gapValues.length ? Math.max(...gapValues) : null,
    progress_to_min_percent: progressMin,
    progress_to_max_percent: progressMax,
    progress_caution: notice !== "baseline_below_target_range",
    progress_notice: notice,
    notice: "목표가 범위 기준 괴리율/진행률입니다. 저장 데이터 기반 확인용입니다.",
  };
}

function eventReaction(businessDate: string, stockRows: StockMarketRow[], indexes: MarketIndexRow[]): Record<string, unknown> {
  const eventRow = stockRows.find((row) => row.business_date === businessDate);
  const benchmark = eventRow ? (String(eventRow.market ?? "").toUpperCase().includes("KOSDAQ") ? "KOSDAQ" : "KOSPI") : null;
  const result: Record<string, unknown> = {
    available: false,
    historical_review: true,
    source: "krx",
    basis: "same_date_krx_stock_and_index_history",
    benchmark,
    affects_ordering: false,
    windows: [],
    notice: "동일 날짜 KRX 종목·지수 이력이 부족합니다.",
  };
  if (!eventRow || eventRow.close_price === null || eventRow.close_price <= 0) {
    result.unavailable_reason = "missing_event_stock_row";
    return result;
  }
  const stockByDate = new Map(stockRows.filter((row) => row.close_price !== null && row.close_price > 0).map((row) => [row.business_date, row]));
  const indexByDate = new Map(indexes.filter((row) => row.close_index !== null && row.close_index > 0).map((row) => [row.business_date, row]));
  const baselineDates = [...stockByDate.keys()].filter((date) => date < businessDate && indexByDate.has(date)).sort();
  if (!baselineDates.length) {
    result.unavailable_reason = "missing_common_baseline";
    return result;
  }
  const baselineDate = baselineDates[baselineDates.length - 1];
  const stockBase = Number(stockByDate.get(baselineDate)?.close_price ?? 0);
  const indexBase = Number(indexByDate.get(baselineDate)?.close_index ?? 0);
  const eventAndAfter = [...stockByDate.keys()].filter((date) => date >= businessDate).sort();
  const windows: Record<string, unknown>[] = [];
  for (const [offset, horizon] of [[0, "D0"], [1, "D+1"], [5, "D+5"], [20, "D+20"]] as Array<[number, string]>) {
    if (offset >= eventAndAfter.length) continue;
    const horizonDate = eventAndAfter[offset];
    const stockReturn = (Number(stockByDate.get(horizonDate)?.close_price ?? 0) / stockBase - 1) * 100;
    const indexRow = indexByDate.get(horizonDate);
    const item: Record<string, unknown> = {
      horizon,
      business_date: horizonDate,
      stock_return_percent: roundHalfEven(stockReturn, 2),
      benchmark_return_percent: null,
      excess_return_percent: null,
    };
    if (!indexRow) item.market_unavailable_reason = "missing_same_date_benchmark";
    else {
      const benchmarkReturn = (Number(indexRow.close_index ?? 0) / indexBase - 1) * 100;
      item.benchmark_return_percent = roundHalfEven(benchmarkReturn, 2);
      item.excess_return_percent = roundHalfEven(stockReturn - benchmarkReturn, 2);
    }
    windows.push(item);
  }
  if (windows.length) {
    result.available = true;
    result.windows = windows;
    result.notice = "KRX 종목과 지수의 동일 날짜 누적 반응입니다.";
  }
  return result;
}

function candidateProfile(
  summary: SummaryRow,
  brokerCount: number,
  target: { min: number | null; max: number | null; available: boolean },
  market: StockMarketRow | undefined,
  sameDayFlow: StockFlowRow[],
  revision: Record<string, unknown>,
  flowWindow: Record<string, unknown>,
  priceVolume: Record<string, unknown>,
): Record<string, unknown> {
  const reasons: string[] = [];
  const internalSignals: string[] = [];
  if (summary.mention_count >= 2) {
    reasons.push("리포트 집중");
    internalSignals.push("리포트 집중");
  } else if (summary.mention_count > 0) internalSignals.push("리포트 언급");
  if (brokerCount >= 2) internalSignals.push("브로커 폭");
  if (target.available) internalSignals.push("목표가 범위");
  if (revision.available) {
    const label = String(revision.direction_label ?? "").trim();
    const revisionLabel = label ? "일자 집계 목표가 범위 " + label : "일자 집계 목표가 범위 변화";
    reasons.push(revisionLabel);
    internalSignals.push(revisionLabel);
  }
  if (market && market.turnover !== null) internalSignals.push("거래대금 참고");
  const hasStockFlow = sameDayFlow.length > 0;
  const persistence = flowPersistenceExists(flowWindow);
  if (hasStockFlow) internalSignals.push("종목별 수급");
  if (persistence) {
    internalSignals.push("수급 전환 지속");
    if (hasStockFlow) reasons.push("수급 전환 지속");
  }
  if (priceVolume.available) internalSignals.push("가격/거래량 위치");

  const missing: string[] = [];
  const internalMissing: string[] = [];
  if (!market) {
    missing.push("선택일 Toss 저장값 없음");
    internalMissing.push("당일 Toss 저장값 없음");
  }
  if (!hasStockFlow) {
    missing.push("종목 수급 저장값 없음");
    internalMissing.push("종목 수급 데이터 없음");
  }
  if (!target.available) {
    missing.push("목표가 정보 없음");
    internalMissing.push("목표가 정보 없음");
  }
  if (!summary.dominant_opinion || summary.dominant_opinion === "N/A") {
    missing.push("투자의견 정보 없음");
    internalMissing.push("투자의견 정보 없음");
  }
  internalMissing.push("외국인 순매수 상위 미포함");
  if (!priceVolume.available) internalMissing.push("가격/거래량 위치 없음");

  let prioritySignal = 0;
  if (persistence && hasStockFlow) prioritySignal += 2;
  if (revision.available && revision.direction === "up") prioritySignal += 1;
  if (summary.mention_count >= 2) prioritySignal += 1;
  let sortSignal = prioritySignal;
  if (hasStockFlow && reasons.some((label) => label !== "리포트 집중")) sortSignal += 2;
  return {
    observation_priority: prioritySignal >= 3 ? "우선 확인" : "확인 후보",
    why_notable: reasons,
    missing_information: missing,
    internal_candidate_signals: internalSignals,
    internal_missing_information: internalMissing,
    sort_density: reasons.length,
    sort_signal: sortSignal,
  };
}

function flowPersistenceExists(reference: Record<string, unknown>): boolean {
  const persistence = reference.persistence as Record<string, Record<string, unknown>> | undefined;
  return !!persistence && Object.values(persistence).some((item) => item.available && Number(item.streak_days ?? 0) >= 2);
}

function supportEvidence(market: StockMarketRow | undefined, priceVolume: Record<string, unknown>): string[] {
  const labels: string[] = [];
  if (market && market.close_price !== null) labels.push("Toss 저장 가격 참고");
  if (market && market.turnover !== null) labels.push("거래대금 참고");
  if (priceVolume.available) {
    if (priceVolume.close_position_52w_percent !== null) labels.push("52주 위치 참고");
    if (priceVolume.volume_multiple_20d !== null) labels.push("거래량 위치 참고");
    if (!labels.includes("52주 위치 참고") && !labels.includes("거래량 위치 참고")) labels.push("가격 위치 참고");
  }
  return labels;
}

function evidenceLayers(primary: unknown, support: unknown, gap: unknown): Record<string, string[]> {
  const publicList = (value: unknown): string[] => {
    if (!Array.isArray(value)) return [];
    return uniqueText(value.map((item) => String(item ?? "")), Number.MAX_SAFE_INTEGER);
  };
  return { primary: publicList(primary), support: publicList(support), gap: publicList(gap) };
}

function newsCollectionStatus(news: Record<string, unknown>): string {
  if (news.available !== true) return "next_check_needed";
  const matched = ["independent_count", "report_recap_count", "unknown_count"].reduce((sum, key) => sum + Number(news[key] ?? 0), 0);
  if (Number(news.direct_count ?? 0) > 0 || Number(news.caution_count ?? 0) > 0 ||
      Number(news.market_context_count ?? 0) > 0 || matched > 0) return "stored_evidence";
  return "stored_no_match";
}

function valueContext(
  reportDate: string,
  market: StockMarketRow | undefined,
  flow: Record<string, unknown>,
  news: Record<string, unknown>,
  baseline: Record<string, unknown>,
): Record<string, unknown> {
  const tossDate = market?.business_date ?? null;
  const turnoverDate = market && market.turnover !== null ? tossDate : null;
  const flowDate = String(flow.snapshot_date || flow.reference_date || "") || null;
  const baselineAvailable = baseline.available === true;
  const currentPriceReferenceTime = baselineAvailable ? baseline.reference_time
    : market && market.close_price !== null ? market.fetched_at : null;
  const currentPriceBasis = baselineAvailable ? "20:00 stored"
    : market && market.close_price !== null ? "Toss stored snapshot" : null;
  const missing = [
    ...(!reportDate ? ["report"] : []),
    ...(!tossDate ? ["toss"] : []),
    ...(!currentPriceReferenceTime ? ["current_price"] : []),
    ...(!turnoverDate ? ["turnover"] : []),
    ...(!flowDate ? ["investor_flow"] : []),
  ];
  return {
    report_reference_date: reportDate,
    toss_reference_date: tossDate,
    current_price_reference_time: currentPriceReferenceTime,
    current_price_basis: currentPriceBasis,
    turnover_reference_date: turnoverDate,
    investor_flow_reference_date: flowDate,
    news_collection_status: newsCollectionStatus(news),
    missing_labels: missing,
  };
}

function tossBaselineReference(row: TossBaselineRow | undefined): Record<string, unknown> {
  const base = {
    source: "toss_openapi",
    read_only: true,
    live_fetch: false,
    writes_db: false,
    baseline_time: "20:00",
    affects_ordering: false,
  };
  if (!row) return {
    ...base, available: false, reference_time: null, last_price: null, currency: null,
    notice: "Toss 20:00 기준 저장값 없음",
  };
  return {
    ...base,
    available: true,
    reference_time: row.fetched_at,
    last_price: row.last_price,
    currency: row.currency,
    notice: "Toss 20:00 기준 저장값",
  };
}

function valueProfile(
  profile: Record<string, unknown>,
  news: Record<string, unknown>,
  baseline: Record<string, unknown>,
  market: StockMarketRow | undefined,
  sameDayFlow: StockFlowRow[],
  now: Date,
  timezone: string,
  businessDate: string,
): Record<string, unknown> {
  const directCount = Number(news.direct_count ?? 0);
  const positiveCount = Number(news.positive_direct_count ?? 0);
  const primaryCautionCount = Number(news.primary_caution_count ?? 0);
  const cautionCount = Number(news.caution_count ?? 0);
  const marketContextCount = Number(news.market_context_count ?? 0);
  const independentCount = Number(news.independent_count ?? 0);
  const reportRecapCount = Number(news.report_recap_count ?? 0);
  const unknownCount = Number(news.unknown_count ?? 0);
  const newsAvailable = news.available === true;
  const newsLabel = String(news.display_label || news.connection_label || "").trim();
  const hasMatchedNews = directCount > 0 || cautionCount > 0 || marketContextCount > 0 ||
    independentCount > 0 || reportRecapCount > 0 || unknownCount > 0;
  const newsNoMatch = newsAvailable && !hasMatchedNews;
  const hasMarket = !!market;
  const hasFlow = sameDayFlow.length > 0;
  const hasBaseline = baseline.available === true;
  const why = (profile.why_notable as string[]) ?? [];
  const targetOnly = why.length > 0 && why.every((item) => item.startsWith("목표가"));
  let valueSignal = Number(profile.sort_signal ?? 0);
  let [direction, directionReason] = newsDirection(directCount, positiveCount, primaryCautionCount);
  if (independentCount === 0) {
    if (hasMatchedNews) {
      direction = String(news.evidence_direction || newsLabel || "종목 뉴스 매칭");
      directionReason = String(news.evidence_direction_reason || news.connection_reason || "저장 뉴스가 후보와 매칭됐습니다.");
    } else if (newsAvailable) {
      direction = "뉴스 매칭 없음";
      directionReason = "뉴스 수집은 완료됐지만 후보와 매칭된 기사는 없습니다.";
    } else {
      direction = "뉴스 수집 전";
      directionReason = "후보 뉴스 수집이 아직 실행되지 않았습니다.";
    }
  }
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const get = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  const localDate = get("year") + "-" + get("month") + "-" + get("day");
  const hour = Number(get("hour")); const minute = Number(get("minute")); const second = Number(get("second"));
  const sameDay = businessDate === localDate;
  const marketCloseWindow = hour < 15 || (hour === 15 && (minute < 30 || (minute === 30 && second === 0)));
  const timeMode = sameDay && hour >= 9 && marketCloseWindow
    ? "intraday" : sameDay && hour >= 20 ? "toss_20_baseline" : sameDay ? "same_day_after_hours" : "stored_history";
  const basePriority = String(profile.observation_priority || "확인 후보") === "정보 보강" ? "확인 후보" : String(profile.observation_priority || "확인 후보");
  let observationPriority = basePriority;
  let valueLabel: string;
  let valueReason: string;
  if (independentCount > 0 && positiveCount > 0 && primaryCautionCount === 0) {
    observationPriority = "우선 확인";
    valueLabel = direction;
    valueReason = directionReason;
    if (directCount > 0) {
      const supportParts = [];
      if (cautionCount > 0) supportParts.push("보조 확인 " + cautionCount + "건");
      if (marketContextCount > 0) supportParts.push("시장맥락 " + marketContextCount + "건");
      if (supportParts.length) valueReason += " · " + supportParts.join(" · ");
    }
  } else if (independentCount > 0 && positiveCount > 0 && primaryCautionCount > 0) {
    observationPriority = "근거 엇갈림"; valueLabel = direction; valueReason = directionReason;
  } else if (independentCount > 0 && primaryCautionCount > 0) {
    observationPriority = "주의 확인"; valueLabel = direction; valueReason = directionReason;
  } else if (independentCount > 0 && directCount > 0) {
    valueLabel = direction; valueReason = directionReason;
  } else if (independentCount > 0 && marketContextCount > 0) {
    valueLabel = "시장 맥락 참고"; valueReason = "시장맥락 뉴스는 직접 후보 판단과 분리해 확인합니다.";
  } else if (hasMatchedNews) {
    valueLabel = newsLabel || "종목 뉴스 매칭";
    valueReason = String(news.connection_reason || news.evidence_direction_reason || "저장 뉴스가 후보와 매칭됐습니다.");
  } else if (targetOnly && newsNoMatch && (!hasMarket || !hasFlow)) {
    valueLabel = "리포트 기준 확인"; valueReason = "목표가 변화가 확인됐고 같은 날짜 뉴스 매칭은 없습니다.";
  } else if (newsNoMatch) {
    valueLabel = "뉴스 매칭 없음"; valueReason = "뉴스 수집은 완료됐지만 후보와 직접 연결된 기사는 없었습니다.";
  } else if (!newsAvailable && timeMode === "intraday") {
    valueLabel = "실시간 확인 대기"; valueReason = "장중에는 뉴스/거래대금 확인 후 우선순위를 다시 봐야 합니다.";
  } else {
    valueLabel = "저장 근거 확인"; valueReason = "저장 리포트와 시장 참고값 기준 후보입니다.";
  }
  const referenceNotes: string[] = [];
  if (hasMatchedNews) {
    if (reportRecapCount > 0 && independentCount === 0) referenceNotes.push("뉴스: 리포트 재인용 매칭");
    else if (directCount > 0 || cautionCount > 0) referenceNotes.push("뉴스: 종목 직접 매칭");
    else referenceNotes.push("뉴스: 시장 맥락 근거 있음");
  } else if (newsAvailable) referenceNotes.push("뉴스: 직접 매칭 없음");
  else referenceNotes.push("뉴스: 수집 전");
  if (!hasMarket) referenceNotes.push("Toss: 선택일 저장값 없음");
  if (!hasFlow) referenceNotes.push("수급: 저장값 없음");
  if (hasBaseline) referenceNotes.push("20:00 저장 현재가 기준");
  return {
    observation_priority: observationPriority,
    value_label: valueLabel,
    value_reason: valueReason,
    evidence_direction: direction,
    evidence_direction_reason: directionReason,
    time_mode: timeMode,
    news_confirmed: hasMatchedNews,
    news_collected: newsAvailable,
    market_reference_available: hasMarket,
    stock_flow_available: hasFlow,
    toss_20_available: hasBaseline,
    rank_reference_available: false,
    reference_notes: referenceNotes.slice(0, 4),
    sort_value_signal: valueSignal,
  };
}
