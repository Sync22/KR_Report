import "server-only";

import { readFileSync } from "node:fs";
import type { DatabaseSync } from "node:sqlite";
import { dirname, resolve } from "node:path";

import { isBusinessDate } from "../domain/daily.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type DbRow = Record<string, unknown>;
type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
};
type MarketRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  market: string | null;
  close_price: number | null;
  change_percent: number | null;
  high_price: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
  source: string;
};
type FlowRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  market: string;
  investor_type: string;
  sell_volume: number | null;
  buy_volume: number | null;
  net_buy_volume: number | null;
  sell_amount: number | null;
  buy_amount: number | null;
  net_buy_amount: number | null;
  volume_unit: string;
  amount_unit: string;
  source: string;
};
type ReportRow = {
  business_date: string;
  stock_name: string;
  broker_name: string;
  published_at: string;
  target_price_value: number;
};
type NewsRow = {
  run_id: string;
  evidence_key: string;
  stock_code: string | null;
  stock_name: string;
  title: string;
  summary: string;
  published_at: string;
  url: string;
  canonical_url: string;
  created_at: string;
  relevance: string;
  relevance_reason: string;
  match_reason: string;
  sentiment: string;
  event_types: string[];
  stock_impact: string;
  source_lane: string;
  lineage_type: string;
  krx_reference_date: string | null;
};
type CategoryRollup = {
  category_type: "sector" | "theme";
  display_name: string;
  stock_count: number;
  report_count: number;
  snapshot_date: string | null;
  mapping_source: string;
};

const institutionLabels = ["금융투자", "보험", "투신", "사모", "은행", "연기금 등", "기타법인", "기타금융"];

function validInputs(businessDate: string, stockCode: string): void {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid stock detail date");
  if (!/^\d{6}$/.test(stockCode)) throw new RangeError("Invalid stock detail code");
}

function text(value: string | null | undefined): string {
  return value ?? "";
}

function compareText(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function compareDateTimes(left: string, right: string): number {
  const leftMilliseconds = Date.parse(left);
  const rightMilliseconds = Date.parse(right);
  const micros = (value: string, milliseconds: number) => {
    const fraction = value.match(/\.(\d+)(?=Z|[+-]\d{2}:\d{2}$|$)/)?.[1] ?? "";
    return milliseconds * 1000 + Number(fraction.padEnd(6, "0").slice(3, 6) || 0);
  };
  return compareNumbers(micros(left, leftMilliseconds), micros(right, rightMilliseconds));
}

function compareNumbers(left: number, right: number): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function roundHalfEven(value: number, digits = 0): number {
  const factor = 10 ** digits;
  const scaled = value * factor;
  const lower = Math.floor(scaled);
  const fraction = scaled - lower;
  const rounded = Math.abs(fraction - 0.5) < Number.EPSILON * Math.max(1, Math.abs(scaled))
    ? (lower % 2 === 0 ? lower : lower + 1)
    : fraction < 0.5 ? lower : lower + 1;
  return rounded / factor;
}

function formattedNumber(value: number): string {
  return Math.trunc(value).toLocaleString("en-US");
}

function formatTargetPrice(value: number | null): string {
  return value === null ? "목표가 없음" : `목표가 ${formattedNumber(value)}원`;
}

function formatTargetRange(minimum: number | null, maximum: number | null): string {
  if (minimum === null && maximum === null) return "목표가 없음";
  if (minimum === null) return `${formattedNumber(maximum!)}원`;
  if (maximum === null || minimum === maximum) return `${formattedNumber(minimum)}원`;
  return `${formattedNumber(minimum)}원~${formattedNumber(maximum)}원`;
}

function opinionDisplay(value: string | null): string {
  const normalized = text(value).trim().toLowerCase();
  const label = ({
    buy: "매수",
    neutral: "중립",
    hold: "중립",
    sell: "매도",
    "n/a": "의견 없음",
    na: "의견 없음",
    "-": "의견 없음",
  } as Record<string, string>)[normalized] ?? (value || "의견 없음");
  return label === "의견 없음" ? label : `리포트 표기: ${label}`;
}

function marketDisplay(value: string | null): string {
  const normalized = text(value).trim().toUpperCase();
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[normalized] ?? "시장 미확인";
}

function investorDisplay(value: string | null): string {
  const normalized = text(value).trim().toLowerCase();
  return ({
    foreign: "외국인", institution: "기관", individual: "개인",
    외국인: "외국인", 기관: "기관", 기관합계: "기관합계", 개인: "개인", 전체: "전체",
  } as Record<string, string>)[normalized] ?? "투자자 미확인";
}

function investorOrder(value: string): number {
  return ({ 외국인: 0, 기관합계: 1, 기관: 2, 개인: 3, 전체: 9 } as Record<string, number>)[investorDisplay(value)] ?? 99;
}

function dateTimeIso(date: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "00";
  const year = Number(part("year"));
  const month = Number(part("month"));
  const day = Number(part("day"));
  const hour = Number(part("hour"));
  const minute = Number(part("minute"));
  const second = Number(part("second"));
  const milliseconds = date.getUTCMilliseconds();
  const offsetMinutes = Math.round((Date.UTC(year, month - 1, day, hour, minute, second, milliseconds) - date.getTime()) / 60000);
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const offset = Math.abs(offsetMinutes);
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}:${part("second")}.${String(milliseconds).padStart(3, "0")}000${sign}${String(Math.floor(offset / 60)).padStart(2, "0")}:${String(offset % 60).padStart(2, "0")}`;
}

function reportTitleDisplay(value: string | null): string {
  const title = text(value).trim();
  if (!title) return "-";
  return title.replace(/\s+\([^()]{1,24}\)\s*$/, "").trim() || title;
}

function stockMarketReference(row: MarketRow | null): Record<string, unknown> | null {
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

function targetProgress(
  database: DatabaseSync,
  businessDate: string,
  stockCode: string,
  summary: SummaryRow | null,
  reference: MarketRow | null,
): Record<string, unknown> {
  if (!summary) return {
    available: false, gap_available: false, progress_available: false,
    validation_available: false, validation_window_days: null,
    max_progress_to_min_percent: null, max_progress_to_max_percent: null,
    hit_min_horizon_days: null, hit_max_horizon_days: null,
    validation_notice: "missing_selected_date_summary",
    notice: "선택 날짜의 저장 리포트 요약이 없어 목표가 도달 참고를 계산하지 않습니다.",
  };
  const targets = [summary.target_price_min, summary.target_price_max].filter((item): item is number => item !== null);
  const marketSeries = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, close_price, change_percent,
           high_price, volume, turnover, fetched_at, source
    FROM stock_market_daily
    WHERE business_date >= ? AND stock_code = ? AND source = ?
    ORDER BY business_date ASC LIMIT 21
  `).all(businessDate, stockCode, "krx") as unknown as MarketRow[];
  if (!summary.stock_code || !targets.length || !reference || reference.close_price === null) return {
    available: false, gap_available: false, progress_available: false,
    validation_available: false, validation_window_days: null,
    max_progress_to_min_percent: null, max_progress_to_max_percent: null,
    hit_min_horizon_days: null, hit_max_horizon_days: null,
    validation_notice: "missing_target_or_market_reference",
    policy: "range_only",
    notice: "목표가, 종목코드, 또는 선택일 Toss 저장 가격이 없어 계산하지 않습니다.",
  };

  const targetMin = Math.min(...targets);
  const targetMax = Math.max(...targets);
  const currentPrice = reference.close_price;
  const baselinePrice = reference.close_price;
  const percent = (numerator: number, denominator: number) => denominator === 0 ? null : roundHalfEven(numerator / denominator * 100, 2);
  const targetProgressPercent = (targetPrice: number) => {
    const numerator = currentPrice - baselinePrice;
    const denominator = targetPrice - baselinePrice;
    return denominator === 0 ? (numerator === 0 ? 0 : null) : percent(numerator, denominator);
  };
  const gaps = [percent(targetMin - currentPrice, currentPrice), percent(targetMax - currentPrice, currentPrice)].filter((item): item is number => item !== null);
  const progressMin = targetProgressPercent(targetMin);
  const progressMax = targetProgressPercent(targetMax);
  const validProgress = [progressMin, progressMax].filter((item): item is number => item !== null);
  const progressNotice = baselinePrice < targetMin ? "baseline_below_target_range"
    : baselinePrice > targetMax ? "baseline_above_target_range" : "baseline_inside_target_range";

  let validation: Record<string, unknown>;
  if (progressNotice !== "baseline_below_target_range") {
    validation = {
      validation_available: false, validation_window_days: null,
      max_progress_to_min_percent: null, max_progress_to_max_percent: null,
      hit_min_horizon_days: null, hit_max_horizon_days: null,
      validation_notice: progressNotice,
    };
  } else {
    const observed = marketSeries.flatMap((item, index) => item.close_price === null ? [] : [{ item, index }]);
    if (!observed.length) {
      validation = {
        validation_available: false, validation_window_days: null,
        max_progress_to_min_percent: null, max_progress_to_max_percent: null,
        hit_min_horizon_days: null, hit_max_horizon_days: null,
        validation_notice: "missing_market_series",
      };
    } else {
      const progressesMin = observed.map(({ item }) => percent(item.close_price! - baselinePrice, targetMin - baselinePrice)).filter((item): item is number => item !== null);
      const progressesMax = observed.map(({ item }) => percent(item.close_price! - baselinePrice, targetMax - baselinePrice)).filter((item): item is number => item !== null);
      const hitMin = observed.find(({ item }) => item.close_price! >= targetMin)?.index ?? null;
      const hitMax = observed.find(({ item }) => item.close_price! >= targetMax)?.index ?? null;
      validation = {
        validation_available: !!(progressesMin.length || progressesMax.length || hitMin !== null || hitMax !== null),
        validation_window_days: Math.max(...observed.map(({ index }) => index)),
        max_progress_to_min_percent: progressesMin.length ? Math.max(...progressesMin) : null,
        max_progress_to_max_percent: progressesMax.length ? Math.max(...progressesMax) : null,
        hit_min_horizon_days: hitMin,
        hit_max_horizon_days: hitMax,
        validation_notice: "stored_window_only",
      };
    }
  }

  return {
    available: !!(gaps.length || validProgress.length),
    gap_available: !!gaps.length,
    progress_available: !!validProgress.length,
    ...validation,
    policy: "range_only",
    baseline_date: businessDate,
    baseline_price: baselinePrice,
    current_date: summary.business_date,
    current_price: currentPrice,
    target_price_min: targetMin,
    target_price_max: targetMax,
    target_gap_min_percent: gaps.length ? Math.min(...gaps) : null,
    target_gap_max_percent: gaps.length ? Math.max(...gaps) : null,
    progress_to_min_percent: progressMin,
    progress_to_max_percent: progressMax,
    progress_caution: progressNotice !== "baseline_below_target_range",
    progress_notice: progressNotice,
    notice: "목표가 범위 기준 괴리율/진행률입니다. 저장 데이터 기반 확인용입니다.",
  };
}

function targetRevisionDirection(current: number | null, previous: number | null): [string | null, string | null] {
  if (current === null || previous === null) return [null, null];
  if (current > previous) return ["up", "상향"];
  if (current < previous) return ["down", "하향"];
  return ["flat", "유지"];
}

function targetRevisionLabel(current: number | null, previous: number | null): string | null {
  if (current === null || previous === null) return null;
  if (current > previous) return "이전 대비 상향 참고";
  if (current < previous) return "이전 대비 하향 참고";
  return "이전 대비 유지 참고";
}

function targetRevisionSummary(current: number | null, previous: number | null, direction: string | null): string {
  if (current === null || previous === null || direction === null) return "최근 조정 없음";
  if (direction === "up") return `목표가 ↑ ${formattedNumber(previous)} → ${formattedNumber(current)}`;
  if (direction === "down") return `목표가 ↓ ${formattedNumber(previous)} → ${formattedNumber(current)}`;
  return `목표가 유지 ${formattedNumber(current)}`;
}

function targetReportRows(database: DatabaseSync, businessDate: string, stockCode: string): ReportRow[] {
  return database.prepare(`
    SELECT business_date, stock_name, broker_name, published_at, target_price_value
    FROM reports
    WHERE stock_code = ? AND business_date <= ? AND target_price_value IS NOT NULL
    ORDER BY business_date DESC, published_at DESC, broker_name ASC
    LIMIT 200
  `).all(stockCode, businessDate) as unknown as ReportRow[];
}

function targetPriceTrail(rows: ReportRow[], businessDate: string, stockCode: string, currentPrice: number | null): Record<string, unknown> {
  const reportItems = rows.slice(0, 6).map((row) => {
    const previous = rows.find((candidate) => candidate.broker_name === row.broker_name && candidate.business_date < row.business_date);
    const [direction, directionLabel] = targetRevisionDirection(row.target_price_value, previous?.target_price_value ?? null);
    const target = row.target_price_value;
    const [year, month, day] = row.business_date.slice(2).split("-");
    return {
      business_date: row.business_date,
      broker_name: row.broker_name,
      published_at: row.published_at,
      target_price_value: target,
      target_price_display: formatTargetRange(target, target),
      previous_target_price_value: previous?.target_price_value ?? null,
      direction,
      direction_label: directionLabel,
      display: `${year}.${month}.${day} · ${row.broker_name} · ${formattedNumber(target)}원 · ${directionLabel ?? "최근 조정 없음"}`,
    };
  });
  const latest = rows[0]?.target_price_value ?? null;
  const latestPrevious = rows.length ? rows.slice(1).find((row) => row.broker_name === rows[0].broker_name && row.business_date < rows[0].business_date) : undefined;
  const previousTarget = latestPrevious?.target_price_value ?? null;
  const [direction, directionLabel] = targetRevisionDirection(latest, previousTarget);
  const attainment = currentPrice !== null && latest !== null && latest !== 0
    ? roundHalfEven(currentPrice / latest * 100, 1)
    : null;
  const byDate = new Map<string, ReportRow[]>();
  for (const row of rows) byDate.set(row.business_date, [...(byDate.get(row.business_date) ?? []), row]);
  const groups = [...byDate.entries()].slice(0, 6);
  const dailyGroups = groups.map(([reportDate, items], index) => {
    const targets = items.map((item) => item.target_price_value);
    const brokers = new Set(items.map((item) => item.broker_name).filter(Boolean));
    const minimum = Math.min(...targets);
    const maximum = Math.max(...targets);
    const average = targets.reduce((sum, item) => sum + item, 0) / targets.length;
    const previousItems = groups[index + 1]?.[1] ?? [];
    const previousAverage = previousItems.length
      ? previousItems.reduce((sum, item) => sum + item.target_price_value, 0) / previousItems.length
      : null;
    const revision = targetRevisionLabel(average, previousAverage);
    const display = `${reportDate.slice(2).replaceAll("-", ".")} 목표가 ${formatTargetRange(minimum, maximum)} · ${targets.length}건 · 증권사 ${brokers.size}곳${revision ? ` · ${revision}` : ""}`;
    return {
      business_date: reportDate,
      target_price_min: minimum,
      target_price_max: maximum,
      target_price_display: formatTargetRange(minimum, maximum),
      report_count: targets.length,
      broker_count: brokers.size,
      average_target_price: roundHalfEven(average),
      previous_average_target_price: previousAverage === null ? null : roundHalfEven(previousAverage),
      revision_label: revision,
      display,
    };
  });
  return {
    available: !!reportItems.length,
    source: "stored_reports",
    live_fetch: false,
    scoring: false,
    recommendation: false,
    business_date: businessDate,
    stock_code: stockCode,
    summary: targetRevisionSummary(latest, previousTarget, direction),
    direction,
    direction_label: directionLabel,
    latest_report_date: rows[0]?.business_date ?? null,
    current_price: currentPrice,
    current_target_price: latest,
    attainment_percent: attainment,
    items: reportItems,
    daily_groups: dailyGroups,
    notice: reportItems.length
      ? "저장된 리포트 목표가 흐름입니다. 목표가 변화는 참고값이며 판단 문구를 포함하지 않습니다."
      : "저장된 목표가 리포트가 없습니다.",
  };
}

function targetJourney(database: DatabaseSync, rows: ReportRow[], businessDate: string, stockCode: string): Record<string, unknown> {
  const items = rows.slice(0, 6).map((row, index) => {
    const previous = rows.slice(index + 1).find((candidate) => candidate.broker_name === row.broker_name);
    const [, directionLabel] = targetRevisionDirection(row.target_price_value, previous?.target_price_value ?? null);
    const series = database.prepare(`
      SELECT business_date, stock_code, stock_name, market, close_price, change_percent,
             high_price, volume, turnover, fetched_at, source
      FROM stock_market_daily
      WHERE business_date >= ? AND stock_code = ? AND source = ?
      ORDER BY business_date ASC LIMIT 120
    `).all(row.business_date, stockCode, "krx") as unknown as MarketRow[];
    let hitIndex: number | null = null;
    let hitDate: string | null = null;
    const observed: number[] = [];
    let latestClose: number | null = null;
    series.forEach((market, marketIndex) => {
      if (market.close_price !== null) latestClose = market.close_price;
      const price = market.high_price ?? market.close_price;
      if (price === null) return;
      observed.push(price);
      if (hitIndex === null && price >= row.target_price_value) {
        hitIndex = marketIndex;
        hitDate = market.business_date;
      }
    });
    const target = row.target_price_value;
    return {
      report_date: row.business_date,
      broker_name: row.broker_name,
      published_at: row.published_at,
      target_price_value: target,
      target_price_display: formatTargetRange(target, target),
      revision_direction_label: directionLabel,
      status: !observed.length ? "no_market_data" : hitIndex !== null ? "hit" : "in_progress",
      hit_date: hitDate,
      hit_trading_days: hitIndex,
      current_attainment_percent: latestClose !== null && target ? roundHalfEven(latestClose / target * 100, 1) : null,
      max_attainment_percent: observed.length && target ? roundHalfEven(Math.max(...observed) / target * 100, 1) : null,
      observed_through: series.at(-1)?.business_date ?? null,
    };
  });
  return {
    available: !!items.length,
    source: "stored_reports_and_stock_market_daily",
    live_fetch: false,
    scoring: false,
    recommendation: false,
    business_date: businessDate,
    stock_code: stockCode,
    price_basis: "high_price_then_close_price",
    items,
    notice: items.length
      ? "저장 리포트 목표가별 도달 기록입니다. 달성 여부는 판단 문구가 아니라 저장 가격 흐름 기준 기록입니다."
      : "저장된 목표가 리포트가 없어 목표가 Journey를 계산하지 않습니다.",
  };
}

function volumeContext(database: DatabaseSync, businessDate: string, stockCode: string): Record<string, unknown> {
  const rows = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, close_price, change_percent,
           volume, turnover, fetched_at, source
    FROM stock_market_daily
    WHERE business_date <= ? AND stock_code = ? AND source = ?
    ORDER BY business_date DESC LIMIT 20
  `).all(businessDate, stockCode, "toss_openapi") as unknown as MarketRow[];
  const referenceDate = rows[0]?.business_date ?? null;
  return {
    available: !!rows.length,
    source: rows.length ? "toss_openapi" : null,
    live_fetch: false,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    items: rows.map((row) => ({
      business_date: row.business_date,
      stock_code: row.stock_code,
      stock_name: row.stock_name,
      market: row.market,
      market_label: marketDisplay(row.market),
      close_price: row.close_price,
      change_percent: row.change_percent,
      volume: row.volume,
      volume_unit: "주",
      source: row.source,
    })),
    notice: rows.length ? "저장된 Toss 거래량 기준입니다." : "선택 종목의 거래량 데이터가 없습니다.",
  };
}

function flowRows(database: DatabaseSync, businessDate: string, stockCode: string): FlowRow[] {
  return database.prepare(`
    SELECT business_date, stock_code, stock_name, market, investor_type,
           sell_volume, buy_volume, net_buy_volume, sell_amount, buy_amount, net_buy_amount,
           volume_unit, amount_unit, source
    FROM stock_investor_flow_daily
    WHERE business_date = ? AND stock_code = ? AND source = ?
    ORDER BY investor_type ASC
  `).all(businessDate, stockCode, "toss_openapi") as unknown as FlowRow[];
}

function investorFlowItem(row: FlowRow): Record<string, unknown> {
  return {
    business_date: row.business_date,
    stock_code: row.stock_code,
    stock_name: row.stock_name,
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
  };
}

function sumFlow(rows: FlowRow[], labels: Set<string>, field: "net_buy_volume" | "buy_volume" | "sell_volume"): number | null {
  let total = 0;
  let found = false;
  for (const row of rows) {
    if (labels.has(investorDisplay(row.investor_type)) && row[field] !== null) {
      total += row[field]!;
      found = true;
    }
  }
  return found ? total : null;
}

function flowTabs(database: DatabaseSync, businessDate: string, stockCode: string): Record<string, unknown> {
  const dates = database.prepare(`
    SELECT business_date FROM stock_investor_flow_daily WHERE business_date <= ? AND source = ?
    UNION SELECT business_date FROM market_investor_flow_daily WHERE business_date <= ? AND source = ?
    UNION SELECT business_date FROM investor_net_buy_top_daily WHERE business_date <= ? AND source = ?
    ORDER BY business_date DESC LIMIT 93
  `).all(businessDate, "toss_openapi", businessDate, "toss_openapi", businessDate, "toss_openapi") as unknown as { business_date: string }[];
  const retail: Record<string, unknown>[] = [];
  const institution: Record<string, unknown>[] = [];
  for (const { business_date: flowDate } of dates) {
    const rows = flowRows(database, flowDate, stockCode);
    if (!rows.length) continue;
    retail.push({
      business_date: flowDate,
      individual: sumFlow(rows, new Set(["개인"]), "net_buy_volume"),
      foreign: sumFlow(rows, new Set(["외국인"]), "net_buy_volume"),
      institution: sumFlow(rows, new Set(["기관", "기관합계"]), "net_buy_volume"),
      individual_buy: sumFlow(rows, new Set(["개인"]), "buy_volume"),
      individual_sell: sumFlow(rows, new Set(["개인"]), "sell_volume"),
      foreign_buy: sumFlow(rows, new Set(["외국인"]), "buy_volume"),
      foreign_sell: sumFlow(rows, new Set(["외국인"]), "sell_volume"),
      institution_buy: sumFlow(rows, new Set(["기관", "기관합계"]), "buy_volume"),
      institution_sell: sumFlow(rows, new Set(["기관", "기관합계"]), "sell_volume"),
    });
    institution.push({
      business_date: flowDate,
      values: Object.fromEntries(institutionLabels.map((label) => [label, sumFlow(rows, new Set([label]), "net_buy_volume")])),
    });
    if (retail.length >= 31) break;
  }
  const referenceDate = retail.length ? retail[0].business_date as string : null;
  return {
    available: !!retail.length,
    source: retail.length ? "toss_openapi" : null,
    live_fetch: false,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    volume_unit: "주",
    retail_foreign_institution: retail,
    institution_detail: { columns: institutionLabels, rows: institution },
    notice: retail.length
      ? "저장된 Toss 우선 후보 수급 기준입니다."
      : "선택일 Toss 20:00 저장 우선 후보 수급 데이터가 없습니다.",
  };
}

function investorFlow(database: DatabaseSync, businessDate: string, stockCode: string): Record<string, unknown> {
  const rows = flowRows(database, businessDate, stockCode).sort((left, right) =>
    investorOrder(left.investor_type) - investorOrder(right.investor_type) || compareText(investorDisplay(left.investor_type), investorDisplay(right.investor_type)));
  return {
    available: !!rows.length,
    source: rows.length ? "toss_openapi" : null,
    data_scope: "stored_toss_close_priority_flow",
    live_fetch: false,
    scoring: false,
    snapshot_date: rows.length ? businessDate : null,
    notice: rows.length
      ? "저장된 Toss 우선 후보 수급 참고입니다. 확정 판단은 포함하지 않습니다."
      : "선택일 Toss 20:00 저장 우선 후보 수급 데이터가 없습니다.",
    rows: rows.map(investorFlowItem),
  };
}

function normalizeNewsIdentity(value: string | null): string {
  return text(value).trim().toLocaleLowerCase();
}

function eventTypes(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  if (typeof value !== "string") return [];
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function newsRows(database: DatabaseSync, businessDate: string, stockCode: string, stockName: string | null): { rows: NewsRow[]; matchingRuns: boolean } {
  const runs = database.prepare(`
    SELECT run_id, stock_code, stock_name FROM news_intelligence_runs
    WHERE target_date = ? ORDER BY created_at DESC, run_id DESC LIMIT 100
  `).all(businessDate) as unknown as { run_id: string; stock_code: string | null; stock_name: string | null }[];
  const normalizedName = normalizeNewsIdentity(stockName);
  const matching = runs.filter((run) => run.stock_code === stockCode || (!!normalizedName && normalizeNewsIdentity(run.stock_name) === normalizedName));
  const rows: NewsRow[] = [];
  for (const run of runs) {
    if (run.stock_code !== null && run.stock_code !== stockCode) continue;
    if (run.stock_code === null && normalizedName && normalizeNewsIdentity(run.stock_name) !== normalizedName) continue;
    const evidence = database.prepare(`
      SELECT run_id, evidence_key, stock_code, stock_name, title, summary, published_at, url,
             canonical_url, created_at, relevance, relevance_reason, match_reason, sentiment,
             event_types_json, stock_impact, source_lane, lineage_type, krx_reference_date
      FROM report_linked_news_evidence
      WHERE run_id = ?
      ORDER BY target_date DESC, created_at DESC, evidence_key
      LIMIT 20
    `).all(run.run_id) as unknown as DbRow[];
    for (const raw of evidence) {
      const row = {
        ...raw,
        event_types: eventTypes(raw.event_types_json),
        lineage_type: typeof raw.lineage_type === "string" && raw.lineage_type ? raw.lineage_type : "unknown",
      } as unknown as NewsRow;
      if (row.stock_code === stockCode || (!!normalizedName && normalizeNewsIdentity(row.stock_name) === normalizedName)) rows.push(row);
    }
  }
  const latest = new Map<string, NewsRow>();
  for (const row of rows) {
    const key = row.canonical_url || row.evidence_key || row.url || `${row.stock_code ?? "None"}:${row.title}:${row.published_at}`;
    const old = latest.get(key);
    if (!old || compareDateTimes(row.created_at, old.created_at) > 0 ||
      (compareDateTimes(row.created_at, old.created_at) === 0 && compareText(row.run_id, old.run_id) > 0)) latest.set(key, row);
  }
  return { rows: [...latest.values()], matchingRuns: matching.length > 0 };
}

function cautionNews(row: NewsRow): boolean {
  return ["Caution", "Negative", "Mixed"].includes(row.sentiment) ||
    ["Caution", "Negative", "Strong Negative"].includes(row.stock_impact) || row.event_types.includes("Risk/Caution");
}

function positiveDirectNews(row: NewsRow): boolean {
  return !(row.source_lane === "top2_search" && row.lineage_type !== "independent") && row.relevance === "direct" &&
    (row.sentiment === "Positive" || ["Positive", "Strong Positive"].includes(row.stock_impact));
}

function primaryCautionNews(row: NewsRow): boolean {
  return !(row.source_lane === "top2_search" && row.lineage_type !== "independent") && row.relevance === "direct" && cautionNews(row);
}

function newsDigestKind(row: NewsRow): string {
  return row.relevance === "direct" ? "종목 직접 매칭" : row.relevance === "market_context" ? "시장 맥락" : "참고 뉴스";
}

function newsLineageLabel(row: NewsRow): string {
  return row.lineage_type === "independent" ? "독립 확인" : row.lineage_type === "report_recap" ? "리포트 재인용" : "독립성 미확인";
}

function newsDigestPriority(row: NewsRow): number {
  const lineage = row.lineage_type === "independent" ? 0 : 10;
  return lineage + (row.relevance === "direct" ? 0 : row.relevance === "market_context" ? 1 : 2);
}

function newsDigestLabel(row: NewsRow): string {
  let result = (row.title || row.summary || "").trim().replace(/\s+/g, " ");
  const stockName = row.stock_name.trim();
  if (stockName) result = result.replace(new RegExp(`^${stockName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*[,，:：·-]?\\s*`), "").trim();
  result = result.replace(/^[\s\-:：,，·]+|[\s\-:：,，·]+$/g, "");
  if (!result) result = row.relevance_reason || row.match_reason || newsDigestKind(row);
  const chars = Array.from(result);
  return chars.length <= 44 ? result : `${chars.slice(0, 43).join("").trimEnd()}…`;
}

function digestItems(rows: NewsRow[], limit: number): Record<string, unknown>[] {
  const ordered = [...rows].sort((left, right) =>
    newsDigestPriority(left) - newsDigestPriority(right) || compareDateTimes(right.published_at, left.published_at) || compareText(left.title, right.title));
  const seen = new Set<string>();
  const items: Record<string, unknown>[] = [];
  for (const row of ordered) {
    const label = newsDigestLabel(row);
    const date = row.published_at.slice(0, 10);
    const key = `${date}\0${newsDigestKind(row)}\0${label}`;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push({
      date,
      stock_name: row.stock_name || row.stock_code || "-",
      label,
      evidence_label: newsDigestKind(row),
      lineage_type: row.lineage_type,
      lineage_label: newsLineageLabel(row),
      relevance: row.relevance,
      source_lane: row.source_lane,
    });
    if (items.length >= Math.max(limit, 0)) break;
  }
  return items;
}

function uniqueTexts(values: string[], limit: number): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const item = value.trim();
    if (!item || seen.has(item)) continue;
    seen.add(item);
    result.push(item);
    if (result.length >= Math.max(limit, 0)) break;
  }
  return result;
}

function emptyNewsBadge(collected: boolean): Record<string, unknown> {
  return {
    available: collected,
    display_label: collected ? "매칭 뉴스 없음" : "뉴스 근거 수집 전",
    reason: collected ? "수집은 완료됐지만 이 후보와 직접 연결된 뉴스는 없었습니다." : "저장 뉴스 근거를 아직 수집하지 않았습니다.",
    connection_label: collected ? "매칭 뉴스 없음" : "뉴스 근거 수집 전",
    connection_reason: collected ? "수집은 실행됐고, 선택 날짜의 후보와 직접 연결된 뉴스는 없었습니다." : "저장 뉴스 근거가 수집되면 후보와 연결됩니다.",
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

function newsObservationDetail(database: DatabaseSync, businessDate: string, stockCode: string, stockName: string | null): Record<string, unknown> {
  const { rows, matchingRuns } = newsRows(database, businessDate, stockCode, stockName);
  if (!rows.length) {
    const badge = emptyNewsBadge(matchingRuns);
    return {
      source: "stored_news_intelligence_observation",
      read_only: true,
      live_fetch: false,
      ...badge,
      top_titles: [],
      empty_state: badge.display_label,
      missing_context: ["stored_news_observation"],
    };
  }
  const independent = rows.filter((row) => row.lineage_type === "independent");
  const direct = rows.filter((row) => row.relevance === "direct").length;
  const caution = rows.filter(cautionNews).length;
  const positive = rows.filter(positiveDirectNews).length;
  const primaryCaution = rows.filter(primaryCautionNews).length;
  const marketContext = rows.filter((row) => row.relevance === "market_context").length;
  const reportRecap = rows.filter((row) => row.lineage_type === "report_recap").length;
  const unknown = rows.length - independent.length - reportRecap;
  const krxDates = rows.flatMap((row) => row.krx_reference_date ? [row.krx_reference_date] : []);
  const krxStatus = krxDates.includes(businessDate) ? "exact" : krxDates.length ? "stale" : "missing";
  let evidenceDirection: string;
  let evidenceDirectionReason: string;
  if (positive && primaryCaution) {
    evidenceDirection = "직접 근거 상충";
    evidenceDirectionReason = `직접 긍정 뉴스 ${positive}건과 직접 주의 뉴스 ${primaryCaution}건이 함께 있습니다.`;
  } else if (positive) {
    evidenceDirection = "상승 근거 우세";
    evidenceDirectionReason = `직접 긍정 뉴스 ${positive}건이 직접 주의 뉴스보다 우세합니다.`;
  } else if (primaryCaution) {
    evidenceDirection = "하방 위험 우세";
    evidenceDirectionReason = `직접 주의 뉴스 ${primaryCaution}건이 있어 리포트 근거를 다시 확인합니다.`;
  } else if (direct) {
    evidenceDirection = "직접 근거 중립";
    evidenceDirectionReason = `직접 연결 뉴스 ${direct}건은 있으나 방향 근거가 분명하지 않습니다.`;
  } else {
    evidenceDirection = "직접 근거 부족";
    evidenceDirectionReason = "후보와 직접 연결된 방향 근거가 아직 부족합니다.";
  }
  let connectionLabel: string;
  let connectionReason: string;
  if (primaryCaution > 0 && positive <= 0) {
    connectionLabel = "주의 뉴스 매칭";
    connectionReason = "주의/혼합 성격의 뉴스가 후보와 직접 매칭됐습니다.";
  } else if (direct > 0) {
    connectionLabel = "종목 뉴스 매칭";
    connectionReason = `후보와 직접 매칭된 뉴스 ${direct}건이 저장돼 있습니다.`;
  } else if (caution > 0) {
    connectionLabel = "주의 뉴스 매칭";
    connectionReason = "주의/혼합 성격의 뉴스가 후보와 매칭됐습니다.";
  } else if (marketContext > 0) {
    connectionLabel = "시장 맥락 참고";
    connectionReason = "업종/시장 맥락 뉴스라 종목 직접 근거로 과신하지 않습니다.";
  } else {
    connectionLabel = "관련 뉴스 매칭";
    connectionReason = "후보와 간접 연결된 저장 뉴스가 있습니다.";
  }
  if (!independent.length && reportRecap) {
    connectionLabel = "리포트 재인용 매칭";
    connectionReason = `후보와 연결된 리포트 재인용 뉴스 ${reportRecap}건이 저장돼 있습니다.`;
    evidenceDirection = "리포트 재인용 흐름";
    evidenceDirectionReason = "리포트 내용을 재인용한 뉴스 흐름이며 별도 독립 근거로 중복 계산하지 않습니다.";
  } else if (!independent.length) {
    connectionLabel = "종목 뉴스 매칭";
    connectionReason = `후보와 직접 매칭된 뉴스 ${rows.length}건이 저장돼 있으며 출처 계보는 확인 전입니다.`;
    evidenceDirection = "출처 계보 확인 전";
    evidenceDirectionReason = "종목 매칭은 확인됐고 독립 원출처 여부는 별도 메타데이터로 남깁니다.";
  }
  const ordered = [...rows].sort((left, right) =>
    (left.relevance === "direct" ? 0 : left.relevance === "indirect" ? 1 : 2) -
      (right.relevance === "direct" ? 0 : right.relevance === "indirect" ? 1 : 2) ||
      compareDateTimes(left.created_at, right.created_at) || compareText(left.title, right.title));
  const topTitle = uniqueTexts(ordered.map((row) => row.title), 1)[0] ?? null;
  const digest = digestItems(rows, 5);
  return {
    source: "stored_news_intelligence_observation",
    read_only: true,
    live_fetch: false,
    available: true,
    display_label: connectionLabel,
    reason: topTitle || "저장 뉴스 observation이 같은 후보와 연결됩니다.",
    direct_count: direct,
    positive_direct_count: positive,
    primary_caution_count: primaryCaution,
    caution_count: caution,
    market_context_count: marketContext,
    independent_count: independent.length,
    report_recap_count: reportRecap,
    unknown_count: unknown,
    krx_reference_status: krxStatus,
    observed_at: rows.reduce((latest, row) => compareDateTimes(row.created_at, latest) > 0 ? row.created_at : latest, rows[0].created_at),
    evidence_direction: evidenceDirection,
    evidence_direction_reason: evidenceDirectionReason,
    top_title: topTitle,
    digest_label: (digest[0]?.label as string | undefined) ?? null,
    news_digest: digest,
    connection_label: connectionLabel,
    connection_reason: connectionReason,
    top_titles: uniqueTexts(ordered.map((row) => row.title), 3),
  };
}

function flowAmount(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000_000) return `${roundHalfEven(absolute / 1_000_000_000_000, 1).toFixed(1)}조`;
  if (absolute >= 100_000_000) return `${roundHalfEven(absolute / 100_000_000)}억`;
  return `${formattedNumber(absolute)}원`;
}

function readEtfMappings(): Map<string, string[]> {
  const root = resolve(process.cwd(), "..");
  const configured = process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH?.trim();
  const coordinatePath = resolve(root, configured || "data/rotation_overlay_coordinates.json");
  let payload: unknown;
  try {
    payload = JSON.parse(readFileSync(resolve(dirname(coordinatePath), "rotation_etf_candidates.json"), "utf8"));
  } catch {
    return new Map();
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return new Map();
  const record = payload as DbRow;
  if (!Array.isArray(record.mappings)) return new Map();
  const mappings = new Map<string, string[]>();
  for (const raw of record.mappings) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) continue;
    const item = raw as DbRow;
    const status = text(typeof item.status === "string" ? item.status : null).trim().toLowerCase();
    if (status && status !== "active") continue;
    const type = text(typeof item.category_type === "string" ? item.category_type : null).trim();
    const displayName = text(typeof item.category_display_name === "string" ? item.category_display_name : null).trim();
    if (!type || !displayName || !Array.isArray(item.etf_codes)) continue;
    const codes = item.etf_codes.map((code) => String(code).trim()).filter(Boolean);
    if (codes.length) mappings.set(`${type}\0${displayName}`, codes);
  }
  return mappings;
}

function categoryRollups(database: DatabaseSync, businessDate: string, type: "sector" | "theme", stockCode: string): CategoryRollup[] {
  const latest = database.prepare(`
    SELECT MAX(snapshot_date) AS snapshot_date FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
  `).get(type, businessDate)?.snapshot_date;
  if (typeof latest === "string") {
    return database.prepare(`
      WITH latest_snapshots AS (
        SELECT cms.display_name, MAX(cms.snapshot_date) AS snapshot_date
        FROM category_membership_snapshots cms
        JOIN category_master cm ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
        WHERE cms.category_type = ? AND cms.snapshot_date <= ? AND cm.enabled = 1
        GROUP BY cms.display_name
      ), category_stock_rows AS (
        SELECT cms.display_name, cms.snapshot_date,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
               MAX(dss.mention_count) AS mention_count,
               MAX(CASE WHEN dss.stock_code = ? THEN 1 ELSE 0 END) AS contains_stock
        FROM daily_stock_summaries dss
        JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
        JOIN latest_snapshots latest ON latest.display_name = cms.display_name AND latest.snapshot_date = cms.snapshot_date
        WHERE dss.business_date = ? AND cms.category_type = ?
        GROUP BY cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
      )
      SELECT display_name, snapshot_date, COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count, MAX(contains_stock) AS contains_stock
      FROM category_stock_rows
      GROUP BY display_name, snapshot_date
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(type, businessDate, stockCode, businessDate, type).flatMap((row) => {
      const item = row as unknown as { display_name: string; snapshot_date: string; stock_count: number; report_count: number; contains_stock: number };
      return item.contains_stock ? [{ category_type: type, display_name: item.display_name, stock_count: item.stock_count,
        report_count: item.report_count, snapshot_date: item.snapshot_date, mapping_source: "dated_snapshot" }] : [];
    });
  }

  const disabledRows = database.prepare(`
    SELECT category_key, display_name FROM category_master WHERE category_type = ? AND enabled = 0
  `).all(type) as unknown as { category_key: string; display_name: string }[];
  const disabled = new Set(disabledRows.flatMap((row) => [row.category_key, row.display_name]));
  if (type === "sector") {
    return (database.prepare(`
      WITH summary_with_sector AS (
        SELECT COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS display_name,
               NULLIF(TRIM(sm.sector_code), '') AS sector_code,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
               dss.mention_count,
               CASE WHEN dss.stock_code = ? THEN 1 ELSE 0 END AS contains_stock
        FROM daily_stock_summaries dss LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
        WHERE dss.business_date = ?
      )
      SELECT display_name, MIN(sector_code) AS category_key,
             COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count,
             MAX(contains_stock) AS contains_stock
      FROM summary_with_sector GROUP BY display_name
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(stockCode, businessDate) as unknown as { display_name: string; category_key: string | null; stock_count: number; report_count: number; contains_stock: number }[])
      .filter((row) => row.contains_stock && !disabled.has(row.display_name) && !disabled.has(row.category_key || ""))
      .map((row) => ({ category_type: type, display_name: row.display_name, stock_count: row.stock_count,
        report_count: row.report_count, snapshot_date: null, mapping_source: "latest_mapping_fallback" }));
  }
  return (database.prepare(`
    WITH theme_stock_rows AS (
      SELECT COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS display_name,
             stm.theme_code AS theme_code,
             COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
             MAX(dss.mention_count) AS mention_count,
             MAX(CASE WHEN dss.stock_code = ? THEN 1 ELSE 0 END) AS contains_stock
      FROM daily_stock_summaries dss JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
      WHERE dss.business_date = ?
      GROUP BY COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code), COALESCE(dss.stock_code, dss.stock_name)
    )
    SELECT display_name, MIN(theme_code) AS category_key,
           COUNT(DISTINCT stock_identity) AS stock_count,
           COALESCE(SUM(mention_count), 0) AS report_count,
           MAX(contains_stock) AS contains_stock
    FROM theme_stock_rows GROUP BY display_name
    ORDER BY report_count DESC, stock_count DESC, display_name ASC
  `).all(stockCode, businessDate) as unknown as { display_name: string; category_key: string; stock_count: number; report_count: number; contains_stock: number }[])
    .filter((row) => row.contains_stock && !disabled.has(row.display_name) && !disabled.has(row.category_key))
    .map((row) => ({ category_type: type, display_name: row.display_name, stock_count: row.stock_count,
      report_count: row.report_count, snapshot_date: null, mapping_source: "latest_mapping_fallback" }));
}

function relatedEtfs(database: DatabaseSync, businessDate: string, etfCodes: string[]): Record<string, unknown>[] {
  const codes = [...new Set(etfCodes.map((code) => code.trim()).filter(Boolean))].sort();
  if (!codes.length) return [];
  const placeholders = codes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT etf_code, etf_name, close_price, change_percent, turnover, underlying_index_name
    FROM etf_daily_snapshots
    WHERE business_date = ? AND etf_code IN (${placeholders}) AND source = ?
    ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
    LIMIT 3
  `).all(businessDate, ...codes, "toss_openapi") as unknown as {
    etf_code: string; etf_name: string; close_price: number | null; change_percent: number | null;
    turnover: number | null; underlying_index_name: string | null;
  }[];
  return rows.map((row) => ({
    ...row,
    evidence_label: row.turnover === null ? "저장 ETF 참고" : `거래대금 ${flowAmount(row.turnover)}`,
  }));
}

function relatedContext(database: DatabaseSync, businessDate: string, stockCode: string): Record<string, unknown> {
  const mappings = readEtfMappings();
  const categories: Record<string, unknown>[] = [];
  for (const type of ["sector", "theme"] as const) {
    for (const rollup of categoryRollups(database, businessDate, type, stockCode)) {
      const categoryLabel = type === "sector" ? "업종" : "테마";
      const categoryDisplayName = !rollup.display_name || rollup.display_name === "N/A"
        ? (type === "sector" ? "업종 미확인" : "테마 미확인")
        : rollup.display_name;
      const etfs = relatedEtfs(database, businessDate, mappings.get(`${type}\0${rollup.display_name}`) ?? []);
      categories.push({
        category_type: type,
        category_label: categoryLabel,
        display_name: rollup.display_name,
        category_display_name: categoryDisplayName,
        public_category_id: `${type}|${rollup.display_name}|${rollup.snapshot_date ?? "fallback"}`,
        stock_count: rollup.stock_count,
        report_count: rollup.report_count,
        snapshot_date: rollup.snapshot_date,
        mapping_source: rollup.mapping_source,
        related_etfs: etfs,
        display: `${categoryLabel} ${categoryDisplayName} · 리포트 ${rollup.report_count}건 · ${rollup.stock_count}종목`,
        etf_notice: etfs.length ? "수동 ETF 매핑과 선택 날짜 저장 ETF 기준" : "저장 ETF 매핑 또는 선택 날짜 ETF 스냅샷 없음",
      });
      if (categories.length >= 4) break;
    }
    if (categories.length >= 4) break;
  }
  return {
    available: !!categories.length,
    source: "stored_category_rollup",
    etf_source: "manual_mapping_stored_toss_etf_snapshot",
    live_fetch: false,
    scoring: false,
    recommendation: false,
    business_date: businessDate,
    stock_code: stockCode,
    categories,
    notice: categories.length ? "선택 종목이 포함된 저장 업종/테마와 수동 ETF 매핑 참고입니다." : "선택 종목의 저장 업종/테마 참고가 없습니다.",
  };
}

export function buildStockDetailSnapshotFromDatabase(database: DatabaseSync, businessDate: string, stockCode: string): Record<string, unknown> {
  validInputs(businessDate, stockCode);
  const reports = database.prepare(`
    SELECT stock_name, stock_code, title, broker_name, published_at,
           target_price_value, opinion_normalized, source_url
    FROM reports
    WHERE business_date = ? AND stock_code = ?
    ORDER BY published_at DESC, broker_name ASC, title ASC
  `).all(businessDate, stockCode) as unknown as {
    stock_name: string; stock_code: string; title: string; broker_name: string; published_at: string;
    target_price_value: number | null; opinion_normalized: string | null; source_url: string | null;
  }[];
  const marketRow = database.prepare(`
    SELECT business_date, stock_code, stock_name, market, close_price, change_percent,
           high_price, volume, turnover, fetched_at, source
    FROM stock_market_daily
    WHERE business_date = ? AND stock_code = ? AND source = ?
    ORDER BY stock_code ASC LIMIT 1
  `).get(businessDate, stockCode, "toss_openapi") as unknown as MarketRow | undefined;
  const krxMetadata = database.prepare(`
    SELECT stock_name FROM krx_stock_metadata WHERE stock_code = ? AND business_date <= ?
    ORDER BY business_date DESC, fetched_at DESC LIMIT 1
  `).get(stockCode, businessDate) as unknown as { stock_name: string } | undefined;
  const stockMetadata = database.prepare("SELECT stock_name FROM stock_metadata WHERE stock_code = ?")
    .get(stockCode) as unknown as { stock_name: string } | undefined;
  const stockName = reports[0]?.stock_name ?? marketRow?.stock_name ?? krxMetadata?.stock_name ?? stockMetadata?.stock_name ?? null;
  const summary = database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display, target_price_min, target_price_max
    FROM daily_stock_summaries WHERE business_date = ? AND stock_code = ?
    ORDER BY mention_count DESC, stock_name ASC LIMIT 1
  `).get(businessDate, stockCode) as unknown as SummaryRow | undefined;
  const current = new Date();
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  const flow = investorFlow(database, businessDate, stockCode);
  const flowTabsDto = flowTabs(database, businessDate, stockCode);
  const news = newsObservationDetail(database, businessDate, stockCode, stockName);
  const targetRows = targetReportRows(database, businessDate, stockCode);
  const progress = targetProgress(database, businessDate, stockCode, summary ?? null, marketRow ?? null);
  const trail = targetPriceTrail(targetRows, businessDate, stockCode, marketRow?.close_price ?? null);
  const journey = targetJourney(database, targetRows, businessDate, stockCode);
  const volume = volumeContext(database, businessDate, stockCode);
  const related = relatedContext(database, businessDate, stockCode);
  const tossDate = marketRow?.business_date ?? null;
  const flowDate = (flow.snapshot_date as string | null) || (flowTabsDto.reference_date as string | null) || null;
  const newsAvailable = news.available === true;
  const newsCounts = [news.direct_count, news.caution_count, news.market_context_count, news.independent_count, news.report_recap_count, news.unknown_count]
    .some((item) => typeof item === "number" && item > 0);
  const valueContext = {
    report_reference_date: reports.length ? businessDate : null,
    toss_reference_date: tossDate,
    current_price_reference_time: marketRow && marketRow.close_price !== null ? marketRow.fetched_at : null,
    current_price_basis: marketRow && marketRow.close_price !== null ? "Toss stored snapshot" : null,
    turnover_reference_date: marketRow && marketRow.turnover !== null ? tossDate : null,
    investor_flow_reference_date: flowDate,
    news_collection_status: !newsAvailable ? "next_check_needed" : newsCounts ? "stored_evidence" : "stored_no_match",
    missing_labels: [
      ...(!reports.length ? ["report"] : []),
      ...(!tossDate ? ["toss"] : []),
      ...(!(marketRow && marketRow.close_price !== null) ? ["current_price"] : []),
      ...(!(marketRow && marketRow.turnover !== null) ? ["turnover"] : []),
      ...(!flowDate ? ["investor_flow"] : []),
    ],
  };
  return {
    now: dateTimeIso(current, timezone),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    stock_code: stockCode,
    stock_name: stockName,
    has_selected_date_report: !!reports.length,
    report_empty_state: reports.length ? null : "선택 날짜에 등록된 리포트가 없습니다.",
    market_reference: stockMarketReference(marketRow ?? null),
    value_context: valueContext,
    target_price_progress: progress,
    target_price_trail: trail,
    target_journey: journey,
    related_context: related,
    news_observation_detail: news,
    recent_volume_days: volume,
    investor_flow: flow,
    investor_flow_tabs: flowTabsDto,
    reports: reports.map((report) => ({
      stock_name: report.stock_name,
      stock_code: report.stock_code,
      title: report.title,
      title_display: reportTitleDisplay(report.title),
      broker_name: report.broker_name,
      published_at: report.published_at,
      target_price_value: report.target_price_value,
      target_price_display: formatTargetPrice(report.target_price_value),
      opinion_normalized: report.opinion_normalized,
      opinion_display: opinionDisplay(report.opinion_normalized),
      source_url: report.source_url,
    })),
  };
}

export function getStockDetailSnapshot(businessDate: string, stockCode: string): Record<string, unknown> {
  validInputs(businessDate, stockCode);
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const snapshot = buildStockDetailSnapshotFromDatabase(database, businessDate, stockCode);
      database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
