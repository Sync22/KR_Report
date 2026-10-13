import { notFound } from "next/navigation";

import { isBusinessDate } from "@/domain/daily";
import { isIntradaySnapshot } from "@/domain/intraday";
import { getIntradaySnapshot } from "@/server/intraday";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

export default async function IntradayPage({ params }: Readonly<{ params: Promise<{ date: string }> }>) {
  const { date } = await params;
  if (!isBusinessDate(date)) notFound();
  let payload: unknown;
  try { payload = getIntradaySnapshot(date); } catch {
    return <main><section className="daily-briefing intraday-summary"><div className="section-header"><h1 id="intraday-heading">장중 리포트 기록</h1></div><Message>선택일의 장중 기록을 불러오지 못했습니다.</Message></section></main>;
  }
  if (!isIntradaySnapshot(payload, date)) return <main><section className="daily-briefing intraday-summary"><div className="section-header"><h1 id="intraday-heading">장중 리포트 기록</h1></div><Message>장중 응답 형식을 확인할 수 없습니다.</Message></section></main>;
  const updatedAt = new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short", timeZone: payload.timezone }).format(new Date(payload.now));
  return (
    <main>
      <section className="daily-briefing intraday-summary">
        <div className="section-header"><h1 id="intraday-heading">장중 리포트 기록</h1></div>
        <p className="updated">기준일 {payload.business_date} · 조회 시각 {updatedAt} KST</p>
        <p className="data-note">저장된 새 리포트 요약 기록입니다. 운영 설정이나 스케줄러 상태는 표시하지 않습니다.</p>
        {!payload.batches.length ? <Message>선택일 장중 리포트 기록이 없습니다.</Message> : <div className="table-wrap"><table>
          <thead><tr><th scope="col">기록 시각</th><th scope="col">상태</th><th scope="col">새 리포트</th><th scope="col">종목</th></tr></thead>
          <tbody>{payload.batches.map((item) => <tr key={item.created_at}>
            <td><time dateTime={item.created_at}>{new Intl.DateTimeFormat("ko-KR", { timeStyle: "short", timeZone: payload.timezone }).format(new Date(item.created_at))} KST</time></td>
            <td>{item.status_label}</td><td>{item.report_count}건</td><td>{item.stock_count}종목</td>
          </tr>)}
          </tbody>
        </table></div>}
        <p className="footer-link"><a href={`/daily/${date}`}>일일 화면으로 돌아가기</a></p>
      </section>
    </main>
  );
}
