import PublicHeader from "@/components/client/public-header";
import { DailyTabsProvider } from "@/components/client/daily-tabs";
import { headers } from "next/headers";
import { isChartLabLocalHost } from "@/server/chart-lab-local";

export default async function DailyLayout({
  children,
  params,
}: Readonly<{ children: React.ReactNode; params: Promise<{ date: string }> }>) {
  const { date } = await params;
  const requestHeaders = await headers();
  const chartLabEnabled = isChartLabLocalHost(requestHeaders.get("host"), requestHeaders.get("x-forwarded-host"));
  return <DailyTabsProvider businessDate={date} chartLabEnabled={chartLabEnabled}><PublicHeader businessDate={date} />{children}</DailyTabsProvider>;
}
