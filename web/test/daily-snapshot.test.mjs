import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

const businessDate = "2020-01-02";
const pythonFixture = String.raw`
import json, sys
from datetime import date
from pathlib import Path
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.cli import _omit_none_values, build_web_view_daily_snapshot

root = Path(sys.argv[1])
config = RuntimeConfig.from_env(root_dir=root)
repository = StockMonitorRepository(root / "data" / "stock_monitor.db", timezone=config.timezone)
repository.initialize()
snapshot = _omit_none_values(build_web_view_daily_snapshot(
    config,
    repository,
    business_date=date.fromisoformat(sys.argv[2]),
    include_observation_summary=False,
))
print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
`;

function pythonSnapshot(root) {
  const projectRoot = resolve(process.cwd(), "..");
  const result = spawnSync("python", ["-c", pythonFixture, root, businessDate], {
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

test("daily snapshot composes the Python default DTO from one read-only SQLite connection", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "stock-monitor-daily-snapshot-"));
  const databasePath = resolve(root, "data", "stock_monitor.db");
  try {
    const expected = pythonSnapshot(root);
    const before = await stat(databasePath);
    const { buildDailySnapshotFromDatabase } = await import("../src/server/daily-snapshot.ts");
    const database = new DatabaseSync(databasePath, { readOnly: true });
    const queryCounts = { tossMarketDateLookups: 0 };
    const observedDatabase = new Proxy(database, {
      get(target, property) {
        if (property === "prepare") return (sql, ...args) => {
          if (String(sql).includes("toss_market_context_snapshots") && String(sql).includes("business_date <= ?")) {
            queryCounts.tossMarketDateLookups += 1;
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
    let actual;
    try {
      database.exec("PRAGMA query_only = ON");
      database.exec("BEGIN");
      actual = buildDailySnapshotFromDatabase(observedDatabase, businessDate, {
        timezone: process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
        tossOpenApiReady: false,
      });
      database.exec("ROLLBACK");
    } finally {
      database.close();
    }

    const withoutDynamicClockFields = (snapshot) => {
      const { now: _now, priority_candidate_evidence: candidate, ...rest } = snapshot;
      const { now: _candidateNow, ...priorityCandidate } = candidate;
      return { ...rest, priority_candidate_evidence: priorityCandidate };
    };
    assert.deepEqual(withoutDynamicClockFields(actual), withoutDynamicClockFields(expected));
    assert.equal(queryCounts.tossMarketDateLookups, 1);
    const after = await stat(databasePath);
    assert.equal(after.size, before.size);
    assert.equal(after.mtimeMs, before.mtimeMs);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
