import { isBusinessDate } from "../../../../domain/daily.ts";
import { isReportFocusCandidate } from "../../../../domain/chart-alerts.ts";
import { getCandidateEvidenceSnapshot } from "../../../../server/candidate-evidence.ts";
import { isChartLabLocalRequest } from "../../../../server/chart-lab-local.ts";
import { chartAlertMonitorService } from "../../../../server/chart-alert-monitor.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };
const MAX_BODY_BYTES = 16 * 1024;

export async function GET(request: Request): Promise<Response> {
  if (!isChartLabLocalRequest(request)) return forbidden();
  const query = new URL(request.url).searchParams;
  const businessDate = query.get("date") ?? "";
  if (query.size !== 1 || !isBusinessDate(businessDate)) return Response.json({ error: "invalid_date" }, { status: 400, headers: NO_STORE });
  try {
    const [status, snapshot] = await Promise.all([
      chartAlertMonitorService.getStatus(),
      Promise.resolve(getCandidateEvidenceSnapshot(businessDate, 20)),
    ]);
    return Response.json({
      ...status,
      candidates: snapshot.rows.filter((row) => isReportFocusCandidate(row, businessDate)).map((row) => ({
        report_business_date: row.business_date,
        stock_code: row.stock_code,
        stock_name: row.stock_name,
        report_count: row.report_summary.report_count,
        report_reason: "리포트 집중" as const,
      })),
    }, { headers: NO_STORE });
  } catch {
    return Response.json({ error: "chart_alerts_unavailable" }, { status: 503, headers: NO_STORE });
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
    if (body.action === "add" && hasOnlyKeys(body, ["action", "report_business_date", "stock_code"]) &&
      typeof body.report_business_date === "string" && isBusinessDate(body.report_business_date) &&
      typeof body.stock_code === "string" && /^\d{6}$/.test(body.stock_code)) {
      const snapshot = getCandidateEvidenceSnapshot(body.report_business_date, 20);
      const candidate = snapshot.rows.find((row) => row.stock_code === body.stock_code && isReportFocusCandidate(row, body.report_business_date as string));
      if (!candidate) return Response.json({ error: "report_focus_not_found" }, { status: 409, headers: NO_STORE });
      const state = await chartAlertMonitorService.addWatch({
        report_business_date: candidate.business_date,
        stock_code: candidate.stock_code,
        stock_name: candidate.stock_name,
        report_count: candidate.report_summary.report_count,
        report_reason: "리포트 집중",
      });
      return Response.json({ state }, { headers: NO_STORE });
    }
    if (body.action === "remove" && hasOnlyKeys(body, ["action", "watch_id"]) &&
      typeof body.watch_id === "string" && /^\d{4}-\d{2}-\d{2}-\d{6}$/.test(body.watch_id)) {
      return Response.json({ state: await chartAlertMonitorService.removeWatch(body.watch_id) }, { headers: NO_STORE });
    }
    if (body.action === "start" && hasOnlyKeys(body, ["action"])) {
      return Response.json({ state: await chartAlertMonitorService.start() }, { headers: NO_STORE });
    }
    if (body.action === "pause" && hasOnlyKeys(body, ["action"])) {
      return Response.json({ state: await chartAlertMonitorService.pause() }, { headers: NO_STORE });
    }
    return Response.json({ error: "invalid_action" }, { status: 400, headers: NO_STORE });
  } catch (error) {
    const message = error instanceof TypeError ? error.message : "";
    const status = ["invalid-chart-alert-watch", "chart-alert-watch-limit", "chart-alert-watches-required", "chart-alert-monitor-owned-elsewhere", "chart-alert-provider-not-configured", "invalid-chart-alert-state"].includes(message) ? 409 : 503;
    return Response.json({ error: status === 409 ? message : "chart_alerts_unavailable" }, { status, headers: NO_STORE });
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
      if (total > MAX_BODY_BYTES) { await reader.cancel(); return { status: 413, error: "request_too_large" }; }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return { status: 200, value: JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) };
  } catch { return { status: 400, error: "invalid_json" }; }
  finally { reader.releaseLock(); }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function hasOnlyKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

function forbidden(): Response {
  return Response.json({ error: "local_chart_lab_only" }, { status: 403, headers: NO_STORE });
}

function methodNotAllowed(): Response {
  return new Response("method not allowed", { status: 405, headers: { ...NO_STORE, allow: "GET, POST", "content-type": "text/plain; charset=utf-8" } });
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
