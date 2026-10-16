export type ChartRange = Readonly<{ start: number; end: number }>;

export function hasVisibleChartBar(bars: ReadonlyArray<Readonly<{ time: string }>>, time: unknown): boolean {
  return typeof time === "string" && bars.some((bar) => bar.time === time);
}

function boundedInteger(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, Math.round(value)));
}

export function resolveChartRange(total: number, count: number, requested?: ChartRange | null): ChartRange {
  const available = Number.isSafeInteger(total) ? Math.max(0, total) : 0;
  if (!available) return { start: 0, end: 0 };
  if (requested && Number.isSafeInteger(requested.start) && Number.isSafeInteger(requested.end) && requested.end > requested.start) {
    const size = Math.min(380, available, requested.end - requested.start);
    const start = boundedInteger(requested.start, 0, available - size);
    return { start, end: start + size };
  }
  const size = Math.min(380, available, Number.isSafeInteger(count) ? Math.max(1, count) : 200);
  return { start: available - size, end: available };
}

export function zoomChartRange(range: ChartRange, total: number, direction: "in" | "out", anchorRatio = 0.5): ChartRange {
  const current = resolveChartRange(total, range.end - range.start, range);
  const size = current.end - current.start;
  if (!size) return current;
  const targetSize = boundedInteger(size * (direction === "in" ? 0.8 : 1.25), Math.min(10, total), Math.min(380, total));
  if (targetSize === size) return current;
  const anchor = Math.max(0, Math.min(1, anchorRatio));
  const anchorIndex = current.start + anchor * (size - 1);
  const start = boundedInteger(anchorIndex - anchor * (targetSize - 1), 0, total - targetSize);
  return { start, end: start + targetSize };
}

export function panChartRange(range: ChartRange, total: number, deltaBars: number): ChartRange {
  const current = resolveChartRange(total, range.end - range.start, range);
  const size = current.end - current.start;
  if (!size || !Number.isFinite(deltaBars)) return current;
  const start = boundedInteger(current.start + deltaBars, 0, total - size);
  return { start, end: start + size };
}
