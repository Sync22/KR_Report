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

type CaptureState = {
  status: string;
  business_date: string | null;
  missing_domains: string[];
} | null;

type StockRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

type EtfRow = {
  business_date: string;
  etf_code: string;
  etf_name: string;
  close_price: number | null;
  change_percent: number | null;
  nav: number | null;
  volume: number | null;
  turnover: number | null;
  underlying_index_name: string | null;
};

type IndexRow = {
  business_date: string;
  index_series: string;
  index_name: string;
  close_index: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
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
  source: string;
};

function captureState(database: DatabaseSync, businessDate: string): CaptureState {
  const row = database.prepare(`
    SELECT status, business_date, detail
    FROM operation_events
    WHERE component = ? AND event_type = ? AND business_date = ?
    ORDER BY event_time DESC, id DESC
    LIMIT 1
  `).get("toss-market-context", "capture", businessDate);
  if (!row) return null;
  if (typeof row.status !== "string") throw new Error("Invalid stored market capture status");
  if (typeof row.business_date !== "string" || !isBusinessDate(row.business_date)) {
    throw new Error("Invalid stored market capture date");
  }
  const detail = typeof row.detail === "string" ? row.detail : "";
  const missingPart = detail.split(";").find((part) => part.trim().startsWith("missing_domains="));
  const separator = missingPart?.indexOf("=") ?? -1;
  const missingRaw = missingPart && separator >= 0 ? missingPart.slice(separator + 1).trim() : "";
  return {
    status: row.status,
    business_date: row.business_date,
    missing_domains: missingRaw.split(",").filter((value) => ALLOWED_MISSING_DOMAINS.has(value)),
  };
}

export function getRecentDailyTossSnapshotDates(database: DatabaseSync, businessDate: string): string[] {
  const rows = database.prepare(`
    SELECT business_date FROM (
      SELECT business_date FROM (
        SELECT DISTINCT business_date FROM toss_market_context_snapshots
        WHERE business_date <= ? AND source = ? ORDER BY business_date DESC LIMIT 3
      )
      UNION
      SELECT business_date FROM (
        SELECT DISTINCT business_date FROM stock_market_daily
        WHERE business_date <= ? AND source = ?
          AND (change_amount IS NOT NULL OR change_percent IS NOT NULL OR volume IS NOT NULL
               OR turnover IS NOT NULL OR market_cap IS NOT NULL OR listed_shares IS NOT NULL
               OR open_price IS NOT NULL OR high_price IS NOT NULL OR low_price IS NOT NULL)
        ORDER BY business_date DESC LIMIT 3
      )
      UNION
      SELECT business_date FROM (
        SELECT DISTINCT business_date FROM etf_daily_snapshots
        WHERE business_date <= ? AND source = ? ORDER BY business_date DESC LIMIT 3
      )
      UNION
      SELECT business_date FROM (
        SELECT DISTINCT business_date FROM market_index_daily
        WHERE business_date <= ? AND source = ? ORDER BY business_date DESC LIMIT 3
      )
    )
    ORDER BY business_date DESC
    LIMIT 3
  `).all(businessDate, SOURCE, businessDate, SOURCE, businessDate, SOURCE, businessDate, SOURCE) as unknown as Array<{ business_date: string }>;
  return rows.map((row) => row.business_date);
}

function stockRows(database: DatabaseSync, businessDate: string, market: string, limit: number): StockRow[] {
  return database.prepare(`
    SELECT business_date, stock_code, stock_name, market, close_price, change_percent,
           volume, turnover, fetched_at
    FROM stock_market_daily
    WHERE business_date = ? AND market = ? AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, stock_code ASC
    LIMIT ?
  `).all(businessDate, market, SOURCE, limit) as unknown as StockRow[];
}

function stockItem(row: StockRow) {
  return {
    business_date: row.business_date,
    stock_code: row.stock_code,
    stock_name: row.stock_name,
    market: row.market,
    close_price: row.close_price,
    change_percent: row.change_percent,
    volume: row.volume,
    turnover: row.turnover,
    fetched_at: row.fetched_at,
  };
}

function etfRows(database: DatabaseSync, businessDate: string, limit: number): EtfRow[] {
  return database.prepare(`
    SELECT business_date, etf_code, etf_name, close_price, change_percent, nav,
           volume, turnover, underlying_index_name
    FROM etf_daily_snapshots
    WHERE business_date = ? AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
    LIMIT ?
  `).all(businessDate, SOURCE, limit) as unknown as EtfRow[];
}

function formatNav(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    roundingMode: "halfEven",
  }).format(value);
}

function formatFlowAmount(value: number): string {
  const amount = Math.abs(value);
  if (amount >= 1_000_000_000_000) {
    return `${new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1, roundingMode: "halfEven", useGrouping: false }).format(amount / 1_000_000_000_000)}조`;
  }
  if (amount >= 100_000_000) {
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, roundingMode: "halfEven", useGrouping: false }).format(amount / 100_000_000)}억`;
  }
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(amount)}원`;
}

function etfItem(row: EtfRow) {
  const evidence: string[] = [];
  if (row.turnover !== null) evidence.push(`거래대금 ${formatFlowAmount(row.turnover)}`);
  if (row.nav !== null) evidence.push(`NAV ${formatNav(row.nav)}`);
  if (row.underlying_index_name) evidence.push(`기초지수 ${row.underlying_index_name}`);
  return {
    business_date: row.business_date,
    etf_code: row.etf_code,
    etf_name: row.etf_name,
    close_price: row.close_price,
    change_percent: row.change_percent,
    nav: row.nav,
    volume: row.volume,
    turnover: row.turnover,
    underlying_index_name: row.underlying_index_name,
    evidence_label: evidence.length ? evidence.join(" · ") : "저장 ETF 일별매매정보",
    rotation_reference: "저장 ETF 거래대금/NAV/기초지수 기준",
  };
}

function indexRows(database: DatabaseSync, businessDate: string, limit: number): IndexRow[] {
  return database.prepare(`
    SELECT business_date, index_series, index_name, close_index, change_percent, volume, turnover
    FROM market_index_daily
    WHERE business_date = ? AND source = ?
    ORDER BY index_series ASC, index_name ASC
    LIMIT ?
  `).all(businessDate, SOURCE, limit) as unknown as IndexRow[];
}

function indexItem(row: IndexRow) {
  return {
    business_date: row.business_date,
    index_series: row.index_series,
    index_name: row.index_name,
    close_index: row.close_index,
    change_percent: row.change_percent,
    volume: row.volume,
    turnover: row.turnover,
  };
}

function tossContext(database: DatabaseSync, businessDate: string, capture: CaptureState) {
  const kospi = stockRows(database, businessDate, "KOSPI", 5);
  const kosdaq = stockRows(database, businessDate, "KOSDAQ", 5);
  const etfs = etfRows(database, businessDate, 5);
  const indices = indexRows(database, businessDate, 10);
  const available = !!(kospi.length || kosdaq.length || etfs.length || indices.length);
  const status = capture?.status ?? null;
  const missing = capture?.missing_domains ?? [];
  const notice = status === "partial"
    ? `선택 날짜의 Toss 저장 스냅샷 일부가 누락되었습니다: ${missing.join(", ") || "필수 데이터"}.`
    : status === "failed"
      ? "선택 날짜의 Toss 저장 캡처가 실패했습니다. 표시된 값은 불완전할 수 있습니다."
      : status === "empty"
        ? "선택 날짜의 Toss 저장 캡처에 사용할 수 있는 데이터가 없습니다."
        : available
          ? "선택 날짜의 Toss 저장 스냅샷 기준입니다. 20:00 저장을 보장하지 않으며 확정 판단은 포함하지 않습니다."
          : "선택 날짜의 Toss 저장 스냅샷이 없습니다. 최신 날짜 값으로 대체하지 않습니다.";
  return {
    available,
    source: available ? SOURCE : null,
    snapshot_date: available ? businessDate : null,
    capture_status: status,
    missing_domains: missing,
    notice,
    top_kospi_by_turnover: kospi.map(stockItem),
    top_kosdaq_by_turnover: kosdaq.map(stockItem),
    top_etfs_by_turnover: etfs.map(etfItem),
    indices: indices.map(indexItem),
  };
}

function tossRecentFlow(database: DatabaseSync, businessDate: string, dates: string[]) {
  const items = dates.map((snapshotDate) => {
    const kospi = stockRows(database, snapshotDate, "KOSPI", 1);
    const kosdaq = stockRows(database, snapshotDate, "KOSDAQ", 1);
    const etfs = etfRows(database, snapshotDate, 1);
    return {
      business_date: snapshotDate,
      kospi_top_by_turnover: kospi.length ? stockItem(kospi[0]!) : null,
      kosdaq_top_by_turnover: kosdaq.length ? stockItem(kosdaq[0]!) : null,
      etf_top_by_turnover: etfs.length ? etfItem(etfs[0]!) : null,
    };
  });
  const exact = !!(dates.length && dates[0] === businessDate);
  return {
    available: !!items.length,
    source: items.length ? SOURCE : null,
    business_date: businessDate,
    reference_date: dates[0] ?? null,
    exact_date_available: exact,
    notice: items.length && exact
      ? "선택 날짜를 포함한 최근 Toss 저장 스냅샷 기준입니다. 실시간값이나 확정 판단은 포함하지 않습니다."
      : items.length
        ? "선택 날짜의 Toss 저장값이 없어 최근 Toss 저장 스냅샷 기준 흐름만 표시합니다."
        : "선택 날짜 이전 또는 해당 날짜의 Toss 저장 스냅샷이 없습니다.",
    items,
  };
}

function marketLabel(value: string): string {
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[value.trim().toUpperCase()] ?? "시장 미확인";
}

function investorLabel(value: string): string {
  return ({
    foreign: "외국인",
    institution: "기관",
    individual: "개인",
    외국인: "외국인",
    기관: "기관",
    기관합계: "기관합계",
    개인: "개인",
    전체: "전체",
  } as Record<string, string>)[value.trim().toLowerCase()] ?? "투자자 미확인";
}

function displayOrder(label: string, order: Record<string, number>): number {
  return order[label] ?? 99;
}

function investorFlowRows(database: DatabaseSync, businessDate: string): MarketFlowRow[] {
  const rows: MarketFlowRow[] = [];
  for (const market of ["KOSPI", "KOSDAQ"]) {
    rows.push(...database.prepare(`
      SELECT business_date, market, investor_type, sell_volume, buy_volume, net_buy_volume,
             sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit, source
      FROM market_investor_flow_daily
      WHERE business_date = ? AND market = ? AND source = ?
      ORDER BY investor_type ASC
    `).all(businessDate, market, SOURCE) as unknown as MarketFlowRow[]);
  }
  return rows;
}

function tossInvestorFlow(database: DatabaseSync, businessDate: string) {
  const rows = investorFlowRows(database, businessDate);
  rows.sort((left, right) => {
    const leftMarket = marketLabel(left.market);
    const rightMarket = marketLabel(right.market);
    const marketOrder = displayOrder(leftMarket, { KOSPI: 0, KOSDAQ: 1, "전체": 2 }) - displayOrder(rightMarket, { KOSPI: 0, KOSDAQ: 1, "전체": 2 });
    if (marketOrder) return marketOrder;
    const leftInvestor = investorLabel(left.investor_type);
    const rightInvestor = investorLabel(right.investor_type);
    const investorOrder = displayOrder(leftInvestor, { "외국인": 0, "기관합계": 1, "기관": 2, "개인": 3, "전체": 9 }) - displayOrder(rightInvestor, { "외국인": 0, "기관합계": 1, "기관": 2, "개인": 3, "전체": 9 });
    return investorOrder || (leftInvestor < rightInvestor ? -1 : leftInvestor > rightInvestor ? 1 : 0);
  });
  const available = !!rows.length;
  return {
    available,
    source: available ? SOURCE : null,
    data_scope: "stored_toss_close_market_flow",
    live_fetch: false,
    scoring: false,
    snapshot_date: available ? businessDate : null,
    notice: available
      ? "저장된 Toss 시장 수급 기준입니다. 확정 판단은 포함하지 않습니다."
      : "선택 날짜의 Toss 시장 수급 데이터가 없습니다.",
    market_flows: rows.map((row) => ({
      business_date: row.business_date,
      market: row.market,
      market_label: marketLabel(row.market),
      investor_type: row.investor_type,
      investor_label: investorLabel(row.investor_type),
      sell_volume: row.sell_volume,
      buy_volume: row.buy_volume,
      net_buy_volume: row.net_buy_volume,
      sell_amount: row.sell_amount,
      buy_amount: row.buy_amount,
      net_buy_amount: row.net_buy_amount,
      volume_unit: row.volume_unit,
      amount_unit: row.amount_unit,
      source: row.source,
    })),
  };
}

export function buildDailyTossContextFromDatabase(database: DatabaseSync, businessDate: string, snapshotDates?: string[]) {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily Toss context date");
  const capture = captureState(database, businessDate);
  const dates = snapshotDates ?? getRecentDailyTossSnapshotDates(database, businessDate);
  return {
    capture_state: capture,
    toss_context: tossContext(database, businessDate, capture),
    toss_recent_flow: tossRecentFlow(database, businessDate, dates),
    toss_investor_flow: tossInvestorFlow(database, businessDate),
  };
}
