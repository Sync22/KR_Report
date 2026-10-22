import { createHash } from "node:crypto";

import type { ChartExplorerBar } from "./chart-explorer.ts";

export type ChartAlertMinuteBar = Omit<ChartExplorerBar, "missingBarsBefore">;

export function isReportFocusCandidate(value: unknown, businessDate: string): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const row = value as Record<string, unknown>;
  const summary = row.report_summary;
  return row.business_date === businessDate && /^[0-9]{6}$/.test(String(row.stock_code ?? "")) &&
    typeof row.stock_name === "string" && !!row.stock_name.trim() &&
    Array.isArray(row.why_notable) && row.why_notable.includes("리포트 집중") &&
    !!summary && typeof summary === "object" && !Array.isArray(summary) &&
    Number.isInteger((summary as Record<string, unknown>).report_count) &&
    Number((summary as Record<string, unknown>).report_count) >= 2;
}

export function parseMinuteCandles(value: unknown): ChartAlertMinuteBar[] {
  if (!Array.isArray(value) || value.length > 200) throw new TypeError("minute-candle-limit");
  const bars = value.map((raw): ChartAlertMinuteBar => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new TypeError("invalid-minute-candle");
    const candle = raw as Record<string, unknown>;
    const time = typeof candle.timestamp === "string" ? Date.parse(candle.timestamp) : Number.NaN;
    const [open, high, low, close, volume] = [candle.openPrice, candle.highPrice, candle.lowPrice, candle.closePrice, candle.volume];
    if (!Number.isFinite(time) || [open, high, low, close, volume].some((item) => typeof item !== "number" || !Number.isFinite(item)) ||
      Number(open) <= 0 || Number(high) <= 0 || Number(low) <= 0 || Number(close) <= 0 || Number(volume) < 0 ||
      Number(high) < Math.max(Number(open), Number(low), Number(close)) || Number(low) > Math.min(Number(open), Number(high), Number(close))) {
      throw new TypeError("invalid-minute-candle");
    }
    return { time: new Date(time).toISOString(), open: Number(open), high: Number(high), low: Number(low), close: Number(close), volume: Number(volume) };
  });
  bars.sort((left, right) => left.time.localeCompare(right.time));
  if (new Set(bars.map((bar) => bar.time)).size !== bars.length) throw new TypeError("duplicate-minute-candle");
  return bars;
}

export function chartAlertEventId(input: {
  watchId: string;
  symbol: string;
  reportBusinessDate: string;
  stockName: string;
  reportCount: number;
  ruleVersion: string;
  kind: string;
  direction: string;
  basisStartTime: string;
  status: string;
}): string {
  return createHash("sha256").update([
    input.watchId, input.symbol, input.reportBusinessDate, input.stockName, String(input.reportCount), "1m",
    input.ruleVersion, input.kind, input.direction, input.basisStartTime, input.status,
  ].join("|"), "utf8").digest("hex");
}
