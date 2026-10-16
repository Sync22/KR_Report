import assert from "node:assert/strict";
import test from "node:test";

import { GET, POST } from "../src/app/api/chart-lab/analysis/route.ts";

test("Chart Lab analysis API is local-only and rejects malformed or repeated parameters", async () => {
  const remote = await GET(new Request("http://example.com/api/chart-lab/analysis?date=2026-10-08&symbol=005930&timeframe=1d", { headers: { host: "example.com" } }));
  const base = { host: "127.0.0.1:3010" };
  const invalid = await GET(new Request("http://127.0.0.1:3010/api/chart-lab/analysis?date=2026-10-08&symbol=005930&timeframe=1d&selected=A,Z", { headers: base }));
  const repeated = await GET(new Request("http://127.0.0.1:3010/api/chart-lab/analysis?date=2026-10-08&date=2026-10-09&symbol=005930&timeframe=1d", { headers: base }));
  assert.equal(remote.status, 403);
  assert.equal(invalid.status, 400);
  assert.equal(repeated.status, 400);
  assert.equal(POST().status, 405);
});
