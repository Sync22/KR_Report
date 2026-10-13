import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

const pythonFixture = String.raw`
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from stock_monitor.cli import (
    _build_web_view_toss_context,
    _build_web_view_toss_investor_flow_context,
    _build_web_view_toss_recent_flow,
    _web_view_toss_capture_state,
)
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    EtfDailySnapshot,
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    OperationEvent,
    StockMarketDailySnapshot,
)

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
repository.initialize()
business_date = date(2026, 5, 8)
fetched_at = datetime(2026, 5, 8, 20, 0)
fetched_at = fetched_at.replace(tzinfo=ZoneInfo(config.timezone))
repository.upsert_stock_market_daily([
    StockMarketDailySnapshot(business_date, "000660", "SK하이닉스", "KOSPI", fetched_at, source="toss_openapi", close_price=200000, change_percent=2.0, volume=200, turnover=500),
    StockMarketDailySnapshot(business_date, "005930", "삼성전자", "KOSPI", fetched_at, source="toss_openapi", close_price=100000, change_percent=1.0, volume=100, turnover=500),
    StockMarketDailySnapshot(business_date, "035720", "카카오", "KOSDAQ", fetched_at, source="toss_openapi", close_price=50000, change_percent=-1.0, volume=300, turnover=300),
    StockMarketDailySnapshot(date(2026, 5, 7), "000660", "SK하이닉스", "KOSPI", datetime(2026, 5, 7, 20), source="toss_openapi", close_price=196000, turnover=400),
    StockMarketDailySnapshot(business_date, "999999", "과거 KRX 행", "KOSPI", fetched_at, source="krx", close_price=1, turnover=999999),
])
repository.upsert_etf_daily_snapshots([
    EtfDailySnapshot(business_date, "069500", "KODEX 200", fetched_at, source="toss_openapi", close_price=40000, nav=40100.5, volume=50, turnover=200000000, underlying_index_name="코스피 200"),
    EtfDailySnapshot(business_date, "229200", "KODEX 코스닥150", fetched_at, source="toss_openapi", close_price=15000, volume=40, turnover=200000000),
    EtfDailySnapshot(business_date, "102780", "KODEX 삼성그룹", fetched_at, source="toss_openapi", close_price=18000, volume=60, turnover=1200000000000),
    EtfDailySnapshot(date(2026, 5, 7), "069500", "KODEX 200", datetime(2026, 5, 7, 20), source="toss_openapi", close_price=39900, turnover=190),
    EtfDailySnapshot(business_date, "999999", "과거 KRX ETF", fetched_at, source="krx", close_price=1, turnover=999999),
])
repository.upsert_market_index_daily([
    MarketIndexDailySnapshot(business_date, "KOSPI", "stock", "코스피", fetched_at, source="toss_openapi", close_index=2700.5, change_percent=0.5, volume=1000, turnover=2000),
    MarketIndexDailySnapshot(business_date, "KOSDAQ", "stock", "코스닥", fetched_at, source="toss_openapi", close_index=850.5, change_percent=-0.5, volume=500, turnover=700),
    MarketIndexDailySnapshot(business_date, "KOSPI", "stock", "과거 KRX 지수", fetched_at, source="krx", close_index=1),
])
repository.upsert_market_investor_flow_daily([
    MarketInvestorFlowDaily(business_date, "KOSDAQ", "individual", fetched_at, net_buy_volume=12, net_buy_amount=1200, source="toss_openapi"),
    MarketInvestorFlowDaily(business_date, "KOSPI", "foreign", fetched_at, net_buy_volume=34, net_buy_amount=3400, source="toss_openapi"),
    MarketInvestorFlowDaily(business_date, "KOSPI", "개인", fetched_at, net_buy_volume=-56, net_buy_amount=-5600, source="toss_openapi"),
    MarketInvestorFlowDaily(business_date, "KOSPI", "foreign", fetched_at, net_buy_volume=999, net_buy_amount=99900, source="krx_data_market"),
])
repository.record_operation_event(OperationEvent(
    datetime(2026, 5, 8, 20, 1), "toss-market-context", "capture", "complete", business_date, "missing_domains=unknown"
))
repository.record_operation_event(OperationEvent(
    datetime(2026, 5, 8, 20, 2), "toss-market-context", "capture", "partial", business_date,
    "snapshot_date=2026-05-08;missing_domains=top20,unknown,market_flow",
))
repository.record_operation_event(OperationEvent(
    datetime(2026, 5, 6, 20), "toss-market-context", "capture", "empty", date(2026, 5, 6), None
))
repository.record_operation_event(OperationEvent(
    datetime(2026, 5, 5, 20), "toss-market-context", "capture", "failed", date(2026, 5, 5), None
))

def projection(selected_date):
    capture_state = _web_view_toss_capture_state(repository, selected_date)
    recent_dates = repository.list_recent_toss_market_snapshot_dates(on_or_before=selected_date, limit=3)
    return {
        "capture_state": capture_state,
        "toss_context": _build_web_view_toss_context(repository, selected_date, capture_state=capture_state),
        "toss_recent_flow": _build_web_view_toss_recent_flow(repository, selected_date, recent_snapshot_dates=recent_dates),
        "toss_investor_flow": _build_web_view_toss_investor_flow_context(repository, selected_date),
    }

print(json.dumps({
    "2026-05-08": projection(business_date),
    "2026-05-06": projection(date(2026, 5, 6)),
    "2026-05-05": projection(date(2026, 5, 5)),
    "2026-05-04": projection(date(2026, 5, 4)),
}, ensure_ascii=False, separators=(",", ":")))
`;

function pythonProjection(root) {
  const projectRoot = resolve(process.cwd(), "..");
  const result = spawnSync("python", ["-c", pythonFixture, root], {
    cwd: projectRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: resolve(projectRoot, "src"),
    },
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  return JSON.parse(result.stdout);
}

test("Toss daily projections match Python source/date/order rules on a read-only snapshot", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-toss-context-"));
  const databasePath = resolve(root, "data", "stock_monitor.db");
  try {
    const expectedByDate = pythonProjection(root);
    const before = await stat(databasePath);
    const projectionModule = await import("../src/server/daily-toss-context.ts").catch(() => ({}));
    assert.equal(typeof projectionModule.buildDailyTossContextFromDatabase, "function");

    for (const [businessDate, expected] of Object.entries(expectedByDate)) {
      const database = new DatabaseSync(databasePath, { readOnly: true });
      try {
        database.exec("PRAGMA query_only = ON");
        database.exec("BEGIN");
        const actual = projectionModule.buildDailyTossContextFromDatabase(database, businessDate);
        database.exec("COMMIT");
        assert.deepEqual(actual, expected);
      } catch (error) {
        database.exec("ROLLBACK");
        throw error;
      } finally {
        database.close();
      }
    }

    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
