import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isRotationOverlaySnapshot } from "@/domain/category-rotation";
import { getRotationOverlaySnapshot } from "@/server/rotation-overlay";

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

function categoryHref(date: string, item: Record<string, unknown>): string {
  const params = new URLSearchParams({
    type: String(item.category_type),
    display_name: String(item.display_name),
    public_category_id: String(item.public_category_id),
  });
  return `/daily/${date}/category?${params}`;
}

export default async function RotationPage({ params }: Readonly<{ params: Promise<{ date: string }> }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  let payload: unknown;
  try { payload = getRotationOverlaySnapshot(date, 5); } catch { return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>업종·테마 위치 참고</h1><Message>저장 분류 자료를 불러오지 못했습니다.</Message></main>; }
  if (!isRotationOverlaySnapshot(payload, date)) return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>업종·테마 위치 참고</h1><Message>분류 참고 응답 형식을 확인할 수 없습니다.</Message></main>;

  return (
    <main>
      <p className="eyebrow">Stock Monitor · 공개 web-view</p>
      <h1>업종·테마 위치 참고</h1>
      <p className="updated">기준일 {payload.business_date} · 저장 리포트 분류 기반</p>
      <p className="data-note">{payload.notice}</p>
      {payload.highlights.length ? <>
        <figure className="rotation-map">
          <img src="/assets/cycle.jpg" alt="업종·테마 분류 참고 이미지" />
          <svg viewBox={`0 0 ${payload.image.width} ${payload.image.height}`} role="img" aria-label="저장 리포트 분류 위치 강조">
            {payload.highlights.map((item, index) => <g key={`${item.category_type}-${item.display_name}-${index}`}>
              <circle cx={Number(item.x)} cy={Number(item.y)} r={Number(item.radius)} />
              <text x={Number(item.x)} y={Number(item.y) + Number(item.radius) + 34} textAnchor="middle">{String(item.rotation_label || item.display_name)}</text>
            </g>)}
          </svg>
        </figure>
        {payload.highlights.map((item, index) => (
          <section className="data-section" aria-label={`${String(item.category_label)} ${String(item.display_name)}`} key={`${item.category_type}-${item.display_name}-${index}`}>
            <h2><a href={categoryHref(date, item)}>{String(item.category_label)}: {String(item.display_name)}</a></h2>
            <p className="data-note">{String(item.rotation_label)} · {String(item.evidence_label)} · 저장 분류 참고</p>
            {item.candidate_stocks.length ? <p className="data-note"><strong>리포트 종목 참고:</strong> {item.candidate_stocks.map((stock, stockIndex) => {
              const label = `${String(stock.stock_name)} (${String(stock.stock_code ?? "자료 없음")}) · 리포트 ${display(stock.mention_count, "건")}${stock.market ? ` · ${String(stock.market)}` : ""}${stock.turnover === null ? "" : ` · 거래대금 ${display(stock.turnover, "원")}`}`;
              return <span key={`${String(stock.stock_code)}-${stockIndex}`}>{label}{stockIndex < item.candidate_stocks.length - 1 ? " / " : ""}</span>;
            })}</p> : <p className="data-note">부족한 정보: 해당 분류 후보 종목 근거 없음</p>}
            {item.candidate_etfs.length ? <p className="data-note"><strong>ETF 참고:</strong> {item.candidate_etfs.map((etf, etfIndex) => <span key={`${String(etf.etf_code)}-${etfIndex}`}>
              {String(etf.etf_name)} ({String(etf.etf_code)}) · {display(etf.turnover, "원")}{etf.underlying_index_name ? ` · ${String(etf.underlying_index_name)}` : ""}{etfIndex < item.candidate_etfs.length - 1 ? " / " : ""}
            </span>)}</p> : <p className="data-note">부족한 정보: 저장 ETF 매핑 또는 기준일 스냅샷 없음</p>}
          </section>
        ))}
      </> : <Message>수동 좌표가 있는 업종/테마 저장 분류가 없습니다.</Message>}
      <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a> · <a href="/market">최근 저장 시장 참고</a></p>
    </main>
  );
}
