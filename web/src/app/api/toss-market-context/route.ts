import { isBusinessDate } from "../../../domain/daily.ts";
import { tossMarketContextService } from "../../../server/toss-market-context.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { ...NO_STORE, allow: "GET", "content-type": "text/plain; charset=utf-8" },
  });
}

function invalidDate(): Response {
  return new Response("invalid date", {
    status: 400,
    headers: { ...NO_STORE, "content-type": "text/plain; charset=utf-8" },
  });
}

export async function GET(request: Request): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed();
  const query = new URL(request.url).searchParams;
  const date = query.get("date");
  if (query.size !== 1 || query.getAll("date").length !== 1 || !date || !isBusinessDate(date)) return invalidDate();
  const result = await tossMarketContextService.getMarketContext(date);
  return Response.json(result.payload, { status: result.status, headers: NO_STORE });
}

export function HEAD(): Response {
  return methodNotAllowed();
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}
