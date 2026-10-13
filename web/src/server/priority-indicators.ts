import "server-only";

import type { CandidateEvidenceRow } from "../domain/candidate-evidence.ts";
import { isBusinessDate } from "../domain/daily.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";
import {
  TossOpenApiClient,
  TossOpenApiError,
  readTossOpenApiConfig,
  type TossOpenApiConfig,
} from "./toss-openapi.ts";
import { buildPriorityIndicatorProjection } from "./web-view-indicators.ts";

type RecordValue = Record<string, unknown>;
type ServiceResult = { status: number; payload: RecordValue };
type PriorityCandidate = {
  code: string;
  name: string;
  market: "KOSPI" | "KOSDAQ" | null;
  marketSource: "selected_date_toss_market_reference" | "stored_toss_stock_universe" | null;
  marketSourceDate: string | null;
};

const PAGE_SIZE = 200;
const MAX_PAGES = 4;
const SOURCE = "Toss OpenAPI · 조정 일봉";
const CACHE_TTL_MS = 30_000;
const HISTORY_REASONS = new Set([
  "invalid_provider_response", "provider_timeout", "provider_unavailable", "provider_http_error",
]);

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function selectedCandidates(date: string): PriorityCandidate[] {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const rows = buildCandidateEvidenceSnapshotFromDatabase(database, date, 2).rows
        .filter((row) => row.selected && /^\d{6}$/.test(row.stock_code.trim()))
        .slice(0, 2);
      const universe = database.prepare(`
        SELECT market, business_date
        FROM toss_stock_universe_cache
        WHERE stock_code = ? AND business_date <= ?
        ORDER BY business_date DESC, fetched_at DESC, market ASC
        LIMIT 1
      `);
      return rows.map((row) => {
        const reference = (row as CandidateEvidenceRow & { market_reference?: RecordValue | null }).market_reference;
        const sameDayMarket = reference?.business_date === date &&
          (reference.market === "KOSPI" || reference.market === "KOSDAQ")
          ? reference.market
          : null;
        if (sameDayMarket) {
          return {
            code: row.stock_code.trim(),
            name: row.stock_name || row.stock_code,
            market: sameDayMarket,
            marketSource: "selected_date_toss_market_reference",
            marketSourceDate: date,
          };
        }
        const stored = universe.get(row.stock_code.trim(), date) as { market?: unknown; business_date?: unknown } | undefined;
        const storedMarket = stored?.market === "KOSPI" || stored?.market === "KOSDAQ" ? stored.market : null;
        return {
          code: row.stock_code.trim(),
          name: row.stock_name || row.stock_code,
          market: storedMarket,
          marketSource: storedMarket ? "stored_toss_stock_universe" : null,
          marketSourceDate: storedMarket && typeof stored?.business_date === "string" ? stored.business_date : null,
        };
      });
    } finally {
      database.exec("ROLLBACK");
    }
  });
}

function zonedParts(value: Date, timezone: string): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function isoOffset(offsetSeconds: number): string {
  const sign = offsetSeconds >= 0 ? "+" : "-";
  const minutes = Math.floor(Math.abs(offsetSeconds) / 60);
  return `${sign}${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function zonedDateTime(value: Date, timezone: string): string {
  const parts = zonedParts(value, timezone);
  const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
    Number(parts.hour), Number(parts.minute), Number(parts.second));
  const offset = Math.round((represented - value.getTime()) / 1000);
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}${isoOffset(offset)}`;
}

function businessDateEnd(date: string, timezone: string): string {
  const [year, month, day] = date.split("-").map(Number);
  const wallClock = Date.UTC(year, month - 1, day, 23, 59, 59);
  let instant = wallClock;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = zonedParts(new Date(instant), timezone);
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
      Number(parts.hour), Number(parts.minute), Number(parts.second));
    instant = wallClock - (represented - instant);
  }
  const parts = zonedParts(new Date(instant), timezone);
  const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
    Number(parts.hour), Number(parts.minute), Number(parts.second));
  return `${date}T23:59:59${isoOffset(Math.round((represented - instant) / 1000))}`;
}

function historyError(error: unknown): RecordValue {
  if (error instanceof TossOpenApiError) {
    if (error.providerReason) return { reason: error.providerReason };
    if (typeof error.statusCode === "number") {
      const providerCode = error.providerCode;
      return {
        reason: "provider_http_error",
        upstream_status: error.statusCode,
        ...(providerCode && /^[A-Za-z0-9._-]{1,100}$/.test(providerCode) ? { provider_code: providerCode } : {}),
      };
    }
    return { reason: "provider_unavailable" };
  }
  if (error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError")) {
    return { reason: "provider_timeout" };
  }
  if (error instanceof TypeError || error instanceof RangeError) return { reason: "invalid_provider_response" };
  return { reason: "provider_unavailable" };
}

function cursorDateTime(value: unknown): [number, number] | null {
  const match = typeof value === "string"
    ? /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(value)
    : null;
  if (!match) return null;
  const [wallTime, fraction, offset] = match.slice(1);
  const parsed = Date.parse(`${wallTime}${offset}`);
  const wallClock = new Date(`${wallTime}Z`);
  if (!Number.isFinite(parsed) || wallClock.toISOString().slice(0, 19) !== wallTime) return null;
  return [Math.floor(parsed / 1000), Number((fraction ?? "").padEnd(6, "0"))];
}

export class PriorityIndicatorsService {
  private readonly client: TossOpenApiClient;
  private readonly loadCandidates: (date: string) => PriorityCandidate[];
  private readonly now: () => Date;
  private readonly timezone: string;
  private readonly cache = new Map<string, { expiresAt: number; result: ServiceResult }>();
  private readonly inFlight = new Map<string, Promise<ServiceResult>>();

  constructor(options: {
    config?: TossOpenApiConfig;
    fetchImpl?: typeof fetch;
    loadCandidates?: (date: string) => PriorityCandidate[];
    now?: () => Date;
    timezone?: string;
  } = {}) {
    this.client = new TossOpenApiClient(options.config ?? readTossOpenApiConfig(), options.fetchImpl);
    this.loadCandidates = options.loadCandidates ?? selectedCandidates;
    this.now = options.now ?? (() => new Date());
    this.timezone = (options.timezone ?? process.env.STOCK_MONITOR_TIMEZONE?.trim()) || "Asia/Seoul";
  }

  async getIndicators(date: string): Promise<ServiceResult> {
    if (!isBusinessDate(date)) return { status: 400, payload: { reason: "invalid_date" } };
    const candidates = this.loadCandidates(date);
    const key = `priority-indicators:${date}:${candidates.map((item) => item.code).join(",")}`;
    const cached = this.cache.get(key);
    if (cached && cached.expiresAt > Date.now()) return cached.result;
    const pending = this.inFlight.get(key);
    if (pending) return pending;
    const request = this.buildIndicators(date, candidates).then((result) => {
      this.cache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, result });
      return result;
    }).finally(() => this.inFlight.delete(key));
    this.inFlight.set(key, request);
    return request;
  }

  private async buildIndicators(date: string, candidates: PriorityCandidate[]): Promise<ServiceResult> {
    const items: RecordValue[] = candidates.map((candidate) => ({
      stock_code: candidate.code,
      stock_name: candidate.name,
      market: candidate.market,
      market_source: candidate.marketSource,
      market_source_date: candidate.marketSourceDate,
      available: false,
      requested_as_of: date,
    }));
    const base: RecordValue = {
      surface: "web-view-priority-indicators",
      read_only: true,
      configured: this.client.configured,
      live_fetch: false,
      source: "toss-openapi-adjusted-daily",
      adjusted: true,
      page_size: PAGE_SIZE,
      max_pages: MAX_PAGES,
      writes_stock_monitor_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      business_date: date,
      derived_from: "web_view_candidate_evidence_top_2",
      items,
    };
    if (!this.client.configured) {
      for (const item of items) item.reason = "toss_not_configured";
      return { status: 200, payload: base };
    }
    if (!candidates.length) return { status: 200, payload: base };

    const historyItems = new Map<string, RecordValue>();
    for (const candidate of candidates) historyItems.set(candidate.code, await this.fetchHistory(candidate.code, date));
    const sourceFetchedAt = zonedDateTime(this.now(), this.timezone);
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index];
      const item = items[index];
      const history = historyItems.get(candidate.code);
      if (!history) {
        item.reason = "provider_unavailable";
        continue;
      }
      if (history.reason) {
        item.reason = history.reason;
        if (typeof history.upstream_status === "number") item.upstream_status = history.upstream_status;
        continue;
      }
      const rawCandles = history.candles;
      const pagesFetched = history.pages_fetched;
      const historyStatus = history.history_status;
      if (!Array.isArray(rawCandles) || !Number.isInteger(pagesFetched) || (pagesFetched as number) < 0 ||
        (pagesFetched as number) > MAX_PAGES || typeof historyStatus !== "string") {
        item.reason = "invalid_provider_response";
        continue;
      }
      if (!(pagesFetched as number) || !["complete", "cursor_not_provided", "page_limit_reached"].includes(historyStatus)) {
        item.reason = "invalid_provider_response";
        continue;
      }
      try {
        const candles = rawCandles.map((raw) => {
          if (!isRecord(raw) || typeof raw.timestamp !== "string" || raw.timestamp.length < 10) throw new TypeError("invalid candle timestamp");
          const day = raw.timestamp.slice(0, 10);
          return {
            time: day,
            open: raw.openPrice,
            high: raw.highPrice,
            low: raw.lowPrice,
            close: raw.closePrice,
            volume: raw.volume,
          };
        });
        const sourceDate = candles.reduce<string | null>((latest, candle) =>
          candle.time <= date && (!latest || candle.time > latest) ? candle.time : latest, null);
        const market = candidate.market ?? "unknown";
        const symbol = market === "KOSPI" ? `${candidate.code}.KS` : market === "KOSDAQ" ? `${candidate.code}.KQ` : candidate.code;
        const projection = buildPriorityIndicatorProjection({
          code: candidate.code,
          symbol,
          market,
          requestedAsOf: date,
          candles,
          source: SOURCE,
          sourceFetchedAt,
          sourceDate,
          barStatus: "unknown",
          confirmedPolicy: "Toss daily candles do not identify finality; status is not inferred.",
          cacheHit: false,
          stale: false,
          lastSuccessAt: sourceFetchedAt,
          sourceCalculationVersion: "toss-adjusted-daily-v1",
        });
        item.candle_count = candles.filter((candle) => candle.time <= date).length;
        item.pages_fetched = pagesFetched;
        item.history_status = historyStatus;
        if (!projection.snapshot.barAsOf) {
          item.reason = "no_daily_candles";
          continue;
        }
        item.available = true;
        item.snapshot = projection.snapshot;
        item.chart = projection.chart;
        item.price_conditions = projection.price_conditions;
        item.indicator_confirmation = projection.indicator_confirmation;
        item.condition_status = projection.condition_status;
        item.condition_explanation = projection.condition_explanation;
      } catch {
        item.reason = "invalid_provider_response";
      }
    }
    base.live_fetch = true;
    return { status: 200, payload: base };
  }

  private async fetchHistory(code: string, date: string): Promise<RecordValue> {
    let before = businessDateEnd(date, this.timezone);
    let cursor = cursorDateTime(before);
    if (cursor === null) return { reason: "invalid_provider_response" };
    const seenCursors = new Set([before]);
    const seenTimestamps = new Set<string>();
    const candles: RecordValue[] = [];
    let pagesFetched = 0;
    let historyStatus = "complete";
    try {
      for (let pageIndex = 0; pageIndex < MAX_PAGES; pageIndex += 1) {
        const response = await this.client.getPriorityDailyHistoryPage(code, before);
        pagesFetched += 1;
        const page = response.result as RecordValue;
        const pageCandles = Array.isArray(page.candles) ? page.candles : [];
        for (const raw of pageCandles) {
          if (!isRecord(raw) || typeof raw.timestamp !== "string") throw new TypeError("Toss history candle had an invalid timestamp.");
          if (raw.timestamp.slice(0, 10) > date || seenTimestamps.has(raw.timestamp)) continue;
          seenTimestamps.add(raw.timestamp);
          candles.push(raw);
        }
        if (!Object.hasOwn(page, "nextBefore")) {
          historyStatus = "cursor_not_provided";
          break;
        }
        const nextBefore = page.nextBefore;
        if (nextBefore === null) break;
        const nextCursor = cursorDateTime(nextBefore);
        if (nextCursor === null || nextCursor[0] > cursor[0] ||
          (nextCursor[0] === cursor[0] && nextCursor[1] >= cursor[1]) || seenCursors.has(nextBefore as string)) {
          throw new TypeError("Toss daily-history cursor did not move backwards.");
        }
        if (pageIndex === MAX_PAGES - 1) {
          historyStatus = "page_limit_reached";
          break;
        }
        seenCursors.add(nextBefore as string);
        before = nextBefore as string;
        cursor = nextCursor;
      }
      candles.sort((left, right) => String(right.timestamp).localeCompare(String(left.timestamp)));
      return { candles: candles.slice(0, PAGE_SIZE * MAX_PAGES), pages_fetched: pagesFetched, history_status: historyStatus };
    } catch (error) {
      const failure = historyError(error);
      if (!HISTORY_REASONS.has(String(failure.reason))) return { reason: "provider_unavailable", pages_fetched: pagesFetched };
      return { ...failure, pages_fetched: pagesFetched };
    }
  }
}

export const priorityIndicatorsService = new PriorityIndicatorsService();
