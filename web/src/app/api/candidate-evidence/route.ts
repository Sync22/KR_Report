import { isBusinessDate } from "../../../domain/daily.ts";
import { getCandidateEvidenceSnapshot, parseCandidateEvidenceLimit } from "../../../server/candidate-evidence.ts";
import { cachedStoredJsonResponse } from "../../../server/stored-response-cache.ts";

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

export function GET(request: Request): Response {
  const query = new URL(request.url).searchParams;
  const businessDate = query.get("date") ?? "";
  if (!isBusinessDate(businessDate)) return invalidDate();
  try {
    const limit = parseCandidateEvidenceLimit(query.get("limit"));
    return cachedStoredJsonResponse(request, [businessDate, limit], () => getCandidateEvidenceSnapshot(businessDate, limit));
  } catch {
    return new Response("candidate evidence unavailable", {
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
