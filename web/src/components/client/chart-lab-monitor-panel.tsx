"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type WatchItem = { symbol: string; name: string };
type MonitorSymbol = WatchItem & { focus: boolean };
type MonitorEvent = Record<string, unknown>;
type MonitorState = { running: boolean; startedAt: string | null; lastPollAt: string | null; lastError: string | null; symbols: MonitorSymbol[]; events: MonitorEvent[] };
type Props = Readonly<{ watchItems: ReadonlyArray<WatchItem>; active: boolean }>;

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asMonitorState(value: unknown): MonitorState | null {
  const state = record(record(value).state);
  if (typeof state.running !== "boolean" || !Array.isArray(state.symbols) || !Array.isArray(state.events)) return null;
  return state as MonitorState;
}

function text(value: unknown, max = 140): string {
  return typeof value === "string" ? value.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max) : "자료 없음";
}

function dateTime(value: unknown): string {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return "시각 없음";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));
}

export default function ChartLabMonitorPanel({ watchItems, active }: Props) {
  const [state, setState] = useState<MonitorState | null>(null);
  const [selected, setSelected] = useState<MonitorSymbol[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/chart-lab/monitor", { method: "GET", cache: "no-store" });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error("로컬 감시 상태를 읽지 못했습니다.");
      const next = asMonitorState(payload);
      if (!next) throw new Error("감시 상태 응답 형식을 확인할 수 없습니다.");
      setState(next);
      setSelected(next.symbols);
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "감시 상태를 읽지 못했습니다."); }
  }, []);

  useEffect(() => { if (active) void loadStatus(); }, [active, loadStatus]);
  useEffect(() => {
    if (!active || !state?.running) return;
    const timer = window.setInterval(() => void loadStatus(), 10_000);
    return () => window.clearInterval(timer);
  }, [active, loadStatus, state?.running]);

  const candidates = useMemo(() => {
    const items = new Map<string, WatchItem>();
    for (const item of [...watchItems, ...selected]) items.set(item.symbol, item);
    return [...items.values()];
  }, [selected, watchItems]);

  async function post(action: "configure" | "start" | "pause") {
    setBusy(true); setError("");
    try {
      const body = action === "configure" ? { action, symbols: selected } : { action };
      const response = await fetch("/api/chart-lab/monitor", {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), cache: "no-store",
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(response.status === 400 ? "감시 종목 수와 집중 종목 수를 확인하세요." : "감시 설정을 저장하지 못했습니다.");
      const next = asMonitorState(payload);
      if (!next) throw new Error("감시 상태 응답 형식을 확인할 수 없습니다.");
      setState(next); setSelected(next.symbols);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "감시 설정을 저장하지 못했습니다."); }
    finally { setBusy(false); }
  }

  function toggleSelected(item: WatchItem, checked: boolean) {
    setSelected((current) => {
      if (checked) {
        if (current.length >= 20 || current.some((value) => value.symbol === item.symbol)) return current;
        return [...current, { ...item, focus: false }];
      }
      return current.filter((value) => value.symbol !== item.symbol);
    });
  }

  function toggleFocus(symbol: string, checked: boolean) {
    setSelected((current) => {
      if (checked && current.filter((item) => item.focus).length >= 3) return current;
      return current.map((item) => item.symbol === symbol ? { ...item, focus: checked } : item);
    });
  }

  return <section className="chart-subpanel chart-lab-monitor" aria-label="서버 패턴 감시">
    <div className="chart-subpanel-heading"><h3>로컬 패턴 감시</h3><span>{state?.running ? "실행 중" : "중지됨"}</span></div>
    <p className="chart-lab-monitor-note">관심 종목 중 최대 20개를 5분 간격으로 확인합니다. 집중 종목 최대 3개는 30초 간격이며, 시작을 눌러야 조회합니다.</p>
    {candidates.length ? <ul className="chart-lab-monitor-symbols">{candidates.map((item) => {
      const current = selected.find((entry) => entry.symbol === item.symbol);
      const focusedCount = selected.filter((entry) => entry.focus).length;
      return <li key={item.symbol}>
        <label><input type="checkbox" checked={!!current} disabled={busy || (!current && selected.length >= 20)} onChange={(event) => toggleSelected(item, event.target.checked)} /><span><strong>{item.name}</strong><small>{item.symbol}</small></span></label>
        <label className="chart-lab-focus"><input type="checkbox" aria-label={`${item.name} 집중 감시`} checked={current?.focus ?? false} disabled={busy || !current || (!current.focus && focusedCount >= 3)} onChange={(event) => toggleFocus(item.symbol, event.target.checked)} />집중</label>
      </li>;
    })}</ul> : <p className="data-note">먼저 관심 종목에 종목을 추가하세요.</p>}
    <div className="chart-lab-monitor-actions">
      <button className="action-secondary" type="button" disabled={busy || !selected.length} onClick={() => void post("configure")}>감시 목록 저장</button>
      {state?.running
        ? <button className="action-secondary" type="button" disabled={busy} onClick={() => void post("pause")}>감시 중지</button>
        : <button className="action-primary" type="button" disabled={busy || !state?.symbols.length} onClick={() => void post("start")}>감시 시작</button>}
      <button className="action-secondary" type="button" disabled={busy} onClick={() => void loadStatus()}>상태 새로고침</button>
    </div>
    <p className="chart-lab-monitor-status" aria-live="polite">마지막 조회 {dateTime(state?.lastPollAt)}{state?.lastError ? ` · 오류 ${text(state.lastError, 80)}` : ""}</p>
    {error ? <p className="chart-lab-error" role="alert">{error}</p> : null}
    <div className="chart-lab-event-list"><strong>저장 사건 {state?.events.length ?? 0}개</strong>
      {state?.events.length ? <ul>{state.events.slice(-12).reverse().map((event, index) => <li key={`${text(event.event_id)}-${index}`}><span>{text(event.name, 60)} · {text(event.kind, 40)} · {text(event.status, 32)}</span><small>{text(event.basis_end_time, 32)} · {text(event.source, 70)} · 조회 {dateTime(event.source_fetched_at)} · 봉 {text(event.bar_status, 16)}</small></li>)}</ul> : <p className="data-note">아직 저장된 패턴 사건이 없습니다.</p>}
    </div>
    <p className="chart-lab-monitor-footnote">상태와 사건은 별도 사용자 파일에 저장됩니다. 운영 SQLite, 스케줄러, Telegram에는 기록하지 않습니다.</p>
  </section>;
}
