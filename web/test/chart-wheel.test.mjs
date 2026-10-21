import assert from "node:assert/strict";
import test from "node:test";

import { addNonPassiveChartWheelListener } from "../src/components/client/chart-wheel.ts";

function wheel(deltaY) {
  const event = new Event("wheel", { cancelable: true });
  Object.defineProperty(event, "deltaY", { value: deltaY });
  return event;
}

test("chart wheel consumes vertical page scroll and unregisters cleanly", () => {
  const target = new EventTarget();
  const observed = [];
  const remove = addNonPassiveChartWheelListener(target, (event) => observed.push(event.deltaY));
  const down = wheel(120);
  const horizontal = wheel(0);

  target.dispatchEvent(down);
  target.dispatchEvent(horizontal);
  remove();
  const afterRemoval = wheel(-120);
  target.dispatchEvent(afterRemoval);

  assert.equal(down.defaultPrevented, true);
  assert.equal(horizontal.defaultPrevented, false);
  assert.equal(afterRemoval.defaultPrevented, false);
  assert.deepEqual(observed, [120]);
});
