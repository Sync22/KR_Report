import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isCategoryDetailSnapshot, isCategoryTrendSnapshot } from "@/domain/category-rotation";
import { getCategoryDetailSnapshot } from "@/server/category-detail";
import { getCategoryTrendSnapshot } from "@/server/category-trend";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function display(value: unknown, suffix = ""): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${new Intl.NumberFormat("ko-KR").format(value)}${suffix}`
    : "자료 없음";
}

function marketReference(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "선택일 Toss 저장값 없음";
  const reference = value as Record<string, unknown>;
  return `${String(reference.business_date ?? "자료 없음")} · ${String(reference.market ?? "시장 미확인")} · 종가 ${display(reference.close_price, "원")} · 등락 ${typeof reference.change_percent === "number" ? `${reference.change_percent.toFixed(2)}%` : "자료 없음"}`;
}

export default async function CategoryPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ date: string }>;
  searchParams: Promise<{ type?: string | string[]; display_name?: string | string[]; public_category_id?: string | string[] }>;
}>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  const query = await searchParams;
  const first = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;
  const requestedType = (first(query.type) ?? "").trim();
  const requestedName = (first(query.display_name) ?? "").trim();
  const categoryParts = (first(query.public_category_id) ?? "").trim().split("|", 3);
  const publicCategoryType = categoryParts[0]?.trim();
  const publicCategoryName = categoryParts[1]?.trim();
  const publicCategory = categoryParts.length === 3 &&
    (publicCategoryType === "sector" || publicCategoryType === "theme") && publicCategoryName
    ? { type: publicCategoryType, name: publicCategoryName }
    : undefined;
  if (publicCategory && requestedType && requestedType !== publicCategory.type) notFound();
  const type = publicCategory?.type ?? requestedType;
  const name = publicCategory?.name ?? requestedName;
  if (!(type === "sector" || type === "theme") || !name || name.length > 120) notFound();

  const [detailSnapshot, trend] = await Promise.all([
    Promise.resolve().then(() => getCategoryDetailSnapshot(date, type, "", name)).catch(() => null),
    Promise.resolve().then(() => getCategoryTrendSnapshot(type, name, 20)).catch(() => null),
  ]);
  if (!isCategoryDetailSnapshot(detailSnapshot, date, type, name)) {
    return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>{name}</h1><Message>선택한 업종/테마 저장 데이터를 확인할 수 없습니다.</Message></main>;
  }
  const detail = detailSnapshot;
  const validTrend = isCategoryTrendSnapshot(trend, type, name) ? trend : null;
  const updatedAt = new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: detail.timezone }).format(new Date(detail.now));
  const marketSourceDate = detail.snapshot_date ?? "자료 없음";

  return (
    <main>
      <p className="eyebrow">Stock Monitor · 공개 web-view</p>
      <h1>{detail.category_label}: {detail.category_display_name}</h1>
      <p className="updated">선택일 {detail.business_date} · 분류 기준일 {marketSourceDate} · 조회 시각: <time dateTime={detail.now}>{updatedAt} KST</time></p>
      <p className="data-note">{detail.mapping_notice} · 종목 {detail.stock_count}개 · 리포트 {detail.report_count}건</p>
      {detail.stocks.length ? <div className="table-wrap"><table>
        <caption className="eyebrow table-caption">선택일 리포트와 날짜가 표시된 Toss 저장 시장 참고</caption>
        <thead><tr><th scope="col">종목</th><th scope="col">리포트</th><th scope="col">증권사</th><th scope="col">리포트 목표가 참고</th><th scope="col">리포트 의견 표기</th><th scope="col">시장 참고</th></tr></thead>
        <tbody>{detail.stocks.map((item, index) => {
          const stockLink = typeof item.stock_code === "string" && /^\d{6}$/.test(item.stock_code);
          const nameCell = `${String(item.stock_name)}${stockLink ? ` (${item.stock_code})` : ""}`;
          const target = item.target_price_min === null && item.target_price_max === null
            ? "자료 없음"
            : `${display(item.target_price_min, "원")} – ${display(item.target_price_max, "원")}`;
          return <tr key={`${String(item.stock_code ?? item.stock_name)}-${index}`}>
            <td>{stockLink ? <a href={`/daily/${date}/stocks/${item.stock_code}`}>{nameCell}</a> : nameCell}</td>
            <td>{display(item.mention_count, "건")}</td><td>{typeof item.broker_display === "string" ? item.broker_display : "자료 없음"}</td>
            <td>{target}</td><td>{item.dominant_opinion ? `리포트 표기: ${String(item.dominant_opinion)}` : "자료 없음"}</td><td>{marketReference(item.market_reference)}</td>
          </tr>;
        })}</tbody>
      </table></div> : <Message>선택일에 이 분류로 저장된 종목이 없습니다.</Message>}

      <section className="data-section" aria-labelledby="trend-heading">
        <h2 id="trend-heading">저장 분류 흐름</h2>
        {validTrend ? validTrend.trend.length ? <div className="table-wrap"><table>
          <thead><tr><th scope="col">분류 기준일</th><th scope="col">리포트</th><th scope="col">종목</th></tr></thead>
          <tbody>{validTrend.trend.map((item, index) => <tr key={`${item.business_date}-${index}`}><td>{String(item.business_date)}</td><td>{display(item.report_count, "건")}</td><td>{display(item.stock_count, "종목")}</td></tr>)}</tbody>
        </table></div> : <Message>저장된 분류 흐름이 없습니다.</Message> : <Message>분류 흐름을 불러오지 못했습니다.</Message>}
        {validTrend ? <p className="data-note">{validTrend.mapping_policy}</p> : null}
      </section>
      <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a> · <a href={`/daily/${date}/rotation`}>업종·테마 위치 참고</a></p>
    </main>
  );
}
