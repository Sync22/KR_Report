import { getArchiveSnapshot, parseArchiveLimit } from "../../../server/archive.ts";

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
    const limit = parseArchiveLimit(new URL(request.url).searchParams.get("limit"));
    return Response.json(getArchiveSnapshot(limit), { headers: { "cache-control": "no-store" } });
  } catch {
    return new Response("Stored archive unavailable", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
}

export function HEAD(): Response {
  return methodNotAllowed();
}

export function OPTIONS(): Response {
  return methodNotAllowed();
}
