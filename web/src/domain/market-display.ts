export function formatMarketTurnover(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "자료 없음";
  const absolute = Math.floor(Math.abs(value));
  const sign = value < 0 ? "−" : "";
  const format = (number: number) => new Intl.NumberFormat("ko-KR").format(number);
  if (absolute < 10_000) return `${format(Math.trunc(value))}원`;

  const hundredMillions = Math.floor(absolute / 100_000_000);
  const tenThousands = Math.floor(absolute % 100_000_000 / 10_000);
  if (hundredMillions) return `${sign}${format(hundredMillions)}억${tenThousands ? ` ${format(tenThousands)}만` : ""}`;
  return `${sign}${format(tenThousands)}만`;
}

export function compactMarketDateTime(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$/.exec(value.trim());
  if (!match) return null;
  const [, date, time, offset] = match;
  const wallTime = new Date(`${date}T${time}:00Z`);
  if (!Number.isFinite(wallTime.getTime()) || wallTime.toISOString().slice(0, 16) !== `${date}T${time}`) return null;
  const parsed = new Date(offset ? value.trim().replace(" ", "T") : `${date}T${time}:00+09:00`);
  if (!Number.isFinite(parsed.getTime())) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(parsed);
  const fields = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${fields.month}.${fields.day} ${fields.hour}:${fields.minute}`;
}
