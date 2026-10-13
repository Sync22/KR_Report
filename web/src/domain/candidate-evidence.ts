import { isBusinessDate } from "./daily.ts";

export type CandidateEvidenceRow = {
  business_date: string;
  stock_code: string;
  stock_name: string;
  observation_priority: string;
  why_notable: string[];
  missing_information: string[];
  evidence_layers: { primary: string[]; support: string[]; gap: string[] };
  report_summary: {
    report_count: number;
    target_price_min: number | null;
    target_price_max: number | null;
  };
  news_observation_badge: {
    available: boolean;
    display_label: string;
    reason: string;
    connection_label?: string;
    connection_reason?: string;
    direct_count?: number;
    caution_count?: number;
    market_context_count?: number;
    krx_reference_status?: string;
    top_title?: string | null;
  };
  research_focus?: {
    available: boolean;
    items: { topic: string; source_title: string; source_kind: string; basis: string; query: string; search_url: string; source_url?: string }[];
    notice: string;
  };
  target_price_revision?: {
    available: boolean;
    current_min: number | null;
    current_max: number | null;
    previous_date: string | null;
    previous_min: number | null;
    previous_max: number | null;
    previous_report_count?: number;
    direction: "up" | "down" | "flat" | null;
    direction_label: string | null;
  };
  selected: boolean;
};

export type CandidateEvidenceSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  available: boolean;
  data_scope: "stored_report_toss_evidence";
  live_fetch: false;
  scoring: false;
  recommendation: false;
  selection_basis: "regular_session_news_cohort" | "stored_candidate_evidence";
  display_policy: string;
  notice: string;
  rows: CandidateEvidenceRow[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item: unknown) => typeof item === "string");
}

function isNumberOrNull(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isSafeResearchUrl(value: unknown, kind: "search" | "report"): value is string {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return false;
    return kind === "search"
      ? url.hostname === "search.naver.com" && url.pathname === "/search.naver"
      : ["stock.naver.com", "finance.naver.com"].includes(url.hostname);
  } catch {
    return false;
  }
}

function isResearchFocus(value: unknown): value is NonNullable<CandidateEvidenceRow["research_focus"]> {
  return isRecord(value) && typeof value.available === "boolean" && typeof value.notice === "string" &&
    Array.isArray(value.items) && value.items.length <= 3 && value.items.every((item: unknown) =>
      isRecord(item) && typeof item.topic === "string" && typeof item.source_title === "string" &&
      typeof item.source_kind === "string" && typeof item.basis === "string" && typeof item.query === "string" &&
      isSafeResearchUrl(item.search_url, "search") &&
      (item.source_url === undefined || isSafeResearchUrl(item.source_url, "report")));
}

function isTargetPriceRevision(value: unknown): value is NonNullable<CandidateEvidenceRow["target_price_revision"]> {
  return isRecord(value) && typeof value.available === "boolean" &&
    isNumberOrNull(value.current_min) && isNumberOrNull(value.current_max) &&
    (value.previous_date === null || (typeof value.previous_date === "string" && isBusinessDate(value.previous_date))) &&
    isNumberOrNull(value.previous_min) && isNumberOrNull(value.previous_max) &&
    (value.previous_report_count === undefined || (Number.isInteger(value.previous_report_count) && Number(value.previous_report_count) >= 0)) &&
    (["up", "down", "flat", null] as unknown[]).includes(value.direction) &&
    (value.direction_label === null || typeof value.direction_label === "string");
}

function isCandidateEvidenceRow(value: unknown, expectedDate: string): value is CandidateEvidenceRow {
  if (!isRecord(value) || !/^[0-9]{6}$/.test(String(value.stock_code ?? ""))) return false;
  const evidence = value.evidence_layers;
  const report = value.report_summary;
  const news = value.news_observation_badge;
  const forbiddenKeys = [
    "_sort_value_signal",
    "_sort_tuple",
    "sort_tuple",
    "internal_candidate_signals",
    "internal_missing_information",
    "quality_flags",
    "evidence_notes",
    "opinion_summary",
    "rank_reference",
  ];
  return (
    value.business_date === expectedDate &&
    typeof value.stock_name === "string" &&
    typeof value.observation_priority === "string" &&
    isStringArray(value.why_notable) &&
    isStringArray(value.missing_information) &&
    isRecord(evidence) &&
    isStringArray(evidence.primary) &&
    isStringArray(evidence.support) &&
    isStringArray(evidence.gap) &&
    isRecord(report) &&
    typeof report.report_count === "number" &&
    Number.isInteger(report.report_count) &&
    isNumberOrNull(report.target_price_min) &&
    isNumberOrNull(report.target_price_max) &&
    isRecord(news) &&
    typeof news.available === "boolean" &&
    typeof news.display_label === "string" &&
    typeof news.reason === "string" &&
    (news.connection_label === undefined || typeof news.connection_label === "string") &&
    (news.connection_reason === undefined || typeof news.connection_reason === "string") &&
    ["direct_count", "caution_count", "market_context_count"].every((key) =>
      news[key] === undefined || (Number.isInteger(news[key]) && Number(news[key]) >= 0)
    ) &&
    (news.krx_reference_status === undefined || typeof news.krx_reference_status === "string") &&
    (news.top_title === undefined || news.top_title === null || typeof news.top_title === "string") &&
    (value.research_focus === undefined || isResearchFocus(value.research_focus)) &&
    (value.target_price_revision === undefined || isTargetPriceRevision(value.target_price_revision)) &&
    typeof value.selected === "boolean" &&
    !forbiddenKeys.some((key) => key in value)
  );
}

export function isCandidateEvidenceSnapshot(
  value: unknown,
  expectedDate: string,
): value is CandidateEvidenceSnapshot {
  if (!isRecord(value) || !Array.isArray(value.rows)) return false;
  const selectedCount = value.rows.filter((row: unknown) => isRecord(row) && row.selected === true).length;
  return (
    typeof value.now === "string" &&
    Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" &&
    value.timezone.length > 0 &&
    value.surface === "web-view" &&
    value.read_only === true &&
    value.business_date === expectedDate &&
    isBusinessDate(value.business_date) &&
    typeof value.available === "boolean" &&
    value.data_scope === "stored_report_toss_evidence" &&
    value.live_fetch === false &&
    value.scoring === false &&
    value.recommendation === false &&
    (value.selection_basis === "regular_session_news_cohort" || value.selection_basis === "stored_candidate_evidence") &&
    typeof value.display_policy === "string" &&
    typeof value.notice === "string" &&
    selectedCount <= 2 &&
    value.rows.every((row: unknown) => isCandidateEvidenceRow(row, expectedDate))
  );
}
