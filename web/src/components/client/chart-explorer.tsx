// Lucian UX/UI Prompt #400 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#400 · synchronized crosshair behavior adapted for price and indicator panes.
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useDailyTabs } from "@/components/client/daily-tabs";
import {
  isChartExplorerResponse,
  isChartExplorerSymbol,
  type ChartExplorerBar,
  type ChartExplorerChartBar,
  type ChartExplorerResponse,
  type ChartExplorerSuccess,
  type ChartExplorerTimeframe,
} from "@/domain/chart-explorer";
import { hasVisibleChartBar, panChartRange, resolveChartRange, zoomChartRange, type ChartRange } from "@/domain/chart-viewport";
import { calculateChartLabIndicators, type ChartLabIndicatorPoint } from "@/domain/chart-lab/indicators";
import { detectChartLabPatterns, type ChartLabPattern } from "@/domain/chart-lab/patterns";
import { evaluateChartLabEntry, type ChartLabEntryResult, type ChartLabStrategy } from "@/domain/chart-lab/entry";
import { isStockSearchSnapshot, type StockSearchItem } from "@/domain/stocks";
import { buildChartReadout } from "@/domain/chart-readout";
import ChartLabMonitorPanel from "@/components/client/chart-lab-monitor-panel";
import ChartLabReportAlertPanel from "@/components/client/chart-lab-report-alert-panel";
import { ChartLabAnalysisPanels, ChartLabPatternOverlay, ChartLabSignalOverlay, CHART_LAB_STRATEGIES } from "@/components/client/chart-lab-panels";
import { addNonPassiveChartWheelListener } from "@/components/client/chart-wheel";

const WATCHLIST_KEY = "stock-monitor-chart-watchlist-v1";
const PERIODS: { key: ChartExplorerTimeframe; label: string }[] = [
  { key: "1d", label: "일봉" }, { key: "1w", label: "주봉" }, { key: "4h", label: "4시간" }, { key: "1mo", label: "월봉" },
];
const SERIES = [
  ["rsi14", "RSI 14"], ["macd", "MACD 12·26·9"], ["obv", "OBV · 누적 거래량"], ["atr14", "ATR 14"], ["volume", "거래량"], ["hidden", "숨김"],
] as const;
type SeriesKey = (typeof SERIES)[number][0];
type WatchGroup = { name: string; items: { symbol: string; name: string }[] };
type ChartBar = ChartExplorerChartBar;
type UnknownRecord = Record<string, unknown>;
type ChartOverlayKey = "sma" | "ema" | "wma" | "bollinger" | "donchian" | "patterns" | "signals";
type ChartOverlayLine = { key: string; label: string; color: string; dash?: string; values: Array<number | null> };

function record(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : {};
}

function isCalculationBar(value: unknown): value is ChartExplorerBar {
  const item = record(value);
  const numbers = [item.open, item.high, item.low, item.close, item.volume];
  return typeof item.time === "string" && Number.isFinite(Date.parse(item.time)) && numbers.every(finite) &&
    (item.open as number) > 0 && (item.high as number) > 0 && (item.low as number) > 0 && (item.close as number) > 0 && (item.volume as number) >= 0 &&
    (item.high as number) >= Math.max(item.open as number, item.low as number, item.close as number) &&
    (item.low as number) <= Math.min(item.open as number, item.high as number, item.close as number);
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function numberLabel(value: unknown, digits = 2): string {
  return finite(value) ? new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(value) : "자료 없음";
}

function timeLabel(value: unknown): string {
  if (typeof value !== "string") return "기준 시각 없음";
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Seoul" }).format(parsed) : value;
}

function axisTimeLabel(value: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime())
    ? new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Seoul" }).format(parsed)
    : value;
}

function chartTimeLabel(value: string | null, timeframe: unknown): string {
  if (!value) return "자료 없음";
  const formatted = axisTimeLabel(value);
  return timeframe === "4h" && value.includes("T") ? `${formatted} KST` : formatted;
}

function timeframeLabel(value: unknown): string {
  return PERIODS.find((period) => period.key === value)?.label ?? "주기 미확인";
}

function structureFamilyLabel(value: unknown): string {
  return ({ horizontal: "수평 가격 기준", flag: "깃대 구조", triangle: "삼각형 구조" } as Record<string, string>)[String(value)] ?? "가격 구조";
}

function structureMeasurementValue(value: unknown, unit: unknown, name: unknown, currency: string | null): string {
  const states: Record<string, string> = {
    "prior-20-high": "직전 20봉 고가 기준", "prior-10-low": "직전 10봉 저가 기준",
    "volume-confirmed": "거래량 확인", "volume-insufficient": "거래량 부족",
    channel: "채널", triangle: "삼각형", "bull-flag": "상승 깃대", "bear-flag": "하락 깃대",
    "symmetrical-triangle": "대칭 삼각형", "ascending-triangle": "상승 삼각형", "descending-triangle": "하락 삼각형",
  };
  if (unit === "date" || !finite(value)) return states[String(value)] ?? String(value ?? "자료 없음");
  const formatted = numberLabel(value, 2);
  if (unit === "price" || unit === "projected-price") return currency ? `${formatted} ${currency}` : formatted;
  if (unit === "price-per-bar") return `${formatted} ${currency ?? ""}/봉`.trim();
  if (unit === "volume") return `${formatted}주`;
  if (unit === "bars" || unit === "projected-bars") return `${formatted}봉`;
  if (unit === "count") return `${formatted}개`;
  if (unit === "ratio") return /volume/i.test(String(name)) ? `${value.toFixed(2)}배` : `${(value * 100).toFixed(1)}%`;
  return formatted;
}

function displayName(snapshot: ChartExplorerResponse): string {
  return snapshot.display_name || snapshot.symbol || "종목";
}

function getStatusLabel(value: unknown): string {
  return ({ confirmed: "확정 봉", provisional: "잠정 봉", unknown: "확정 상태 미확인", ready: "계산됨", "partial-data": "일부 자료", "insufficient-data": "자료 부족", "no-geometry": "조건에 맞는 구조 없음", forming: "형성 중", expired: "관측 종료", retested: "재확인 관측", "breakout-pending": "추가 확인 필요", failed: "조건 미충족", unavailable: "계산 자료 없음" } as Record<string, string>)[String(value)] ?? (typeof value === "string" && value ? value : "상태 자료 없음");
}

function unavailableReasonLabel(value: unknown): string {
  return ({
    invalid_query: "요청한 기준일·종목·주기를 확인하세요.",
    unsupported_instrument_type: "주식 티커만 조회할 수 있습니다.",
    symbol_not_found: "선택일 저장 종목에서 이 코드를 찾지 못했습니다.",
    symbol_mapping_unavailable: "선택일 Toss 시장 분류가 없어 국내 4시간 봉을 요청하지 않았습니다.",
    stored_lookup_unavailable: "선택일 저장 종목을 확인할 수 없습니다.",
    toss_not_configured: "Toss 읽기 전용 연결 설정이 준비되지 않았습니다.",
    provider_timeout: "외부 자료 제공처의 응답이 시간 초과되었습니다.",
    provider_http_error: "외부 자료 제공처가 요청을 완료하지 못했습니다. 잠시 후 다시 조회하세요.",
    provider_unavailable: "외부 자료 제공처에 연결할 수 없습니다.",
    rate_limited: "외부 종목 조회가 잠시 제한되었습니다. 1분 뒤 다시 조회하세요.",
    invalid_provider_response: "외부 자료 형식이나 응답 값을 확인할 수 없습니다.",
    no_chart_data: "선택한 기준일까지 표시할 봉 자료가 없습니다.",
  } as Record<string, string>)[String(value)] ?? "차트 자료를 제공할 수 없습니다.";
}

function loadWatchGroups(value: string | null): WatchGroup[] {
  if (!value) return [{ name: "기본", items: [] }];
  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [{ name: "기본", items: [] }];
    const groups = parsed.flatMap((raw): WatchGroup[] => {
      const row = record(raw);
      if (typeof row.name !== "string" || !row.name.trim() || !Array.isArray(row.items)) return [];
      const items = row.items.flatMap((item): { symbol: string; name: string }[] => {
        const entry = record(item);
        return typeof entry.symbol === "string" && isChartExplorerSymbol(entry.symbol) && typeof entry.name === "string"
          ? [{ symbol: entry.symbol, name: entry.name.slice(0, 80) }]
          : [];
      }).slice(0, 100);
      return [{ name: row.name.trim().slice(0, 32), items }];
    }).slice(0, 12);
    return groups.length ? groups : [{ name: "기본", items: [] }];
  } catch { return [{ name: "기본", items: [] }]; }
}

function selectedNumber(group: UnknownRecord, key: string): number | null {
  return finite(group[key]) ? group[key] as number : null;
}

function ChartIndicatorDetails({ snapshot }: Readonly<{ snapshot: ChartExplorerSuccess }>) {
  const indicators = snapshot.snapshot.indicators;
  const formatPair = (left: unknown, right: unknown) => `${numberLabel(left, 4)} / ${numberLabel(right, 4)}`;
  const rows: [string, string, string][] = [
    ["SMA 20 / 60 / 120 / 200", [indicators.movingAverages.sma20, indicators.movingAverages.sma60, indicators.movingAverages.sma120, indicators.movingAverages.sma200].map((value) => numberLabel(value, 4)).join(" / "), indicators.movingAverages.status],
    ["EMA 20 / 60 / 120 / 200", [indicators.movingAverages.ema20, indicators.movingAverages.ema60, indicators.movingAverages.ema120, indicators.movingAverages.ema200].map((value) => numberLabel(value, 4)).join(" / "), indicators.movingAverages.status],
    ["WMA 20 / 60 / 120 / 200", [indicators.movingAverages.wma20, indicators.movingAverages.wma60, indicators.movingAverages.wma120, indicators.movingAverages.wma200].map((value) => numberLabel(value, 4)).join(" / "), indicators.movingAverages.status],
    ["Bollinger 20 · 하단 / 중간 / 상단", [indicators.bollinger20.lower, indicators.bollinger20.middle, indicators.bollinger20.upper].map((value) => numberLabel(value, 4)).join(" / "), indicators.bollinger20.status],
    ["Donchian 20 · 하단 / 중간 / 상단", [indicators.donchian20.lower, indicators.donchian20.middle, indicators.donchian20.upper].map((value) => numberLabel(value, 4)).join(" / "), indicators.donchian20.status],
    ["MACD / Signal / Histogram", [indicators.macd129.macd, indicators.macd129.signal, indicators.macd129.histogram].map((value) => numberLabel(value, 4)).join(" / "), indicators.macd129.status],
    ["RSI 14", numberLabel(indicators.rsi14.value), indicators.rsi14.status],
    ["ATR 14", numberLabel(indicators.atr14.value, 4), indicators.atr14.status],
    ["OBV / 5봉 변화", formatPair(indicators.obv.value, indicators.obv.delta5), indicators.obv.status],
    ["거래량 / 20봉 평균", indicators.volume.ratio20 === null ? "자료 없음" : `${numberLabel(indicators.volume.ratio20)}배`, indicators.volume.status],
  ];
  return <details className="chart-indicator-details"><summary>전체 지표 값과 계산 상태</summary><div className="table-wrap"><table><thead><tr><th scope="col">지표</th><th scope="col">최근 값</th><th scope="col">계산 상태</th></tr></thead><tbody>{rows.map(([label, value, status]) => <tr key={label}><th scope="row">{label}</th><td>{value}</td><td>{status}</td></tr>)}</tbody></table></div></details>;
}

function MarketSummary({ snapshot }: Readonly<{ snapshot: ChartExplorerSuccess }>) {
  const price = record(snapshot.snapshot.price);
  const indicators = record(snapshot.snapshot.indicators);
  const moving = record(indicators.movingAverages);
  const volume = record(indicators.volume);
  const close = selectedNumber(price, "close");
  const sma20 = selectedNumber(moving, "sma20");
  const sma60 = selectedNumber(moving, "sma60");
  const rsi = selectedNumber(record(indicators.rsi14), "value");
  const volumeRatio = selectedNumber(volume, "ratio20");
  const readout = buildChartReadout(close, sma20, sma60, volumeRatio);
  return <section className="chart-observation" aria-labelledby="chart-observation-title">
    <div className="chart-observation-heading"><div><p className="eyebrow">CHART READOUT · 관찰 참고</p><h2 id="chart-observation-title">{readout.headline}</h2></div><span>{timeframeLabel(snapshot.timeframe)} · {chartTimeLabel(snapshot.snapshot.barAsOf, snapshot.timeframe)} · {getStatusLabel(snapshot.bar_status)}</span></div>
    <p className="chart-observation-summary">{readout.summary}</p>
    <details className="chart-observation-next"><summary>다음에 확인할 것</summary><p>{readout.nextCheck}</p></details>
    <ul className="chart-readout-facts">
      <li><span>RSI 14</span><strong>{rsi === null ? "자료 없음" : `${numberLabel(rsi)} / 100`}</strong><small>수치 참고 · 단독 판단 기준 아님</small></li>
      <li><span>거래량 / 20봉 평균</span><strong>{volumeRatio === null ? "자료 없음" : `${numberLabel(volumeRatio)}배`}</strong><small>최근 봉 포함 여부는 지표 기준 참조</small></li>
      <li><span>봉 상태</span><strong>{getStatusLabel(snapshot.bar_status)}</strong><small>{snapshot.adjusted ? "수정주가" : "미조정 가격"}</small></li>
    </ul>
    <p className="chart-readout-notice">자동 매매 신호나 매수·매도 권고가 아닙니다. 원천 자료의 기준 시각과 잠정 여부를 함께 확인하세요.</p>
  </section>;
}

function StructureOverlay({ structures, bars, x, y, priceTop, plotRight, minimum, maximum }: Readonly<{
  structures: unknown[]; bars: ChartBar[]; x: (index: number) => number; y: (value: number) => number; priceTop: number; plotRight: number; minimum: number; maximum: number;
}>) {
  const indexByTime = new Map(bars.map((bar, index) => [bar.time, index]));
  return <>{structures.map((raw, index) => {
    const structure = record(raw);
    if (!hasVisibleChartBar(bars, structure.barTime)) return null;
    const measurements = Array.isArray(structure.measurements) ? structure.measurements.map(record) : [];
    const value = (name: string) => measurements.find((measurement) => measurement.name === name)?.value;
    if (structure.family === "horizontal") {
      const boundary = Number(value("boundary"));
      if (!Number.isFinite(boundary) || boundary < minimum || boundary > maximum) return null;
      return <g key={`structure-${index}`}><line x1="62" y1={y(boundary)} x2={plotRight} y2={y(boundary)} stroke="#76614f" strokeDasharray="6 5" strokeWidth="1.5" /><text x="68" y={Math.max(priceTop + 14, y(boundary) - 4)} fill="#56452f">{value("type") === "prior-20-high" ? "직전 20봉 고가 참고" : value("type") === "prior-10-low" ? "직전 10봉 저가 참고" : "수평 가격 기준"}</text></g>;
    }
    const points = structure.family === "flag"
      ? [1, 2, 3, 4].map((point) => [indexByTime.get(String(value(`geometry.points.${point}.time`) ?? "")), Number(value(`geometry.points.${point}.price`))] as const)
      : structure.family === "triangle"
        ? [[indexByTime.get(String(value("geometry.points.1.time") ?? "")), Number(value("geometry.points.1.price"))], [indexByTime.get(String(structure.barTime ?? "")), Number(value("upperPrice"))], [indexByTime.get(String(structure.barTime ?? "")), Number(value("lowerPrice"))], [indexByTime.get(String(value("geometry.points.3.time") ?? "")), Number(value("geometry.points.3.price"))]] as const
        : [];
    if (points.length !== 4 || points.some(([barIndex, price]) => barIndex === undefined || !Number.isFinite(price))) return null;
    return <g key={`structure-${index}`}><polygon points={points.map(([barIndex, price]) => `${x(barIndex!)},${y(price)}`).join(" ")} fill="#163300" fillOpacity=".08" stroke="#163300" strokeOpacity=".72" strokeWidth="1.7" /><text x={x(points[0][0]!)} y={Math.max(priceTop + 14, y(points[0][1]) - 7)} fill="#163300">{structure.family === "flag" ? "깃대 측정 구간" : "삼각 구간 관찰"}</text></g>;
  })}</>;
}

function chartIndexAtPointer(event: React.PointerEvent<SVGSVGElement>, count: number, left = 62, right = 12): number {
  const rect = event.currentTarget.getBoundingClientRect();
  const viewX = (event.clientX - rect.left) / rect.width * 1200;
  const slot = (1200 - left - right) / count;
  return Math.max(0, Math.min(count - 1, Math.floor((viewX - left) / slot)));
}

function chartZoomAnchor(event: WheelEvent, svg: SVGSVGElement, left = 62, right = 12): number {
  const rect = svg.getBoundingClientRect();
  const viewX = (event.clientX - rect.left) / rect.width * 1200;
  return Math.max(0, Math.min(1, (viewX - left) / (1200 - left - right)));
}

type ChartInteractionProps = Readonly<{
  selectedBarIndex: number | null;
  range: ChartRange;
  onSelectBar: (index: number) => void;
  onClearBar: () => void;
  onPan: (base: ChartRange, deltaBars: number) => void;
  onZoom: (direction: "in" | "out", anchorRatio: number) => void;
}>;

function useChartWheelRef(onZoom: ChartInteractionProps["onZoom"], left = 62, right = 12) {
  const onZoomRef = useRef(onZoom);
  const cleanupRef = useRef<(() => void) | null>(null);
  onZoomRef.current = onZoom;
  return useCallback((svg: SVGSVGElement | null) => {
    cleanupRef.current?.();
    cleanupRef.current = svg ? addNonPassiveChartWheelListener(svg, (event) => {
      onZoomRef.current(event.deltaY < 0 ? "in" : "out", chartZoomAnchor(event, svg, left, right));
    }) : null;
  }, [left, right]);
}

function PriceChart({ bars, snapshot, indicators, patterns, signals, signalStrategies, overlays, dataOffset, showStructures, selectedBarIndex, range, onSelectBar, onClearBar, onPan, onZoom }: Readonly<ChartInteractionProps & { bars: ChartBar[]; snapshot: ChartExplorerSuccess; indicators: ReadonlyArray<ChartLabIndicatorPoint>; patterns: ReadonlyArray<ChartLabPattern>; signals: ChartLabEntryResult["signalHistory"] | null; signalStrategies: ReadonlyArray<ChartLabStrategy>; overlays: ReadonlyArray<ChartOverlayKey>; dataOffset: number; showStructures: boolean }>) {
  const width = 1200, height = 420, left = 62, right = 150, top = 22, priceBottom = 312, volumeTop = 344, bottom = 396;
  const drag = useRef<{ pointerId: number; startX: number; base: ChartRange; moved: boolean } | null>(null);
  const wheelRef = useChartWheelRef(onZoom, left, right);
  if (!bars.length) return <p className="message">표시할 봉 자료가 없습니다.</p>;
  const overlayLines: ChartOverlayLine[] = [];
  const familyColors = {
    sma: ["#447fba", "#d47733", "#7d659e", "#2d786b"],
    ema: ["#2b9b9f", "#d2a22f", "#a34c68", "#738340"],
    wma: ["#526d9a", "#c56b52", "#867143", "#53796c"],
  } as const;
  const periods = [20, 60, 120, 200] as const;
  for (const family of ["sma", "ema", "wma"] as const) {
    if (!overlays.includes(family)) continue;
    periods.forEach((period, index) => {
      const key = `${family}${period}` as keyof ChartLabIndicatorPoint;
      overlayLines.push({ key, label: `${family.toUpperCase()} ${period}`, color: familyColors[family][index], values: indicators.map((point) => point[key] as number | null) });
    });
  }
  if (overlays.includes("bollinger")) {
    for (const field of ["upper", "middle", "lower"] as const) overlayLines.push({
      key: `bollinger-${field}`, label: `BB ${field}`, color: field === "middle" ? "#b19463" : "#c7b792", dash: field === "middle" ? undefined : "4 4",
      values: indicators.map((point) => point.bollinger20?.[field] ?? null),
    });
  }
  if (overlays.includes("donchian")) {
    for (const field of ["upper", "middle", "lower"] as const) overlayLines.push({
      key: `donchian-${field}`, label: `DC ${field}`, color: field === "middle" ? "#28776d" : "#75a49a", dash: field === "middle" ? undefined : "2 4",
      values: indicators.map((point) => point.donchian20?.[field] ?? null),
    });
  }
  const priceValues = bars.flatMap((bar, localIndex) => [bar.high, bar.low, ...overlayLines.map((line) => line.values[dataOffset + range.start + localIndex])].filter(finite));
  const minimumRaw = Math.min(...priceValues), maximumRaw = Math.max(...priceValues);
  const pad = Math.max((maximumRaw - minimumRaw) * .05, Math.abs(maximumRaw) * .002, .01);
  const minimum = minimumRaw - pad, maximum = maximumRaw + pad;
  const y = (value: number) => top + ((maximum - value) / (maximum - minimum || 1)) * (priceBottom - top);
  const slot = (width - left - right) / bars.length, x = (index: number) => left + (index + .5) * slot;
  const candleWidth = Math.max(1, Math.min(9, slot * .68));
  const maxVolume = Math.max(1, ...bars.map((bar) => bar.volume));
  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = maximum - (maximum - minimum) * index / 4;
    return <g key={`grid-${index}`}><line x1={left} y1={y(value)} x2={width - right} y2={y(value)} stroke="#d3d0c4" /><text x="3" y={y(value) + 4}>{numberLabel(value, 2)}</text></g>;
  });
  const lines = overlayLines.flatMap((line) => {
    const segments: string[][] = [];
    let current: string[] = [];
    bars.forEach((_, localIndex) => {
      const value = line.values[dataOffset + range.start + localIndex];
      if (finite(value)) current.push(`${x(localIndex)},${y(value)}`);
      else if (current.length) { segments.push(current); current = []; }
    });
    if (current.length) segments.push(current);
    return segments.filter((segment) => segment.length > 1).map((segment, index) => <polyline key={`${line.key}-${index}`} points={segment.join(" ")} fill="none" stroke={line.color} strokeWidth={line.key.startsWith("sma") ? 2 : 1.5} strokeDasharray={line.dash} />);
  });
  const latest = bars.at(-1)!;
  const selectedIndex = selectedBarIndex !== null && selectedBarIndex < bars.length ? selectedBarIndex : null;
  const detail = bars[selectedIndex ?? bars.length - 1];
  const detailGlobalIndex = dataOffset + range.start + (selectedIndex ?? bars.length - 1);
  const detailIndicator = indicators[detailGlobalIndex];
  const detailRows: [string, unknown][] = [
    ["시가", detail.open], ["고가", detail.high], ["저가", detail.low], ["종가", detail.close], ["거래량", detail.volume],
    ["SMA 20", detail.sma20], ["SMA 60", detail.sma60], ["SMA 120", detail.sma120], ["SMA 200", detail.sma200],
    ["EMA 20 / 60", `${numberLabel(detailIndicator?.ema20)} / ${numberLabel(detailIndicator?.ema60)}`],
    ["WMA 20 / 60", `${numberLabel(detailIndicator?.wma20)} / ${numberLabel(detailIndicator?.wma60)}`],
    ["Bollinger 20", detailIndicator?.bollinger20 ? `${numberLabel(detailIndicator.bollinger20.lower)} / ${numberLabel(detailIndicator.bollinger20.middle)} / ${numberLabel(detailIndicator.bollinger20.upper)}` : "자료 없음"],
    ["Donchian 20", detailIndicator?.donchian20 ? `${numberLabel(detailIndicator.donchian20.lower)} / ${numberLabel(detailIndicator.donchian20.middle)} / ${numberLabel(detailIndicator.donchian20.upper)}` : "자료 없음"],
    ["RSI 14", detail.rsi14], ["MACD", detail.macd], ["Signal", detail.macdSignal], ["MACD hist.", detail.macdHistogram], ["ATR 14", detail.atr14], ["OBV", detail.obv],
  ];
  const movingAverageFamily = (["sma", "ema", "wma"] as const).find((family) => overlayLines.some((line) => line.key.startsWith(family)));
  const edgeValues = [
    { key: "close", label: `종가 ${numberLabel(latest.close, 2)}`, value: latest.close, color: "#d03238" },
    ...overlayLines.filter((line) => movingAverageFamily ? line.key.startsWith(movingAverageFamily) : false).flatMap((line) => {
      const value = line.values[dataOffset + range.start + bars.length - 1];
      return finite(value) ? [{ key: line.key, label: `${line.label} ${numberLabel(value, 2)}`, value, color: line.color }] : [];
    }),
  ].map((item) => ({ ...item, targetY: y(item.value) })).sort((a, b) => a.targetY - b.targetY);
  let previousLabelY = top - 20;
  const stackedEdgeValues = edgeValues.map((item) => {
    const labelY = Math.max(item.targetY, previousLabelY + 20);
    previousLabelY = labelY;
    return { ...item, labelY };
  });
  const labelOverflow = Math.max(0, (stackedEdgeValues.at(-1)?.labelY ?? priceBottom) - (priceBottom - 9));
  const priceEdgeLabels = stackedEdgeValues.map((item) => ({ ...item, labelY: item.labelY - labelOverflow }));
  function moveToPointer(event: React.PointerEvent<SVGSVGElement>) {
    if (drag.current?.pointerId === event.pointerId) {
      const deltaX = event.clientX - drag.current.startX;
      const rect = event.currentTarget.getBoundingClientRect();
      if (Math.abs(deltaX) > 4) drag.current.moved = true;
      if (drag.current.moved) {
        const pixelsPerBar = rect.width * ((width - left - right) / width) / bars.length;
        onPan(drag.current.base, Math.round(-deltaX / pixelsPerBar));
        return;
      }
    }
    onSelectBar(chartIndexAtPointer(event, bars.length, left, right));
  }
  function moveByKey(event: React.KeyboardEvent<SVGSVGElement>) {
    if (event.key === "Escape") { event.preventDefault(); onClearBar(); return; }
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const current = selectedIndex ?? bars.length - 1;
    onSelectBar(Math.max(0, Math.min(bars.length - 1, current + (event.key === "ArrowLeft" ? -1 : 1))));
  }
  function startDrag(event: React.PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    drag.current = { pointerId: event.pointerId, startX: event.clientX, base: range, moved: false };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function finishDrag(event: React.PointerEvent<SVGSVGElement>) {
    const current = drag.current;
    if (current?.pointerId === event.pointerId && !current.moved) onSelectBar(chartIndexAtPointer(event, bars.length, left, right));
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    drag.current = null;
  }
  return <div className="chart-price-wrap"><svg ref={wheelRef} className="chart-price-svg" viewBox={`0 0 ${width} ${height}`} role="group" tabIndex={0} aria-describedby="chart-gesture-help" aria-label={`${snapshot.display_name} ${timeframeLabel(snapshot.timeframe)} 캔들 및 거래량 차트. 봉에 포인터를 두거나 좌우 방향키로 탐색합니다.`} onPointerDown={startDrag} onPointerMove={moveToPointer} onPointerUp={finishDrag} onPointerCancel={() => { drag.current = null; }} onKeyDown={moveByKey}>
    {grid}
    {showStructures ? <StructureOverlay structures={snapshot.snapshot.structures} bars={bars} x={x} y={y} priceTop={top} plotRight={width - right} minimum={minimum} maximum={maximum} /> : null}
    {bars.map((bar, index) => {
      const color = bar.close > bar.open ? "#d03238" : bar.close < bar.open ? "#3976b9" : "#74766f";
      const volumeHeight = bar.volume / maxVolume * (bottom - volumeTop);
      return <g key={bar.time}><line x1={x(index)} y1={y(bar.high)} x2={x(index)} y2={y(bar.low)} stroke={color} strokeWidth="1.2" />
        <rect x={x(index) - candleWidth / 2} y={Math.min(y(bar.open), y(bar.close))} width={candleWidth} height={Math.max(1, Math.abs(y(bar.open) - y(bar.close)))} fill={color} />
        <rect x={x(index) - candleWidth / 2} y={bottom - volumeHeight} width={candleWidth} height={volumeHeight} fill={color} fillOpacity=".3" /></g>;
    })}
    {overlays.includes("patterns") ? <ChartLabPatternOverlay patterns={patterns} bars={bars} range={{ start: dataOffset + range.start, end: dataOffset + range.end }} x={x} y={y} /> : null}
    {overlays.includes("signals") && signals ? <ChartLabSignalOverlay signals={signals} selected={signalStrategies} bars={bars} range={{ start: dataOffset + range.start, end: dataOffset + range.end }} x={x} y={y} /> : null}
    {lines}<line className="chart-latest-close-line" x1={left} y1={y(latest.close)} x2={width - right} y2={y(latest.close)} stroke="#76614f" strokeDasharray="3 4" />
    {selectedIndex !== null ? <g className="chart-crosshair" aria-hidden="true" pointerEvents="none"><line className="chart-crosshair-vertical" x1={x(selectedIndex)} y1={top} x2={x(selectedIndex)} y2={bottom} /><line className="chart-crosshair-horizontal" x1={left} y1={y(bars[selectedIndex].close)} x2={width - right} y2={y(bars[selectedIndex].close)} /><circle className="chart-crosshair-point" cx={x(selectedIndex)} cy={y(bars[selectedIndex].close)} r="4" /></g> : null}
    {priceEdgeLabels.map((item) => <g key={item.key} className="chart-price-edge-label" aria-hidden="true" pointerEvents="none"><line x1={width - right} y1={item.targetY} x2={width - right + 5} y2={item.labelY} stroke={item.color} strokeWidth="1.2" /><rect x={width - right + 6} y={item.labelY - 9} width={right - 12} height="18" rx="2" fill={item.color} /><text x={width - right + 11} y={item.labelY + 3}>{item.label}</text></g>)}
    <line x1={left} y1={bottom} x2={width - right} y2={bottom} stroke="#9a9587" />
    <text x={left} y={height - 7}>{chartTimeLabel(bars[0].time, snapshot.timeframe)}</text><text x={width - right - 110} y={height - 7}>{chartTimeLabel(latest.time, snapshot.timeframe)}</text>
    <text x="5" y={volumeTop + 12}>거래량</text>
  </svg><div className="chart-bar-details" role="group" aria-label={`${selectedIndex === null ? "범위 끝 봉" : "선택한 봉"} 상세`}><div className="chart-bar-details-heading"><strong>{chartTimeLabel(detail.time, snapshot.timeframe)}</strong><span>{selectedIndex === null ? "표시 범위 끝 봉" : "선택한 봉"} · {snapshot.adjusted ? "수정주가" : "미조정 가격"} · 확정 상태 미확인</span></div><dl>{detailRows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{typeof value === "string" ? value : numberLabel(value, 4)}</dd></div>)}</dl></div><div className="chart-legend">
    <span><i className="chart-legend-candle" />{snapshot.adjusted ? "수정주가 캔들" : "미조정 가격 캔들"}</span>
    {overlayLines.map((line) => <span key={line.key}><i style={{ background: line.color }} />{line.label}</span>)}
    <span><i className="chart-legend-latest-close" />범위 끝 봉 종가</span>
    {selectedIndex !== null ? <span><i className="chart-legend-crosshair" />선택 봉 시각·종가</span> : null}
    {overlays.includes("patterns") ? <div className="chart-overlay-key" aria-label="패턴 선 색상 설명"><span><i className="chart-legend-triangle" />파랑 · 삼각 경계</span><span><i className="chart-legend-flag" />주황 · 깃대 구간</span><span><i className="chart-legend-boundary" />청록 · 수평 경계</span></div> : null}
    {overlays.includes("signals") ? <div className="chart-overlay-key" aria-label="전략 원신호 설명">{signalStrategies.map((strategy) => { const item = CHART_LAB_STRATEGIES.find((candidate) => candidate.id === strategy); return <span key={strategy}><b className="chart-signal-key-label">{strategy}</b>{item ? <>{item.name} · {item.rule}</> : "전략 규칙 자료 없음"}</span>; })}<span><i className="chart-legend-entry-signal" />▲ 진입 원신호</span><span><i className="chart-legend-exit-signal" />▼ 이탈 원신호</span><span>표시 봉 확정 여부는 확인되지 않았습니다.</span></div> : null}
    <span><i className="chart-legend-volume" />거래량</span>
    {showStructures && snapshot.snapshot.structures.length ? <span><i className="chart-legend-structure" />저장 구조 · 수평 기준선 / 깃대·삼각 영역</span> : null}
  </div></div>;
}

function SecondaryChart({ bars, series, timeframe, selectedBarIndex, range, onSelectBar, onClearBar, onPan, onZoom }: Readonly<ChartInteractionProps & { bars: ChartBar[]; series: SeriesKey; timeframe: ChartExplorerTimeframe }>) {
  const drag = useRef<{ pointerId: number; startX: number; base: ChartRange; moved: boolean } | null>(null);
  const wheelRef = useChartWheelRef(onZoom);
  if (series === "hidden") return null;
  const width = 1200, height = 180, left = 62, right = 12, top = 16, bottom = 144;
  const key = series === "macd" ? "macd" : series;
  const values = bars.map((bar) => bar[key]).filter(finite);
  if (!values.length) return <p className="data-note">선택 지표를 계산할 봉이 부족합니다.</p>;
  let min = series === "rsi14" ? 0 : Math.min(...values), max = series === "rsi14" ? 100 : Math.max(...values);
  if (series === "macd") { const extent = Math.max(Math.abs(min), Math.abs(max), .001); min = -extent; max = extent; }
  if (min === max) { min -= 1; max += 1; }
  const slot = (width - left - right) / bars.length, x = (index: number) => left + (index + .5) * slot;
  const y = (value: number) => top + ((max - value) / (max - min)) * (bottom - top);
  const zeroY = y(series === "macd" ? 0 : min);
  const linePoints = bars.map((bar, index) => finite(bar[key]) ? `${x(index)},${y(bar[key]!)}` : null).filter((point): point is string => point !== null);
  const title = SERIES.find(([id]) => id === series)?.[1] ?? "보조 지표";
  const selectedIndex = selectedBarIndex !== null && selectedBarIndex < bars.length ? selectedBarIndex : null;
  function moveToPointer(event: React.PointerEvent<SVGSVGElement>) {
    if (drag.current?.pointerId === event.pointerId) {
      const deltaX = event.clientX - drag.current.startX;
      const rect = event.currentTarget.getBoundingClientRect();
      if (Math.abs(deltaX) > 4) drag.current.moved = true;
      if (drag.current.moved) {
        const pixelsPerBar = rect.width * ((width - left - right) / width) / bars.length;
        onPan(drag.current.base, Math.round(-deltaX / pixelsPerBar));
        return;
      }
    }
    onSelectBar(chartIndexAtPointer(event, bars.length, left, right));
  }
  function moveByKey(event: React.KeyboardEvent<SVGSVGElement>) {
    if (event.key === "Escape") { event.preventDefault(); onClearBar(); return; }
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const current = selectedIndex ?? bars.length - 1;
    onSelectBar(Math.max(0, Math.min(bars.length - 1, current + (event.key === "ArrowLeft" ? -1 : 1))));
  }
  function startDrag(event: React.PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    drag.current = { pointerId: event.pointerId, startX: event.clientX, base: range, moved: false };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function finishDrag(event: React.PointerEvent<SVGSVGElement>) {
    const current = drag.current;
    if (current?.pointerId === event.pointerId && !current.moved) onSelectBar(chartIndexAtPointer(event, bars.length, left, right));
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    drag.current = null;
  }
  const selectedValue = selectedIndex === null ? null : bars[selectedIndex][key];
  const selectedY = finite(selectedValue) ? y(selectedValue) : null;
  const readoutWidth = 184, readoutHeight = 34;
  const readoutX = selectedIndex === null ? left : Math.max(left + 4, Math.min(width - right - readoutWidth - 4, x(selectedIndex) + 12));
  const readoutY = selectedY === null ? top : Math.max(top + 2, Math.min(bottom - readoutHeight - 2, selectedY > top + readoutHeight + 8 ? selectedY - readoutHeight - 8 : selectedY + 8));
  return <div className="chart-secondary-wrap"><h3>{title}</h3><svg ref={wheelRef} className="chart-secondary-svg" viewBox={`0 0 ${width} ${height}`} role="group" tabIndex={0} aria-describedby="chart-gesture-help" aria-label={`${title} 보조 지표. 좌우 방향키로 봉을 탐색합니다.`} onPointerDown={startDrag} onPointerMove={moveToPointer} onPointerUp={finishDrag} onPointerCancel={() => { drag.current = null; }} onKeyDown={moveByKey}>
    {[0, .5, 1].map((fraction) => <line key={fraction} x1={left} x2={width - right} y1={top + fraction * (bottom - top)} y2={top + fraction * (bottom - top)} stroke="#d3d0c4" strokeDasharray={fraction ? "" : "4 4"} />)}
    {series === "macd" ? bars.map((bar, index) => finite(bar.macdHistogram) ? <rect key={bar.time} x={x(index) - Math.max(1, slot * .55) / 2} y={Math.min(y(bar.macdHistogram), zeroY)} width={Math.max(1, slot * .55)} height={Math.max(1, Math.abs(zeroY - y(bar.macdHistogram)))} fill={bar.macdHistogram >= 0 ? "#d03238" : "#3976b9"} fillOpacity=".6" /> : null) : null}
    <polyline points={linePoints.join(" ")} fill="none" stroke="#2d786b" strokeWidth="2.2" />
    {series === "macd" ? <polyline points={bars.map((bar, index) => finite(bar.macdSignal) ? `${x(index)},${y(bar.macdSignal)}` : null).filter((point): point is string => point !== null).join(" ")} fill="none" stroke="#d47733" strokeWidth="1.8" /> : null}
    {series === "rsi14" ? [30, 70].map((value) => <g key={value}><line x1={left} x2={width - right} y1={y(value)} y2={y(value)} stroke="#76614f" strokeDasharray="5 4" /><text x="5" y={y(value) + 4}>{value}</text></g>) : null}
    {selectedIndex !== null && selectedY !== null ? <g className="chart-crosshair" aria-hidden="true" pointerEvents="none"><line className="chart-crosshair-vertical" x1={x(selectedIndex)} y1={top} x2={x(selectedIndex)} y2={bottom} /><line className="chart-crosshair-horizontal" x1={left} y1={selectedY} x2={width - right} y2={selectedY} /><circle className="chart-crosshair-point" cx={x(selectedIndex)} cy={selectedY} r="4" /></g> : null}
    {selectedIndex !== null && finite(selectedValue) ? <g className="chart-secondary-hover-readout" aria-hidden="true" pointerEvents="none"><rect x={readoutX} y={readoutY} width={readoutWidth} height={readoutHeight} rx="3" /><text className="chart-secondary-hover-value" x={readoutX + 8} y={readoutY + 14}>{title} · {numberLabel(selectedValue, 2)}</text><text className="chart-secondary-hover-time" x={readoutX + 8} y={readoutY + 27}>{chartTimeLabel(bars[selectedIndex].time, timeframe)}</text></g> : null}
    <text x={left} y={height - 5}>{bars[0] ? chartTimeLabel(bars[0].time, timeframe) : ""}</text><text x={width - right - 110} y={height - 5}>{bars.at(-1) ? chartTimeLabel(bars.at(-1)!.time, timeframe) : ""}</text>
  </svg></div>;
}

function VolumeProfile({ snapshot }: Readonly<{ snapshot: ChartExplorerSuccess }>) {
  const profile = snapshot.snapshot.indicators.volumeProfile12;
  const peak = Math.max(1, ...profile.bins.map((bin) => bin.volume));
  return <section className="chart-subpanel" aria-labelledby="chart-volume-profile-title"><div className="chart-subpanel-heading"><h3 id="chart-volume-profile-title">가격 구간 거래량</h3><span>{profile.count}봉 · HLC3</span></div>
    <p className="data-note">실제 호가·체결 분포가 아니라 봉 가격(HLC3)으로 산출한 참고 추정입니다. · {getStatusLabel(profile.status)}</p>
    {profile.bins.length ? <div className="chart-profile-list">{[...profile.bins].reverse().map((bin) => <div className="chart-profile-row" key={`${bin.low}-${bin.high}`}><span>{numberLabel(bin.low, 2)}–{numberLabel(bin.high, 2)}</span><div><i style={{ width: `${bin.volume / peak * 100}%` }} /></div><strong>{new Intl.NumberFormat("ko-KR", { notation: "compact", maximumFractionDigits: 1 }).format(bin.volume)}</strong></div>)}</div> : <p className="data-note">가격 구간 계산 자료가 없습니다.</p>}
  </section>;
}

type ChartWatchlistItem = WatchGroup["items"][number];
type ChartWatchlistProps = Readonly<{
  groups: WatchGroup[];
  selectedGroup: string;
  groupName: string;
  groupsLoaded: boolean;
  watchStorageError: boolean;
  canAddCurrent: boolean;
  onSelectGroup: (name: string) => void;
  onGroupNameChange: (name: string) => void;
  onAddCurrent: () => void;
  onAddGroup: (event: React.FormEvent<HTMLFormElement>) => void;
  onDeleteGroup: () => void;
  onOpenItem: (item: ChartWatchlistItem) => void;
  onRemoveItem: (symbol: string) => void;
}>;

function ChartWatchlistPanel({ groups, selectedGroup, groupName, groupsLoaded, watchStorageError, canAddCurrent, onSelectGroup, onGroupNameChange, onAddCurrent, onAddGroup, onDeleteGroup, onOpenItem, onRemoveItem }: ChartWatchlistProps) {
  const selectedItems = groups.find((group) => group.name === selectedGroup)?.items ?? [];
  return <section className="chart-subpanel chart-watchlist" aria-label="차트 관심 종목"><div className="chart-watchlist-heading"><div className="chart-subpanel-heading"><h3>관심 종목</h3><span>{selectedItems.length}개 · 이 브라우저에 저장</span></div><div className="chart-watchlist-tools">
    <label htmlFor="chart-watch-group">그룹</label><select id="chart-watch-group" value={selectedGroup} onChange={(event) => onSelectGroup(event.target.value)} disabled={!groupsLoaded}>{groups.map((group) => <option key={group.name}>{group.name}</option>)}</select>
    <button className="action-secondary" type="button" onClick={onAddCurrent} disabled={!canAddCurrent}>현재 종목 추가</button>
    <details className="chart-group-manager"><summary>그룹 관리</summary><form className="chart-group-add" onSubmit={onAddGroup}><label className="sr-only" htmlFor="chart-new-group">새 그룹 이름</label><input id="chart-new-group" value={groupName} onChange={(event) => onGroupNameChange(event.target.value)} maxLength={32} placeholder="새 그룹 이름" disabled={!groupsLoaded} /><button type="submit" className="action-secondary" disabled={!groupsLoaded}>그룹 추가</button></form>{groups.length > 1 && selectedGroup !== "기본" ? <button className="chart-remove-group" type="button" onClick={onDeleteGroup}>현재 그룹 삭제</button> : null}</details>
  </div></div>
    {watchStorageError ? <p className="data-note" role="status">브라우저 저장소를 사용할 수 없어 관심 목록이 유지되지 않을 수 있습니다.</p> : null}
    {selectedItems.length ? <ul className="chart-watch-items">{selectedItems.map((item) => <li key={item.symbol}><button type="button" onClick={() => onOpenItem(item)}><strong>{item.name}</strong><span>{item.symbol}</span></button><button type="button" aria-label={`${item.name} 관심 종목 제거`} onClick={() => onRemoveItem(item.symbol)}>×</button></li>)}</ul> : <p className="chart-watchlist-empty">관심 목록이 비어 있습니다. 검색한 종목을 현재 그룹에 추가하세요.</p>}
  </section>;
}

export default function ChartExplorerClient({ businessDate, initialSymbol, initialTimeframe = "1d" }: Readonly<{ businessDate: string; initialSymbol: string; initialTimeframe?: ChartExplorerTimeframe }>) {
  const { activeTab } = useDailyTabs();
  const [symbol, setSymbol] = useState(initialSymbol);
  const [symbolName, setSymbolName] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState<ChartExplorerTimeframe>(initialTimeframe);
  const [data, setData] = useState<ChartExplorerResponse | null>(null);
  const [calculationBars, setCalculationBars] = useState<ChartExplorerBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(initialSymbol);
  const [matches, setMatches] = useState<StockSearchItem[]>([]);
  const [searchMessage, setSearchMessage] = useState("");
  const [series, setSeries] = useState<SeriesKey>("rsi14");
  const [visibleBarsCount, setVisibleBarsCount] = useState(200);
  const [requestedChartRange, setRequestedChartRange] = useState<ChartRange | null>(null);
  const [selectedBarIndex, setSelectedBarIndex] = useState<number | null>(null);
  const [visibleOverlays, setVisibleOverlays] = useState<ChartOverlayKey[]>(["sma", "patterns", "signals"]);
  const [selectedStrategies, setSelectedStrategies] = useState<ChartLabStrategy[]>(["F"]);
  const [strategyMode, setStrategyMode] = useState<"all" | "any">("all");
  const [maxAtr, setMaxAtr] = useState(0.5);
  const [showStructures, setShowStructures] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [groups, setGroups] = useState<WatchGroup[]>([{ name: "기본", items: [] }]);
  const [groupsLoaded, setGroupsLoaded] = useState(false);
  const [groupsChanged, setGroupsChanged] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("기본");
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [analysisIndex, setAnalysisIndex] = useState(0);
  const requestSequence = useRef(0);
  const activeRequest = useRef(false);
  const [watchStorageError, setWatchStorageError] = useState(false);

  const fetchChart = useCallback(async (requestedSymbol = symbol, requestedTimeframe = timeframe, requestedName?: string) => {
    const normalized = requestedSymbol.trim();
    if (!isChartExplorerSymbol(normalized)) { setError("종목 코드 또는 Yahoo 티커 형식을 확인하세요."); return; }
    if (activeRequest.current) return;
    activeRequest.current = true;
    const sequence = ++requestSequence.current;
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({ date: businessDate, symbol: normalized, timeframe: requestedTimeframe, selected: "F", mode: "all", maxAtr: "0.5" });
      const response = await fetch(`/api/chart-lab/analysis?${params}`, { method: "GET", cache: "no-store" });
      let payload: unknown = null;
      try { payload = await response.json(); } catch { /* A route error can be plain text. */ }
      if (!response.ok) {
        throw new Error(response.status === 400 ? "요청한 종목·주기·기준일 조합을 확인하세요." : "차트 자료를 가져오지 못했습니다. 잠시 후 다시 조회하세요.");
      }
      const chart = record(payload).chart;
      if (!isChartExplorerResponse(chart)) throw new Error("차트 응답 형식을 확인할 수 없습니다.");
      const rows = record(payload).calculationBars;
      if (chart.available && (!Array.isArray(rows) || rows.length > 800 || !rows.every(isCalculationBar) || rows.some((bar, index) => index > 0 && rows[index - 1].time >= bar.time))) {
        throw new Error("계산 봉 자료의 순서나 형식을 확인할 수 없습니다.");
      }
      if (sequence !== requestSequence.current) return;
      setData(chart); setCalculationBars(chart.available ? rows as ChartExplorerBar[] : []); setSymbol(normalized);
      setSymbolName(chart.available ? chart.display_name : (requestedName ?? chart.display_name) || normalized);
      setQuery(normalized);
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.set("symbol", normalized); url.searchParams.set("timeframe", requestedTimeframe);
        window.history.replaceState(null, "", url);
      }
    } catch (cause) { if (sequence === requestSequence.current) setError(cause instanceof Error ? cause.message : "차트 조회에 실패했습니다."); }
    finally { if (sequence === requestSequence.current) { activeRequest.current = false; setLoading(false); } }
  }, [businessDate, symbol, symbolName, timeframe]);

  useEffect(() => {
    if (activeTab !== "chart" || groupsLoaded) return;
    try { setGroups(loadWatchGroups(window.localStorage.getItem(WATCHLIST_KEY))); }
    catch { setWatchStorageError(true); }
    finally { setGroupsLoaded(true); }
  }, [activeTab, groupsLoaded]);
  useEffect(() => { if (groupsLoaded && groupsChanged) { try { window.localStorage.setItem(WATCHLIST_KEY, JSON.stringify(groups)); } catch { setWatchStorageError(true); } } }, [groups, groupsChanged, groupsLoaded]);
  useEffect(() => {
    if (activeTab === "chart" && !loadedOnce && isChartExplorerSymbol(initialSymbol)) { setLoadedOnce(true); void fetchChart(initialSymbol, timeframe); }
  }, [activeTab, fetchChart, initialSymbol, loadedOnce, timeframe]);
  useEffect(() => {
    if (!autoRefresh || activeTab !== "chart" || !data?.available) return;
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void fetchChart(symbol, timeframe); }, 60_000);
    return () => window.clearInterval(timer);
  }, [activeTab, autoRefresh, data?.available, fetchChart, symbol, timeframe]);

  const rawBars = useMemo<ChartExplorerBar[]>(() => data?.available ? calculationBars : [], [calculationBars, data]);
  const allBars = useMemo(() => data?.available ? data.chart.bars : [], [data]);
  const displayOffset = Math.max(0, rawBars.length - allBars.length);
  const datasetKey = data?.available ? `${data.symbol}:${data.timeframe}` : "";
  useEffect(() => { setRequestedChartRange(null); setSelectedBarIndex(null); }, [datasetKey]);
  const visibleRange = useMemo(() => resolveChartRange(allBars.length, visibleBarsCount, requestedChartRange), [allBars.length, requestedChartRange, visibleBarsCount]);
  const bars = useMemo(() => allBars.slice(visibleRange.start, visibleRange.end), [allBars, visibleRange]);
  const requestedAnalysisIndex = selectedBarIndex === null ? Math.max(0, rawBars.length - 1) : Math.min(rawBars.length - 1, displayOffset + visibleRange.start + selectedBarIndex);
  useEffect(() => { setAnalysisIndex(Math.max(0, rawBars.length - 1)); }, [datasetKey]);
  useEffect(() => {
    const timer = window.setTimeout(() => setAnalysisIndex(requestedAnalysisIndex), 140);
    return () => window.clearTimeout(timer);
  }, [datasetKey, requestedAnalysisIndex]);
  const chartIndicators = useMemo(() => calculateChartLabIndicators(rawBars), [rawBars]);
  const chartPatterns = useMemo(() => data?.available ? detectChartLabPatterns(rawBars.slice(0, analysisIndex + 1), data.timeframe) : [], [analysisIndex, data, rawBars]);
  const chartSignals = useMemo(() => data?.available && rawBars.length
    ? evaluateChartLabEntry(rawBars, { timeframe: data.timeframe, asOfIndex: analysisIndex, confirmedThroughIndex: null, judgmentReady: true, historical: analysisIndex < rawBars.length - 1, selected: selectedStrategies, mode: strategyMode, maxAtr }).signalHistory
    : null, [analysisIndex, data, maxAtr, rawBars, selectedStrategies, strategyMode]);
  const structureRows = data?.available && Array.isArray(data.snapshot.structures) ? data.snapshot.structures : [];
  const requestPending = !!data?.available && (symbol !== data.symbol || timeframe !== data.timeframe);

  function zoomChart(direction: "in" | "out", anchorRatio = 0.5) {
    const next = zoomChartRange(visibleRange, allBars.length, direction, anchorRatio);
    setRequestedChartRange(next);
    setVisibleBarsCount(next.end - next.start);
    setSelectedBarIndex(null);
  }

  function panChart(base: ChartRange, deltaBars: number) {
    const next = panChartRange(base, allBars.length, deltaBars);
    setRequestedChartRange(next);
    setVisibleBarsCount(next.end - next.start);
    setSelectedBarIndex(null);
  }

  function chooseVisibleBars(count: number) {
    setVisibleBarsCount(count);
    setRequestedChartRange(null);
    setSelectedBarIndex(null);
  }

  function toggleOverlay(key: ChartOverlayKey) {
    setVisibleOverlays((current) => current.includes(key) ? current.filter((value) => value !== key) : [...current, key]);
  }

  function focusChartIndex(index: number) {
    if (!Number.isInteger(index) || index < displayOffset || index >= displayOffset + allBars.length) {
      setSearchMessage("선택한 구조가 현재 표시 중인 최근 380봉 범위보다 오래되었습니다.");
      return;
    }
    const displayIndex = index - displayOffset;
    const count = Math.min(allBars.length, Math.max(50, visibleRange.end - visibleRange.start));
    const start = Math.max(0, Math.min(allBars.length - count, displayIndex - Math.floor(count / 2)));
    setRequestedChartRange({ start, end: start + count });
    setVisibleBarsCount(count);
    setSelectedBarIndex(displayIndex - start);
  }

  async function searchStocks(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setMatches([]); setSearchMessage("");
    const trimmed = query.trim();
    if (!trimmed) { setSearchMessage("종목명, 코드 또는 티커를 입력하세요."); return; }
    try {
      const params = new URLSearchParams({ date: businessDate, q: trimmed, limit: "20" });
      const response = await fetch(`/api/stocks/search?${params}`, { method: "GET", cache: "no-store" });
      const payload: unknown = await response.json();
      if (!response.ok || !isStockSearchSnapshot(payload, businessDate, trimmed)) throw new Error("저장 종목 검색을 완료하지 못했습니다.");
      setMatches(payload.items); setSearchMessage(payload.items.length ? `${payload.items.length}개 저장 종목` : payload.empty_state ?? "저장된 종목이 없습니다.");
      const exact = payload.items.find((item) => item.stock_code === trimmed);
      if (!exact && isChartExplorerSymbol(trimmed) && !/^\d{6}$/.test(trimmed)) { setSymbol(trimmed); setSymbolName(trimmed); setSearchMessage("저장 종목 없음 · Yahoo 티커로 조회합니다."); await fetchChart(trimmed, timeframe, trimmed); }
    } catch (cause) { setSearchMessage(cause instanceof Error ? cause.message : "종목 검색에 실패했습니다."); }
  }

  function addCurrentToGroup() {
    if (!groupsLoaded || !isChartExplorerSymbol(symbol) || !symbolName.trim()) return;
    setGroupsChanged(true);
    setGroups((current) => current.map((group) => group.name === selectedGroup && !group.items.some((item) => item.symbol === symbol)
      ? { ...group, items: [...group.items, { symbol, name: symbolName }].slice(0, 100) } : group));
  }

  function addGroup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const name = groupName.trim().slice(0, 32);
    if (!groupsLoaded || !name || groups.some((group) => group.name === name) || groups.length >= 12) return;
    setGroupsChanged(true);
    setGroups((current) => [...current, { name, items: [] }]); setSelectedGroup(name); setGroupName("");
  }

  function deleteSelectedGroup() {
    if (selectedGroup === "기본" || groups.length <= 1) return;
    setGroupsChanged(true);
    setGroups((current) => current.filter((group) => group.name !== selectedGroup));
    setSelectedGroup("기본");
  }

  function openWatchlistItem(item: ChartWatchlistItem) {
    setSymbol(item.symbol); setSymbolName(item.name); void fetchChart(item.symbol, timeframe, item.name);
  }

  function removeWatchlistItem(symbolToRemove: string) {
    setGroupsChanged(true);
    setGroups((current) => current.map((group) => group.name === selectedGroup
      ? { ...group, items: group.items.filter((item) => item.symbol !== symbolToRemove) } : group));
  }

  const watchlistPanel = <ChartWatchlistPanel
    groups={groups} selectedGroup={selectedGroup} groupName={groupName} groupsLoaded={groupsLoaded} watchStorageError={watchStorageError}
    canAddCurrent={groupsLoaded && isChartExplorerSymbol(symbol) && !!symbolName.trim()}
    onSelectGroup={setSelectedGroup} onGroupNameChange={setGroupName} onAddCurrent={addCurrentToGroup} onAddGroup={addGroup}
    onDeleteGroup={deleteSelectedGroup} onOpenItem={openWatchlistItem} onRemoveItem={removeWatchlistItem}
  />;

  return <div className="chart-explorer-workspace">
    <section className="chart-command-panel" aria-label="차트 조회 조건">
      <div className="chart-symbol-workspace">
        <form className="chart-symbol-search" onSubmit={searchStocks} role="search">
          <label htmlFor="chart-symbol-query">차트 종목 검색</label><input id="chart-symbol-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="종목명 · 코드 · Yahoo 티커" autoComplete="off" />
          <button className="action-secondary" type="submit">검색</button>
        </form>
        {watchlistPanel}
      </div>
      <div className="chart-command-right">
        <div className="chart-periods" role="group" aria-label="봉 주기">{PERIODS.map((period) => <button key={period.key} type="button" aria-pressed={timeframe === period.key} onClick={() => setTimeframe(period.key)}>{period.label}</button>)}</div>
        <button className="action-primary" type="button" disabled={loading || !isChartExplorerSymbol(symbol)} onClick={() => void fetchChart(symbol, timeframe)}>{loading ? "조회 중…" : "조회"}</button>
        <button className="action-secondary" type="button" disabled={loading || !data?.available} onClick={() => void fetchChart(symbol, timeframe)}>새로고침</button>
        <button className={`action-secondary${autoRefresh ? " is-active" : ""}`} type="button" aria-pressed={autoRefresh} disabled={!data?.available} onClick={() => setAutoRefresh((value) => !value)}>자동갱신 {autoRefresh ? "ON" : "OFF"}</button>
      </div>
      <p className="chart-command-note" aria-live="polite">{searchMessage || (requestPending ? "선택을 변경했습니다. 조회 버튼을 눌러 새 자료를 요청하세요. · " : "") + `기준일 ${businessDate} · 차트 조회는 사용자가 선택한 종목에만 요청합니다. 자동갱신은 60초 간격이며 화면이 숨겨지면 멈춥니다.`}</p>
      <details className="chart-help"><summary>도움말</summary><p>국내 6자리 코드는 선택일 저장 종목과 Toss 시장 분류가 확인될 때만 조회합니다. `005930.KS`처럼 거래소 접미사를 직접 입력하면 별도의 Yahoo 티커로 조회합니다. 주봉·월봉은 일봉 집계이며, 4시간봉은 제공처 1시간 봉을 각 시장의 현지 날짜 기준으로 묶습니다. Yahoo 자료는 미조정이고 모든 봉의 확정 상태는 미확인으로 표시합니다.</p><p>관심 목록은 이 브라우저에 저장됩니다. 화면 자동갱신은 선택 종목 하나를 60초 간격으로 다시 읽고, 서버 패턴 감시는 별도 상태이며 사용자가 시작해야 작동합니다.</p><p>A/B/C/F와 R/H는 상류 규칙에 따른 조건 검토입니다. 원신호·유지 조건·확정 상태를 나눠 보여주며 주문이나 수익성을 보증하지 않습니다.</p></details>
      {matches.length ? <ul className="chart-search-results" aria-label="저장 종목 검색 결과">{matches.map((item) => <li key={item.stock_code}><button type="button" onClick={() => { setSymbol(item.stock_code); setSymbolName(item.stock_name); setQuery(item.stock_code); setMatches([]); void fetchChart(item.stock_code, timeframe, item.stock_name); }}><strong>{item.stock_name}</strong><span>{item.stock_code} · {item.market ?? "시장 분류 없음"}</span></button></li>)}</ul> : null}
    </section>

    {error ? <p className="message" role="alert">{error}</p> : null}
    {data?.available ? <>
      <header className="chart-result-heading"><div><p className="eyebrow">CHART · SELECTED SYMBOL</p><h2>{displayName(data)} <span>{data.symbol}</span></h2></div><p>{timeframeLabel(data.timeframe)} · 기준 봉 {chartTimeLabel(data.snapshot.barAsOf, data.timeframe)} · 통화 {data.currency ?? "자료 없음"}</p></header>
      <MarketSummary snapshot={data} />
      <div className="chart-explorer-layout">
        <div className="chart-main-column">
          <section className="chart-surface" aria-label="가격 차트">
            <div className="chart-surface-heading"><div><p className="eyebrow">PRICE & VOLUME</p><h2>{timeframeLabel(data.timeframe)} 가격 흐름</h2></div><div className="chart-surface-tools"><div className="chart-viewport-controls" role="group" aria-label="차트 보기 조절"><button className="action-secondary" type="button" onClick={() => zoomChart("out")}>− 축소</button><button className="action-secondary" type="button" onClick={() => zoomChart("in")}>＋ 확대</button><button className="action-secondary" type="button" onClick={() => { setRequestedChartRange(null); setSelectedBarIndex(null); }}>최신 봉</button>{selectedBarIndex !== null ? <button className="action-secondary" type="button" onClick={() => setSelectedBarIndex(null)}>선택 해제</button> : null}</div><label className="chart-range-select">표시 봉<select value={visibleBarsCount} onChange={(event) => chooseVisibleBars(Number(event.target.value))}>{![50, 100, 200, 380].includes(visibleBarsCount) ? <option value={visibleBarsCount}>{visibleBarsCount}봉 · 확대</option> : null}<option value={50}>50봉</option><option value={100}>100봉</option><option value={200}>200봉</option><option value={380}>최대 380봉</option></select></label><div className="chart-overlay-controls">
              {([["sma", "SMA"], ["ema", "EMA"], ["wma", "WMA"], ["bollinger", "Bollinger"], ["donchian", "Donchian"], ["patterns", "패턴"], ["signals", "전략 원신호"]] as const).map(([key, label]) => <label key={key}><input type="checkbox" checked={visibleOverlays.includes(key)} onChange={() => toggleOverlay(key)} />{label}</label>)}
              <label><input type="checkbox" checked={showStructures} onChange={(event) => setShowStructures(event.target.checked)} />구조 측정</label>
            </div></div></div>
            <p id="chart-gesture-help" className="chart-gesture-help">마우스 휠은 차트 확대·축소에만 사용됩니다 (위: 확대 · 아래: 축소). 봉 위에 포인터를 두면 세로선이 해당 봉으로 이동하고, 가로선과 점은 그 봉의 종가를 가리킵니다. 오른쪽 색 태그는 범위 끝 종가와 대표 이동평균 값입니다. 아래 봉 상세에서 시가·고가·저가·종가와 지표를 확인하세요. 차트를 끌어 과거 봉 이동 · 좌우 방향키로 봉 이동 · Esc 또는 선택 해제로 해제</p>
            <p className="chart-data-basis">{data.adjusted ? "수정주가" : "미조정 가격"} · 통화 {data.currency ?? "자료 없음"} · {data.timeframe === "4h" ? "공급처 1시간 봉을 현지 날짜별 4개씩 묶음" : "일봉 원천 또는 집계 봉"} · {getStatusLabel(data.bar_status)} · {bars.length}봉 표시</p>
            <PriceChart bars={bars} snapshot={data} indicators={chartIndicators} patterns={chartPatterns} signals={chartSignals} signalStrategies={selectedStrategies} overlays={visibleOverlays} dataOffset={displayOffset} showStructures={showStructures} selectedBarIndex={selectedBarIndex} range={visibleRange} onSelectBar={setSelectedBarIndex} onClearBar={() => setSelectedBarIndex(null)} onPan={panChart} onZoom={zoomChart} />
            <ChartIndicatorDetails snapshot={data} />
          </section>
          <section className="chart-surface chart-secondary-surface"><div className="chart-surface-heading"><div><p className="eyebrow">INDICATOR</p><h2>보조 지표</h2></div><label className="chart-series-select">지표<select value={series} onChange={(event) => setSeries(event.target.value as SeriesKey)}>{SERIES.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div><SecondaryChart bars={bars} series={series} timeframe={data.timeframe} selectedBarIndex={selectedBarIndex} range={visibleRange} onSelectBar={setSelectedBarIndex} onClearBar={() => setSelectedBarIndex(null)} onPan={panChart} onZoom={zoomChart} /></section>
          <ChartLabAnalysisPanels bars={rawBars} timeframe={data.timeframe} asOfIndex={analysisIndex} currency={data.currency} patterns={chartPatterns} selectedStrategies={selectedStrategies} mode={strategyMode} maxAtr={maxAtr} onSelectedStrategiesChange={setSelectedStrategies} onModeChange={setStrategyMode} onMaxAtrChange={setMaxAtr} onFocusIndex={focusChartIndex} />
          <details className="chart-surface chart-disclosure chart-structure-disclosure" role="group" aria-label="가격 구조 관찰">
            <summary className="chart-surface-heading chart-disclosure-summary"><div><p className="eyebrow">STRUCTURE NOTES</p><h2>가격 구조 관찰</h2></div><span>{structureRows.length}개 · 서버 계산 참고</span></summary>
            <div className="chart-disclosure-content">
            {structureRows.length ? <ul className="chart-structure-list">{structureRows.map((raw, index) => { const item = record(raw); const measurements = Array.isArray(item.measurements) ? item.measurements.map(record) : []; return <li key={`${String(item.family)}-${index}`}><strong>{structureFamilyLabel(item.family)}</strong><span>{getStatusLabel(item.status)}</span><small>{timeframeLabel(item.timeframe ?? data.timeframe)} · 관측 봉 {chartTimeLabel(typeof item.barTime === "string" ? item.barTime : null, data.timeframe)}</small>{measurements.length ? <details className="chart-measurements"><summary>측정 근거 {measurements.length}개</summary><dl>{measurements.map((measurement, measurementIndex) => <div key={`${String(measurement.name)}-${measurementIndex}`}><dt>{String(measurement.label ?? measurement.name ?? "측정 항목")}</dt><dd>{structureMeasurementValue(measurement.value, measurement.unit, measurement.name, data.currency)}</dd></div>)}</dl></details> : null}</li>; })}</ul> : <p className="data-note">선택한 기준일·주기에서 표시할 구조 측정이 없습니다. 없음은 하락·상승 판단이 아니라 탐지 자료 상태입니다.</p>}
            </div>
          </details>
        </div>
        <aside className="chart-side-column" aria-label="차트 참고 자료">
          <ChartLabMonitorPanel watchItems={groups.find((group) => group.name === selectedGroup)?.items ?? []} active={activeTab === "chart"} />
          <ChartLabReportAlertPanel businessDate={businessDate} active={activeTab === "chart"} />
          <VolumeProfile snapshot={data} />
          <section className="chart-subpanel"><div className="chart-subpanel-heading"><h3>출처 · 기준 시점</h3><span>{data.source ?? "출처 없음"}</span></div><dl className="chart-provenance-list"><div><dt>요청 기준일</dt><dd>{data.requested_as_of}</dd></div><div><dt>실제 기준 봉</dt><dd>{chartTimeLabel(data.snapshot.barAsOf, data.timeframe)}</dd></div><div><dt>자료 기준일</dt><dd>{data.source_date ?? "자료 없음"}</dd></div><div><dt>수집 시각</dt><dd>{timeLabel(data.source_fetched_at)}</dd></div><div><dt>자료 상태</dt><dd>{getStatusLabel(data.bar_status)}</dd></div></dl>
            <p className="chart-data-basis">{data.live_fetch ? "조회 시 공급처 요청" : "서버 메모리 캐시 조회"} · 운영 SQLite 저장·후보 순서·주문 기능에 영향 없음</p></section>
        </aside>
      </div>
    </> : <div className="chart-explorer-layout">
      <div className="chart-main-column">{data ? <section className="chart-unavailable"><p className="eyebrow">자료 상태</p><h2>{symbolName || data.display_name || data.symbol || "종목"}</h2><p>{unavailableReasonLabel(data.reason)}</p><p className="data-note">출처 {data.source ?? "없음"} · 자료 기준일 {data.source_date ?? "없음"} · 요청 기준일 {businessDate}</p></section>
        : <section className="chart-empty"><p className="eyebrow">START WITH ONE SYMBOL</p><h2>종목을 골라 차트 자료를 확인하세요.</h2><p>저장 종목 검색 결과나 Yahoo 티커를 조회하면 가격·거래량·지표·출처를 한 화면에 표시합니다. 기본 화면에서는 외부 차트 자료를 요청하지 않습니다.</p></section>}</div>
      <aside className="chart-side-column chart-side-column-single" aria-label="차트 참고 자료"><ChartLabMonitorPanel watchItems={groups.find((group) => group.name === selectedGroup)?.items ?? []} active={activeTab === "chart"} /><ChartLabReportAlertPanel businessDate={businessDate} active={activeTab === "chart"} /></aside>
    </div>}
  </div>;
}
