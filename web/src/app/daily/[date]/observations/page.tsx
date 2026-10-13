import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isBacktestObservationSnapshot, isObservationSummarySnapshot } from "@/domain/observation";
import { getBacktestObservationSnapshot } from "@/server/backtest-observation";
import { getObservationSummarySnapshot } from "@/server/observation-summary";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function display(value: unknown, suffix = ""): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${new Intl.NumberFormat("ko-KR").format(value)}${suffix}`
    : "자료 없음";
}

function percent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(2)}%` : "자료 없음";
}

function categoryHref(date: string, item: Record<string, unknown>): string {
  return `/daily/${date}/category?${new URLSearchParams({ type: String(item.category_type), display_name: String(item.display_name), public_category_id: String(item.public_category_id) })}`;
}

export default async function ObservationsPage({ params }: Readonly<{ params: Promise<{ date: string }> }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  let summaryRaw: unknown = null;
  let backtestRaw: unknown = null;
  try { summaryRaw = getObservationSummarySnapshot(date); } catch { summaryRaw = null; }
  try { backtestRaw = getBacktestObservationSnapshot(date, 20, 2); } catch { backtestRaw = null; }
  const summary = isObservationSummarySnapshot(summaryRaw, date) ? summaryRaw : null;
  const backtest = isBacktestObservationSnapshot(backtestRaw, date) ? backtestRaw : null;

  return (
    <main>
      <p className="eyebrow">Stock Monitor · 공개 web-view</p>
      <h1>저장 관찰 요약</h1>
      <p className="updated">기준일 {date} · 저장된 리포트와 시장 참고값</p>
      {!summary ? <Message>선택일 관찰 요약을 불러오지 못했습니다.</Message> : <>
        <p className="summary">{summary.market_mood.display}</p>
        <p className="data-note">{summary.notice}</p>
        <ul className="status-list">
          {summary.market_mood.lines.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}
        </ul>

        <section className="data-section" aria-labelledby="report-heading">
          <h2 id="report-heading">리포트 집중</h2>
          {summary.report_concentration.items.length ? <div className="table-wrap"><table>
            <thead><tr><th scope="col">종목</th><th scope="col">저장 근거</th></tr></thead>
            <tbody>{summary.report_concentration.items.map((item, index) => <tr key={`${item.stock_code}-${index}`}>
              <td>{/^\d{6}$/.test(String(item.stock_code)) ? <a href={`/daily/${date}/stocks/${item.stock_code}`}>{item.stock_name} ({item.stock_code})</a> : item.stock_name}</td>
              <td>{item.display}</td>
            </tr>)}</tbody>
          </table></div> : <Message>선택일 저장 리포트 집중 근거가 없습니다.</Message>}
        </section>

        <section className="data-section" aria-labelledby="flow-heading">
          <h2 id="flow-heading">수급 참고</h2>
          {summary.flow_reference.items.length ? <div className="table-wrap"><table>
            <thead><tr><th scope="col">종목</th><th scope="col">수급 기준일</th><th scope="col">저장 참고</th></tr></thead>
            <tbody>{summary.flow_reference.items.map((item, index) => <tr key={`${item.stock_code}-${index}`}>
              <td>{item.stock_name}</td><td>{String(item.reference_date ?? "자료 없음")}</td><td>{item.display}</td>
            </tr>)}</tbody>
          </table></div> : <Message>저장 수급 참고가 없습니다.</Message>}
        </section>

        <section className="data-section" aria-labelledby="price-heading">
          <h2 id="price-heading">저장 가격·거래량 참고</h2>
          {summary.price_volume_reference.items.length ? <div className="table-wrap"><table>
            <thead><tr><th scope="col">종목</th><th scope="col">기준일</th><th scope="col">저장 참고</th></tr></thead>
            <tbody>{summary.price_volume_reference.items.map((item, index) => <tr key={`${item.stock_code}-${index}`}>
              <td>{item.stock_name}</td><td>{String(item.reference_date ?? "자료 없음")}</td><td>{item.display}</td>
            </tr>)}</tbody>
          </table></div> : <Message>저장 가격·거래량 참고가 없습니다.</Message>}
        </section>

        <section className="data-section" aria-labelledby="breadth-heading">
          <h2 id="breadth-heading">업종·테마 분포</h2>
          {[...summary.sector_breadth.sectors, ...summary.sector_breadth.themes].length ? <ul className="status-list">
            {[...summary.sector_breadth.sectors, ...summary.sector_breadth.themes].map((item, index) => <li key={`${item.public_category_id}-${index}`}>
              <a href={categoryHref(date, item)}>{item.display}</a><span className="secondary"> · 분류 기준일 {item.snapshot_date ?? "최근 저장 분류"}</span>
            </li>)}
          </ul> : <Message>저장 업종·테마 분류가 없습니다.</Message>}
        </section>
      </>}

      <section className="data-section" aria-labelledby="backtest-heading">
        <details>
          <summary><h2 id="backtest-heading">복기·연구: 과거 리포트 반응과 목표가 확인</h2></summary>
          {!backtest ? <Message>과거 복기 데이터를 불러오지 못했습니다.</Message> : <>
            <p className="data-note">{backtest.notice} · 기준일 {backtest.business_date} · 리포트 {backtest.mention_threshold}건 이상 · 점수/추천 계산 없음</p>
            {!backtest.rows.length ? <Message>조건에 맞는 저장 복기 데이터가 없습니다.</Message> : backtest.rows.map((row, index) => {
              const target = row.target_observation;
              const flow = row.stock_flow_observation;
              const netBuy = row.net_buy_top_observation;
              return <section className="data-section" aria-label={`${row.stock_name} 과거 관찰`} key={`${row.stock_code}-${index}`}>
                <h3>{row.stock_name} ({row.stock_code}) · 리포트 {row.report_summary.report_count}건</h3>
                <p className="data-note">원천 기준: 2026년 저장 리포트·KRX 가격/수급 복기 · 현재 후보 순서와 분리</p>
                <div className="table-wrap"><table>
                  <thead><tr><th scope="col">관찰 구간</th><th scope="col">기준일</th><th scope="col">종가 변화</th><th scope="col">상태</th></tr></thead>
                  <tbody>{row.reaction_windows.map((window) => <tr key={window.horizon_days}>
                    <td>D+{window.horizon_days}</td><td>{window.horizon_date ?? "자료 대기"}</td>
                    <td>{window.available ? percent(window.close_return_percent) : "자료 없음"}</td>
                    <td>{window.available ? "저장값 있음" : String(window.unavailable_reason ?? "자료 없음")}</td>
                  </tr>)}</tbody>
                </table></div>
                <ul className="status-list">
                  <li>리포트 의견 표기: {String(row.report_summary.dominant_opinion ?? "자료 없음")} · 목표가 {display(row.report_summary.target_price_min, "원")} – {display(row.report_summary.target_price_max, "원")}</li>
                  <li>기준 시세: {row.base_market ? `${String(row.base_market.business_date)} · 종가 ${display(row.base_market.close_price, "원")}` : "저장 기준 시세 없음"}</li>
                  <li>목표가 기준일: {String(target.baseline_date ?? "자료 없음")} · 확인 기준일: {String(target.current_date ?? "자료 없음")}</li>
                  <li>목표가 구간 차이: {percent(target.target_gap_min_percent)} – {percent(target.target_gap_max_percent)} · 진행 참고: {percent(target.progress_to_min_percent)} / {percent(target.progress_to_max_percent)}</li>
                  <li>목표가 검증 상태: {typeof target.validation_notice === "string" ? target.validation_notice : "자료 없음"}{target.progress_caution && typeof target.progress_notice === "string" ? ` · ${target.progress_notice}` : ""}</li>
                  <li>저장 수급: {flow.available ? (Array.isArray(flow.investor_types) ? flow.investor_types.join(", ") : "저장 행 있음") : "자료 없음"} · 외국인 순매수 상위: {netBuy.available ? `포함${netBuy.foreign_top_rank ? ` (${String(netBuy.foreign_top_rank)}위)` : ""}` : "미포함"}</li>
                </ul>
                {row.evidence_notes.length ? <p className="data-note">저장 근거 메모: {row.evidence_notes.join(" · ")}</p> : null}
              </section>;
            })}
          </>}
        </details>
      </section>
      <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a></p>
    </main>
  );
}
