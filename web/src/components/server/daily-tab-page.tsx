import "server-only";

import { notFound } from "next/navigation";

import { DailyTabPanels } from "@/components/client/daily-tabs";
import MainPanel from "@/components/server/daily-main-panel";
import CandidatePanel from "@/components/server/daily-candidates-panel";
import StockPanel from "@/components/server/daily-stocks-panel";
import ChartExplorerPanel from "@/components/server/chart-explorer-panel";
import { isBusinessDate } from "@/domain/daily";
import { isChartExplorerTimeframe } from "@/domain/chart-explorer";
import { getDailyTabWorkspace, type DailyTabWorkspace } from "@/server/daily-tab-workspace";
import { headers } from "next/headers";
import { isChartLabLocalHost } from "@/server/chart-lab-local";

export type DailyTabPageProps = Readonly<{
  params: Promise<{ date: string }>;
  searchParams: Promise<{
    stock?: string | string[];
    q?: string | string[];
    include_single?: string | string[];
    limit?: string | string[];
    symbol?: string | string[];
    timeframe?: string | string[];
  }>;
}>;

export default async function DailyTabPage({ params, searchParams }: DailyTabPageProps) {
  const [{ date }, query] = await Promise.all([params, searchParams]);
  if (!isBusinessDate(date)) notFound();
  const requestHeaders = await headers();
  const chartLabEnabled = isChartLabLocalHost(requestHeaders.get("host"), requestHeaders.get("x-forwarded-host"));
  const selectedStockCode = typeof query.stock === "string" ? query.stock : null;
  let workspace: DailyTabWorkspace;
  try {
    workspace = getDailyTabWorkspace(date, selectedStockCode);
  } catch {
    workspace = { daily: null, candidates: null, stocks: null, selectedStockDetail: null };
  }
  const panelParams = Promise.resolve({ date });
  const panelQuery = Promise.resolve(query);
  const chartSymbol = typeof query.symbol === "string" ? query.symbol : Array.isArray(query.symbol) ? query.symbol[0] ?? "" : "";
  const initialSymbol = chartSymbol || selectedStockCode || workspace.candidates?.rows[0]?.stock_code || "";
  const chartTimeframe = isChartExplorerTimeframe(query.timeframe) ? query.timeframe : "1d";

  return <DailyTabPanels
    main={<MainPanel params={panelParams} workspace={workspace} />}
    watch={<CandidatePanel params={panelParams} searchParams={panelQuery} workspace={workspace} />}
    stock={<StockPanel params={panelParams} searchParams={panelQuery} workspace={workspace} />}
    chart={chartLabEnabled ? <ChartExplorerPanel businessDate={date} initialSymbol={initialSymbol} initialTimeframe={chartTimeframe} /> : null}
  />;
}
