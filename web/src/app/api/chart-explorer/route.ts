import { isBusinessDate } from "../../../domain/daily.ts";
import { isChartExplorerSymbol, isChartExplorerTimeframe } from "../../../domain/chart-explorer.ts";
import { chartExplorerService, invalidChartExplorerRequest } from "../../../server/chart-explorer.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { ...NO_STORE, allow: "GET", "content-type": "text/plain; charset=utf-8" },
  });
}

export async function GET(request: Request): Promise<Response> {
  if (request.method !== "GET") return methodNotAllowed();
  const query = new URL(request.url).searchParams;
  const date = query.get("date");
  const symbol = query.get("symbol");
  const timeframe = query.get("timeframe");
  const validShape = query.size === 3 && ["date", "symbol", "timeframe"].every((key) => query.getAll(key).length === 1);
  if (!validShape || !date || !isBusinessDate(date) || !symbol || !isChartExplorerSymbol(symbol) || !timeframe || !isChartExplorerTimeframe(timeframe)) {
    return Response.json(invalidChartExplorerRequest(date, symbol, isChartExplorerTimeframe(timeframe) ? timeframe : null), {
      status: 400,
      headers: NO_STORE,
    });
  }
  try {
    const result = await chartExplorerService.getChart(date, symbol, timeframe);
    return Response.json(result.payload, {
      status: result.status,
      headers: result.status === 429 ? { ...NO_STORE, "retry-after": "60" } : NO_STORE,
    });
  } catch {
    return Response.json(invalidChartExplorerRequest(date, symbol, timeframe), { status: 503, headers: NO_STORE });
  }
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function POST(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
