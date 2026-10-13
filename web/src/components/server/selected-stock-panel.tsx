import "server-only";

import { dailyStoredTimeLabel, isBusinessDate } from "@/domain/daily";
import type { CandidateEvidenceRow } from "@/domain/candidate-evidence";
import { isStockDetailSnapshot, type StockDetailSnapshot } from "@/domain/stocks";
import { getStockDetailSnapshot } from "@/server/stock-detail";

type SelectableStock = Readonly<{ stock_code: string | null }>;

type Props = Readonly<{
  date: string;
  selectedStockCode: string | null;
  allowedStocks: readonly SelectableStock[];
  candidate?: CandidateEvidenceRow | null;
  detailSnapshot?: StockDetailSnapshot | null;
  sectionId?: string;
}>;

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function stockPrice(value: number | null): string {
  return value === null ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

function stockPriceBasis(stock: StockDetailSnapshot): string {
  const { current_price_basis: basis, current_price_reference_time: time } = stock.value_context;
  if (basis === "20:00 stored") return time ? `${dailyStoredTimeLabel(time)} 저장` : "20:00 저장";
  if (basis === "Toss stored snapshot") return time ? `${dailyStoredTimeLabel(time)} 저장` : "Toss 저장";
  return "다음 확인 필요";
}

function stockNewsStatus(value: string): string {
  if (value === "stored_evidence") return "최신 저장 기준";
  if (value === "stored_no_match") return "매칭 뉴스 없음";
  return "다음 확인 필요";
}

function stockMissingLabels(values: string[]): string {
  const labels: Record<string, string> = { report: "리포트", toss: "Toss", current_price: "현재가", turnover: "거래대금", investor_flow: "수급" };
  return values.map((value) => labels[value] ?? "기준 자료").join(" · ");
}

function stockPercent(value: number | null): string {
  return value === null ? "자료 없음" : `${value > 0 ? "+" : ""}${new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 2 }).format(value)}%`;
}

function stockQuantity(value: number | null): string {
  return value === null ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}주`;
}

function targetJourneyStatus(item: StockDetailSnapshot["target_journey"]["items"][number]): string {
  const observed = item.observed_through ? ` · 관측 ${item.observed_through}` : "";
  if (item.status === "hit") return `달성 · ${item.hit_trading_days === 0 ? "당일" : `${item.hit_trading_days ?? "-"}영업일`}${observed}`;
  if (item.status === "in_progress") {
    const parts = ["진행 중"];
    if (item.current_attainment_percent !== null) parts.push(`현재 ${stockPercent(item.current_attainment_percent)}`);
    if (item.max_attainment_percent !== null) parts.push(`최대 ${stockPercent(item.max_attainment_percent)}`);
    if (item.observed_through) parts.push(`관측 ${item.observed_through}`);
    return parts.join(" · ");
  }
  return "가격 검증 대기";
}

function krxReferenceLabel(value: string | undefined): string {
  if (value === "exact") return "KRX 당일";
  if (value === "stale") return "KRX 이전 기준";
  return "KRX 없음";
}

export default async function SelectedStockPanel({
  date,
  selectedStockCode,
  allowedStocks,
  candidate = null,
  detailSnapshot,
  sectionId = "selected-stock",
}: Props) {
  const stockCode = typeof selectedStockCode === "string" && /^\d{6}$/.test(selectedStockCode)
    ? selectedStockCode
    : null;
  if (!isBusinessDate(date) || !stockCode || !allowedStocks.some((stock) => stock.stock_code === stockCode)) return null;

  let stock: StockDetailSnapshot | null = null;
  if (detailSnapshot !== undefined) {
    if (detailSnapshot && isStockDetailSnapshot(detailSnapshot, date, stockCode)) stock = detailSnapshot;
  } else {
    try {
      const payload = getStockDetailSnapshot(date, stockCode);
      if (isStockDetailSnapshot(payload, date, stockCode)) stock = payload;
    } catch {
      stock = null;
    }
  }

  if (!stock) {
    return (
      <section id={sectionId} className="daily-briefing selected-stock-panel" aria-labelledby={`${sectionId}-heading`}>
        <div className="section-header"><h2 id={`${sectionId}-heading`}>선택 종목</h2></div>
        <Message>선택 종목의 저장 상세를 불러오지 못했습니다.</Message>
      </section>
    );
  }

  const selectedCandidate = candidate?.stock_code === stockCode ? candidate : null;
  const market = stock.market_reference;
  const reports = stock.reports;
  const referenceLabel = market
    ? `Toss 저장 ${stockPrice(market.close_price)} · ${market.business_date} · ${dailyStoredTimeLabel(market.fetched_at)}`
    : "Toss 저장 기준값 없음";

  return (
    <section id={sectionId} className="daily-briefing selected-stock-panel" aria-labelledby={`${sectionId}-heading`}>
      <div className="section-header">
        <h2 id={`${sectionId}-heading`}>선택 종목</h2>
        <a className="market-context-link" href={`/daily/${date}/stocks/${stock.stock_code}`}>전체 종목 상세</a>
      </div>
      <div className="selected-stock-grid">
        <section className="selected-stock-context-card" aria-label="선택 종목 저장 근거">
          <h3>{stock.stock_name ?? stock.stock_code} ({stock.stock_code}) · {referenceLabel}</h3>
          <h4>데이터 기준</h4>
          <dl className="selected-stock-basis-grid">
            <div><dt>저장 가격 기준</dt><dd>{stockPriceBasis(stock)}</dd></div>
            <div><dt>거래대금 기준일</dt><dd>{stock.value_context.turnover_reference_date ?? "다음 확인 필요"}</dd></div>
            <div><dt>Toss 저장 기준일</dt><dd>{stock.value_context.toss_reference_date ?? "다음 확인 필요"}</dd></div>
            <div><dt>수급 기준일</dt><dd>{stock.value_context.investor_flow_reference_date ?? "다음 확인 필요"}</dd></div>
            <div><dt>리포트 기준일</dt><dd>{stock.value_context.report_reference_date ?? "다음 확인 필요"}</dd></div>
            <div><dt>뉴스 수집 상태</dt><dd>{stockNewsStatus(stock.value_context.news_collection_status)}</dd></div>
          </dl>
          {stock.value_context.missing_labels.length ? <p className="data-note">확인 공백 · {stockMissingLabels(stock.value_context.missing_labels)}</p> : null}
          <div className="selected-stock-ledger">
            <h4>근거 원장</h4>
            {selectedCandidate ? <>
              <p>상태 · {selectedCandidate.observation_priority} · {selectedCandidate.news_observation_badge.display_label || "저장 뉴스 없음"}</p>
              <p>해석 · {selectedCandidate.why_notable.join(" · ") || "저장 리포트 기준 후보"}</p>
              <p>리포트 근거 · 리포트 {reports.length}건 · {selectedCandidate.target_price_revision?.direction_label ?? "목표가 변경 참고 없음"}</p>
            </> : <p>상태 · 선택일 저장 종목의 리포트 상세</p>}
            <p>뉴스 근거 · {stock.news_observation_detail.connection_label ?? stock.news_observation_detail.display_label} · {stock.news_observation_detail.connection_reason ?? stock.news_observation_detail.reason}</p>
            <p>저장 기준 · {referenceLabel}</p>
            <a className="market-context-link" href={`/daily/${date}/main#toss-market-refresh`}>당일 시장 · 수급 보기</a>
          </div>
        </section>
        <section className="selected-stock-reports" aria-label="선택 종목 리포트">
          <div className="section-header"><h3>선택 종목 리포트</h3><span>전체 {reports.length}건</span></div>
          {reports.length ? <ul className="selected-stock-report-list">{reports.map((report, index) => <li key={`${report.published_at}-${index}`}>
            <h4>{report.title_display}</h4>
            <p>{report.broker_name || "증권사 자료 없음"} · {report.published_at.replace("T", " ").slice(0, 16)} · {report.target_price_display || "자료 없음"} · {report.opinion_display || "자료 없음"}</p>
          </li>)}</ul> : <Message>{stock.report_empty_state ?? "선택 날짜에 등록된 리포트가 없습니다."}</Message>}
        </section>
      </div>
      <details className="data-section selected-stock-history">
        <summary className="disclosure-summary">목표가 · 수급 · 거래량 · 업종/ETF · 뉴스 저장 이력</summary>
        <section className="data-section" aria-label="저장 리포트 목표가 흐름">
          <h3>저장 리포트 목표가 흐름</h3>
          {stock.target_price_trail.available ? (
            <>
              <p className="summary">{stock.target_price_trail.summary}</p>
              {stock.target_price_trail.attainment_percent === null ? null : (
                <p className="data-note">
                  선택일 저장값 · 현재가 {stockPrice(stock.target_price_trail.current_price)} · 최근 리포트 목표가 {stockPrice(stock.target_price_trail.current_target_price)} · 달성률 {stockPercent(stock.target_price_trail.attainment_percent)}
                </p>
              )}
              {stock.target_price_progress.validation_available ? (
                <p className="data-note">
                  저장 구간 도달 참고 · 하단 {stock.target_price_progress.hit_min_horizon_days === null ? "도달 확인 없음" : `${stock.target_price_progress.hit_min_horizon_days}거래일`}
                  · 상단 {stock.target_price_progress.hit_max_horizon_days === null ? "도달 확인 없음" : `${stock.target_price_progress.hit_max_horizon_days}거래일`}
                </p>
              ) : null}
            </>
          ) : <Message>{stock.target_price_trail.notice}</Message>}
          {stock.target_journey.available ? (
            <div className="table-wrap">
              <table>
                <caption className="eyebrow table-caption">선택일 이후 저장 가격 이력 · 고가 우선, 종가 보조</caption>
                <thead><tr><th scope="col">리포트 기준일</th><th scope="col">증권사</th><th scope="col">리포트 목표가</th><th scope="col">저장 가격 기록</th></tr></thead>
                <tbody>{stock.target_journey.items.map((item, index) => (
                  <tr key={`${item.report_date}-${item.broker_name}-${index}`}>
                    <td>{item.report_date}</td>
                    <td>{item.broker_name || "자료 없음"}</td>
                    <td>{item.target_price_display}</td>
                    <td>{targetJourneyStatus(item)}{item.revision_direction_label ? ` · 목표가 조정 ${item.revision_direction_label}` : ""}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <p className="data-note">{stock.target_journey.notice}</p>}
        </section>
        <section className="data-section" aria-label="저장 업종 테마와 ETF 참고">
          <h3>저장 업종·테마와 ETF 참고</h3>
          {stock.related_context.available ? (
            <ul className="status-list">{stock.related_context.categories.map((item, index) => (
              <li key={`${item.category_type}-${item.category_display_name}-${index}`}>
                <strong><a href={`/daily/${date}/category?${new URLSearchParams({
                  type: item.category_type,
                  display_name: item.category_display_name,
                  public_category_id: item.public_category_id,
                })}`}>{item.display}</a></strong>
                <span className="secondary"> · {item.related_etfs.length
                  ? item.related_etfs.map((etf) => `${etf.etf_name} (${etf.etf_code}) · ${etf.evidence_label}`).join(" / ")
                  : item.etf_notice}</span>
              </li>
            ))}</ul>
          ) : <Message>{stock.related_context.notice}</Message>}
          <p className="data-note">저장 분류와 수동 ETF 매핑 · 선택일 Toss ETF 기준 · 실시간 조회 없음</p>
        </section>
        <section className="data-section" aria-label="저장 수급과 거래량">
          <h3>저장 수급과 거래량</h3>
          <h4>기간별 수급량 · 단위 주</h4>
          {!stock.investor_flow_tabs.available
            ? <Message>{stock.investor_flow_tabs.notice || stock.investor_flow.notice}</Message>
            : null}
          {stock.investor_flow_tabs.available && !stock.investor_flow_tabs.exact_date_available ? (
            <p className="data-note">선택 날짜 수급이 없어 최근 저장일 {stock.investor_flow_tabs.reference_date ?? "자료 없음"} 기준 흐름을 표시합니다.</p>
          ) : null}
          {stock.investor_flow_tabs.retail_foreign_institution.length ? (
            <div className="table-wrap">
              <table>
                <caption className="eyebrow table-caption">Toss 저장 수급 · 기준일 {stock.investor_flow_tabs.reference_date ?? date}</caption>
                <thead><tr><th scope="col">날짜</th><th scope="col">개인</th><th scope="col">외국인</th><th scope="col">기관</th></tr></thead>
                <tbody>{stock.investor_flow_tabs.retail_foreign_institution.map((item) => (
                  <tr key={item.business_date}>
                    <td>{item.business_date}</td>
                    <td>{stockQuantity(item.individual)}</td>
                    <td>{stockQuantity(item.foreign)}</td>
                    <td>{stockQuantity(item.institution)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
          <h4>저장 거래량</h4>
          {!stock.recent_volume_days.available ? <Message>{stock.recent_volume_days.notice}</Message> : null}
          {stock.recent_volume_days.available && !stock.recent_volume_days.exact_date_available ? (
            <p className="data-note">선택 날짜 거래량이 없어 최근 저장일 {stock.recent_volume_days.reference_date ?? "자료 없음"} 기준 흐름을 표시합니다.</p>
          ) : null}
          {stock.recent_volume_days.items.length ? (
            <div className="table-wrap">
              <table>
                <caption className="eyebrow table-caption">Toss 저장 거래량 · 기준일 {stock.recent_volume_days.reference_date ?? date}</caption>
                <thead><tr><th scope="col">날짜</th><th scope="col">거래량</th><th scope="col">종가</th><th scope="col">등락률</th></tr></thead>
                <tbody>{stock.recent_volume_days.items.map((item) => (
                  <tr key={item.business_date}>
                    <td>{item.business_date}</td>
                    <td>{stockQuantity(item.volume)}</td>
                    <td>{stockPrice(item.close_price)}</td>
                    <td>{stockPercent(item.change_percent)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : null}
        </section>
        <section className="data-section" aria-label="저장 뉴스 관찰 상세">
          <h3>저장 뉴스 관찰</h3>
          <p className="summary">
            <strong>{stock.news_observation_detail.connection_label ?? stock.news_observation_detail.display_label}</strong>
            {" · "}{stock.news_observation_detail.connection_reason ?? stock.news_observation_detail.reason}
          </p>
          {stock.news_observation_detail.available ? (
            <p className="data-note">
              뉴스 근거 직접 {stock.news_observation_detail.direct_count ?? 0} · 주의 {stock.news_observation_detail.caution_count ?? 0}
              · 시장 맥락 {stock.news_observation_detail.market_context_count ?? 0} · {krxReferenceLabel(stock.news_observation_detail.krx_reference_status)}
            </p>
          ) : null}
          {stock.news_observation_detail.news_digest?.length ? (
            <ul className="status-list">{stock.news_observation_detail.news_digest.map((item, index) => (
              <li key={`${item.date}-${item.label}-${index}`}>
                <span className="secondary">{item.date} · {item.stock_name}</span>
                <strong>{item.label}</strong>
                <span className="secondary"> · {item.evidence_label} · {item.lineage_label}</span>
              </li>
            ))}</ul>
          ) : null}
          {!stock.news_observation_detail.news_digest?.length && stock.news_observation_detail.top_titles?.length ? (
            <ul className="status-list">{stock.news_observation_detail.top_titles.map((title) => <li key={title}>{title}</li>)}</ul>
          ) : null}
        </section>
      </details>
    </section>
  );
}
