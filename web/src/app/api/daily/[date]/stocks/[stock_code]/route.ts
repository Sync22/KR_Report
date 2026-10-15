import { isBusinessDate } from "@/domain/daily";
import { getStockDetailSnapshot } from "@/server/stock-detail";
import { cachedStoredJsonResponse } from "../../../../../../server/stored-response-cache.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ date: string; stock_code: string }> };

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

function invalidStockCode(): Response {
  return new Response("invalid stock code", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function GET(request: Request, { params }: RouteContext): Promise<Response> {
  const { date, stock_code: stockCode } = await params;
  if (!isBusinessDate(date)) return invalidDate();
  if (!/^\d{6}$/.test(stockCode)) return invalidStockCode();
  try {
    return cachedStoredJsonResponse(request, [], () => getStockDetailSnapshot(date, stockCode));
  } catch {
    return new Response("stock detail unavailable", {
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
