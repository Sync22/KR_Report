"use client";

import { useCallback, useEffect, useState } from "react";

type Candidate = { report_business_date: string; stock_code: string; stock_name: string; report_count: number; report_reason: "리포트 집중" };
type Watch = Candidate & { watch_id: string; added_at: string; initialized: boolean; last_polled_at: string | null; last_bar_time: string | null; failure_count: number };
type AlertEvent = { event_id: string; stock_code: string; stock_name: string; report_business_date: string; rule_version: string; kind: string; observed_state: string; basis_bar_time: string; source: string; source_fetched_at: string; finality: string };
type View = { state: { running: boolean; startedAt: string | null; lastPollAt: string | null; lastError: string | null; watches: Watch[]; events: AlertEvent[] }; candidates: Candidate[]; ownerActiveElsewhere: boolean; providerReady: boolean };

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function parseView(value: unknown): View | null {
  const row = record(value);
  const state = record(row.state);
  if (typeof state.running !== "boolean" || !Array.isArray(state.watches) || !Array.isArray(state.events) || !Array.isArray(row.candidates) ||
    typeof row.ownerActiveElsewhere !== "boolean" || typeof row.providerReady !== "boolean") return null;
  return row as View;
}

function safeText(value: unknown, max = 120): string {
  return typeof value === "string" ? value.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max) : "자료 없음";
}

function dateTime(value: unknown): string {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return "시각 없음";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short", timeZone: "Asia/Seoul" }).format(new Date(value));
}

function eventLabel(kind: unknown, status: unknown): string {
  const kindLabel: Record<string, string> = {
    "bull-flag": "상승 깃발", "bear-flag": "하락 깃발", "ascending-triangle": "상승 삼각 구조",
    "descending-triangle": "하락 삼각 구조", "symmetrical-triangle": "대칭 삼각 구조",
    "support-breakout": "지지 경계 하향", "resistance-breakout": "저항 경계 상향",
  };
  const stateLabel: Record<string, string> = { forming: "형성 관찰", "observed-breakout": "경계 이탈 관찰", "observed-crossing": "경계 교차 관찰" };
  return `${kindLabel[safeText(kind)] ?? "패턴 관찰"} · ${stateLabel[safeText(status)] ?? "상태 기록"}`;
}

export default function ChartLabReportAlertPanel({ businessDate, active }: Readonly<{ businessDate: string; active: boolean }>) {
  const [view, setView] = useState<View | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/chart-lab/report-alerts?date=${encodeURIComponent(businessDate)}`, { method: "GET", cache: "no-store" });
      const value: unknown = await response.json();
      if (!response.ok) throw new Error("리포트 집중 감시 상태를 읽지 못했습니다.");
      const next = parseView(value);
      if (!next) throw new Error("감시 상태 응답 형식을 확인할 수 없습니다.");
      setView(next); setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "감시 상태를 읽지 못했습니다."); }
  }, [businessDate]);

  useEffect(() => { if (active) void loadStatus(); }, [active, loadStatus]);
  useEffect(() => {
    if (!active || !view?.state.running) return;
    const timer = window.setInterval(() => void loadStatus(), 10_000);
    return () => window.clearInterval(timer);
  }, [active, loadStatus, view?.state.running]);

  async function post(body: Record<string, unknown>) {
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/chart-lab/report-alerts", {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body), cache: "no-store",
      });
      const value: unknown = await response.json();
      if (!response.ok) {
        const reason = record(value).error;
        const message = reason === "chart-alert-provider-not-configured" ? "Toss MARKET_DATA_CHART 설정이 없어 감시를 시작하지 않았습니다."
          : reason === "chart-alert-watch-limit" ? "리포트 집중 감시는 최대 3종목까지 가능합니다."
            : reason === "chart-alert-monitor-owned-elsewhere" ? "다른 로컬 서버가 감시를 소유하고 있습니다."
              : reason === "chart-alert-watches-required" ? "먼저 리포트 집중 종목을 추가하세요."
                : "감시 설정을 변경하지 못했습니다.";
        throw new Error(message);
      }
      await loadStatus();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "감시 설정을 저장하지 못했습니다."); }
    finally { setBusy(false); }
  }

  const watches = view?.state.watches ?? [];
  const events = view?.state.events ?? [];
  const canControl = !busy && !view?.ownerActiveElsewhere;
  return <section className="chart-subpanel chart-report-alerts" aria-label="리포트 집중 종목 차트 알림">
    <div className="chart-subpanel-heading"><h3>리포트 집중 감시</h3><span>{view?.state.running ? "실행 중" : "중지됨"}</span></div>
    <p className="chart-lab-monitor-note">선택일에 리포트가 2건 이상 모인 종목만 최대 3개까지 추가합니다. 시작을 눌러야 Toss 1분봉을 조회합니다.</p>
    <div className="chart-report-alert-status"><span>{view?.providerReady ? "Toss 1분봉 설정 확인 · 요청은 감시 시작 후" : "Toss MARKET_DATA_CHART 설정 필요"}</span><span>봉 확정: 미확인</span></div>
    {view?.ownerActiveElsewhere ? <p className="chart-lab-error" role="status">다른 로컬 서버가 감시 프로세스를 소유하고 있습니다.</p> : null}
    <ul className="chart-report-alert-candidates" aria-label="리포트 집중 후보">
      {(view?.candidates ?? []).map((candidate) => {
        const watched = watches.some((item) => item.stock_code === candidate.stock_code && item.report_business_date === candidate.report_business_date);
        return <li key={`${candidate.report_business_date}-${candidate.stock_code}`}>
          <span><strong>{candidate.stock_name}</strong><small>{candidate.stock_code} · {candidate.report_count}건 · 기준 {candidate.report_business_date}</small></span>
          <button className="action-secondary" type="button" disabled={!canControl || watched || watches.length >= 3} onClick={() => void post({ action: "add", report_business_date: candidate.report_business_date, stock_code: candidate.stock_code })}>{watched ? "추가됨" : "감시에 추가"}</button>
        </li>;
      })}
    </ul>
    {!view?.candidates.length ? <p className="data-note">선택일에 리포트 집중 후보가 없습니다.</p> : null}
    {watches.length ? <ul className="chart-report-alert-watches" aria-label="감시 목록">{watches.map((watch) => <li key={watch.watch_id}>
      <span><strong>{watch.stock_name}</strong><small>{watch.stock_code} · 리포트 {watch.report_count}건 · 마지막 봉 {dateTime(watch.last_bar_time)}</small></span>
      <button type="button" className="chart-remove-group" disabled={!canControl} onClick={() => void post({ action: "remove", watch_id: watch.watch_id })}>제거</button>
    </li>)}</ul> : <p className="data-note">감시 종목을 아직 추가하지 않았습니다.</p>}
    <div className="chart-lab-monitor-actions">
      {view?.state.running
        ? <button className="action-secondary" type="button" disabled={!canControl} onClick={() => void post({ action: "pause" })}>감시 중지</button>
        : <button className="action-primary" type="button" disabled={!canControl || !view?.providerReady || !watches.length} onClick={() => void post({ action: "start" })}>1분봉 감시 시작</button>}
      <button className="action-secondary" type="button" disabled={busy} onClick={() => void loadStatus()}>상태 새로고침</button>
    </div>
    <p className="chart-lab-monitor-status" aria-live="polite">마지막 확인 {dateTime(view?.state.lastPollAt)}{view?.state.lastError ? ` · ${safeText(view.state.lastError, 80)}` : ""}</p>
    {error ? <p className="chart-lab-error" role="alert">{error}</p> : null}
    <div className="chart-lab-event-list"><strong>기록된 상태 변화 {events.length}개</strong>
      {events.length ? <ul>{events.slice(-8).reverse().map((event) => <li key={event.event_id}>
        <span>{safeText(event.stock_name)} · {eventLabel(event.kind, event.observed_state)}</span>
        <small>{dateTime(event.basis_bar_time)} · {safeText(event.source)} · 봉 확정 미확인</small>
      </li>)}</ul> : <p className="data-note">새로운 상태 변화가 없습니다.</p>}
    </div>
    <p className="chart-lab-monitor-footnote">Next는 이 로컬 상태와 이벤트 파일만 기록합니다. SQLite와 Telegram은 Python 전용이며, 이 화면은 추천·매수/매도·주문을 만들지 않습니다.</p>
  </section>;
}
