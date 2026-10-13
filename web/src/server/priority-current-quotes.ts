import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const NAVER_QUOTE_ORIGIN = "https://stock.naver.com";
const NAVER_QUOTE_TIMEOUT_MS = 8_000;
const NAVER_QUOTE_MAX_RESPONSE_BYTES = 256 * 1024;

export type NaverQuoteSnapshot = {
  stock_code: string;
  stock_name: string | null;
  sector_code: string | null;
  sector_name: string | null;
  current_price: number | null;
  market_status: string | null;
  trade_time: string | null;
  prev_close_price: number | null;
  change_price: number | null;
  change_percent: number | null;
  trade_amount: number | null;
  trade_volume: number | null;
};

type QuoteItem = NaverQuoteSnapshot;

function latestBusinessDate(database: DatabaseSync): string | null {
  const row = database.prepare(`
    SELECT MAX(business_date) AS latest_business_date
    FROM (
      SELECT business_date FROM reports
      UNION ALL
      SELECT business_date FROM daily_stock_summaries
    )
  `).get() as { latest_business_date: unknown } | undefined;
  if (!row || row.latest_business_date === null) return null;
  if (typeof row.latest_business_date !== "string" || !isBusinessDate(row.latest_business_date)) {
    throw new Error("Invalid stored latest business date");
  }
  return row.latest_business_date;
}

function dateTimeIso(value: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "00";
  const milliseconds = value.getUTCMilliseconds();
  const offsetMinutes = Math.round((Date.UTC(
    Number(part("year")), Number(part("month")) - 1, Number(part("day")),
    Number(part("hour")), Number(part("minute")), Number(part("second")), milliseconds,
  ) - value.getTime()) / 60_000);
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const offset = Math.abs(offsetMinutes);
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}:${part("second")}.${String(milliseconds).padStart(3, "0")}000${sign}${String(Math.floor(offset / 60)).padStart(2, "0")}:${String(offset % 60).padStart(2, "0")}`;
}

function providerText(value: unknown): string {
  return String(value || "").trim();
}

function providerInteger(value: unknown): number | null {
  const text = providerText(value).replaceAll(",", "");
  if (!/^[+-]?\d+$/.test(text)) return null;
  const parsed = Number(text);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function providerFloat(value: unknown): number | null {
  const text = providerText(value).replaceAll(",", "");
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text)) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function providerTradeTime(value: unknown): string | null {
  const raw = providerText(value);
  const match = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(raw);
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match;
  const parsed = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second)));
  if (parsed.getUTCFullYear() !== Number(year) || parsed.getUTCMonth() !== Number(month) - 1 ||
    parsed.getUTCDate() !== Number(day) || parsed.getUTCHours() !== Number(hour) ||
    parsed.getUTCMinutes() !== Number(minute) || parsed.getUTCSeconds() !== Number(second)) return null;
  return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
}

async function fetchQuote(stockCode: string): Promise<QuoteItem> {
  const url = `${NAVER_QUOTE_ORIGIN}/api/domestic/detail/${stockCode}/detail?codeType=KRX`;
  const response = await fetch(url, {
    headers: { "User-Agent": "stock-monitor/0.1" },
    signal: AbortSignal.timeout(NAVER_QUOTE_TIMEOUT_MS),
    cache: "no-store",
    redirect: "error",
  });
  if (!response.ok) throw new Error("Naver quote request failed");
  const length = Number(response.headers.get("content-length"));
  if (Number.isSafeInteger(length) && length > NAVER_QUOTE_MAX_RESPONSE_BYTES) {
    await response.body?.cancel().catch(() => {});
    throw new Error("Naver quote response exceeds the allowed size");
  }
  if (!response.body) throw new Error("Naver quote response body is missing");
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let byteLength = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      byteLength += value.byteLength;
      if (byteLength > NAVER_QUOTE_MAX_RESPONSE_BYTES) {
        await reader.cancel();
        throw new Error("Naver quote response exceeds the allowed size");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(byteLength);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const payload: unknown = JSON.parse(new TextDecoder().decode(bytes));
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error("Naver quote response shape is invalid");
  const item = payload as Record<string, unknown>;
  return {
    stock_code: stockCode,
    stock_name: providerText(item.itemname) || null,
    sector_code: providerText(item.upjongCode) || null,
    sector_name: providerText(item.upJongName) || null,
    current_price: providerInteger(item.nowPrice),
    market_status: providerText(item.marketStatus) || null,
    trade_time: providerTradeTime(item.tradeTime),
    prev_close_price: providerInteger(item.prevClosePrice),
    change_price: providerInteger(item.prevChangePrice),
    change_percent: providerFloat(item.prevChangeRate),
    trade_amount: providerInteger(item.tradeAmount),
    trade_volume: providerInteger(item.tradeVolume),
  };
}

export async function fetchNaverQuoteSnapshot(stockCode: string): Promise<NaverQuoteSnapshot> {
  if (!/^\d{6}$/.test(stockCode)) throw new Error("Naver quote symbol is invalid");
  return fetchQuote(stockCode);
}

export async function getPriorityCurrentQuotesSnapshot(businessDate: string): Promise<{ status: 200 | 409; payload: Record<string, unknown> }> {
  const now = new Date();
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  const selection = withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const latestDate = latestBusinessDate(database);
      if (latestDate && businessDate !== latestDate) return { latestBusinessDate: latestDate, codes: null };
      const candidates = buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, 2, now);
      const codes = candidates.rows
        .filter((row) => row.selected)
        .slice(0, 2)
        .map((row) => row.stock_code.trim())
        .filter((code) => /^\d{6}$/.test(code));
      return { latestBusinessDate: latestDate, codes };
    } finally {
      database.exec("ROLLBACK");
    }
  });

  if (selection.latestBusinessDate && businessDate !== selection.latestBusinessDate) return {
    status: 409,
    payload: {
      surface: "web-view-priority-current-quotes",
      read_only: true,
      live_fetch: false,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      priority_date: businessDate,
      latest_business_date: selection.latestBusinessDate,
      items: [],
      reason: "latest_business_date_only",
    },
  };

  const checkedAt = dateTimeIso(new Date(), timezone);
  const items: QuoteItem[] = [];
  const errors: string[] = [];
  for (const stockCode of selection.codes ?? []) {
    try {
      items.push(await fetchQuote(stockCode));
    } catch {
      errors.push(stockCode);
    }
  }
  return {
    status: 200,
    payload: {
      surface: "web-view-priority-current-quotes",
      read_only: true,
      live_fetch: true,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      priority_date: businessDate,
      latest_business_date: selection.latestBusinessDate,
      checked_at: checkedAt,
      items: items.map((item) => ({
        stock_code: item.stock_code,
        stock_name: item.stock_name,
        current_price: item.current_price,
        change_percent: item.change_percent,
        trade_amount: item.trade_amount,
        market_status: item.market_status,
        trade_time: item.trade_time,
      })),
      errors,
      derived_from: "web_view_candidate_evidence_top_2",
    },
  };
}
