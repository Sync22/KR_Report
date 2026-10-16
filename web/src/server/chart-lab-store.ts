import { mkdir, open, readFile, rename, stat, unlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { isChartExplorerSymbol } from "../domain/chart-explorer.ts";

const MAX_STATE_BYTES = 2 * 1024 * 1024;
const MAX_EVENTS = 500;

export type ChartLabMonitorState = {
  schemaVersion: 1;
  running: boolean;
  startedAt: string | null;
  lastPollAt: string | null;
  lastError: string | null;
  symbols: Array<{ symbol: string; name: string; focus: boolean; lastPolledAt: string | null; failureCount: number }>;
  events: Array<Record<string, unknown>>;
};

export function emptyChartLabState(): ChartLabMonitorState {
  return { schemaVersion: 1, running: false, startedAt: null, lastPollAt: null, lastError: null, symbols: [], events: [] };
}

export function chartLabStatePath(): string {
  const root = process.env.LOCALAPPDATA || process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state");
  return path.join(root, "StockMonitor", "ChartLab", "monitor-state.json");
}

export async function readChartLabState(filePath = chartLabStatePath()): Promise<ChartLabMonitorState> {
  try {
    const info = await stat(filePath);
    if (info.size > MAX_STATE_BYTES) throw new TypeError("invalid-chart-lab-state");
    return validateState(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if (record(error).code === "ENOENT") return emptyChartLabState();
    throw new TypeError("invalid-chart-lab-state");
  }
}

export async function writeChartLabState(state: ChartLabMonitorState, filePath = chartLabStatePath()): Promise<void> {
  const validated = validateState(state);
  const contents = JSON.stringify(validated);
  if (Buffer.byteLength(contents, "utf8") > MAX_STATE_BYTES) throw new TypeError("invalid-chart-lab-state");
  const folder = path.dirname(filePath);
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
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
  try {
    await rename(tempPath, filePath);
  } catch (error) {
    await unlink(tempPath).catch(() => undefined);
    throw error;
  }
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function validTime(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && Number.isFinite(Date.parse(value)) && value.length <= 40);
}

function isJson(value: unknown, depth = 0): boolean {
  if (depth > 12) return false;
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.length <= 20_000 && value.every((item) => isJson(item, depth + 1));
  if (value && typeof value === "object") return Object.values(value).length <= 200 && Object.values(value).every((item) => isJson(item, depth + 1));
  return false;
}

function validateState(input: unknown): ChartLabMonitorState {
  const value = record(input);
  const keys = ["schemaVersion", "running", "startedAt", "lastPollAt", "lastError", "symbols", "events"];
  if (Object.keys(value).length !== keys.length || keys.some((key) => !Object.hasOwn(value, key)) || value.schemaVersion !== 1 ||
    typeof value.running !== "boolean" || !validTime(value.startedAt) || !validTime(value.lastPollAt) ||
    (value.lastError !== null && (typeof value.lastError !== "string" || value.lastError.length > 200)) ||
    !Array.isArray(value.symbols) || value.symbols.length > 20 || !Array.isArray(value.events) || value.events.length > MAX_EVENTS) {
    throw new TypeError("invalid-chart-lab-state");
  }
  const seen = new Set<string>();
  let focusCount = 0;
  const symbols = value.symbols.map((raw) => {
    const item = record(raw);
    if (Object.keys(item).length !== 5 || typeof item.symbol !== "string" || !isChartExplorerSymbol(item.symbol) ||
      typeof item.name !== "string" || !item.name.trim() || item.name.length > 120 || /[\u0000-\u001f\u007f]/.test(item.name) ||
      typeof item.focus !== "boolean" || !validTime(item.lastPolledAt) || typeof item.failureCount !== "number" ||
      !Number.isInteger(item.failureCount) || item.failureCount < 0 || item.failureCount > 8 || seen.has(item.symbol)) throw new TypeError("invalid-chart-lab-state");
    seen.add(item.symbol);
    if (item.focus && ++focusCount > 3) throw new TypeError("invalid-chart-lab-state");
    return { symbol: item.symbol, name: item.name.trim(), focus: item.focus, lastPolledAt: item.lastPolledAt, failureCount: item.failureCount };
  });
  if (value.events.some((event) => !isPlainRecord(event) || !isJson(event))) throw new TypeError("invalid-chart-lab-state");
  return {
    schemaVersion: 1,
    running: value.running,
    startedAt: value.startedAt,
    lastPollAt: value.lastPollAt,
    lastError: value.lastError,
    symbols,
    events: JSON.parse(JSON.stringify(value.events)) as Array<Record<string, unknown>>,
  };
}
