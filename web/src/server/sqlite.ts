import "server-only";

import { DatabaseSync } from "node:sqlite";
import { resolve } from "node:path";

export function withReadOnlyDatabase<T>(read: (database: DatabaseSync) => T): T {
  const projectRoot = resolve(process.cwd(), "..");
  const databasePath = resolve(projectRoot, process.env.STOCK_MONITOR_DB_PATH?.trim() || "data/stock_monitor.db");
  const database = new DatabaseSync(databasePath, { readOnly: true, timeout: 5000 });
  try {
    database.exec("PRAGMA query_only = ON");
    return read(database);
  } finally {
    database.close();
  }
}
