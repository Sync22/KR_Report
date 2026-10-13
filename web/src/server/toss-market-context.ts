import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";
import {
  TossOpenApiClient,
  TossOpenApiError,
  readTossOpenApiConfig,
  type TossOpenApiConfig,
  type TossReadonlyResponse,
} from "./toss-openapi.ts";

type StoredContext = { latestBusinessDate: string | null; symbols: string[] };
type Payload = Record<string, unknown>;
type ServiceResult = { status: number; payload: Payload };
type CacheEntry = { savedAt: number; payload: Payload };
type Market = "KOSPI" | "KOSDAQ";

const CACHE_TTL_SECONDS = 30;
const STALE_TTL_SECONDS = 300;
const MARKET_ORDER: Market[] = ["KOSPI", "KOSDAQ"];
const MARKET_ENDPOINTS = [
  ["KOSPI", "market-indicator-kospi-daily-candles"],
  ["KOSDAQ", "market-indicator-kosdaq-daily-candles"],
] as const;
const INVESTOR_ENDPOINTS = [
  ["KOSPI", "market-investor-kospi"],
  ["KOSDAQ", "market-investor-kosdaq"],
] as const;

function readStoredContext(database: DatabaseSync, date: string): StoredContext {
  const row = database.prepare(`
    SELECT MAX(business_date) AS business_date
    FROM (
      SELECT business_date FROM reports
      UNION ALL
      SELECT business_date FROM daily_stock_summaries
    )
  `).get() as { business_date: unknown } | undefined;
  const latestBusinessDate = row?.business_date === null || row?.business_date === undefined
    ? null
    : typeof row.business_date === "string" && isBusinessDate(row.business_date) ? row.business_date : "invalid";
  if (latestBusinessDate === "invalid") throw new Error("Stored latest business date is invalid");
  if (latestBusinessDate !== date) return { latestBusinessDate, symbols: [] };

  const snapshot = buildCandidateEvidenceSnapshotFromDatabase(database, date, 2);
  const symbols = [...new Set(snapshot.rows
    .filter((candidate) => candidate.selected)
    .map((candidate) => candidate.stock_code.trim())
    .filter((symbol) => /^\d{6}$/.test(symbol)))].slice(0, 2);
  return { latestBusinessDate, symbols };
}

function readStoredContextSnapshot(date: string): StoredContext {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      return readStoredContext(database, date);
    } finally {
      database.exec("ROLLBACK");
    }
  });
}

function pythonString(value: unknown): string {
  if (value === null) return "None";
  if (value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  return String(value);
}

function truthyText(value: unknown): string {
  return value ? pythonString(value).trim() : "";
}

function providerNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const raw = pythonString(value);
  if (!raw.trim()) return null;
  const result = Number(raw);
  return Number.isFinite(result) ? result : null;
}

function object(value: unknown): Payload | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Payload : null;
}

function projectInvestorRecord(value: unknown): Payload | null {
  const record = object(value);
  if (!record) return null;
  const result: Payload = {};
  for (const key of ["date", "updatedAt"]) if (Object.hasOwn(record, key)) result[key] = record[key];
  for (const key of ["individual", "foreigner", "institution", "otherCorporation"]) {
    const amount = object(record[key]);
    if (!amount) continue;
    const projected: Payload = {};
    for (const field of ["buyAmount", "sellAmount"]) if (Object.hasOwn(amount, field)) projected[field] = amount[field];
    result[key] = projected;
  }
  return result;
}

function projectMarketPriceChanges(marketPrices: unknown, candleResults: Record<Market, unknown>, referenceDate: string): Payload {
  const priceBySymbol = new Map<string, unknown>();
  if (Array.isArray(marketPrices)) {
    for (const value of marketPrices) {
      const item = object(value);
      const symbol = item ? truthyText(item.symbol) : "";
      if (symbol) priceBySymbol.set(symbol, item?.lastPrice);
    }
  }
  const changes: Payload = {};
  for (const market of MARKET_ORDER) {
    const page = object(candleResults[market]);
    const candles = Array.isArray(page?.candles) ? page.candles : [];
    const prior = candles
      .map(object)
      .filter((item): item is Payload => !!item && typeof item.timestamp === "string" && item.timestamp.slice(0, 10) < referenceDate)
      .sort((a, b) => String(a.timestamp) > String(b.timestamp) ? -1 : String(a.timestamp) < String(b.timestamp) ? 1 : 0)[0];
    if (!prior) continue;
    const close = providerNumber(prior.closePrice);
    const price = providerNumber(priceBySymbol.get(market));
    if (close === null || price === null || close <= 0) continue;
    changes[market] = {
      base_date: String(prior.timestamp).slice(0, 10),
      base_close: pythonString(prior.closePrice),
      change_rate: (price - close) / close,
    };
  }
  return changes;
}

function rateLimitEntry(response: TossReadonlyResponse): Record<string, string> {
  return response.rateLimit;
}

function wrapPayload(payload: Payload, latestBusinessDate: string | null): ServiceResult {
  return {
    status: 200,
    payload: {
      surface: "web-view-toss-market-context",
      read_only: true,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      ...payload,
      latest_business_date: latestBusinessDate,
      derived_from: "web_view_candidate_evidence_top_2",
    },
  };
}

function unavailablePayload(date: string, configured: boolean): Payload {
  return {
    configured,
    live_fetch: false,
    reference_date: date,
    rankings: [],
    market_prices: [],
    priority_overlap_symbols: [],
    investor_flow: { KOSPI: null, KOSDAQ: null },
    reason: "upstream_unavailable",
  };
}

function latestDateConflict(latestBusinessDate: string | null, configured: boolean): ServiceResult {
  return {
    status: 409,
    payload: {
      surface: "web-view-toss-market-context",
      read_only: true,
      configured,
      live_fetch: false,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      reference_date: null,
      rankings: [],
      market_prices: [],
      priority_overlap_symbols: [],
      investor_flow: { KOSPI: null, KOSDAQ: null },
      latest_business_date: latestBusinessDate,
      reason: latestBusinessDate === null ? "latest_business_date_unavailable" : "latest_business_date_only",
    },
  };
}

function failedDatabaseRead(configured: boolean): ServiceResult {
  return {
    status: 502,
    payload: {
      surface: "web-view-toss-market-context",
      read_only: true,
      configured,
      live_fetch: false,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      reference_date: null,
      rankings: [],
      market_prices: [],
      priority_overlap_symbols: [],
      investor_flow: { KOSPI: null, KOSDAQ: null },
      reason: "upstream_unavailable",
    },
  };
}

async function waitForSharedRequest<T>(request: Promise<T>, timeoutMs: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      request,
      new Promise<T>((_resolve, reject) => { timer = setTimeout(() => reject(new Error("Toss market-context request timed out")), timeoutMs); }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

export class TossMarketContextService {
  private readonly client: TossOpenApiClient;
  private readonly cache = new Map<string, CacheEntry>();
  private readonly inflight = new Map<string, Promise<CacheEntry>>();
  private readonly loadContext: (date: string) => StoredContext;
  private readonly clock: () => number;

  constructor(options: {
    config?: TossOpenApiConfig;
    fetchImpl?: typeof fetch;
    loadContext?: (date: string) => StoredContext;
    clock?: () => number;
  } = {}) {
    this.client = new TossOpenApiClient(options.config ?? readTossOpenApiConfig(), options.fetchImpl);
    this.loadContext = options.loadContext ?? readStoredContextSnapshot;
    this.clock = options.clock ?? (() => performance.now() / 1000);
  }

  async getMarketContext(date: string): Promise<ServiceResult> {
    let stored: StoredContext;
    try {
      stored = this.loadContext(date);
    } catch {
      return failedDatabaseRead(this.client.configured);
    }
    if (!stored.latestBusinessDate || stored.latestBusinessDate !== date) {
      return latestDateConflict(stored.latestBusinessDate, this.client.configured);
    }
    const symbols = [...new Set(stored.symbols.map((symbol) => symbol.trim()).filter((symbol) => /^\d{6}$/.test(symbol)))].slice(0, 2);
    if (!this.client.configured) {
      return wrapPayload({
        surface: "toss-market-context",
        read_only: true,
        configured: false,
        live_fetch: false,
        writes_db: false,
        sends_telegram: false,
        registers_scheduler: false,
        affects_ordering: false,
        reference_date: date,
        ranked_at: null,
        rankings: [],
        market_prices: [],
        priority_overlap_symbols: [],
        investor_flow: { KOSPI: null, KOSDAQ: null },
        priority_symbols: symbols,
        cache: "disabled",
        reason: "not_configured",
      }, stored.latestBusinessDate);
    }

    const cacheKey = `${date}:${symbols.join(",")}`;
    const now = this.clock();
    const cached = this.cache.get(cacheKey);
    if (cached && now - cached.savedAt <= CACHE_TTL_SECONDS) {
      return wrapPayload({ ...cached.payload, cache: "hit" }, stored.latestBusinessDate);
    }
    const sharedRequest = this.inflight.get(cacheKey);
    if (sharedRequest) {
      try {
        const shared = await waitForSharedRequest(sharedRequest, Math.max(this.client.config.timeoutSeconds * 4 + 1, 1) * 1000);
        const age = this.clock() - shared.savedAt;
        if (age <= CACHE_TTL_SECONDS) return wrapPayload({ ...shared.payload, cache: "shared" }, stored.latestBusinessDate);
        if (age <= STALE_TTL_SECONDS) return wrapPayload({ ...shared.payload, cache: "stale", stale_reason: "upstream_unavailable" }, stored.latestBusinessDate);
      } catch {
        if (cached && this.clock() - cached.savedAt <= STALE_TTL_SECONDS) {
          return wrapPayload({ ...cached.payload, cache: "stale", stale_reason: "upstream_unavailable" }, stored.latestBusinessDate);
        }
        return wrapPayload(unavailablePayload(date, this.client.configured), stored.latestBusinessDate);
      }
      return wrapPayload(unavailablePayload(date, this.client.configured), stored.latestBusinessDate);
    }

    const request = this.fetchLive(date, symbols);
    this.inflight.set(cacheKey, request);
    try {
      const fresh = await request;
      this.cache.set(cacheKey, fresh);
      return wrapPayload(fresh.payload, stored.latestBusinessDate);
    } catch {
      const previous = this.cache.get(cacheKey);
      if (previous && this.clock() - previous.savedAt <= STALE_TTL_SECONDS) {
        return wrapPayload({ ...previous.payload, cache: "stale", stale_reason: "upstream_unavailable" }, stored.latestBusinessDate);
      }
      return wrapPayload(unavailablePayload(date, this.client.configured), stored.latestBusinessDate);
    } finally {
      if (this.inflight.get(cacheKey) === request) this.inflight.delete(cacheKey);
    }
  }

  private async fetchLive(date: string, prioritySymbols: string[]): Promise<CacheEntry> {
    const started = this.clock();
    const rankingResponse = await this.client.getMarketRankings();
    const pricesResponse = await this.client.getMarketIndicatorPrices();
    const candleResults: Record<Market, unknown> = { KOSPI: {}, KOSDAQ: {} };
    const investorFlow: Record<Market, Payload | null> = { KOSPI: null, KOSDAQ: null };
    const rateLimit: Record<string, Record<string, string>> = {
      "ranking-kr-top20": rateLimitEntry(rankingResponse),
      "market-indicator-prices": rateLimitEntry(pricesResponse),
    };
    for (const [market, endpoint] of MARKET_ENDPOINTS) {
      const response = await this.client.getMarketIndicatorCandles(market);
      candleResults[market] = response.result;
      rateLimit[endpoint] = rateLimitEntry(response);
    }
    for (const [market, endpoint] of INVESTOR_ENDPOINTS) {
      const response = await this.client.getMarketInvestorTrading(market, date);
      const result = object(response.result);
      const records = Array.isArray(result?.records) ? result.records : [];
      const record = records.map(object).find((item) => item?.date === date);
      investorFlow[market] = projectInvestorRecord(record);
      rateLimit[endpoint] = rateLimitEntry(response);
    }

    const rankingResult = object(rankingResponse.result) ?? {};
    const rankings = Array.isArray(rankingResult.rankings) ? rankingResult.rankings : [];
    const rankingSymbols = rankings
      .map(object)
      .filter((item): item is Payload => !!item)
      .map((item) => truthyText(item.symbol))
      .filter(Boolean);
    let stockNames: Record<string, string> = {};
    let stockMarkets: Record<string, string> = {};
    let stockSecurityTypes: Record<string, string> = {};
    let etfSymbols: string[] = [];
    let stockMetadataAvailable = !rankingSymbols.length;
    let stockMetadataReason: string | null = null;
    if (rankingSymbols.length) {
      try {
        const stockResponse = await this.client.getMarketRankingStocks(rankingSymbols);
        rateLimit["market-ranking-stocks"] = rateLimitEntry(stockResponse);
        const rows = Array.isArray(stockResponse.result) ? stockResponse.result.map(object).filter((item): item is Payload => !!item) : [];
        stockNames = Object.fromEntries(rows
          .map((item) => [truthyText(item.symbol), truthyText(item.name)])
          .filter(([symbol, name]) => !!symbol && !!name));
        stockMarkets = Object.fromEntries(rows
          .map((item) => [truthyText(item.symbol), truthyText(item.market)])
          .filter(([symbol]) => !!symbol));
        stockSecurityTypes = Object.fromEntries(rows
          .map((item) => [truthyText(item.symbol), truthyText(item.securityType)])
          .filter(([symbol]) => !!symbol));
        etfSymbols = rows
          .filter((item) => truthyText(item.symbol) && truthyText(item.securityType).toUpperCase() === "ETF")
          .map((item) => truthyText(item.symbol));
        stockMetadataAvailable = Object.keys(stockNames).length === rankingSymbols.length &&
          Object.keys(stockSecurityTypes).length === rankingSymbols.length;
        if (!stockMetadataAvailable) stockMetadataReason = "partial_stock_metadata";
      } catch (error) {
        if (!(error instanceof TossOpenApiError)) throw error;
        stockMetadataReason = "stock_metadata_unavailable";
      }
    }
    const rankedSymbols = new Set(rankings
      .map(object)
      .filter((item): item is Payload => !!item)
      .map((item) => truthyText(item.symbol))
      .filter(Boolean));
    const marketPrices = Array.isArray(pricesResponse.result) ? pricesResponse.result : [];
    const payload: Payload = {
      surface: "toss-market-context",
      read_only: true,
      configured: true,
      live_fetch: true,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      reference_date: date,
      ranked_at: rankingResult.rankedAt ?? null,
      rankings,
      stock_names: stockNames,
      stock_markets: stockMarkets,
      stock_security_types: stockSecurityTypes,
      etf_symbols: etfSymbols,
      stock_metadata_available: stockMetadataAvailable,
      stock_metadata_reason: stockMetadataReason,
      market_prices: marketPrices,
      market_price_changes: projectMarketPriceChanges(marketPrices, candleResults, date),
      priority_overlap_symbols: prioritySymbols.filter((symbol) => rankedSymbols.has(symbol)),
      investor_flow: investorFlow,
      fetched_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      latency_ms: Math.round((this.clock() - started) * 1000 * 10) / 10,
      rate_limit: rateLimit,
      cache: "miss",
    };
    return { savedAt: this.clock(), payload };
  }
}

export const tossMarketContextService = new TossMarketContextService();
