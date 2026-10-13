import assert from "node:assert/strict";
import test from "node:test";

import { dailyTabFromPathname, dailyTabHref, isDailyTabPage } from "../src/components/client/daily-tab-state.ts";

test("daily tab state follows the legacy route aliases", () => {
  assert.equal(dailyTabFromPathname("/daily/2026-10-08/main"), "main");
  assert.equal(dailyTabFromPathname("/daily/2026-10-08/candidates"), "watch");
  assert.equal(dailyTabFromPathname("/daily/2026-10-08/stocks"), "stock");
  assert.equal(dailyTabFromPathname("/daily/2026-10-08/stocks/005930"), "stock");
  assert.equal(dailyTabFromPathname("/daily/2026-10-08/intraday"), null);
  assert.equal(isDailyTabPage("/daily/2026-10-08/main"), true);
  assert.equal(isDailyTabPage("/daily/2026-10-08/candidates"), true);
  assert.equal(isDailyTabPage("/daily/2026-10-08/stocks"), true);
  assert.equal(isDailyTabPage("/daily/2026-10-08/stocks/005930"), false);
});

test("tab changes keep one selected six-digit stock and drop unrelated search state", () => {
  assert.equal(
    dailyTabHref("2026-10-08", "watch", "?stock=005930&q=Samsung&include_single=1&limit=12", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/candidates?stock=005930&include_single=1&limit=12",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "stock", "", "/daily/2026-10-08/stocks/005930"),
    "/daily/2026-10-08/stocks?stock=005930",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "main", "", "/daily/2026-10-08/stocks/005930"),
    "/daily/2026-10-08/main?stock=005930",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "watch", "", "/daily/2026-10-08/stocks/005930"),
    "/daily/2026-10-08/candidates?stock=005930",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "main", "?stock=invalid", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/main",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "main", "?stock=005930&stock=000660", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/main",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "watch", "?stock=005930&include_single=1&include_single=1&limit=12&limit=18", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/candidates?stock=005930",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "watch", "?stock=005930&include_single=1&limit=999", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/candidates?stock=005930&include_single=1&limit=100",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "watch", "?stock=005930&limit=invalid", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/candidates?stock=005930",
  );
  assert.equal(
    dailyTabHref("2026-10-08", "stock", "?q=005930", "/daily/2026-10-08/stocks"),
    "/daily/2026-10-08/stocks?q=005930",
  );
});
