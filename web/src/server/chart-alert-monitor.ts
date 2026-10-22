import "server-only";

import { chartAlertEventId } from "../domain/chart-alerts.ts";
import type { ChartExplorerBar } from "../domain/chart-explorer.ts";
import { detectChartLabPatterns, type ChartLabPattern } from "../domain/chart-lab/patterns.ts";
import { acquireChartAlertLock, chartAlertSpoolPath, chartAlertStatePath, emptyChartAlertState, readChartAlertState, writeChartAlertEvent, writeChartAlertState, type ChartAlertEvent, type ChartAlertState, type ChartAlertWatch } from "./chart-alert-store.ts";
import { chartExplorerService, type ChartAlertMinuteResult } from "./chart-explorer.ts";

const POLL_INTERVAL_MS = 60_000;
const MIN_REQUEST_GAP_MS = 6_000;
const MAX_EVENTS = 200;
const MAX_KNOWN_EVENT_IDS = 1_000;

type Dependencies = {
  statePath: string;
  spoolPath: string;
  lockPath: string;
  getMinuteBars: (date: string, symbol: string) => Promise<ChartAlertMinuteResult>;
  detectPatterns: (bars: readonly ChartExplorerBar[], timeframe: "1m") => readonly ChartLabPattern[];
  now: () => Date;
  marketOpen: (date: Date) => boolean | Promise<boolean>;
  providerConfigured: () => boolean;
};

type WatchInput = { report_business_date: string; stock_code: string; stock_name: string; report_count: number; report_reason: "리포트 집중" };

export class ChartAlertMonitorService {
  private readonly dependencies: Dependencies;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private busy = false;
  private writes: Promise<void> = Promise.resolve();
  private releaseLease: (() => Promise<void>) | null = null;
  private deferPollingUntil = 0;

  constructor(dependencies: Partial<Dependencies> = {}) {
    const statePath = dependencies.statePath ?? chartAlertStatePath();
    this.dependencies = {
      statePath,
      spoolPath: dependencies.spoolPath ?? chartAlertSpoolPath(),
      lockPath: dependencies.lockPath ?? `${statePath}.lock`,
      getMinuteBars: dependencies.getMinuteBars ?? ((date, symbol) => chartExplorerService.getAlertMinuteBars(date, symbol)),
      detectPatterns: dependencies.detectPatterns ?? detectChartLabPatterns,
      now: dependencies.now ?? (() => new Date()),
      marketOpen: dependencies.marketOpen ?? ((date) => chartExplorerService.isKrxMarketOpenAt(date)),
      providerConfigured: dependencies.providerConfigured ?? (() => chartExplorerService.chartAlertProviderConfigured),
    };
  }

  async getStatus(): Promise<{ state: ChartAlertState; intervals: { focusMs: number }; ownerActiveElsewhere: boolean; providerReady: boolean }> {
    const state = await this.read();
    const providerReady = this.dependencies.providerConfigured();
    if (state.running && !this.releaseLease) {
      this.releaseLease = await acquireChartAlertLock(this.dependencies.lockPath);
      if (this.releaseLease) this.schedule(0);
      else return { state, intervals: { focusMs: POLL_INTERVAL_MS }, ownerActiveElsewhere: true, providerReady };
    }
    return { state, intervals: { focusMs: POLL_INTERVAL_MS }, ownerActiveElsewhere: false, providerReady };
  }

  async addWatch(input: WatchInput): Promise<ChartAlertState> {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(input.report_business_date) || !/^\d{6}$/.test(input.stock_code) ||
      !input.stock_name.trim() || input.stock_name.length > 120 || !Number.isInteger(input.report_count) || input.report_count < 2 ||
      input.report_reason !== "리포트 집중") throw new TypeError("invalid-chart-alert-watch");
    return this.withLease(async () => this.update((state) => {
      const watchId = `${input.report_business_date}-${input.stock_code}`;
      if (state.watches.some((watch) => watch.watch_id === watchId)) return state;
      if (state.watches.length >= 3) throw new TypeError("chart-alert-watch-limit");
      const watch: ChartAlertWatch = {
        watch_id: watchId,
        report_business_date: input.report_business_date,
        stock_code: input.stock_code,
        stock_name: input.stock_name.trim(),
        report_count: input.report_count,
        added_at: this.dependencies.now().toISOString(),
        initialized: false,
        last_polled_at: null,
        last_bar_time: null,
        failure_count: 0,
        known_event_ids: [],
      };
      return { ...state, watches: [...state.watches, watch] };
    }));
  }

  async removeWatch(watchId: string): Promise<ChartAlertState> {
    return this.withLease(async () => this.update((state) => ({ ...state, watches: state.watches.filter((watch) => watch.watch_id !== watchId) })));
  }

  async start(): Promise<ChartAlertState> {
    if (!this.dependencies.providerConfigured()) throw new TypeError("chart-alert-provider-not-configured");
    if (!this.releaseLease) this.releaseLease = await acquireChartAlertLock(this.dependencies.lockPath);
    if (!this.releaseLease) throw new TypeError("chart-alert-monitor-owned-elsewhere");
    try {
      const state = await this.update((current) => {
        if (!current.watches.length) throw new TypeError("chart-alert-watches-required");
        return current.running ? current : { ...current, running: true, startedAt: this.dependencies.now().toISOString(), lastError: null };
      });
      this.schedule(0);
      return state;
    } catch (error) {
      await this.release();
      throw error;
    }
  }

  async pause(): Promise<ChartAlertState> {
    this.clearTimer();
    if (!this.releaseLease) {
      this.releaseLease = await acquireChartAlertLock(this.dependencies.lockPath);
      if (!this.releaseLease) throw new TypeError("chart-alert-monitor-owned-elsewhere");
    }
    const state = await this.update((current) => ({ ...current, running: false }));
    await this.release();
    return state;
  }

  async pollOnce(): Promise<void> {
    this.clearTimer();
    if (!this.releaseLease) throw new TypeError("chart-alert-monitor-not-owner");
    await this.tick();
  }

  private async withLease<T>(work: () => Promise<T>): Promise<T> {
    if (this.releaseLease) return work();
    const release = await acquireChartAlertLock(this.dependencies.lockPath);
    if (!release) throw new TypeError("chart-alert-monitor-owned-elsewhere");
    try { return await work(); }
    finally { await release(); }
  }

  private async release(): Promise<void> {
    const release = this.releaseLease;
    this.releaseLease = null;
    await release?.();
  }

  private async read(): Promise<ChartAlertState> {
    return readChartAlertState(this.dependencies.statePath);
  }

  private update(change: (state: ChartAlertState) => ChartAlertState): Promise<ChartAlertState> {
    const operation = this.writes.then(async () => {
      const next = change(await this.read());
      await writeChartAlertState(next, this.dependencies.statePath);
      return next;
    });
    this.writes = operation.then(() => undefined, () => undefined);
    return operation;
  }

  private schedule(delayMs: number): void {
    this.clearTimer();
    this.timer = setTimeout(() => { void this.tick(); }, Math.max(0, delayMs));
    this.timer.unref?.();
  }

  private clearTimer(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private nextDelay(state: ChartAlertState): number {
    const now = this.dependencies.now().getTime();
    const due = state.watches.map((watch) => ({ watch, at: watch.last_polled_at
      ? Date.parse(watch.last_polled_at) + POLL_INTERVAL_MS * Math.min(8, 2 ** Math.min(3, watch.failure_count))
      : Number.NEGATIVE_INFINITY })).sort((left, right) => left.at - right.at);
    const symbolDelay = due.length ? Math.max(0, due[0].at - now) : POLL_INTERVAL_MS;
    const lastPoll = state.lastPollAt ? Date.parse(state.lastPollAt) : Number.NEGATIVE_INFINITY;
    const rateDelay = Number.isFinite(lastPoll) ? Math.max(0, lastPoll + MIN_REQUEST_GAP_MS - now) : 0;
    return Math.max(symbolDelay, rateDelay, this.deferPollingUntil - now);
  }

  private async tick(): Promise<void> {
    this.timer = null;
    if (this.busy || !this.releaseLease) return;
    this.busy = true;
    let selectedId: string | null = null;
    const polledAt = this.dependencies.now().toISOString();
    try {
      const state = await this.read();
      if (!state.running || !state.watches.length) return;
      const now = this.dependencies.now();
      const selected = state.watches.map((watch) => ({ watch, due: watch.last_polled_at
        ? Date.parse(watch.last_polled_at) + POLL_INTERVAL_MS * Math.min(8, 2 ** Math.min(3, watch.failure_count))
        : Number.NEGATIVE_INFINITY })).filter((item) => item.due <= now.getTime()).sort((left, right) => left.due - right.due)[0]?.watch;
      if (!selected) return;
      selectedId = selected.watch_id;
      try {
        if (!await this.dependencies.marketOpen(now)) {
          this.deferPollingUntil = now.getTime() + POLL_INTERVAL_MS;
          return;
        }
        this.deferPollingUntil = 0;
      } catch {
        this.deferPollingUntil = now.getTime() + POLL_INTERVAL_MS;
        await this.recordFailure(selectedId, polledAt, "market_calendar_unavailable");
        return;
      }
      const result = await this.dependencies.getMinuteBars(selected.report_business_date, selected.stock_code);
      if (!result.available) { await this.recordFailure(selectedId, polledAt, result.reason); return; }
      const lastBar = result.bars.at(-1);
      const lagMs = lastBar ? now.getTime() - Date.parse(lastBar.time) : Number.POSITIVE_INFINITY;
      if (!lastBar || lagMs < -60_000 || lagMs > 3 * 60_000) {
        await this.recordFailure(selectedId, polledAt, "minute_bars_stale_or_unavailable");
        return;
      }
      const patterns = this.dependencies.detectPatterns(result.bars, "1m").filter(isEventPattern);
      await this.recordPatterns(selected, result, patterns, polledAt, lastBar.time);
    } catch (error) {
      await this.recordFailure(selectedId, polledAt, error instanceof TypeError ? error.message.slice(0, 180) : "chart_alert_poll_failed").catch(() => undefined);
    } finally {
      this.busy = false;
      const state = await this.read().catch(() => emptyChartAlertState());
      if (state.running) this.schedule(this.nextDelay(state));
    }
  }

  private async recordFailure(watchId: string | null, polledAt: string, reason: string): Promise<void> {
    await this.update((state) => ({
      ...state,
      lastPollAt: polledAt,
      lastError: reason,
      watches: state.watches.map((watch) => watch.watch_id === watchId
        ? { ...watch, last_polled_at: polledAt, failure_count: Math.min(8, watch.failure_count + 1) }
        : watch),
    }));
  }

  private async recordPatterns(
    selected: ChartAlertWatch,
    result: Extract<ChartAlertMinuteResult, { available: true }>,
    patterns: readonly ChartLabPattern[],
    polledAt: string,
    lastBarTime: string,
  ): Promise<void> {
    const state = await this.read();
    const current = state.watches.find((watch) => watch.watch_id === selected.watch_id);
    if (!state.running || !current) return;
    const additions = current.initialized
      ? patterns.filter((pattern) => !current.known_event_ids.includes(eventId(selected, pattern)))
        .map((pattern) => eventSnapshot(selected, result, pattern, polledAt))
      : [];
    for (const event of additions) await writeChartAlertEvent(event, this.dependencies.spoolPath);
    const knownIds = [...new Set([...current.known_event_ids, ...patterns.map((pattern) => eventId(selected, pattern))])].slice(-MAX_KNOWN_EVENT_IDS);
    await this.update((latest) => ({
      ...latest,
      lastPollAt: polledAt,
      lastError: null,
      watches: latest.watches.map((watch) => watch.watch_id === selected.watch_id
        ? { ...watch, initialized: true, last_polled_at: polledAt, last_bar_time: lastBarTime, failure_count: 0, known_event_ids: knownIds }
        : watch),
      events: [...latest.events, ...additions].slice(-MAX_EVENTS),
    }));
  }
}

function eventId(watch: ChartAlertWatch, pattern: ChartLabPattern): string {
  return chartAlertEventId({ watchId: watch.watch_id, symbol: watch.stock_code,
    reportBusinessDate: watch.report_business_date, stockName: watch.stock_name, reportCount: watch.report_count,
    ruleVersion: pattern.ruleVersion, kind: pattern.kind, direction: pattern.direction!,
    basisStartTime: pattern.basis.startTime!, status: pattern.status });
}

function isEventPattern(pattern: ChartLabPattern): boolean {
  return pattern.kind !== "diagnostic" && !!pattern.direction && pattern.basis.startTime !== null &&
    pattern.basis.endTime !== null && pattern.status !== "unsupported-timeframe" && pattern.status !== "insufficient-data" &&
    pattern.status !== "data-gap" && pattern.status !== "invalid-data";
}

function eventSnapshot(
  watch: ChartAlertWatch,
  result: Extract<ChartAlertMinuteResult, { available: true }>,
  pattern: ChartLabPattern,
  observedAt: string,
): ChartAlertEvent {
  return {
    schema_version: 1,
    event_id: eventId(watch, pattern),
    watch_id: watch.watch_id,
    report_business_date: watch.report_business_date,
    stock_code: watch.stock_code,
    stock_name: watch.stock_name,
    report_count: watch.report_count,
    report_reason: "리포트 집중",
    rule_key: pattern.ruleVersion,
    rule_version: pattern.ruleVersion,
    timeframe: "1m",
    kind: pattern.kind,
    direction: pattern.direction as "up" | "down" | "neutral",
    observed_state: pattern.status,
    basis_start_time: pattern.basis.startTime!,
    basis_bar_time: pattern.basis.endTime!,
    source: "Toss OpenAPI · 1m candles",
    source_fetched_at: result.sourceFetchedAt,
    finality: "unknown",
    observed_at: observedAt,
  };
}

export const chartAlertMonitorService = new ChartAlertMonitorService();
