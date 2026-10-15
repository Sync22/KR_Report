import { isBusinessDate } from "@/domain/daily";
import { getDailySnapshot } from "@/server/daily-snapshot";
import { overlayDailyIntradayMarketTop } from "@/server/daily-market-commentary";
import { fetchNaverQuoteSnapshot } from "@/server/priority-current-quotes";
import { cachedStoredJsonResponse } from "../../../../server/stored-response-cache.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ date: string }> };

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8" },
  });
}

function invalidDate(): Response {
  return new Response("invalid date", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidQuery(): Response {
  return new Response("invalid query", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function GET(request: Request, { params }: RouteContext): Promise<Response> {
  const date = (await params).date;
  if (request.method !== "GET") return methodNotAllowed();
  if (!isBusinessDate(date)) return invalidDate();

  const query = new URL(request.url).searchParams;
  if (query.size === 0) {
    try {
      return cachedStoredJsonResponse(request, [], () => getDailySnapshot(date));
    } catch {
      return new Response("stored daily snapshot unavailable", {
        status: 500,
        headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
      });
    }
  }

  if (
    query.size === 3 &&
    query.getAll("intraday_market_top").length === 1 && query.get("intraday_market_top") === "1" &&
    query.getAll("market_top_limit").length === 1 && query.get("market_top_limit") === "100" &&
    query.getAll("market_top_page_size").length === 1 && query.get("market_top_page_size") === "20"
  ) {
    try {
      const snapshot = getDailySnapshot(date);
      const overlay = await overlayDailyIntradayMarketTop(snapshot, date, { fetchQuote: fetchNaverQuoteSnapshot });
      return Response.json(overlay, { headers: { "cache-control": "no-store" } });
    } catch {
      return new Response("daily market-top reference unavailable", {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
      });
    }
  }
  return invalidQuery();
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}

export function HEAD(): Response {
  return methodNotAllowed();
}
