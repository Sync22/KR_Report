import { isBusinessDate } from "../../../domain/daily.ts";
import { tossPriorityDailyCandlesService } from "../../../server/toss-priority-daily-candles.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { ...NO_STORE, allow: "GET", "content-type": "text/plain; charset=utf-8" },
  });
}

function invalidQuery(): Response {
  return new Response("invalid date or days", {
    status: 400,
    headers: { ...NO_STORE, "content-type": "text/plain; charset=utf-8" },
  });
}

function firstNonBlank(searchParams: URLSearchParams, name: string): string | null {
  return searchParams.getAll(name).find((value) => value !== "") ?? null;
}

function parseDays(raw: string | null): { kind: "valid"; count: 30 | 90 | 180 } | { kind: "invalid" } | { kind: "unsupported" } {
  if (raw === null) return { kind: "valid", count: 90 };
  const value = raw.trim();
  if (!/^[+-]?(?:\d(?:_?\d)*)$/.test(value)) return { kind: "invalid" };
  const parsed = Number(value.replaceAll("_", ""));
  if (parsed === 30 || parsed === 90 || parsed === 180) return { kind: "valid", count: parsed };
  return { kind: "unsupported" };
}

function unsupportedCount(): Response {
  return Response.json({
    surface: "web-view-toss-priority-daily-candles",
    read_only: true,
    writes_db: false,
    reason: "unsupported_candle_count",
  }, { status: 400, headers: NO_STORE });
}

export async function GET(request: Request): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed();
  const query = new URL(request.url).searchParams;
  const date = firstNonBlank(query, "date");
  const count = parseDays(firstNonBlank(query, "days"));
  if (!date || !isBusinessDate(date) || count.kind === "invalid") return invalidQuery();
  if (count.kind === "unsupported") return unsupportedCount();

  const result = await tossPriorityDailyCandlesService.getCandles(date, count.count);
  return Response.json(result.payload, { status: result.status, headers: NO_STORE });
}

export function HEAD(): Response {
  return methodNotAllowed();
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}
