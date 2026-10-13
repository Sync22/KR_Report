import { isBusinessDate } from "./daily.ts";

export type IntradaySnapshot = {
  now: string;
  timezone: string;
  surface: "web-view";
  read_only: true;
  business_date: string;
  batches: { business_date: string; created_at: string; status_label: "발송됨" | "대기" | "확인필요"; report_count: number; stock_count: number }[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function isIntradaySnapshot(value: unknown, expectedDate: string): value is IntradaySnapshot {
  if (!isRecord(value) || !Array.isArray(value.batches)) return false;
  const keys = ["now", "timezone", "surface", "read_only", "business_date", "batches"];
  if (Object.keys(value).some((key) => !keys.includes(key))) return false;
  return (
    typeof value.now === "string" && Number.isFinite(Date.parse(value.now)) &&
    typeof value.timezone === "string" && value.timezone.length > 0 &&
    value.surface === "web-view" && value.read_only === true &&
    value.business_date === expectedDate && isBusinessDate(expectedDate) &&
    value.batches.every((item: unknown) => isRecord(item) &&
      Object.keys(item).every((key) => ["business_date", "created_at", "status_label", "report_count", "stock_count"].includes(key)) &&
      item.business_date === expectedDate && isBusinessDate(item.business_date) &&
      typeof item.created_at === "string" && Number.isFinite(Date.parse(item.created_at)) &&
      ["발송됨", "대기", "확인필요"].includes(String(item.status_label)) &&
      Number.isInteger(item.report_count) && (item.report_count as number) >= 0 &&
      Number.isInteger(item.stock_count) && (item.stock_count as number) >= 0
    )
  );
}
