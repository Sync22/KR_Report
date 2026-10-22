import "server-only";

import PublicHeader from "@/components/client/public-header";
import { DailyTabsProvider } from "@/components/client/daily-tabs";
import { headers } from "next/headers";
import { isChartLabLocalHost } from "@/server/chart-lab-local";

export default async function DailyPageShell({ businessDate, children }: Readonly<{ businessDate: string; children: React.ReactNode }>) {
  const requestHeaders = await headers();
  const chartLabEnabled = isChartLabLocalHost(requestHeaders.get("host"), requestHeaders.get("x-forwarded-host"));
  return <DailyTabsProvider businessDate={businessDate} chartLabEnabled={chartLabEnabled}><PublicHeader businessDate={businessDate} />{children}</DailyTabsProvider>;
}
