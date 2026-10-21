import "server-only";

import { isBusinessDate } from "../domain/daily.ts";
import {
  aggregateDailyBars,
  aggregateHourlyBarsToFourHours,
  isChartExplorerSymbol,
  isChartExplorerTimeframe,
  type ChartExplorerBar,
  type ChartExplorerSession,
  type ChartExplorerResponse,
  type ChartExplorerSuccess,
  type ChartExplorerTimeframe,
} from "../domain/chart-explorer.ts";
import { buildChartExplorerProjection } from "./web-view-indicators.ts";
import { getStockSearchSnapshot } from "./stock-search.ts";
import { TossOpenApiClient, TossOpenApiError, readTossOpenApiConfig, type TossKrxMarketDay } from "./toss-openapi.ts";

const YAHOO_CHART_BASE_URL = "https://query1.finance.yahoo.com";
const YAHOO_TIMEOUT_MS = 12_000;
const YAHOO_MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
const MAX_DAILY_PAGES = 4;
const PAGE_SIZE = 200;
const CACHE_TTL_MS = 30_000;
const CACHE_MAX_ENTRIES = 64;
const UPSTREAM_WINDOW_MS = 60_000;
const UPSTREAM_REQUESTS_PER_WINDOW = 12;
const KRX_CALENDAR_CACHE_MS = 24 * 60 * 60 * 1000;
const KRX_CALENDAR_MIN_INTERVAL_MS = 1000;
const MAX_KRX_CALENDAR_LOOKUPS = 32;
const H4_CONTINUITY_CONTEXT_BARS = 140;

type ValueRecord = Record<string, unknown>;
type SessionContinuityStatus = "verified" | "unsupported" | "calendar-not-configured" | "calendar-rate-limited" |
  "calendar-request-limit" | "calendar-date-unavailable" | "calendar-session-mismatch" |
  "calendar-response-shape" | "calendar-day-shape" | "calendar-session-shape" | "calendar-interval-shape" |
  "calendar-start-time-format" | "calendar-end-time-format" | "calendar-interval-order" |
  "calendar-duplicate-days" | "calendar-invalid-order" | "calendar-invalid-data" | "calendar-unavailable" | `calendar-http-${number}`;
type ServiceResult = {
  status: number;
  payload: ChartExplorerResponse;
  calculationBars?: ChartExplorerBar[];
  sessionContinuityStatus?: SessionContinuityStatus;
  marketMappingSource?: "stored-toss-stock-universe" | "toss-stock-master";
};

class UpstreamRateLimitError extends Error {}
type YahooResult = { bars: ChartExplorerBar[]; displayName: string; sourceDate: string | null; currency: string | null; timezone: string };

function isRecord(value: unknown): value is ValueRecord {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function unavailable(input: {
  date?: string | null;
  symbol?: string | null;
  displayName?: string;
  instrumentType?: "stock" | "crypto" | null;
  timeframe?: ChartExplorerTimeframe | null;
  reason: string;
  source?: string | null;
  fetchedAt?: string | null;
  sourceDate?: string | null;
  adjusted?: boolean | null;
  currency?: string | null;
  liveFetch?: boolean;
}): ChartExplorerResponse {
  return {
    surface: "web-view-chart-explorer",
    read_only: true,
    writes_stock_monitor_db: false,
    live_fetch: input.liveFetch ?? false,
    requested_as_of: input.date ?? null,
    symbol: input.symbol ?? null,
    display_name: input.displayName ?? input.symbol ?? "종목",
    instrument_type: input.instrumentType ?? null,
    timeframe: input.timeframe ?? null,
    available: false,
    source: input.source ?? null,
    source_fetched_at: input.fetchedAt ?? null,
    source_date: input.sourceDate ?? null,
    bar_status: input.fetchedAt ? "unknown" : null,
    adjusted: input.adjusted ?? null,
    currency: input.currency ?? null,
    reason: input.reason,
  };
}

export function invalidChartExplorerRequest(date: string | null, symbol: string | null, timeframe: ChartExplorerTimeframe | null): ChartExplorerResponse {
  return unavailable({
    date: date && isBusinessDate(date) ? date : null,
    symbol: symbol && isChartExplorerSymbol(symbol) ? symbol : null,
    displayName: symbol && isChartExplorerSymbol(symbol) ? symbol : "종목",
    instrumentType: symbol && isChartExplorerSymbol(symbol) ? instrumentType(symbol) : null,
    timeframe: timeframe && isChartExplorerTimeframe(timeframe) ? timeframe : null,
    reason: "invalid_query",
  });
}

function instrumentType(symbol: string): "stock" | "crypto" {
  return /^\d{6}$/.test(symbol) || !/-(?:USD|USDT|USDC|BTC|ETH|EUR|GBP|JPY|AUD|CAD)$/i.test(symbol) ? "stock" : "crypto";
}

function normalizeName(value: unknown, fallback: string): string {
  if (typeof value !== "string") return fallback;
  const name = value.replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, 120);
  return name || fallback;
}

function numeric(value: unknown): number | null {
  if (typeof value !== "number" && typeof value !== "string") return null;
  if (typeof value === "string" && !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim())) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function offsetSeconds(value: string): number | null {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return null;
  const [, wallTime, , offset] = match;
  const millis = Date.parse(`${wallTime}${offset}`);
  const wallClock = Date.parse(`${wallTime}Z`);
  if (!Number.isFinite(millis) || !Number.isFinite(wallClock) || new Date(wallClock).toISOString().slice(0, 19) !== wallTime) return null;
  return Math.floor(millis / 1000);
}

function zonedParts(value: Date, timezone: string): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function isoOffset(offset: number): string {
  const sign = offset >= 0 ? "+" : "-";
  const minutes = Math.floor(Math.abs(offset) / 60);
  return `${sign}${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function calendarDate(value: Date, timezone: string): string {
  const parts = zonedParts(value, timezone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function addCalendarDay(date: string): string {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + 1);
  return value.toISOString().slice(0, 10);
}

function isWeekday(date: string): boolean {
  const weekday = new Date(`${date}T00:00:00Z`).getUTCDay();
  return weekday > 0 && weekday < 6;
}

function defaultKrxSession(date: string): ChartExplorerSession {
  return { date, open: `${date}T09:00:00+09:00`, close: `${date}T15:30:00+09:00` };
}

function hasRegularKrxHourlyBars(bars: readonly ChartExplorerBar[], date: string): boolean {
  if (bars.length !== 6) return false;
  const expected = new Set(Array.from({ length: 6 }, (_, index) =>
    new Date(`${date}T${String(9 + index).padStart(2, "0")}:00:00+09:00`).toISOString()));
  return bars.every((bar) => expected.has(bar.time)) && new Set(bars.map((bar) => bar.time)).size === 6;
}

function regularSession(day: TossKrxMarketDay): ChartExplorerSession | null {
  const market = day.regularMarket;
  return market ? { date: day.date, open: market.startTime, close: market.endTime } : null;
}

function businessDateEnd(date: string, timezone: string): string {
  const [year, month, day] = date.split("-").map(Number);
  const wallClock = Date.UTC(year, month - 1, day, 23, 59, 59);
  let instant = wallClock;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = zonedParts(new Date(instant), timezone);
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second));
    instant = wallClock - (represented - instant);
  }
  const parts = zonedParts(new Date(instant), timezone);
  const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute), Number(parts.second));
  return `${date}T23:59:59${isoOffset(Math.round((represented - instant) / 1000))}`;
}

function localDate(timestampSeconds: number, timezone: string): string {
  const parts = zonedParts(new Date(timestampSeconds * 1000), timezone);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function sourceDate(bars: ReadonlyArray<ChartExplorerBar>): string | null {
  return bars.reduce<string | null>((latest, bar) => {
    const day = bar.time.slice(0, 10);
    return !latest || day > latest ? day : latest;
  }, null);
}

function dateWindow(date: string, days: number): { period1: number; period2: number } {
  const start = Date.parse(`${date}T00:00:00Z`);
  const dayMs = 24 * 60 * 60 * 1000;
  return {
    period1: Math.floor((start - days * dayMs) / 1000),
    period2: Math.floor((start + 3 * dayMs) / 1000),
  };
}

async function readBoundedJson(response: Response): Promise<ValueRecord> {
  const reader = response.body?.getReader();
  if (!reader) throw new TypeError("provider-response-empty");
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > YAHOO_MAX_RESPONSE_BYTES) {
        await reader.cancel().catch(() => undefined);
        throw new TypeError("provider-response-too-large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const payload: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  if (!isRecord(payload) || Object.keys(payload).length !== 1 || !Object.hasOwn(payload, "chart")) throw new TypeError("provider-response-shape");
  return payload;
}

async function fetchYahooChart(symbol: string, date: string, interval: "1d" | "1h"): Promise<YahooResult> {
  const window = dateWindow(date, interval === "1h" ? 365 : 5 * 365);
  const url = new URL(`/v8/finance/chart/${encodeURIComponent(symbol)}`, YAHOO_CHART_BASE_URL);
  for (const [key, value] of Object.entries({
    period1: String(window.period1), period2: String(window.period2), interval,
    includePrePost: "false", includeAdjustedClose: "false",
  })) url.searchParams.set(key, value);

  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(YAHOO_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof Error && error.name === "TimeoutError") throw new Error("provider_timeout");
    throw new Error("provider_unavailable");
  }
  if (!response.ok) {
    await response.body?.cancel().catch(() => undefined);
    throw new Error("provider_http_error");
  }

  const payload = await readBoundedJson(response);
  const chart = payload.chart;
  if (!isRecord(chart) || Object.keys(chart).some((key) => !["result", "error"].includes(key)) || !Object.hasOwn(chart, "result") || !Object.hasOwn(chart, "error")) {
    throw new TypeError("provider-response-shape");
  }
  if (chart.error !== null || !Array.isArray(chart.result) || chart.result.length !== 1) throw new Error("provider_unavailable");
  const result = chart.result[0];
  if (!isRecord(result) || Object.keys(result).some((key) => !["meta", "timestamp", "indicators"].includes(key)) ||
    !["meta", "timestamp", "indicators"].every((key) => Object.hasOwn(result, key)) || !isRecord(result.meta) || !isRecord(result.indicators)) {
    throw new TypeError("provider-response-shape");
  }
  const meta = result.meta;
  if (meta.symbol !== symbol || typeof meta.exchangeTimezoneName !== "string" || !Array.isArray(result.timestamp) ||
    result.timestamp.length > (interval === "1h" ? 9000 : 1500) || result.timestamp.some((stamp) => !Number.isInteger(stamp) || (stamp as number) < 0)) {
    throw new TypeError("provider-response-meta");
  }
  if (meta.currency !== undefined && meta.currency !== null && (typeof meta.currency !== "string" || !/^[A-Z]{3}$/.test(meta.currency))) {
    throw new TypeError("provider-response-currency");
  }
  if (meta.instrumentType !== undefined && meta.instrumentType !== null && typeof meta.instrumentType !== "string") throw new TypeError("provider-response-instrument");
  if (meta.instrumentType === "CRYPTOCURRENCY") throw new Error("unsupported_instrument_type");
  const timezone = meta.exchangeTimezoneName;
  try { new Intl.DateTimeFormat("en-US", { timeZone: timezone }).format(0); } catch { throw new TypeError("provider-response-timezone"); }
  if (Object.keys(result.indicators).some((key) => !["quote", "adjclose"].includes(key)) ||
    !Array.isArray(result.indicators.quote) || result.indicators.quote.length !== 1 || !isRecord(result.indicators.quote[0])) {
    throw new TypeError("provider-response-indicators");
  }
  const quote = result.indicators.quote[0];
  const quoteKeys = ["open", "high", "low", "close", "volume"];
  if (Object.keys(quote).some((key) => !quoteKeys.includes(key)) || !quoteKeys.every((key) => Array.isArray(quote[key]))) {
    throw new TypeError("provider-response-quote");
  }
  const timestamps = result.timestamp as number[];
  if (quoteKeys.some((key) => (quote[key] as unknown[]).length !== timestamps.length) ||
    (result.indicators.adjclose !== undefined && (!Array.isArray(result.indicators.adjclose) || result.indicators.adjclose.length !== 1 ||
      !isRecord(result.indicators.adjclose[0]) || !Array.isArray(result.indicators.adjclose[0].adjclose) || result.indicators.adjclose[0].adjclose.length !== timestamps.length))) {
    throw new TypeError("provider-response-series-length");
  }

  const bars: ChartExplorerBar[] = [];
  let latestSourceDate: string | null = null;
  for (let index = 0; index < timestamps.length; index += 1) {
    const timestamp = timestamps[index];
    const day = localDate(timestamp, timezone);
    if (day > date) continue;
    const values = Object.fromEntries(quoteKeys.map((key) => [key, (quote[key] as unknown[])[index]]));
    if (Object.values(values).every((value) => value === null)) continue;
    const open = numeric(values.open), high = numeric(values.high), low = numeric(values.low), close = numeric(values.close), volume = numeric(values.volume);
    if ([open, high, low, close, volume].some((value) => value === null)) throw new TypeError("provider-response-invalid-bar");
    const bar = { time: interval === "1h" ? new Date(timestamp * 1000).toISOString() : day, open: open!, high: high!, low: low!, close: close!, volume: volume! };
    if (bar.open <= 0 || bar.high <= 0 || bar.low <= 0 || bar.close <= 0 || bar.volume < 0 ||
      bar.high < Math.max(bar.open, bar.low, bar.close) || bar.low > Math.min(bar.open, bar.high, bar.close)) throw new TypeError("provider-response-invalid-bar");
    bars.push(bar);
    if (!latestSourceDate || day > latestSourceDate) latestSourceDate = day;
  }
  if (!bars.length) throw new Error("no_chart_data");
  const unique = new Set(bars.map((bar) => bar.time));
  if (unique.size !== bars.length) throw new TypeError("provider-response-duplicate-bar");
  const normalized = bars.sort((left, right) => left.time.localeCompare(right.time)).slice(-9000);
  return {
    bars: normalized,
    displayName: normalizeName(meta.shortName ?? meta.longName, symbol),
    sourceDate: latestSourceDate,
    currency: typeof meta.currency === "string" ? meta.currency : null,
    timezone,
  };
}

function reasonForToss(error: unknown): string {
  if (error instanceof TossOpenApiError) {
    if (error.providerReason) return error.providerReason;
    return error.statusCode !== undefined ? "provider_http_error" : "provider_unavailable";
  }
  return error instanceof TypeError || error instanceof RangeError ? "invalid_provider_response" : "provider_unavailable";
}

function continuityFailure(error: unknown): SessionContinuityStatus {
  if (error instanceof TossOpenApiError) {
    if (error.statusCode === 429) return "calendar-rate-limited";
    if (error.statusCode !== undefined) return `calendar-http-${error.statusCode}`;
    const invalidShapes: Record<string, SessionContinuityStatus> = {
      "Toss KRX calendar response had an unexpected shape.": "calendar-response-shape",
      "Toss KRX calendar day had an unexpected shape.": "calendar-day-shape",
      "Toss KRX session response had an unexpected shape.": "calendar-session-shape",
      "Toss KRX session interval shape was invalid.": "calendar-interval-shape",
      "Toss KRX session start time format was invalid.": "calendar-start-time-format",
      "Toss KRX session end time format was invalid.": "calendar-end-time-format",
      "Toss KRX session interval order was invalid.": "calendar-interval-order",
      "Toss KRX calendar included duplicate dates.": "calendar-duplicate-days",
      "Toss KRX calendar order was invalid.": "calendar-invalid-order",
    };
    if (error.providerReason === "invalid_provider_response") return invalidShapes[error.message] ?? "calendar-invalid-data";
    return "calendar-unavailable";
  }
  if (error instanceof TypeError) {
    if (error.message === "toss-not-configured" || error.message === "krx-calendar-unavailable") return "calendar-not-configured";
    if (error.message === "krx-calendar-request-limit") return "calendar-request-limit";
    if (error.message === "krx-calendar-date-unavailable") return "calendar-date-unavailable";
    if (error.message === "krx-calendar-bar-date-mismatch") return "calendar-session-mismatch";
    if (error.message.startsWith("krx-calendar-")) return "calendar-invalid-data";
  }
  return "calendar-unavailable";
}

function reasonForYahoo(error: unknown): string {
  if (error instanceof Error && ["provider_timeout", "provider_http_error", "provider_unavailable", "no_chart_data", "unsupported_instrument_type"].includes(error.message)) return error.message;
  return error instanceof TypeError || error instanceof SyntaxError ? "invalid_provider_response" : "provider_unavailable";
}

export class ChartExplorerService {
  private readonly toss = new TossOpenApiClient();
  private readonly timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  private readonly cache = new Map<string, { expiresAt: number; result: ServiceResult }>();
  private readonly inFlight = new Map<string, Promise<ServiceResult>>();
  private readonly krxCalendarCache = new Map<string, { expiresAt: number; day: TossKrxMarketDay }>();
  private readonly krxCalendarBundleCache = new Map<string, { expiresAt: number; days: TossKrxMarketDay[] }>();
  private readonly krxCalendarInFlight = new Map<string, Promise<TossKrxMarketDay[]>>();
  private readonly currentKrxMarketCache = new Map<string, { expiresAt: number; market: "KOSPI" | "KOSDAQ" }>();
  private upstreamRequestTimes: number[] = [];
  private lastKrxCalendarRequestAt = 0;

  private takeUpstreamSlot(): boolean {
    const now = Date.now();
    this.upstreamRequestTimes = this.upstreamRequestTimes.filter((startedAt) => startedAt > now - UPSTREAM_WINDOW_MS);
    if (this.upstreamRequestTimes.length >= UPSTREAM_REQUESTS_PER_WINDOW) return false;
    this.upstreamRequestTimes.push(now);
    return true;
  }

  async getChart(
    date: string, symbol: string, timeframe: ChartExplorerTimeframe, options: { sessionContinuity?: boolean } = {},
  ): Promise<ServiceResult> {
    if (!isBusinessDate(date) || !isChartExplorerSymbol(symbol) || !isChartExplorerTimeframe(timeframe)) {
      return { status: 400, payload: unavailable({ date: isBusinessDate(date) ? date : null, symbol: isChartExplorerSymbol(symbol) ? symbol : null, timeframe, reason: "invalid_query" }) };
    }
    const type = instrumentType(symbol);
    const sessionContinuity = options.sessionContinuity === true && timeframe === "4h";
    const key = `${date}:${symbol}:${timeframe}:${sessionContinuity ? "session-aware" : "default"}`;
    const cached = this.cache.get(key);
    if (cached && cached.expiresAt > Date.now()) return { ...cached.result, payload: { ...cached.result.payload, live_fetch: false } };
    if (cached) this.cache.delete(key);
    const pending = this.inFlight.get(key);
    if (pending) return pending;
    const request = this.buildChart(date, symbol, timeframe, type, sessionContinuity).then((result) => {
      this.cache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, result });
      while (this.cache.size > CACHE_MAX_ENTRIES) this.cache.delete(this.cache.keys().next().value as string);
      return result;
    }).finally(() => this.inFlight.delete(key));
    this.inFlight.set(key, request);
    return request;
  }

  private async buildChart(
    date: string, symbol: string, timeframe: ChartExplorerTimeframe, type: "stock" | "crypto", sessionContinuity: boolean,
  ): Promise<ServiceResult> {
    let displayName = symbol;
    let providerSymbol = symbol;
    let market: "KOSPI" | "KOSDAQ" | null = null;
    let marketMappingSource: ServiceResult["marketMappingSource"];
    if (type === "crypto") return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "unsupported_instrument_type" }) };
    if (/^\d{6}$/.test(symbol)) {
      let item;
      try {
        const snapshot = getStockSearchSnapshot(date, symbol, 1);
        item = snapshot.items.find((candidate) => candidate.stock_code === symbol);
      } catch {
        return { status: 503, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "stored_lookup_unavailable" }) };
      }
      if (!item) return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "symbol_not_found" }) };
      displayName = normalizeName(item.stock_name, symbol);
      if (item.market_source === "stored_toss_stock_universe" && (item.market === "KOSPI" || item.market === "KOSDAQ")) {
        market = item.market;
        marketMappingSource = "stored-toss-stock-universe";
      }
      if (timeframe === "4h") {
        if (market === null && sessionContinuity && this.toss.configured) {
          if (!this.takeUpstreamSlot()) return { status: 429, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "rate_limited" }) };
          try {
            market = await this.getCurrentKrxMarket(symbol);
            if (market) marketMappingSource = "toss-stock-master";
          } catch {
            return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "symbol_mapping_unavailable" }) };
          }
        }
        if (market === null) return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "symbol_mapping_unavailable" }) };
        providerSymbol = `${symbol}.${market === "KOSPI" ? "KS" : "KQ"}`;
      }
    }

    let dailyBars: ChartExplorerBar[] = [];
    let source: string;
    let adjusted: boolean;
    let fetchedAt: string | null = null;
    let latestSourceDate: string | null = null;
    let currency: string | null = null;
    let sourceTimezone = this.timezone;
    let hourlyBars: ChartExplorerBar[] | null = null;

    if (timeframe === "4h") {
      source = `Yahoo Finance chart · ${providerSymbol} · 1h bars`;
      adjusted = false;
      if (!this.takeUpstreamSlot()) return { status: 429, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "rate_limited", source, adjusted }) };
      try {
        const yahoo = await fetchYahooChart(providerSymbol.toUpperCase(), date, "1h");
        fetchedAt = new Date().toISOString();
        displayName = /^\d{6}$/.test(symbol) ? displayName : yahoo.displayName;
        latestSourceDate = yahoo.sourceDate;
        currency = yahoo.currency;
        sourceTimezone = yahoo.timezone;
        hourlyBars = yahoo.bars;
      } catch (error) {
        const reason = reasonForYahoo(error);
        return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: reason === "unsupported_instrument_type" ? "crypto" : type, timeframe, reason, source, fetchedAt, sourceDate: latestSourceDate, adjusted, currency, liveFetch: true }) };
      }
    } else if (/^\d{6}$/.test(symbol)) {
      source = "Toss OpenAPI · adjusted daily candles";
      adjusted = true;
      if (!this.toss.configured) return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "toss_not_configured", source, adjusted }) };
      try {
        const response = await this.fetchTossDailyHistory(symbol, date);
        dailyBars = response.bars;
        latestSourceDate = response.sourceDate;
        currency = response.currency;
        fetchedAt = new Date().toISOString();
      } catch (error) {
        if (error instanceof UpstreamRateLimitError) {
          return { status: 429, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "rate_limited", source, adjusted }) };
        }
        return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: reasonForToss(error), source, adjusted, currency, liveFetch: true }) };
      }
    } else {
      providerSymbol = symbol.toUpperCase();
      source = `Yahoo Finance chart · ${providerSymbol} · 1d bars`;
      adjusted = false;
      if (!this.takeUpstreamSlot()) return { status: 429, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "rate_limited", source, adjusted }) };
      try {
        const yahoo = await fetchYahooChart(providerSymbol, date, "1d");
        dailyBars = yahoo.bars.slice(-800);
        latestSourceDate = yahoo.sourceDate;
        currency = yahoo.currency;
        fetchedAt = new Date().toISOString();
        displayName = yahoo.displayName;
      } catch (error) {
        const reason = reasonForYahoo(error);
        return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: reason === "unsupported_instrument_type" ? "crypto" : type, timeframe, reason, source, adjusted, currency, liveFetch: true }) };
      }
    }

    const defaultHourlyAggregation = timeframe === "4h" ? aggregateHourlyBarsToFourHours(hourlyBars ?? [], sourceTimezone) : null;
    let aggregated = timeframe === "4h"
      ? defaultHourlyAggregation ?? []
      : aggregateDailyBars(dailyBars.slice(-800), timeframe);
    const explicitKrxTicker = /\.K[QS]$/i.test(symbol);
    let sessionContinuityStatus: ServiceResult["sessionContinuityStatus"];
    if (sessionContinuity && timeframe === "4h" && (explicitKrxTicker || (/^\d{6}$/.test(symbol) && market !== null)) && sourceTimezone === "Asia/Seoul") {
      try {
        const defaultBars = defaultHourlyAggregation ?? [];
        const startIndex = Math.max(0, defaultBars.length - H4_CONTINUITY_CONTEXT_BARS);
        const startDate = defaultBars[startIndex] ? calendarDate(new Date(defaultBars[startIndex].time), sourceTimezone) : null;
        if (!startDate) throw new TypeError("krx-calendar-unavailable");
        const continuityHourlyBars = (hourlyBars ?? []).filter((bar) => calendarDate(new Date(bar.time), sourceTimezone) >= startDate);
        const sessions = await this.getKrxSessions(continuityHourlyBars, sourceTimezone);
        const sessionBars = aggregateHourlyBarsToFourHours(continuityHourlyBars, sourceTimezone, sessions);
        const requiredBars = Math.min(120, defaultBars.length);
        if (sessionBars.length >= requiredBars && sessionBars.every((bar) => Number.isSafeInteger(bar.missingBarsBefore) && bar.missingBarsBefore! >= 0)) {
          const prefix = defaultBars.filter((bar) => calendarDate(new Date(bar.time), sourceTimezone) < startDate);
          aggregated = [...prefix, ...sessionBars];
          sessionContinuityStatus = "verified";
        } else sessionContinuityStatus = "calendar-unavailable";
      } catch (error) {
        // Keep the chart visible; missing continuity metadata makes R/H remain unsupported.
        sessionContinuityStatus = continuityFailure(error);
      }
    } else if (sessionContinuity && timeframe === "4h") sessionContinuityStatus = "unsupported";
    aggregated = aggregated.slice(-800);
    if (!aggregated.length || !fetchedAt) {
      return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "no_chart_data", source, fetchedAt, sourceDate: latestSourceDate, adjusted, currency, liveFetch: !!fetchedAt }) };
    }
    try {
      const projectedBars = aggregated.map(({ missingBarsBefore: _missingBarsBefore, ...bar }) => bar);
      const calculated = buildChartExplorerProjection({
        requestedAsOf: date,
        symbol,
        timeframe,
        candles: projectedBars,
        source,
        sourceFetchedAt: fetchedAt,
        sourceTimezone,
      });
      const chartBars = calculated.chart.bars;
      const bars = chartBars.map(({ time, open, high, low, close, volume }) => ({ time, open, high, low, close, volume }));
      const success: ChartExplorerSuccess = {
        surface: "web-view-chart-explorer",
        read_only: true,
        writes_stock_monitor_db: false,
        live_fetch: true,
        requested_as_of: date,
        symbol,
        display_name: displayName,
        instrument_type: type,
        timeframe,
        available: true,
        source,
        source_fetched_at: fetchedAt,
        source_date: latestSourceDate,
        bar_status: "unknown",
        adjusted,
        currency,
        bars,
        snapshot: calculated.snapshot,
        chart: calculated.chart,
      };
      return { status: 200, payload: success, calculationBars: aggregated,
        ...(sessionContinuityStatus ? { sessionContinuityStatus } : {}),
        ...(marketMappingSource ? { marketMappingSource } : {}) };
    } catch {
      return { status: 200, payload: unavailable({ date, symbol, displayName, instrumentType: type, timeframe, reason: "invalid_provider_response", source, fetchedAt, sourceDate: latestSourceDate, adjusted, currency, liveFetch: true }),
        ...(sessionContinuityStatus ? { sessionContinuityStatus } : {}) };
    }
  }

  private async getCurrentKrxMarket(symbol: string): Promise<"KOSPI" | "KOSDAQ" | null> {
    const cached = this.currentKrxMarketCache.get(symbol);
    if (cached && cached.expiresAt > Date.now()) return cached.market;
    const response = await this.toss.getMarketRankingStocks([symbol]);
    if (!Array.isArray(response.result)) throw new TypeError("invalid-krx-market-master");
    const item = response.result.find((value) => isRecord(value) && value.symbol === symbol);
    if (!isRecord(item) || (item.market !== "KOSPI" && item.market !== "KOSDAQ")) return null;
    const market = item.market;
    this.currentKrxMarketCache.set(symbol, { expiresAt: Date.now() + KRX_CALENDAR_CACHE_MS, market });
    return market;
  }

  private async getKrxSessions(bars: readonly ChartExplorerBar[], timezone: string): Promise<ChartExplorerSession[]> {
    if (!this.toss.configured || timezone !== "Asia/Seoul" || !bars.length) throw new TypeError("krx-calendar-unavailable");
    const grouped = new Map<string, ChartExplorerBar[]>();
    for (const bar of bars) {
      const date = calendarDate(new Date(bar.time), timezone);
      grouped.set(date, [...(grouped.get(date) ?? []), bar]);
    }
    const dates = [...grouped.keys()].sort();
    const sessions = new Map<string, ChartExplorerSession>();
    let lookups = 0;
    for (const date of dates) {
      const dayBars = grouped.get(date)!;
      if (hasRegularKrxHourlyBars(dayBars, date)) {
        sessions.set(date, defaultKrxSession(date));
        continue;
      }
      if (++lookups > MAX_KRX_CALENDAR_LOOKUPS) throw new TypeError("krx-calendar-request-limit");
      const day = await this.getKrxCalendarDay(date);
      const session = regularSession(day);
      if (!session) throw new TypeError("krx-calendar-bar-date-mismatch");
      sessions.set(date, session);
    }
    for (let index = 1; index < dates.length; index += 1) {
      let candidate = addCalendarDay(dates[index - 1]);
      while (candidate < dates[index]) {
        if (isWeekday(candidate)) {
          if (++lookups > MAX_KRX_CALENDAR_LOOKUPS) throw new TypeError("krx-calendar-request-limit");
          const days = await this.getKrxCalendarDays(candidate);
          for (const day of days) {
            if (day.date > dates[index - 1] && day.date < dates[index]) {
              const session = regularSession(day);
              if (session && !grouped.has(day.date)) sessions.set(day.date, session);
            }
          }
          const nextSession = days.find((day) => day.date > candidate && day.regularMarket !== null);
          if (!nextSession || nextSession.date >= dates[index]) break;
          candidate = nextSession.date;
          continue;
        }
        candidate = addCalendarDay(candidate);
      }
    }
    return [...sessions.values()].sort((a, b) => a.open.localeCompare(b.open));
  }

  private async getKrxCalendarDay(date: string): Promise<TossKrxMarketDay> {
    const cached = this.krxCalendarCache.get(date);
    if (cached && cached.expiresAt > Date.now()) return cached.day;
    const days = await this.getKrxCalendarDays(date);
    const day = days.find((item) => item.date === date);
    if (!day) throw new TypeError("krx-calendar-date-unavailable");
    return day;
  }

  private async getKrxCalendarDays(date: string): Promise<TossKrxMarketDay[]> {
    const cached = this.krxCalendarBundleCache.get(date);
    if (cached && cached.expiresAt > Date.now()) return cached.days;
    const pending = this.krxCalendarInFlight.get(date);
    if (pending) return pending;
    if (!this.toss.configured) throw new TypeError("toss-not-configured");
    if (!this.takeUpstreamSlot()) throw new TypeError("krx-calendar-request-limit");
    const request = (async () => {
      const delay = KRX_CALENDAR_MIN_INTERVAL_MS - (Date.now() - this.lastKrxCalendarRequestAt);
      if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
      this.lastKrxCalendarRequestAt = Date.now();
      const response = await this.toss.getKrxMarketCalendar(date);
      return response.result;
    })();
    this.krxCalendarInFlight.set(date, request);
    try {
      const days = await request;
      const expiresAt = Date.now() + KRX_CALENDAR_CACHE_MS;
      this.krxCalendarBundleCache.set(date, { expiresAt, days });
      for (const day of days) this.krxCalendarCache.set(day.date, { expiresAt, day });
      while (this.krxCalendarCache.size > 512) this.krxCalendarCache.delete(this.krxCalendarCache.keys().next().value as string);
      return days;
    } finally {
      this.krxCalendarInFlight.delete(date);
    }
  }

  private async fetchTossDailyHistory(symbol: string, date: string): Promise<{ bars: ChartExplorerBar[]; sourceDate: string | null; currency: string | null }> {
    const beforeStart = businessDateEnd(date, this.timezone);
    let before = beforeStart;
    let cursor = offsetSeconds(before);
    if (cursor === null) throw new TypeError("invalid_history_cursor");
    const seenCursors = new Set([before]);
    const seenCandles = new Set<string>();
    const candles: ChartExplorerBar[] = [];
    const currencies: Array<string | null> = [];
    for (let pageIndex = 0; pageIndex < MAX_DAILY_PAGES; pageIndex += 1) {
      if (!this.takeUpstreamSlot()) throw new UpstreamRateLimitError("rate_limited");
      const response = await this.toss.getPriorityDailyHistoryPage(symbol, before);
      const page = response.result;
      if (!isRecord(page) || Object.keys(page).some((key) => !["candles", "nextBefore"].includes(key)) || !Array.isArray(page.candles) || page.candles.length > PAGE_SIZE) {
        throw new TypeError("invalid_history_page");
      }
      for (const candle of page.candles) {
        if (!isRecord(candle) || Object.keys(candle).some((key) => !["timestamp", "openPrice", "highPrice", "lowPrice", "closePrice", "volume", "currency"].includes(key)) ||
          !["timestamp", "openPrice", "highPrice", "lowPrice", "closePrice", "volume", "currency"].every((key) => Object.hasOwn(candle, key)) || typeof candle.timestamp !== "string") {
          throw new TypeError("invalid_history_candle");
        }
        if (candle.currency !== null && (typeof candle.currency !== "string" || !/^[A-Z]{3}$/.test(candle.currency))) throw new TypeError("invalid_history_currency");
        const day = candle.timestamp.slice(0, 10);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || day > date || seenCandles.has(candle.timestamp)) continue;
        const open = numeric(candle.openPrice), high = numeric(candle.highPrice), low = numeric(candle.lowPrice), close = numeric(candle.closePrice), volume = numeric(candle.volume);
        if ([open, high, low, close, volume].some((value) => value === null) || open! <= 0 || high! <= 0 || low! <= 0 || close! <= 0 || volume! < 0 ||
          high! < Math.max(open!, low!, close!) || low! > Math.min(open!, high!, close!)) throw new TypeError("invalid_history_candle");
        seenCandles.add(candle.timestamp);
        candles.push({ time: day, open: open!, high: high!, low: low!, close: close!, volume: volume! });
        currencies.push(typeof candle.currency === "string" ? candle.currency : null);
      }

      if (!Object.hasOwn(page, "nextBefore")) break;
      const nextBefore = page.nextBefore;
      if (nextBefore === null) break;
      if (typeof nextBefore !== "string") throw new TypeError("invalid_history_cursor");
      const nextCursor = offsetSeconds(nextBefore);
      if (nextCursor === null || nextCursor >= cursor || seenCursors.has(nextBefore)) throw new TypeError("invalid_history_cursor");
      if (pageIndex === MAX_DAILY_PAGES - 1) break;
      seenCursors.add(nextBefore);
      before = nextBefore;
      cursor = nextCursor;
    }
    candles.sort((left, right) => left.time.localeCompare(right.time));
    if (new Set(candles.map((bar) => bar.time)).size !== candles.length) throw new TypeError("duplicate_daily_bar");
    const distinctCurrencies = new Set(currencies.filter((value): value is string => value !== null));
    return {
      bars: candles.slice(-PAGE_SIZE * MAX_DAILY_PAGES),
      sourceDate: sourceDate(candles),
      currency: distinctCurrencies.size === 1 && currencies.every((value) => value !== null) ? [...distinctCurrencies][0] : null,
    };
  }
}

export const chartExplorerService = new ChartExplorerService();
