import "server-only";

import { withReadOnlyDatabase } from "./sqlite.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { isBusinessDate } from "../domain/daily.ts";

import {
  TossOpenApiClient,
  readTossOpenApiConfig,
  type TossOpenApiConfig,
} from "./toss-openapi.ts";

type StoredPriorityContext = { latestBusinessDate: string | null; symbols: string[] };
type QuotePayload = Record<string, unknown>;
type ServiceResult = { status: number; payload: QuotePayload };
type CacheEntry = { savedAt: number; payload: QuotePayload };

const CACHE_TTL_SECONDS = 30;
const STALE_TTL_SECONDS = 300;
const EMPTY_INVESTOR_TRADING = (date: string) => ({ reference_date: date, available: false, items: [] });

function readStoredContext(businessDate: string): StoredPriorityContext {
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const row = database.prepare(`
        SELECT MAX(business_date) AS business_date
        FROM (
          SELECT business_date FROM reports
          UNION ALL
          SELECT business_date FROM daily_stock_summaries
        )
      `).get() as { business_date: string | null };
      const latestBusinessDate = typeof row.business_date === "string" ? row.business_date : null;
      if (latestBusinessDate !== null && !isBusinessDate(latestBusinessDate)) {
        throw new Error("Stored latest business date is invalid");
      }
      if (latestBusinessDate && latestBusinessDate !== businessDate) return { latestBusinessDate, symbols: [] };

      const candidates = buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, 2);
      const symbols = [...new Set(candidates.rows
        .filter((candidate) => candidate.selected && /^\d{6}$/.test(candidate.stock_code))
        .map((candidate) => candidate.stock_code))].slice(0, 2);
      return { latestBusinessDate, symbols };
    } finally {
      database.exec("ROLLBACK");
    }
  });
}

function basePayload(date: string, configured: boolean): QuotePayload {
  return {
    surface: "web-view-toss-priority-quotes",
    read_only: true,
    configured,
    live_fetch: false,
    writes_db: false,
    sends_telegram: false,
    registers_scheduler: false,
    affects_ordering: false,
    priority_date: date,
  };
}

function investorTradingForDate(result: unknown, date: string, symbol: string): Record<string, unknown> | null {
  if (!result || typeof result !== "object" || Array.isArray(result)) return null;
  const records = (result as Record<string, unknown>).records;
  if (!Array.isArray(records)) return null;
  const record = records.find((item) => item && typeof item === "object" && !Array.isArray(item) &&
    (item as Record<string, unknown>).date === date && typeof (item as Record<string, unknown>).updatedAt === "string") as Record<string, unknown> | undefined;
  if (!record) return null;
  const netBuyVolume = (value: unknown): number | null => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const raw = (value as Record<string, unknown>).netBuyVolume;
    const parsed = typeof raw === "string" && /^\s*[+-]?\d+\s*$/.test(raw) ? Number(raw) :
      typeof raw === "number" && Number.isSafeInteger(raw) ? raw : null;
    return parsed !== null && Number.isSafeInteger(parsed) ? parsed : null;
  };
  return {
    symbol,
    business_date: date,
    updated_at: record.updatedAt,
    individual_net_buy_volume: netBuyVolume(record.individual),
    foreigner_net_buy_volume: netBuyVolume(record.foreigner),
    institution_net_buy_volume: netBuyVolume(record.institution),
  };
}

export class TossPriorityQuotesService {
  private readonly client: TossOpenApiClient;
  private readonly cache = new Map<string, CacheEntry>();
  private readonly inflight = new Map<string, Promise<CacheEntry>>();
  private readonly loadContext: (date: string) => StoredPriorityContext;
  private readonly clock: () => number;

  constructor(options: {
    config?: TossOpenApiConfig;
    fetchImpl?: typeof fetch;
    loadContext?: (date: string) => StoredPriorityContext;
    clock?: () => number;
  } = {}) {
    const config = options.config ?? readTossOpenApiConfig();
    this.client = new TossOpenApiClient(config, options.fetchImpl);
    this.loadContext = options.loadContext ?? readStoredContext;
    this.clock = options.clock ?? (() => performance.now() / 1000);
  }

  get configured(): boolean {
    return this.client.configured;
  }

  async getQuotes(date: string): Promise<ServiceResult> {
    const context = this.loadContext(date);
    const symbols = [...new Set(context.symbols.filter((symbol) => /^\d{6}$/.test(symbol)))].slice(0, 2);
    const common = { ...basePayload(date, this.client.configured), symbols, latest_business_date: context.latestBusinessDate,
      derived_from: "web_view_candidate_evidence_top_2" };

    if (context.latestBusinessDate && context.latestBusinessDate !== date) {
      return {
        status: 409,
        payload: {
          ...basePayload(date, this.client.configured),
          latest_business_date: context.latestBusinessDate,
          symbols: [],
          quotes: [],
          investor_trading: EMPTY_INVESTOR_TRADING(date),
          reason: "latest_business_date_only",
        },
      };
    }
    if (!this.client.configured) {
      return {
        status: 200,
        payload: {
          ...common,
          quotes: [],
          investor_trading: EMPTY_INVESTOR_TRADING(date),
          cache: "disabled",
          reason: "not_configured",
        },
      };
    }
    if (!symbols.length) {
      return {
        status: 200,
        payload: {
          ...common,
          live_fetch: false,
          symbols: [],
          quotes: [],
          investor_trading: EMPTY_INVESTOR_TRADING(date),
          cache: "empty",
          reason: "no_priority_symbols",
        },
      };
    }

    const key = date + ":" + symbols.join(",");
    const current = this.clock();
    const cached = this.cache.get(key);
    if (cached && current - cached.savedAt <= CACHE_TTL_SECONDS) {
      return { status: 200, payload: { ...cached.payload, latest_business_date: context.latestBusinessDate, cache: "hit" } };
    }
    const sharedRequest = this.inflight.get(key);
    if (sharedRequest) {
      try {
        const shared = await sharedRequest;
        const age = this.clock() - shared.savedAt;
        if (age <= CACHE_TTL_SECONDS) {
          return { status: 200, payload: { ...shared.payload, latest_business_date: context.latestBusinessDate, cache: "shared" } };
        }
        if (age <= STALE_TTL_SECONDS) return this.staleResult(shared, context.latestBusinessDate);
      } catch {
        if (cached && this.clock() - cached.savedAt <= STALE_TTL_SECONDS) return this.staleResult(cached, context.latestBusinessDate);
        return this.upstreamUnavailable(date);
      }
    }

    const request = this.fetchLive(date, symbols, common);
    this.inflight.set(key, request);
    try {
      const fresh = await request;
      this.cache.set(key, fresh);
      return { status: 200, payload: { ...fresh.payload, latest_business_date: context.latestBusinessDate } };
    } catch {
      const previous = this.cache.get(key);
      if (previous && this.clock() - previous.savedAt <= STALE_TTL_SECONDS) return this.staleResult(previous, context.latestBusinessDate);
      return this.upstreamUnavailable(date);
    } finally {
      if (this.inflight.get(key) === request) this.inflight.delete(key);
    }
  }

  private async fetchLive(date: string, symbols: string[], common: QuotePayload): Promise<CacheEntry> {
    const started = this.clock();
    const quoteResponse = await this.client.getPrices(symbols);
    const investors: Record<string, unknown>[] = [];
    try {
      for (const symbol of symbols) {
        const investorResponse = await this.client.getPriorityInvestorTrading(symbol, date);
        const item = investorTradingForDate(investorResponse.result, date, symbol);
        if (item) investors.push(item);
      }
    } catch {
      investors.length = 0;
    }
    const payload: QuotePayload = {
      ...common,
      live_fetch: true,
      symbols,
      fetched_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      latency_ms: Math.round((this.clock() - started) * 1000),
      rate_limit: quoteResponse.rateLimit,
      quotes: quoteResponse.result,
      investor_trading: { reference_date: date, available: investors.length > 0, items: investors },
      cache: "miss",
    };
    return { savedAt: this.clock(), payload };
  }

  private staleResult(entry: CacheEntry, latestBusinessDate: string | null): ServiceResult {
    return {
      status: 200,
      payload: { ...entry.payload, latest_business_date: latestBusinessDate, cache: "stale", stale_reason: "upstream_unavailable" },
    };
  }

  private upstreamUnavailable(date: string): ServiceResult {
    return {
      status: 502,
      payload: { ...basePayload(date, this.client.configured), symbols: [], quotes: [], reason: "upstream_unavailable" },
    };
  }
}

export const tossPriorityQuotesService = new TossPriorityQuotesService();

export function parseTossPriorityQuotesDate(request: Request): string | null {
  if (request.method !== "GET") return null;
  const query = new URL(request.url).searchParams;
  const date = query.get("date");
  return query.size === 1 && query.getAll("date").length === 1 && date && isBusinessDate(date) ? date : null;
}
