import "server-only";

import type { DatabaseSync } from "node:sqlite";

import { isBusinessDate } from "../domain/daily.ts";
import type { CandidateEvidenceSnapshot } from "../domain/candidate-evidence.ts";
import { buildCandidateEvidenceSnapshotFromDatabase } from "./candidate-evidence.ts";
import { buildDailyBaseSnapshot } from "./daily-base.ts";
import {
  buildMarketCommentaryPracticeSnapshot,
  buildWebViewMarketBriefingContext,
} from "./daily-market-commentary.ts";
import { buildDailySourceFreshnessFromDatabase } from "./daily-freshness.ts";
import { buildNewsObservationSummaryFromDatabase } from "./daily-news-observation.ts";
import { buildDailyTossContextFromDatabase, getRecentDailyTossSnapshotDates } from "./daily-toss-context.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

type DailySnapshotOptions = {
  now?: Date;
  timezone?: string;
  tossOpenApiReady?: boolean;
  priorityCandidateEvidence?: CandidateEvidenceSnapshot;
};

function currentDateInTimezone(now: Date, timezone: string): string {
  const values = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now).map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function omitNoneValues(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(omitNoneValues);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== null).map(([key, item]) => [key, omitNoneValues(item)]));
  }
  return value;
}

export function buildDailySnapshotFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  options: DailySnapshotOptions = {},
): Record<string, unknown> {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily snapshot date");

  const now = options.now ?? new Date();
  const timezone = options.timezone?.trim() || process.env.STOCK_MONITOR_TIMEZONE?.trim() || "Asia/Seoul";
  const tossOpenApiReady = options.tossOpenApiReady ?? process.env.STOCK_MONITOR_TOSS_OPENAPI_READY === "true";
  const tossSnapshotDates = getRecentDailyTossSnapshotDates(database, businessDate);
  const tossMarketReferenceDate = tossSnapshotDates[0] ?? null;
  const base = buildDailyBaseSnapshot(database, businessDate);
  const priorityCandidateEvidence = options.priorityCandidateEvidence ?? buildCandidateEvidenceSnapshotFromDatabase(database, businessDate, 2, now);
  const priorityStockCodes = priorityCandidateEvidence.rows
    .filter((row) => row.selected)
    .slice(0, 2)
    .flatMap((row) => row.stock_code?.trim() ? [row.stock_code.trim()] : []);
  const newsObservationSummary = buildNewsObservationSummaryFromDatabase(database, businessDate, {
    stockCodes: priorityStockCodes,
  });
  const marketBriefing = {
    ...buildWebViewMarketBriefingContext(database, businessDate, base.stocks, tossMarketReferenceDate),
    news_observation_summary: newsObservationSummary,
  };
  const marketCommentary = buildMarketCommentaryPracticeSnapshot(database, businessDate, {
    summaries: base.stocks,
    marketBriefing,
    currentDate: currentDateInTimezone(now, timezone),
  });
  const sourceFreshnessSummary = buildDailySourceFreshnessFromDatabase(database, businessDate, {
    reportCount: base.report_count,
    candidateStockCodes: priorityStockCodes,
    tossOpenApiReady,
    tossMarketReferenceDate,
  });
  const toss = buildDailyTossContextFromDatabase(database, businessDate, tossSnapshotDates);

  const snapshot = {
    now: now.toISOString(),
    timezone,
    surface: "web-view",
    read_only: true,
    business_date: businessDate,
    public_contract: {
      read_only: true,
      source_scope: "저장 데이터 기준",
      missing_value_policy: "누락값은 계산에서 제외하고 상세에 '-'로 표시합니다.",
      recommendation: false,
      control_exposed: false,
    },
    report_count: base.report_count,
    summary_stock_count: base.summary_stock_count,
    mapping_notice: base.mapping_notice,
    category_contract: base.category_contract,
    market_reference_notice: "Toss 저장 스냅샷 기준입니다.",
    market_briefing: marketBriefing,
    market_commentary: marketCommentary,
    observation_summary: null,
    observation_summary_deferred: true,
    priority_candidate_evidence: priorityCandidateEvidence,
    news_observation_summary: newsObservationSummary,
    source_freshness_summary: sourceFreshnessSummary,
    toss_context: toss.toss_context,
    toss_recent_flow: toss.toss_recent_flow,
    toss_investor_flow: toss.toss_investor_flow,
    stocks: base.stocks,
    sectors: base.sectors,
    themes: base.themes,
    market_mood: base.market_mood,
    watch_candidates: base.watch_candidates,
  };
  return omitNoneValues(snapshot) as Record<string, unknown>;
}

export function getDailySnapshot(businessDate: string): Record<string, unknown> {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid daily snapshot date");
  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const snapshot = buildDailySnapshotFromDatabase(database, businessDate);
      database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
