import "server-only";

import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isCandidateEvidenceSnapshot } from "@/domain/candidate-evidence";
import SelectedStockPanel from "@/components/server/selected-stock-panel";
import type { DailyTabWorkspace } from "@/server/daily-tab-workspace";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

export default async function CandidateEvidencePage({
  params,
  searchParams,
  workspace,
}: Readonly<{
  params: Promise<{ date: string }>;
  searchParams: Promise<{ stock?: string | string[] }>;
  workspace: DailyTabWorkspace;
}>) {
  const [{ date }, query] = await Promise.all([params, searchParams]);
  if (!isBusinessDate(date)) notFound();

  const payload: unknown = workspace.candidates;
  if (!payload) {
    return (
      <main>
        <section className="daily-briefing watch-candidate-panel" aria-labelledby="watch-candidates-heading">
          <div className="section-header"><h1 id="watch-candidates-heading">오늘의 관찰 후보 ({date})</h1><span className="status-pill">우선 확인</span></div>
          <Message>저장 후보 근거를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.</Message>
        </section>
      </main>
    );
  }

  if (!isCandidateEvidenceSnapshot(payload, date)) {
    return (
      <main>
        <section className="daily-briefing watch-candidate-panel" aria-labelledby="watch-candidates-heading">
          <div className="section-header"><h1 id="watch-candidates-heading">오늘의 관찰 후보 ({date})</h1><span className="status-pill">우선 확인</span></div>
          <Message>후보 근거 응답 형식을 확인할 수 없습니다.</Message>
        </section>
      </main>
    );
  }

  const requestedStockCode = Array.isArray(query.stock) ? null : query.stock ?? null;
  const selectedCandidate = requestedStockCode
    ? payload.rows.find((item) => item.stock_code === requestedStockCode) ?? null
    : null;

  return (
    <main>
      <section className="daily-briefing watch-candidate-panel" aria-labelledby="watch-candidates-heading">
        <div className="section-header">
          <h1 id="watch-candidates-heading">오늘의 관찰 후보 <span className="secondary">({payload.business_date})</span></h1>
          <span className="status-pill">우선 확인</span>
        </div>
        <p className="brief">후보를 고르면 종목 탭에서 리포트, 뉴스 근거, 가격·수급 기준을 한 번에 확인합니다.</p>
        <p className="data-note">서버가 정한 저장 후보 순서 · 기준일 {payload.business_date} · 실시간 조회 없음</p>

        {!payload.available || payload.rows.length === 0 ? (
          <Message>선택한 날짜에 저장된 관찰 후보가 없습니다.</Message>
        ) : (
          <div className="watch-candidate-grid" aria-label="저장 관찰 후보">
            {payload.rows.map((item, index) => {
              const news = item.news_observation_badge;
              const newsLabel = index >= 2 && news.available !== true
                ? "Top2 뉴스 수집 대상 아님"
                : news.connection_label ?? news.display_label ?? "저장 뉴스 없음";
              const missing = item.missing_information.length
                ? ` · 확인 공백 ${item.missing_information.join(" · ")}`
                : "";
              return (
                <a
                  className="watch-candidate-card"
                  href={`/daily/${date}/stocks?${new URLSearchParams({ stock: item.stock_code })}#selected-stock`}
                  aria-current={selectedCandidate?.stock_code === item.stock_code ? "page" : undefined}
                  key={item.stock_code}
                >
                  <div className="watch-candidate-heading">
                    <div><span className="watch-candidate-rank">{index + 1}.</span> <strong>{item.stock_name} ({item.stock_code})</strong></div>
                    <span className="candidate-priority">{item.observation_priority}</span>
                  </div>
                  <p className="watch-candidate-reason">{item.why_notable.slice(0, 3).join(" · ") || "저장 근거 확인"}</p>
                  <div className="watch-candidate-footer">
                    <p className="watch-candidate-news">뉴스: {newsLabel}{missing}</p>
                    <span className="watch-candidate-open">종목 상세 보기 <span aria-hidden="true">→</span></span>
                  </div>
                </a>
              );
            })}
          </div>
        )}
      </section>
      <SelectedStockPanel
        date={date}
        selectedStockCode={requestedStockCode}
        sectionId="watch-selected-stock"
        allowedStocks={payload.rows}
        candidate={selectedCandidate}
        detailSnapshot={workspace.selectedStockDetail}
      />
    </main>
  );
}
