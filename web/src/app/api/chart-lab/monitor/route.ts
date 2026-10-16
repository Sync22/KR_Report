import { isChartLabLocalRequest } from "../../../../server/chart-lab-local.ts";
import { chartLabMonitorService } from "../../../../server/chart-lab-monitor.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };
const MAX_BODY_BYTES = 16 * 1024;

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { ...NO_STORE, allow: "GET, POST", "content-type": "text/plain; charset=utf-8" },
  });
}

function forbidden(): Response {
  return Response.json({ error: "local_chart_lab_only" }, { status: 403, headers: NO_STORE });
}

export async function GET(request: Request): Promise<Response> {
  if (!isChartLabLocalRequest(request)) return forbidden();
  if (new URL(request.url).searchParams.size) return Response.json({ error: "invalid_query" }, { status: 400, headers: NO_STORE });
  try {
    return Response.json(await chartLabMonitorService.getStatus(), { headers: NO_STORE });
  } catch {
    return Response.json({ error: "monitor_state_unavailable" }, { status: 503, headers: NO_STORE });
  }
}

export async function POST(request: Request): Promise<Response> {
  if (!isChartLabLocalRequest(request, true)) return forbidden();
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) {
    return Response.json({ error: "json_required" }, { status: 415, headers: NO_STORE });
  }
  const length = Number(request.headers.get("content-length"));
  if (Number.isFinite(length) && length > MAX_BODY_BYTES) return Response.json({ error: "request_too_large" }, { status: 413, headers: NO_STORE });
  const parsed = await boundedJson(request);
  if (parsed.status !== 200) return Response.json({ error: parsed.error }, { status: parsed.status, headers: NO_STORE });
  const body = asRecord(parsed.value);
  try {
    if (body.action === "configure" && hasOnlyKeys(body, ["action", "symbols"])) {
      const symbols = parseSymbols(body.symbols);
      if (!symbols) return Response.json({ error: "invalid_symbols" }, { status: 400, headers: NO_STORE });
      return Response.json({ state: await chartLabMonitorService.configure(symbols) }, { headers: NO_STORE });
    }
    if (body.action === "start" && hasOnlyKeys(body, ["action"])) {
      return Response.json({ state: await chartLabMonitorService.start() }, { headers: NO_STORE });
    }
    if (body.action === "pause" && hasOnlyKeys(body, ["action"])) {
      return Response.json({ state: await chartLabMonitorService.pause() }, { headers: NO_STORE });
    }
    return Response.json({ error: "invalid_action" }, { status: 400, headers: NO_STORE });
  } catch (error) {
    const message = error instanceof TypeError ? error.message : "";
    const status = message === "monitor-symbols-required" || message === "invalid-chart-lab-state" ? 400 : 503;
    return Response.json({ error: status === 400 ? "invalid_monitor_state" : "monitor_state_unavailable" }, { status, headers: NO_STORE });
  }
}

async function boundedJson(request: Request): Promise<{ status: 200; value: unknown } | { status: 400 | 413; error: string }> {
  if (!request.body) return { status: 400, error: "invalid_json" };
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_BODY_BYTES) {
        await reader.cancel();
        return { status: 413, error: "request_too_large" };
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return { status: 200, value: JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) };
  } catch {
    return { status: 400, error: "invalid_json" };
  } finally {
    reader.releaseLock();
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function hasOnlyKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

function parseSymbols(value: unknown): Array<{ symbol: string; name: string; focus: boolean }> | null {
  if (!Array.isArray(value) || value.length > 20) return null;
  const result: Array<{ symbol: string; name: string; focus: boolean }> = [];
  for (const raw of value) {
    const item = asRecord(raw);
    if (!hasOnlyKeys(item, ["symbol", "name", "focus"]) || typeof item.symbol !== "string" ||
      typeof item.name !== "string" || typeof item.focus !== "boolean") return null;
    result.push({ symbol: item.symbol, name: item.name, focus: item.focus });
  }
  return result;
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
