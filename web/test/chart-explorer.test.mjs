import assert from "node:assert/strict";
import test from "node:test";

import {
  aggregateDailyBars,
  aggregateHourlyBarsToFourHours,
  isChartExplorerSymbol,
  isChartExplorerTimeframe,
} from "../src/domain/chart-explorer.ts";
import { GET, POST } from "../src/app/api/chart-explorer/route.ts";
import { ChartExplorerService } from "../src/server/chart-explorer.ts";

function bar(time, index) {
  return { time, open: 10 + index, high: 12 + index, low: 9 + index, close: 11 + index, volume: 100 + index };
}

test("Chart Explorer accepts bounded equity symbol and timeframe shapes", () => {
  assert.equal(isChartExplorerSymbol("005930"), true);
  assert.equal(isChartExplorerSymbol("SATL"), true);
  assert.equal(isChartExplorerSymbol("RAIN"), true);
  assert.equal(isChartExplorerSymbol("A/B"), false);
  assert.equal(isChartExplorerSymbol("https://example.com"), false);
  assert.equal(isChartExplorerSymbol("a symbol"), false);
  assert.equal(isChartExplorerTimeframe("1d"), true);
  assert.equal(isChartExplorerTimeframe("4h"), true);
  assert.equal(isChartExplorerTimeframe("1y"), false);
});

test("Chart Explorer API rejects extra query fields and non-GET methods", async () => {
  const response = await GET(new Request("http://localhost/api/chart-explorer?date=2026-10-08&symbol=005930&timeframe=1d&limit=9000"));
  assert.equal(response.status, 400);
  assert.equal((await response.json()).reason, "invalid_query");
  assert.equal(POST().status, 405);
});

test("Chart Explorer bounds cache-miss provider queries per process", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(null, { status: 503 });
  try {
    const service = new ChartExplorerService();
    for (let index = 0; index < 12; index += 1) {
      const result = await service.getChart("2026-10-08", `TEST${index}`, "1d");
      assert.equal(result.status, 200);
      assert.equal(result.payload.reason, "provider_http_error");
    }
    const limited = await service.getChart("2026-10-08", "TEST12", "1d");
    assert.equal(limited.status, 429);
    assert.equal(limited.payload.reason, "rate_limited");
  } finally { globalThis.fetch = originalFetch; }
});

test("daily history aggregates weekly and monthly OHLCV without changing source order", () => {
  const source = [
    bar("2026-10-05", 0), bar("2026-10-06", 1), bar("2026-10-07", 2),
    bar("2026-10-12", 3),
  ];
  assert.deepEqual(aggregateDailyBars(source, "1w"), [
    { time: "2026-10-05", open: 10, high: 14, low: 9, close: 13, volume: 303 },
    { time: "2026-10-12", open: 13, high: 15, low: 12, close: 14, volume: 103 },
  ]);
  assert.deepEqual(aggregateDailyBars(source, "1mo"), [
    { time: "2026-10-01", open: 10, high: 15, low: 9, close: 14, volume: 406 },
  ]);
});

test("hourly history groups four-hour bars by provider-local session date", () => {
  const source = Array.from({ length: 7 }, (_, index) => bar(`2026-10-15T${String(index).padStart(2, "0")}:00:00.000Z`, index));
  const grouped = aggregateHourlyBarsToFourHours(source, "Asia/Seoul");
  assert.equal(grouped.length, 2);
  assert.deepEqual(grouped[0], {
    time: source[0].time, open: 10, high: 15, low: 9, close: 14, volume: 406,
  });
  assert.deepEqual(grouped[1], {
    time: source[4].time, open: 14, high: 18, low: 13, close: 17, volume: 315,
  });
});

test("session-aware 4h aggregation preserves holes instead of shifting later bars", () => {
  const at = (date, hour) => new Date(`${date}T${String(hour).padStart(2, "0")}:00:00+09:00`).toISOString();
  const session = (date) => ({ date, open: at(date, 9), close: `${date}T15:30:00+09:00` });
  const source = [9, 10, 12, 13, 14, ...[9, 10, 11, 12, 13, 14]].map((hour, index) => {
    const date = index < 5 ? "2026-10-15" : "2026-10-16";
    const time = at(date, hour);
    return { ...bar(time, index), time };
  });

  const grouped = aggregateHourlyBarsToFourHours(source, "Asia/Seoul", [session("2026-10-15"), session("2026-10-16")]);

  assert.deepEqual(grouped.map(({ time, missingBarsBefore }) => [time, missingBarsBefore]), [
    [at("2026-10-15", 13), 1],
    [at("2026-10-16", 9), 0],
    [at("2026-10-16", 13), 0],
  ]);
});

test("session-aware 4h aggregation counts only sessions confirmed by the calendar", () => {
  const at = (date, hour) => new Date(`${date}T${String(hour).padStart(2, "0")}:00:00+09:00`).toISOString();
  const session = (date) => ({ date, open: at(date, 9), close: `${date}T15:30:00+09:00` });
  const source = ["2026-10-15", "2026-10-17"].flatMap((date, dayIndex) => Array.from({ length: 6 }, (_, index) => {
    const time = at(date, 9 + index);
    return { ...bar(time, dayIndex * 10 + index), time };
  }));

  const withMissingSession = aggregateHourlyBarsToFourHours(source, "Asia/Seoul", [
    session("2026-10-15"), session("2026-10-16"), session("2026-10-17"),
  ]);
  const withHoliday = aggregateHourlyBarsToFourHours(source, "Asia/Seoul", [
    session("2026-10-15"), session("2026-10-17"),
  ]);

  assert.equal(withMissingSession.find((item) => item.time === at("2026-10-17", 9)).missingBarsBefore, 2);
  assert.equal(withHoliday.find((item) => item.time === at("2026-10-17", 9)).missingBarsBefore, 0);
});
