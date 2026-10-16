import assert from "node:assert/strict";
import test from "node:test";

import { isChartLabLocalRequest } from "../src/server/chart-lab-local.ts";

test("Chart Lab accepts loopback requests on the fixed preview origin", () => {
  const request = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", { headers: { host: "127.0.0.1:3010" } });
  assert.equal(isChartLabLocalRequest(request), true);
});

test("Chart Lab accepts the loopback URL when the framework omits the Host header", () => {
  const request = new Request("http://127.0.0.1:3010/api/chart-lab/monitor");
  assert.equal(request.headers.get("host"), null);
  assert.equal(isChartLabLocalRequest(request), true);
});

test("Chart Lab normalizes loopback Host headers that omit the explicit preview port", () => {
  const request = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", { headers: { host: "127.0.0.1" } });
  assert.equal(isChartLabLocalRequest(request), true);
});

test("Chart Lab rejects non-loopback hosts even when forwarded headers claim localhost", () => {
  const request = new Request("http://example.com/api/chart-lab/monitor", {
    headers: { host: "example.com", "x-forwarded-host": "127.0.0.1:3010" },
  });
  assert.equal(isChartLabLocalRequest(request), false);
});

test("Chart Lab mutations require an exact same-origin request", () => {
  const sameOrigin = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST",
    headers: { host: "127.0.0.1:3010", origin: "http://127.0.0.1:3010" },
  });
  const crossOrigin = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST",
    headers: { host: "127.0.0.1:3010", origin: "http://attacker.example" },
  });
  const missingOrigin = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", {
    method: "POST",
    headers: { host: "127.0.0.1:3010" },
  });
  assert.equal(isChartLabLocalRequest(sameOrigin, true), true);
  assert.equal(isChartLabLocalRequest(crossOrigin, true), false);
  assert.equal(isChartLabLocalRequest(missingOrigin, true), false);
});
