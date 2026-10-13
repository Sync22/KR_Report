import PublicHeader from "@/components/client/public-header";
import { DailyTabsProvider } from "@/components/client/daily-tabs";

export default async function DailyLayout({
  children,
  params,
}: Readonly<{ children: React.ReactNode; params: Promise<{ date: string }> }>) {
  const { date } = await params;
  return <DailyTabsProvider businessDate={date}><PublicHeader businessDate={date} />{children}</DailyTabsProvider>;
}
