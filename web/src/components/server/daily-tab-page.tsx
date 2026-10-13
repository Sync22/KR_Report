import "server-only";

import { notFound } from "next/navigation";

import { DailyTabPanels } from "@/components/client/daily-tabs";
import MainPanel from "@/components/server/daily-main-panel";
import CandidatePanel from "@/components/server/daily-candidates-panel";
import StockPanel from "@/components/server/daily-stocks-panel";
import { isBusinessDate } from "@/domain/daily";
import { getDailyTabWorkspace, type DailyTabWorkspace } from "@/server/daily-tab-workspace";

export type DailyTabPageProps = Readonly<{
  params: Promise<{ date: string }>;
  searchParams: Promise<{
    stock?: string | string[];
    q?: string | string[];
    include_single?: string | string[];
    limit?: string | string[];
  }>;
}>;

export default async function DailyTabPage({ params, searchParams }: DailyTabPageProps) {
  const [{ date }, query] = await Promise.all([params, searchParams]);
  if (!isBusinessDate(date)) notFound();
  const selectedStockCode = typeof query.stock === "string" ? query.stock : null;
  let workspace: DailyTabWorkspace;
  try {
    workspace = getDailyTabWorkspace(date, selectedStockCode);
  } catch {
    workspace = { daily: null, candidates: null, stocks: null, flow: null, selectedStockDetail: null };
  }
  const panelParams = Promise.resolve({ date });
  const panelQuery = Promise.resolve(query);

  return <DailyTabPanels
    main={<MainPanel params={panelParams} workspace={workspace} />}
    watch={<CandidatePanel params={panelParams} searchParams={panelQuery} workspace={workspace} />}
    stock={<StockPanel params={panelParams} searchParams={panelQuery} workspace={workspace} />}
  />;
}
