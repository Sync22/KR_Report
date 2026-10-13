import "server-only";

export const TOSS_OPENAPI_BASE_URL = "https://openapi.tossinvest.com";
export const TOSS_OPENAPI_MAX_RESPONSE_BYTES = 1_048_576;

export type TossOpenApiConfig = {
  clientId: string | null;
  clientSecret: string | null;
  liveEnabled: boolean;
  baseUrl: string;
  timeoutSeconds: number;
  configured: boolean;
};

type TossPayload = Record<string, unknown>;
type TossToken = { accessToken: string; expiresAt: number };
export type TossReadonlyResponse = { result: unknown; rateLimit: Record<string, string> };
type Market = "KOSPI" | "KOSDAQ";

const MARKET_INVESTOR_BREAKDOWN_FIELDS = [
  "financialInvestment", "insurance", "trust", "privateEquityFund", "bank", "otherFinancialInstitution", "pensionFund",
];
const MARKET_CANDLE_FIELDS = ["timestamp", "openPrice", "highPrice", "lowPrice", "closePrice", "volume", "currency"];
const STOCK_FIELDS = [
  "symbol", "name", "englishName", "isinCode", "market", "securityType", "isCommonShare", "status", "currency",
  "listDate", "delistDate", "sharesOutstanding", "leverageFactor", "koreanMarketDetail",
];

export class TossOpenApiError extends Error {
  readonly statusCode?: number;
  readonly retryAfter?: string;
  readonly providerCode?: string;
  readonly providerReason?: "invalid_provider_response" | "provider_timeout" | "provider_unavailable";

  constructor(
    message: string,
    statusCode?: number,
    retryAfter?: string,
    providerCode?: string,
    providerReason?: "invalid_provider_response" | "provider_timeout" | "provider_unavailable",
  ) {
    super(message);
    this.statusCode = statusCode;
    this.retryAfter = retryAfter;
    this.providerCode = providerCode;
    this.providerReason = providerReason;
  }
}

export function readTossOpenApiConfig(env: Record<string, string | undefined> = process.env): TossOpenApiConfig {
  const clientId = env.STOCK_MONITOR_TOSS_OPENAPI_CLIENT_ID?.trim() || null;
  const clientSecret = env.STOCK_MONITOR_TOSS_OPENAPI_CLIENT_SECRET?.trim() || null;
  const liveEnabled = /^(1|true|yes|on)$/i.test(env.STOCK_MONITOR_TOSS_OPENAPI_LIVE_ENABLED?.trim() ?? "");
  const baseUrl = (env.STOCK_MONITOR_TOSS_OPENAPI_BASE_URL?.trim() || TOSS_OPENAPI_BASE_URL).replace(/\/$/, "");
  const configuredTimeout = Number(env.STOCK_MONITOR_TOSS_OPENAPI_TIMEOUT_SECONDS);
  const timeoutSeconds = Number.isFinite(configuredTimeout) && configuredTimeout >= 1 && configuredTimeout <= 30
    ? configuredTimeout
    : 15;
  return {
    clientId,
    clientSecret,
    liveEnabled,
    baseUrl,
    timeoutSeconds,
    configured: liveEnabled && !!clientId && !!clientSecret && baseUrl === TOSS_OPENAPI_BASE_URL,
  };
}

function isRecord(value: unknown): value is TossPayload {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function hasOnlyKeys(value: TossPayload, allowed: readonly string[]): boolean {
  return Object.keys(value).every((key) => allowed.includes(key));
}

function hasScalarValues(value: TossPayload, nested: readonly string[] = []): boolean {
  return Object.entries(value).every(([key, item]) => nested.includes(key) ||
    item === null || !["object", "function"].includes(typeof item));
}

function objectList(value: unknown, allowed: readonly string[]): TossPayload[] {
  if (!Array.isArray(value) || value.some((item) => !isRecord(item) || !hasOnlyKeys(item, allowed))) {
    throw new TossOpenApiError("Toss market-context response had an unexpected shape.");
  }
  return value as TossPayload[];
}

async function readBoundedJson(response: Response, action: string): Promise<TossPayload> {
  const reader = response.body?.getReader();
  if (!reader) throw new TossOpenApiError(`Toss ${action} returned an empty response.`);
  const chunks: Uint8Array[] = [];
  let byteLength = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      byteLength += value.byteLength;
      if (byteLength > TOSS_OPENAPI_MAX_RESPONSE_BYTES) {
        await reader.cancel().catch(() => undefined);
        throw new TossOpenApiError(`Toss ${action} response exceeded the size limit.`);
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof TossOpenApiError) throw error;
    throw new TossOpenApiError(`Toss ${action} response could not be read.`);
  } finally {
    reader.releaseLock();
  }
  try {
    const bytes = new Uint8Array(byteLength);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const payload: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!isRecord(payload)) throw new Error("shape");
    return payload;
  } catch {
    throw new TossOpenApiError(`Toss ${action} returned invalid JSON.`);
  }
}

function rateLimit(headers: Headers): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, name] of [
    ["limit", "x-ratelimit-limit"],
    ["remaining", "x-ratelimit-remaining"],
    ["reset", "x-ratelimit-reset"],
    ["retry_after", "retry-after"],
  ]) {
    const value = headers.get(name);
    if (value !== null) result[key] = value;
  }
  return result;
}

export class TossOpenApiClient {
  private token: TossToken | null = null;
  private tokenRequest: Promise<TossToken> | null = null;
  private automaticReissueUsed = false;
  readonly config: TossOpenApiConfig;
  private readonly fetchImpl: typeof fetch;
  private readonly now: () => number;

  constructor(
    config: TossOpenApiConfig = readTossOpenApiConfig(),
    fetchImpl: typeof fetch = fetch,
    now: () => number = Date.now,
  ) {
    this.config = config;
    this.fetchImpl = fetchImpl;
    this.now = now;
  }

  get configured(): boolean {
    return this.config.configured;
  }

  async getPrices(symbols: readonly string[]): Promise<TossReadonlyResponse> {
    if (!this.configured || symbols.length < 1 || symbols.length > 2 || symbols.some((symbol) => !/^\d{6}$/.test(symbol))) {
      throw new TossOpenApiError("Toss prices request is outside the fixed read-only profile.");
    }
    const url = new URL("/api/v1/prices", TOSS_OPENAPI_BASE_URL);
    url.searchParams.set("symbols", symbols.join(","));
    const response = await this.getWithToken("prices", url);
    const rows = response.payload.result;
    if (!Array.isArray(rows) || rows.length > symbols.length) throw new TossOpenApiError("Toss prices response had an unexpected shape.");
    const quotes = rows.map((row: unknown) => {
      if (!isRecord(row) || Object.keys(row).some((key) => !["symbol", "timestamp", "lastPrice", "currency"].includes(key)) ||
        Object.values(row).some((value) => value !== null && !["string", "number", "boolean"].includes(typeof value)) ||
        typeof row.symbol !== "string" || !symbols.includes(row.symbol)) {
        throw new TossOpenApiError("Toss prices response included an unsupported item.");
      }
      return row;
    });
    return { result: quotes, rateLimit: response.rateLimit };
  }

  async getPriorityDailyCandles(symbol: string, before: string, count: 30 | 90 | 180): Promise<TossReadonlyResponse> {
    if (!this.configured || !/^\d{6}$/.test(symbol) || !isOffsetDateTime(before) || ![30, 90, 180].includes(count)) {
      throw new TossOpenApiError("Toss daily candle request is outside the fixed read-only profile.");
    }
    const url = new URL("/api/v1/candles", TOSS_OPENAPI_BASE_URL);
    for (const [key, value] of Object.entries({ symbol, interval: "1d", count: String(count), before, adjusted: "true" })) {
      url.searchParams.set(key, value);
    }
    const response = await this.getWithToken("priority daily candles", url, true);
    const page = response.payload.result;
    if (!isRecord(page) || Object.keys(page).some((key) => !["candles", "nextBefore"].includes(key)) ||
      !Array.isArray(page.candles) || page.candles.length > count ||
      (page.nextBefore !== undefined && page.nextBefore !== null && typeof page.nextBefore !== "string")) {
      throw new TossOpenApiError("Toss daily candle response had an unexpected shape.");
    }
    const fields = ["timestamp", "openPrice", "highPrice", "lowPrice", "closePrice", "volume", "currency"];
    for (const candle of page.candles) {
      if (!isRecord(candle) || Object.keys(candle).some((key) => !fields.includes(key)) ||
        fields.some((key) => !Object.hasOwn(candle, key)) || typeof candle.timestamp !== "string" ||
        Object.values(candle).some((value) => value !== null && !["string", "number", "boolean"].includes(typeof value))) {
        throw new TossOpenApiError("Toss daily candle response included an unsupported item.");
      }
    }
    return { result: page, rateLimit: response.rateLimit };
  }

  async getPriorityDailyHistoryPage(symbol: string, before: string): Promise<TossReadonlyResponse> {
    if (!this.configured || !/^\d{6}$/.test(symbol) || !isOffsetDateTime(before)) {
      throw new TossOpenApiError("Toss daily history request is outside the fixed read-only profile.");
    }
    const url = new URL("/api/v1/candles", TOSS_OPENAPI_BASE_URL);
    for (const [key, value] of Object.entries({ symbol, interval: "1d", count: "200", before, adjusted: "true" })) {
      url.searchParams.set(key, value);
    }
    let response: { payload: TossPayload; rateLimit: Record<string, string> };
    try {
      response = await this.getWithToken("priority daily history", url, true);
    } catch (error) {
      if (error instanceof TossOpenApiError && error.statusCode === undefined && !error.providerReason) {
        throw new TossOpenApiError(error.message, undefined, undefined, undefined, "invalid_provider_response");
      }
      throw error;
    }
    const page = response.payload.result;
    if (!isRecord(page) || Object.keys(page).some((key) => !["candles", "nextBefore"].includes(key)) ||
      !Array.isArray(page.candles) || page.candles.length > 200 ||
      (page.nextBefore !== undefined && page.nextBefore !== null && typeof page.nextBefore !== "string")) {
      throw new TossOpenApiError("Toss daily history response had an unexpected shape.", undefined, undefined, undefined, "invalid_provider_response");
    }
    const fields = ["timestamp", "openPrice", "highPrice", "lowPrice", "closePrice", "volume", "currency"];
    for (const candle of page.candles) {
      if (!isRecord(candle) || Object.keys(candle).some((key) => !fields.includes(key)) ||
        fields.some((key) => !Object.hasOwn(candle, key)) || typeof candle.timestamp !== "string" ||
        Object.values(candle).some((value) => value !== null && !["string", "number", "boolean"].includes(typeof value))) {
        throw new TossOpenApiError("Toss daily history response included an unsupported item.", undefined, undefined, undefined, "invalid_provider_response");
      }
    }
    return { result: page, rateLimit: response.rateLimit };
  }

  async getPriorityInvestorTrading(symbol: string, date: string): Promise<TossReadonlyResponse> {
    if (!this.configured || !/^\d{6}$/.test(symbol) || !isIsoDate(date)) {
      throw new TossOpenApiError("Toss investor-trading request is outside the fixed read-only profile.");
    }
    const url = new URL(`/api/v1/stocks/${symbol}/investor-trading`, TOSS_OPENAPI_BASE_URL);
    url.searchParams.set("count", "1");
    url.searchParams.set("until", date);
    const response = await this.getWithToken("priority investor-trading", url);
    const result = response.payload.result;
    if (!isRecord(result) || Object.keys(result).some((key) => !["nextUntil", "records"].includes(key)) || !Array.isArray(result.records) || result.records.length > 1) {
      throw new TossOpenApiError("Toss investor-trading response had an unexpected shape.");
    }
    for (const record of result.records) {
      if (!isRecord(record) || Object.keys(record).some((key) => ![
        "date", "updatedAt", "individual", "foreigner", "institution", "otherCorporation", "foreignerHolding", "cfd",
      ].includes(key))) throw new TossOpenApiError("Toss investor-trading response included an unsupported item.");
      for (const key of ["individual", "foreigner", "institution"]) {
        const amount = record[key];
        if (amount === undefined || amount === null) continue;
        const allowed = key === "institution"
          ? ["buyVolume", "sellVolume", "netBuyVolume", "breakdown"]
          : ["buyVolume", "sellVolume", "netBuyVolume"];
        if (!isRecord(amount) || Object.keys(amount).some((field) => !allowed.includes(field)) ||
          Object.entries(amount).some(([field, value]) => field !== "breakdown" && value !== null && !["string", "number"].includes(typeof value))) {
          throw new TossOpenApiError("Toss investor-trading response included an unsupported amount.");
        }
      }
    }
    return { result, rateLimit: response.rateLimit };
  }

  async getMarketRankings(): Promise<TossReadonlyResponse> {
    const response = await this.getMarketContextResult("ranking", "/api/v1/rankings", {
      type: "MARKET_TRADING_AMOUNT", marketCountry: "KR", duration: "realtime", count: "20",
    });
    const result = response.result;
    if (!isRecord(result) || !hasOnlyKeys(result, ["rankedAt", "rankings"]) ||
      (result.rankedAt !== undefined && result.rankedAt !== null && typeof result.rankedAt !== "string")) {
      throw new TossOpenApiError("Toss ranking response had an unexpected shape.");
    }
    const rows = objectList(result.rankings, ["rank", "symbol", "currency", "price", "tradingVolume", "tradingAmount"]);
    if (rows.length > 20) throw new TossOpenApiError("Toss ranking response exceeded the Top20 limit.");
    for (const row of rows) {
      if (!hasScalarValues(row, ["price"])) throw new TossOpenApiError("Toss ranking response included nested content.");
      const price = row.price;
      if (price === undefined || price === null) continue;
      if (!isRecord(price) || !hasOnlyKeys(price, ["lastPrice", "basePrice", "changeRate"]) || !hasScalarValues(price)) {
        throw new TossOpenApiError("Toss ranking price had an unexpected shape.");
      }
    }
    return response;
  }

  async getMarketIndicatorPrices(): Promise<TossReadonlyResponse> {
    const response = await this.getMarketContextResult("market-indicator prices", "/api/v1/market-indicators/prices", {
      symbols: "KOSPI,KOSDAQ",
    });
    const rows = objectList(response.result, ["symbol", "timestamp", "lastPrice"]);
    if (rows.length > 2 || rows.some((row) => !hasScalarValues(row))) {
      throw new TossOpenApiError("Toss market-indicator price response had an unexpected shape.");
    }
    return response;
  }

  async getMarketIndicatorCandles(market: Market): Promise<TossReadonlyResponse> {
    const response = await this.getMarketContextResult(`market-indicator ${market} candles`,
      `/api/v1/market-indicators/${market}/candles`, { interval: "1d", count: "2" });
    const page = response.result;
    if (!isRecord(page) || !hasOnlyKeys(page, ["candles", "nextBefore"]) ||
      (page.nextBefore !== undefined && page.nextBefore !== null && typeof page.nextBefore !== "string")) {
      throw new TossOpenApiError("Toss market-indicator candle response had an unexpected shape.");
    }
    const rows = objectList(page.candles, MARKET_CANDLE_FIELDS);
    if (rows.length > 2 || rows.some((row) => !hasScalarValues(row))) {
      throw new TossOpenApiError("Toss market-indicator candle response exceeded its row limit.");
    }
    return response;
  }

  async getMarketInvestorTrading(market: Market, date: string): Promise<TossReadonlyResponse> {
    if (!isIsoDate(date)) throw new TossOpenApiError("Toss market-investor date is outside the fixed read-only profile.");
    const response = await this.getMarketContextResult(`market-investor ${market}`,
      `/api/v1/market-indicators/${market}/investor-trading`, { interval: "1d", count: "1", until: date });
    const result = response.result;
    if (!isRecord(result) || !hasOnlyKeys(result, ["nextUntil", "records"])) {
      throw new TossOpenApiError("Toss market-investor response had an unexpected shape.");
    }
    const records = objectList(result.records, ["date", "updatedAt", "individual", "foreigner", "institution", "otherCorporation"]);
    if (records.length > 1) throw new TossOpenApiError("Toss market-investor response exceeded the one-record limit.");
    for (const record of records) {
      if (!hasScalarValues(record, ["individual", "foreigner", "institution", "otherCorporation"])) {
        throw new TossOpenApiError("Toss market-investor record included nested content.");
      }
      for (const investor of ["individual", "foreigner", "institution", "otherCorporation"]) {
        const value = record[investor];
        if (value === undefined || value === null) continue;
        const allowed = investor === "institution" ? ["buyAmount", "sellAmount", "breakdown"] : ["buyAmount", "sellAmount"];
        if (!isRecord(value) || !hasOnlyKeys(value, allowed) || !hasScalarValues(value, ["breakdown"])) {
          throw new TossOpenApiError("Toss market-investor amount had an unexpected shape.");
        }
        if (value.breakdown === undefined || value.breakdown === null) continue;
        if (investor !== "institution" || !isRecord(value.breakdown) || !hasOnlyKeys(value.breakdown, MARKET_INVESTOR_BREAKDOWN_FIELDS)) {
          throw new TossOpenApiError("Toss institution breakdown had an unexpected shape.");
        }
        for (const amount of Object.values(value.breakdown)) {
          if (!isRecord(amount) || !hasOnlyKeys(amount, ["buyAmount", "sellAmount"]) || !hasScalarValues(amount)) {
            throw new TossOpenApiError("Toss institution breakdown amount had an unexpected shape.");
          }
        }
      }
    }
    return response;
  }

  async getMarketRankingStocks(symbols: readonly string[]): Promise<TossReadonlyResponse> {
    if (!this.configured || symbols.length < 1 || symbols.length > 20 || symbols.some((symbol) => !/^[0-9A-Z]{6}$/.test(symbol))) {
      throw new TossOpenApiError("Toss ranking metadata request is outside the fixed read-only profile.");
    }
    const response = await this.getMarketContextResult("ranking metadata", "/api/v1/stocks", { symbols: symbols.join(",") });
    const rows = objectList(response.result, STOCK_FIELDS);
    for (const row of rows) {
      if (!hasScalarValues(row, ["koreanMarketDetail"])) throw new TossOpenApiError("Toss ranking metadata included nested content.");
      const detail = row.koreanMarketDetail;
      if (detail === undefined || detail === null) continue;
      if (!isRecord(detail) || !hasOnlyKeys(detail, ["liquidationTrading", "nxtSupported", "krxTradingSuspended", "nxtTradingSuspended"]) ||
        !hasScalarValues(detail)) throw new TossOpenApiError("Toss Korean market metadata had an unexpected shape.");
    }
    return response;
  }

  private async getMarketContextResult(action: string, path: string, params: Record<string, string>): Promise<TossReadonlyResponse> {
    if (!this.configured) throw new TossOpenApiError("Toss market-context request is not configured.");
    const url = new URL(path, TOSS_OPENAPI_BASE_URL);
    for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
    const response = await this.getWithToken(action, url);
    return { result: response.payload.result, rateLimit: response.rateLimit };
  }

  private async getWithToken(action: string, url: URL, captureProviderCode = false): Promise<{ payload: TossPayload; rateLimit: Record<string, string> }> {
    const failedToken = await this.getToken(captureProviderCode);
    try {
      return await this.get(url, failedToken.accessToken, action, captureProviderCode);
    } catch (error) {
      if (!(error instanceof TossOpenApiError) || error.statusCode !== 401) throw error;
      let retryToken = this.token;
      if (retryToken === failedToken) {
        if (this.automaticReissueUsed) throw new TossOpenApiError("Toss automatic token reissue budget is exhausted.", 401);
        this.automaticReissueUsed = true;
        this.token = null;
        retryToken = null;
      }
      retryToken ??= await this.getToken(captureProviderCode);
      return this.get(url, retryToken.accessToken, action, captureProviderCode);
    }
  }

  private async getToken(captureProviderCode = false): Promise<TossToken> {
    if (this.token && this.token.expiresAt - this.now() > 30_000) return this.token;
    if (this.tokenRequest) return this.tokenRequest;
    this.tokenRequest = (async () => {
      const body = new URLSearchParams({
        grant_type: "client_credentials",
        client_id: this.config.clientId ?? "",
        client_secret: this.config.clientSecret ?? "",
      });
      const { payload } = await this.request(new URL("/oauth2/token", TOSS_OPENAPI_BASE_URL), {
        method: "POST",
        headers: { accept: "application/json", "content-type": "application/x-www-form-urlencoded" },
        body,
      }, "token request", captureProviderCode);
      if (typeof payload.access_token !== "string" || !payload.access_token ||
        typeof payload.token_type !== "string" || payload.token_type.toLowerCase() !== "bearer" ||
        !Number.isSafeInteger(payload.expires_in) || Number(payload.expires_in) <= 0) {
        throw new TossOpenApiError("Toss token response had an unexpected shape.");
      }
      const token = { accessToken: payload.access_token, expiresAt: this.now() + Number(payload.expires_in) * 1000 };
      this.token = token;
      return token;
    })();
    try {
      return await this.tokenRequest;
    } finally {
      this.tokenRequest = null;
    }
  }

  private async get(url: URL, accessToken: string, action: string, captureProviderCode = false) {
    return this.request(url, {
      method: "GET",
      headers: { accept: "application/json", authorization: `Bearer ${accessToken}` },
    }, action, captureProviderCode);
  }

  private async request(url: URL, init: RequestInit, action: string, captureProviderCode = false): Promise<{ payload: TossPayload; rateLimit: Record<string, string> }> {
    if (url.origin !== TOSS_OPENAPI_BASE_URL) throw new TossOpenApiError("Toss request origin is outside the official allowlist.");
    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        ...init,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(this.config.timeoutSeconds * 1000),
      });
    } catch (error) {
      const reason = error instanceof Error && error.name === "TimeoutError" ? "provider_timeout" : "provider_unavailable";
      throw new TossOpenApiError(`Toss ${action} failed (transport error).`, undefined, undefined, undefined, reason);
    }
    const limits = rateLimit(response.headers);
    if (!response.ok) {
      const providerCode = captureProviderCode ? await safeProviderCode(response, [this.config.clientId, this.config.clientSecret, this.token?.accessToken]) : undefined;
      if (!captureProviderCode) await response.body?.cancel().catch(() => undefined);
      throw new TossOpenApiError(`Toss ${action} failed (HTTP ${response.status}).`, response.status, limits.retry_after, providerCode);
    }
    return { payload: await readBoundedJson(response, action), rateLimit: limits };
  }
}

async function safeProviderCode(response: Response, privateValues: (string | null | undefined)[]): Promise<string | undefined> {
  const reader = response.body?.getReader();
  if (!reader) return undefined;
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > 8192) {
        await reader.cancel().catch(() => undefined);
        return undefined;
      }
      chunks.push(value);
    }
  } catch {
    return undefined;
  } finally {
    reader.releaseLock();
  }
  try {
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const payload: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!isRecord(payload)) return undefined;
    const nestedError = payload.error;
    const rawCode = typeof payload.code === "string" ? payload.code : typeof nestedError === "string" ? nestedError :
      isRecord(nestedError) && typeof nestedError.code === "string" ? nestedError.code : undefined;
    if (!rawCode || !/^[A-Za-z0-9._-]{1,100}$/.test(rawCode) || privateValues.includes(rawCode)) return undefined;
    return rawCode;
  } catch {
    return undefined;
  }
}

function isOffsetDateTime(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false;
  return Number.isFinite(Date.parse(value));
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + "T00:00:00.000Z");
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
