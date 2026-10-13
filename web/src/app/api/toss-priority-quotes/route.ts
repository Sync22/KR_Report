import { parseTossPriorityQuotesDate, tossPriorityQuotesService } from "../../../server/toss-priority-quotes.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidQuery(): Response {
  return new Response("invalid date or query", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function GET(request: Request): Promise<Response> {
  const date = parseTossPriorityQuotesDate(request);
  if (!date) return invalidQuery();
  try {
    const result = await tossPriorityQuotesService.getQuotes(date);
    return Response.json(result.payload, { status: result.status, headers: { "cache-control": "no-store" } });
  } catch {
    return Response.json({
      surface: "web-view-toss-priority-quotes",
      read_only: true,
      configured: tossPriorityQuotesService.configured,
      live_fetch: false,
      writes_db: false,
      sends_telegram: false,
      registers_scheduler: false,
      affects_ordering: false,
      priority_date: date,
      symbols: [],
      quotes: [],
      reason: "stored_data_unavailable",
    }, { status: 503, headers: { "cache-control": "no-store" } });
  }
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}

export function HEAD(): Response {
  return methodNotAllowed();
}
