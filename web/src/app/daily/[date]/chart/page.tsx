import DailyTabPage, { type DailyTabPageProps } from "@/components/server/daily-tab-page";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { isChartLabLocalHost } from "@/server/chart-lab-local";

export default async function ChartExplorerPage(props: DailyTabPageProps) {
  const requestHeaders = await headers();
  if (!isChartLabLocalHost(requestHeaders.get("host"), requestHeaders.get("x-forwarded-host"))) notFound();
  return <DailyTabPage {...props} />;
}
