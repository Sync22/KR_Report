import { isBusinessDate } from "@/domain/daily";
import { getRotationOverlaySnapshot, parseRotationOverlayLimit } from "@/server/rotation-overlay";

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
    const snapshot = getRotationOverlaySnapshot(businessDate, parseRotationOverlayLimit(query.get("limit")));
    const { path: _localPath, ...image } = snapshot.image;
    return Response.json({ ...snapshot, image }, { headers: { "cache-control": "no-store" } });
  } catch {
    return new Response("rotation data unavailable", {
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
