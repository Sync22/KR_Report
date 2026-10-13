import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate, type DailyStockSummarySnapshot } from "../domain/daily.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string;
};

type MarketRow = {
  business_date: string;
  stock_code: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

function marketReferences(database: DatabaseSync, businessDate: string, summaries: SummaryRow[]): Map<string, MarketRow> {
  const codes = [...new Set(summaries
    .map((item) => item.stock_code)
    .filter((code): code is string => typeof code === "string" && !!code.trim())
    .map((code) => code.trim()))].sort();
  if (!codes.length) return new Map();
  const placeholders = codes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT business_date, stock_code, market, close_price, change_percent, volume, turnover, fetched_at
    FROM stock_market_daily
    WHERE business_date = ? AND source = ? AND stock_code IN (${placeholders})
    ORDER BY stock_code ASC
  `).all(businessDate, "toss_openapi", ...codes) as unknown as MarketRow[];
  return new Map(rows.map((item) => [item.stock_code, item]));
}

export function buildDailyStockSummarySnapshotFromDatabase(database: DatabaseSync, businessDate: string): DailyStockSummarySnapshot {
  const summaries = database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
           target_price_min, target_price_max, dominant_opinion
    FROM daily_stock_summaries
    WHERE business_date = ?
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as SummaryRow[];
  const marketRefs = marketReferences(database, businessDate, summaries);
  return {
    surface: "web-view",
    read_only: true,
    live_fetch: false,
    business_date: businessDate,
    stocks: summaries.map((item) => {
      const reference = marketRefs.get(item.stock_code || "");
      return {
        ...item,
        market_reference: reference ? {
          business_date: reference.business_date,
          market: reference.market,
          close_price: reference.close_price,
          change_percent: reference.change_percent,
          volume: reference.volume,
          turnover: reference.turnover,
          fetched_at: reference.fetched_at,
        } : null,
      };
    }),
  };
}

export function getDailyStockSummarySnapshot(businessDate: string): DailyStockSummarySnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily stock summary date");
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const snapshot = buildDailyStockSummarySnapshotFromDatabase(database, businessDate);
      database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
