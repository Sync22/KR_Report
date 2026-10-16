import assert from "node:assert/strict";
import test from "node:test";

import { appendChartLabEvents, chartLabEventId } from "../src/domain/chart-lab/events.ts";

const key = (status) => ({
  symbol: "005930", kind: "ascending-triangle", basisStartTime: "2026-09-01", ruleVersion: "triangle-d-v2", status,
});

test("Chart Lab event history appends pattern state transitions without replacing prior snapshots", () => {
  const forming = { event_id: chartLabEventId(key("forming")), status: "forming", snapshot: { close: 100 } };
  const breakout = { event_id: chartLabEventId(key("observed-breakout")), status: "observed-breakout", snapshot: { close: 112 } };
  const first = appendChartLabEvents([], [forming]);
  const second = appendChartLabEvents(first, [forming, breakout]);
  assert.deepEqual(first, [forming]);
  assert.deepEqual(second, [forming, breakout]);
  assert.notEqual(forming.event_id, breakout.event_id);
});

test("Chart Lab event history deduplicates existing IDs and retains only its bounded tail", () => {
  const existing = Array.from({ length: 3 }, (_, index) => ({ event_id: `event-${index}`, index }));
  assert.deepEqual(appendChartLabEvents(existing, [existing[1]], 3), existing);
  const next = { event_id: "event-3", index: 3 };
  assert.deepEqual(appendChartLabEvents(existing, [next], 3), [existing[1], existing[2], next]);
});

test("Chart Lab event IDs reject missing identity fields", () => {
  assert.throws(() => chartLabEventId({ ...key("forming"), symbol: "" }), /invalid-chart-lab-event-key/);
});
