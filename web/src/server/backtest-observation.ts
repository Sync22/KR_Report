import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { BacktestObservationSnapshot } from "../domain/observation.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const HORIZONS = [1, 5, 10, 20] as const;
const NOTICE = "저장된 2026년 리포트/KRX 가격/수급 기준의 리포트 후 흐름입니다. 저장 데이터 기반 확인용입니다.";
type DbRow = Record<string, string | number | null>;
type SummaryRow = DbRow & {
  business_date: string;
  stock_name: string;
  stock_code: string;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string | null;
};
type MarketRow = DbRow & {
  business_date: string;
  stock_code: string;
  market: string | null;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

function dateTimeIso(now: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "00";
  const milliseconds = now.getUTCMilliseconds();
  const offsetMinutes = Math.round((Date.UTC(
    Number(part("year")), Number(part("month")) - 1, Number(part("day")),
    Number(part("hour")), Number(part("minute")), Number(part("second")), milliseconds,
  ) - now.getTime()) / 60000);
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const offset = Math.abs(offsetMinutes);
  const fraction = milliseconds ? `.${String(milliseconds).padStart(3, "0")}000` : "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}:${part("second")}${fraction}${sign}${String(Math.floor(offset / 60)).padStart(2, "0")}:${String(offset % 60).padStart(2, "0")}`;
}

function pythonRoundToTwo(value: number): number {
  if (!Number.isFinite(value) || value === 0) return value;
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, value);
  const bits = view.getBigUint64(0);
  const one = BigInt(1);
  const negative = (bits >> BigInt(63)) !== BigInt(0);
  const encodedExponent = Number((bits >> BigInt(52)) & BigInt(2047));
  const fraction = bits & ((one << BigInt(52)) - one);
  const significand = encodedExponent === 0 ? fraction : fraction | (one << BigInt(52));
  const exponent = encodedExponent === 0 ? -1074 : encodedExponent - 1023 - 52;
  const numerator = significand * BigInt(100);
  let cents: bigint;
  if (exponent >= 0) {
    cents = numerator << BigInt(exponent);
  } else {
    const divisor = one << BigInt(-exponent);
    const quotient = numerator / divisor;
    const remainder = numerator % divisor;
    const doubledRemainder = remainder * BigInt(2);
    cents = doubledRemainder > divisor || (doubledRemainder === divisor && quotient % BigInt(2) === one)
      ? quotient + one
      : quotient;
  }
  return Number(negative ? -cents : cents) / 100;
}

function percent(numerator: number, denominator: number): number | null {
  return denominator === 0 ? null : pythonRoundToTwo((numerator / denominator) * 100);
}

function marketReference(item: MarketRow | undefined): Record<string, unknown> | null {
  if (!item) return null;
  return {
    business_date: item.business_date,
    market: item.market,
    close_price: item.close_price,
    change_percent: item.change_percent,
    volume: item.volume,
    turnover: item.turnover,
    fetched_at: item.fetched_at,
  };
}

function marketDisplay(value: string | null): string {
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[value?.trim().toUpperCase() ?? ""] ?? "시장 미확인";
}

function reactionWindow(
  horizon: number,
  base: MarketRow | undefined,
  series: MarketRow[],
): BacktestObservationSnapshot["rows"][number]["reaction_windows"][number] {
  if (!base) return {
    horizon_days: horizon, available: false, horizon_date: null, base_close_price: null,
    horizon_close_price: null, close_return_percent: null, horizon_volume: null,
    horizon_turnover: null, unavailable_reason: "missing_base_market",
  };
  if (base.close_price === null) return {
    horizon_days: horizon, available: false, horizon_date: null, base_close_price: null,
    horizon_close_price: null, close_return_percent: null, horizon_volume: null,
    horizon_turnover: null, unavailable_reason: "missing_base_close_price",
  };
  if (series.length <= horizon) return {
    horizon_days: horizon, available: false, horizon_date: null, base_close_price: base.close_price,
    horizon_close_price: null, close_return_percent: null, horizon_volume: null,
    horizon_turnover: null, unavailable_reason: "missing_horizon_market",
  };
  const item = series[horizon];
  if (item.close_price === null) return {
    horizon_days: horizon, available: false, horizon_date: item.business_date,
    base_close_price: base.close_price, horizon_close_price: null, close_return_percent: null,
    horizon_volume: item.volume, horizon_turnover: item.turnover, unavailable_reason: "missing_horizon_close_price",
  };
  return {
    horizon_days: horizon, available: true, horizon_date: item.business_date,
    base_close_price: base.close_price, horizon_close_price: item.close_price,
    close_return_percent: percent(item.close_price - base.close_price, base.close_price),
    horizon_volume: item.volume, horizon_turnover: item.turnover, unavailable_reason: null,
  };
}

function targetObservation(
  database: DatabaseSync,
  summary: SummaryRow,
  base: MarketRow | undefined,
  series: MarketRow[],
): BacktestObservationSnapshot["rows"][number]["target_observation"] {
  const targetValues = [summary.target_price_min, summary.target_price_max].filter((value): value is number => value !== null);
  const unavailable = (reason: string) => ({
    available: false, gap_available: false, progress_available: false, baseline_date: null,
    baseline_price: null, current_date: null, current_price: null, target_price_min: null,
    target_price_max: null, target_gap_min_percent: null, target_gap_max_percent: null,
    progress_to_min_percent: null, progress_to_max_percent: null, progress_caution: false,
    progress_notice: null, validation_available: false, validation_window_days: null,
    max_progress_to_min_percent: null, max_progress_to_max_percent: null,
    hit_min_horizon_days: null, hit_max_horizon_days: null, validation_notice: null,
    unavailable_reason: reason,
  });
  if (!summary.stock_code || !targetValues.length) return unavailable("missing_target_price");
  if (!base || base.close_price === null) return unavailable("missing_base_close_price");

  const targetMin = Math.min(...targetValues);
  const targetMax = Math.max(...targetValues);
  const currentPrice = base.close_price;
  const gapValues = [percent(targetMin - currentPrice, currentPrice), percent(targetMax - currentPrice, currentPrice)]
    .filter((value): value is number => value !== null);
  const baselineRow = database.prepare(`
    SELECT MIN(business_date) AS business_date
    FROM reports
    WHERE stock_code = ? AND business_date <= ? AND target_price_value IS NOT NULL
  `).get(summary.stock_code, summary.business_date) as DbRow | undefined;
  const baselineDate = baselineRow?.business_date;
  const baselineMarket = typeof baselineDate === "string" ? database.prepare(`
    SELECT close_price FROM stock_market_daily
    WHERE business_date = ? AND stock_code = ? AND source = 'krx'
    ORDER BY stock_code ASC LIMIT 1
  `).get(baselineDate, summary.stock_code) as DbRow | undefined : undefined;
  const baselinePriceValue = baselineMarket?.close_price;
  const baselinePrice = baselinePriceValue === null || baselinePriceValue === undefined ? null
    : typeof baselinePriceValue === "number" ? baselinePriceValue : (() => { throw new Error("Invalid stored baseline close price"); })();
  const progress = (target: number) => baselinePrice === null ? null : targetProgress(currentPrice, baselinePrice, target);
  const progressToMin = progress(targetMin);
  const progressToMax = progress(targetMax);
  const progressValues = [progressToMin, progressToMax].filter((value): value is number => value !== null);
  const progressNotice = baselinePrice === null ? null
    : baselinePrice < targetMin ? "baseline_below_target_range"
      : baselinePrice > targetMax ? "baseline_above_target_range" : "baseline_inside_target_range";

  let validation: Record<string, unknown>;
  if (baselinePrice === null) validation = emptyValidation("missing_baseline_price");
  else if (progressNotice !== "baseline_below_target_range") validation = emptyValidation(progressNotice ?? "unsupported_target_direction");
  else {
    const observed = series.flatMap((item, index) => item.close_price === null ? [] : [{ item, index }]);
    if (!observed.length) validation = emptyValidation("missing_market_series");
    else {
      const minProgress = observed.map(({ item }) => targetProgress(item.close_price!, baselinePrice, targetMin)).filter((value): value is number => value !== null);
      const maxProgress = observed.map(({ item }) => targetProgress(item.close_price!, baselinePrice, targetMax)).filter((value): value is number => value !== null);
      const hitMin = observed.find(({ item }) => item.close_price! >= targetMin)?.index ?? null;
      const hitMax = observed.find(({ item }) => item.close_price! >= targetMax)?.index ?? null;
      validation = {
        validation_available: Boolean(minProgress.length || maxProgress.length || hitMin !== null || hitMax !== null),
        validation_window_days: Math.max(...observed.map(({ index }) => index)),
        max_progress_to_min_percent: minProgress.length ? Math.max(...minProgress) : null,
        max_progress_to_max_percent: maxProgress.length ? Math.max(...maxProgress) : null,
        hit_min_horizon_days: hitMin, hit_max_horizon_days: hitMax, validation_notice: "stored_window_only",
      };
    }
  }

  return {
    available: Boolean(gapValues.length || progressValues.length),
    gap_available: Boolean(gapValues.length), progress_available: Boolean(progressValues.length),
    baseline_date: typeof baselineDate === "string" ? baselineDate : null, baseline_price: baselinePrice,
    current_date: summary.business_date, current_price: currentPrice,
    target_price_min: targetMin, target_price_max: targetMax,
    target_gap_min_percent: gapValues.length ? Math.min(...gapValues) : null,
    target_gap_max_percent: gapValues.length ? Math.max(...gapValues) : null,
    progress_to_min_percent: progressToMin, progress_to_max_percent: progressToMax,
    progress_caution: progressNotice !== "baseline_below_target_range", progress_notice: progressNotice,
    ...validation, validation_notice: validation.validation_notice as string | null, unavailable_reason: null,
  };
}

function targetProgress(current: number, baseline: number, target: number): number | null {
  const denominator = target - baseline;
  const numerator = current - baseline;
  if (denominator === 0) return numerator === 0 ? 0 : null;
  return percent(numerator, denominator);
}

function emptyValidation(reason: string): Record<string, unknown> {
  return {
    validation_available: false, validation_window_days: null,
    max_progress_to_min_percent: null, max_progress_to_max_percent: null,
    hit_min_horizon_days: null, hit_max_horizon_days: null, validation_notice: reason,
  };
}

function sumFlow(rows: DbRow[], types: string[], field: string): number | null {
  const values = rows.filter((row) => types.includes(String(row.investor_type))).map((row) => row[field])
    .filter((value): value is number => typeof value === "number");
  return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
}

function backtestRow(database: DatabaseSync, summary: SummaryRow): BacktestObservationSnapshot["rows"][number] {
  const stockCode = summary.stock_code || "";
  const base = database.prepare(`
    SELECT business_date, stock_code, market, close_price, change_percent, volume, turnover, fetched_at
    FROM stock_market_daily WHERE business_date = ? AND source = 'krx' AND stock_code = ?
    ORDER BY stock_code ASC LIMIT 1
  `).get(summary.business_date, stockCode) as MarketRow | undefined;
  const series = database.prepare(`
    SELECT business_date, stock_code, market, close_price, change_percent, volume, turnover, fetched_at
    FROM stock_market_daily WHERE business_date >= ? AND stock_code = ? AND source = 'krx'
    ORDER BY business_date ASC LIMIT 21
  `).all(summary.business_date, stockCode) as MarketRow[];
  const flowRows = database.prepare(`
    SELECT investor_type, net_buy_volume, net_buy_amount
    FROM stock_investor_flow_daily
    WHERE business_date = ? AND stock_code = ? AND source = 'krx_data_market'
    ORDER BY investor_type ASC
  `).all(summary.business_date, stockCode) as DbRow[];
  const top = database.prepare(`
    SELECT market, rank, net_buy_volume, net_buy_amount
    FROM investor_net_buy_top_daily
    WHERE business_date = ? AND stock_code = ? AND investor_type = 'foreign' AND source = 'krx_data_market'
    ORDER BY rank ASC, market ASC LIMIT 1
  `).get(summary.business_date, stockCode) as DbRow | undefined;
  const reactions = HORIZONS.map((horizon) => reactionWindow(horizon, base, series));
  const target = targetObservation(database, summary, base, series);
  const flow = {
    available: Boolean(flowRows.length),
    individual_net_buy_volume: sumFlow(flowRows, ["개인"], "net_buy_volume"),
    foreign_net_buy_volume: sumFlow(flowRows, ["외국인"], "net_buy_volume"),
    institution_net_buy_volume: sumFlow(flowRows, ["기관", "기관합계"], "net_buy_volume"),
    individual_net_buy_amount: sumFlow(flowRows, ["개인"], "net_buy_amount"),
    foreign_net_buy_amount: sumFlow(flowRows, ["외국인"], "net_buy_amount"),
    institution_net_buy_amount: sumFlow(flowRows, ["기관", "기관합계"], "net_buy_amount"),
    investor_types: [...new Set(flowRows.map((row) => String(row.investor_type)))].sort(),
  };
  const netBuyTop = {
    available: Boolean(top), foreign_top_rank: top?.rank ?? null,
    market: top?.market ? marketDisplay(String(top.market)) : null,
    net_buy_volume: top?.net_buy_volume ?? null, net_buy_amount: top?.net_buy_amount ?? null,
  };
  const brokerNames = new Set(summary.broker_display.split(",")
    .map((broker) => broker.trim().replace(/\(\d+\)$/, "").trim()).filter(Boolean));
  const reportSummary = {
    report_count: summary.mention_count, broker_count: brokerNames.size,
    broker_display: summary.broker_display, target_price_min: summary.target_price_min,
    target_price_max: summary.target_price_max, dominant_opinion: summary.dominant_opinion,
  };
  const notes = [`리포트 ${summary.mention_count}건`];
  const hasTargetPrice = [reportSummary.target_price_min, reportSummary.target_price_max, target.target_price_min, target.target_price_max]
    .some((value) => value !== null && value !== undefined);
  if (hasTargetPrice) {
    notes.push("목표가 있음");
    if (!target.available && target.unavailable_reason === "missing_base_close_price") notes.push("KRX 기준가 대기");
  } else notes.push("목표가 없음");
  notes.push(flow.available ? "당일 수급 있음" : "당일 수급 없음");
  notes.push(netBuyTop.available ? "외국인 순매수 상위 포함" : "외국인 순매수 상위 미포함");
  const availableHorizons = reactions.filter((item) => item.available).map((item) => `D+${item.horizon_days}`);
  const pendingHorizons = reactions.filter((item) => !item.available).map((item) => `D+${item.horizon_days}`);
  if (availableHorizons.length) notes.push(`${availableHorizons.join("/")} 반응 가능`);
  if (pendingHorizons.length) notes.push(`${pendingHorizons.join("/")} 대기`);

  return {
    business_date: summary.business_date, stock_code: summary.stock_code, stock_name: summary.stock_name,
    report_summary: reportSummary, base_market: marketReference(base), reaction_windows: reactions,
    target_observation: target, stock_flow_observation: flow, net_buy_top_observation: netBuyTop,
    evidence_notes: notes,
  };
}

export function buildBacktestObservationSnapshotFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  limit = 20,
  mentionThreshold = 2,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): BacktestObservationSnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid backtest observation date");
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) throw new RangeError("Backtest observation limit is outside the allowed range");
  if (!Number.isInteger(mentionThreshold) || mentionThreshold < 1 || mentionThreshold > 20) throw new RangeError("Backtest observation mention threshold is outside the allowed range");

  const summaries = database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
      target_price_min, target_price_max, dominant_opinion
    FROM daily_stock_summaries
    WHERE business_date = ? AND stock_code IS NOT NULL AND TRIM(stock_code) <> '' AND mention_count >= ?
    ORDER BY mention_count DESC, stock_name ASC
    LIMIT ?
  `).all(businessDate, mentionThreshold, limit) as SummaryRow[];
  const rows = summaries.map((summary) => backtestRow(database, summary));
  return {
    now: dateTimeIso(now, timezone), timezone, surface: "web-view", read_only: true,
    business_date: businessDate, available: rows.length > 0,
    data_scope: "stored_report_krx_backtest_observation", live_fetch: false,
    scoring: false, recommendation: false, mention_threshold: mentionThreshold,
    horizons: [...HORIZONS], notice: NOTICE, rows,
  };
}

export function getBacktestObservationSnapshot(
  businessDate: string,
  limit = 20,
  mentionThreshold = 2,
  now = new Date(),
): BacktestObservationSnapshot {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const snapshot = buildBacktestObservationSnapshotFromDatabase(database, businessDate, limit, mentionThreshold, now);
      database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
