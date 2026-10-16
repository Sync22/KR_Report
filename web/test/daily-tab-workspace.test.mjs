import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import { isDailyStockSummarySnapshot } from "../src/domain/daily.ts";

const businessDate = "2026-10-08";
const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const pythonSetup = String.raw`
import sys
from pathlib import Path
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
repository = StockMonitorRepository(root / "data" / "stock_monitor.db", timezone=config.timezone)
repository.initialize()
`;
const pythonDaily = String.raw`
import json, sys
from datetime import date, datetime
from pathlib import Path
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.cli import _omit_none_values, build_web_view_daily_snapshot

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
repository = StockMonitorRepository(root / "data" / "stock_monitor.db", timezone=config.timezone)
snapshot = _omit_none_values(build_web_view_daily_snapshot(
    config,
    repository,
    business_date=date.fromisoformat(sys.argv[2]),
    now=datetime.fromisoformat(sys.argv[3]),
    include_observation_summary=False,
))
print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
`;

function initializeFixture(root) {
  const result = spawnSync("python", ["-c", pythonSetup, root], {
    cwd: projectRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      STOCK_MONITOR_DB_PATH: "",
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: resolve(projectRoot, "src"),
    },
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
}

function expectedPythonDaily(root, now) {
  const result = spawnSync("python", ["-c", pythonDaily, root, businessDate, now], {
    cwd: projectRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      STOCK_MONITOR_DB_PATH: "",
      PYTHONIOENCODING: "utf-8",
      PYTHONPATH: resolve(projectRoot, "src"),
    },
  });
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  return JSON.parse(result.stdout);
}

function withoutNulls(value) {
  if (Array.isArray(value)) return value.map(withoutNulls);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== null).map(([key, item]) => [key, withoutNulls(item)]));
  }
  return value;
}

function withoutDynamicClockFields(value) {
  if (Array.isArray(value)) return value.map(withoutDynamicClockFields);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value)
      .filter(([key, item]) => key !== "now" && item !== null)
      .map(([key, item]) => [key, withoutDynamicClockFields(item)]));
  }
  return value;
}

test("daily tab workspace builds its panels from one candidate read and one SQLite snapshot", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-daily-tab-workspace-"));
  const databasePath = join(root, "data", "stock_monitor.db");
  try {
    initializeFixture(root);
    const writeDb = new DatabaseSync(databasePath);
    writeDb.prepare(`
      INSERT INTO daily_stock_summaries (
        business_date, stock_name, stock_code, mention_count, broker_display,
        target_price_min, target_price_max, dominant_opinion, generated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(businessDate, "삼성전자", "005930", 2, "증권사 A (1)", 70000, 80000, "buy", `${businessDate}T20:00:00+09:00`);
    writeDb.prepare(`
      INSERT INTO stock_market_daily (
        business_date, stock_code, stock_name, market, section_name,
        close_price, change_amount, change_percent, open_price, high_price, low_price,
        volume, turnover, market_cap, listed_shares, fetched_at, source
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(businessDate, "005930", "삼성전자", "KOSPI", null, null, null, null, null, null, null, null, null, null, null, `${businessDate}T20:00:00+09:00`, "toss_openapi");
    writeDb.close();

    const before = await stat(databasePath);
    const fixedNow = "2026-10-13T12:00:00+09:00";
    const expectedDaily = expectedPythonDaily(root, fixedNow);
    const database = new DatabaseSync(databasePath, { readOnly: true });
    const reads = { candidateSummary: 0 };
    const observedDatabase = new Proxy(database, {
      get(target, property) {
        if (property === "prepare") return (sql, ...args) => {
          if (String(sql).includes("FROM daily_stock_summaries") && String(sql).includes("stock_code IS NOT NULL")) {
            reads.candidateSummary += 1;
          }
          const statement = target.prepare(sql, ...args);
          return new Proxy(statement, {
            get(row, method) {
              const value = Reflect.get(row, method, row);
              return typeof value === "function" ? value.bind(row) : value;
            },
          });
        };
        const value = Reflect.get(target, property, target);
        return typeof value === "function" ? value.bind(target) : value;
      },
    });

    let workspace;
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      workspace = (await import("../src/server/daily-tab-workspace.ts"))
        .buildDailyTabWorkspaceFromDatabase(observedDatabase, businessDate, null, new Date("2026-10-13T03:00:00Z"));
      database.exec("ROLLBACK");
    } finally {
      database.close();
    }

    assert.equal(reads.candidateSummary, 1);
    assert.deepEqual(
      workspace.daily.priority_candidate_evidence.rows,
      withoutNulls(workspace.candidates.rows.slice(0, 2)),
    );
    assert.equal(workspace.daily.stocks[0].stock_code, "005930");
    assert.equal(workspace.stocks.stocks[0].stock_code, "005930");
    assert.equal(isDailyStockSummarySnapshot(workspace.stocks, businessDate), true);
    assert.deepEqual(withoutDynamicClockFields(workspace.daily), withoutDynamicClockFields(expectedDaily));
    assert.equal("flow" in workspace, false);
    assert.equal(workspace.selectedStockDetail, null);
    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
