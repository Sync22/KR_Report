import "server-only";

import { notFound } from "next/navigation";

import {
  dailyBrokerDisplay,
  dailyReportOpinionLabel,
  dailyStoredMarketReference,
  defaultIncludeSingleReportStocks,
  isBusinessDate,
  isDailyStockSummarySnapshot,
  parseDailyStockLimit,
} from "@/domain/daily";
import { isCandidateEvidenceSnapshot, type CandidateEvidenceRow } from "@/domain/candidate-evidence";
import { isStockSearchSnapshot } from "@/domain/stocks";
import SelectedStockPanel from "@/components/server/selected-stock-panel";
import StockSummarySingleToggle from "@/components/client/stock-summary-single-toggle";
import type { DailyTabWorkspace } from "@/server/daily-tab-workspace";
import { getStockSearchSnapshot } from "@/server/stock-search";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function reportedPrice(value: number | null | undefined): string {
  return value === null || value === undefined ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

function stockSelectionHref(date: string, stockCode: string, includeSingle: boolean, visibleLimit: number): string {
  const query = new URLSearchParams({ stock: stockCode });
  if (includeSingle) query.set("include_single", "1");
  if (visibleLimit > 6) query.set("limit", String(visibleLimit));
  return `/daily/${date}/stocks?${query}#selected-stock`;
}

export default async function StockSearchPage({
  params,
  searchParams,
  workspace,
}: Readonly<{
  params: Promise<{ date: string }>;
  searchParams: Promise<{ q?: string | string[]; include_single?: string | string[]; limit?: string | string[]; stock?: string | string[] }>;
  workspace: DailyTabWorkspace;
}>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();

  const paramsValue = await searchParams;
  const rawQuery = Array.isArray(paramsValue.q) ? paramsValue.q[0] : paramsValue.q;
  const query = (rawQuery ?? "").trim();
  const rawIncludeSingle = Array.isArray(paramsValue.include_single) ? paramsValue.include_single[0] : paramsValue.include_single;
  const requestedIncludeSingle = rawIncludeSingle === "1";
  const rawLimit = Array.isArray(paramsValue.limit) ? paramsValue.limit[0] : paramsValue.limit;
  const visibleLimit = parseDailyStockLimit(rawLimit ?? null);
  const selectedStockCode = typeof paramsValue.stock === "string" ? paramsValue.stock : null;

  if (!query) {
    const dailyPayload: unknown = workspace.stocks;
    if (!isDailyStockSummarySnapshot(dailyPayload, date)) return <main><section className="daily-briefing stock-summary-page"><h1>일일 종목 요약 ({date})</h1><Message>선택일 종목 요약 자료를 불러오지 못했습니다.</Message></section></main>;

    const includeSingle = defaultIncludeSingleReportStocks(dailyPayload.stocks, requestedIncludeSingle);
    let selectedCandidate: CandidateEvidenceRow | null = null;
    if (selectedStockCode && /^\d{6}$/.test(selectedStockCode) && dailyPayload.stocks.some((stock) => stock.stock_code === selectedStockCode)) {
      const evidence: unknown = workspace.candidates;
      if (isCandidateEvidenceSnapshot(evidence, date)) {
        selectedCandidate = evidence.rows.find((candidate) => candidate.stock_code === selectedStockCode) ?? null;
      }
    }
    const hasRepeatedMentions = dailyPayload.stocks.some((stock) => stock.mention_count > 1);
    const filteredStocks = includeSingle ? dailyPayload.stocks : dailyPayload.stocks.filter((stock) => stock.mention_count > 1);
    const visibleStocks = filteredStocks.slice(0, visibleLimit);
    const singleCount = dailyPayload.stocks.filter((stock) => stock.mention_count === 1).length;
    const remainingCount = Math.max(filteredStocks.length - visibleStocks.length, 0);
    const statusParts = [includeSingle
      ? `1건 포함 ${visibleStocks.length}종목 표시`
      : `2건 이상 ${visibleStocks.length}종목 표시`];
    if (remainingCount) statusParts.push(`추가 ${remainingCount}종목 숨김`);
    if (!includeSingle && singleCount) statusParts.push(`1건 ${singleCount}종목 숨김`);
    const moreParams = new URLSearchParams();
    if (selectedStockCode) moreParams.set("stock", selectedStockCode);
    if (includeSingle) moreParams.set("include_single", "1");
    moreParams.set("limit", String(Math.min(100, visibleLimit + 6)));
    const moreHref = `/daily/${date}/stocks?${moreParams}${selectedStockCode ? "#selected-stock" : ""}`;
    return (
      <main>
        <section className="daily-briefing stock-summary-page" aria-labelledby="stock-summary-heading">
          <div className="section-header stock-summary-heading">
            <h1 id="stock-summary-heading">일일 종목 요약 <span className="secondary">({date})</span></h1>
            <div className="stock-summary-actions">
              <StockSummarySingleToggle
                date={date}
                selectedStockCode={selectedStockCode}
                visibleLimit={visibleLimit}
                includeSingle={includeSingle}
                disabled={!hasRepeatedMentions}
              />
              {remainingCount ? <a className="ghost-button" href={moreHref}>더 보기 ({remainingCount})</a> : null}
            </div>
          </div>
          <p className="summary">{statusParts.join(" · ")} · Naver 저장 리포트 집계</p>
          <SelectedStockPanel
            date={date}
            selectedStockCode={selectedStockCode}
            allowedStocks={dailyPayload.stocks}
            candidate={selectedCandidate}
            detailSnapshot={workspace.selectedStockDetail}
          />
          {visibleStocks.length === 0 ? <Message>선택일에 표시할 종목 요약이 없습니다.</Message> : (
            <div className="table-wrap stock-summary-table-wrap">
              <table className="mobile-card-table main-reference-ledger stock-main-ledger">
                <caption className="sr-only">선택일 종목 요약 · 기준일 {date}</caption>
                <thead><tr>
                  <th scope="col">종목</th><th scope="col">건수</th><th scope="col">증권사</th>
                  <th scope="col">목표가</th><th scope="col">원문 의견</th><th scope="col">Toss 참고</th>
                </tr></thead>
                <tbody>{visibleStocks.map((stock) => {
                  const market = dailyStoredMarketReference(stock);
                  const selected = stock.stock_code === selectedStockCode;
                  const selectionHref = stock.stock_code && /^\d{6}$/.test(stock.stock_code)
                    ? stockSelectionHref(date, stock.stock_code, includeSingle, visibleLimit)
                    : null;
                  return <tr key={`${stock.stock_code ?? stock.stock_name}-${stock.business_date}`}>
                    <td data-label="종목">{selectionHref
                      ? <a className="stock-selection-link" href={selectionHref} aria-current={selected ? "true" : undefined}>{stock.stock_name}<span className="secondary"> ({stock.stock_code})</span></a>
                      : <>{stock.stock_name}{stock.stock_code ? <span className="secondary"> ({stock.stock_code})</span> : null}</>}</td>
                    <td data-label="건수">{stock.mention_count}건</td><td data-label="증권사">{dailyBrokerDisplay(stock.broker_display)}</td>
                    <td data-label="목표가">{stock.target_price_min == null && stock.target_price_max == null
                      ? "목표가 -" : `${reportedPrice(stock.target_price_min)} ~ ${reportedPrice(stock.target_price_max)}`}</td>
                    <td data-label="원문 의견">{dailyReportOpinionLabel(stock.dominant_opinion)}</td>
                    <td data-label="Toss 참고"><span>{market.price}</span><span className="secondary stock-market-reference">{market.detail}</span></td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    );
  }

  let payload: unknown;
  try {
    payload = getStockSearchSnapshot(date, query);
  } catch {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>저장 종목 검색</h1>
        <Message>저장 종목을 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.</Message>
      </main>
    );
  }
  if (!isStockSearchSnapshot(payload, date, query)) {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>저장 종목 검색</h1>
        <Message>종목 검색 응답 형식을 확인할 수 없습니다.</Message>
      </main>
    );
  }

  const updatedAt = new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: payload.timezone,
  }).format(new Date(payload.now));

  return (
    <main>
      <p className="eyebrow">Stock Monitor · 공개 web-view</p>
      <h1>저장 종목 검색</h1>
      <p className="updated">
        기준일 {payload.business_date} · 조회 시각: <time dateTime={payload.now}>{updatedAt} KST</time>
      </p>
      <form action={`/daily/${date}/stocks`} method="get" className="search-form">
        <label htmlFor="stock-query">종목명 또는 코드</label>
        <input id="stock-query" name="q" type="search" defaultValue={query} autoComplete="off" />
        <button type="submit">검색</button>
      </form>
      <p className="data-note">
        저장 종목 메타데이터 기준 · 종목 우주 기준일 {payload.stock_universe_reference_date ?? "자료 없음"}
      </p>
      {payload.items.length === 0 ? (
        <Message>{payload.empty_state ?? "조회된 저장 종목이 없습니다."}</Message>
      ) : (
        <div className="table-wrap">
          <table>
            <caption className="eyebrow table-caption">검색 결과 {payload.items.length}건</caption>
            <thead>
              <tr>
                <th scope="col">종목</th>
                <th scope="col">시장</th>
                <th scope="col">선택일 저장 상태</th>
              </tr>
            </thead>
            <tbody>
              {payload.items.map((item) => (
                <tr key={item.stock_code}>
                  <td><a href={`/daily/${date}/stocks/${item.stock_code}`}>{item.stock_name} ({item.stock_code})</a></td>
                  <td>
                    {item.market
                      ? `${item.market} · ${item.market_source === "stored_toss_stock_universe" ? "Toss 종목 우주" : "KRX 종목 메타데이터"} · 기준일 ${item.market_reference_date}`
                      : "시장 기준 자료 없음"}
                  </td>
                  <td>{item.display_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a></p>
    </main>
  );
}
