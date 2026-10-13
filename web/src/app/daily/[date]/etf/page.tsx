import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isEtfTrendSnapshot } from "@/domain/market";
import { getEtfTrendSnapshot } from "@/server/etf-trend";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

function display(value: unknown, suffix = ""): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${new Intl.NumberFormat("ko-KR").format(value)}${suffix}`
    : "자료 없음";
}

function percent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(2)}%` : "자료 없음";
}

export default async function EtfTrendPage({ params }: Readonly<{ params: Promise<{ date: string }> }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  let payload: unknown;
  try { payload = getEtfTrendSnapshot(date, 5); } catch {
    return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>ETF 저장 흐름</h1><Message>ETF 저장 데이터를 불러오지 못했습니다.</Message></main>;
  }
  if (!isEtfTrendSnapshot(payload, date)) return <main><p className="eyebrow">Stock Monitor · 공개 web-view</p><h1>ETF 저장 흐름</h1><Message>ETF 응답 형식을 확인할 수 없습니다.</Message></main>;
  const updatedAt = new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: payload.timezone }).format(new Date(payload.now));
  const freshness = payload.reference_date === null ? "자료 없음" : payload.exact_date_available ? "선택일 저장값" : "이전 저장값";

  return (
    <main>
      <p className="eyebrow">Stock Monitor · 공개 web-view</p>
      <h1>ETF 저장 흐름</h1>
      <p className="updated">선택일 {payload.business_date} · ETF 기준일 {payload.reference_date ?? "자료 없음"} · {freshness}</p>
      <p className="data-note">{payload.notice} · {payload.composition_scope} · 실시간 호출 없음</p>
      <p className="data-note">집계 기준: {payload.basis}. 구성종목이나 매매 판단은 포함하지 않습니다.</p>
      {!payload.items.length ? <Message>{payload.notice}</Message> : payload.items.map((day) => (
        <section className="data-section" aria-label={`${day.business_date} ETF 저장값`} key={day.business_date}>
          <h2>{day.business_date} · 거래대금 상위 ETF</h2>
          {!day.top_etfs_by_turnover.length ? <Message>저장 ETF 값이 없습니다.</Message> : <div className="table-wrap"><table>
            <thead><tr><th scope="col">ETF</th><th scope="col">종가</th><th scope="col">등락률</th><th scope="col">거래대금</th><th scope="col">기초지수</th></tr></thead>
            <tbody>{day.top_etfs_by_turnover.map((item, index) => <tr key={`${String(item.etf_code)}-${index}`}>
              <td>{typeof item.etf_name === "string" ? item.etf_name : "자료 없음"} ({typeof item.etf_code === "string" ? item.etf_code : "자료 없음"})</td><td>{display(item.close_price, "원")}</td>
              <td>{percent(item.change_percent)}</td><td>{display(item.turnover, "원")}</td><td>{typeof item.underlying_index_name === "string" ? item.underlying_index_name : "자료 없음"}</td>
            </tr>)}</tbody>
          </table></div>}
        </section>
      ))}
      <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a> · <a href="/market">최근 저장 시장 참고</a></p>
    </main>
  );
}
