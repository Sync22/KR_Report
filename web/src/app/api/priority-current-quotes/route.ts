import { isBusinessDate } from "../../../domain/daily.ts";
import { getPriorityCurrentQuotesSnapshot } from "../../../server/priority-current-quotes.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidDate(): Response {
  return new Response("invalid date or query", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function GET(request: Request): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed();
  const query = new URL(request.url).searchParams;
  const date = query.get("date");
  if (query.size !== 1 || query.getAll("date").length !== 1 || !date || !isBusinessDate(date)) return invalidDate();

  try {
    const result = await getPriorityCurrentQuotesSnapshot(date);
    return Response.json(result.payload, {
      status: result.status,
      headers: { "cache-control": "no-store" },
    });
  } catch {
    return new Response("priority current quotes unavailable", {
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
