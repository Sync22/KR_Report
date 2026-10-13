import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

const scenarios = [
  {
    id: "priority_partial",
    business_date: "2026-05-08",
    report_count: 5,
    candidate_codes: ["000003", "000004"],
    ready: true,
  },
  {
    id: "priority_exact_without_reports",
    business_date: "2026-05-08",
    report_count: 0,
    candidate_codes: ["000001", "000004"],
    ready: false,
  },
  {
    id: "default_candidate_order",
    business_date: "2026-05-08",
    report_count: 5,
    candidate_codes: [],
    ready: false,
  },
  {
    id: "exact_fallback_and_complete_capture",
    business_date: "2026-05-07",
    report_count: 0,
    candidate_codes: [],
    ready: false,
  },
  {
    id: "stale_and_failed_capture",
    business_date: "2026-05-09",
    report_count: 0,
    candidate_codes: ["999999"],
    ready: false,
  },
  {
    id: "missing_and_empty_capture",
    business_date: "2026-05-06",
    report_count: 0,
    candidate_codes: [],
    ready: true,
  },
];

const pythonFixture = String.raw`
import json
import sys
from datetime import date
from pathlib import Path

from stock_monitor.cli import (
    _apply_toss_capture_state_to_freshness_item,
    _build_stock_flow_source_freshness_item,
    _build_web_view_source_freshness_summary,
    _web_view_toss_capture_state,
)
from stock_monitor.db.repository import StockMonitorRepository

root = Path(sys.argv[1])
root.joinpath("data").mkdir(parents=True, exist_ok=True)
repository = StockMonitorRepository(root / "data" / "stock_monitor.db", timezone="Asia/Seoul")
repository.initialize()

with repository.connect() as connection, connection:
    connection.executemany(
        """
        INSERT INTO daily_stock_summaries (
            business_date, stock_name, stock_code, mention_count, broker_display,
            target_price_min, target_price_max, dominant_opinion, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-08", "Alpha", "000001", 4, "Broker", None, None, "neutral", "2026-05-08T20:00:00"),
            ("2026-05-08", "Beta", "000002", 3, "Broker", None, None, "neutral", "2026-05-08T20:00:00"),
            ("2026-05-08", "Gamma", "000003", 2, "Broker", None, None, "neutral", "2026-05-08T20:00:00"),
            ("2026-05-08", "Delta", "000004", 1, "Broker", None, None, "neutral", "2026-05-08T20:00:00"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO stock_market_daily (
            business_date, stock_code, stock_name, market, close_price,
            change_percent, turnover, fetched_at, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-08", "000001", "Alpha", "KOSPI", 1000, 1.0, 100, "2026-05-08T20:00:00", "toss_openapi"),
            ("2026-05-07", "000001", "Alpha", "KOSPI", 990, 1.0, 90, "2026-05-07T20:00:00", "toss_openapi"),
        ],
    )
    connection.execute(
        """
        INSERT INTO etf_daily_snapshots (
            business_date, etf_code, etf_name, close_price, fetched_at, source
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("2026-05-07", "069500", "KODEX 200", 40000, "2026-05-07T20:00:00", "toss_openapi"),
    )
    connection.executemany(
        """
        INSERT INTO stock_investor_flow_daily (
            business_date, stock_code, stock_name, market, investor_type,
            net_buy_volume, fetched_at, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-08", "000001", "Alpha", "KOSPI", "외국인", 10, "2026-05-08T20:00:00", "toss_openapi"),
            ("2026-05-07", "000001", "Alpha", "KOSPI", "외국인", 9, "2026-05-07T20:00:00", "toss_openapi"),
            ("2026-05-08", "000002", "Beta", "KOSPI", "외국인", 8, "2026-05-08T20:00:00", "toss_openapi"),
            ("2026-05-07", "000003", "Gamma", "KOSPI", "외국인", 7, "2026-05-07T20:00:00", "toss_openapi"),
            ("2026-05-08", "000004", "Delta", "KOSPI", "외국인", 6, "2026-05-08T20:00:00", "toss_openapi"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO market_investor_flow_daily (
            business_date, market, investor_type, net_buy_volume, fetched_at, source
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-08", "KOSPI", "외국인", 100, "2026-05-08T20:00:00", "toss_openapi"),
            ("2026-05-07", "KOSPI", "외국인", 90, "2026-05-07T20:00:00", "toss_openapi"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO operation_events (event_time, component, event_type, status, business_date, detail)
        VALUES (?, 'toss-market-context', 'capture', ?, ?, ?)
        """,
        [
            ("2026-05-08T20:01:00+09:00", "complete", "2026-05-08", "missing_domains=unknown"),
            ("2026-05-08T20:02:00+09:00", "partial", "2026-05-08", "snapshot_date=2026-05-08;missing_domains=top20,unknown,market_flow,candidate_close_reassessment"),
            ("2026-05-07T20:02:00+09:00", "complete", "2026-05-07", "missing_domains=security_metadata,unknown"),
            ("2026-05-09T20:02:00+09:00", "failed", "2026-05-09", None),
            ("2026-05-06T20:02:00+09:00", "empty", "2026-05-06", None),
        ],
    )

def project(scenario):
    business_date = date.fromisoformat(scenario["business_date"])
    summaries = repository.list_daily_summaries(business_date)
    investor_flow_item = _build_stock_flow_source_freshness_item(
        repository,
        business_date,
        summaries=summaries,
        priority_stock_codes=scenario["candidate_codes"],
    )
    result = _build_web_view_source_freshness_summary(
        business_date=business_date,
        report_count=scenario["report_count"],
        recent_toss_snapshot_dates=repository.list_recent_toss_market_snapshot_dates(
            on_or_before=business_date, limit=3
        ),
        recent_toss_etf_snapshot_dates=repository.list_recent_toss_etf_snapshot_dates(
            on_or_before=business_date, limit=1
        ),
        recent_flow_dates=repository.list_recent_investor_flow_dates(
            on_or_before=business_date, source="toss_openapi", limit=1
        ),
        toss_openapi_ready=scenario["ready"],
        investor_flow_item=investor_flow_item,
    )
    capture_state = _web_view_toss_capture_state(repository, business_date)
    toss_market_item = next(item for item in result["items"] if item["key"] == "toss_market")
    _apply_toss_capture_state_to_freshness_item(toss_market_item, capture_state)
    return result

print(json.dumps({scenario["id"]: project(scenario) for scenario in json.loads(sys.argv[2])}, ensure_ascii=False, separators=(",", ":")))
`;

function pythonProjection(root) {
  const projectRoot = resolve(process.cwd(), "..");
  const result = spawnSync("python", ["-c", pythonFixture, root, JSON.stringify(scenarios)], {
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

test("daily source freshness matches Python while reading the caller's read-only SQLite connection", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-daily-freshness-"));
  const databasePath = resolve(root, "data", "stock_monitor.db");
  try {
    const expectedById = pythonProjection(root);
    const before = await stat(databasePath);
    const projectionModule = await import("../src/server/daily-freshness.ts").catch(() => ({}));
    assert.equal(typeof projectionModule.buildDailySourceFreshnessFromDatabase, "function");

    const database = new DatabaseSync(databasePath, { readOnly: true });
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      const actualById = Object.fromEntries(scenarios.map((scenario) => [
        scenario.id,
        projectionModule.buildDailySourceFreshnessFromDatabase(database, scenario.business_date, {
          reportCount: scenario.report_count,
          candidateStockCodes: scenario.candidate_codes,
          tossOpenApiReady: scenario.ready,
        }),
      ]));
      assert.deepEqual(actualById, expectedById);
      assert.deepEqual(actualById.priority_partial.items.map((item) => item.key), [
        "reports", "toss_market", "toss_etf", "investor_flow", "toss_openapi",
      ]);
      const priorityFlow = actualById.priority_partial.items[3];
      assert.equal(priorityFlow.status, "partial");
      assert.equal(priorityFlow.reference_date, "2026-05-08");
      assert.deepEqual(priorityFlow.reference_dates, ["2026-05-08", "2026-05-07"]);
      assert.equal(priorityFlow.coverage_count, 2);
      assert.equal(priorityFlow.candidate_count, 2);
      assert.deepEqual(actualById.priority_partial.items[1].missing_domains, [
        "top20", "market_flow", "candidate_close_reassessment",
      ]);
      assert.equal(actualById.priority_exact_without_reports.items[0].status, "missing");
      assert.equal(actualById.priority_exact_without_reports.items[3].status, "exact");
      assert.equal(actualById.exact_fallback_and_complete_capture.items[3].data_scope, "stored_toss_close_market_flow");
      assert.equal(actualById.stale_and_failed_capture.items[1].status, "stale");
      assert.equal(actualById.stale_and_failed_capture.items[1].capture_status, "failed");
      assert.equal(actualById.missing_and_empty_capture.items[1].status, "missing");
      assert.equal(actualById.missing_and_empty_capture.items[1].capture_status, "empty");
      database.exec("COMMIT");
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    } finally {
      database.close();
    }

    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
