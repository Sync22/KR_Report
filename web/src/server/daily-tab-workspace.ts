import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate, type DailyStock, type DailyStockSummarySnapshot } from "../domain/daily.ts";
import { isCandidateEvidenceSnapshot, type CandidateEvidenceSnapshot } from "../domain/candidate-evidence.ts";
import { isFlowTrendSnapshot, type FlowTrendSnapshot } from "../domain/market.ts";
import { isStockDetailSnapshot, type StockDetailSnapshot } from "../domain/stocks.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { buildDailySnapshotFromDatabase } from "./daily-snapshot.ts";
import { buildFlowTrendSnapshot } from "./flow-trend.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";
import { buildStockDetailSnapshotFromDatabase } from "./stock-detail.ts";
import { buildDailyStockSummarySnapshotFromDatabase } from "./stock-summary.ts";

export type DailyTabWorkspace = Readonly<{
  daily: Record<string, unknown> | null;
  candidates: CandidateEvidenceSnapshot | null;
  stocks: DailyStockSummarySnapshot | null;
  flow: FlowTrendSnapshot | null;
  selectedStockDetail: StockDetailSnapshot | null;
}>;

function read<T>(operation: () => T): T | null {
  try {
    return operation();
  } catch {
    return null;
  }
}

export function buildDailyTabWorkspaceFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  selectedStockCode: string | null,
  now = new Date(),
): DailyTabWorkspace {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily tab date");

  const rawCandidates = read(() => buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, 8, now));
  const candidates = isCandidateEvidenceSnapshot(rawCandidates, businessDate) ? rawCandidates : null;
  const priorityCandidates = candidates ? { ...candidates, rows: candidates.rows.slice(0, 2) } : undefined;
  const rawDaily = read(() => buildDailySnapshotFromDatabase(database, businessDate, {
    now,
    priorityCandidateEvidence: priorityCandidates,
  }));
  const daily = rawDaily?.business_date === businessDate ? rawDaily : null;

  let stocks: DailyStockSummarySnapshot | null = daily && Array.isArray(daily.stocks)
    ? {
      surface: "web-view",
      read_only: true,
      live_fetch: false,
      business_date: businessDate,
      stocks: (daily.stocks as DailyStock[]).map((stock) => ({
        ...stock,
        market_reference: stock.market_reference ? {
          ...stock.market_reference,
          close_price: stock.market_reference.close_price ?? null,
          change_percent: stock.market_reference.change_percent ?? null,
          volume: stock.market_reference.volume ?? null,
          turnover: stock.market_reference.turnover ?? null,
        } : null,
      })) as DailyStockSummarySnapshot["stocks"],
    }
    : null;
  if (!stocks) stocks = read(() => buildDailyStockSummarySnapshotFromDatabase(database, businessDate));

  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  const rawFlow = read(() => buildFlowTrendSnapshot(database, businessDate, 5, now, timezone));
  const flow = isFlowTrendSnapshot(rawFlow, businessDate) ? rawFlow : null;

  const selectedIsStored = typeof selectedStockCode === "string" && /^\d{6}$/.test(selectedStockCode) && (
    candidates?.rows.some((row) => row.stock_code === selectedStockCode) === true ||
    stocks?.stocks.some((row) => row.stock_code === selectedStockCode) === true
  );
  const rawSelectedStockDetail = selectedIsStored
    ? read(() => buildStockDetailSnapshotFromDatabase(database, businessDate, selectedStockCode))
    : null;
  const selectedStockDetail = isStockDetailSnapshot(rawSelectedStockDetail, businessDate, selectedIsStored ? selectedStockCode : "")
    ? rawSelectedStockDetail
    : null;

  return { daily, candidates, stocks, flow, selectedStockDetail };
}

export function getDailyTabWorkspace(businessDate: string, selectedStockCode: string | null): DailyTabWorkspace {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily tab date");
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const workspace = buildDailyTabWorkspaceFromDatabase(database, businessDate, selectedStockCode);
      database.exec("COMMIT");
      return workspace;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
