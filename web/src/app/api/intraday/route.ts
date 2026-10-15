import { isBusinessDate } from "@/domain/daily";
import { getIntradaySnapshot } from "@/server/intraday";
import { cachedStoredJsonResponse } from "../../../server/stored-response-cache.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export function GET(request: Request): Response {
  const businessDate = new URL(request.url).searchParams.get("date") ?? "";
  if (!isBusinessDate(businessDate)) {
    return new Response("invalid date", {
      status: 400,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
  try {
    return cachedStoredJsonResponse(request, [businessDate], () => getIntradaySnapshot(businessDate));
  } catch {
    return new Response("Stored intraday summary unavailable", {
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
