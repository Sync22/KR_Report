"use client";

import { useMemo, useState } from "react";
import type { ChartExplorerBar, ChartExplorerTimeframe } from "@/domain/chart-explorer";
import type { ChartRange } from "@/domain/chart-viewport";
import type { ChartLabPattern, ChartLabPoint } from "@/domain/chart-lab/patterns";
import { evaluateChartLabEntry, type ChartLabEntryResult, type ChartLabSignal, type ChartLabStrategy } from "@/domain/chart-lab/entry";
import { evaluateChartLabLowEntry, type ChartLabLowEntryResult, type LowFamily } from "@/domain/chart-lab/low-structure";

export const CHART_LAB_STRATEGIES: Array<{ id: ChartLabStrategy; name: string; rule: string }> = [
  { id: "A", name: "추세 전환", rule: "SMA 20/60 상향 교차" },
  { id: "B", name: "침체 반등", rule: "RSI 30 상향 회복" },
  { id: "C", name: "고점 돌파", rule: "직전 20봉 고가 상향 돌파" },
  { id: "F", name: "추세·거래량 돌파", rule: "C + 추세·거래량 확인" },
];

const PATTERN_LABELS: Record<string, string> = {
  "bull-flag": "상승 깃대", "bear-flag": "하락 깃대", "ascending-triangle": "상승 삼각형",
  "descending-triangle": "하락 삼각형", "symmetrical-triangle": "대칭 삼각형",
  "support-breakout": "지지 이탈 관측", "resistance-breakout": "저항 돌파 관측", diagnostic: "탐지 상태",
};
const PATTERN_STATUS: Record<string, string> = {
  forming: "형성 관측", "observed-breakout": "돌파 관측", "observed-crossing": "경계 통과 관측",
  "unsupported-timeframe": "주기 미지원", "insufficient-data": "봉 부족", "data-gap": "자료 간격 확인 필요", "invalid-data": "자료 오류",
};
const LOW_PHASE: Record<string, string> = {
  breached: "지지 이탈 · 회복 대기", reclaimed: "회복 · 재시험 대기", tested: "재시험 · 반등 대기",
  rising: "높은 저점 · 고점 돌파 대기", ready: "조건 구조 준비됨", invalidated: "구조 무효화", expired: "기간 만료", superseded: "새 구조로 교체",
};

function finite(value: unknown): value is number { return typeof value === "number" && Number.isFinite(value); }
function formatted(value: unknown, digits = 2): string { return finite(value) ? new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(value) : "자료 없음"; }
function safeText(value: unknown, fallback = "자료 없음"): string { return typeof value === "string" && value.trim() ? value.replace(/[\u0000-\u001f\u007f]/g, " ").slice(0, 180) : fallback; }

function phaseLabel(value: string): string {
  return ({ unavailable: "자료 부족", exit: "이탈 조건", new: "새 원신호", maintained: "유지 중", tracking: "후속 확인", wait: "조건 대기" } as Record<string, string>)[value] ?? value;
}

function lowPhaseLabel(value: string): string { return LOW_PHASE[value] ?? value; }

export function ChartLabAnalysisPanels({
  bars, timeframe, asOfIndex, currency, patterns, selectedStrategies, mode, maxAtr, onSelectedStrategiesChange, onModeChange, onMaxAtrChange, onFocusIndex,
}: Readonly<{
  bars: ReadonlyArray<ChartExplorerBar>;
  timeframe: ChartExplorerTimeframe;
  asOfIndex: number;
  currency: string | null;
  patterns: ReadonlyArray<ChartLabPattern>;
  selectedStrategies: ReadonlyArray<ChartLabStrategy>;
  mode: "all" | "any";
  maxAtr: number;
  onSelectedStrategiesChange: (strategies: ChartLabStrategy[]) => void;
  onModeChange: (mode: "all" | "any") => void;
  onMaxAtrChange: (maxAtr: number) => void;
  onFocusIndex: (index: number) => void;
}>) {
  const [lowSelected, setLowSelected] = useState<LowFamily[]>(["R", "H"]);
  const historical = asOfIndex < bars.length - 1;
  const entry = useMemo<ChartLabEntryResult>(() => evaluateChartLabEntry(bars, {
    timeframe, asOfIndex, confirmedThroughIndex: null, judgmentReady: true, historical, selected: selectedStrategies, mode, maxAtr,
  }), [asOfIndex, bars, historical, maxAtr, mode, selectedStrategies, timeframe]);
  const low = useMemo<ChartLabLowEntryResult>(() => evaluateChartLabLowEntry(bars, {
    timeframe, asOfIndex, confirmedThroughIndex: null, judgmentReady: true, historical, selected: lowSelected,
  }), [asOfIndex, bars, historical, lowSelected, timeframe]);
  const visiblePatterns = patterns.filter((pattern) => pattern.kind !== "diagnostic").slice(-16).reverse();
  const diagnostics = patterns.filter((pattern) => pattern.kind === "diagnostic");
  const currentBasis = bars[asOfIndex]?.time ?? null;

  function toggleStrategy(strategy: ChartLabStrategy, checked: boolean) {
    onSelectedStrategiesChange(checked ? [...selectedStrategies, strategy].filter((item, index, list) => list.indexOf(item) === index) : selectedStrategies.filter((item) => item !== strategy));
  }

  return <div className="chart-lab-analysis-grid">
    <section className="chart-surface chart-lab-analysis-panel" aria-label="진입 조건 검토">
      <div className="chart-surface-heading"><div><p className="eyebrow">ENTRY REVIEW · UPSTREAM RULES</p><h2>A/B/C/F 조건 검토</h2></div><span>{timeframe === "4h" ? "4시간" : timeframe === "1d" ? "일봉" : "집계 봉"} · 기준 {currentBasis ?? "자료 없음"}</span></div>
      <div className="chart-lab-settings">
        <fieldset><legend>전략 선택</legend>{CHART_LAB_STRATEGIES.map((item) => <label key={item.id}><input type="checkbox" checked={selectedStrategies.includes(item.id)} onChange={(event) => toggleStrategy(item.id, event.target.checked)} /><b>{item.id}</b><span>{item.name}<small>{item.rule}</small></span></label>)}</fieldset>
        <label>조합 방식<select value={mode} onChange={(event) => onModeChange(event.target.value as "all" | "any")}><option value="all">선택 조건 모두</option><option value="any">하나 이상</option></select></label>
        <label>추격 상한<select value={maxAtr} onChange={(event) => onMaxAtrChange(Number(event.target.value))}><option value={0.5}>기준가 + 0.5 ATR</option><option value={1}>기준가 + 1.0 ATR</option><option value={1.5}>기준가 + 1.5 ATR</option></select></label>
      </div>
      <div className="chart-lab-decision" data-state={entry.code}><div><span>{historical ? "과거 기준 · 봉 확정 미확인" : entry.status === "unconfirmed" ? "봉 확정 미확인" : entry.status === "historical" ? "과거 봉 비교" : "계산 상태"}</span><strong>{entry.label}</strong></div><p>{entry.reason}</p><small>계산 조건: {entry.setupDecision.label} · {entry.setupDecision.reason} · 기준 봉 {entry.basis ?? "없음"}</small></div>
      <div className="table-wrap chart-lab-rule-table"><table><thead><tr><th>조건</th><th>원신호</th><th>유지 상태</th><th>필요 자료</th></tr></thead><tbody>{entry.rows.map((row) => <tr key={row.id}><th>{row.id} · {row.name}</th><td>{row.signal === "entry" ? "원신호" : row.signal === "exit" ? "이탈" : "없음"}</td><td>{phaseLabel(row.phase)}</td><td>{row.readiness.ready ? "확인됨" : row.readiness.missing.join(" · ") || "자료 없음"}</td></tr>)}</tbody></table></div>
      <p className="chart-lab-footnote">지표 계산 상태와 최종 조건 판정을 분리합니다. 현재 원천의 봉 확정 상태는 unknown이며, 이 화면은 확인된 주문·체결이나 수익성을 뜻하지 않습니다.</p>
    </section>

    <section className="chart-surface chart-lab-analysis-panel" aria-label="저점 구조 검토">
      <div className="chart-surface-heading"><div><p className="eyebrow">LOW STRUCTURE · R / H</p><h2>저점 구조와 확인 단계</h2></div><span>{historical ? "과거 기준 · 확정 미확인" : low.reviewStatus === "unconfirmed" ? "확정 미확인" : low.reviewStatus === "historical" ? "과거 비교" : "계산됨"}</span></div>
      <div className="chart-lab-low-toggles"><span>저점 방식</span>{(["R", "H"] as const).map((family) => <label key={family}><input type="checkbox" checked={lowSelected.includes(family)} onChange={(event) => setLowSelected((current) => event.target.checked ? [...current, family] : current.filter((item) => item !== family))} />{family === "R" ? "R · 지지 회복" : "H · 높은 저점"}</label>)}</div>
      <div className="chart-lab-decision" data-state={low.code}><div><span>{low.setup}</span><strong>{low.label}</strong></div><p>{low.reason}</p><small>계산 기준 {low.basis ?? currentBasis ?? "자료 없음"} · 상한 {formatted(low.chaseLimit)} {currency ?? ""}</small></div>
      <ul className="chart-lab-low-rows">{low.rows.map((row) => <li key={row.id}><div><strong>{row.id} · {row.name}</strong><span>{lowPhaseLabel(row.phase)}</span></div><p>{row.description.reason}</p><small>{row.structure ? `구조 시작 ${row.structure.startedAt} · 알려진 시각 ${row.structure.knownAt}` : row.description.label}</small></li>)}</ul>
      {low.analysisReason ? <p className="chart-lab-footnote">구조 데이터: {safeText(low.analysisReason)}</p> : null}
      {low.status === "unsupported" ? <p className="chart-lab-footnote">이 주기에서 필요한 세션 연속성 자료가 없어 R/H를 계산하지 않습니다.</p> : null}
    </section>

    <details className="chart-surface chart-lab-analysis-panel chart-lab-pattern-panel chart-disclosure" role="group" aria-label="패턴과 과거 사건">
      <summary className="chart-surface-heading chart-disclosure-summary"><div><p className="eyebrow">PATTERN HISTORY</p><h2>패턴 · 경계 사건</h2></div><span>{visiblePatterns.length}건 · {currentBasis ?? "자료 없음"}</span></summary>
      <div className="chart-disclosure-content">
      {visiblePatterns.length ? <ul className="chart-lab-pattern-list">{visiblePatterns.map((pattern, index) => {
        const basisIndex = pattern.basis.endIndex;
        const measurement = Object.entries(pattern.measurements).slice(0, 3).map(([name, value]) => `${name} ${typeof value === "number" ? formatted(value) : safeText(value)}`).join(" · ");
        return <li key={`${pattern.kind}-${pattern.basis.startTime}-${pattern.ruleVersion}-${index}`}>
          <button type="button" disabled={basisIndex === null} onClick={() => basisIndex !== null && onFocusIndex(basisIndex)}>
            <strong>{PATTERN_LABELS[pattern.kind] ?? pattern.kind}</strong><span>{PATTERN_STATUS[pattern.status] ?? pattern.status} · {pattern.direction === "up" ? "상향" : pattern.direction === "down" ? "하향" : "방향 미정"}</span>
            <small>{pattern.basis.startTime ?? "기준 없음"} → {pattern.basis.endTime ?? "기준 없음"} · {pattern.ruleVersion}</small>
            {measurement ? <small>{measurement}</small> : null}
          </button>
        </li>;
      })}</ul> : <p className="data-note">선택 기준 봉까지 표시할 깃대·삼각형·수평 경계 사건이 없습니다. 없음은 반대 방향 신호가 아닙니다.</p>}
      {diagnostics.length ? <p className="chart-lab-footnote">탐지 진단: {[...new Set(diagnostics.map((item) => PATTERN_STATUS[item.status] ?? item.status))].join(" · ")}</p> : null}
      <p className="chart-lab-footnote">과거 봉 선택 시 그 시점 뒤의 데이터는 전략·패턴 계산에서 제외됩니다. 사건을 누르면 해당 기준 봉으로 이동합니다.</p>
      </div>
    </details>
  </div>;
}

function pointVisible(point: ChartLabPoint, range: ChartRange): boolean {
  return point.index >= range.start && point.index < range.end;
}

export function ChartLabPatternOverlay({ patterns, bars, range, x, y }: Readonly<{
  patterns: ReadonlyArray<ChartLabPattern>;
  bars: ReadonlyArray<ChartExplorerBar>;
  range: ChartRange;
  x: (index: number) => number;
  y: (value: number) => number;
}>) {
  const colorFor = (pattern: ChartLabPattern) => pattern.family === "flag" ? "#b66d26" : pattern.family === "horizontal" ? "#117e79" : "#285fc2";
  const latestByFamily = new Map<ChartLabPattern["family"], ChartLabPattern>();
  for (const pattern of patterns) {
    const endIndex = pattern.basis.endIndex;
    if (pattern.kind === "diagnostic" || endIndex === null || endIndex < range.start || endIndex >= range.end) continue;
    if ((latestByFamily.get(pattern.family)?.basis.endIndex ?? -1) <= endIndex) latestByFamily.set(pattern.family, pattern);
  }
  return <g className="chart-lab-pattern-overlay" aria-label="차트 패턴 구조 오버레이">
    {patterns.filter((pattern) => pattern.kind !== "diagnostic").map((pattern, index) => {
      const color = colorFor(pattern);
      const lines = [pattern.geometry.upper, pattern.geometry.lower, pattern.geometry.boundary].filter((line) => line && pointVisible(line.start, range) && pointVisible(line.end, range));
      const points = pattern.geometry.points?.filter((point) => pointVisible(point, range)) ?? [];
      const pole = pattern.geometry.pole?.filter((point) => pointVisible(point, range)) ?? [];
      const { upper, lower } = pattern.geometry;
      const areaPoints = upper && lower && [upper.start, upper.end, lower.end, lower.start].every((point) => pointVisible(point, range))
        ? [upper.start, upper.end, lower.end, lower.start] : [];
      if (!lines.length && points.length < 2 && pole.length < 2 && areaPoints.length < 3) return null;
      const local = (point: ChartLabPoint) => `${x(point.index - range.start)},${y(point.price)}`;
      const latestIndex = pattern.basis.endIndex;
      const latestBar = latestIndex === null || latestIndex < range.start || latestIndex >= range.end ? null : bars[latestIndex - range.start];
      const latestCallout = latestByFamily.get(pattern.family) === pattern && latestBar;
      const latestX = latestCallout && latestIndex !== null ? x(latestIndex - range.start) : 0;
      const calloutAtLeft = latestIndex !== null && latestIndex - range.start > (range.end - range.start) * .72;
      const calloutText = `${PATTERN_LABELS[pattern.kind] ?? pattern.kind} · ${PATTERN_STATUS[pattern.status] ?? pattern.status}`;
      const calloutWidth = Math.min(220, Math.max(128, calloutText.length * 8 + 16));
      const calloutX = calloutAtLeft ? latestX - calloutWidth - 8 : latestX + 8;
      const calloutY = latestBar ? Math.max(24, Math.min(292, y(latestBar.close) - 10)) : 0;
      return <g key={`${pattern.kind}-${pattern.basis.startTime}-${pattern.ruleVersion}-${index}`} opacity=".8" data-pattern-kind={pattern.kind}>
        {areaPoints.length ? <polygon points={areaPoints.map(local).join(" ")} fill={color} fillOpacity={pattern.status === "forming" ? ".24" : ".16"} stroke="none" /> : null}
        {lines.map((line, lineIndex) => <line key={lineIndex} x1={x(line!.start.index - range.start)} y1={y(line!.start.price)} x2={x(line!.end.index - range.start)} y2={y(line!.end.price)} stroke={color} strokeWidth="2" strokeDasharray={pattern.status === "forming" ? "5 4" : undefined} />)}
        {points.length > 1 ? <polyline points={points.map(local).join(" ")} fill="none" stroke={color} strokeWidth="2" /> : null}
        {pole.length > 1 ? <polyline points={pole.map(local).join(" ")} fill="none" stroke={color} strokeWidth="3" /> : null}
        {latestIndex !== null && latestBar ? <circle cx={latestX} cy={y(latestBar.close)} r="4" fill={color} stroke="white" strokeWidth="1" /> : null}
        {latestCallout ? <g className="chart-pattern-callout" pointerEvents="none"><rect x={calloutX} y={calloutY - 14} width={calloutWidth} height="22" rx="3" fill="var(--sm-panel)" stroke={color} strokeWidth="1" /><text x={calloutX + 6} y={calloutY + 1} style={{ fill: color }}>{calloutText}</text></g> : null}
      </g>;
    })}
  </g>;
}

export function ChartLabSignalOverlay({ signals, selected, bars, range, x, y }: Readonly<{
  signals: ChartLabEntryResult["signalHistory"];
  selected: ReadonlyArray<ChartLabStrategy>;
  bars: ReadonlyArray<ChartExplorerBar>;
  range: ChartRange;
  x: (index: number) => number;
  y: (value: number) => number;
}>) {
  const markers: Array<{ key: string; strategy: string; index: number; signal: ChartLabSignal }> = [];
  for (const strategy of selected) {
    signals[strategy].forEach((signal, index) => {
      if (signal !== "none" && index >= range.start && index < range.end) markers.push({ key: `${strategy}-${index}-${signal}`, strategy, index, signal });
    });
  }
  return <g className="chart-lab-signal-overlay" aria-label="전략 원신호 표시">
    {markers.map((marker) => {
      const bar = bars[marker.index - range.start];
      if (!bar) return null;
      const entry = marker.signal === "entry";
      const color = entry ? "#338764" : "#c66b4a";
      const strategy = CHART_LAB_STRATEGIES.find((item) => item.id === marker.strategy);
      const cx = x(marker.index - range.start);
      const cy = entry ? y(bar.low) + 9 : y(bar.high) - 9;
      return <g key={marker.key} role="img" aria-label={`${marker.strategy} ${strategy?.name ?? "전략"} · ${entry ? "진입" : "이탈"} 원신호 · 봉 확정 미확인`} data-strategy-signal={marker.strategy} data-signal={marker.signal}>
        <title>{`${marker.strategy} · ${strategy?.name ?? "전략 규칙 자료 없음"} · ${entry ? "진입" : "이탈"} 원신호 · 봉 확정 미확인`}</title>
        <path d={`M ${cx} ${cy - (entry ? 4 : -4)} L ${cx - 4} ${cy + (entry ? 3 : -3)} L ${cx + 4} ${cy + (entry ? 3 : -3)} Z`} fill={color} />
        <text className="chart-signal-marker-label" x={cx + 6} y={cy + 4} style={{ fill: color }}>{marker.strategy}</text>
      </g>;
    })}
  </g>;
}
