import "server-only";

import { notFound } from "next/navigation";
import Link from "next/link";

import { dailyFreshnessLabel, isBusinessDate, isDailySnapshot, type DailyStockMarketReference } from "@/domain/daily";
import { isCandidateEvidenceSnapshot } from "@/domain/candidate-evidence";
import type { DailyTabWorkspace } from "@/server/daily-tab-workspace";
import MainTop2Client from "@/components/client/main-top2";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function observationTimestampLabel(value: string | null, timezone: string): string {
  return value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value)) : "시각 자료 없음";
}

function latestCollectionLabel(value: string): string {
  return value === "matched" ? "매칭됨"
    : value === "no_match" ? "매칭 없음"
      : value === "not_collected" ? "수집 기록 없음" : "상태 확인 필요";
}

export default async function MainTop2Page({ params, workspace }: Readonly<{ params: Promise<{ date: string }>; workspace: DailyTabWorkspace }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  const payload: unknown = workspace.candidates;
  const dailySnapshot: unknown = workspace.daily;
  if (!payload) return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>Main · 우선 확인</h1><Message>저장된 후보를 불러오지 못했습니다.</Message></main>;
  if (!isCandidateEvidenceSnapshot(payload, date)) return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>Main · 우선 확인</h1><Message>후보 응답 형식을 확인할 수 없습니다.</Message></main>;
  const candidates = payload.rows.filter((row) => row.selected).slice(0, 2);
  const daily = isDailySnapshot(dailySnapshot, date) ? dailySnapshot : null;
  const briefingHeadline = daily?.market_briefing?.time_slot_mood_card?.headline ?? null;
  const canOverlapIntradayMarketTop = daily?.market_commentary?.same_day_report_status?.can_overlap_intraday_market_top ?? false;
  const intradayMarketTopReason = daily?.market_commentary?.same_day_report_status?.reason ?? "저장된 당일 상태를 확인할 수 없습니다.";
  const evidencePoints = candidates.map((candidate) =>
    `${candidate.stock_name}: ${candidate.why_notable.slice(0, 2).join(" · ") || "저장 리포트 기준 후보"}`
  );
  const missingPoints = candidates.flatMap((candidate) =>
    candidate.missing_information.slice(0, 1).map((item) => `${candidate.stock_name}: ${item}`)
  ).slice(0, 2);
  const marketPoint = daily?.market_briefing?.time_slot_mood_card?.sections
    ?.find((section) => section.key === "core_points")?.items
    ?.find((item) => !item.startsWith("리포트 "))
    ?.replace(/^지수 참고:\s*/, "");
  const news = daily?.news_observation_summary;
  const newsTitles = news?.top_titles?.filter(Boolean).slice(0, 3) ?? [];
  const perStockNews = news?.items?.slice(0, 6) ?? [];
  const featuredNews = perStockNews.find((item) => item.connection_label === news?.display_label) ?? perStockNews[0];
  const observedAt = news?.observed_at
    ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: daily?.timezone || "Asia/Seoul" }).format(new Date(news.observed_at))
    : null;
  const krxNewsStatus: Record<string, string> = {
    exact: "KRX 선택일 기준",
    current: "KRX 선택일 기준",
    stale: "KRX 기준일 이전값",
    missing: "KRX 기준 자료 없음",
    unavailable: "KRX 참고 없음",
    disabled: "KRX 참고 미사용",
  };
  const marketReferences: { stock_code: string; market_reference: DailyStockMarketReference | null }[] = candidates.map((candidate) => ({
    stock_code: candidate.stock_code,
    market_reference: daily?.stocks.find((stock) => stock.stock_code === candidate.stock_code)?.market_reference ?? null,
  }));
  return (
    <main className="main-board">
      {!candidates.length ? <section className="main-priority-card"><h1>오늘의 관찰</h1><Message>선택일 저장 후보가 없습니다.</Message></section> : <MainTop2Client
        businessDate={date}
        briefingHeadline={briefingHeadline}
        reportCount={daily?.report_count ?? null}
        summaryStockCount={daily?.summary_stock_count ?? null}
        candidates={candidates}
        marketReferences={marketReferences}
        canOverlapIntradayMarketTop={canOverlapIntradayMarketTop}
        intradayMarketTopReason={intradayMarketTopReason}
      />}
      <div className="main-reading-grid">
        <section className="main-news-feature news-observation-summary" aria-labelledby="main-news-heading">
          <div className="news-observation-summary-head">
            <h2 id="main-news-heading">{news?.display_label || "뉴스 관찰"}</h2><span className="status-pill">저장 뉴스</span>
            {observedAt && news?.observed_at ? <time dateTime={news.observed_at}>수집 시각 {observedAt}</time> : <span>수집 시각 없음</span>}
          </div>
          <div className="main-news-feature-grid">
            <div>
              <p>{news?.reason ?? "뉴스 관찰 상태를 확인할 수 없습니다."}</p>
              <p>{news?.connection_note || (news?.available ? "저장 뉴스 관찰 상태입니다." : "우선 확인 후보와 연결할 저장 뉴스 관찰이 없습니다.")}</p>
              {featuredNews ? <div className="news-observation-summary-featured">
                <b>{featuredNews.connection_label || featuredNews.display_label}</b>
                {/^[0-9]{6}$/.test(featuredNews.stock_code ?? "")
                  ? <Link href={`/daily/${date}/stocks?stock=${featuredNews.stock_code}#selected-stock`} prefetch={false}>{featuredNews.stock_name} ({featuredNews.stock_code})</Link>
                  : <span>{featuredNews.stock_name}</span>}
                {featuredNews.top_title || featuredNews.reason ? <p>{featuredNews.top_title || featuredNews.reason}</p> : null}
                <span>직접 {featuredNews.direct_count}건 · 주의 {featuredNews.caution_count}건 · 시장 맥락 {featuredNews.market_context_count}건 · {krxNewsStatus[featuredNews.krx_reference_status] || "KRX 참고 상태 확인"} · 최근 수집 {latestCollectionLabel(featuredNews.latest_collection_status)} {featuredNews.latest_collection_at ? observationTimestampLabel(featuredNews.latest_collection_at, daily?.timezone || "Asia/Seoul") : "시각 자료 없음"}</span>
              </div> : null}
            </div>
            <div>
              {news?.available && newsTitles.length ? <ul className="news-observation-summary-titles">{newsTitles.map((title) => <li key={title}>{title}</li>)}</ul> : null}
              <div className="news-observation-summary-meta">
                {typeof news?.candidate_overlap_count === "number" ? <span>Main 후보 겹침 {news.candidate_overlap_count}종목</span> : null}
                {typeof news?.direct_count === "number" ? <span>직접 근거 {news.direct_count}건</span> : null}
                {typeof news?.caution_count === "number" ? <span>주의 근거 {news.caution_count}건</span> : null}
                {typeof news?.market_context_count === "number" ? <span>시장 맥락 {news.market_context_count}건</span> : null}
                {news?.krx_reference_status ? <span>{krxNewsStatus[news.krx_reference_status] || "KRX 참고 상태 확인"}</span> : null}
              </div>
              {news?.missing_context.length ? <p className="data-note">추가 맥락 확인 공백 {news.missing_context.length}건</p> : null}
            </div>
          </div>
        </section>
        <section className="daily-briefing main-readout" aria-labelledby="daily-briefing-heading">
          <header className="main-readout-heading">
            <h2 id="daily-briefing-heading">근거와 확인 공백</h2>
            <span>읽기 메모 · {date}</span>
          </header>
          <dl className="briefing-ledger">
            <div><dt>관찰 이유</dt><dd>{evidencePoints.join(" / ") || "저장 후보 자료 없음"}</dd></div>
            <div><dt>확인 공백</dt><dd>{missingPoints.join(" / ") || "저장 후보 자료에 표시된 누락 항목 없음"}</dd></div>
            {marketPoint ? <div><dt>지수 요약</dt><dd>{marketPoint}</dd></div> : null}
          </dl>
        </section>
        <aside className="main-proof-rail" aria-labelledby="main-source-heading">
          <h2 id="main-source-heading" className="main-proof-heading">출처 원장 / 기준 시점</h2>
          <section className="source-freshness-summary">
            <div className="source-freshness-head"><b>데이터 기준</b><span className="status-pill">저장 상태</span></div>
            {daily?.source_freshness_summary.items.length ? <ul className="source-freshness-items">
              {daily.source_freshness_summary.items.map((item) => {
                const count = item.count === undefined ? "" : ` · ${new Intl.NumberFormat("ko-KR").format(item.count)}건`;
                const coverage = item.coverage_count === undefined || item.candidate_count === undefined
                  ? "" : ` · 후보 ${new Intl.NumberFormat("ko-KR").format(item.coverage_count)}/${new Intl.NumberFormat("ko-KR").format(item.candidate_count)}`;
                return <li className="source-freshness-item" key={item.key}>
                  <b>{item.label}</b><span>{dailyFreshnessLabel(item, date)}</span><span>{item.reference_date ? `기준 ${item.reference_date}` : "기준일 없음"}{count}{coverage}</span>
                </li>;
              })}
            </ul> : <p className="data-note">저장 source 상태를 확인할 수 없습니다.</p>}
          </section>
        </aside>
      </div>
      <nav className="main-reference-links" aria-label="선택일 기록">
        <Link href={`/daily/${date}/intraday`} prefetch={false}>장중 기록 보기 →</Link>
      </nav>
    </main>
  );
}
