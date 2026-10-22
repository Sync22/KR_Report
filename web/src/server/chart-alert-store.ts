import { randomUUID } from "node:crypto";
import { mkdir, open, readFile, readdir, rename, stat, unlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const MAX_STATE_BYTES = 1_048_576;
const MAX_EVENTS = 200;
const MAX_SPOOL_FILES = 500;
const MAX_EVENT_BYTES = 32 * 1024;
const SOURCES = new Set(["Toss OpenAPI · 1m candles"]);
const PATTERN_KINDS = new Set(["bull-flag", "bear-flag", "ascending-triangle", "descending-triangle", "symmetrical-triangle", "support-breakout", "resistance-breakout"]);
const PATTERN_STATUSES = new Set(["forming", "observed-breakout", "observed-crossing"]);
const DIRECTIONS = new Set(["up", "down", "neutral"]);
const RULE_VERSIONS = new Set(["flag-m1-v1", "triangle-m1-v1", "horizontal-m1-v1"]);

export type ChartAlertWatch = {
  watch_id: string;
  report_business_date: string;
  stock_code: string;
  stock_name: string;
  report_count: number;
  added_at: string;
  initialized: boolean;
  last_polled_at: string | null;
  last_bar_time: string | null;
  failure_count: number;
  known_event_ids: string[];
};

export type ChartAlertEvent = {
  schema_version: 1;
  event_id: string;
  watch_id: string;
  report_business_date: string;
  stock_code: string;
  stock_name: string;
  report_count: number;
  report_reason: "리포트 집중";
  rule_key: string;
  rule_version: string;
  timeframe: "1m";
  kind: string;
  direction: "up" | "down" | "neutral";
  observed_state: string;
  basis_start_time: string;
  basis_bar_time: string;
  source: "Toss OpenAPI · 1m candles";
  source_fetched_at: string;
  finality: "unknown";
  observed_at: string;
};

export type ChartAlertState = {
  schemaVersion: 1;
  running: boolean;
  startedAt: string | null;
  lastPollAt: string | null;
  lastError: string | null;
  watches: ChartAlertWatch[];
  events: ChartAlertEvent[];
};

export function chartAlertStatePath(): string {
  return path.join(localStateRoot(), "StockMonitor", "ChartLab", "report-alerts.json");
}

export function chartAlertSpoolPath(): string {
  return path.join(localStateRoot(), "StockMonitor", "ChartLab", "alert-spool");
}

export function emptyChartAlertState(): ChartAlertState {
  return { schemaVersion: 1, running: false, startedAt: null, lastPollAt: null, lastError: null, watches: [], events: [] };
}

export async function readChartAlertState(filePath = chartAlertStatePath()): Promise<ChartAlertState> {
  try {
    const info = await stat(filePath);
    if (info.size > MAX_STATE_BYTES) throw new TypeError("invalid-chart-alert-state");
    return validateState(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if (record(error).code === "ENOENT") return emptyChartAlertState();
    throw new TypeError("invalid-chart-alert-state");
  }
}

export async function writeChartAlertState(state: ChartAlertState, filePath = chartAlertStatePath()): Promise<void> {
  const contents = JSON.stringify(validateState(state));
  if (Buffer.byteLength(contents, "utf8") > MAX_STATE_BYTES) throw new TypeError("invalid-chart-alert-state");
  const folder = path.dirname(filePath);
  const tempPath = `${filePath}.${process.pid}.${randomUUID()}.tmp`;
  await mkdir(folder, { recursive: true });
  const handle = await open(tempPath, "wx", 0o600);
  try {
    await handle.writeFile(contents, "utf8");
    await handle.sync();
  } catch (error) {
    await handle.close();
    await unlink(tempPath).catch(() => undefined);
    throw error;
  }
  await handle.close();
  try { await rename(tempPath, filePath); }
  catch (error) { await unlink(tempPath).catch(() => undefined); throw error; }
}

export async function writeChartAlertEvent(event: ChartAlertEvent, folder = chartAlertSpoolPath()): Promise<boolean> {
  const validated = validateEvent(event);
  await mkdir(folder, { recursive: true });
  const filename = `${validated.event_id}.json`;
  const finalPath = path.join(folder, filename);
  try { await stat(finalPath); return false; }
  catch (error) { if (record(error).code !== "ENOENT") throw error; }
  const files = await readdir(folder);
  if (files.filter((file) => /^[a-f0-9]{64}\.json$/.test(file)).length >= MAX_SPOOL_FILES) throw new TypeError("chart-alert-spool-full");
  const contents = JSON.stringify(validated);
  if (Buffer.byteLength(contents, "utf8") > MAX_EVENT_BYTES) throw new TypeError("chart-alert-event-too-large");
  const tempPath = `${finalPath}.${process.pid}.${randomUUID()}.tmp`;
  const handle = await open(tempPath, "wx", 0o600);
  try { await handle.writeFile(contents, "utf8"); await handle.sync(); }
  catch (error) { await handle.close(); await unlink(tempPath).catch(() => undefined); throw error; }
  await handle.close();
  try { await rename(tempPath, finalPath); return true; }
  catch (error) { await unlink(tempPath).catch(() => undefined); throw error; }
}

export async function acquireChartAlertLock(filePath: string): Promise<(() => Promise<void>) | null> {
  await mkdir(path.dirname(filePath), { recursive: true });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const token = randomUUID();
    const contents = JSON.stringify({ pid: process.pid, token, started_at: new Date().toISOString() });
    try {
      const handle = await open(filePath, "wx", 0o600);
      try { await handle.writeFile(contents, "utf8"); await handle.sync(); }
      catch (error) { await handle.close(); await unlink(filePath).catch(() => undefined); throw error; }
      await handle.close();
      return async () => {
        try {
          const owner = JSON.parse(await readFile(filePath, "utf8")) as Record<string, unknown>;
          if (owner.token === token && owner.pid === process.pid) await unlink(filePath);
        } catch { /* A replacement owner or already-removed lease must remain untouched. */ }
      };
    } catch (error) {
      if (record(error).code !== "EEXIST") throw error;
      const stale = await staleLock(filePath);
      if (!stale || attempt > 0) return null;
      await unlink(filePath).catch(() => undefined);
    }
  }
  return null;
}

function localStateRoot(): string {
  return process.env.LOCALAPPDATA || process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state");
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function validTime(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && value.length <= 40 && Number.isFinite(Date.parse(value)));
}

function validateWatch(value: unknown): ChartAlertWatch {
  const item = record(value);
  const keys = ["watch_id", "report_business_date", "stock_code", "stock_name", "report_count", "added_at", "initialized", "last_polled_at", "last_bar_time", "failure_count", "known_event_ids"];
  if (Object.keys(item).length !== keys.length || keys.some((key) => !Object.hasOwn(item, key)) ||
    typeof item.report_business_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(item.report_business_date) ||
    typeof item.stock_code !== "string" || !/^\d{6}$/.test(item.stock_code) ||
    item.watch_id !== `${item.report_business_date}-${item.stock_code}` ||
    typeof item.stock_name !== "string" || !item.stock_name.trim() || item.stock_name.length > 120 || /[\u0000-\u001f\u007f]/.test(item.stock_name) ||
    !Number.isInteger(item.report_count) || Number(item.report_count) < 2 || Number(item.report_count) > 1000 ||
    !validTime(item.added_at) || typeof item.initialized !== "boolean" || !validTime(item.last_polled_at) || !validTime(item.last_bar_time) ||
    !Number.isInteger(item.failure_count) || Number(item.failure_count) < 0 || Number(item.failure_count) > 8 ||
    !Array.isArray(item.known_event_ids) || item.known_event_ids.length > 1000 || item.known_event_ids.some((id) => typeof id !== "string" || !/^[a-f0-9]{64}$/.test(id))) {
    throw new TypeError("invalid-chart-alert-state");
  }
  return item as ChartAlertWatch;
}

function validateEvent(value: unknown): ChartAlertEvent {
  const event = record(value);
  const keys = ["schema_version", "event_id", "watch_id", "report_business_date", "stock_code", "stock_name", "report_count", "report_reason", "rule_key", "rule_version", "timeframe", "kind", "direction", "observed_state", "basis_start_time", "basis_bar_time", "source", "source_fetched_at", "finality", "observed_at"];
  if (Object.keys(event).length !== keys.length || keys.some((key) => !Object.hasOwn(event, key)) || event.schema_version !== 1 ||
    typeof event.event_id !== "string" || !/^[a-f0-9]{64}$/.test(event.event_id) || typeof event.watch_id !== "string" ||
    typeof event.report_business_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(event.report_business_date) ||
    typeof event.stock_code !== "string" || !/^\d{6}$/.test(event.stock_code) ||
    event.watch_id !== `${event.report_business_date}-${event.stock_code}` ||
    typeof event.stock_name !== "string" || !event.stock_name.trim() || event.stock_name.length > 120 || /[\u0000-\u001f\u007f]/.test(event.stock_name) ||
    !Number.isInteger(event.report_count) || Number(event.report_count) < 2 || Number(event.report_count) > 1000 || event.report_reason !== "리포트 집중" ||
    typeof event.rule_key !== "string" || !RULE_VERSIONS.has(event.rule_version as string) || event.rule_key !== event.rule_version ||
    event.timeframe !== "1m" || !PATTERN_KINDS.has(event.kind as string) || !DIRECTIONS.has(event.direction as string) ||
    !PATTERN_STATUSES.has(event.observed_state as string) || !validTime(event.basis_start_time) || !event.basis_start_time ||
    !validTime(event.basis_bar_time) || !event.basis_bar_time || !SOURCES.has(event.source as string) || event.finality !== "unknown" ||
    !validTime(event.source_fetched_at) || !event.source_fetched_at || !validTime(event.observed_at) || !event.observed_at) {
    throw new TypeError("invalid-chart-alert-event");
  }
  return event as ChartAlertEvent;
}

function validateState(input: unknown): ChartAlertState {
  const state = record(input);
  const keys = ["schemaVersion", "running", "startedAt", "lastPollAt", "lastError", "watches", "events"];
  if (Object.keys(state).length !== keys.length || keys.some((key) => !Object.hasOwn(state, key)) || state.schemaVersion !== 1 ||
    typeof state.running !== "boolean" || !validTime(state.startedAt) || !validTime(state.lastPollAt) ||
    (state.lastError !== null && (typeof state.lastError !== "string" || state.lastError.length > 200)) ||
    !Array.isArray(state.watches) || state.watches.length > 3 || !Array.isArray(state.events) || state.events.length > MAX_EVENTS) {
    throw new TypeError("invalid-chart-alert-state");
  }
  const watches = state.watches.map(validateWatch);
  if (new Set(watches.map((watch) => watch.watch_id)).size !== watches.length || state.events.some((event) => {
    try { validateEvent(event); return false; } catch { return true; }
  })) throw new TypeError("invalid-chart-alert-state");
  return { schemaVersion: 1, running: state.running, startedAt: state.startedAt, lastPollAt: state.lastPollAt,
    lastError: state.lastError, watches, events: state.events as ChartAlertEvent[] };
}

async function staleLock(filePath: string): Promise<boolean> {
  try {
    const owner = record(JSON.parse(await readFile(filePath, "utf8")));
    if (!Number.isInteger(owner.pid) || Number(owner.pid) <= 0 || typeof owner.token !== "string") return false;
    try { process.kill(Number(owner.pid), 0); return false; }
    catch (error) { return record(error).code === "ESRCH"; }
  } catch { return false; }
}
