import { isBusinessDate } from "../../../domain/daily.ts";
import { priorityIndicatorsService } from "../../../server/priority-indicators.ts";

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
  return new Response("invalid date or query", {
    status: 400,
    headers: { ...NO_STORE, "content-type": "text/plain; charset=utf-8" },
  });
}

export async function GET(request: Request): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed();
  const query = new URL(request.url).searchParams;
  const date = query.get("date");
  if (query.size !== 1 || query.getAll("date").length !== 1 || !date || !isBusinessDate(date)) return invalidQuery();
  const result = await priorityIndicatorsService.getIndicators(date);
  return Response.json(result.payload, { status: result.status, headers: NO_STORE });
}

export function POST(): Response {
  return methodNotAllowed();
}

export function HEAD(): Response {
  return methodNotAllowed();
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}
