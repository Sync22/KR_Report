import { isBusinessDate } from "../../../../domain/daily.ts";
import { isChartExplorerSymbol, isChartExplorerTimeframe, type ChartExplorerTimeframe } from "../../../../domain/chart-explorer.ts";
import { buildChartLabAnalysis } from "../../../../domain/chart-lab/analysis.ts";
import type { ChartLabStrategy } from "../../../../domain/chart-lab/entry.ts";
import { isChartLabLocalRequest } from "../../../../server/chart-lab-local.ts";
import { chartExplorerService } from "../../../../server/chart-explorer.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };
const STRATEGIES = new Set<ChartLabStrategy>(["A", "B", "C", "F"]);
const ALLOWED_KEYS = new Set(["date", "symbol", "timeframe", "asOf", "selected", "mode", "maxAtr"]);

function invalidQuery(): Response {
  return Response.json({ error: "invalid_chart_lab_query" }, { status: 400, headers: NO_STORE });
}

function methodNotAllowed(): Response {
  return new Response("method not allowed", { status: 405, headers: { ...NO_STORE, allow: "GET", "content-type": "text/plain; charset=utf-8" } });
}

function parseSelected(value: string | null): ChartLabStrategy[] | null {
  if (value === null) return ["F"];
  const items = value.split(",");
  if (!items.length || items.length > 4 || items.some((item) => !STRATEGIES.has(item as ChartLabStrategy)) || new Set(items).size !== items.length) return null;
  return items as ChartLabStrategy[];
}

function parseMaxAtr(value: string | null): number | null {
  if (value === null) return 0.5;
  if (!/^(?:0\.[1-9]|[1-4](?:\.\d)?|5(?:\.0)?)$/.test(value)) return null;
  const parsed = Number(value);
  return parsed >= 0.1 && parsed <= 5 ? parsed : null;
}

export async function GET(request: Request): Promise<Response> {
  if (!isChartLabLocalRequest(request)) return Response.json({ error: "local_chart_lab_only" }, { status: 403, headers: NO_STORE });
  const query = new URL(request.url).searchParams;
  if (query.size < 3 || query.size > ALLOWED_KEYS.size || [...query.keys()].some((key) => !ALLOWED_KEYS.has(key)) ||
    [...query.keys()].some((key) => query.getAll(key).length !== 1)) return invalidQuery();
  const date = query.get("date"), symbol = query.get("symbol"), timeframe = query.get("timeframe");
  const selected = parseSelected(query.get("selected"));
  const mode = query.get("mode") ?? "all";
  const maxAtr = parseMaxAtr(query.get("maxAtr"));
  const asOf = query.get("asOf");
  if (!date || !isBusinessDate(date) || !symbol || !isChartExplorerSymbol(symbol) || !timeframe || !isChartExplorerTimeframe(timeframe) ||
    !selected || (mode !== "all" && mode !== "any") || maxAtr === null || (asOf !== null && (asOf.length > 40 || !Number.isFinite(Date.parse(asOf))))) return invalidQuery();

  try {
    const result = await chartExplorerService.getChart(date, symbol, timeframe as ChartExplorerTimeframe, { sessionContinuity: timeframe === "4h" });
    if (!result.payload.available) return Response.json({ chart: result.payload, analysis: null,
      session_continuity_status: result.sessionContinuityStatus ?? null, market_mapping_source: result.marketMappingSource ?? null },
    { status: result.status, headers: result.status === 429 ? { ...NO_STORE, "retry-after": "60" } : NO_STORE });
    const calculationBars = result.calculationBars ?? result.payload.bars;
    const asOfIndex = asOf === null ? calculationBars.length - 1 : calculationBars.findIndex((bar) => bar.time === asOf);
    if (asOfIndex < 0) return Response.json({ error: "basis_bar_unavailable" }, { status: 404, headers: NO_STORE });
    const analysis = buildChartLabAnalysis(calculationBars, { symbol, timeframe: timeframe as ChartExplorerTimeframe, asOfIndex, selected, mode, maxAtr });
    return Response.json({ surface: "chart-lab-local", read_only: true, writes_stock_monitor_db: false,
      session_continuity_status: result.sessionContinuityStatus ?? null, market_mapping_source: result.marketMappingSource ?? null,
      chart: result.payload, calculationBars, analysis }, { headers: NO_STORE });
  } catch {
    return Response.json({ error: "chart_lab_analysis_unavailable" }, { status: 503, headers: NO_STORE });
  }
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function POST(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
