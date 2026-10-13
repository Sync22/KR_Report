export const dynamic = "force-dynamic";

export function GET(): Response {
  return new Response("ok", { headers: {
    "content-type": "text/plain; charset=utf-8",
    "cache-control": "no-store",
    "x-stock-monitor-service": "next-web-view",
  } });
}

export function OPTIONS(): Response {
  return new Response("method not allowed", { status: 405, headers: { allow: "GET", "content-type": "text/plain; charset=utf-8" } });
}
