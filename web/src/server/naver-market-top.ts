import "server-only";

export type NaverMarket = "KOSPI" | "KOSDAQ";

export type NaverMarketTopStock = {
  market: NaverMarket;
  sort_type: string | null;
  stock_code: string;
  stock_name: string | null;
  stock_end_type: string | null;
  current_price: number | null;
  change_price: number | null;
  change_percent: number | null;
  trade_amount: number | null;
  trade_volume: number | null;
  market_status: string | null;
  trade_time: string | null;
};

const NAVER_ORIGIN = "https://m.stock.naver.com";
const MAX_RESPONSE_BYTES = 256 * 1024;
const REQUEST_TIMEOUT_MS = 8_000;

export class NaverMarketTopError extends Error {
  readonly code: "invalid_request" | "invalid_response" | "response_too_large" | "upstream_unavailable";

  constructor(code: NaverMarketTopError["code"]) {
    super(code);
    this.name = "NaverMarketTopError";
    this.code = code;
  }
}

function textOrNull(value: unknown): string | null {
  const text = value == null ? "" : String(value).trim();
  return text || null;
}

function parseInteger(value: unknown): number | null {
  const text = String(value || "").trim().replaceAll(",", "");
  if (!/^[+-]?\d+$/.test(text)) return null;
  const parsed = Number(text);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function parseNumber(value: unknown): number | null {
  const text = String(value || "").trim().replaceAll(",", "");
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text)) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseMarketTime(value: unknown): string | null {
  const text = textOrNull(value);
  if (!text) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/.exec(text) ??
    /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(text);
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match;
  const parsed = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second)));
  if (parsed.getUTCFullYear() !== Number(year) || parsed.getUTCMonth() + 1 !== Number(month) ||
    parsed.getUTCDate() !== Number(day) || parsed.getUTCHours() !== Number(hour) ||
    parsed.getUTCMinutes() !== Number(minute) || parsed.getUTCSeconds() !== Number(second)) return null;
  return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
}

async function readBoundedText(response: Response): Promise<string> {
  const contentLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_RESPONSE_BYTES) {
    await response.body?.cancel().catch(() => undefined);
    throw new NaverMarketTopError("response_too_large");
  }
  if (!response.body) throw new NaverMarketTopError("invalid_response");

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_RESPONSE_BYTES) {
        await reader.cancel().catch(() => undefined);
        throw new NaverMarketTopError("response_too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

export async function fetchNaverMarketTopStocks(
  market: NaverMarket,
  options: { page: number; pageSize: number; fetchImpl?: typeof fetch },
): Promise<NaverMarketTopStock[]> {
  if ((market !== "KOSPI" && market !== "KOSDAQ") || !Number.isInteger(options.page) ||
    options.page < 1 || options.page > 5 || options.pageSize !== 20) {
    throw new NaverMarketTopError("invalid_request");
  }

  const url = new URL(`/api/stocks/priceTop/${market}`, NAVER_ORIGIN);
  url.searchParams.set("page", String(options.page));
  url.searchParams.set("pageSize", String(options.pageSize));
  let response: Response;
  try {
    response = await (options.fetchImpl ?? fetch)(url, {
      method: "GET",
      headers: { accept: "application/json", "user-agent": "stock-monitor/0.1" },
      redirect: "error",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new NaverMarketTopError("upstream_unavailable");
  }
  if (!response.ok) {
    await response.body?.cancel().catch(() => undefined);
    throw new NaverMarketTopError("upstream_unavailable");
  }

  let payload: unknown;
  try {
    payload = JSON.parse(await readBoundedText(response));
  } catch (error) {
    if (error instanceof NaverMarketTopError) throw error;
    throw new NaverMarketTopError("invalid_response");
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload) ||
    !Array.isArray((payload as Record<string, unknown>).stocks)) {
    throw new NaverMarketTopError("invalid_response");
  }

  const source = payload as Record<string, unknown>;
  const sortType = textOrNull(source.stockListSortType);
  return (source.stocks as unknown[]).flatMap((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row)) return [];
    const item = row as Record<string, unknown>;
    const stockCode = textOrNull(item.itemCode);
    if (!stockCode) return [];
    return [{
      market,
      sort_type: sortType,
      stock_code: stockCode,
      stock_name: textOrNull(item.stockName),
      stock_end_type: textOrNull(item.stockEndType),
      current_price: parseInteger(item.closePriceRaw || item.closePrice),
      change_price: parseInteger(item.compareToPreviousClosePriceRaw || item.compareToPreviousClosePrice),
      change_percent: parseNumber(item.fluctuationsRatio),
      trade_amount: parseInteger(item.accumulatedTradingValueRaw || item.accumulatedTradingValue),
      trade_volume: parseInteger(item.accumulatedTradingVolumeRaw || item.accumulatedTradingVolume),
      market_status: textOrNull(item.marketStatus),
      trade_time: parseMarketTime(item.localTradedAt),
    }];
  });
}
