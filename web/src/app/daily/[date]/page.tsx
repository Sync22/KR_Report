import { notFound } from "next/navigation";

import { dailyFreshnessLabel, dailyStockDetailHref, dailyStoredMarketReference, isBusinessDate, isDailySnapshot } from "@/domain/daily";
import { getDailySnapshot } from "@/server/daily-snapshot";
import StoredMarketContext from "@/components/stored-market-context";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function reportedPrice(value: number | null | undefined): string {
  return value === null || value === undefined ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

export default async function DailyPage({ params }: Readonly<{ params: Promise<{ date: string }> }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();

  let payload: unknown;
  try {
    payload = getDailySnapshot(date);
  } catch {
    return (
      <main className="overview-page">
        <p className="eyebrow">선택일 요약</p>
        <h1>{date} 일일 리서치</h1>
        <Message>저장된 데이터를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.</Message>
      </main>
    );
  }
  if (!isDailySnapshot(payload, date)) {
    return (
      <main className="overview-page">
        <p className="eyebrow">선택일 요약</p>
        <h1>{date} 일일 리서치</h1>
        <Message>일일 응답 형식을 확인할 수 없습니다.</Message>
      </main>
    );
  }

  const updatedAt = new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: payload.timezone,
  }).format(new Date(payload.now));

  return (
    <main className="overview-page">
      <header className="page-intro overview-intro">
        <div>
          <p className="eyebrow">선택일 요약</p>
          <h1>{date} 리서치</h1>
          <p className="updated">기준일 {payload.business_date} · 조회 시각 <time dateTime={payload.now}>{updatedAt} KST</time></p>
        </div>
        <div className="overview-count" aria-label={`저장 리포트 ${payload.report_count}건, 요약 종목 ${payload.summary_stock_count}종목`}>
          <span>저장 리포트</span><strong>{payload.report_count}<small>건</small></strong><span>{payload.summary_stock_count}종목</span>
        </div>
      </header>
      <p className="overview-note">일일 요약은 선택일에 저장된 보고서 집계입니다. 표시된 목표가는 리포트 원문 기준 참고값입니다.</p>
      <div className="overview-actions">
        <section className="overview-action-card overview-action-primary" aria-labelledby="overview-first-heading">
          <p className="eyebrow">먼저 확인</p>
          <h2 id="overview-first-heading">오늘의 관찰 후보</h2>
          <p>Main Top2와 저장된 관찰 후보의 근거를 확인합니다.</p>
          <div className="page-action-row">
            <a className="action-primary" href={`/daily/${date}/main`}>Main Top2 보기 <span aria-hidden="true">→</span></a>
            <a className="action-secondary" href={`/daily/${date}/candidates`}>후보 전체 보기</a>
          </div>
        </section>
        <section className="overview-action-card" aria-labelledby="overview-stock-search-heading">
          <p className="eyebrow">종목 찾기</p>
          <h2 id="overview-stock-search-heading">저장 리포트 검색</h2>
          <p>선택일에 저장된 종목명 또는 코드를 검색합니다.</p>
          <form action={`/daily/${date}/stocks`} method="get" className="search-form">
            <label htmlFor="stock-query">종목명 또는 코드</label>
            <input id="stock-query" name="q" type="search" autoComplete="off" />
            <button type="submit">검색</button>
          </form>
        </section>
      </div>
      <nav className="overview-reference-links" aria-label="선택일 참고 화면">
        <span>참고 · 복기</span>
        <a href="/market">시장</a>
        <a href={`/daily/${date}/etf`}>ETF 흐름</a>
        <a href={`/daily/${date}/rotation`}>업종·테마 순환</a>
        <a href={`/daily/${date}/observations`}>관찰 복기</a>
        <a href={`/daily/${date}/intraday`}>장중 기록</a>
      </nav>
      <section className="overview-stocks data-section" aria-labelledby="overview-stocks-heading">
        <div className="section-header overview-section-heading">
          <div><p className="eyebrow">저장 데이터</p><h2 id="overview-stocks-heading">종목 요약</h2></div>
          <span>{payload.stocks.length}종목</span>
        </div>
      {payload.stocks.length === 0 ? (
        <Message>선택한 날짜에 저장된 종목 요약이 없습니다.</Message>
      ) : (
        <div className="table-wrap stock-summary-table-wrap">
          <table className="mobile-card-table">
            <caption className="eyebrow table-caption">선택일 종목 요약</caption>
            <thead>
              <tr>
                <th scope="col">종목</th>
                <th scope="col">보고서</th>
                <th scope="col">증권사</th>
                <th scope="col">리포트 목표가 참고</th>
                <th scope="col">리포트 의견 표기</th>
                <th scope="col">Toss 참고</th>
              </tr>
            </thead>
            <tbody>
              {payload.stocks.map((stock) => {
                const market = dailyStoredMarketReference(stock);
                const detailHref = dailyStockDetailHref(date, stock.stock_code);
                return (
                <tr key={`${stock.stock_code ?? stock.stock_name}-${stock.business_date}`}>
                  <td data-label="종목">
                    {detailHref ? (
                      <a href={detailHref}>
                        {stock.stock_name}<span className="secondary"> ({stock.stock_code})</span>
                      </a>
                    ) : <>{stock.stock_name}{stock.stock_code ? <span className="secondary"> ({stock.stock_code})</span> : null}</>}
                  </td>
                  <td data-label="보고서">{stock.mention_count}건</td>
                  <td data-label="증권사">{stock.broker_display || "자료 없음"}</td>
                  <td data-label="리포트 목표가 참고">
                    {reportedPrice(stock.target_price_min)} – {reportedPrice(stock.target_price_max)}
                  </td>
                  <td data-label="리포트 의견 표기">{stock.dominant_opinion ? `리포트 표기: ${stock.dominant_opinion}` : "자료 없음"}</td>
                  <td data-label="Toss 참고"><span>{market.price}</span><span className="secondary stock-market-reference">{market.detail}</span></td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      </section>

      <div className="overview-detail-grid">
      <section className="data-section" aria-labelledby="source-heading">
        <div className="section-header overview-section-heading"><div><p className="eyebrow">기준 확인</p><h2 id="source-heading">출처와 신선도</h2></div></div>
        <ul className="status-list">
          {payload.source_freshness_summary.items.map((item) => {
            const status = dailyFreshnessLabel(item, payload.business_date);
            return (
              <li key={item.key}>
                <strong>{item.label}</strong>
                <span className="status-value">{status}</span>
                {item.reference_date ? <span className="secondary"> · 출처 기준일 {item.reference_date}</span> : null}
                {item.notice ? <p>{item.notice}</p> : null}
                {item.missing_domains?.length ? <p>저장 누락 항목: {item.missing_domains.join(", ")}</p> : null}
              </li>
            );
          })}
        </ul>
        <p className="data-note">
          Toss 저장 기준일: {payload.toss_context.snapshot_date ?? "자료 없음"} · {payload.toss_context.notice}
        </p>
        {payload.toss_context.missing_domains.length > 0 ? (
          <p className="data-note">Toss 저장 누락 항목: {payload.toss_context.missing_domains.join(", ")}</p>
        ) : null}
      </section>
      <section className="data-section" aria-labelledby="news-heading">
        <div className="section-header overview-section-heading"><div><p className="eyebrow">저장 관찰</p><h2 id="news-heading">뉴스 상태</h2></div></div>
        <p className="summary">
          <strong>{payload.news_observation_summary.display_label}</strong> · {payload.news_observation_summary.reason}
        </p>
        {payload.news_observation_summary.observed_at ? (
          <p className="data-note">
            관찰 시각: <time dateTime={payload.news_observation_summary.observed_at}>{payload.news_observation_summary.observed_at}</time>
          </p>
        ) : null}
        {payload.news_observation_summary.missing_context.length > 0 ? (
          <p className="data-note">누락 상태: {payload.news_observation_summary.missing_context.join(", ")}</p>
        ) : null}
      </section>
      </div>
      <StoredMarketContext snapshot={payload} />
      <p className="footer-link"><a href="/archive">아카이브로 돌아가기</a></p>
    </main>
  );
}
