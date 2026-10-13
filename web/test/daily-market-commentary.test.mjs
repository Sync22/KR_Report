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
from types import SimpleNamespace

from stock_monitor import cli
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    MarketIndexDailySnapshot,
    MarketInvestorFlowDaily,
    Report,
    StockMarketDailySnapshot,
)

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
repository.initialize()

def report(day, name, code, title, source_id, hour, minute=0, target=None):
    return Report(
        stock_name=name,
        stock_code=code,
        title=title,
        broker_name="NH투자증권",
        published_at=datetime(day.year, day.month, day.day, hour, minute),
        business_date=day,
        collected_at=datetime(day.year, day.month, day.day, hour, minute + 5),
        target_price_value=target,
        opinion_normalized="buy" if target else "na",
        source_url=f"https://stock.naver.com/research/company/{source_id}",
        source_id=source_id,
        identity_key=source_id,
    )

previous_date = date(2026, 5, 7)
business_date = date(2026, 5, 8)
repository.insert_reports([
    report(previous_date, "전일후보A", "111111", "전일 리포트 A", "previous-a", 9, target=50000),
    report(previous_date, "전일후보B", "222222", "전일 리포트 B", "previous-b", 10, target=70000),
    report(business_date, "삼성전자", "005930", "반도체 수요 점검", "today-a1", 9, target=100000),
    report(business_date, "삼성전자", "005930", "메모리 수급 개선", "today-a2", 10, target=110000),
    report(business_date, "기아", "000270", "신차 판매 호조", "today-b", 11, target=140000),
    report(business_date, "코드없는 종목", None, "코드 미확인 리포트", "today-c", 12),
])
repository.rebuild_daily_summaries(previous_date)
repository.rebuild_daily_summaries(business_date)

fetched_at = datetime(2026, 5, 7, 20, 0)
repository.upsert_market_index_daily([
    MarketIndexDailySnapshot(
        business_date=previous_date, index_series="KOSPI", index_class="KOSPI",
        index_name="코스피", close_index=2745.11, change_percent=0.8,
        fetched_at=fetched_at, source="toss_openapi",
    ),
    MarketIndexDailySnapshot(
        business_date=previous_date, index_series="KOSDAQ", index_class="KOSDAQ",
        index_name="코스닥", close_index=850.25, change_percent=-0.3,
        fetched_at=fetched_at, source="toss_openapi",
    ),
])
repository.upsert_stock_market_daily([
    StockMarketDailySnapshot(business_date=previous_date, stock_code="000001", stock_name="가온", market="KOSPI", turnover=3_500_000_000_000, fetched_at=fetched_at, source="toss_openapi"),
    StockMarketDailySnapshot(business_date=previous_date, stock_code="000002", stock_name="나래", market="KOSPI", turnover=45_000_000_000, fetched_at=fetched_at, source="toss_openapi"),
    StockMarketDailySnapshot(business_date=previous_date, stock_code="000003", stock_name="다온", market="KOSPI", turnover=80_000_000, fetched_at=fetched_at, source="toss_openapi"),
    StockMarketDailySnapshot(business_date=previous_date, stock_code="000004", stock_name="라온", market="KOSDAQ", turnover=1_200_000_000_000, fetched_at=fetched_at, source="toss_openapi"),
    StockMarketDailySnapshot(business_date=previous_date, stock_code="000005", stock_name="마루", market="KOSDAQ", turnover=15_000_000, fetched_at=fetched_at, source="toss_openapi"),
])
flows = []
for market, values in (
    ("KOSPI", {"개인": 12_000_000_000, "외국인": -8_000_000_000, "기관": 2_000_000_000, "기관합계": 6_000_000_000}),
    ("KOSDAQ", {"개인": -4_000_000_000, "외국인": 9_000_000_000, "기관": -1_000_000_000, "기관합계": -5_000_000_000}),
):
    for investor_type, net_amount in values.items():
        flows.append(MarketInvestorFlowDaily(
            business_date=previous_date,
            market=market,
            investor_type=investor_type,
            sell_amount=10_000_000_000,
            buy_amount=10_000_000_000 + net_amount,
            net_buy_amount=net_amount,
            volume_unit="주",
            amount_unit="원",
            fetched_at=fetched_at,
            source="toss_openapi",
        ))
repository.upsert_market_investor_flow_daily(flows)
repository.upsert_market_index_daily([
    MarketIndexDailySnapshot(
        business_date=previous_date, index_series="KOSPI", index_class="KOSPI",
        index_name="코스피", close_index=1, change_percent=50,
        fetched_at=fetched_at, source="krx_open_api",
    ),
])

summaries = repository.list_daily_summaries(business_date)
mood_sectors = [
    SimpleNamespace(sector_name="반도체", display_name="반도체", report_count=2),
    SimpleNamespace(sector_name=None, display_name="N/A", report_count=99),
    SimpleNamespace(sector_name="자동차", display_name="자동차", report_count=1),
]
summary_rows = [
    {
        "business_date": item.business_date.isoformat(),
        "stock_name": item.stock_name,
        "stock_code": item.stock_code,
        "mention_count": item.mention_count,
        "broker_display": item.broker_display,
        "target_price_min": item.target_price_min,
        "target_price_max": item.target_price_max,
        "dominant_opinion": item.dominant_opinion,
    }
    for item in summaries
]
sector_rows = [
    {"sector_name": item.sector_name, "display_name": item.display_name, "report_count": item.report_count}
    for item in mood_sectors
]
briefing = cli._build_web_view_market_briefing_context(repository, business_date, summaries=summaries)
commentary = cli._build_market_commentary_practice_snapshot(
    config, repository, None, summaries=summaries, market_briefing=briefing,
)
print(json.dumps({
    "business_date": business_date.isoformat(),
    "summaries": summary_rows,
    "sectors": sector_rows,
    "market_mood": cli._build_market_mood_snapshot(business_date, summaries, mood_sectors),
    "market_briefing": briefing,
    "market_commentary": commentary,
}, ensure_ascii=False, separators=(",", ":")))
`;

function pythonSnapshot(root) {
  const projectRoot = resolve(process.cwd(), "..");
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => key !== "STOCK_MONITOR_DB_PATH"));
  const result = spawnSync("python", ["-c", pythonFixture, root], {
    cwd: projectRoot,
    encoding: "utf8",
    env: {
      ...env,
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: resolve(projectRoot, "src"),
    },
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  return JSON.parse(result.stdout);
}

test("daily market commentary helpers match the stored Python builders without changing SQLite", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-daily-market-commentary-"));
  const databasePath = resolve(root, "data", "stock_monitor.db");
  try {
    const expected = pythonSnapshot(root);
    const before = await stat(databasePath);
    const helpers = await import("../src/server/daily-market-commentary.ts").catch(() => ({}));
    assert.equal(typeof helpers.buildMarketMoodSnapshot, "function");
    assert.equal(typeof helpers.buildWebViewMarketBriefingContext, "function");
    assert.equal(typeof helpers.buildMarketCommentaryPracticeSnapshot, "function");

    const database = new DatabaseSync(databasePath, { readOnly: true });
    let actual;
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      const marketBriefing = helpers.buildWebViewMarketBriefingContext(
        database,
        expected.business_date,
        expected.summaries,
      );
      actual = {
        market_mood: helpers.buildMarketMoodSnapshot(
          expected.business_date,
          expected.summaries,
          expected.sectors,
        ),
        market_briefing: marketBriefing,
        market_commentary: helpers.buildMarketCommentaryPracticeSnapshot(
          database,
          null,
          { summaries: expected.summaries, marketBriefing },
        ),
      };
      database.exec("COMMIT");
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    } finally {
      database.close();
    }

    assert.deepEqual(actual, {
      market_mood: expected.market_mood,
      market_briefing: expected.market_briefing,
      market_commentary: expected.market_commentary,
    });
    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
