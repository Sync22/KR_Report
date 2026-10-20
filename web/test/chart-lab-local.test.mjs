import assert from "node:assert/strict";
import test from "node:test";

import { isChartLabLocalHost, isChartLabLocalRequest } from "../src/server/chart-lab-local.ts";

test("Chart Lab accepts loopback requests on the fixed preview origin", () => {
  const request = new Request("http://127.0.0.1:3010/api/chart-lab/monitor", { headers: { host: "127.0.0.1:3010" } });
  assert.equal(isChartLabLocalRequest(request), true);
});

test("Chart Lab accepts loopback requests on the replacement web-view port", () => {
  const request = new Request("http://127.0.0.1:8780/api/chart-lab/monitor", { headers: { host: "127.0.0.1:8780" } });
  assert.equal(isChartLabLocalHost("127.0.0.1:8780"), true);
  assert.equal(isChartLabLocalRequest(request), true);
});

test("Chart Lab page host check rejects non-loopback hosts", () => {
  assert.equal(isChartLabLocalHost("web-view.example.com"), false);
  assert.equal(isChartLabLocalHost("127.0.0.1:8780"), true);
  assert.equal(isChartLabLocalHost("127.0.0.1:8780", "web-view.example.com"), false);
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

test("Chart Lab rejects a forwarded public host even if the origin host is loopback", () => {
  const request = new Request("http://127.0.0.1:8780/api/chart-lab/monitor", {
    headers: { host: "127.0.0.1:8780", "x-forwarded-host": "web-view.example.com" },
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
