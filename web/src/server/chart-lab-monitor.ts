import "server-only";

import type { ChartExplorerBar, ChartExplorerSuccess, ChartExplorerTimeframe } from "../domain/chart-explorer.ts";
import { detectChartLabPatterns, type ChartLabPattern } from "../domain/chart-lab/patterns.ts";
import { appendChartLabEvents, chartLabEventId, type ChartLabEventRecord } from "../domain/chart-lab/events.ts";
import { chartExplorerService } from "./chart-explorer.ts";
import { chartLabStatePath, emptyChartLabState, readChartLabState, writeChartLabState, type ChartLabMonitorState } from "./chart-lab-store.ts";

const REGULAR_INTERVAL_MS = 5 * 60_000;
const FOCUS_INTERVAL_MS = 30_000;
const MIN_REQUEST_GAP_MS = 6_000;
const MAX_EVENTS = 500;

type ChartResult = { status: number; payload: ChartExplorerSuccess | { available: false; reason?: string } };
type Dependencies = {
  statePath: string;
  getChart: (date: string, symbol: string, timeframe: ChartExplorerTimeframe) => Promise<ChartResult>;
  detectPatterns: (bars: readonly ChartExplorerBar[], timeframe: ChartExplorerTimeframe) => readonly ChartLabPattern[];
  now: () => Date;
};
type WatchSymbol = ChartLabMonitorState["symbols"][number];

export class ChartLabMonitorService {
  private readonly dependencies: Dependencies;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private busy = false;
  private writes: Promise<void> = Promise.resolve();

  constructor(dependencies: Partial<Dependencies> = {}) {
    this.dependencies = {
      statePath: dependencies.statePath ?? chartLabStatePath(),
      getChart: dependencies.getChart ?? ((date, symbol, timeframe) => chartExplorerService.getChart(date, symbol, timeframe)),
      detectPatterns: dependencies.detectPatterns ?? detectChartLabPatterns,
      now: dependencies.now ?? (() => new Date()),
    };
  }

  async getStatus(): Promise<{ state: ChartLabMonitorState; intervals: { regularMs: number; focusMs: number } }> {
    const state = await this.read();
    if (state.running && !this.timer && !this.busy) this.scheduleNext(state);
    return { state, intervals: { regularMs: REGULAR_INTERVAL_MS, focusMs: FOCUS_INTERVAL_MS } };
  }

  async configure(input: ReadonlyArray<{ symbol: string; name: string; focus: boolean }>): Promise<ChartLabMonitorState> {
    const state = await this.update((current) => {
      const old = new Map(current.symbols.map((item) => [item.symbol, item]));
      const symbols = input.map((item) => {
        const prior = old.get(item.symbol);
        return { symbol: item.symbol, name: item.name, focus: item.focus, lastPolledAt: prior?.lastPolledAt ?? null, failureCount: prior?.failureCount ?? 0 };
      });
      if (current.running && !symbols.length) throw new TypeError("monitor-symbols-required");
      return { ...current, symbols };
    });
    if (state.running) this.scheduleNext(state);
    return state;
  }

  async start(): Promise<ChartLabMonitorState> {
    const state = await this.update((current) => {
      if (!current.symbols.length) throw new TypeError("monitor-symbols-required");
      return current.running ? current : { ...current, running: true, startedAt: this.dependencies.now().toISOString(), lastError: null };
    });
    this.scheduleNext(state, 0);
    return state;
  }

  async pause(): Promise<ChartLabMonitorState> {
    this.clearTimer();
    return this.update((current) => ({ ...current, running: false }));
  }

  async pollDueOnce(): Promise<void> {
    this.clearTimer();
    await this.tick();
  }

  private async read(): Promise<ChartLabMonitorState> {
    return readChartLabState(this.dependencies.statePath);
  }

  private update(change: (state: ChartLabMonitorState) => ChartLabMonitorState): Promise<ChartLabMonitorState> {
    const operation = this.writes.then(async () => {
      const current = await this.read();
      const next = change(current);
      await writeChartLabState(next, this.dependencies.statePath);
      return next;
    });
    this.writes = operation.then(() => undefined, () => undefined);
    return operation;
  }

  private scheduleNext(state: ChartLabMonitorState, minimumDelay = 0): void {
    if (!state.running || this.busy) return;
    const now = this.dependencies.now().getTime();
    const due = state.symbols.map((symbol) => ({ symbol, at: nextDueAt(symbol) })).sort((left, right) => {
      if (left.symbol.focus !== right.symbol.focus) return left.symbol.focus ? -1 : 1;
      return left.at - right.at;
    });
    const symbolDelay = due.length ? Math.max(0, due[0].at - now) : Number.POSITIVE_INFINITY;
    const lastPoll = state.lastPollAt ? Date.parse(state.lastPollAt) : Number.NEGATIVE_INFINITY;
    const rateDelay = Number.isFinite(lastPoll) ? Math.max(0, lastPoll + MIN_REQUEST_GAP_MS - now) : 0;
    this.schedule(Math.max(minimumDelay, symbolDelay, rateDelay));
  }

  private schedule(delayMs: number): void {
    this.clearTimer();
    if (!Number.isFinite(delayMs)) return;
    this.timer = setTimeout(() => { void this.tick(); }, Math.max(0, delayMs));
    this.timer.unref?.();
  }

  private clearTimer(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private async tick(): Promise<void> {
    this.timer = null;
    if (this.busy) return;
    this.busy = true;
    let pollingSymbol: string | null = null;
    try {
      const state = await this.read();
      if (!state.running || !state.symbols.length) return;
      const now = this.dependencies.now();
      const due = state.symbols.map((symbol) => ({ symbol, at: nextDueAt(symbol) }))
        .filter((item) => item.at <= now.getTime())
        .sort((left, right) => Number(right.symbol.focus) - Number(left.symbol.focus) || left.at - right.at);
      if (!due.length) return;
      const selected = due[0].symbol;
      pollingSymbol = selected.symbol;
      const requestedAt = now.toISOString();
      const result = await this.dependencies.getChart(koreaDate(now), selected.symbol, "1d");
      if (result.status !== 200 || !result.payload.available) {
        const reason = result.payload.available ? "provider_error" : result.payload.reason ?? "provider_unavailable";
        await this.recordFailure(selected.symbol, requestedAt, reason);
        return;
      }
      const payload = result.payload;
      const detections = this.dependencies.detectPatterns(payload.bars, "1d");
      await this.recordPatterns(selected, payload, detections, requestedAt);
    } catch (error) {
      const reason = error instanceof TypeError ? error.message.slice(0, 180) : "monitor_poll_failed";
      const state = await this.read().catch(() => emptyChartLabState());
      const selected = state.symbols.find((item) => item.symbol === pollingSymbol);
      if (selected) await this.recordFailure(selected.symbol, this.dependencies.now().toISOString(), reason).catch(() => undefined);
    } finally {
      this.busy = false;
      const state = await this.read().catch(() => emptyChartLabState());
      if (state.running) this.scheduleNext(state);
    }
  }

  private async recordFailure(symbol: string, polledAt: string, reason: string): Promise<void> {
    await this.update((state) => {
      if (!state.running) return state;
      return {
        ...state,
        lastPollAt: polledAt,
        lastError: reason,
        symbols: state.symbols.map((item) => item.symbol === symbol
          ? { ...item, lastPolledAt: polledAt, failureCount: Math.min(8, item.failureCount + 1) } : item),
      };
    });
  }

  private async recordPatterns(
    selected: WatchSymbol,
    payload: ChartExplorerSuccess,
    patterns: readonly ChartLabPattern[],
    polledAt: string,
  ): Promise<void> {
    await this.update((state) => {
      if (!state.running) return state;
      const current = state.symbols.find((item) => item.symbol === selected.symbol);
      if (!current) return state;
      const additions = patterns.filter(isEventPattern).map((pattern) => eventSnapshot(selected, payload, pattern, polledAt))
      return {
        ...state,
        lastPollAt: polledAt,
        lastError: null,
        symbols: state.symbols.map((item) => item.symbol === selected.symbol
          ? { ...item, lastPolledAt: polledAt, failureCount: 0 } : item),
        events: appendChartLabEvents(state.events, additions, MAX_EVENTS),
      };
    });
  }
}

function nextDueAt(symbol: WatchSymbol): number {
  const base = symbol.focus ? FOCUS_INTERVAL_MS : REGULAR_INTERVAL_MS;
  const backoff = Math.min(8, 2 ** Math.min(3, symbol.failureCount));
  return symbol.lastPolledAt ? Date.parse(symbol.lastPolledAt) + base * backoff : Number.NEGATIVE_INFINITY;
}

function isEventPattern(pattern: ChartLabPattern): boolean {
  return pattern.kind !== "diagnostic" && pattern.basis.startIndex !== null && pattern.basis.endIndex !== null &&
    pattern.basis.startTime !== null && pattern.basis.endTime !== null;
}

function eventSnapshot(
  item: WatchSymbol,
  payload: ChartExplorerSuccess,
  pattern: ChartLabPattern,
  observedAt: string,
): ChartLabEventRecord {
  const startIndex = pattern.basis.startIndex!;
  const endIndex = pattern.basis.endIndex!;
  return {
    event_id: chartLabEventId({ symbol: item.symbol, kind: pattern.kind, basisStartTime: pattern.basis.startTime!, ruleVersion: pattern.ruleVersion, status: pattern.status }),
    symbol: item.symbol,
    name: item.name,
    timeframe: "1d",
    kind: pattern.kind,
    status: pattern.status,
    direction: pattern.direction,
    rule_version: pattern.ruleVersion,
    data_status: pattern.dataStatus,
    basis_start_time: pattern.basis.startTime,
    basis_end_time: pattern.basis.endTime,
    observed_at: observedAt,
    source: payload.source,
    source_fetched_at: payload.source_fetched_at,
    source_date: payload.source_date,
    adjusted: payload.adjusted,
    bar_status: payload.bar_status,
    snapshot: {
      pattern,
      bars: payload.bars.slice(Math.max(0, startIndex), Math.min(payload.bars.length, endIndex + 1)),
    },
  };
}

function koreaDate(date: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const values = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export const chartLabMonitorService = new ChartLabMonitorService();
