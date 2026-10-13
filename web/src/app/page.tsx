import { redirect } from "next/navigation";
import { isArchiveSnapshot } from "@/domain/archive";
import { getArchiveSnapshot } from "@/server/archive";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export default function HomePage() {
  let payload: unknown;
  try { payload = getArchiveSnapshot(100); } catch { redirect("/archive"); }
  if (!isArchiveSnapshot(payload) || !payload.latest_business_date) redirect("/archive");
  redirect(`/daily/${payload.latest_business_date}/main`);
}
