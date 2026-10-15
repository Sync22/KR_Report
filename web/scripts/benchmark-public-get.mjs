import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WARMUPS = 5;
const SAMPLES = 30;

function query(values) {
  return new URLSearchParams(values).toString();
}

export function buildBenchmarkCases(date, stockCode) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date) {
    throw new TypeError("STOCK_MONITOR_BENCH_DATE must be a real YYYY-MM-DD date.");
  }
  if (!/^\d{6}$/.test(stockCode)) throw new TypeError("STOCK_MONITOR_BENCH_STOCK_CODE must be a six-digit code.");

  const dated = (values) => query({ date, ...values });
  return [
    ["archive", "/api/archive?limit=20"],
    ["daily", `/api/daily/${date}`],
    ["stock-detail", `/api/daily/${date}/stocks/${stockCode}`],
    ["stock-search", `/api/stocks/search?${dated({ q: "삼성", limit: "8" })}`],
    ["candidate-evidence", `/api/candidate-evidence?${dated({ limit: "8" })}`],
    ["observation-summary", `/api/observation-summary?${dated({})}`],
    ["observation-backtest", `/api/observation/backtest?${dated({ limit: "20", mention_threshold: "2" })}`],
    ["market", "/api/market"],
    ["intraday", `/api/intraday?${dated({})}`],
    ["flow-trend", `/api/flow-trend?${dated({ limit: "5" })}`],
    ["etf-trend", `/api/etf-trend?${dated({ limit: "5" })}`],
    ["rotation-overlay", `/api/rotation-overlay?${dated({ limit: "5", symbols: stockCode })}`],
    ["category", `/api/category?${dated({ type: "sector", display_name: "반도체", public_category_id: "sector|반도체|fallback" })}`],
    ["category-trend", `/api/category-trend?${query({ type: "sector", display_name: "__e2e_category_trend__", limit: "999" })}`],
  ].map(([name, path]) => ({ name, path, kind: "stored" }));
}

export function nearestRank(values, quantile) {
  if (values.length === 0 || quantile <= 0 || quantile > 1) throw new RangeError("A percentile needs samples and a quantile in (0, 1].");
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.ceil(quantile * sorted.length) - 1];
}

export function countCacheStates(states) {
  return states.reduce((counts, state) => {
    if (state === "hit") counts.hit += 1;
    else if (state === "miss") counts.miss += 1;
    else counts.unreported += 1;
    return counts;
  }, { hit: 0, miss: 0, unreported: 0 });
}

export function loopbackOrigin(rawValue, label) {
  const url = new URL(rawValue);
  if (!new Set(["localhost", "127.0.0.1", "[::1]"]).has(url.hostname)) {
    throw new Error(`${label} must use a loopback host; this benchmark is local-only.`);
  }
  return url.origin;
}

async function request(origin, path, pythonCookie, service) {
  const headers = { "accept-encoding": "identity", "x-stock-monitor-benchmark": "1" };
  if (service === "Python" && pythonCookie) headers.cookie = pythonCookie;
  const started = performance.now();
  const response = await fetch(new URL(path, origin), {
    cache: "no-store",
    headers,
    redirect: "manual",
    signal: AbortSignal.timeout(15_000),
  });
  const body = await response.arrayBuffer();
  const elapsedMs = performance.now() - started;
  if (response.status !== 200) {
    const authHint = service === "Python" && response.status === 401
      ? " Keep the existing access-code gate; provide an already-authorized session cookie through STOCK_MONITOR_PYTHON_COOKIE or leave Python timing unmeasured."
      : "";
    throw new Error(`${service} ${path} returned HTTP ${response.status}.${authHint}`);
  }
  return {
    elapsedMs,
    bytes: body.byteLength,
    status: response.status,
    cacheState: response.headers.get("x-stock-monitor-cache"),
  };
}

async function main() {
  const pythonOrigin = loopbackOrigin(process.env.STOCK_MONITOR_PYTHON_WEB_VIEW_URL ?? "http://127.0.0.1:8780", "Python origin");
  const nextOrigin = loopbackOrigin(process.env.STOCK_MONITOR_NEXT_ORIGIN ?? "http://127.0.0.1:3010", "Next origin");
  const date = process.env.STOCK_MONITOR_BENCH_DATE ?? "2026-10-08";
  const stockCode = process.env.STOCK_MONITOR_BENCH_STOCK_CODE ?? "005930";
  const cases = buildBenchmarkCases(date, stockCode);
  const pythonCookie = process.env.STOCK_MONITOR_PYTHON_COOKIE;
  const rows = [];
  const startedAt = new Date().toISOString();
  console.log(`Developer-PC stored GET benchmark | started_at=${startedAt} | date=${date} | warmups=${WARMUPS} | samples=${SAMPLES} | accept-encoding=identity`);
  console.log("Both services receive x-stock-monitor-benchmark: 1; Python ignores it. Next reports its process-local cache state. Latencies include the full loopback response body.");

  for (const benchmarkCase of cases) {
    const times = { Python: [], Next: [] };
    const firstRequest = {};
    const firstCacheState = {};
    const measuredNextCacheStates = [];
    const statuses = {};
    let pythonBytes = 0;
    let nextBytes = 0;
    for (let index = 0; index < WARMUPS + SAMPLES; index += 1) {
      const order = index % 2 === 0 ? ["Python", "Next"] : ["Next", "Python"];
      for (const service of order) {
        const result = await request(
          service === "Python" ? pythonOrigin : nextOrigin,
          benchmarkCase.path,
          pythonCookie,
          service,
        );
        if (index === 0) {
          firstRequest[service] = result.elapsedMs;
          firstCacheState[service] = result.cacheState;
        }
        statuses[service] = result.status;
        if (index >= WARMUPS) {
          times[service].push(result.elapsedMs);
          if (service === "Next") measuredNextCacheStates.push(result.cacheState);
        }
        if (service === "Python") pythonBytes = result.bytes;
        else nextBytes = result.bytes;
      }
    }
    rows.push({
      path: benchmarkCase.path,
      pythonStatus: statuses.Python,
      pythonFirst: firstRequest.Python,
      pythonP50: nearestRank(times.Python, 0.5),
      pythonP95: nearestRank(times.Python, 0.95),
      pythonBytes,
      nextStatus: statuses.Next,
      nextFirst: firstRequest.Next,
      nextFirstCache: firstCacheState.Next,
      nextMeasuredCache: countCacheStates(measuredNextCacheStates),
      nextP50: nearestRank(times.Next, 0.5),
      nextP95: nearestRank(times.Next, 0.95),
      nextBytes,
    });
  }

  console.log("| Route | Python status | Python first ms | Python post-warmup p50/p95 ms | Python bytes | Next status | Next first ms | Next first cache | Next measured hit/miss/unreported | Next p50/p95 ms | Next bytes |");
  console.log("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |");
  for (const row of rows) {
    const { hit, miss, unreported } = row.nextMeasuredCache;
    console.log(`| ${row.path} | ${row.pythonStatus} | ${row.pythonFirst.toFixed(2)} | ${row.pythonP50.toFixed(2)} / ${row.pythonP95.toFixed(2)} | ${row.pythonBytes} | ${row.nextStatus} | ${row.nextFirst.toFixed(2)} | ${row.nextFirstCache ?? "unreported"} | ${hit}/${miss}/${unreported} | ${row.nextP50.toFixed(2)} / ${row.nextP95.toFixed(2)} | ${row.nextBytes} |`);
  }
  console.log(`run_started_at=${startedAt} | run_finished_at=${new Date().toISOString()}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : "Benchmark failed.");
    process.exitCode = 1;
  });
}
