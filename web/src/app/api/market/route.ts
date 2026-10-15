import { getMarketSnapshot } from "@/server/market-snapshot";
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
  try {
    return cachedStoredJsonResponse(request, [], () => getMarketSnapshot());
  } catch {
    return new Response("Stored market snapshot unavailable", {
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
