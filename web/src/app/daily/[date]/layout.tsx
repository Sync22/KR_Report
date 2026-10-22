import DailyPageShell from "@/components/server/daily-page-shell";

export default async function DailyLayout({
  children,
  params,
}: Readonly<{ children: React.ReactNode; params: Promise<{ date: string }> }>) {
  const { date } = await params;
  return <DailyPageShell businessDate={date}>{children}</DailyPageShell>;
}
