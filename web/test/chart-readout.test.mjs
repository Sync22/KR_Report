import assert from "node:assert/strict";
import test from "node:test";

import { buildChartReadout } from "../src/domain/chart-readout.ts";

test("chart readout uses descriptive average and volume comparisons with a next check", () => {
  assert.deepEqual(buildChartReadout(110, 105, 100, 0.8), {
    headline: "상승 흐름",
    summary: "종가가 60일 평균 위에 있고, 20일 평균은 60일 평균 위에 있습니다. 거래량은 20봉 평균보다 적습니다.",
    nextCheck: "다음 확정 봉에서 종가가 20일 평균 위를 유지하는지 확인합니다.",
  });
  assert.equal(buildChartReadout(80, 90, 100, 1.2).headline, "하락 흐름");
  assert.equal(buildChartReadout(100, 102, 100, 1).headline, "평균선 혼합 구간");
  assert.equal(buildChartReadout(null, 102, 100, null).headline, "평균선 자료 부족");
  assert.match(buildChartReadout(null, 102, 100, null).summary, /거래량 평균 비교 자료가 없습니다/);
});
