import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

const BUSINESS_DATE = "2026-05-04";
const FIXED_NOW = "2026-05-05T03:00:00+00:00";
const FIXTURE_SCRIPT = String.raw`
import json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from stock_monitor.cli import build_web_view_backtest_observation_snapshot
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import InvestorNetBuyTopDaily, Report, StockInvestorFlowDaily, StockMarketDailySnapshot

business_date = date.fromisoformat(sys.argv[2])
repository = StockMonitorRepository(Path(sys.argv[1]), timezone="Asia/Seoul")
repository.initialize()

def report(code, name, broker, report_id, target, report_date=business_date):
    return Report(
        stock_name=name, stock_code=code, title=f"저장 리포트 {report_id}", broker_name=broker,
        published_at=datetime.combine(report_date, datetime.min.time()),
        collected_at=datetime(2026, 5, 4, 20, 0), business_date=report_date,
        target_price_raw=str(target), target_price_value=target, opinion_raw="Buy",
        opinion_normalized="buy", source_url=f"https://example.test/{report_id}",
        source_id=report_id, identity_key=report_id,
    )

repository.insert_reports([
    report("005930", "삼성전자", "NH투자증권", "samsung-1", 9000),
    report("005930", "삼성전자", "KB증권", "samsung-2", 10000),
    report("005930", "삼성전자", "하나증권", "samsung-prior", 8500, business_date - timedelta(days=1)),
    report("000660", "SK하이닉스", "NH투자증권", "hynix-1", 12000),
    report("000660", "SK하이닉스", "KB증권", "hynix-2", 13000),
    report("LEGACY", "Legacy 종목", "테스트증권", "legacy-1", 50000),
    report("LEGACY", "Legacy 종목", "테스트증권", "legacy-2", 52000),
])
repository.rebuild_daily_summaries(business_date)

repository.upsert_stock_market_daily([
    StockMarketDailySnapshot(
        business_date=business_date + timedelta(days=index), stock_code="005930", stock_name="삼성전자",
        market="KOSPI", close_price=8000 + index * 10, volume=1000 + index,
        turnover=2000 + index * 100, fetched_at=datetime(2026, 5, 4, 20, 0), source="krx",
    )
    for index in range(21)
])
repository.upsert_stock_market_daily([
    StockMarketDailySnapshot(
        business_date=business_date, stock_code="005930", stock_name="삼성전자", market="KOSPI",
        close_price=99999, volume=99999, turnover=99999,
        fetched_at=datetime(2026, 5, 4, 20, 1), source="toss_openapi",
    )
])
repository.upsert_stock_investor_flow_daily([
    StockInvestorFlowDaily(
        business_date=business_date, stock_code="005930", stock_name="삼성전자", market="STK",
        investor_type=investor, net_buy_volume=volume, net_buy_amount=amount,
        fetched_at=datetime(2026, 5, 4, 20, 0), source="krx_data_market",
    )
    for investor, volume, amount in [("개인", -4, -500), ("외국인", 5, 800), ("기관", 2, 300), ("기관합계", 3, 400)]
])
repository.upsert_stock_investor_flow_daily([
    StockInvestorFlowDaily(
        business_date=business_date, stock_code="005930", stock_name="삼성전자", market="STK",
        investor_type="외국인", net_buy_volume=99999, net_buy_amount=99999,
        fetched_at=datetime(2026, 5, 4, 20, 1), source="toss_openapi",
    )
])
repository.upsert_investor_net_buy_top_daily([
    InvestorNetBuyTopDaily(
        business_date=business_date, market="STK", investor_type="foreign", rank=2,
        stock_code="005930", stock_name="삼성전자", net_buy_volume=5, net_buy_amount=800,
        fetched_at=datetime(2026, 5, 4, 20, 0), source="krx_data_market",
    )
])

now = datetime.fromisoformat(sys.argv[3]).astimezone(ZoneInfo("Asia/Seoul"))
snapshot = build_web_view_backtest_observation_snapshot(
    SimpleNamespace(timezone="Asia/Seoul"), repository,
    business_date=business_date, mention_threshold=2, limit=20, now=now,
)
print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
`;

function createFixture() {
  const root = mkdtempSync(join(tmpdir(), "stock-monitor-backtest-"));
  const databasePath = join(root, "stock_monitor.db");
  const projectRoot = resolve(process.cwd(), "..");
  const pythonPath = [resolve(projectRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(";");
  const result = spawnSync("python", ["-c", FIXTURE_SCRIPT, databasePath, BUSINESS_DATE, FIXED_NOW], {
    cwd: projectRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: pythonPath, PYTHONIOENCODING: "utf-8" },
    timeout: 30000,
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message || "Python backtest fixture failed");
  return { root, databasePath, expected: JSON.parse(result.stdout) };
}

function withoutNow(snapshot) {
  const { now: _now, ...rest } = snapshot;
  return rest;
}

test("direct backtest snapshot matches Python DTO in one read-only SQLite snapshot", async () => {
  const { root, databasePath, expected } = createFixture();
  const oldPath = process.env.STOCK_MONITOR_DB_PATH;
  const oldTimezone = process.env.STOCK_MONITOR_TIMEZONE;
  try {
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    process.env.STOCK_MONITOR_TIMEZONE = "Asia/Seoul";
    const before = statSync(databasePath);
    const service = await import("../src/server/backtest-observation.ts");
    const domain = await import("../src/domain/observation.ts");
    const route = await import("../src/app/api/observation/backtest/route.ts");
    const actual = service.getBacktestObservationSnapshot(BUSINESS_DATE, 20, 2, new Date(FIXED_NOW));
    const response = route.GET(new Request(`http://next.local/api/observation/backtest?date=${BUSINESS_DATE}&limit=20&mention_threshold=2&ignored=x`));
    assert.equal(response.status, 200);
    const routed = await response.json();

    assert.deepEqual(withoutNow(actual), withoutNow(expected));
    assert.deepEqual(withoutNow(routed), withoutNow(expected));
    assert.equal(domain.isBacktestObservationSnapshot(actual, BUSINESS_DATE), true);
    const samsung = actual.rows.find((row) => row.stock_code === "005930");
    const skHynix = actual.rows.find((row) => row.stock_code === "000660");
    assert.equal(samsung.reaction_windows[0].close_return_percent, 0.12);
    assert.equal(samsung.stock_flow_observation.institution_net_buy_volume, 5);
    assert.equal(samsung.stock_flow_observation.institution_net_buy_amount, 700);
    assert.equal(samsung.net_buy_top_observation.market, "KOSPI");
    assert.equal(skHynix.target_observation.progress_caution, false);
    assert.equal(skHynix.target_observation.progress_notice, null);
    assert.equal(skHynix.target_observation.validation_notice, null);
    assert.equal(samsung.target_observation.baseline_date, "2026-05-03");
    assert.equal(samsung.target_observation.baseline_price, null);
    assert.equal(samsung.target_observation.progress_notice, null);
    assert.equal(samsung.target_observation.validation_notice, "missing_baseline_price");
    assert.equal(actual.rows.some((row) => row.stock_code === "LEGACY"), true);
    assert.equal(domain.isBacktestObservationSnapshot(actual, BUSINESS_DATE), true);

    const after = statSync(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
    const writable = new DatabaseSync(databasePath);
    writable.exec("BEGIN IMMEDIATE; ROLLBACK");
    writable.close();
  } finally {
    if (oldPath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = oldPath;
    if (oldTimezone === undefined) delete process.env.STOCK_MONITOR_TIMEZONE;
    else process.env.STOCK_MONITOR_TIMEZONE = oldTimezone;
    rmSync(root, { recursive: true, force: true });
  }
});

test("backtest route keeps Python date, query bounds, and GET-only behavior", async () => {
  const { root, databasePath } = createFixture();
  const oldPath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const route = await import("../src/app/api/observation/backtest/route.ts");
    for (const response of [route.HEAD(), route.OPTIONS(), route.POST(), route.PUT(), route.PATCH(), route.DELETE()]) {
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(route.GET(new Request("http://next.local/api/observation/backtest")).status, 400);
    assert.equal(route.GET(new Request("http://next.local/api/observation/backtest?date=2026-02-30")).status, 400);

    const defaults = await route.GET(new Request(`http://next.local/api/observation/backtest?date=&date=${BUSINESS_DATE}&limit=&limit=1&mention_threshold=`)).json();
    assert.equal(defaults.mention_threshold, 2);
    assert.equal(defaults.rows.length, 1);
    const bounded = await route.GET(new Request(`http://next.local/api/observation/backtest?date=${BUSINESS_DATE}&limit=999&mention_threshold=999`)).json();
    assert.equal(bounded.mention_threshold, 20);
    assert.equal(bounded.rows.length, 0);
  } finally {
    if (oldPath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = oldPath;
    rmSync(root, { recursive: true, force: true });
  }
});

test("backtest route returns a generic failure and releases its read transaction", async () => {
  const root = mkdtempSync(join(tmpdir(), "stock-monitor-backtest-error-"));
  const databasePath = join(root, "fixture.db");
  const database = new DatabaseSync(databasePath);
  database.exec("CREATE TABLE unrelated (value TEXT)");
  database.close();
  const oldPath = process.env.STOCK_MONITOR_DB_PATH;
  try {
    process.env.STOCK_MONITOR_DB_PATH = databasePath;
    const route = await import("../src/app/api/observation/backtest/route.ts");
    const response = route.GET(new Request("http://next.local/api/observation/backtest?date=2026-05-06"));
    assert.equal(response.status, 503);
    assert.equal(await response.text(), "backtest observation unavailable");
    const writable = new DatabaseSync(databasePath);
    writable.exec("BEGIN IMMEDIATE; ROLLBACK");
    writable.close();
  } finally {
    if (oldPath === undefined) delete process.env.STOCK_MONITOR_DB_PATH;
    else process.env.STOCK_MONITOR_DB_PATH = oldPath;
    rmSync(root, { recursive: true, force: true });
  }
});
