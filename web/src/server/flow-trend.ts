import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { FlowTrendSnapshot } from "../domain/market.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const SOURCE = "toss_openapi";
const MAX_FLOW_TREND_LIMIT = 20;
const DEFAULT_FLOW_TREND_LIMIT = 5;

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

function marketDisplay(value: string): string {
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[value.trim().toUpperCase()] ?? "시장 미확인";
}

function investorDisplay(value: string): string {
  return ({
    foreign: "외국인",
    institution: "기관",
    individual: "개인",
    "외국인": "외국인",
    "기관": "기관",
    "기관합계": "기관합계",
    "개인": "개인",
    "전체": "전체",
  } as Record<string, string>)[value.trim().toLowerCase()] ?? "투자자 미확인";
}

function sortKey(value: string, order: Record<string, number>): [number, string] {
  const label = value;
  return [order[label] ?? 99, label];
}

function compareLabel(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

export function parseFlowTrendLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? DEFAULT_FLOW_TREND_LIMIT : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, MAX_FLOW_TREND_LIMIT)) : DEFAULT_FLOW_TREND_LIMIT;
}

export function buildFlowTrendSnapshot(
  database: DatabaseSync,
  businessDate: string,
  limit: number,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): FlowTrendSnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid flow trend date");
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_FLOW_TREND_LIMIT) throw new RangeError("Invalid flow trend limit");

  const snapshotDates = database.prepare(`
    SELECT business_date
    FROM market_investor_flow_daily
    WHERE business_date <= ? AND source = ?
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT ?
  `).all(businessDate, SOURCE, limit).map((row) => {
    if (typeof row.business_date !== "string" || !isBusinessDate(row.business_date)) {
      throw new Error("Invalid stored flow date");
    }
    return row.business_date;
  });

  const listFlows = database.prepare(`
    SELECT business_date, market, investor_type, sell_volume, buy_volume, net_buy_volume,
           sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit, source
    FROM market_investor_flow_daily
    WHERE business_date = ? AND market IN (?, ?) AND source = ?
  `);
  const marketOrder = { KOSPI: 0, KOSDAQ: 1, "전체": 2 };
  const investorOrder = { "외국인": 0, "기관합계": 1, "기관": 2, "개인": 3, "전체": 9 };
  const items = snapshotDates.map((snapshotDate) => {
    const marketFlows = (listFlows.all(snapshotDate, "KOSPI", "KOSDAQ", SOURCE) as unknown as MarketFlowRow[])
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
      }))
      .sort((left, right) => {
        const [leftMarket, leftMarketLabel] = sortKey(left.market_label, marketOrder);
        const [rightMarket, rightMarketLabel] = sortKey(right.market_label, marketOrder);
        if (leftMarket !== rightMarket) return leftMarket - rightMarket;
        const marketLabels = compareLabel(leftMarketLabel, rightMarketLabel);
        if (marketLabels) return marketLabels;
        const [leftInvestor, leftInvestorLabel] = sortKey(left.investor_label, investorOrder);
        const [rightInvestor, rightInvestorLabel] = sortKey(right.investor_label, investorOrder);
        if (leftInvestor !== rightInvestor) return leftInvestor - rightInvestor;
        return compareLabel(leftInvestorLabel, rightInvestorLabel);
      });
    return { business_date: snapshotDate, market_flows: marketFlows };
  });

  const referenceDate = snapshotDates[0] ?? null;
  const available = items.length > 0;
  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    available,
    source: available ? SOURCE : null,
    data_scope: "stored_toss_close_market_flow",
    live_fetch: false,
    scoring: false,
    notice: available
      ? "선택 날짜를 포함한 최근 Toss 저장 시장 수급 기준입니다. 실시간 호출은 포함하지 않습니다."
      : "선택 날짜 이전 또는 해당 날짜의 저장 수급 데이터가 없습니다.",
    items,
  };
}

export function getFlowTrendSnapshot(businessDate: string, limit = DEFAULT_FLOW_TREND_LIMIT): FlowTrendSnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildFlowTrendSnapshot(database, businessDate, limit, new Date(), timezone));
}
