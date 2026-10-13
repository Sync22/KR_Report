import { isBusinessDate } from "../../../../domain/daily.ts";
import { getBacktestObservationSnapshot } from "../../../../server/backtest-observation.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidDate(): Response {
  return new Response("invalid date", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function queryInt(search: URLSearchParams, name: string, fallback: number, minimum: number, maximum: number): number {
  const raw = search.getAll(name).find((value) => value !== "");
  if (raw === undefined || !/^[+-]?\d+(?:_\d+)*$/.test(raw.trim())) return fallback;
  try {
    const value = BigInt(raw.trim().replaceAll("_", ""));
    if (value < BigInt(minimum)) return minimum;
    if (value > BigInt(maximum)) return maximum;
    return Number(value);
  } catch {
    return fallback;
  }
}

export function GET(request: Request): Response {
  if (request.method !== "GET") return methodNotAllowed();
  const search = new URL(request.url).searchParams;
  const businessDate = search.getAll("date").find((value) => value !== "") ?? "";
  if (!isBusinessDate(businessDate)) return invalidDate();
  const limit = queryInt(search, "limit", 20, 1, 100);
  const mentionThreshold = queryInt(search, "mention_threshold", 2, 1, 20);
  try {
    return Response.json(getBacktestObservationSnapshot(businessDate, limit, mentionThreshold), {
      headers: { "cache-control": "no-store" },
    });
  } catch {
    return new Response("backtest observation unavailable", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function POST(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
