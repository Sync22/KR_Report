import "server-only";

import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isStockDetailSnapshot, type StockDetailSnapshot } from "@/domain/stocks";
import { getStockDetailSnapshot } from "@/server/stock-detail";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function price(value: number | null): string {
  return value === null ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}원`;
}

function percent(value: number | null): string {
  return value === null ? "자료 없음" : `${value > 0 ? "+" : ""}${new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 2 }).format(value)}%`;
}

function quantity(value: number | null): string {
  return value === null ? "자료 없음" : `${new Intl.NumberFormat("ko-KR").format(value)}주`;
}

function dateLabel(value: string | null): string {
  return value ?? "다음 확인 필요";
}

function priceBasisLabel(context: StockDetailSnapshot["value_context"]): string {
  const time = context.current_price_reference_time ?? "";
  if (context.current_price_basis === "20:00 stored") return time ? `${time.slice(11, 16) || "20:00"} 저장` : "20:00 저장";
  if (context.current_price_basis === "Toss stored snapshot") return time ? `${time.replace("T", " ").slice(0, 16)} 저장` : "Toss 저장";
  return "다음 확인 필요";
}

function newsCollectionLabel(value: string): string {
  if (value === "stored_evidence") return "최신 저장 기준";
  if (value === "stored_no_match") return "매칭 뉴스 없음";
  return "다음 확인 필요";
}

function missingReferenceLabels(values: string[]): string {
  const labels: Record<string, string> = {
    report: "리포트",
    toss: "Toss",
    current_price: "현재가",
    turnover: "거래대금",
    investor_flow: "수급",
  };
  return values.map((value) => labels[value] ?? "기준 자료").join(", ");
}

function krxReferenceLabel(value: string | undefined): string {
  if (value === "exact") return "KRX 당일";
  if (value === "stale") return "KRX 이전 기준";
  return "KRX 없음";
}

function timestampLabel(value: string, timezone: string): string {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value));
}

function targetJourneyStatus(item: StockDetailSnapshot["target_journey"]["items"][number]): string {
  const observed = item.observed_through ? ` · 관측 ${item.observed_through}` : "";
  if (item.status === "hit") return `달성 · ${item.hit_trading_days === 0 ? "당일" : `${item.hit_trading_days ?? "-"}영업일`}${observed}`;
  if (item.status === "in_progress") {
    const parts = ["진행 중"];
    if (item.current_attainment_percent !== null) parts.push(`현재 ${percent(item.current_attainment_percent)}`);
    if (item.max_attainment_percent !== null) parts.push(`최대 ${percent(item.max_attainment_percent)}`);
    if (item.observed_through) parts.push(`관측 ${item.observed_through}`);
    return parts.join(" · ");
  }
  return "가격 검증 대기";
}

function safeReportUrl(value: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

export default async function StockDetailPage({
  params,
}: Readonly<{ params: Promise<{ date: string; stock_code: string }> }>) {
  const { date, stock_code: stockCode } = await params;
  if (!isBusinessDate(date) || !/^\d{6}$/.test(stockCode)) notFound();

  let payload: unknown;
  try {
    payload = getStockDetailSnapshot(date, stockCode);
  } catch {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>종목 상세</h1>
        <Message>저장된 종목 정보를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.</Message>
      </main>
    );
  }
  if (!isStockDetailSnapshot(payload, date, stockCode)) {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>종목 상세</h1>
        <Message>종목 상세 응답 형식을 확인할 수 없습니다.</Message>
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
      <h1>{payload.stock_name ?? payload.stock_code} <span className="secondary">({payload.stock_code})</span></h1>
      <p className="updated">
        기준일 {payload.business_date} · 조회 시각: <time dateTime={payload.now}>{updatedAt} KST</time>
      </p>

      <section className="data-section" aria-labelledby="market-heading">
        <h2 id="market-heading">저장 시장 참고</h2>
        {payload.market_reference ? (
          <p className="data-note">
            Toss 저장 스냅샷 · {payload.market_reference.business_date} · {payload.market_reference.market ?? "시장 자료 없음"}
            · 종가 {price(payload.market_reference.close_price)} · 등락 {percent(payload.market_reference.change_percent)}
            · 저장 시각 <time dateTime={payload.market_reference.fetched_at}>{timestampLabel(payload.market_reference.fetched_at, payload.timezone)}</time>
          </p>
        ) : (
          <Message>선택일의 Toss 저장 시장 참고가 없습니다. 다른 날짜 값으로 대체하지 않습니다.</Message>
        )}
      </section>
      <p><a className="market-context-link" href={`/daily/${date}/main#toss-market-refresh`}>당일 시장 · 수급 보기</a></p>

      <section className="data-section" aria-labelledby="basis-heading">
        <h2 id="basis-heading">저장 데이터 기준</h2>
        <ul className="status-list">
          <li>리포트 기준일: {dateLabel(payload.value_context.report_reference_date)}</li>
          <li>저장 가격 기준: {priceBasisLabel(payload.value_context)}</li>
          <li>거래대금 기준일: {dateLabel(payload.value_context.turnover_reference_date)}</li>
          <li>Toss 저장 기준일: {dateLabel(payload.value_context.toss_reference_date)}</li>
          <li>수급 기준일: {dateLabel(payload.value_context.investor_flow_reference_date)}</li>
          <li>뉴스 수집 상태: {newsCollectionLabel(payload.value_context.news_collection_status)}</li>
        </ul>
        {payload.value_context.missing_labels.length ? (
          <p className="data-note">기준 확인 필요: {missingReferenceLabels(payload.value_context.missing_labels)}</p>
        ) : null}
      </section>

      <section className="data-section" aria-labelledby="target-heading">
        <h2 id="target-heading">저장 리포트 목표가 흐름</h2>
        {payload.target_price_trail.available ? (
          <>
            <p className="summary">{payload.target_price_trail.summary}</p>
            {payload.target_price_trail.attainment_percent === null ? null : (
              <p className="data-note">
                선택일 저장값 · 현재가 {price(payload.target_price_trail.current_price)} · 최근 리포트 목표가 {price(payload.target_price_trail.current_target_price)} · 달성률 {percent(payload.target_price_trail.attainment_percent)}
              </p>
            )}
            {payload.target_price_progress.validation_available ? (
              <p className="data-note">
                저장 구간 도달 참고 · 하단 {payload.target_price_progress.hit_min_horizon_days === null ? "도달 확인 없음" : `${payload.target_price_progress.hit_min_horizon_days}거래일`}
                · 상단 {payload.target_price_progress.hit_max_horizon_days === null ? "도달 확인 없음" : `${payload.target_price_progress.hit_max_horizon_days}거래일`}
              </p>
            ) : null}
          </>
        ) : (
          <Message>{payload.target_price_trail.notice}</Message>
        )}
        {payload.target_journey.available ? (
          <div className="table-wrap">
            <table>
              <caption className="eyebrow table-caption">선택일 이후 저장 가격 이력 · 고가 우선, 종가 보조</caption>
              <thead><tr><th scope="col">리포트 기준일</th><th scope="col">증권사</th><th scope="col">리포트 목표가</th><th scope="col">저장 가격 기록</th></tr></thead>
              <tbody>
                {payload.target_journey.items.map((item, index) => (
                  <tr key={`${item.report_date}-${item.broker_name}-${index}`}>
                    <td>{item.report_date}</td>
                    <td>{item.broker_name || "자료 없음"}</td>
                    <td>{item.target_price_display}</td>
                    <td>{targetJourneyStatus(item)}{item.revision_direction_label ? ` · 목표가 조정 ${item.revision_direction_label}` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="data-note">{payload.target_journey.notice}</p>
        )}
      </section>

      <section className="data-section" aria-labelledby="related-heading">
        <h2 id="related-heading">저장 업종·테마와 ETF 참고</h2>
        {payload.related_context.available ? (
          <ul className="status-list">
            {payload.related_context.categories.map((item, index) => (
              <li key={`${item.category_type}-${item.category_display_name}-${index}`}>
                <strong><a href={`/daily/${date}/category?${new URLSearchParams({ type: item.category_type, display_name: item.category_display_name, public_category_id: item.public_category_id })}`}>{item.display}</a></strong>
                <span className="secondary"> · {item.related_etfs.length ? item.related_etfs.map((etf) => `${etf.etf_name} (${etf.etf_code}) · ${etf.evidence_label}`).join(" / ") : item.etf_notice}</span>
              </li>
            ))}
          </ul>
        ) : (
          <Message>{payload.related_context.notice}</Message>
        )}
        <p className="data-note">저장 분류와 수동 ETF 매핑 · 선택일 저장 ETF 기준 · 실시간 조회 없음</p>
      </section>

      <section className="data-section" aria-labelledby="flow-heading">
        <h2 id="flow-heading">저장 수급과 거래량</h2>
        <h3>기간별 수급량 · 단위 주</h3>
        {!payload.investor_flow_tabs.available ? <Message>{payload.investor_flow_tabs.notice || payload.investor_flow.notice}</Message> : null}
        {payload.investor_flow_tabs.available && !payload.investor_flow_tabs.exact_date_available ? (
          <p className="data-note">선택 날짜 수급이 없어 최근 저장일 {payload.investor_flow_tabs.reference_date ?? "자료 없음"} 기준 흐름을 표시합니다.</p>
        ) : null}
        {payload.investor_flow_tabs.retail_foreign_institution.length ? (
          <div className="table-wrap">
            <table>
              <caption className="eyebrow table-caption">기준일 {payload.investor_flow_tabs.reference_date ?? date}</caption>
              <thead><tr><th scope="col">날짜</th><th scope="col">개인</th><th scope="col">외국인</th><th scope="col">기관</th></tr></thead>
              <tbody>
                {payload.investor_flow_tabs.retail_foreign_institution.map((item) => (
                  <tr key={item.business_date}><td>{item.business_date}</td><td>{quantity(item.individual)}</td><td>{quantity(item.foreign)}</td><td>{quantity(item.institution)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <h3>저장 거래량</h3>
        {!payload.recent_volume_days.available ? <Message>{payload.recent_volume_days.notice}</Message> : null}
        {payload.recent_volume_days.available && !payload.recent_volume_days.exact_date_available ? (
          <p className="data-note">선택 날짜 거래량이 없어 최근 저장일 {payload.recent_volume_days.reference_date ?? "자료 없음"} 기준 흐름을 표시합니다.</p>
        ) : null}
        {payload.recent_volume_days.items.length ? (
          <div className="table-wrap">
            <table>
              <caption className="eyebrow table-caption">Toss 저장 거래량 · 기준일 {payload.recent_volume_days.reference_date ?? date}</caption>
              <thead><tr><th scope="col">날짜</th><th scope="col">거래량</th><th scope="col">종가</th><th scope="col">등락률</th></tr></thead>
              <tbody>
                {payload.recent_volume_days.items.map((item) => (
                  <tr key={item.business_date}><td>{item.business_date}</td><td>{quantity(item.volume)}</td><td>{price(item.close_price)}</td><td>{percent(item.change_percent)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="data-section" aria-labelledby="reports-heading">
        <h2 id="reports-heading">선택일 리포트</h2>
        {payload.reports.length === 0 ? (
          <Message>{payload.report_empty_state ?? "선택 날짜에 등록된 리포트가 없습니다."}</Message>
        ) : (
          <div className="table-wrap">
            <table>
              <caption className="eyebrow table-caption">저장 리포트 {payload.reports.length}건</caption>
              <thead>
                <tr>
                  <th scope="col">리포트</th>
                  <th scope="col">증권사</th>
                  <th scope="col">작성 시각</th>
                  <th scope="col">리포트 목표가</th>
                  <th scope="col">리포트 의견 표기</th>
                </tr>
              </thead>
              <tbody>
                {payload.reports.map((report, index) => {
                  const href = safeReportUrl(report.source_url);
                  return (
                    <tr key={`${report.published_at}-${index}`}>
                      <td>{href ? <a href={href} target="_blank" rel="noreferrer">{report.title_display}</a> : report.title_display}</td>
                      <td>{report.broker_name || "자료 없음"}</td>
                      <td><time dateTime={report.published_at}>{report.published_at.replace("T", " ").slice(0, 16)}</time></td>
                      <td>{report.target_price_display || "자료 없음"}</td>
                      <td>{report.opinion_display || "자료 없음"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="data-section" aria-labelledby="news-heading">
        <h2 id="news-heading">저장 뉴스 관찰</h2>
        <p className="summary">
          <strong>{payload.news_observation_detail.connection_label ?? payload.news_observation_detail.display_label}</strong> · {payload.news_observation_detail.connection_reason ?? payload.news_observation_detail.reason}
        </p>
        {payload.news_observation_detail.available ? (
          <p className="data-note">
            뉴스 근거 직접 {payload.news_observation_detail.direct_count ?? 0} · 주의 {payload.news_observation_detail.caution_count ?? 0}
            · 시장 맥락 {payload.news_observation_detail.market_context_count ?? 0} · {krxReferenceLabel(payload.news_observation_detail.krx_reference_status)}
          </p>
        ) : null}
        {payload.news_observation_detail.news_digest?.length ? (
          <ul className="status-list">
            {payload.news_observation_detail.news_digest.map((item, index) => (
              <li key={`${item.date}-${item.label}-${index}`}>
                <span className="secondary">{item.date} · {item.stock_name}</span>
                <strong>{item.label}</strong>
                <span className="secondary"> · {item.evidence_label} · {item.lineage_label}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {!payload.news_observation_detail.news_digest?.length && payload.news_observation_detail.top_titles?.length ? (
          <ul className="status-list">
            {payload.news_observation_detail.top_titles.map((title) => <li key={title}>{title}</li>)}
          </ul>
        ) : null}
      </section>

      <p className="footer-link">
        <a href={`/daily/${date}`}>일일 화면으로 돌아가기</a> · <a href={`/daily/${date}/stocks`}>종목 검색</a>
      </p>
    </main>
  );
}
