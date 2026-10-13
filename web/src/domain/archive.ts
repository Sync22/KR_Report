import { isBusinessDate } from "./daily.ts";

export type ArchiveDate = {
  business_date: string;
  report_count: number;
  summary_stock_count: number;
  news_observation_count: number;
  category_mapping: ArchiveCategoryMapping;
};

export type ArchiveCategoryMapping = {
  mapping_basis: "dated_snapshot" | "latest_mapping_fallback";
  sector_snapshot_date: string | null;
  theme_snapshot_date: string | null;
  label: string;
};

export type ArchiveCategoryMappingSummary = {
  dated_snapshot_count: number;
  fallback_count: number;
  notice: string;
};

export type ArchiveSnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  date_count: number;
  latest_business_date: string | null;
  filter_hint: string;
  category_mapping_summary: ArchiveCategoryMappingSummary;
  dates: ArchiveDate[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object";
}

function isCount(value: unknown): value is number {
  return Number.isInteger(value) && (value as number) >= 0;
}

function isArchiveCategoryMapping(value: unknown, businessDate: string): value is ArchiveCategoryMapping {
  if (!isRecord(value)) return false;
  return (
    (value.mapping_basis === "dated_snapshot" || value.mapping_basis === "latest_mapping_fallback") &&
    (value.sector_snapshot_date === null ||
      (isBusinessDate(value.sector_snapshot_date) && value.sector_snapshot_date <= businessDate)) &&
    (value.theme_snapshot_date === null ||
      (isBusinessDate(value.theme_snapshot_date) && value.theme_snapshot_date <= businessDate)) &&
    (value.mapping_basis !== "dated_snapshot" ||
      (value.sector_snapshot_date !== null && value.theme_snapshot_date !== null)) &&
    typeof value.label === "string"
  );
}

export function isArchiveSnapshot(value: unknown): value is ArchiveSnapshot {
  if (!isRecord(value) || !Array.isArray(value.dates)) return false;
  const dates: unknown[] = value.dates;
  const categorySummary = value.category_mapping_summary;
  const datesValid = dates.every((row: unknown) => {
    if (!isRecord(row) || !isBusinessDate(row.business_date)) return false;
    return isCount(row.report_count) && isCount(row.summary_stock_count) &&
      isCount(row.news_observation_count) && isArchiveCategoryMapping(row.category_mapping, row.business_date);
  });
  const datesAreDescending = dates.every((row: unknown, index) => {
    if (!isRecord(row) || !isBusinessDate(row.business_date)) return false;
    if (index === 0) return true;
    const previous = dates[index - 1];
    return isRecord(previous) && typeof previous.business_date === "string" && row.business_date < previous.business_date;
  });
  return (
    typeof value.now === "string" &&
    Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" &&
    value.timezone.length > 0 &&
    value.surface === "web-view" &&
    value.read_only === true &&
    isCount(value.date_count) &&
    value.date_count <= 100 &&
    value.date_count === dates.length &&
    (value.latest_business_date === null ||
      (isBusinessDate(value.latest_business_date) && value.latest_business_date === (dates[0] as Record<string, unknown> | undefined)?.business_date)) &&
    (dates.length > 0 || value.latest_business_date === null) &&
    typeof value.filter_hint === "string" &&
    isRecord(categorySummary) &&
    isCount(categorySummary.dated_snapshot_count) &&
    isCount(categorySummary.fallback_count) &&
    categorySummary.dated_snapshot_count + categorySummary.fallback_count === value.date_count &&
    typeof categorySummary.notice === "string" &&
    datesValid &&
    datesAreDescending
  );
}
