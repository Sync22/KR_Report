import { parseDailyStockLimit } from "../../domain/daily.ts";

export type DailyTab = "main" | "watch" | "stock" | "chart";

const tabRoutes: Record<DailyTab, string> = {
  main: "main",
  watch: "candidates",
  stock: "stocks",
  chart: "chart",
};

export function dailyTabFromPathname(pathname: string): DailyTab | null {
  if (pathname === "/") return "main";
  if (pathname.endsWith("/main")) return "main";
  if (pathname.endsWith("/candidates")) return "watch";
  if (pathname.endsWith("/chart")) return "chart";
  if (pathname.includes("/stocks")) return "stock";
  return null;
}

export function isDailyTabPage(pathname: string): boolean {
  return pathname === "/" || /^\/daily\/\d{4}-\d{2}-\d{2}\/(?:main|candidates|stocks|chart)$/.test(pathname);
}

export function dailyTabHref(date: string, tab: DailyTab, search: string, pathname: string): string {
  if (isDailyTabPage(pathname) && dailyTabFromPathname(pathname) === tab) return `${pathname}${search}`;
  const query = new URLSearchParams(search);
  const queryCodes = query.getAll("stock");
  const pathCode = pathname.match(/\/stocks\/(\d{6})$/)?.[1];
  const stockCode = queryCodes.length === 1 ? queryCodes[0] : pathCode;
  const selectedStock = stockCode && /^\d{6}$/.test(stockCode) ? stockCode : null;
  const params = new URLSearchParams();
  if (selectedStock) params.set("stock", selectedStock);
  const includeSingle = query.getAll("include_single");
  if (includeSingle.length === 1 && includeSingle[0] === "1") params.set("include_single", "1");
  const limits = query.getAll("limit");
  if (limits.length === 1 && /^\d+$/.test(limits[0].trim()) && Number.isSafeInteger(Number(limits[0]))) {
    params.set("limit", String(parseDailyStockLimit(limits[0])));
  }
  const suffix = params.size ? `?${params}` : "";
  return `/daily/${date}/${tabRoutes[tab]}${suffix}`;
}
