"use client";

import { useState } from "react";
import Link from "next/link";

import type { CandidateEvidenceRow } from "@/domain/candidate-evidence";
import { dailyStoredTimeLabel, type DailyStockMarketReference } from "@/domain/daily";
import {
  isMainTop2IndicatorsSnapshot,
  isIntradayMarketTopSnapshot,
  isPriorityCurrentQuotesSnapshot,
  isPriorityQuoteSnapshot,
  isTossMarketContextSnapshot,
  indicatorHistoryStatusLabel,
  indicatorPriceChartBars,
  priceThresholdState,
  type IndicatorChartBar,
  type MainTop2IndicatorItem,
  type MainTop2IndicatorsSnapshot,
} from "@/domain/main-top2";

type Props = {
  businessDate: string;
  candidates: CandidateEvidenceRow[];
  marketReferences: { stock_code: string; market_reference: DailyStockMarketReference | null }[];
  canOverlapIntradayMarketTop: boolean;
  intradayMarketTopReason: string;
};
type RecordValue = Record<string, unknown>;
type IndicatorSeries = "rsi14" | "obv" | "macd" | "atr14" | "volume" | "hidden";

function record(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : {};
}

function text(value: unknown, fallback = "자료 없음"): string {
  return typeof value === "string" && value ? value : fallback;
}

function amount(value: unknown, suffix = "원"): string {
  const number = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
  return Number.isFinite(number) ? `${new Intl.NumberFormat("ko-KR").format(number)}${suffix}` : "자료 없음";
}

function percent(value: unknown): string {
  const number = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
  return Number.isFinite(number) ? `${number > 0 ? "+" : ""}${number.toFixed(2)}%` : "자료 없음";
}

function stateText(value: unknown): string {
  const map: Record<string, string> = {
    up: "상승 방향", down: "하락 방향", mixed: "혼합", neutral: "중립", insufficient_data: "자료 부족",
    up_aligned: "상승 방향 일치", down_aligned: "하락 방향 일치", below_threshold: "기준 미달", missing: "자료 없음",
    above_prior_20_bar_high: "직전 20봉 고가 초과", below_prior_10_bar_low: "직전 10봉 저가 하회", within_reference_band: "두 가격 기준 미도달",
    within_peak_volume_bins: "최고 거래량 구간 안", below_peak_volume_bins: "최고 거래량 구간 아래", above_peak_volume_bins: "최고 거래량 구간 위", between_peak_volume_bins: "최고 거래량 구간 사이",
    ready: "계산됨", "partial-data": "일부 자료", "insufficient-data": "자료 부족", "no-geometry": "조건에 맞는 구조 없음",
    paused: "일시 중지", unsupported: "지원하지 않음", error: "계산 오류", disabled: "비활성",
    forming: "형성 중", confirmed: "확인됨", "breakout-pending": "돌파 대기", failed: "유효하지 않음", expired: "만료", retested: "재확인",
    "volume-confirmed": "거래량 확인", "volume-insufficient": "거래량 부족",
    provider_unavailable: "Toss 자료를 가져오지 못했습니다.", provider_timeout: "Toss 응답 시간 초과", provider_http_error: "Toss 응답 오류",
    invalid_provider_response: "Toss 응답 형식 확인 필요", provider_response_mismatch: "종목 응답 확인 필요", unsupported_schema: "지원되지 않는 지표 형식",
    toss_not_configured: "Toss 연결 설정 대기", no_daily_candles: "기준 일봉 없음",
  };
  return map[String(value)] ?? text(value);
}

function useNoDataMessage(error: unknown): string {
  return error instanceof Error ? error.message : "조회에 실패했습니다. 다시 요청할 수 있습니다.";
}

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message" role="status" aria-live="polite" aria-atomic="true">{children}</p>;
}

async function jsonGet(path: string): Promise<{ response: Response; payload: unknown }> {
  const response = await fetch(path, { method: "GET", cache: "no-store" });
  let payload: unknown = null;
  try { payload = await response.json(); } catch { /* The route may return plain-text diagnostics. */ }
  return { response, payload };
}

function candidateDetailLabel(candidate: CandidateEvidenceRow): string {
  const labels = [
    candidate.report_summary.report_count ? `리포트 ${candidate.report_summary.report_count}건` : null,
    candidate.news_observation_badge.available && candidate.news_observation_badge.display_label.includes("재인용") ? "저장 뉴스" : null,
    candidate.target_price_revision?.available ? "목표가 변경" : (candidate.report_summary.target_price_min !== null || candidate.report_summary.target_price_max !== null ? "목표가 범위" : null),
  ].filter((value): value is string => !!value);
  return labels.join(" · ") || "저장 세부 근거";
}

function safeCandidateResearchUrl(value: string | undefined, kind: "search" | "report"): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return undefined;
    const allowed = kind === "search"
      ? url.hostname === "search.naver.com" && url.pathname === "/search.naver"
      : ["stock.naver.com", "finance.naver.com"].includes(url.hostname);
    return allowed ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export default function MainTop2Client({ businessDate, candidates, marketReferences, canOverlapIntradayMarketTop, intradayMarketTopReason }: Props) {
  const codes = candidates.map((item) => item.stock_code);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState("");
  const [quoteView, setQuoteView] = useState<{ source: "Toss" | "Naver"; data: RecordValue } | null>(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState("");
  const [marketView, setMarketView] = useState<RecordValue | null>(null);
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [intradayError, setIntradayError] = useState("");
  const [intradayView, setIntradayView] = useState<RecordValue | null>(null);
  const [indicatorLoading, setIndicatorLoading] = useState(false);
  const [indicatorError, setIndicatorError] = useState("");
  const [indicatorView, setIndicatorView] = useState<MainTop2IndicatorsSnapshot | null>(null);
  const [indicatorRange, setIndicatorRange] = useState(200);
  const [indicatorSeries, setIndicatorSeries] = useState<IndicatorSeries>("rsi14");

  async function loadQuoteReference() {
    setQuoteLoading(true); setQuoteError(""); setQuoteView(null);
    try {
      const toss = await jsonGet(`/api/toss-priority-quotes?date=${encodeURIComponent(businessDate)}`);
      const tossData = record(toss.payload);
      if (toss.response.status === 409) throw new Error(`Toss 현재가 조회는 최신 영업일 ${text(tossData.latest_business_date)}만 가능합니다.`);
      if (!toss.response.ok || !isPriorityQuoteSnapshot(toss.payload, businessDate, codes)) throw new Error("Toss 현재가 응답 형식을 확인할 수 없습니다.");
      const quotes = tossData.quotes as RecordValue[];
      if (tossData.configured === true && quotes.length === codes.length) {
        setQuoteView({ source: "Toss", data: tossData });
        return;
      }
      const naver = await jsonGet(`/api/priority-current-quotes?date=${encodeURIComponent(businessDate)}`);
      const naverData = record(naver.payload);
      if (naver.response.status === 409) throw new Error(`저장 기준일 ${text(naverData.latest_business_date)}에 한해 현재가 참고를 조회할 수 있습니다.`);
      if (!naver.response.ok || !isPriorityCurrentQuotesSnapshot(naver.payload, businessDate, codes)) throw new Error("Naver 현재가 참고 응답을 확인할 수 없습니다.");
      setQuoteView({ source: "Naver", data: naverData });
    } catch (error) { setQuoteError(useNoDataMessage(error)); }
    finally { setQuoteLoading(false); }
  }

  async function loadMarketContext() {
    setMarketLoading(true); setMarketError(""); setMarketView(null);
    try {
      const result = await jsonGet(`/api/toss-market-context?date=${encodeURIComponent(businessDate)}`);
      const payload = record(result.payload);
      if (result.response.status === 409) throw new Error(`시장 조회는 최신 영업일 ${text(payload.latest_business_date)}만 가능합니다.`);
      if (!result.response.ok || !isTossMarketContextSnapshot(result.payload, businessDate)) throw new Error("Toss 시장 참고 응답을 확인할 수 없습니다.");
      setMarketView(payload);
    } catch (error) { setMarketError(useNoDataMessage(error)); }
    finally { setMarketLoading(false); }
  }

  async function loadIntradayMarketTop() {
    setIntradayLoading(true); setIntradayError(""); setIntradayView(null);
    try {
      const path = `/api/daily/${encodeURIComponent(businessDate)}?intraday_market_top=1&market_top_limit=100&market_top_page_size=20`;
      const result = await jsonGet(path);
      if (!result.response.ok || !isIntradayMarketTopSnapshot(result.payload, businessDate, codes)) throw new Error("Naver 장중 거래대금 참고 응답을 확인할 수 없습니다.");
      setIntradayView(record(record(result.payload).market_commentary));
    } catch (error) { setIntradayError(useNoDataMessage(error)); }
    finally { setIntradayLoading(false); }
  }

  async function loadIndicators() {
    setIndicatorLoading(true); setIndicatorError(""); setIndicatorView(null);
    try {
      const result = await jsonGet(`/api/priority-indicators?date=${encodeURIComponent(businessDate)}`);
      if (!result.response.ok || !isMainTop2IndicatorsSnapshot(result.payload, businessDate, codes)) throw new Error("Main Top2 기술 지표 응답을 확인할 수 없습니다.");
      setIndicatorView(result.payload);
    } catch (error) { setIndicatorError(useNoDataMessage(error)); }
    finally { setIndicatorLoading(false); }
  }

  return (
    <section className="main-priority-card">
      <div className="section-header main-priority-heading">
        <h1>오늘의 우선순위</h1>
        <button id="toss-market-refresh" type="button" onClick={loadMarketContext} disabled={marketLoading}>{marketLoading ? "지수 · 수급 확인 중" : "지수 · 수급 확인"}</button>
      </div>
      <div className="main-priority-controls">
        <div className="main-priority-control-group" aria-label="장중 참고">
          <span className="main-priority-control-label">장중</span>
          <button type="button" onClick={loadQuoteReference} disabled={quoteLoading}>{quoteLoading ? "현재가 조회 중" : "Toss 현재가 · 수급"}</button>
          <button type="button" onClick={loadIntradayMarketTop} disabled={intradayLoading || !canOverlapIntradayMarketTop} title={!canOverlapIntradayMarketTop ? intradayMarketTopReason : undefined}>{intradayLoading ? "겹침 조회 중" : "거래대금 겹침"}</button>
        </div>
        <div className="main-priority-control-group" aria-label="차트 범위와 보조 지표">
          <label htmlFor="top2-daily-range">일봉 범위
            <select id="top2-daily-range" value={indicatorRange} onChange={(event) => setIndicatorRange(Number(event.target.value))}>
              <option value={50}>50거래일</option><option value={100}>100거래일</option><option value={200}>200거래일</option>
            </select>
          </label>
          <label htmlFor="top2-indicator-series">보조 지표
            <select id="top2-indicator-series" value={indicatorSeries} onChange={(event) => setIndicatorSeries(event.target.value as IndicatorSeries)}>
              <option value="rsi14">RSI 14</option><option value="obv">OBV</option><option value="macd">MACD 12·26·9</option><option value="atr14">ATR 14</option><option value="volume">거래량</option><option value="hidden">숨김</option>
            </select>
          </label>
          <button type="button" onClick={loadIndicators} disabled={indicatorLoading}>{indicatorLoading ? "차트 조회 중" : "차트 · 지표 확인"}</button>
        </div>
      </div>
      <section className="main-top2-candidates" aria-label="Main Top2 저장 후보">
        {candidates.map((candidate, index) => {
          const marketReference = marketReferences.find((item) => item.stock_code === candidate.stock_code)?.market_reference;
          return <article className="main-top2-candidate" key={candidate.stock_code}>
            <div className="main-top2-candidate-heading">
              <span className="candidate-rank">{index + 1}.</span>
              <h2><Link href={`/daily/${businessDate}/stocks?stock=${candidate.stock_code}#selected-stock`} prefetch={false}>{candidate.stock_name} ({candidate.stock_code})</Link></h2>
              <span className="candidate-priority">{candidate.observation_priority}</span>
            </div>
            <p>{candidate.why_notable.slice(0, 2).join(" · ") || "저장 후보 근거"}</p>
            <span className="main-top2-market-reference" title={marketReference
              ? `Toss 선택일 저장 ${amount(marketReference.close_price)} · 기준 ${marketReference.business_date} · 저장 ${dailyStoredTimeLabel(marketReference.fetched_at)} · 등락 ${percent(marketReference.change_percent)}`
              : `Toss 선택일 저장값 없음 · 기준일 ${businessDate}`}>
              {marketReference
                ? `Toss 선택일 저장 ${amount(marketReference.close_price)} · ${marketReference.business_date} ${dailyStoredTimeLabel(marketReference.fetched_at)}`
                : `Toss 선택일 저장값 없음 · ${businessDate}`}
            </span>
          </article>;
        })}
      </section>
      <section className="top-two-evidence-grid" aria-label="Main Top2 저장 근거">
        {candidates.map((candidate) => {
          const marketReference = marketReferences.find((item) => item.stock_code === candidate.stock_code)?.market_reference;
          return <details className="top-two-evidence-details" key={candidate.stock_code}>
              <summary><span>{candidateDetailLabel(candidate)}</span><span>기준 {businessDate}</span></summary>
              <div className="candidate-evidence-grid">
                <p><b>출처</b> · Naver 저장 리포트 · 기준일 {businessDate}</p>
                {marketReference ? <p><b>시장 기준</b> · Toss 저장 {amount(marketReference.close_price)} · {percent(marketReference.change_percent)} · 기준 {marketReference.business_date} · 저장 {dailyStoredTimeLabel(marketReference.fetched_at)}</p> : null}
                {candidate.evidence_layers.primary.length ? <p><b>주요 근거</b> · {candidate.evidence_layers.primary.join(" · ")}</p> : null}
                {candidate.evidence_layers.support.length ? <p><b>보조 근거</b> · {candidate.evidence_layers.support.join(" · ")}</p> : null}
                {candidate.evidence_layers.gap.length ? <p><b>확인 공백</b> · {candidate.evidence_layers.gap.join(" · ")}</p> : null}
                <p><b>리포트</b> · {candidate.report_summary.report_count}건 · 목표가 {amount(candidate.report_summary.target_price_min)} ~ {amount(candidate.report_summary.target_price_max)}</p>
                {candidate.target_price_revision?.available ? <p><b>목표가 변경 참고</b> · 이전 {candidate.target_price_revision.previous_date ?? "기준일 없음"} {amount(candidate.target_price_revision.previous_min)} ~ {amount(candidate.target_price_revision.previous_max)} → 현재 {amount(candidate.target_price_revision.current_min)} ~ {amount(candidate.target_price_revision.current_max)} · {candidate.target_price_revision.direction_label ?? "변경 정보 없음"}{typeof candidate.target_price_revision.previous_report_count === "number" ? ` · 이전 리포트 ${candidate.target_price_revision.previous_report_count}건` : ""}</p> : null}
                {candidate.research_focus?.items.length ? <div><b>연결된 원문 제목</b><ul className="status-list">{candidate.research_focus.items.slice(0, 3).map((item, itemIndex) => {
                  const reportUrl = item.source_kind === "리포트" ? safeCandidateResearchUrl(item.source_url, "report") : undefined;
                  const href = reportUrl ?? safeCandidateResearchUrl(item.search_url, "search");
                  return <li key={`${item.source_kind}-${item.source_title}-${itemIndex}`}>{item.source_title || item.topic}{href ? <> · <a href={href} target="_blank" rel="noopener noreferrer">{reportUrl ? "원문" : "Naver 검색"}</a></> : null}</li>;
                })}</ul></div> : null}
                <p><b>뉴스 상태</b> · {candidate.news_observation_badge.display_label || "저장 뉴스 없음"}</p>
                <p><b>누락 정보</b> · {candidate.missing_information.join(" · ") || "저장 누락 정보 없음"}</p>
              </div>
            </details>;
        })}
      </section>
      <p className="main-priority-status" aria-live="polite">Main Top2 저장 후보를 표시합니다. 차트 · 지표 확인을 누르면 선택일 자료를 조회합니다.</p>
      {quoteError ? <Message>{quoteError}</Message> : null}
      {marketError ? <Message>{marketError}</Message> : null}
      {intradayError ? <Message>{intradayError}</Message> : null}
      {indicatorError ? <Message>{indicatorError}</Message> : null}
      {quoteView ? <QuoteReference data={quoteView.data} source={quoteView.source} codes={codes} /> : null}
      {marketView ? <MarketContext data={marketView} /> : null}
      {intradayView ? <IntradayMarketTop data={intradayView} codes={codes} /> : null}
      {indicatorView ? <IndicatorsView payload={indicatorView} range={indicatorRange} series={indicatorSeries} /> : null}
    </section>
  );
}

function QuoteReference({ data, source, codes }: Readonly<{ data: RecordValue; source: "Toss" | "Naver"; codes: string[] }>) {
  const quoteMap = new Map<string, RecordValue>();
  const quotes = source === "Toss" ? data.quotes : data.items;
  if (Array.isArray(quotes)) for (const raw of quotes) {
    const item = record(raw);
    const code = String(source === "Toss" ? item.symbol ?? "" : item.stock_code ?? "");
    if (codes.includes(code)) quoteMap.set(code, item);
  }
  const investor = record(data.investor_trading);
  const investorMap = new Map<string, RecordValue>();
  if (Array.isArray(investor.items)) for (const raw of investor.items) {
    const item = record(raw); investorMap.set(String(item.symbol ?? ""), item);
  }
  const fetchedAt = text(source === "Toss" ? data.fetched_at : data.checked_at);
  return <section className="data-section" aria-label={`${source} 현재가 참고`}>
    <p className="data-note">출처: {source} · 기준일 {text(data.priority_date)} · 확인 시각: {fetchedAt} · {data.live_fetch === true ? "실시간 조회" : "저장/캐시 참고"} · 후보 순서 변경 없음</p>
    <div className="table-wrap"><table>
      <thead><tr><th scope="col">Main 후보</th><th scope="col">현재가 참고</th><th scope="col">등락</th><th scope="col">당일 수급 참고</th><th scope="col">기준 시각</th></tr></thead>
      <tbody>{codes.map((code) => {
        const item = quoteMap.get(code);
        const flow = investorMap.get(code);
        const currentPrice = source === "Toss" ? item?.lastPrice : item?.current_price;
        const change = source === "Toss" ? item?.changeRate : item?.change_percent;
        const referenceTime = source === "Toss" ? flow?.updated_at : item?.trade_time ?? item?.market_status;
        return <tr key={code}><td>{code}</td><td>{amount(currentPrice)}</td><td>{percent(change)}</td>
          <td>{flow ? `외국인 ${amount(flow.foreigner_net_buy_volume, "주")} · 기관 ${amount(flow.institution_net_buy_volume, "주")}` : source === "Toss" ? "수급 참고 없음" : text(item?.market_status, "수급 참고 없음")}</td><td>{text(referenceTime)}</td>
        </tr>;
      })}</tbody>
    </table></div>
    {source === "Toss" ? <p className="data-note">수급 기준일 {text(investor.reference_date)} · 기준 시각은 각 행의 updated_at으로 표시합니다. 수급은 provisional입니다.</p> : <p className="data-note">Naver fallback 참고 · 종목별 거래 시각은 행의 trade_time을 따릅니다.</p>}
    {data.cache === "stale" ? <p className="data-note">이전 조회값 · 마지막 성공 {text(data.fetched_at)} · 최신 조회 실패</p> : null}
  </section>;
}

function MarketContext({ data }: Readonly<{ data: RecordValue }>) {
  const prices = Array.isArray(data.market_prices) ? data.market_prices.map(record) : [];
  const flow = record(data.investor_flow);
  const marketName = (key: string) => key === "KOSPI" ? "코스피" : "코스닥";
  return <section className="data-section" aria-label="Toss 시장 참고 결과">
    <p className="data-note">출처: Toss · 기준일 {text(data.reference_date)} · 확인 시각 {text(data.fetched_at ?? data.ranked_at)} · 지수/수급 참고 전용</p>
    <div className="table-wrap"><table>
      <thead><tr><th scope="col">지수</th><th scope="col">현재 기준값</th><th scope="col">전일 대비</th></tr></thead>
      <tbody>{prices.filter((item) => ["KOSPI", "KOSDAQ"].includes(String(item.symbol))).map((item) => {
        const changes = record(data.market_price_changes); const change = record(changes[String(item.symbol)]);
        return <tr key={String(item.symbol)}><td>{marketName(String(item.symbol))}</td><td>{amount(item.lastPrice, "")}</td><td>{percent(typeof change.change_rate === "number" ? change.change_rate * 100 : null)}</td></tr>;
      })}</tbody>
    </table></div>
    <p className="data-note">Toss 잠정 시장 수급 · 기준 시각 20:20 KST 이후의 확정값을 의미하지 않습니다.</p>
    <div className="table-wrap"><table><thead><tr><th scope="col">시장</th><th scope="col">투자자</th><th scope="col">순매수 참고</th><th scope="col">기준 시각</th></tr></thead>
      <tbody>{["KOSPI", "KOSDAQ"].flatMap((market) => {
        const row = record(flow[market]);
        return ["individual", "foreigner", "institution"].map((investor) => {
          const amountRecord = record(row[investor]);
          const buy = Number(amountRecord.buyAmount); const sell = Number(amountRecord.sellAmount);
          const net = Number.isFinite(buy) && Number.isFinite(sell) ? buy - sell : null;
          return <tr key={`${market}-${investor}`}><td>{marketName(market)}</td><td>{investor === "individual" ? "개인" : investor === "foreigner" ? "외국인" : "기관"}</td><td>{amount(net, "원")}</td><td>{text(row.updatedAt, "자료 없음")}</td></tr>;
        });
      })}</tbody>
    </table></div>
    <p className="data-note">Top20 시장 순위와 후보 겹침 목록은 이 화면에서 후보 순서에 반영하지 않습니다.</p>
  </section>;
}

function IntradayMarketTop({ data, codes }: Readonly<{ data: RecordValue; codes: string[] }>) {
  const reference = record(data.intraday_market_top_reference);
  const quotes = record(data.intraday_quote_reference);
  const status = record(data.same_day_report_status);
  const items = Array.isArray(reference.items) ? reference.items.map(record) : [];
  const quoteItems = Array.isArray(quotes.items) ? quotes.items.map(record).filter((item) => codes.includes(String(item.stock_code))) : [];
  const errors = Array.isArray(reference.errors) ? reference.errors : [];
  const quoteErrors = Array.isArray(quotes.errors) ? quotes.errors : [];
  return <section className="data-section" aria-label="Naver 거래대금 겹침 결과">
    <p className="data-note">출처 Naver 장중 거래대금 상위 · 확인 시각 {text(reference.checked_at)} · 조회 {text(reference.calls, "0")}회 · 오류 {errors.length}건</p>
    {!status.can_overlap_intraday_market_top && !items.length ? <Message>{text(reference.empty_reason ?? status.reason)}</Message> : null}
    {items.length ? <div className="table-wrap"><table>
      <thead><tr><th scope="col">종목</th><th scope="col">시장/순위</th><th scope="col">현재가/등락</th><th scope="col">거래대금</th><th scope="col">리포트/겹침</th><th scope="col">거래 시각</th></tr></thead>
      <tbody>{items.map((item, index) => <tr key={`${String(item.stock_code)}-${index}`}>
        <td>{String(item.stock_name)} ({String(item.stock_code)})</td><td>{String(item.market)} · {String(item.rank)}위</td>
        <td>{amount(item.current_price)} · {percent(item.change_percent)}</td><td>{amount(item.trade_amount)}</td>
        <td>리포트 {String(item.mention_count)}건{codes.includes(String(item.stock_code)) ? " · Main Top2 포함" : ""}</td>
        <td>{text(item.trade_time ?? item.checked_at)}</td>
      </tr>)}</tbody>
    </table></div> : null}
    {reference.empty_reason && items.length ? <p className="data-note">{String(reference.empty_reason)}</p> : null}
    <h3>Main Top2 Naver 현재가 참고</h3>
    <p className="data-note">출처 {text(quotes.source)} · 조회 상태 {quotes.live_fetch === true ? "실시간 조회" : "조회 안 함"} · 오류 {quoteErrors.length}건</p>
    {quoteItems.length ? <div className="table-wrap"><table>
      <thead><tr><th scope="col">종목</th><th scope="col">현재가/등락</th><th scope="col">거래대금</th><th scope="col">거래 시각</th><th scope="col">종목 식별 출처</th></tr></thead>
      <tbody>{quoteItems.map((item, index) => <tr key={`${String(item.stock_code)}-${index}`}>
        <td>{String(item.stock_name)} ({String(item.stock_code)})</td><td>{amount(item.current_price)} · {percent(item.change_percent)}</td>
        <td>{amount(item.trade_amount)}</td><td>{text(item.trade_time ?? item.market_status)}</td><td>{item.resolution_source === "summary_stock_code" ? "저장 종목 코드" : "Naver 이름 검색"}</td>
      </tr>)}</tbody>
    </table></div> : <Message>Main Top2 Naver 현재가 자료가 없습니다.</Message>}
    <p className="data-note">거래대금 겹침은 참고 범위 표시이며 후보 생성이나 순위 변경에 쓰지 않습니다.</p>
  </section>;
}

function IndicatorsView({ payload, range, series }: Readonly<{ payload: MainTop2IndicatorsSnapshot; range: number; series: IndicatorSeries }>) {
  return <section className="data-section" aria-label="Main Top2 지표 응답">
    <p className="data-note">Toss 조정 일봉 · 기준일 {payload.business_date} · upstream 호출: {payload.live_fetch ? "있음" : "없음"} · DB 저장 없음 · 후보 순서 변경 없음</p>
    {payload.items.map((item) => item.available ? <IndicatorItem key={item.stock_code} item={item} range={range} series={series} /> : <article className="data-section" key={item.stock_code}>
      <h3>{item.stock_name} ({item.stock_code})</h3><Message>지표 자료 없음 · {stateText(item.reason)}</Message>
      <p className="data-note">시장 분류 출처: {text(item.market_source)} · 기준일 {text(item.market_source_date)}</p>
    </article>)}
  </section>;
}

function IndicatorPriceChart({ item, bars }: Readonly<{ item: MainTop2IndicatorItem; bars: IndicatorChartBar[] }>) {
  if (!bars.length) return <Message>표시할 수정주가 일봉이 없습니다.</Message>;
  const width = 1000, height = 350, left = 62, right = 10, priceTop = 28, priceBottom = 236, volumeTop = 278, volumeBottom = 326;
  const plotWidth = width - left - right, slotWidth = plotWidth / bars.length;
  const x = (index: number) => left + (index + 0.5) * slotWidth;
  const priceValues = bars.flatMap((bar) => [bar.high, bar.low, bar.sma20, bar.sma60, bar.sma120, bar.sma200].filter((value): value is number => value !== null));
  const unpaddedMin = Math.min(...priceValues), unpaddedMax = Math.max(...priceValues);
  const padding = Math.max((unpaddedMax - unpaddedMin) * 0.04, Math.abs(unpaddedMax) * 0.002, 0.01);
  const minPrice = unpaddedMin - padding, maxPrice = unpaddedMax + padding, priceRange = maxPrice - minPrice || 1;
  const y = (value: number) => priceTop + ((maxPrice - value) / priceRange) * (priceBottom - priceTop);
  const maxVolume = Math.max(1, ...bars.map((bar) => bar.volume));
  const candleWidth = Math.max(1.2, Math.min(9, slotWidth * 0.68));
  const dateIndex = new Map(bars.map((bar, index) => [bar.time, index]));
  const grid = Array.from({ length: 5 }, (_, index) => {
    const value = maxPrice - (maxPrice - minPrice) * index / 4;
    const lineY = y(value);
    return <g key={`grid-${index}`}><line x1={left} y1={lineY} x2={width - right} y2={lineY} /><text x="2" y={lineY + 4}>{new Intl.NumberFormat("ko-KR").format(value)}</text></g>;
  });
  let previousMonth = "";
  const monthMarks = bars.flatMap((bar, index) => {
    const month = bar.time.slice(0, 7);
    if (month === previousMonth) return [];
    previousMonth = month;
    const boundaryX = x(index) - slotWidth / 2;
    return [<g key={`month-${month}`}><line x1={boundaryX} y1={priceTop} x2={boundaryX} y2={volumeBottom} strokeDasharray="4 4" /><text x={Math.min(boundaryX + 3, width - 52)} y="15">{month.slice(5)}</text></g>];
  });
  const averageColors = { sma20: "#2563eb", sma60: "#f97316", sma120: "#8b5cf6", sma200: "#0f766e" } as const;
  const averageLines = Object.entries(averageColors).flatMap(([field, color]) => {
    const segments: string[][] = [];
    let points: string[] = [];
    for (let index = 0; index < bars.length; index++) {
      const value = bars[index][field as keyof IndicatorChartBar];
      if (typeof value !== "number") {
        if (points.length > 1) segments.push(points);
        points = [];
      } else points.push(`${x(index)},${y(value)}`);
    }
    if (points.length > 1) segments.push(points);
    return segments.map((line, index) => <polyline key={`${field}-${index}`} points={line.join(" ")} fill="none" stroke={color} strokeWidth="2.2" />);
  });
  const structures = <IndicatorStructureOverlay item={item} bars={bars} dateIndex={dateIndex} x={x} y={y} priceTop={priceTop} />;
  const latestClose = bars.at(-1)!.close;

  return <div className="indicator-price-chart-wrap">
    <svg className="indicator-price-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${item.stock_name} 수정주가 캔들, SMA 20·60·120·200, 거래량, 구조 측정`}>
      {grid}{monthMarks}{structures}
      {bars.map((bar, index) => {
        const candleX = x(index), color = bar.close > bar.open ? "#d34b43" : bar.close < bar.open ? "#3577c8" : "#7b8790";
        const volumeHeight = bar.volume / maxVolume * (volumeBottom - volumeTop);
        return <g key={bar.time}>
          <line x1={candleX} y1={y(bar.high)} x2={candleX} y2={y(bar.low)} stroke={color} strokeWidth="1.2" />
          <rect x={candleX - candleWidth / 2} y={Math.min(y(bar.open), y(bar.close))} width={candleWidth} height={Math.max(1, Math.abs(y(bar.open) - y(bar.close)))} fill={color} />
          <rect x={candleX - candleWidth / 2} y={volumeBottom - volumeHeight} width={candleWidth} height={volumeHeight} fill={color} fillOpacity=".32" />
        </g>;
      })}
      {averageLines}
      <line x1={left} y1={y(latestClose)} x2={width - right} y2={y(latestClose)} stroke="#c94d46" strokeDasharray="3 3" />
      <line x1={left} y1={volumeBottom} x2={width - right} y2={volumeBottom} />
      <text x={left} y={height - 4}>{bars[0].time}</text><text x={width - right - 70} y={height - 4}>{bars.at(-1)!.time}</text>
      <text x="2" y={volumeTop + 8}>거래량</text>
    </svg>
    <div className="indicator-chart-legend">
      {Object.entries(averageColors).map(([field, color]) => <span key={field}><i style={{ background: color }} />{field.toUpperCase()} · {amount(bars.at(-1)![field as keyof IndicatorChartBar])}</span>)}
      <span>캔들 · 수정주가</span><span>거래량</span>
    </div>
  </div>;
}

function IndicatorStructureOverlay({
  item, bars, dateIndex, x, y, priceTop,
}: Readonly<{
  item: MainTop2IndicatorItem;
  bars: IndicatorChartBar[];
  dateIndex: Map<string, number>;
  x: (index: number) => number;
  y: (value: number) => number;
  priceTop: number;
}>) {
  const structures = item.snapshot?.structures ?? [];
  const minPrice = Math.min(...bars.map((bar) => bar.low));
  const maxPrice = Math.max(...bars.map((bar) => bar.high));
  return <>{structures.map((structure, index) => {
    const rawMeasurements = Array.isArray(structure.measurements) ? structure.measurements.map(record) : [];
    const measurements = new Map(rawMeasurements.filter((entry) => typeof entry.name === "string").map((entry) => [String(entry.name), entry.value]));
    if (structure.family === "horizontal") {
      const boundary = Number(measurements.get("boundary"));
      if (!Number.isFinite(boundary) || boundary < minPrice || boundary > maxPrice) return null;
      const type = measurements.get("type");
      const label = type === "prior-20-high" ? `직전 20봉 고가 ${amount(boundary)}` : type === "prior-10-low" ? `직전 10봉 저가 ${amount(boundary)}` : "수평 기준";
      const lineY = y(boundary);
      return <g key={`structure-${index}`}><line x1="62" y1={lineY} x2="990" y2={lineY} stroke="#7c6aa6" strokeDasharray="6 4" strokeWidth="1.5" /><text x="70" y={Math.max(priceTop + 12, lineY - 4)} fill="#6c568f">{label}</text></g>;
    }
    let points: [number, number][] = [];
    if (structure.family === "flag") {
      for (const point of [1, 2, 3, 4]) {
        const barIndex = dateIndex.get(String(measurements.get(`geometry.points.${point}.time`) ?? ""));
        const price = Number(measurements.get(`geometry.points.${point}.price`));
        if (barIndex === undefined || !Number.isFinite(price)) { points = []; break; }
        points.push([x(barIndex), y(price)]);
      }
    } else if (structure.family === "triangle") {
      const start = dateIndex.get(String(measurements.get("geometry.points.1.time") ?? ""));
      const end = dateIndex.get(String(structure.barTime ?? ""));
      const prices = [
        Number(measurements.get("geometry.points.1.price")), Number(measurements.get("upperPrice")),
        Number(measurements.get("lowerPrice")), Number(measurements.get("geometry.points.3.price")),
      ];
      if (start !== undefined && end !== undefined && prices.every(Number.isFinite)) {
        points = [[x(start), y(prices[0])], [x(end), y(prices[1])], [x(end), y(prices[2])], [x(start), y(prices[3])]];
      }
    }
    if (points.length !== 4) return null;
    const label = structure.family === "flag" ? "채널 측정 구간" : "삼각 측정 구간 · 관측 봉";
    return <g key={`structure-${index}`}><polygon points={points.map(([pointX, pointY]) => `${pointX},${pointY}`).join(" ")} fill="#2563eb" fillOpacity=".08" stroke="#2563eb" strokeOpacity=".75" strokeWidth="1.6" /><text x={points[0][0]} y={Math.max(priceTop + 14, points[0][1] - 7)} fill="#1d4ed8">{label}</text></g>;
  })}</>;
}

function IndicatorAuxiliaryChart({ item, bars, series }: Readonly<{ item: MainTop2IndicatorItem; bars: IndicatorChartBar[]; series: IndicatorSeries }>) {
  if (series === "hidden") return <p className="data-note">보조 지표 표시를 숨겼습니다. 가격·거래량 차트는 계속 표시됩니다.</p>;
  if (!bars.length) return <Message>선택한 지표를 표시할 봉이 없습니다.</Message>;
  const width = 1000, height = 155, left = 62, right = 10, top = 18, bottom = 126;
  const slotWidth = (width - left - right) / bars.length, x = (index: number) => left + (index + 0.5) * slotWidth;
  const title = ({ rsi14: "RSI 14", macd: "MACD 12·26·9", obv: "OBV · 누적 거래량", atr14: "ATR 14", volume: "거래량", hidden: "" })[series];
  const values = bars.flatMap((bar) => series === "macd" ? [bar.macd, bar.macdSignal, bar.macdHistogram] : [bar[series]]).filter((value): value is number => typeof value === "number");
  if (!values.length) return <Message>{title} · 계산에 필요한 봉이 부족합니다.</Message>;
  let minValue = series === "rsi14" ? 0 : Math.min(...values), maxValue = series === "rsi14" ? 100 : Math.max(...values);
  if (series === "macd") { const extent = Math.max(Math.abs(minValue), Math.abs(maxValue), 0.001); minValue = -extent; maxValue = extent; }
  if (minValue === maxValue) { minValue -= 1; maxValue += 1; }
  const y = (value: number) => top + ((maxValue - value) / (maxValue - minValue)) * (bottom - top);
  const zeroY = y(series === "macd" ? 0 : minValue);
  const grid = series === "rsi14" ? [30, 50, 70].map((value) => <g key={value}><line x1={left} y1={y(value)} x2={width - right} y2={y(value)} strokeDasharray="4 4" /><text x="8" y={y(value) + 4}>{value}</text></g>) : <line x1={left} y1={zeroY} x2={width - right} y2={zeroY} />;
  const points = (key: "rsi14" | "obv" | "atr14") => bars.map((bar, index) => typeof bar[key] === "number" ? `${x(index)},${y(bar[key]!)}` : null).filter((point): point is string => point !== null).join(" ");
  const volumeMax = Math.max(1, ...bars.map((bar) => bar.volume));
  const plot = series === "macd" ? <>
    {bars.map((bar, index) => bar.macdHistogram === null ? null : <rect key={`hist-${bar.time}`} x={x(index) - Math.max(1.2, Math.min(8, slotWidth * .62)) / 2} y={Math.min(y(bar.macdHistogram), zeroY)} width={Math.max(1.2, Math.min(8, slotWidth * .62))} height={Math.max(1, Math.abs(zeroY - y(bar.macdHistogram)))} fill={bar.macdHistogram >= 0 ? "#d34b43" : "#3577c8"} fillOpacity=".65" />)}
    <polyline points={bars.map((bar, index) => bar.macd === null ? null : `${x(index)},${y(bar.macd)}`).filter((point): point is string => point !== null).join(" ")} fill="none" stroke="#2563eb" strokeWidth="2" />
    <polyline points={bars.map((bar, index) => bar.macdSignal === null ? null : `${x(index)},${y(bar.macdSignal)}`).filter((point): point is string => point !== null).join(" ")} fill="none" stroke="#f97316" strokeWidth="2" />
  </> : series === "volume" ? bars.map((bar, index) => {
    const barHeight = bar.volume / volumeMax * (bottom - top), previous = index ? bars[index - 1].close : bar.open;
    return <rect key={bar.time} x={x(index) - Math.max(1.2, Math.min(8, slotWidth * .62)) / 2} y={bottom - barHeight} width={Math.max(1.2, Math.min(8, slotWidth * .62))} height={barHeight} fill={bar.close >= previous ? "#d34b43" : "#3577c8"} fillOpacity=".72" />;
  }) : <polyline points={points(series)} fill="none" stroke={series === "rsi14" ? "#147d78" : series === "obv" ? "#147d78" : "#7c3aed"} strokeWidth="2.4" />;
  const line = series === "macd" ? "MACD 파랑 · 시그널 주황 · 막대는 두 선의 차이" : series === "rsi14" ? "RSI 14 · 점선은 30 / 50 / 70 참고선" : title;
  return <div className="indicator-aux-chart-wrap">
    <h4>{title}</h4>
    <svg className="indicator-aux-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${item.stock_name} ${title} 보조 지표 차트`}>
      {grid}{plot}<text x={left} y={height - 6}>{bars[0].time}</text><text x={width - right - 70} y={height - 6}>{bars.at(-1)!.time}</text>
    </svg>
    <p className="data-note">{line}</p>
  </div>;
}

function IndicatorItem({ item, range, series }: Readonly<{ item: MainTop2IndicatorItem; range: number; series: IndicatorSeries }>) {
  const snapshot = item.snapshot!; const chart = item.chart!; const conditions = item.price_conditions!;
  const confirmation = item.indicator_confirmation!; const indicators = record(snapshot.indicators);
  const moving = record(indicators.movingAverages); const bollinger = record(indicators.bollinger20);
  const donchian = record(indicators.donchian20); const rsi = record(indicators.rsi14); const macd = record(indicators.macd129);
  const volume = record(indicators.volume); const obv = record(indicators.obv); const atr = record(indicators.atr14);
  const profile = record(indicators.volumeProfile12);
  const visibleBars = indicatorPriceChartBars(chart.bars, range);
  const profileBins = Array.isArray(profile.bins) ? profile.bins.map(record) : [];
  const peaks = profileBins.filter((bin) => bin.peak === true);
  const structures = snapshot.structures;

  return <article className="main-top2-indicator-item" aria-label={`${item.stock_name} 기술 참고`}>
    <h3>{item.stock_name} ({item.stock_code})</h3>
    <p className="data-note">요청일 {item.requested_as_of} · 실제 봉 기준일 {text(snapshot.barAsOf)} · Toss 조회 시각 {text(snapshot.sourceFetchedAt)} · 봉 상태 {stateText(snapshot.barStatus)}</p>
    <p className="data-note">출처 {text(snapshot.source)} · 출처 기준일 {text(snapshot.sourceDate)} · {text(snapshot.confirmedPolicy)}</p>
    <section className="condition-card" aria-label="사용자 정의 가격 조건 상태">
      <h4>{text(item.condition_status)} · 사용자 정의 Main 조건</h4>
      <p>{text(item.condition_explanation)}</p>
      <p>선택일 종가 {amount(conditions.reference_close)} · 기준봉 {text(conditions.reference_bar_date)}</p>
      <p>진입 확인 기준: 종가가 직전 20봉 고가 {amount(conditions.prior_20_bar_high)} 초과 · {thresholdStateText(priceThresholdState(conditions.reference_close, conditions.prior_20_bar_high, "above"))}</p>
      <p>탈출 확인 기준: 종가가 직전 10봉 저가 {amount(conditions.prior_10_bar_low)} 하회 · {thresholdStateText(priceThresholdState(conditions.reference_close, conditions.prior_10_bar_low, "below"))}</p>
      <p>통합 가격 상태: {stateText(conditions.price_condition_state)} · 방향 일치: {stateText(confirmation.directional_alignment_state)} · 거래량: {stateText(confirmation.volume_confirmation_state)} ({typeof confirmation.volume_ratio20 === "number" ? `${confirmation.volume_ratio20.toFixed(2)}배` : "자료 없음"})</p>
    </section>

    <div className="indicator-chart-stack">
      <IndicatorPriceChart item={item} bars={visibleBars} />
      <IndicatorAuxiliaryChart item={item} bars={visibleBars} series={series} />
    </div>

    <section className="data-section" aria-label="계산 지표와 확인 상태">
      <h4>방향 지표와 보조 참고</h4>
      <div className="table-wrap"><table><thead><tr><th scope="col">항목</th><th scope="col">값</th><th scope="col">상태</th></tr></thead><tbody>
        <tr><th scope="row">SMA 20/60/120/200</th><td>{[20, 60, 120, 200].map((period) => amount(moving[`sma${period}`])).join(" / ")}</td><td>{stateText(confirmation.sma_state)}</td></tr>
        <tr><th scope="row">EMA 20/60/120/200</th><td>{[20, 60, 120, 200].map((period) => amount(moving[`ema${period}`])).join(" / ")}</td><td>{stateText(confirmation.ema_state)}</td></tr>
        <tr><th scope="row">WMA 20/60/120/200</th><td>{[20, 60, 120, 200].map((period) => amount(moving[`wma${period}`])).join(" / ")}</td><td>{stateText(confirmation.wma_state)}</td></tr>
        <tr><th scope="row">RSI 14</th><td>{typeof rsi.value === "number" ? rsi.value.toFixed(2) : "자료 없음"}</td><td>{stateText(confirmation.rsi_state)}</td></tr>
        <tr><th scope="row">MACD / Signal / Histogram</th><td>{[macd.macd, macd.signal, macd.histogram].map((value) => typeof value === "number" ? value.toFixed(3) : "자료 없음").join(" / ")}</td><td>{stateText(confirmation.macd_state)}</td></tr>
        <tr><th scope="row">Bollinger 20 · 하단/중간/상단</th><td>{[bollinger.lower, bollinger.middle, bollinger.upper].map((value) => amount(value)).join(" / ")}</td><td>{stateText(confirmation.bollinger_state)}</td></tr>
        <tr><th scope="row">Donchian 20 · 하단/중간/상단</th><td>{[donchian.lower, donchian.middle, donchian.upper].map((value) => amount(value)).join(" / ")}</td><td>{stateText(confirmation.donchian_state)}</td></tr>
        <tr><th scope="row">OBV / 5봉 변화</th><td>{[obv.value, obv.delta5].map((value) => typeof value === "number" ? new Intl.NumberFormat("ko-KR").format(value) : "자료 없음").join(" / ")}</td><td>{stateText(confirmation.obv_state)}</td></tr>
        <tr><th scope="row">거래량 비율 20</th><td>{typeof volume.ratio20 === "number" ? `${volume.ratio20.toFixed(2)}배` : "자료 없음"}</td><td>{stateText(confirmation.volume_confirmation_state)}</td></tr>
        <tr><th scope="row">ATR 14</th><td>{amount(atr.value)} · 종가 대비 {percent(confirmation.atr14_percent_of_close)}</td><td>방향 조건에는 미포함</td></tr>
      </tbody></table></div>
      <p className="data-note">각 계열 상태: {stateText(confirmation.directional_alignment_state)} · 기준봉 {text(conditions.reference_bar_date)} · 봉 확정성은 provider가 제공하지 않아 추정하지 않습니다.</p>
    </section>

    <section className="data-section" aria-label="거래량 프로파일 피크 구간">
      <h4>HLC3 거래량 프로파일 · 개별 peak bin</h4>
      <p className="data-note">현재 종가 위치: {stateText(confirmation.volume_profile_state)} · ATR14/peak bin은 방향 조건에 포함하지 않습니다.</p>
      {peaks.length ? <ul className="status-list">{peaks.map((bin, index) => <li key={`${String(bin.low)}-${index}`}>{amount(bin.low)} – {amount(bin.high)} · {typeof conditions.reference_close === "number" && conditions.reference_close >= Number(bin.low) && conditions.reference_close <= Number(bin.high) ? "종가가 구간 안" : "종가가 구간 밖"}</li>)}</ul> : <Message>peak bin 자료 없음</Message>}
    </section>

    <details className="data-section"><summary><strong>출처 · 이력 · 구조 측정 참고</strong></summary>
      <p className="data-note indicator-history">가져온 일봉: Toss {typeof item.candle_count === "number" ? item.candle_count : "자료 없음"}봉 · 차트 {visibleBars.length}봉 · {typeof item.pages_fetched === "number" ? item.pages_fetched : "자료 없음"}페이지 · {indicatorHistoryStatusLabel(item.history_status)}</p>
      {structures.length ? structures.map((structure, index) => <section className="data-section" key={`${String(structure.family)}-${index}`}>
        <h4>{String(structure.family)} · {stateText(structure.status)}</h4>
        {Array.isArray(structure.measurements) ? <ul className="status-list">{structure.measurements.map((raw, rowIndex) => {
          const measurement = record(raw); return <li key={`${String(measurement.name)}-${rowIndex}`}>{String(measurement.label)}: {String(measurement.value)} {String(measurement.unit)}</li>;
        })}</ul> : null}
      </section>) : <Message>저장 구조 측정이 없습니다.</Message>}
    </details>
  </article>;
}

function thresholdStateText(state: "reached" | "missed" | "insufficient_data"): string {
  return state === "reached" ? "가격 기준 도달" : state === "missed" ? "가격 기준 미도달" : "판정 불가 · 자료 부족";
}
