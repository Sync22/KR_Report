import assert from "node:assert/strict";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, TossOpenApiClient } from "../src/server/toss-openapi.ts";

test("chart alert client requests one bounded Toss 1-minute candle page", async () => {
  const calls = [];
  const client = new TossOpenApiClient({
    clientId: "test-client", clientSecret: "test-secret", liveEnabled: true,
    baseUrl: TOSS_OPENAPI_BASE_URL, timeoutSeconds: 2, configured: true,
  }, async (input, init) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (url.pathname === "/oauth2/token") return Response.json({ access_token: "test-token", token_type: "Bearer", expires_in: 3600 });
    return Response.json({ result: { candles: [{
      timestamp: "2026-10-22T09:00:00+09:00", openPrice: 100, highPrice: 101, lowPrice: 99, closePrice: 100, volume: 10, currency: "KRW",
    }], nextBefore: null } });
  });
  const result = await client.getChartAlertMinuteCandles("005930", "2026-10-22T00:01:00.000Z");
  const candleCall = calls.find((call) => call.url.pathname === "/api/v1/candles");
  assert.equal(calls.length, 2);
  assert.equal(candleCall.url.origin, TOSS_OPENAPI_BASE_URL);
  assert.equal(candleCall.url.searchParams.get("symbol"), "005930");
  assert.equal(candleCall.url.searchParams.get("interval"), "1m");
  assert.equal(candleCall.url.searchParams.get("count"), "200");
  assert.equal(candleCall.url.searchParams.get("before"), "2026-10-22T00:01:00.000Z");
  assert.deepEqual(result.result.candles[0].openPrice, 100);
});

test("chart alert client rejects malformed symbols and cursors without network access", async () => {
  let calls = 0;
  const client = new TossOpenApiClient({
    clientId: "test-client", clientSecret: "test-secret", liveEnabled: true,
    baseUrl: TOSS_OPENAPI_BASE_URL, timeoutSeconds: 2, configured: true,
  }, async () => { calls += 1; return Response.json({}); });
  await assert.rejects(client.getChartAlertMinuteCandles("AAPL", "2026-10-22T00:00:00Z"), /fixed read-only profile/);
  await assert.rejects(client.getChartAlertMinuteCandles("005930", "not-a-date"), /fixed read-only profile/);
  assert.equal(calls, 0);
});
