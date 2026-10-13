import "server-only";

import type { DatabaseSync } from "node:sqlite";
import { isBusinessDate } from "../domain/daily.ts";
import { isTradingBusinessDay } from "./observation-summary.ts";
import { fetchNaverMarketTopStocks, NaverMarketTopError, type NaverMarket, type NaverMarketTopStock } from "./naver-market-top.ts";
import { fetchNaverQuoteSnapshot, type NaverQuoteSnapshot } from "./priority-current-quotes.ts";

const TOSS_SOURCE = "toss_openapi";

type DailySummary = {
  business_date?: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display?: string;
  target_price_min?: number | null;
  target_price_max?: number | null;
  dominant_opinion?: string | null;
};

type SectorRollup = {
  sector_name?: string | null;
  display_name?: string | null;
  report_count?: number | null;
};

type MarketIndex = {
  business_date: string;
  index_series: string;
  index_name: string;
  close_index: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
};

type MarketStock = {
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

type MarketFlow = {
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

type MarketBriefing = {
  turnover_reference_lines?: string[];
  flow_reference_lines?: string[];
  [key: string]: unknown;
};

function formatIndexPercent(value: number | null): string {
  if (value === null) return "-";
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    roundingMode: "halfEven",
    useGrouping: false,
  }).format(value);
  return `${value > 0 ? "+" : ""}${formatted}%`;
}

function formatIndexLevel(value: number | null): string {
  return value === null
    ? "-"
    : new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      roundingMode: "halfEven",
    }).format(value);
}

function formatAmount(value: number): string {
  const amount = Math.abs(value);
  if (amount >= 1_000_000_000_000) {
    return `${new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1, roundingMode: "halfEven", useGrouping: false }).format(amount / 1_000_000_000_000)}조`;
  }
  if (amount >= 100_000_000) {
    return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, roundingMode: "halfEven", useGrouping: false }).format(amount / 100_000_000)}억`;
  }
  return `${new Intl.NumberFormat("en-US").format(amount)}원`;
}

function marketDirection(value: number | null): string {
  if (value === null) return "확인불가";
  if (value >= 0.5) return "상승";
  if (value <= -0.5) return "하락";
  return "보합권";
}

function flowDirection(value: number | null): string {
  if (value === null || value === 0) return "중립";
  return value > 0 ? "순유입" : "순유출";
}

function marketDisplay(value: string | null): string {
  return ({ STK: "KOSPI", KOSPI: "KOSPI", KSQ: "KOSDAQ", KOSDAQ: "KOSDAQ", ALL: "전체" } as Record<string, string>)[value?.trim().toUpperCase() ?? ""] ?? "시장 미확인";
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

function targetPriceRange(summary: DailySummary): { min: number | null; max: number | null; available: boolean } {
  const min = summary.target_price_min ?? null;
  const max = summary.target_price_max ?? null;
  return { min, max, available: min !== null || max !== null };
}

function marketStockItem(item: MarketStock) {
  return {
    business_date: item.business_date,
    stock_code: item.stock_code,
    stock_name: item.stock_name,
    market: item.market,
    close_price: item.close_price,
    change_percent: item.change_percent,
    volume: item.volume,
    turnover: item.turnover,
    fetched_at: item.fetched_at,
  };
}

function marketFlowItem(item: MarketFlow) {
  return {
    business_date: item.business_date,
    market: item.market,
    market_label: marketDisplay(item.market),
    investor_type: item.investor_type,
    investor_label: investorDisplay(item.investor_type),
    sell_volume: item.sell_volume,
    buy_volume: item.buy_volume,
    net_buy_volume: item.net_buy_volume,
    sell_amount: item.sell_amount,
    buy_amount: item.buy_amount,
    net_buy_amount: item.net_buy_amount,
    volume_unit: item.volume_unit,
    amount_unit: item.amount_unit,
    source: item.source,
  };
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
  `).get(businessDate, TOSS_SOURCE, businessDate, TOSS_SOURCE, businessDate, TOSS_SOURCE, businessDate, TOSS_SOURCE) as { business_date: string } | undefined;
  return row?.business_date ?? null;
}

function dailySummaries(database: DatabaseSync, businessDate: string): DailySummary[] {
  return database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
           target_price_min, target_price_max, dominant_opinion
    FROM daily_stock_summaries
    WHERE business_date = ?
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as DailySummary[];
}

function marketIndices(database: DatabaseSync, businessDate: string, source?: string): MarketIndex[] {
  const rows = source === undefined
    ? database.prepare(`
      SELECT business_date, index_series, index_name, close_index, change_percent, volume, turnover
      FROM market_index_daily
      WHERE business_date = ?
      ORDER BY index_series ASC, index_name ASC
      LIMIT 200
    `).all(businessDate)
    : database.prepare(`
      SELECT business_date, index_series, index_name, close_index, change_percent, volume, turnover
      FROM market_index_daily
      WHERE business_date = ? AND source = ?
      ORDER BY index_series ASC, index_name ASC
      LIMIT 200
    `).all(businessDate, source);
  return rows as unknown as MarketIndex[];
}

function namedIndex(indices: MarketIndex[], series: string, name: string): MarketIndex | null {
  return indices.find((item) => item.index_series === series && item.index_name === name) ?? null;
}

function marketReferenceLabel(database: DatabaseSync, businessDate: string): string {
  const indices = marketIndices(database, businessDate);
  const labels = [namedIndex(indices, "KOSPI", "코스피"), namedIndex(indices, "KOSDAQ", "코스닥")]
    .filter((item): item is MarketIndex => item !== null)
    .flatMap((item) => {
      if (item.change_percent === null) return [];
      return [`${item.index_series.toUpperCase()} ${formatIndexPercent(item.change_percent)}`];
    });
  return labels.length ? labels.join(" / ") : "저장된 KOSPI/KOSDAQ 지수 참고값 없음";
}

function marketBriefingNotableStocks(summaries: DailySummary[]) {
  return summaries
    .slice()
    .sort((left, right) => right.mention_count - left.mention_count || compareText(left.stock_name, right.stock_name))
    .filter((item) => item.mention_count >= 2)
    .slice(0, 5)
    .map((item) => ({
      stock_name: item.stock_name,
      stock_code: item.stock_code,
      mention_count: item.mention_count,
      target_price_min: item.target_price_min ?? null,
      target_price_max: item.target_price_max ?? null,
      target_price_display: targetPriceRange(item),
    }));
}

function compareText(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function webViewIndexItem(item: MarketIndex) {
  return {
    business_date: item.business_date,
    index_series: item.index_series,
    index_name: item.index_name,
    close_index: item.close_index,
    change_percent: item.change_percent,
    volume: item.volume,
    turnover: item.turnover,
  };
}

function briefingIndexSummary(businessDate: string, referenceDate: string | null, kospi: MarketIndex | null, kosdaq: MarketIndex | null) {
  const picked = [kospi, kosdaq].filter((item): item is MarketIndex => item !== null);
  return {
    available: picked.length > 0,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    indices: picked.map(webViewIndexItem),
  };
}

function briefingTurnoverSummary(
  businessDate: string,
  referenceDate: string | null,
  rowsByMarket: Record<string, MarketStock[]>,
) {
  const markets = ["KOSPI", "KOSDAQ"].flatMap((market) => {
    const items = (rowsByMarket[market] ?? []).map((item) => ({
      ...marketStockItem(item),
      turnover_display: item.turnover === null ? "-" : formatAmount(item.turnover),
    }));
    return items.length ? [{ market, items }] : [];
  });
  const topItems = markets.flatMap((market) => market.items)
    .sort((left, right) => (right.turnover ?? 0) - (left.turnover ?? 0))
    .slice(0, 3);
  return {
    available: markets.length > 0,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    markets,
    top_items: topItems,
  };
}

function briefingFlowSummary(businessDate: string, referenceDate: string | null, rows: MarketFlow[]) {
  const byInvestor = new Map(rows.map((item) => [item.investor_type, item]));
  const items = ["개인", "외국인", "기관합계"].flatMap((investorType) => {
    const row = byInvestor.get(investorType);
    if (!row) return [];
    return [{ ...marketFlowItem(row), direction_label: flowDirection(row.net_buy_amount) }];
  });
  return {
    available: items.length > 0,
    business_date: businessDate,
    reference_date: referenceDate,
    exact_date_available: referenceDate === businessDate,
    market: "STK",
    market_label: "KOSPI",
    items,
  };
}

function formatFlowReferenceLine(rows: MarketFlow[], referenceDate: string, businessDate: string): string[] {
  const byInvestor = new Map(rows.map((item) => [item.investor_type, item]));
  const pieces = ([
    ["개인", "개인"], ["외국인", "외국인"], ["기관", "기관"],
  ] as const).flatMap(([label, key]) => {
    const row = byInvestor.get(key);
    return row?.net_buy_amount == null ? [] : [`${label} ${flowDirection(row.net_buy_amount)}`];
  });
  if (!pieces.length) return [];
  const suffix = referenceDate === businessDate ? "" : " / 리포트일 전 최신";
  return [`수급 참고 · ${referenceDate.slice(2).replaceAll("-", ".")} Toss KOSPI/KOSDAQ 저장값${suffix}`, `- ${pieces.join(" / ")}`];
}

function checkPointsFromCached(
  businessDate: string,
  referenceDate: string | null,
  kospi: MarketIndex | null,
  kosdaq: MarketIndex | null,
  flowFragment: string | null,
): string[] {
  const points: string[] = [];
  if (referenceDate !== null && kospi && kosdaq) {
    const prefix = referenceDate === businessDate ? "" : `${referenceDate.slice(2).replaceAll("-", ".")} 기준 `;
    points.push(`- ${prefix}KOSPI ${marketDirection(kospi.change_percent)}, KOSDAQ ${marketDirection(kosdaq.change_percent)} 흐름`);
  }
  if (flowFragment) points.push(`- KOSPI 수급 참고: ${flowFragment} 우위`);
  points.push("- 종목별 세부 근거는 사용자 웹뷰에서 확인");
  return ["확인 포인트", ...points.slice(0, 3)];
}

function checkPoints(lines: string[]): string[] {
  return lines.slice(1).flatMap((line) => {
    const point = line.replace(/^- /, "").trim();
    if (!point) return [];
    return [point.includes("사용자 웹뷰") ? "아래 종목/관찰 탭에서 세부 근거 확인" : point];
  });
}

function indexDirectionPoint(point: string): boolean {
  const normalized = point.replaceAll(" ", "");
  return (point.includes("KOSPI") || point.includes("코스피") || normalized.includes("코스피")) &&
    (point.includes("KOSDAQ") || point.includes("코스닥") || normalized.includes("코스닥")) &&
    (point.includes("흐름") || point.includes("하락") || point.includes("상승"));
}

function timeSlotMoodCard(
  businessDate: string,
  summaries: DailySummary[],
  indexSummary: ReturnType<typeof briefingIndexSummary>,
  turnoverSummary: ReturnType<typeof briefingTurnoverSummary>,
  flowSummary: ReturnType<typeof briefingFlowSummary>,
  notableStocks: ReturnType<typeof marketBriefingNotableStocks>,
  points: string[],
) {
  const reportCount = summaries.reduce((count, summary) => count + summary.mention_count, 0);
  const stockCount = summaries.length;
  const headline = reportCount <= 0 || stockCount <= 0
    ? "저장된 리포트 요약이 없어 시장 분위기 문구를 만들지 않음"
    : notableStocks.length
      ? `리포트 ${reportCount}건 중 ${notableStocks[0].stock_name || notableStocks[0].stock_code || "다건 언급 종목"} ${notableStocks[0].mention_count}건${notableStocks.length > 1 ? ` 외 ${notableStocks.length - 1}종목` : ""}이 눈에 띔`
      : `리포트 ${reportCount}건 / ${stockCount}종목, 다건 언급 종목은 제한적`;
  const sourceGaps = (["index", "turnover", "flow"] as const).flatMap((key) => {
    const summary = key === "index" ? indexSummary : key === "turnover" ? turnoverSummary : flowSummary;
    return summary.reference_date && summary.available && summary.reference_date !== businessDate
      ? [{ code: `${key}_stored_reference_fallback`, message: `${key} 참고값은 ${summary.reference_date} 저장값이며 선택일과 다릅니다.` }]
      : [];
  });
  const indexItems = indexSummary.indices.map((item) =>
    `${item.index_name || item.index_series}: ${formatIndexLevel(item.close_index)} ${formatIndexPercent(item.change_percent)}`);
  const turnoverItems = turnoverSummary.top_items.map((item) =>
    `${item.stock_name || item.stock_code}: ${item.turnover_display || "거래대금 저장값"}`);
  const notableItems = notableStocks.map((item) => {
    const targetMin = item.target_price_display.min;
    const targetMax = item.target_price_display.max;
    const target = !item.target_price_display.available
      ? ""
      : targetMin === null
        ? `${new Intl.NumberFormat("en-US").format(targetMax ?? 0)}원`
        : targetMax === null || targetMin === targetMax
          ? `${new Intl.NumberFormat("en-US").format(targetMin)}원`
          : `${new Intl.NumberFormat("en-US").format(targetMin)}원~${new Intl.NumberFormat("en-US").format(targetMax)}원`;
    return target
      ? `${item.stock_name || item.stock_code || "-"}: 리포트 ${item.mention_count}건 / 목표가 참고 ${target}`
      : `${item.stock_name || item.stock_code || "-"}: 리포트 ${item.mention_count}건`;
  });
  const flowItems = flowSummary.items.map((item) => `${item.investor_label}: ${item.direction_label || "방향 확인"}`);
  const corePoints = [`리포트 ${reportCount}건 / ${stockCount}종목 기준으로 압축`];
  if (indexSummary.indices.length) {
    const directions = indexSummary.indices.map((item) => `${item.index_name || item.index_series} ${marketDirection(item.change_percent)}`);
    if (directions.length) corePoints.push(`지수 참고: ${directions.join(" / ")}`);
  }
  if (flowItems.length) corePoints.push(`수급 참고: ${flowItems.slice(0, 3).join(" / ")}`);
  const cardCheckPoints = points.filter((point) => point && !indexDirectionPoint(point)).slice(0, 3);
  if (!indexSummary.exact_date_available) cardCheckPoints.push("지수와 등락률은 최신 저장 Toss 기준시각을 함께 확인");
  return {
    source: "stored_report_toss_market_mood_card",
    read_only: true,
    live_fetch: false,
    scoring: false,
    recommendation: false,
    production_integration: false,
    manual_review_candidate: true,
    business_date: businessDate,
    title: "국장 시장 분위기",
    reference_note: "당일 리포트와 저장된 Toss 기준값 참고",
    headline,
    sections: [
      { key: "indices", label: "지수", available: indexItems.length > 0, reference_date: indexSummary.reference_date, exact_date_available: indexSummary.exact_date_available, items: indexItems },
      { key: "notable_stocks", label: "주요 종목", available: notableItems.length > 0 || turnoverItems.length > 0, reference_date: businessDate, items: notableItems, turnover_reference_items: turnoverItems },
      { key: "core_points", label: "핵심 포인트", available: corePoints.length > 0, items: corePoints.slice(0, 4), flow_reference_items: flowItems },
      { key: "check_points", label: "확인 포인트", available: cardCheckPoints.length > 0, items: cardCheckPoints.slice(0, 4) },
    ],
    source_gaps: sourceGaps,
  };
}

/** Projects same-connection daily summary and sector rows into the Python market-mood DTO. */
export function buildMarketMoodSnapshot(
  businessDate: string | null,
  summaries: readonly DailySummary[],
  sectorRollups: readonly SectorRollup[],
) {
  const activeSectors = sectorRollups.filter((item) => {
    const name = item.sector_name || item.display_name;
    return !!name && name !== "N/A";
  });
  const topSector = activeSectors[0];
  return {
    business_date: businessDate,
    total_reports: summaries.reduce((count, summary) => count + summary.mention_count, 0),
    stock_count: summaries.length,
    active_sector_count: activeSectors.length,
    top_sector_name: topSector ? topSector.sector_name || topSector.display_name || null : null,
    top_sector_report_count: topSector
      ? Object.hasOwn(topSector, "report_count") ? topSector.report_count : 0
      : 0,
    multi_report_stock_count: summaries.filter((summary) => summary.mention_count >= 2).length,
    target_price_stock_count: summaries.filter((summary) => summary.target_price_min != null || summary.target_price_max != null).length,
  };
}

/** Reads stored Toss market evidence on the caller's read-only connection. */
export function buildWebViewMarketBriefingContext(
  database: DatabaseSync,
  businessDate: string,
  summaries = dailySummaries(database, businessDate),
  latestMarketReferenceDate?: string | null,
) {
  const referenceDate = latestMarketReferenceDate === undefined
    ? latestTossMarketDate(database, businessDate)
    : latestMarketReferenceDate;
  const indices = referenceDate ? marketIndices(database, referenceDate, TOSS_SOURCE) : [];
  const kospi = namedIndex(indices, "KOSPI", "코스피");
  const kosdaq = namedIndex(indices, "KOSDAQ", "코스닥");
  const rowsByMarket: Record<string, MarketStock[]> = {};
  if (referenceDate) {
    for (const market of ["KOSPI", "KOSDAQ"]) {
      rowsByMarket[market] = (database.prepare(`
        SELECT business_date, stock_code, stock_name, market, close_price,
               change_percent, volume, turnover, fetched_at
        FROM stock_market_daily
        WHERE business_date = ? AND market = ? AND source = ?
        ORDER BY COALESCE(turnover, 0) DESC, stock_code ASC
        LIMIT 3
      `).all(referenceDate, market, TOSS_SOURCE) as unknown as MarketStock[]).filter((item) => item.turnover !== null);
    }
  }
  const flowRows = referenceDate
    ? (["KOSPI", "KOSDAQ"] as const).flatMap((market) => database.prepare(`
      SELECT business_date, market, investor_type, sell_volume, buy_volume, net_buy_volume,
             sell_amount, buy_amount, net_buy_amount, volume_unit, amount_unit, source
      FROM market_investor_flow_daily
      WHERE business_date = ? AND market = ? AND source = ?
      ORDER BY investor_type ASC
    `).all(referenceDate, market, TOSS_SOURCE) as unknown as MarketFlow[])
    : [];
  const byInvestor = new Map(flowRows.map((item) => [item.investor_type, item]));
  const flowDirections = ([
    ["개인", "개인"], ["외국인", "외국인"], ["기관", "기관합계"],
  ] as const).flatMap(([label, key]) => {
    const amount = byInvestor.get(key)?.net_buy_amount;
    if (amount == null || amount === 0) return [];
    return [`${label} ${amount > 0 ? "매수" : "매도"}`];
  });
  const flowFragment = !flowDirections.length || !referenceDate
    ? null
    : `${referenceDate === businessDate ? "" : `${referenceDate.slice(2).replaceAll("-", ".")} 기준 `}${flowDirections.join(", ")}`;
  const suffix = referenceDate === null || referenceDate === businessDate ? "" : " / 리포트일 전 최신";
  const marketReferenceLines = !referenceDate || (!kospi && !kosdaq)
    ? []
    : [
      `지수 참고 · ${referenceDate.slice(2).replaceAll("-", ".")} Toss 저장값${suffix}`,
      `- ${[
        ...(kospi ? [`KOSPI ${formatIndexLevel(kospi.close_index)} ${formatIndexPercent(kospi.change_percent)}`] : []),
        ...(kosdaq ? [`KOSDAQ ${formatIndexLevel(kosdaq.close_index)} ${formatIndexPercent(kosdaq.change_percent)}`] : []),
      ].join(" / ")}`,
    ];
  const turnoverLines = ["KOSPI", "KOSDAQ"].flatMap((market) => {
    const rows = rowsByMarket[market] ?? [];
    return rows.length ? [`- ${market}: ${rows.map((item) => `${item.stock_name} ${formatAmount(item.turnover ?? 0)}`).join(" / ")}`] : [];
  });
  const turnoverReferenceLines = !referenceDate || !turnoverLines.length
    ? []
    : [`거래대금 참고 · ${referenceDate.slice(2).replaceAll("-", ".")} Toss 저장값${suffix}`, ...turnoverLines];
  const flowReferenceLines = referenceDate ? formatFlowReferenceLine(flowRows, referenceDate, businessDate) : [];
  const pointLines: string[] = [];
  if (referenceDate && kospi && kosdaq) {
    const prefix = referenceDate === businessDate ? "" : `${referenceDate.slice(2).replaceAll("-", ".")} 기준 `;
    pointLines.push(`- ${prefix}KOSPI ${marketDirection(kospi.change_percent)}, KOSDAQ ${marketDirection(kosdaq.change_percent)} 흐름`);
  }
  if (flowFragment) pointLines.push(`- KOSPI 수급 참고: ${flowFragment} 우위`);
  pointLines.push("- 종목별 세부 근거는 사용자 웹뷰에서 확인");
  const checkPointLines = ["확인 포인트", ...pointLines.slice(0, 3)];
  const indexSummary = briefingIndexSummary(businessDate, referenceDate, kospi, kosdaq);
  const turnoverSummary = briefingTurnoverSummary(businessDate, referenceDate, rowsByMarket);
  const flowSummary = briefingFlowSummary(businessDate, referenceDate, flowRows);
  const notableStocks = marketBriefingNotableStocks(summaries);
  const normalizedCheckPoints = checkPoints(checkPointLines);
  return {
    source: "stored_report_toss_market_briefing",
    live_fetch: false,
    scoring: false,
    recommendation: false,
    business_date: businessDate,
    market_reference_lines: marketReferenceLines,
    turnover_reference_lines: turnoverReferenceLines,
    flow_reference_lines: flowReferenceLines,
    check_point_lines: checkPointLines,
    index_summary: indexSummary,
    turnover_summary: turnoverSummary,
    flow_summary: flowSummary,
    notable_stocks: notableStocks,
    check_points: normalizedCheckPoints,
    time_slot_mood_card: timeSlotMoodCard(businessDate, summaries, indexSummary, turnoverSummary, flowSummary, notableStocks, normalizedCheckPoints),
  };
}

function previousReportDate(database: DatabaseSync, businessDate: string): string | null {
  const row = database.prepare(`
    SELECT business_date FROM reports
    WHERE business_date < ?
    GROUP BY business_date
    ORDER BY business_date DESC
    LIMIT 500
  `).get(businessDate) as { business_date: string } | undefined;
  return row?.business_date ?? null;
}

function sameDayReportStatus(
  businessDate: string,
  reportCount: number,
  summaries: DailySummary[],
  currentDate?: string,
) {
  const stockCodeCount = new Set(summaries.flatMap((item) => item.stock_code ? [item.stock_code] : [])).size;
  const outsideCurrentSession = currentDate !== undefined &&
    (currentDate !== businessDate || !isTradingBusinessDay(currentDate));
  const canOverlap = !outsideCurrentSession && summaries.length > 0 && stockCodeCount > 0;
  const reason = outsideCurrentSession
    ? "오늘 정규장 시간에만 확인 할 수 있습니다."
    : summaries.length <= 0
      ? "당일 리포트 요약이 없어 거래대금 교집합을 만들 수 없습니다."
      : stockCodeCount <= 0
        ? "종목 코드가 있는 당일 리포트 요약이 없어 거래대금 교집합을 만들 수 없습니다."
        : `리포트 요약 ${stockCodeCount}개 종목 기준으로 Naver 거래대금 상위와 교집합을 확인할 수 있습니다.`;
  return {
    business_date: businessDate,
    report_count: reportCount,
    summary_stock_count: summaries.length,
    summary_stock_code_count: stockCodeCount,
    can_overlap_intraday_market_top: canOverlap,
    reason,
  };
}

function emptyIntradayQuoteReference(limit = 10) {
  return { source: "naver_quote", live_fetch: false, writes_snapshot_tables: false, limit, delay_seconds: null, items: [], errors: [] };
}

function emptyIntradayMarketTopReference(emptyReason: string | null) {
  return {
    source: "naver_price_top",
    live_fetch: false,
    writes_snapshot_tables: false,
    markets: ["KOSPI", "KOSDAQ"],
    limit: 100,
    page_size: 20,
    delay_seconds: null,
    checked_at: null,
    items: [],
    errors: [],
    empty_reason: emptyReason,
  };
}

function commentaryStockNames(summaries: DailySummary[], limit: number): string {
  const names = summaries
    .slice()
    .sort((left, right) => right.mention_count - left.mention_count || compareText(left.stock_name, right.stock_name))
    .slice(0, Math.max(limit, 0))
    .map((item) => item.stock_name)
    .filter(Boolean);
  return names.length ? names.join(", ") : "확인 후보 없음";
}

/** Builds only the stored/default practice DTO; optional live Naver requests are omitted. */
export function buildMarketCommentaryPracticeSnapshot(
  database: DatabaseSync,
  businessDate: string | null,
  options: { summaries?: DailySummary[]; marketBriefing?: MarketBriefing; currentDate?: string } = {},
) {
  const resolvedDate = businessDate || (database.prepare("SELECT MAX(business_date) AS business_date FROM reports").get() as { business_date: string | null }).business_date;
  if (!resolvedDate) {
    return {
      surface: "market-commentary-practice",
      read_only: true,
      live_fetch: false,
      sends_telegram: false,
      registers_scheduler: false,
      business_date: null,
      market_reference: "저장된 리포트가 없습니다.",
      comments: [],
    };
  }
  const summaries = options.summaries ?? dailySummaries(database, resolvedDate);
  const reportCount = (database.prepare("SELECT COUNT(*) AS count FROM reports WHERE business_date = ?").get(resolvedDate) as { count: number }).count;
  const sameDayStatus = sameDayReportStatus(resolvedDate, reportCount, summaries, options.currentDate);
  const notableNames = summaries.slice(0, 3).map((summary) => summary.stock_name);
  const notableLabel = notableNames.length ? notableNames.join(", ") : "확인 후보 없음";
  const marketReference = marketReferenceLabel(database, resolvedDate);
  const openingDate = previousReportDate(database, resolvedDate);
  const openingSummaries = openingDate ? dailySummaries(database, openingDate) : [];
  const openingLabel = commentaryStockNames(openingSummaries, 2);
  const openingMarketReference = openingDate
    ? marketReferenceLabel(database, openingDate)
    : "전일 저장 리포트 기준 없음";
  const briefing = options.marketBriefing ?? buildWebViewMarketBriefingContext(database, resolvedDate, summaries);
  const turnoverDetails = (briefing.turnover_reference_lines ?? []).slice(1, 4).map((line) => line.replace("- ", ""));
  const flowDetails = (briefing.flow_reference_lines ?? []).slice(1, 4).map((line) => line.replace("- ", ""));
  const quoteReference = emptyIntradayQuoteReference();
  const marketTopReference = emptyIntradayMarketTopReference(sameDayStatus.can_overlap_intraday_market_top ? null : sameDayStatus.reason);
  const marketTopEmptyReason = marketTopReference.empty_reason;
  const comments = [
    {
      phase: "opening",
      time: "09:15",
      label: "장초반",
      reference_date: openingDate,
      comment: "",
      opinion: "당일 리포트가 쌓이기 전에는 전일 후보와 지수 참고를 분리해서 봅니다.",
      details: openingDate
        ? [`전일 후보: ${openingLabel}`, `전일 기준: ${openingDate}`, `전일 지수: ${openingMarketReference}`]
        : ["전일 후보: 없음", `당일 기준: ${resolvedDate}`],
    },
    {
      phase: "midday",
      time: "12:00",
      label: "점심",
      reference_date: resolvedDate,
      comment: `12:00에는 ${notableLabel} 리포트 집중과 거래대금 상위가 겹치는지 확인합니다.`,
      opinion: "오전 리포트 집중과 거래대금 상위가 겹치면 종목 탭에서 근거를 먼저 봅니다.",
      details: marketTopEmptyReason
        ? [String(marketTopEmptyReason)]
        : [...(notableNames.length ? [`우선 확인: ${notableLabel}`] : []), ...turnoverDetails.slice(0, 2)],
    },
    {
      phase: "preclose",
      time: "15:15",
      label: "장 마감 전",
      reference_date: resolvedDate,
      comment: "수급 전환이 반복되는 종목만 종목 탭에서 한 번 더 확인합니다.",
      opinion: "",
      details: flowDetails.slice(0, 3).length ? flowDetails.slice(0, 3) : ["종목별 [12009] 수급 저장값 대기"],
    },
  ];
  return {
    surface: "market-commentary-practice",
    read_only: true,
    live_fetch: false,
    sends_telegram: false,
    registers_scheduler: false,
    business_date: resolvedDate,
    market_reference: marketReference,
    report_count: reportCount,
    summary_stock_count: summaries.length,
    same_day_report_status: sameDayStatus,
    intraday_market_top_reference: marketTopReference,
    intraday_quote_reference: quoteReference,
    comments,
    boundary: { public_numeric_score: false, trading_recommendation: false, telegram_send: false },
  };
}

type IntradaySummary = { stock_code: string | null; stock_name: string; mention_count: number };
type IntradayMarketTopDependencies = {
  now?: Date;
  timezone?: string;
  delaySeconds?: number;
  fetchPage?: (market: NaverMarket, page: number, pageSize: number) => Promise<NaverMarketTopStock[]>;
  fetchQuote?: (stockCode: string) => Promise<NaverQuoteSnapshot>;
};

function timezoneParts(value: Date, timezone: string): Record<string, string> {
  return Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(value).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function dateInTimezone(value: Date, timezone: string): string {
  const parts = timezoneParts(value, timezone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function zonedDateTime(value: Date, timezone: string): string {
  const parts = timezoneParts(value, timezone);
  const offset = Math.round((Date.UTC(
    Number(parts.year), Number(parts.month) - 1, Number(parts.day),
    Number(parts.hour), Number(parts.minute), Number(parts.second), value.getUTCMilliseconds(),
  ) - value.getTime()) / 60_000);
  const sign = offset >= 0 ? "+" : "-";
  const minutes = Math.abs(offset);
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}.${String(value.getUTCMilliseconds()).padStart(3, "0")}${sign}${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function formatSignedPercent(value: number | null): string {
  return value === null || !Number.isFinite(value)
    ? "등락률 확인불가"
    : `${value > 0 ? "+" : ""}${new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 2, maximumFractionDigits: 2, roundingMode: "halfEven", useGrouping: false,
    }).format(value)}%`;
}

function intradayMarketTopDetailLines(reference: Record<string, unknown>): string[] {
  if (!Array.isArray(reference.items)) return [];
  return reference.items.flatMap((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return [];
    const item = value as Record<string, unknown>;
    const stockName = String(item.stock_name || item.stock_code || "-");
    const market = String(item.market || "-");
    const rank = typeof item.rank === "number" ? item.rank : null;
    const tradeAmount = typeof item.trade_amount === "number" ? item.trade_amount : null;
    const amountLabel = tradeAmount === null ? "거래대금 확인불가" : formatAmount(tradeAmount);
    const mentionCount = typeof item.mention_count === "number" ? item.mention_count : null;
    const mentionLabel = mentionCount === null ? "리포트 언급" : `리포트 ${mentionCount}건`;
    const rankLabel = rank === null ? `${market} 거래대금 상위` : `${market} 거래대금 ${rank}위`;
    return [`${stockName} 거래대금 ${amountLabel} · ${formatSignedPercent(typeof item.change_percent === "number" ? item.change_percent : null)} · ${rankLabel} · ${mentionLabel}`];
  });
}

function intradayQuoteDetailLines(reference: Record<string, unknown>): string[] {
  if (!Array.isArray(reference.items)) return [];
  return reference.items.flatMap((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return [];
    const item = value as Record<string, unknown>;
    const stockName = String(item.stock_name || item.stock_code || "-");
    const tradeAmount = typeof item.trade_amount === "number" ? item.trade_amount : null;
    const amountLabel = tradeAmount === null ? "거래대금 확인불가" : formatAmount(tradeAmount);
    const currentPrice = typeof item.current_price === "number" ? item.current_price : null;
    const priceLabel = currentPrice === null ? "현재가 확인불가" : `현재가 ${new Intl.NumberFormat("ko-KR").format(currentPrice)}원`;
    return [`${stockName} 거래대금 ${amountLabel} · ${formatSignedPercent(typeof item.change_percent === "number" ? item.change_percent : null)} · ${priceLabel}`];
  });
}

function firstNames(reference: Record<string, unknown>): string {
  if (!Array.isArray(reference.items) || reference.items.length === 0) return "확인 후보 없음";
  const names = reference.items.flatMap((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return [];
    const item = value as Record<string, unknown>;
    return [String(item.stock_name || item.stock_code || "").trim()];
  }).filter(Boolean).slice(0, 3);
  return names.join(", ") || "확인 후보 없음";
}

export async function buildIntradayMarketTopReference(
  summaries: readonly IntradaySummary[],
  options: IntradayMarketTopDependencies = {},
): Promise<Record<string, unknown>> {
  const now = options.now ?? new Date();
  const timezone = options.timezone?.trim() || process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  const limit = 100;
  const pageSize = 20;
  const delaySeconds = Math.max(0, options.delaySeconds ?? 0.5);
  const fetchPage = options.fetchPage ?? ((market, page, size) => fetchNaverMarketTopStocks(market, { page, pageSize: size }));
  const summaryByCode = new Map(summaries.flatMap((summary) => {
    const code = String(summary.stock_code || "").trim();
    return code ? [[code, summary] as const] : [];
  }));
  const items: Record<string, unknown>[] = [];
  const errors: { market: NaverMarket; page: string; error: string }[] = [];
  const seenCodes = new Set<string>();
  const markets: NaverMarket[] = ["KOSPI", "KOSDAQ"];
  let calls = 0;

  for (const market of markets) {
    for (let page = 1; page <= Math.ceil(limit / pageSize); page += 1) {
      if (delaySeconds > 0 && calls > 0) await new Promise((resolve) => setTimeout(resolve, delaySeconds * 1000));
      let rows: NaverMarketTopStock[];
      try {
        rows = await fetchPage(market, page, pageSize);
      } catch (error) {
        errors.push({
          market,
          page: String(page),
          error: error instanceof NaverMarketTopError ? error.code : "upstream_unavailable",
        });
        break;
      }
      calls += 1;
      if (rows.length === 0) break;
      for (const [offset, row] of rows.entries()) {
        if (row.stock_end_type && row.stock_end_type.toLowerCase() !== "stock") continue;
        const summary = summaryByCode.get(row.stock_code);
        if (!summary || seenCodes.has(row.stock_code)) continue;
        seenCodes.add(row.stock_code);
        items.push({
          source: "naver_price_top",
          market: row.market,
          rank: (page - 1) * pageSize + offset + 1,
          stock_name: row.stock_name || summary.stock_name,
          stock_code: row.stock_code,
          mention_count: summary.mention_count,
          current_price: row.current_price,
          change_price: row.change_price,
          change_percent: row.change_percent,
          trade_amount: row.trade_amount,
          trade_volume: row.trade_volume,
          market_status: row.market_status,
          trade_time: row.trade_time,
          checked_at: zonedDateTime(now, timezone),
          stock_end_type: row.stock_end_type,
        });
      }
      if (rows.length < pageSize) break;
    }
  }

  items.sort((left, right) =>
    Number(right.trade_amount ?? -1) - Number(left.trade_amount ?? -1) ||
    Number(right.mention_count ?? 0) - Number(left.mention_count ?? 0) ||
    compareText(String(right.stock_name ?? ""), String(left.stock_name ?? "")),
  );
  const emptyReason = items.length ? null : errors.length
    ? "Naver 거래대금 상위 확인 중 오류가 발생했습니다."
    : `거래대금 상위 ${limit} 안에는 언급 종목이 없습니다.`;
  return {
    source: "naver_price_top",
    live_fetch: true,
    writes_snapshot_tables: false,
    markets,
    limit,
    page_size: pageSize,
    delay_seconds: delaySeconds,
    checked_at: zonedDateTime(now, timezone),
    calls,
    items,
    errors,
    empty_reason: emptyReason,
  };
}

async function buildIntradayQuoteReference(
  summaries: readonly IntradaySummary[],
  dependencies: IntradayMarketTopDependencies,
): Promise<Record<string, unknown>> {
  const limit = summaries.length;
  if (!limit) return emptyIntradayQuoteReference(0);
  const fetchQuote = dependencies.fetchQuote ?? fetchNaverQuoteSnapshot;
  const items: Record<string, unknown>[] = [];
  const errors: Record<string, string>[] = [];
  const seenCodes = new Set<string>();
  for (const summary of summaries.slice(0, limit)) {
    const code = String(summary.stock_code || "").trim();
    if (!/^\d{6}$/.test(code)) {
      errors.push({ stock_name: summary.stock_name, error: "stock_code_not_resolved" });
      continue;
    }
    if (seenCodes.has(code)) continue;
    seenCodes.add(code);
    try {
      const quote = await fetchQuote(code);
      items.push({
        stock_name: quote.stock_name || summary.stock_name,
        stock_code: quote.stock_code,
        mention_count: summary.mention_count,
        current_price: quote.current_price,
        prev_close_price: quote.prev_close_price,
        change_price: quote.change_price,
        change_percent: quote.change_percent,
        trade_amount: quote.trade_amount,
        trade_volume: quote.trade_volume,
        market_status: quote.market_status,
        trade_time: quote.trade_time,
        sector_name: quote.sector_name,
        resolution_source: "summary_stock_code",
      });
    } catch {
      errors.push({ stock_name: summary.stock_name, stock_code: code, error: "upstream_unavailable" });
    }
  }
  items.sort((left, right) =>
    Number(right.trade_amount ?? -1) - Number(left.trade_amount ?? -1) ||
    Number(right.mention_count ?? 0) - Number(left.mention_count ?? 0) ||
    compareText(String(right.stock_name ?? ""), String(left.stock_name ?? "")),
  );
  return { source: "naver_quote", live_fetch: true, writes_snapshot_tables: false, limit, delay_seconds: 0, items, errors };
}

export async function overlayDailyIntradayMarketTop(
  base: Record<string, unknown>,
  expectedDate: string,
  dependencies: IntradayMarketTopDependencies = {},
): Promise<Record<string, unknown>> {
  if (!isBusinessDate(expectedDate) || base.business_date !== expectedDate || !base.market_commentary || typeof base.market_commentary !== "object") return base;
  const commentary = base.market_commentary as Record<string, unknown>;
  const status = commentary.same_day_report_status;
  if (!status || typeof status !== "object" ||
    commentary.business_date !== expectedDate ||
    (status as Record<string, unknown>).business_date !== expectedDate ||
    (status as Record<string, unknown>).can_overlap_intraday_market_top !== true) return base;

  const now = dependencies.now ?? new Date();
  const timezone = dependencies.timezone?.trim() || process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  if (dateInTimezone(now, timezone) !== expectedDate || !isTradingBusinessDay(expectedDate)) return base;

  const summaries = Array.isArray(base.stocks) ? base.stocks.filter((item): item is IntradaySummary =>
    !!item && typeof item === "object" && !Array.isArray(item) &&
    typeof (item as Record<string, unknown>).stock_name === "string" &&
    typeof (item as Record<string, unknown>).mention_count === "number",
  ).map((item) => ({
    stock_code: typeof (item as Record<string, unknown>).stock_code === "string" ? (item as Record<string, unknown>).stock_code as string : null,
    stock_name: (item as Record<string, unknown>).stock_name as string,
    mention_count: (item as Record<string, unknown>).mention_count as number,
  })) : [];
  const summaryByCode = new Map(summaries.flatMap((summary) => summary.stock_code ? [[summary.stock_code, summary] as const] : []));
  const candidateEvidence = base.priority_candidate_evidence;
  const candidateRows = candidateEvidence && typeof candidateEvidence === "object" && Array.isArray((candidateEvidence as Record<string, unknown>).rows)
    ? ((candidateEvidence as Record<string, unknown>).rows as Record<string, unknown>[]) : [];
  const prioritySummaries = candidateRows
    .filter((row) => row?.selected === true)
    .slice(0, 2)
    .flatMap((row) => {
      const code = String(row.stock_code || "").trim();
      const summary = summaryByCode.get(code);
      return summary ? [summary] : [];
    });

  const intradayQuoteReference = await buildIntradayQuoteReference(prioritySummaries, { ...dependencies, timezone });
  const intradayMarketTopReference = await buildIntradayMarketTopReference(summaries, { ...dependencies, now, timezone });
  const marketTopDetails = intradayMarketTopDetailLines(intradayMarketTopReference);
  const quoteDetails = intradayQuoteDetailLines(intradayQuoteReference);
  const notableLabel = summaries.slice(0, 3).map((summary) => summary.stock_name).join(", ") || "확인 후보 없음";
  const emptyReason = String(intradayMarketTopReference.empty_reason || "");
  const comments = Array.isArray(commentary.comments) ? commentary.comments.map((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return value;
    const item = value as Record<string, unknown>;
    if (item.phase === "midday") {
      const comment = marketTopDetails.length
        ? `12:00에는 Naver 거래대금 상위 기준 ${firstNames(intradayMarketTopReference)} 언급 겹침을 우선 확인합니다.`
        : quoteDetails.length
          ? `12:00에는 Naver 장중 quote 기준 ${firstNames(intradayQuoteReference)} 거래대금/등락률을 우선 확인합니다.`
          : `12:00에는 ${notableLabel} 리포트 집중과 거래대금 상위가 겹치는지 확인합니다.`;
      const turnoverDetails = Array.isArray((base.market_briefing as Record<string, unknown> | undefined)?.turnover_reference_lines)
        ? ((base.market_briefing as Record<string, unknown>).turnover_reference_lines as unknown[]).slice(1, 3).filter((line): line is string => typeof line === "string").map((line) => line.replace(/^- /, ""))
        : [];
      const details = marketTopDetails.length ? marketTopDetails.slice(0, 3)
        : quoteDetails.length ? quoteDetails.slice(0, 3)
          : emptyReason ? [emptyReason]
            : [...(summaries.length ? [`우선 확인: ${notableLabel}`] : []), ...turnoverDetails];
      return { ...item, comment, details };
    }
    if (item.phase === "preclose" && (!Array.isArray(item.details) || item.details.length === 0)) {
      return { ...item, details: marketTopDetails.slice(0, 3).length ? marketTopDetails.slice(0, 3) : quoteDetails.slice(0, 3).length ? quoteDetails.slice(0, 3) : ["종목별 [12009] 수급 저장값 대기"] };
    }
    return item;
  }) : [];

  return {
    ...base,
    now: now.toISOString(),
    market_commentary: {
      ...commentary,
      live_fetch: true,
      intraday_market_top_reference: intradayMarketTopReference,
      intraday_quote_reference: intradayQuoteReference,
      comments,
    },
  };
}
