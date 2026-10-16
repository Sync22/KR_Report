export type ChartLabEventIdentity = {
  symbol: string;
  kind: string;
  basisStartTime: string;
  ruleVersion: string;
  status: string;
};
export type ChartLabEventRecord = Record<string, unknown> & { event_id: string };

export function chartLabEventId(identity: ChartLabEventIdentity): string {
  const values = [identity.symbol, identity.kind, identity.basisStartTime, identity.ruleVersion, identity.status];
  if (values.some((value) => typeof value !== "string" || !value.trim() || value.length > 120)) throw new TypeError("invalid-chart-lab-event-key");
  return values.join(":");
}

export function appendChartLabEvents(
  previous: ReadonlyArray<Record<string, unknown>>,
  additions: ReadonlyArray<ChartLabEventRecord>,
  limit = 500,
): Array<Record<string, unknown>> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 500) throw new TypeError("invalid-chart-lab-event-limit");
  const events = [...previous];
  const knownIds = new Set(events.map((event) => event.event_id).filter((id): id is string => typeof id === "string"));
  for (const event of additions) {
    if (typeof event.event_id !== "string" || !event.event_id || knownIds.has(event.event_id)) continue;
    events.push(event);
    knownIds.add(event.event_id);
  }
  return events.slice(-limit);
}
