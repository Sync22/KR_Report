# Web-View Evidence Composition Implementation Plan

## Task 1: Lock contracts with tests

**Files:** `tests/test_web_view.py`, `tests/test_cli_commands.py`

1. Change the news-collection route expectation to `405` with no collector call.
2. Add narrow HTML contract checks for Top2 quote-gap coherence, target-range rendering, request dedupe state, and removal of automatic news collection.
3. Add or update the browser-smoke timing test if an existing seam is available.
4. Run the focused tests and confirm the old implementation fails.

## Task 2: Apply the minimum implementation

**Files:** `src/stock_monitor/cli.py`, `src/stock_monitor/cli_web_view_checks.py`

1. Remove the web-view news write route, button, automatic collection JavaScript, and route capability declaration while preserving scheduler/CLI collection helpers.
2. Cache the same-date/same-Top2 Toss result in page state; keep explicit refresh as the only forced reload.
3. Fix Top2 missing-evidence and target-range text, show the real third reason, and remove the stock-detail news-prefix duplication.
4. Replace the mobile smoke race with a selector wait.
5. Delete only uncalled JavaScript/CSS associated with DOM cards that no longer exist.

## Task 3: Update canonical documentation

**Files:** `docs/codex/surface-guide.md`, `docs/codex/news-intelligence.md`, `docs/codex/operating-guide.md`

1. Add one canonical evidence-composition purpose section to `surface-guide.md`.
2. Remove the historical web-view POST exception and point collection to scheduler/CLI.
3. Keep other documents short and link back to the canonical surface purpose.

## Task 4: Verify the real product

1. Run focused pytest suites and `git diff --check`.
2. Run `web-view-value-qa` and `web-view-browser-smoke`.
3. Start a temporary loopback gate-disabled server without changing production configuration.
4. Inspect desktop and mobile `/`, all tabs, Watch-to-Stock navigation, Top2 live quote text, request counts, and public-safe route methods.
5. Stop the temporary server and report only confirmed results and residual risks.
