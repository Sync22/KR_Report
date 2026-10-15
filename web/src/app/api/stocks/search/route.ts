import { isBusinessDate } from "@/domain/daily";
import { getStockSearchSnapshot, parseStockSearchLimit } from "@/server/stock-search";
import { cachedStoredJsonResponse } from "../../../../server/stored-response-cache.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export function GET(request: Request): Response {
  const params = new URL(request.url).searchParams;
  const businessDate = params.get("date") ?? "";
  if (!isBusinessDate(businessDate)) {
    return new Response("invalid date", {
      status: 400,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
  try {
    const limit = parseStockSearchLimit(params.get("limit"));
    const query = params.get("q") ?? "";
    return cachedStoredJsonResponse(request, [businessDate, query.trim(), limit], () => getStockSearchSnapshot(businessDate, query, limit));
  } catch {
    return new Response("Stored stock search unavailable", {
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
