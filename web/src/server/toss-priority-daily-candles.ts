import "server-only";

import { isBusinessDate } from "../domain/daily.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";
import {
  TossOpenApiClient,
  TossOpenApiError,
  readTossOpenApiConfig,
  type TossOpenApiConfig,
} from "./toss-openapi.ts";

type CandleCount = 30 | 90 | 180;
type CandlePayload = Record<string, unknown>;
type ServiceResult = { status: number; payload: CandlePayload };

function selectedTopTwoSymbols(date: string): string[] {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const snapshot = buildCandidateEvidenceSnapshotFromDatabase(database, date, 2);
      return [...new Set(snapshot.rows
        .filter((candidate) => candidate.selected)
        .map((candidate) => candidate.stock_code.trim())
        .filter((symbol) => /^\d{6}$/.test(symbol)))].slice(0, 2);
    } finally {
      database.exec("ROLLBACK");
    }
  });
}

function localParts(value: Date, timezone: string): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function isoOffset(offsetSeconds: number): string {
  const sign = offsetSeconds >= 0 ? "+" : "-";
  const absoluteMinutes = Math.floor(Math.abs(offsetSeconds) / 60);
  return `${sign}${String(Math.floor(absoluteMinutes / 60)).padStart(2, "0")}:${String(absoluteMinutes % 60).padStart(2, "0")}`;
}

function zonedDateTime(value: Date, timezone: string): string {
  const parts = localParts(value, timezone);
  const offset = Math.round((Date.UTC(
    Number(parts.year), Number(parts.month) - 1, Number(parts.day),
    Number(parts.hour), Number(parts.minute), Number(parts.second), value.getUTCMilliseconds(),
  ) - value.getTime()) / 1000);
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}${isoOffset(offset)}`;
}

function businessDateEnd(date: string, timezone: string): string {
  const [year, month, day] = date.split("-").map(Number);
  const wallClock = Date.UTC(year, month - 1, day, 23, 59, 59);
  let instant = wallClock;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = localParts(new Date(instant), timezone);
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
      Number(parts.hour), Number(parts.minute), Number(parts.second));
    instant = wallClock - (represented - instant);
  }
  const finalParts = localParts(new Date(instant), timezone);
  const represented = Date.UTC(Number(finalParts.year), Number(finalParts.month) - 1, Number(finalParts.day),
    Number(finalParts.hour), Number(finalParts.minute), Number(finalParts.second));
  return `${date}T23:59:59${isoOffset(Math.round((represented - instant) / 1000))}`;
}

function candleDate(value: unknown, timezone: string): string | null {
  if (typeof value !== "string" || !value) return null;
  const instant = new Date(value);
  if (!Number.isFinite(instant.getTime())) return null;
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) {
    const date = value.slice(0, 10);
    return isBusinessDate(date) ? date : null;
  }
  const parts = localParts(instant, timezone);
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  return isBusinessDate(date) ? date : null;
}

function basePayload(date: string, count: number, configured: boolean, symbols: string[]): CandlePayload {
  return {
    surface: "web-view-toss-priority-daily-candles",
    read_only: true,
    configured,
    live_fetch: false,
    writes_db: false,
    sends_telegram: false,
    registers_scheduler: false,
    affects_ordering: false,
    business_date: date,
    requested_count: count,
    adjusted: true,
    symbols,
    items: [],
    derived_from: "web_view_candidate_evidence_top_2",
  };
}

export class TossPriorityDailyCandlesService {
  private readonly client: TossOpenApiClient;
  private readonly loadSymbols: (date: string) => string[];
  private readonly now: () => Date;
  private readonly timezone: string;

  constructor(options: {
    config?: TossOpenApiConfig;
    fetchImpl?: typeof fetch;
    loadSymbols?: (date: string) => string[];
    now?: () => Date;
    timezone?: string;
  } = {}) {
    this.client = new TossOpenApiClient(options.config ?? readTossOpenApiConfig(), options.fetchImpl);
    this.loadSymbols = options.loadSymbols ?? selectedTopTwoSymbols;
    this.now = options.now ?? (() => new Date());
    this.timezone = (options.timezone ?? process.env.STOCK_MONITOR_TIMEZONE?.trim()) || "Asia/Seoul";
  }

  async getCandles(date: string, count: number): Promise<ServiceResult> {
    if (!isBusinessDate(date)) return { status: 400, payload: { reason: "invalid_date" } };
    if (![30, 90, 180].includes(count)) {
      return {
        status: 400,
        payload: {
          surface: "web-view-toss-priority-daily-candles",
          read_only: true,
          writes_db: false,
          reason: "unsupported_candle_count",
        },
      };
    }

    const symbols = [...new Set(this.loadSymbols(date).map((symbol) => symbol.trim()).filter((symbol) => /^\d{6}$/.test(symbol)))].slice(0, 2);
    const countValue = count as CandleCount;
    const base = basePayload(date, count, this.client.configured, symbols);
    if (!symbols.length) return { status: 200, payload: { ...base, reason: "no_priority_symbols" } };

    const before = businessDateEnd(date, this.timezone);
    const common = {
      surface: "web-view-toss-priority-daily-candles",
      read_only: true,
      configured: this.client.configured,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      priority_date: date,
      before,
      interval: "1d",
      count,
      adjusted: true,
      symbols,
    };
    if (!this.client.configured) {
      return {
        status: 200,
        payload: {
          ...base,
          ...common,
          items: [],
          rate_limit: {},
          cache: "disabled",
          available: false,
          reason: "not_configured",
        },
      };
    }

    const items: { symbol: string; candles: Record<string, unknown>[]; excluded_candle_count: number }[] = [];
    const rateLimit: Record<string, Record<string, string>> = {};
    let receivedCount = 0;
    let matchedCount = 0;
    let excludedCount = 0;
    try {
      for (const symbol of symbols) {
        const response = await this.client.getPriorityDailyCandles(symbol, before, countValue);
        const page = response.result as { candles: Record<string, unknown>[] };
        const visible: Record<string, unknown>[] = [];
        for (const candle of page.candles) {
          receivedCount += 1;
          const dateValue = candleDate(candle.timestamp, this.timezone);
          if (dateValue !== null && dateValue <= date) visible.push(candle);
        }
        const itemExcluded = page.candles.length - visible.length;
        matchedCount += visible.length;
        excludedCount += itemExcluded;
        items.push({ symbol, candles: visible, excluded_candle_count: itemExcluded });
        rateLimit[symbol] = response.rateLimit;
      }
    } catch (error) {
      const errorType = error instanceof TossOpenApiError
        ? error.statusCode === undefined ? "RuntimeError" : "TossOpenApiHttpError"
        : error instanceof Error ? error.name : "RuntimeError";
      const payload: CandlePayload = { ...base, reason: "upstream_unavailable", error_type: errorType };
      const status = error instanceof TossOpenApiError ? error.statusCode : undefined;
      if (typeof status === "number" && Number.isInteger(status) && status >= 100 && status <= 599) payload.upstream_status = status;
      const providerCode = error instanceof TossOpenApiError ? error.providerCode : undefined;
      if (typeof providerCode === "string" && /^[A-Za-z0-9._-]{1,100}$/.test(providerCode)) payload.provider_code = providerCode;
      return { status: 502, payload };
    }

    if (receivedCount > 0 && matchedCount === 0) {
      return { status: 409, payload: { ...base, before, items: [], reason: "no_candles_before_top2_business_date" } };
    }
    return {
      status: 200,
      payload: {
        ...base,
        ...common,
        live_fetch: true,
        items,
        rate_limit: rateLimit,
        cache: "miss",
        available: matchedCount > 0,
        fetched_at: zonedDateTime(this.now(), this.timezone),
        excluded_candle_count: excludedCount,
      },
    };
  }
}

export const tossPriorityDailyCandlesService = new TossPriorityDailyCandlesService();
