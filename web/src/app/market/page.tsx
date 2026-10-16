import { isMarketSnapshot, isFlowTrendSnapshot, type FlowTrendSnapshot } from "@/domain/market";
import { getFlowTrendSnapshot } from "@/server/flow-trend";
import { getMarketSnapshot } from "@/server/market-snapshot";
import PublicPageHeader from "@/components/server/public-page-header";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

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

function changeClass(value: unknown): string {
  return typeof value === "number" && value > 0 ? "market-change-positive"
    : typeof value === "number" && value < 0 ? "market-change-negative" : "";
}

function text(value: unknown): string {
  return typeof value === "string" && value ? value : "자료 없음";
}

export default async function MarketPage() {
  let raw: unknown;
  try {
    raw = getMarketSnapshot();
  } catch {
    return <><PublicPageHeader current="market" /><main className="market-page"><p className="eyebrow">저장 시장 데이터</p><h1>저장 시장</h1><Message>저장된 시장 데이터를 불러오지 못했습니다.</Message></main></>;
  }
  if (!isMarketSnapshot(raw)) {
    return <><PublicPageHeader current="market" /><main className="market-page"><p className="eyebrow">저장 시장 데이터</p><h1>저장 시장</h1><Message>시장 응답 형식을 확인할 수 없습니다.</Message></main></>;
  }
  const market = raw;
  let flow: FlowTrendSnapshot | null = null;
  if (market.snapshot_date) {
    try {
      const candidate: unknown = getFlowTrendSnapshot(market.snapshot_date, 5);
      if (isFlowTrendSnapshot(candidate, market.snapshot_date)) flow = candidate;
    } catch { /* Keep market data visible if the separate stored-flow read is unavailable. */ }
  }
  const updatedAt = new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: market.timezone }).format(new Date(market.now));

  return (
    <><PublicPageHeader current="market" /><main className="market-page">
      <header className="page-intro">
        <div>
          <p className="eyebrow">저장 시장 데이터</p>
          <h1>저장 시장</h1>
          <p className="updated">조회 시각 <time dateTime={market.now}>{updatedAt} KST</time> · 실시간 조회 없음</p>
        </div>
        <div className="overview-count" aria-label={`Toss 저장 기준일 ${market.snapshot_date ?? "자료 없음"}`}>
          <span>Toss 20:00 스냅샷</span><strong>{market.snapshot_date ?? "자료 없음"}</strong><span>저장값 참고</span>
        </div>
      </header>
      {market.capture_status && market.capture_status !== "complete" ? (
        <p className="market-capture-note" role="status">저장 상태: {market.capture_status} · 누락 항목: {market.missing_domains.join(", ") || "확인된 누락 없음"}</p>
      ) : null}
      {market.latest_capture_attempt ? (
        <p className="data-note market-capture-detail">최근 저장 시도: {market.latest_capture_attempt.business_date ?? "기준일 없음"} · {market.latest_capture_attempt.status} · 누락 항목: {market.latest_capture_attempt.missing_domains.join(", ") || "없음"}</p>
      ) : null}
      {market.snapshot_date === null ? <Message>저장된 Toss 20:00 시장 스냅샷이 없습니다.</Message> : null}

      <section className="data-section market-index-section" aria-labelledby="index-heading">
        <div className="section-header overview-section-heading"><div><p className="eyebrow">지수 · 기준일 함께 표시</p><h2 id="index-heading">시장 지수</h2></div></div>
        {market.market_indices.length ? <div className="market-index-grid">{market.market_indices.map((item, index) => (
          <article className="market-index-card" key={`${item.index_series}-${index}`}>
            <div className="market-index-card-head"><h3>{text(item.index_name)}</h3><span>{text(item.business_date)}</span></div>
            <strong>{display(item.close_index)}</strong>
            <p className={changeClass(item.change_percent)}>{percent(item.change_percent)}</p>
            <span className="market-index-turnover">거래대금 {display(item.turnover, "원")}</span>
          </article>
        ))}</div> : <Message>저장된 시장 지수 데이터가 없습니다.</Message>}
      </section>

      <div className="market-table-grid">{([
        ["KOSPI 거래대금 상위", market.top_kospi_stocks],
        ["KOSDAQ 거래대금 상위", market.top_kosdaq_stocks],
        ["ETF 거래대금 상위", market.top_etfs],
      ] as const).map(([title, rows]) => (
        <section className={`data-section market-table-card${title.startsWith("ETF") ? " market-etf-table" : ""}`} aria-label={title} key={title}>
          <h2>{title}</h2>
          {rows.length ? <div className="table-wrap"><table>
            <thead><tr><th scope="col">종목</th><th scope="col">기준일</th><th scope="col">종가</th><th scope="col">등락률</th><th scope="col">거래대금</th></tr></thead>
            <tbody>{rows.map((item, index) => <tr key={`${item.stock_code ?? item.etf_code}-${index}`}>
              <td>{text(item.stock_name ?? item.etf_name)}{item.stock_code || item.etf_code ? ` (${text(item.stock_code ?? item.etf_code)})` : ""}</td>
              <td>{text(item.business_date)}</td><td>{display(item.close_price)}</td><td>{percent(item.change_percent)}</td><td>{display(item.turnover, "원")}</td>
            </tr>)}</tbody>
          </table></div> : <Message>저장된 데이터가 없습니다.</Message>}
        </section>
      ))}</div>

      <section className="data-section market-flow-section" aria-labelledby="flow-heading">
        <h2 id="flow-heading">저장 시장 수급 흐름</h2>
        {flow ? <>
          <p className="data-note">선택 기준일 {flow.business_date} · 수급 기준일 {flow.reference_date ?? "자료 없음"} · {flow.reference_date === null ? "자료 없음" : flow.exact_date_available ? "선택일 저장값" : "이전 저장값"} · 실시간 호출 없음</p>
          <p className="data-note">{flow.notice}</p>
          {flow.items.length ? flow.items.map((day) => <section className="data-section" aria-label={`${day.business_date} 시장 수급`} key={day.business_date}>
            <h3>{day.business_date}</h3>
            <div className="table-wrap"><table>
              <thead><tr><th scope="col">시장</th><th scope="col">투자자</th><th scope="col">순매수량</th><th scope="col">순매수금액</th></tr></thead>
              <tbody>{day.market_flows.map((item, index) => <tr key={`${item.market}-${item.investor_type}-${index}`}>
                <td>{text(item.market_label)}</td><td>{text(item.investor_label)}</td>
                <td>{display(item.net_buy_volume, ` ${text(item.volume_unit)}`)}</td><td>{display(item.net_buy_amount, ` ${text(item.amount_unit)}`)}</td>
              </tr>)}</tbody>
            </table></div>
          </section>) : <Message>{flow.notice}</Message>}
        </> : <Message>시장 수급 데이터를 확인할 수 없습니다. 기준일이 없거나 저장 수급 조회에 실패했습니다.</Message>}
      </section>
      {market.snapshot_date ? <p className="footer-link"><a href={`/daily/${market.snapshot_date}/etf`}>ETF 저장 흐름 전체 보기</a></p> : null}
      <p className="footer-link"><a href="/archive">아카이브로 돌아가기</a></p>
    </main></>
  );
}
