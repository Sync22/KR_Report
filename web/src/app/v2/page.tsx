import "server-only";

import Link from "next/link";
import { isArchiveSnapshot } from "@/domain/archive";
import { isBusinessDate, isDailySnapshot, type DailySnapshot } from "@/domain/daily";
import { isCandidateEvidenceSnapshot, type CandidateEvidenceSnapshot } from "@/domain/candidate-evidence";
import { isEtfTrendSnapshot, type EtfTrendSnapshot } from "@/domain/market";
import { isStockDetailSnapshot, type StockDetailSnapshot } from "@/domain/stocks";
import { getArchiveSnapshot } from "@/server/archive";
import { getDailySnapshot } from "@/server/daily-snapshot";
import { getCandidateEvidenceSnapshot } from "@/server/candidate-evidence";
import { getEtfTrendSnapshot } from "@/server/etf-trend";
import { getStockDetailSnapshot } from "@/server/stock-detail";
import styles from "./v2-preview.module.css";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const metadata = { title: "KR-Stock Web View V2" };

type PageProps = Readonly<{
  searchParams: Promise<{ date?: string | string[]; stock?: string | string[] }>;
}>;

type NewsLineData = {
  available?: boolean;
  display_label?: string;
  reason?: string;
  connection_label?: string;
  connection_reason?: string;
  direct_count?: number | null;
  caution_count?: number | null;
  market_context_count?: number | null;
  krx_reference_status?: string;
  top_title?: string | null;
};

function singleValue(value: string | string[] | undefined): string | null {
  return typeof value === "string" ? value : null;
}

function formatCount(value: number | null | undefined): string {
  return new Intl.NumberFormat("ko-KR").format(value ?? 0);
}

function cautionCountText(direct: number | null | undefined, caution: number | null | undefined, label: string): string {
  const cautionLabel = (direct ?? 0) > 0 && !label.startsWith("주의") ? "보조 확인" : "주의";
  return `${cautionLabel} ${formatCount(caution)}`;
}

function newsKindLabel(badge: NewsLineData): string {
  if (badge.available !== true) return "뉴스 근거 수집 전";
  if ((badge.direct_count ?? 0) > 0) return "직접 뉴스";
  if ((badge.caution_count ?? 0) > 0) return "주의 뉴스";
  if ((badge.market_context_count ?? 0) > 0) return "시장맥락 위주";
  return badge.display_label || "뉴스 근거 있음";
}

function NewsLine({ badge, showTitle = true }: Readonly<{ badge: NewsLineData; showTitle?: boolean }>) {
  const label = badge.connection_label || newsKindLabel(badge);
  if (badge.available !== true) {
    return <><span className={`${styles.chip} ${styles.chipWarn}`}>{label}</span><span className={styles.newsLine}>{badge.reason || "저장 뉴스 근거를 아직 수집하지 않았습니다."}</span></>;
  }
  const krx = badge.krx_reference_status || "missing";
  return <>
    <span className={`${styles.chip} ${styles.chipStrong}`}>{label}</span>
    <span className={styles.chip}>직접 {formatCount(badge.direct_count)} · {cautionCountText(badge.direct_count, badge.caution_count, label)} · 시장맥락 {formatCount(badge.market_context_count)}</span>
    <span className={`${styles.chip} ${krx === "stale" ? styles.chipWarn : ""}`}>KRX {krx}</span>
    {badge.connection_reason ? <span className={styles.newsLine}>{badge.connection_reason}</span> : null}
    {showTitle && badge.top_title ? <span className={styles.newsLine}>{badge.top_title}</span> : null}
  </>;
}

function V2Card({ children, label }: Readonly<{ children: React.ReactNode; label: string }>) {
  return <section className={styles.card} aria-label={label}>{children}</section>;
}

export default async function PublicV2Page({ searchParams }: PageProps) {
  const query = await searchParams;
  let archive: ReturnType<typeof getArchiveSnapshot> | null = null;
  try {
    const payload: unknown = getArchiveSnapshot(80);
    if (isArchiveSnapshot(payload)) archive = payload;
  } catch { /* Keep the public preview usable when archive data is unavailable. */ }

  const requestedDate = singleValue(query.date);
  const selectedDate = isBusinessDate(requestedDate)
    ? requestedDate
    : archive?.dates[0]?.business_date ?? "";
  let dailyRaw: unknown = null;
  let evidenceRaw: unknown = null;
  let etfRaw: unknown = null;
  if (selectedDate) {
    [dailyRaw, evidenceRaw, etfRaw] = await Promise.all([
      Promise.resolve().then(() => getDailySnapshot(selectedDate)).catch(() => null),
      Promise.resolve().then(() => getCandidateEvidenceSnapshot(selectedDate, 8)).catch(() => null),
      Promise.resolve().then(() => getEtfTrendSnapshot(selectedDate, 4)).catch(() => null),
    ]);
  }
  const daily: DailySnapshot | null = selectedDate && isDailySnapshot(dailyRaw, selectedDate) ? dailyRaw : null;
  const candidates: CandidateEvidenceSnapshot | null = selectedDate && isCandidateEvidenceSnapshot(evidenceRaw, selectedDate)
    ? evidenceRaw
    : null;
  const etfTrend: EtfTrendSnapshot | null = selectedDate && isEtfTrendSnapshot(etfRaw, selectedDate) ? etfRaw : null;
  const requestedStock = singleValue(query.stock);
  const selectedCandidate = candidates?.rows.find((item) => item.stock_code === requestedStock) ?? null;
  let detailRaw: unknown = null;
  if (selectedDate && selectedCandidate) {
    detailRaw = await Promise.resolve()
      .then(() => getStockDetailSnapshot(selectedDate, selectedCandidate.stock_code))
      .catch(() => null);
  }
  const detail: StockDetailSnapshot | null = selectedDate && selectedCandidate &&
    isStockDetailSnapshot(detailRaw, selectedDate, selectedCandidate.stock_code)
    ? detailRaw
    : null;

  const briefing = daily?.market_briefing;
  const points = [...(briefing?.check_points ?? []), ...(briefing?.market_reference_lines ?? [])].slice(0, 5);
  const news = daily?.news_observation_summary;
  const firstEtf = etfTrend?.items.flatMap((item) => item.top_etfs_by_turnover)[0] ?? null;
  const firstEtfName = typeof firstEtf?.etf_name === "string" ? firstEtf.etf_name : firstEtf?.etf_code;
  const firstEtfEvidence = typeof firstEtf?.evidence_label === "string" ? firstEtf.evidence_label : "ETF 저장 참고";
  const etfLine = firstEtfName
    ? `${firstEtfName} · ${firstEtfEvidence}`
    : etfTrend
      ? `${etfTrend.display_label} · 기준 ${etfTrend.reference_date ?? "자료 없음"} · ${etfTrend.notice}`
      : "저장 ETF 흐름을 불러오지 못했습니다.";
  const allNewsTitles = detail ? [
    ...(detail.news_observation_detail.top_titles ?? []),
    detail.news_observation_detail.top_title ?? "",
  ] : [];
  const newsTitles = allNewsTitles.filter((title, index) => Boolean(title) && allNewsTitles.indexOf(title) === index).slice(0, 3);
  const detailReports = detail?.reports.slice(0, 3) ?? [];

  return (
    <div className={styles.page}>
      <main className={styles.main} id="surface-v2-app">
        <header className={styles.hero}>
          <div>
            <h1 className={styles.heroTitle}>KR-Stock V2 Preview</h1>
            <p className={styles.heroDescription}>저장 데이터 기준으로 흐름, 후보, 근거, 상세를 분리해서 보는 실험 화면입니다.</p>
          </div>
          <Link className={styles.link} href="/" prefetch={false}>기존 화면으로</Link>
        </header>

        <nav className={styles.dateRail} aria-label="날짜 선택">
          {archive?.dates.slice(0, 18).map((item) => (
            <Link
              className={`${styles.dateButton} ${item.business_date === selectedDate ? styles.active : ""}`}
              aria-current={item.business_date === selectedDate ? "date" : undefined}
              href={`/v2?date=${item.business_date}`}
              prefetch={false}
              scroll={false}
              replace
              key={item.business_date}
            >
              {item.business_date}{item.news_observation_count ? ` · 뉴스 ${formatCount(item.news_observation_count)}` : ""}
            </Link>
          ))}
          {!archive?.dates.length ? <span className={styles.muted}>저장된 날짜가 없습니다.</span> : null}
        </nav>

        <section className={styles.layout}>
          <div className={styles.column}>
            <V2Card label="오늘의 흐름">
              <h2>오늘의 흐름 <span className={styles.muted}>{selectedDate ? `(${selectedDate})` : ""}</span></h2>
              <p className={styles.reason}>{daily
                ? daily.report_count
                  ? `리포트 ${formatCount(daily.report_count)}건, ${formatCount(daily.summary_stock_count)}개 종목 기준으로 읽습니다.`
                  : "선택 날짜에 저장된 리포트 요약이 없습니다."
                : "선택 날짜의 저장 요약을 불러오지 못했습니다."}</p>
              <div className={styles.statusRow}>
                <span className={`${styles.chip} ${styles.chipStrong}`}>저장 데이터</span>
                <span className={styles.chip}>GET-only</span>
                {briefing?.source ? <span className={styles.chip}>{briefing.source}</span> : null}
              </div>
              <ul className={styles.list}>
                {points.length
                  ? points.map((point, index) => <li key={`${index}-${point}`}>{point}</li>)
                  : <li className={styles.muted}>저장된 확인 포인트가 없습니다.</li>}
              </ul>
            </V2Card>

            <V2Card label="볼 종목">
              <h2>볼 종목</h2>
              <p className={styles.reason}>후보 카드의 뉴스 줄은 저장된 observation만 사용합니다.</p>
              {candidates?.rows.length ? <div className={styles.candidateList}>
                {candidates.rows.slice(0, 8).map((item, index) => {
                  const badge = item.news_observation_badge;
                  const reason = item.why_notable.slice(0, 2).join(" · ") || "저장 리포트 기준 후보입니다.";
                  const href = `/v2?${new URLSearchParams({ date: selectedDate, stock: item.stock_code })}`;
                  return (
                    <Link
                      className={`${styles.candidateCard} ${selectedCandidate?.stock_code === item.stock_code ? styles.selected : ""}`}
                      href={href}
                      prefetch={false}
                      scroll={false}
                      replace
                      aria-current={selectedCandidate?.stock_code === item.stock_code ? "true" : undefined}
                      key={item.stock_code}
                    >
                      <span className={styles.candidateHead}>
                        <b>{formatCount(index + 1)}. {item.stock_name} <span className={styles.muted}>{item.stock_code}</span></b>
                        <span className={styles.chip}>{item.observation_priority}</span>
                      </span>
                      <span className={styles.statusRow}><NewsLine badge={badge} /></span>
                      <span className={styles.reason}>{reason}</span>
                    </Link>
                  );
                })}
              </div> : <p className={candidates ? styles.muted : styles.error}>
                {candidates ? "오늘의 관찰 후보가 없습니다." : "저장 후보를 불러오지 못했습니다."}
              </p>}
            </V2Card>
          </div>

          <div className={styles.column}>
            <V2Card label="근거 레이어">
              <h2>근거 레이어</h2>
              <div className={styles.evidenceGrid}>
                <div className={styles.evidenceRow}><b>리포트</b><span>{daily ? `${formatCount(daily.report_count)}건 · ${formatCount(daily.summary_stock_count)}종목` : "저장 리포트 자료를 확인할 수 없습니다."}</span></div>
                <div className={styles.evidenceRow}><b>뉴스</b><span>{news?.available
                  ? `${news.display_label} · 직접 ${formatCount(news.direct_count)} · ${cautionCountText(news.direct_count, news.caution_count, news.display_label)} · 시장맥락 ${formatCount(news.market_context_count)}`
                  : news?.reason || "뉴스 근거 수집 전"}</span></div>
                <div className={styles.evidenceRow}><b>Toss/수급</b><span>{briefing?.index_summary?.reference_date
                  ? `지수 기준 ${briefing.index_summary.reference_date}`
                  : daily?.toss_context.snapshot_date
                    ? `Toss 저장 기준 ${daily.toss_context.snapshot_date}`
                    : "저장 Toss 기준 확인 필요"}</span></div>
                <div className={styles.evidenceRow}><b>순환매/ETF</b><span>{etfLine}</span></div>
              </div>
            </V2Card>

            <V2Card label="종목 상세">
              <h2 id="stock-detail">종목 상세</h2>
              {detail && selectedCandidate ? <div className={styles.detail}>
                <p className={styles.detailTitle}>{detail.stock_name || selectedCandidate.stock_name} <span className={styles.muted}>{detail.stock_code}</span></p>
                <div className={styles.statusRow}><NewsLine badge={detail.news_observation_detail} showTitle={false} /></div>
                <ul className={styles.list}>
                  {newsTitles.length ? newsTitles.map((title, index) => <li key={`news-${index}-${title}`}>{title}</li>)
                    : <li className={styles.muted}>저장 뉴스 관찰 상세가 없습니다.</li>}
                  {detailReports.map((report) => <li key={`${report.stock_code}-${report.title}`}>{report.title || report.report_title || "리포트 제목 없음"}</li>)}
                </ul>
              </div> : selectedCandidate
                ? <p className={styles.error}>선택한 종목의 저장 상세를 불러오지 못했습니다.</p>
                : <p className={styles.muted}>볼 종목 카드를 누르면 리포트와 뉴스 관찰 상세를 불러옵니다.</p>}
            </V2Card>
          </div>
        </section>
      </main>
    </div>
  );
}
