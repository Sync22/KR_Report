import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { IntradaySnapshot } from "../domain/intraday.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type IntradayBatchRow = {
  business_date: string;
  created_at: string;
  status: string;
  report_count: number;
  stock_count: number;
};

function intradayStatusLabel(status: string): "발송됨" | "대기" | "확인필요" {
  if (status === "sent") return "발송됨";
  if (status === "pending") return "대기";
  return "확인필요";
}

export function buildIntradaySnapshot(
  database: DatabaseSync,
  businessDate: string,
  now = new Date(),
  timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul",
): IntradaySnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid intraday business date");
  const rows = database.prepare(`
    SELECT
      b.business_date,
      b.created_at,
      b.status,
      COUNT(abr.report_identity_key) AS report_count,
      COUNT(DISTINCT COALESCE(NULLIF(TRIM(r.stock_code), ''), r.stock_name)) AS stock_count
    FROM intraday_alert_batches b
    LEFT JOIN intraday_alert_batch_reports abr ON abr.batch_id = b.batch_id
    LEFT JOIN reports r ON r.identity_key = abr.report_identity_key
    WHERE b.business_date = ?
    GROUP BY b.batch_id, b.business_date, b.created_at, b.status
    ORDER BY b.created_at ASC, b.batch_id ASC
  `).all(businessDate) as unknown as IntradayBatchRow[];

  return {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    batches: rows.map((row) => {
      if (typeof row.business_date !== "string" || typeof row.created_at !== "string" || typeof row.status !== "string" ||
        !Number.isSafeInteger(row.report_count) || row.report_count < 0 ||
        !Number.isSafeInteger(row.stock_count) || row.stock_count < 0) {
        throw new Error("Invalid stored intraday batch summary");
      }
      return {
        business_date: row.business_date,
        created_at: row.created_at,
        status_label: intradayStatusLabel(row.status),
        report_count: row.report_count,
        stock_count: row.stock_count,
      };
    }),
  };
}

export function getIntradaySnapshot(businessDate: string, now = new Date()): IntradaySnapshot {
  const timezone = process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  return withReadOnlyDatabase((database) => buildIntradaySnapshot(database, businessDate, now, timezone));
}
