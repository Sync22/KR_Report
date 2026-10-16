import type { ChartExplorerBar } from "../chart-explorer.ts";

// Adapted from https://github.com/gmparkingplace/Stock-Newbby (Apache-2.0):
// scripts/signals.py, scripts/indicators.py and results/dashboard/technical-indicators.js.
export const CHART_LAB_INDICATOR_VERSION = "technical-v3";

export type ChartLabIndicatorPoint = {
  time: string;
  sma20: number | null;
  sma60: number | null;
  sma120: number | null;
  sma200: number | null;
  ema20: number | null;
  ema60: number | null;
  ema120: number | null;
  ema200: number | null;
  wma20: number | null;
  wma60: number | null;
  wma120: number | null;
  wma200: number | null;
  bollinger20: { middle: number; upper: number; lower: number } | null;
  donchian20: { upper: number; middle: number; lower: number } | null;
  rsi14: number | null;
  atr14: number | null;
  donchianHigh20: number | null;
  donchianLow10: number | null;
  volumeRatio20: number | null;
};

const known = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function rollingMean(values: readonly (number | null)[], period: number): Array<number | null> {
  return values.map((_, index) => {
    const start = index - period + 1;
    if (start < 0) return null;
    let mean = 0;
    for (let cursor = start; cursor <= index; cursor += 1) {
      const value = values[cursor];
      if (!known(value)) return null;
      mean += value;
    }
    mean /= period;
    return Number.isFinite(mean) ? mean : null;
  });
}

function exponentialMean(values: readonly (number | null)[], period: number): Array<number | null> {
  const result: Array<number | null> = values.map(() => null);
  const alpha = 2 / (period + 1);
  let seed: number[] = [];
  let previous: number | null = null;
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (!known(value)) { seed = []; previous = null; continue; }
    if (previous === null) {
      seed.push(value);
      if (seed.length < period) continue;
      previous = seed.reduce((sum, next) => sum + next / period, 0);
      seed = [];
    } else previous += alpha * (value - previous);
    result[index] = Number.isFinite(previous) ? previous : null;
  }
  return result;
}

function weightedMean(values: readonly (number | null)[], period: number): Array<number | null> {
  const denominator = period * (period + 1) / 2;
  return values.map((_, index) => {
    const start = index - period + 1;
    if (start < 0) return null;
    let value = 0;
    for (let cursor = start; cursor <= index; cursor += 1) {
      if (!known(values[cursor])) return null;
      value += values[cursor]! * ((cursor - start + 1) / denominator);
    }
    return Number.isFinite(value) ? value : null;
  });
}

function bollinger(values: readonly (number | null)[], period: number, multiplier: number): Array<ChartLabIndicatorPoint["bollinger20"]> {
  return values.map((_, index) => {
    const start = index - period + 1;
    if (start < 0) return null;
    const window = values.slice(start, index + 1);
    if (!window.every(known)) return null;
    const middle = window.reduce((sum, value) => sum + value / period, 0);
    const deviation = Math.sqrt(window.reduce((sum, value) => sum + (value - middle) ** 2 / period, 0));
    return [middle, middle + multiplier * deviation, middle - multiplier * deviation].every(Number.isFinite)
      ? { middle, upper: middle + multiplier * deviation, lower: middle - multiplier * deviation }
      : null;
  });
}

function currentDonchian(bars: readonly ChartExplorerBar[], index: number, period: number): ChartLabIndicatorPoint["donchian20"] {
  const start = index - period + 1;
  if (start < 0) return null;
  const window = bars.slice(start, index + 1);
  if (!window.every((bar) => known(bar.high) && known(bar.low) && bar.high >= bar.low)) return null;
  const upper = Math.max(...window.map((bar) => bar.high));
  const lower = Math.min(...window.map((bar) => bar.low));
  return { upper, middle: upper / 2 + lower / 2, lower };
}

function wilderRsi(values: readonly (number | null)[], period: number): Array<number | null> {
  const result: Array<number | null> = values.map(() => null);
  let seedGain = 0;
  let seedLoss = 0;
  let seeded = 0;
  let averageGain: number | null = null;
  let averageLoss: number | null = null;

  for (let index = 1; index < values.length; index += 1) {
    const current = values[index];
    const previous = values[index - 1];
    if (!known(current) || !known(previous)) {
      seedGain = 0;
      seedLoss = 0;
      seeded = 0;
      averageGain = null;
      averageLoss = null;
      continue;
    }
    const delta = current - previous;
    const gain = Math.max(0, delta);
    const loss = Math.max(0, -delta);
    if (averageGain === null || averageLoss === null) {
      seedGain += gain;
      seedLoss += loss;
      seeded += 1;
      if (seeded === period) {
        averageGain = seedGain / period;
        averageLoss = seedLoss / period;
      }
    } else {
      averageGain = (averageGain * (period - 1) + gain) / period;
      averageLoss = (averageLoss * (period - 1) + loss) / period;
    }
    if (averageGain !== null && averageLoss !== null) {
      result[index] = averageLoss === 0 ? 100 : 100 - 100 / (1 + averageGain / averageLoss);
    }
  }
  return result;
}

function wilderAtr(bars: readonly ChartExplorerBar[], period: number): Array<number | null> {
  const result: Array<number | null> = bars.map(() => null);
  let seed: number[] = [];
  let previousClose: number | null = null;
  let average: number | null = null;
  for (let index = 0; index < bars.length; index += 1) {
    const bar = bars[index];
    if (![bar.high, bar.low, bar.close].every(known) || bar.high < bar.low) {
      seed = [];
      previousClose = null;
      average = null;
      continue;
    }
    const trueRange = previousClose === null
      ? bar.high - bar.low
      : Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
    previousClose = bar.close;
    if (average === null) {
      seed.push(trueRange);
      if (seed.length === period) {
        average = seed.reduce((value, next) => value + next, 0) / period;
        seed = [];
      }
    } else {
      average += (trueRange - average) / period;
    }
    if (average !== null && Number.isFinite(average)) result[index] = average;
  }
  return result;
}

function priorExtreme(bars: readonly ChartExplorerBar[], index: number, period: number, field: "high" | "low"): number | null {
  const start = index - period;
  if (start < 0) return null;
  const values = bars.slice(start, index).map((bar) => bar[field]);
  if (!values.every(known)) return null;
  return field === "high" ? Math.max(...values) : Math.min(...values);
}

export function calculateChartLabIndicators(bars: ReadonlyArray<ChartExplorerBar>): ChartLabIndicatorPoint[] {
  const closes = bars.map((bar) => known(bar.close) ? bar.close : null);
  const volumes = bars.map((bar) => known(bar.volume) && bar.volume >= 0 ? bar.volume : null);
  const volumeMeans = rollingMean(volumes, 20);
  const sma20 = rollingMean(closes, 20);
  const sma60 = rollingMean(closes, 60);
  const sma120 = rollingMean(closes, 120);
  const sma200 = rollingMean(closes, 200);
  const ema20 = exponentialMean(closes, 20);
  const ema60 = exponentialMean(closes, 60);
  const ema120 = exponentialMean(closes, 120);
  const ema200 = exponentialMean(closes, 200);
  const wma20 = weightedMean(closes, 20);
  const wma60 = weightedMean(closes, 60);
  const wma120 = weightedMean(closes, 120);
  const wma200 = weightedMean(closes, 200);
  const bollinger20 = bollinger(closes, 20, 2);
  const rsi14 = wilderRsi(closes, 14);
  const atr14 = wilderAtr(bars, 14);
  return bars.map((bar, index) => ({
    time: bar.time,
    sma20: sma20[index],
    sma60: sma60[index],
    sma120: sma120[index],
    sma200: sma200[index],
    ema20: ema20[index],
    ema60: ema60[index],
    ema120: ema120[index],
    ema200: ema200[index],
    wma20: wma20[index],
    wma60: wma60[index],
    wma120: wma120[index],
    wma200: wma200[index],
    bollinger20: bollinger20[index],
    donchian20: currentDonchian(bars, index, 20),
    rsi14: rsi14[index],
    atr14: atr14[index],
    donchianHigh20: priorExtreme(bars, index, 20, "high"),
    donchianLow10: priorExtreme(bars, index, 10, "low"),
    volumeRatio20: volumeMeans[index] !== null && volumeMeans[index]! > 0 && volumes[index] !== null
      ? volumes[index]! / volumeMeans[index]!
      : null,
  }));
}
