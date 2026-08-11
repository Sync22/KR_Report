# Hourly Telegram Market Context Implementation Plan

> **Execution:** Use subagent-driven development for the implementation steps,
> with a reviewer pass before the final verification.

**Goal:** Keep the existing 30-minute scheduled report collection and dedupe
path, but send one factual Telegram briefing at 08:30 and hourly from 09:30
through 15:30 KST. Later briefings include available Toss market context
without changing candidate ordering or creating a trading signal.

**Architecture:** The scheduled poll remains the only trigger. New reports
continue to create the existing intraday outbox batches. At a designated
delivery time, the poll combines pending batches for that business date into
one Telegram message and only marks every included batch sent after Telegram
accepts that message. Manual poll behavior and the existing
`mood`/`lunch`/`preclose` market-briefing scheduler remain unchanged.

**Tech Stack:** Python 3.10, SQLite repository/outbox, Telegram Bot API,
pytest, PowerShell Task Scheduler wrappers.

## Scope Decisions

- Scheduled delivery times: `08:30`, `09:30` ... `15:30` KST on Korean
  business days.
- `08:30` is report-first and must render when Toss data is unavailable.
- Pending batches for the current business date are merged at the next valid
  delivery time. A missed delivery therefore reports all still-pending items,
  rather than silently losing them or pretending the range was one hour.
- Batches created after the final `15:30` window remain stored and visible in
  intraday history. They are not silently delivered with the next business
  day's briefing.
- Later briefings may append existing bounded Toss Top20 overlap, current
  quote, and same-day provisional investor-volume context for server-derived
  Top2 candidates. Missing or failed Toss data remains an explicit neutral
  absence.
- No schema migration, new scheduler task, account/asset/order endpoint,
  public route, or web-view write/control behavior is introduced.

## Task 1: Align The Operating Contract (A)

**Files:**
- Modify: `docs/codex/operating-guide.md`
- Modify: `docs/codex/documentation-index.md` only if the canonical entry
  needs an explicit link to the new hourly-delivery design

1. Replace the ambiguous `StockMonitor-Poll` wording with separate collection
   and Telegram-delivery cadence.
2. Correct stale Toss `hold` statements only where they describe the current
   promoted, bounded read-only provider path; retain lab/hold language for
   unsupported endpoints and experiments.
3. Record the after-15:30 no-cross-day-delivery behavior and the fact that the
   existing three market-briefing slots are a separate lane.

**Verification:**
- Run `python -m stock_monitor docs-hygiene-audit --json`.

## Task 2: Align The Public-Surface Contract (B)

**Files:**
- Modify: `docs/codex/surface-guide.md`

1. Add the already implemented GET-only Toss quote and market-context routes
   to the API inventory with their bounded Top2/Top20 semantics.
2. Describe the public-safe scope precisely: stored report evidence remains
   primary; Toss values are dated source context, not scores, advice, or a
   source of candidate creation.
3. Keep the web-view contract independent from Telegram delivery scheduling;
   do not expose outbox, scheduler, token, or operator state.

**Verification:**
- Run `python -m stock_monitor docs-hygiene-audit --json`.
- Run the focused public-route tests identified in `tests/test_web_view.py`.

## Task 3: Specify Delivery Windows With Tests First (C1)

**Files:**
- Modify: `tests/test_intraday_empty_notification.py`
- Modify: `src/stock_monitor/cli.py`

1. Add focused tests for the scheduled delivery predicate: allow 08:30 and
   09:30 through 15:30, reject other scheduled poll times, and preserve the
   immediate manual-poll path.
2. Make `_run_manual_poll` distinguish a manual delivery from a scheduled
   collection run using its existing `scheduled_run_at` argument.
3. Suppress both immediate pending-batch processing and empty alerts on
   non-delivery scheduled polls; collection, insert, summary rebuild, and
   bounded news collection remain unchanged.

**Verification:**
- Run `python -m pytest tests/test_intraday_empty_notification.py -q`.

## Task 4: Merge Pending Batches Safely (C2)

**Files:**
- Modify: `src/stock_monitor/cli.py`
- Modify: `src/stock_monitor/db/repository.py`
- Modify: `tests/test_intraday_empty_notification.py`
- Modify: `tests/test_intraday_paging.py` only if active paging state needs
  an adjusted expectation

1. Add a repository operation that marks an explicit set of batch IDs sent in
   one SQLite transaction after one successful Telegram call. Keep existing
   single-batch methods for the manual/paging path.
2. In the scheduled path, load only pending batches for the current business
   date, combine and deduplicate their reports by identity key, and build one
   report section with the existing intraday formatter.
3. On a send failure, retain each included batch as failed/pending for the next
   valid same-day window. Do not mark any batch sent before Telegram returns a
   message ID.
4. Do not combine prior-business-date batches into a new day. Leave them
   visible for operator recovery rather than mislabeling them as current
   reports.

**Verification:**
- Run `python -m pytest tests/test_intraday_empty_notification.py tests/test_intraday_paging.py -q`.

## Task 5: Add Neutral Toss Context To Later Briefings (C3)

**Files:**
- Modify: `src/stock_monitor/cli.py`
- Modify: `tests/test_intraday_empty_notification.py`
- Modify: `tests/test_toss_openapi.py` only for an existing provider contract
  assertion that the new formatter relies on

1. Build the 08:30 message from the merged report section only, with a clear
   source/check-time boundary and no live Toss dependency.
2. For 09:30 through 15:30, reuse the established
   `_build_market_briefing_toss_priority_context` and its bounded line builders
   to append available Top20 overlap, priority quotes, and same-day
   provisional investor-volume context.
3. Catch provider unavailability as the existing context helper does; retain
   the report message and state that the source was unavailable rather than
   inventing a value or suppressing delivery.
4. Keep the report section as the seed/order source. Do not modify candidate
   ranking, scoring, routes, scheduled market-briefing slots, or provider
   endpoint allowlists.

**Verification:**
- Run `python -m pytest tests/test_intraday_empty_notification.py tests/test_toss_openapi.py -q`.
- Run `python -m pytest tests/test_cli_commands.py -q -k "market_briefing or scheduled_poll"`.

## Task 6: Review And Verify

**Files:** all changed files from Tasks 1-5.

1. Review the diff against the no-score/no-trading/no-public-control and
   secret-redaction constraints.
2. Confirm no schema migration or Task Scheduler registration change was
   introduced.
3. Run the focused suite, then the relevant full test files and documentation
   audit.

**Verification:**
- `python -m pytest tests/test_intraday_empty_notification.py tests/test_intraday_paging.py tests/test_toss_openapi.py -q`
- `python -m pytest tests/test_web_view.py -q`
- `python -m stock_monitor docs-hygiene-audit --json`
- `git diff --check`
- `git status --short`
