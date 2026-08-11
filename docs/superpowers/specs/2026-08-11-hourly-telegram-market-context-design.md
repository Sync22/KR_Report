# Hourly Telegram Market Context Design

## Purpose

Replace the existing 30-minute intraday Telegram delivery cadence with a
compact hourly market-context briefing. Keep the 30-minute report collection
and dedupe cadence unchanged.

## Delivery Schedule

Send at `08:30`, then `09:30` through `15:30` KST on Korean business days.

- `08:30`: report-first pre-market briefing. Do not require Toss Top20,
  current price, or same-day provisional investor-volume data.
- `09:30` through `15:30`: summarize the preceding hour of new reports and
  include available current market context.

The existing poll task remains the execution trigger. No new scheduler task
is introduced.

## Briefing Content

The report remains the candidate seed and ordering source. Each hourly
briefing may add, when available:

- independent same-day news for server-derived report candidates;
- Toss Top20 market-context overlap;
- Toss current price and same-day provisional investor-volume for the
  server-derived top two;
- explicit source and checked-time labels.

Missing Toss data is neutral. It must not suppress a report briefing, lower a
candidate, create a candidate, or become a score or trading instruction.

## Boundaries

- `web-view` remains GET-only and public-safe.
- The hourly Telegram change does not add account, asset, order, or execution
  API use.
- It does not add a new persistence path. Existing explicit-confirmation
  Top20 capture/replay and bounded scheduled news collection retain their
  separate contracts.
- No new Task Scheduler registration is added.
- Telegram content remains factual market context, not a recommendation,
  investment grade, score, or buy/sell signal.

## Verification

- Existing 30-minute collection still records/dedupes reports.
- Telegram delivery occurs only at the approved schedule.
- The 08:30 briefing succeeds without Toss market data.
- Later briefings tolerate unavailable Toss responses and preserve report
  content.
- Existing public-surface, secret-redaction, and no-order endpoint tests stay
  green.
