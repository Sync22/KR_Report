import { isArchiveSnapshot } from "@/domain/archive";
import { getArchiveSnapshot } from "@/server/archive";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function Message({ children }: Readonly<{ children: React.ReactNode }>) {
  return <p className="message">{children}</p>;
}

export default async function ArchivePage() {
  let payload: unknown;
  try {
    payload = getArchiveSnapshot(100);
  } catch {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>종목 리서치 아카이브</h1>
        <Message>저장된 데이터를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.</Message>
      </main>
    );
  }
  if (!isArchiveSnapshot(payload)) {
    return (
      <main>
        <p className="eyebrow">Stock Monitor · 공개 web-view</p>
        <h1>종목 리서치 아카이브</h1>
        <Message>아카이브 응답 형식을 확인할 수 없습니다.</Message>
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
      <h1>종목 리서치 아카이브</h1>
      <p className="updated">
        리포트 출처: Naver Research · 조회 시각: <time dateTime={payload.now}>{updatedAt} KST</time>
      </p>
      <p className="summary">
        저장일 {payload.date_count}일 · 최신 기준일 {payload.latest_business_date ?? "자료 없음"}
      </p>
      <p className="footer-link"><a href="/market">최근 저장 시장 참고</a></p>
      {payload.latest_business_date ? <p className="footer-link"><a href={`/daily/${payload.latest_business_date}/main`}>최신 기준일 Main Top2 보기</a></p> : null}
      {payload.dates.length === 0 ? (
        <Message>저장된 아카이브가 없습니다.</Message>
      ) : (
        <div className="table-wrap">
          <table>
            <caption className="eyebrow" style={{ padding: "12px 16px", textAlign: "left" }}>
              날짜별 저장 데이터
            </caption>
            <thead>
              <tr>
                <th scope="col">기준일</th>
                <th scope="col">보고서</th>
                <th scope="col">종목</th>
                <th scope="col">뉴스 관찰</th>
              </tr>
            </thead>
            <tbody>
              {payload.dates.map((row) => (
                <tr key={row.business_date}>
                  <td><a href={`/daily/${row.business_date}/main`}>{row.business_date}</a></td>
                  <td>{row.report_count}건</td>
                  <td>{row.summary_stock_count}종목</td>
                  <td>{row.news_observation_count}건</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
