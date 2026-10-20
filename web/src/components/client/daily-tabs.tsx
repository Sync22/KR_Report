"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { dailyTabFromPathname, dailyTabHref, isDailyTabPage, type DailyTab } from "@/components/client/daily-tab-state";

type DailyTabsContextValue = Readonly<{
  activeTab: DailyTab | null;
  canSwitchTabs: boolean;
  chartLabEnabled: boolean;
  selectTab: (tab: DailyTab) => void;
}>;

const DailyTabsContext = createContext<DailyTabsContextValue | null>(null);

export function DailyTabsProvider({ businessDate, chartLabEnabled, children }: Readonly<{ businessDate: string; chartLabEnabled: boolean; children: ReactNode }>) {
  const pathname = usePathname();
  const routeTab = dailyTabFromPathname(pathname);
  const [activeTab, setActiveTab] = useState(routeTab);
  const canSwitchTabs = isDailyTabPage(pathname);

  useEffect(() => setActiveTab(routeTab), [routeTab]);

  function selectTab(tab: DailyTab) {
    if (!canSwitchTabs || tab === activeTab || (tab === "chart" && !chartLabEnabled)) return;
    const href = dailyTabHref(businessDate, tab, window.location.search, window.location.pathname);
    if (href !== `${window.location.pathname}${window.location.search}`) window.history.pushState(null, "", href);
    setActiveTab(tab);
  }

  return <DailyTabsContext.Provider value={{ activeTab, canSwitchTabs, chartLabEnabled, selectTab }}>{children}</DailyTabsContext.Provider>;
}

export function useDailyTabs(): DailyTabsContextValue {
  const context = useContext(DailyTabsContext);
  if (!context) throw new Error("Daily tabs must be used inside DailyTabsProvider");
  return context;
}

export function DailyTabPanels({ main, watch, stock, chart }: Readonly<{ main: ReactNode; watch: ReactNode; stock: ReactNode; chart: ReactNode | null }>) {
  const { activeTab } = useDailyTabs();
  return <div className="daily-tab-panels">
    <div id="daily-main-panel" role="tabpanel" aria-labelledby="daily-main-tab" hidden={activeTab !== "main"}>{main}</div>
    <div id="daily-watch-panel" role="tabpanel" aria-labelledby="daily-watch-tab" hidden={activeTab !== "watch"}>{watch}</div>
    <div id="daily-stock-panel" role="tabpanel" aria-labelledby="daily-stock-tab" hidden={activeTab !== "stock"}>{stock}</div>
    {chart !== null ? <div id="daily-chart-panel" role="tabpanel" aria-labelledby="daily-chart-tab" hidden={activeTab !== "chart"}>{chart}</div> : null}
  </div>;
}
