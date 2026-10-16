import type { ChartExplorerBar, ChartExplorerTimeframe } from "../chart-explorer.ts";
import { detectChartLabPatterns, type ChartLabPattern } from "./patterns.ts";
import { calculateChartLabIndicators, type ChartLabIndicatorPoint } from "./indicators.ts";
import { evaluateChartLabEntry, type ChartLabEntryResult, type ChartLabStrategy } from "./entry.ts";
import { evaluateChartLabLowEntry, type ChartLabLowEntryResult } from "./low-structure.ts";

export type ChartLabAnalysisOptions = {
  symbol: string;
  timeframe: ChartExplorerTimeframe;
  asOfIndex: number;
  selected?: ReadonlyArray<ChartLabStrategy>;
  mode?: "all" | "any";
  maxAtr?: number;
};

export type ChartLabAnalysis = {
  version: "chart-lab-analysis-v1";
  symbol: string;
  timeframe: ChartExplorerTimeframe;
  basis: string;
  barCount: number;
  historical: boolean;
  indicators: ChartLabIndicatorPoint[];
  entry: ChartLabEntryResult;
  lowEntry: ChartLabLowEntryResult;
  patterns: ChartLabPattern[];
};

export function buildChartLabAnalysis(bars: ReadonlyArray<ChartExplorerBar>, options: ChartLabAnalysisOptions): ChartLabAnalysis {
  const { symbol, timeframe, asOfIndex } = options;
  if (!Number.isInteger(asOfIndex) || asOfIndex < 0 || asOfIndex >= bars.length) throw new RangeError("invalid-chart-lab-as-of-index");
  const basisBars = bars.slice(0, asOfIndex + 1);
  const basisIndex = basisBars.length - 1;
  return {
    version: "chart-lab-analysis-v1",
    symbol,
    timeframe,
    basis: basisBars[basisIndex].time,
    barCount: basisBars.length,
    historical: asOfIndex < bars.length - 1,
    indicators: calculateChartLabIndicators(basisBars),
    entry: evaluateChartLabEntry(basisBars, {
      timeframe,
      asOfIndex: basisIndex,
      confirmedThroughIndex: null,
      judgmentReady: true,
      historical: asOfIndex < bars.length - 1,
      selected: options.selected,
      mode: options.mode,
      maxAtr: options.maxAtr,
    }),
    lowEntry: evaluateChartLabLowEntry(basisBars, {
      symbol,
      timeframe,
      asOfIndex: basisIndex,
      confirmedThroughIndex: null,
      judgmentReady: true,
      historical: asOfIndex < bars.length - 1,
    }),
    patterns: detectChartLabPatterns(basisBars, timeframe),
  };
}
