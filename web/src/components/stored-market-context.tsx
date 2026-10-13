import type { DailySnapshot, DailyStoredMarketItem } from "@/domain/daily";
import type { FlowTrendSnapshot } from "@/domain/market";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function storedNumber(value: number | null | undefined, unit = ""): string {
  return value === null || value === undefined ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}${unit}`;
}

function storedPercent(value: number | null | undefined): string {
  return value === null || value === undefined ? "자료 없음" : `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function recentMarketName(item: DailyStoredMarketItem | null): string {
  if (!item) return "저장 자료 없음";
  const name = item.stock_name || "종목명 자료 없음";
  const code = item.stock_code ? ` (${item.stock_code})` : "";
  return `${name}${code} · 거래대금 ${storedNumber(item.turnover, "원")} · 등락 ${storedPercent(item.change_percent)}`;
}

function flowValue(value: unknown, unit: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${new Intl.NumberFormat("ko-KR").format(value)} ${typeof unit === "string" ? unit : ""}`.trim()
    : "자료 없음";
}

function FlowTrendDetails({ flowTrend }: Readonly<{ flowTrend?: FlowTrendSnapshot | null }>) {
  if (flowTrend === undefined) return null;
  return <details className="market-context-flow-trend">
    <summary className="market-context-flow-trend-summary"><span>수급 흐름</span><span>Toss 저장값 · 실시간 호출 없음</span></summary>
    {flowTrend ? <>
      <p className="data-note">선택 기준일 {flowTrend.business_date} · 수급 기준일 {flowTrend.reference_date ?? "자료 없음"} · {flowTrend.reference_date === null ? "자료 없음" : flowTrend.exact_date_available ? "선택일 저장값" : "이전 저장값"}</p>
      <p className="data-note">{flowTrend.notice}</p>
      {flowTrend.items.length ? flowTrend.items.map((day) => (
        <section className="data-section" aria-label={`${day.business_date} 저장 시장 수급`} key={day.business_date}>
          <h3>{day.business_date}</h3>
          {day.market_flows.length ? <div className="table-wrap"><table>
            <thead><tr><th scope="col">시장</th><th scope="col">투자자</th><th scope="col">순매수량</th><th scope="col">순매수금액</th></tr></thead>
            <tbody>{day.market_flows.map((item, index) => <tr key={`${item.market}-${item.investor_type}-${index}`}>
              <td>{typeof item.market_label === "string" ? item.market_label : "시장 미확인"}</td>
              <td>{typeof item.investor_label === "string" ? item.investor_label : "투자자 미확인"}</td>
              <td>{flowValue(item.net_buy_volume, item.volume_unit)}</td>
              <td>{flowValue(item.net_buy_amount, item.amount_unit)}</td>
            </tr>)}</tbody>
          </table></div> : <Message>해당 날짜의 KOSPI·KOSDAQ 수급 행이 없습니다.</Message>}
        </section>
      )) : <Message>{flowTrend.notice}</Message>}
    </> : <Message>저장 시장 수급을 확인할 수 없습니다.</Message>}
  </details>;
}

export default function StoredMarketContext({ snapshot, flowTrend, openByDefault = false }: Readonly<{ snapshot: DailySnapshot | null; flowTrend?: FlowTrendSnapshot | null; openByDefault?: boolean }>) {
  if (!snapshot) return <details className="daily-briefing daily-market-context">
    <summary className="section-header disclosure-summary"><h2>시장 문맥 · Toss 당일 · Toss 저장</h2><span>조회값과 저장값을 구분해 표시</span></summary>
    <Message>선택일 저장 시장 문맥을 확인할 수 없습니다.</Message>
    <FlowTrendDetails flowTrend={flowTrend} />
  </details>;
  const context = snapshot.toss_context;
  const recent = snapshot.toss_recent_flow;
  const flow = snapshot.toss_investor_flow;
  const marketItems = [
    ...context.top_kospi_by_turnover,
    ...context.top_kosdaq_by_turnover,
    ...context.top_etfs_by_turnover,
  ];

  return (
    <details className="daily-briefing daily-market-context" open={openByDefault}>
      <summary className="section-header disclosure-summary">
        <h2>시장 문맥 · Toss 당일 · Toss 저장</h2>
        <span>조회값과 저장값을 구분해 표시</span>
      </summary>
      <p className="data-note">
        선택일 저장 시장값: {context.snapshot_date ?? "자료 없음"} · {context.notice}
        {context.capture_status ? ` · 캡처 ${context.capture_status}` : ""}
      </p>
      {context.missing_domains.length ? <p className="data-note">저장 누락 항목: {context.missing_domains.join(", ")}</p> : null}

      <section aria-labelledby="stored-index-heading">
        <h3 id="stored-index-heading">선택일 저장 지수</h3>
        {context.indices.length ? <div className="table-wrap"><table>
          <thead><tr><th scope="col">지수</th><th scope="col">저장값</th><th scope="col">등락률</th><th scope="col">거래대금</th></tr></thead>
          <tbody>{context.indices.map((item) => <tr key={`${item.index_series ?? item.index_name}-${item.business_date}`}>
            <td>{item.index_name ?? item.index_series ?? "지수명 자료 없음"}</td>
            <td>{storedNumber(item.close_index)}</td>
            <td>{storedPercent(item.change_percent)}</td>
            <td>{storedNumber(item.turnover, "원")}</td>
          </tr>)}</tbody>
        </table></div> : <Message>선택일 저장 지수 자료가 없습니다.</Message>}
      </section>

      <section aria-labelledby="stored-turnover-heading">
        <h3 id="stored-turnover-heading">선택일 저장 거래대금 상위</h3>
        {marketItems.length ? <div className="table-wrap"><table>
          <thead><tr><th scope="col">시장·종목</th><th scope="col">기준일</th><th scope="col">저장값</th><th scope="col">등락률</th><th scope="col">거래대금</th></tr></thead>
          <tbody>{marketItems.map((item) => <tr key={`${item.market ?? "ETF"}-${item.stock_code ?? item.etf_code ?? item.stock_name ?? item.etf_name}-${item.business_date}`}>
            <td>{item.market ?? "ETF"} · {item.stock_name ?? item.etf_name ?? "종목명 자료 없음"}{item.stock_code || item.etf_code ? ` (${item.stock_code ?? item.etf_code})` : ""}</td>
            <td>{item.business_date}</td>
            <td>{storedNumber(item.close_price, "원")}</td>
            <td>{storedPercent(item.change_percent)}</td>
            <td>{storedNumber(item.turnover, "원")}</td>
          </tr>)}</tbody>
        </table></div> : <Message>선택일 저장 거래대금 자료가 없습니다.</Message>}
      </section>

      <section aria-labelledby="stored-recent-flow-heading">
        <h3 id="stored-recent-flow-heading">최근 Toss 저장 흐름</h3>
        <p className="data-note">
          {recent.notice} · 선택일 {recent.business_date} · 기준일 {recent.reference_date ?? "자료 없음"}
          {recent.exact_date_available ? " · 선택일 자료" : " · 선택일 이전 저장값"}
        </p>
        {recent.available ? <div className="table-wrap"><table>
          <thead><tr><th scope="col">기준일</th><th scope="col">KOSPI 거래대금 상위</th><th scope="col">KOSDAQ 거래대금 상위</th></tr></thead>
          <tbody>{recent.items.map((item) => <tr key={item.business_date}>
            <td>{item.business_date}</td><td>{recentMarketName(item.kospi_top_by_turnover)}</td><td>{recentMarketName(item.kosdaq_top_by_turnover)}</td>
          </tr>)}</tbody>
        </table></div> : <Message>최근 Toss 저장 흐름 자료가 없습니다.</Message>}
      </section>

      <section aria-labelledby="stored-investor-flow-heading">
        <h3 id="stored-investor-flow-heading">Toss 저장 시장 수급</h3>
        <p className="data-note">{flow.notice} · 기준일 {flow.snapshot_date ?? "자료 없음"} · 저장 참고용</p>
        {flow.market_flows.length ? <div className="table-wrap"><table>
          <thead><tr><th scope="col">시장</th><th scope="col">투자자</th><th scope="col">순매수량</th><th scope="col">순매수금액</th></tr></thead>
          <tbody>{flow.market_flows.map((item) => <tr key={`${item.market}-${item.investor_type}-${item.business_date}`}>
            <td>{item.market_label}</td><td>{item.investor_label}</td>
            <td>{storedNumber(item.net_buy_volume, item.volume_unit ?? "주")}</td>
            <td>{storedNumber(item.net_buy_amount, item.amount_unit ?? "원")}</td>
          </tr>)}</tbody>
        </table></div> : <Message>선택일 시장 수급 자료가 없습니다.</Message>}
      </section>
      <FlowTrendDetails flowTrend={flowTrend} />
      <p className="footer-link"><a href={`/daily/${snapshot.business_date}/etf`}>ETF 저장 흐름</a> · <a href={`/daily/${snapshot.business_date}/rotation`}>업종·테마 위치 참고</a></p>
    </details>
  );
}
