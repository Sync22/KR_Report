"use client";

import { useRef, useState } from "react";
import { isRotationOverlaySnapshot, type RotationOverlaySnapshot } from "@/domain/category-rotation";
import { isEtfTrendSnapshot, type EtfTrendSnapshot } from "@/domain/market";

function amount(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? `${new Intl.NumberFormat("ko-KR").format(value)}원` : "자료 없음";
}

function percent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(2)}%` : "자료 없음";
}

function categoryHref(date: string, item: RotationOverlaySnapshot["highlights"][number]): string {
  const params = new URLSearchParams({ type: item.category_type, display_name: item.display_name, public_category_id: item.public_category_id });
  return `/daily/${date}/category?${params}`;
}

export default function MainRotationOverlay({ businessDate }: Readonly<{ businessDate: string }>) {
  const rotationLoaded = useRef(false);
  const etfLoaded = useRef(false);
  const [loading, setLoading] = useState(false);
  const [rotation, setRotation] = useState<RotationOverlaySnapshot | null>(null);
  const [etfs, setEtfs] = useState<EtfTrendSnapshot | null>(null);
  const [rotationError, setRotationError] = useState("");
  const [etfError, setEtfError] = useState("");

  async function load() {
    if ((rotationLoaded.current && etfLoaded.current) || loading) return;
    setLoading(true);
    const params = new URLSearchParams({ date: businessDate, limit: "5" });
    const requests: Promise<void>[] = [];
    if (!rotationLoaded.current) {
      setRotationError("");
      requests.push((async () => {
        try {
          const response = await fetch(`/api/rotation-overlay?${params}`, { cache: "no-store" });
          const body: unknown = await response.json().catch(() => null);
          if (!response.ok || !isRotationOverlaySnapshot(body, businessDate)) throw new Error();
          setRotation(body);
          rotationLoaded.current = true;
        } catch { setRotationError("업종·테마 저장 분류를 불러오지 못했습니다."); }
      })());
    }
    if (!etfLoaded.current) {
      setEtfError("");
      requests.push((async () => {
        try {
          const response = await fetch(`/api/etf-trend?${params}`, { cache: "no-store" });
          const body: unknown = await response.json().catch(() => null);
          if (!response.ok || !isEtfTrendSnapshot(body, businessDate)) throw new Error();
          setEtfs(body);
          etfLoaded.current = true;
        } catch { setEtfError("ETF 저장 흐름을 불러오지 못했습니다."); }
      })());
    }
    await Promise.all(requests);
    setLoading(false);
  }

  return (
    <details className="daily-briefing main-industry-etf-details" onToggle={(event) => { if (event.currentTarget.open) void load(); }}>
      <summary className="section-header disclosure-summary">
        <h2>업종 · ETF 참고 <span className="secondary">({businessDate})</span></h2>
      </summary>
      <p className="data-note">리포트 분류와 저장 ETF 값의 참고 화면입니다. 실제 자금 순환을 계산하지 않습니다.</p>
      <section aria-label="최근 저장 ETF 거래대금">
        <h3>거래대금 상위 ETF</h3>
        {loading && !etfs ? <p className="data-note">ETF 저장 흐름을 불러오는 중입니다.</p> : null}
        {etfError ? <p className="data-note">{etfError}</p> : null}
        {etfs?.available ? etfs.items.map((day) => (
          <div className="table-wrap" key={day.business_date}>
            <table>
              <caption className="eyebrow table-caption">Toss 저장 ETF · 기준일 {day.business_date}</caption>
              <thead><tr><th scope="col">ETF</th><th scope="col">종가</th><th scope="col">등락</th><th scope="col">거래대금</th></tr></thead>
              <tbody>{day.top_etfs_by_turnover.map((item) => (
                <tr key={`${day.business_date}-${String(item.etf_code)}`}>
                  <td>{String(item.etf_name)} ({String(item.etf_code)})</td>
                  <td>{amount(item.close_price)}</td>
                  <td>{percent(item.change_percent)}</td>
                  <td>{amount(item.turnover)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )) : etfs ? <p className="data-note">{etfs.notice} · 기준일 {etfs.reference_date ?? "자료 없음"}</p> : null}
      </section>
      <section aria-label="업종·테마 위치 참고">
        <h3>업종 · 테마 위치 참고</h3>
        {loading && !rotation ? <p className="data-note">저장 분류를 불러오는 중입니다.</p> : null}
        {rotationError ? <p className="data-note">{rotationError}</p> : null}
        {rotation?.highlights.length ? <>
          <figure className="rotation-map">
            <img src="/assets/cycle.jpg" alt="업종·테마 분류 참고 이미지" />
            <svg viewBox={`0 0 ${rotation.image.width} ${rotation.image.height}`} role="img" aria-label="저장 리포트 분류 위치 강조">
              {rotation.highlights.map((item, index) => <g key={`${item.category_type}-${item.display_name}-${index}`}>
                <circle cx={item.x} cy={item.y} r={item.radius} />
                <text x={item.x} y={item.y + item.radius + 34} textAnchor="middle">{item.label || item.display_name}</text>
              </g>)}
            </svg>
          </figure>
          <ul className="status-list main-rotation-evidence">
            {rotation.highlights.map((item) => <li key={`${item.category_type}-${item.display_name}`}>
              <strong><a href={categoryHref(businessDate, item)}>{item.category_label}: {item.display_name}</a></strong>
              <p>{item.rotation_label} · {item.evidence_label} · 저장 분류 참고</p>
              <p>{item.candidate_stocks.length ? `리포트 종목 참고 · ${item.candidate_stocks.map((stock) => `${stock.stock_name}${stock.stock_code ? ` (${stock.stock_code})` : ""}`).join(" / ")}` : "부족한 정보 · 해당 분류 후보 종목 근거 없음"}</p>
              <p>{item.candidate_etfs.length ? `ETF 참고 · ${item.candidate_etfs.map((etf) => `${etf.etf_name}${etf.etf_code ? ` (${etf.etf_code})` : ""} · 거래대금 ${amount(etf.turnover)}`).join(" / ")}` : "부족한 정보 · 저장 ETF 매핑 또는 기준일 스냅샷 없음"}</p>
            </li>)}
          </ul>
        </> : rotation ? <p className="data-note">{rotation.notice} · 수동 좌표가 있는 업종·테마 저장 분류가 없습니다.</p> : null}
      </section>
      <p className="footer-link"><a href={`/daily/${businessDate}/etf`}>ETF 저장 흐름 전체 보기</a> · <a href={`/daily/${businessDate}/rotation`}>업종·테마 전체 보기</a></p>
    </details>
  );
}
