import assert from "node:assert/strict";
import test from "node:test";

import { TOSS_OPENAPI_BASE_URL, TossOpenApiClient } from "../src/server/toss-openapi.ts";

function makeClient(calendar) {
  const requests = [];
  const client = new TossOpenApiClient({
    clientId: "test-client", clientSecret: "test-secret", liveEnabled: true,
    baseUrl: TOSS_OPENAPI_BASE_URL, timeoutSeconds: 5, configured: true,
  }, async (input, init) => {
    const url = new URL(input);
    requests.push({ url, init });
    if (url.pathname === "/oauth2/token") {
      return Response.json({ access_token: "test-access", token_type: "Bearer", expires_in: 3600 });
    }
    return Response.json({ result: calendar });
  });
  return { client, requests };
}

test("KRX calendar reads only the selected date's regular session", async () => {
  const date = "2026-10-16";
  const { client, requests } = makeClient({
    today: { date, integrated: { preMarket: null, regularMarket: { startTime: "2026-10-16T00:00:00.000Z", singlePriceAuctionStartTime: "2026-10-16T06:20:00.000Z", endTime: "2026-10-16T06:30:00.000Z" }, afterMarket: null } },
    previousBusinessDay: { date: "2026-10-15", integrated: { preMarket: null, regularMarket: { startTime: "2026-10-15T00:00:00.000Z", singlePriceAuctionStartTime: "2026-10-15T06:20:00.000Z", endTime: "2026-10-15T06:30:00.000Z" }, afterMarket: null } },
    nextBusinessDay: { date: "2026-10-19", integrated: { preMarket: null, regularMarket: { startTime: "2026-10-19T00:00:00.000Z", singlePriceAuctionStartTime: "2026-10-19T06:20:00.000Z", endTime: "2026-10-19T06:30:00.000Z" }, afterMarket: null } },
  });

  const result = await client.getKrxMarketCalendar(date);

  assert.deepEqual(result.result.map(({ date: itemDate, regularMarket }) => [itemDate, regularMarket?.startTime ?? null]), [
    ["2026-10-15", "2026-10-15T00:00:00.000Z"],
    [date, "2026-10-16T00:00:00.000Z"],
    ["2026-10-19", "2026-10-19T00:00:00.000Z"],
  ]);
  assert.equal(requests[1].init.method, "GET");
  assert.equal(requests[1].url.pathname, "/api/v1/market-calendar/KR");
  assert.equal(requests[1].url.searchParams.get("date"), date);
});

test("KRX calendar preserves a confirmed closed weekday without inventing a session", async () => {
  const { client } = makeClient({
    today: { date: "2026-10-09", integrated: null },
    previousBusinessDay: { date: "2026-10-08", integrated: { preMarket: null, regularMarket: { startTime: "2026-10-08T00:00:00.000Z", endTime: "2026-10-08T06:30:00.000Z" }, afterMarket: null } },
    nextBusinessDay: { date: "2026-10-12", integrated: { preMarket: null, regularMarket: { startTime: "2026-10-12T00:00:00.000Z", endTime: "2026-10-12T06:30:00.000Z" }, afterMarket: null } },
  });
  const result = await client.getKrxMarketCalendar("2026-10-09");
  assert.equal(result.result.find((day) => day.date === "2026-10-09").regularMarket, null);
});

test("KRX calendar rejects malformed regular session intervals", async () => {
  const { client } = makeClient({
    today: { date: "2026-10-16", integrated: { preMarket: null, regularMarket: { startTime: "bad", endTime: "bad" }, afterMarket: null } },
    previousBusinessDay: { date: "2026-10-15", integrated: null },
    nextBusinessDay: { date: "2026-10-19", integrated: null },
  });
  await assert.rejects(client.getKrxMarketCalendar("2026-10-16"), { providerReason: "invalid_provider_response" });
});
