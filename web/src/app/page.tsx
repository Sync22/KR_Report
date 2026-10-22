import { redirect } from "next/navigation";
import { isArchiveSnapshot } from "@/domain/archive";
import { getArchiveSnapshot } from "@/server/archive";
import DailyPageShell from "@/components/server/daily-page-shell";
import DailyTabPage from "@/components/server/daily-tab-page";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export default function HomePage() {
  let payload: unknown;
  try { payload = getArchiveSnapshot(1); } catch { redirect("/archive"); }
  if (!isArchiveSnapshot(payload) || !payload.latest_business_date) redirect("/archive");
  const date = payload.latest_business_date;
  return <DailyPageShell businessDate={date}><DailyTabPage params={Promise.resolve({ date })} searchParams={Promise.resolve({})} /></DailyPageShell>;
}
