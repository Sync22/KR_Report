export type ChartReadout = Readonly<{
  headline: string;
  summary: string;
  nextCheck: string;
}>;

export function buildChartReadout(close: number | null, sma20: number | null, sma60: number | null, volumeRatio20: number | null): ChartReadout {
  const hasAverages = close !== null && sma20 !== null && sma60 !== null;
  const headline = !hasAverages
    ? "평균선 자료 부족"
    : close > sma60 && sma20 > sma60
      ? "상승 흐름"
      : close < sma60 && sma20 < sma60
        ? "하락 흐름"
        : "평균선 혼합 구간";
  const volume = volumeRatio20 === null
    ? "거래량 평균 비교 자료가 없습니다."
    : volumeRatio20 < 1
      ? "거래량은 20봉 평균보다 적습니다."
      : volumeRatio20 > 1
        ? "거래량은 20봉 평균보다 많습니다."
        : "거래량은 20봉 평균과 같습니다.";
  const relation = hasAverages
    ? `종가가 60일 평균 ${close > sma60 ? "위" : close < sma60 ? "아래" : "부근"}에 있고, 20일 평균은 60일 평균 ${sma20 > sma60 ? "위" : sma20 < sma60 ? "아래" : "부근"}에 있습니다.`
    : "종가와 20·60일 평균의 관계를 비교할 자료가 부족합니다.";
  const nextCheck = headline === "상승 흐름"
    ? "다음 확정 봉에서 종가가 20일 평균 위를 유지하는지 확인합니다."
    : headline === "하락 흐름"
      ? "다음 확정 봉에서 종가가 20일 평균을 회복하는지 확인합니다."
      : headline === "평균선 혼합 구간"
        ? "다음 확정 봉에서 종가와 20·60일 평균의 위치 관계를 다시 비교합니다."
        : "20·60일 평균 자료가 충분해진 뒤 관계를 비교합니다.";
  return { headline, summary: `${relation} ${volume}`, nextCheck };
}
