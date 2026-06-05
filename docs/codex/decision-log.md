# Decision Log

## Scope Constraint

- All decisions here apply only to `{PROJECT_ROOT}`.
- No external folder state should be treated as part of this project.

## 2026-04-24 to 2026-04-25

### Project Purpose

- Build a personal-use MVP that monitors the Naver Stock research company page for the domestic stocks tab.
- Collect newly observed reports during Korean business hours.
- Send a next-business-day morning summary.

### Page Scope

- MVP scope is limited to the domestic stocks tab on the target research page.
- Other tabs are intentionally excluded for now because parsing rules are not yet clearly defined there.

### Polling Window

- Poll every 30 minutes from `08:30` to `16:30` KST.
- This window intentionally covers the current desktop-validation monitoring window and is separate from the `08:10` KRX Open API backfill after the official next-business-day `08:00` publication window and the `08:20` daily briefing sequence.
- Polling hours remain configurable through environment variables and task registration arguments.

### Business-Day Rule

- Scheduling follows Korean market business days.
- Daily summary is sent at `07:00` KST on the next Korean business day.
- 2024~2026 KRX market holidays and year-end closures are treated as default business-day overrides.

### Meaning of Mention Count

- Mention count is defined as the number of new reports for a stock on that business day.
- It is not defined as scroll exposure count across polling runs.

### New Report Identity

- A report is treated as new based on:
- stock
- title
- broker
- published datetime

### Daily Aggregation Rule

- Aggregate by `stock x business day`.
- Daily summary notification sends the top `7` summarized stocks by default.
- Additional summary pages are fetched on demand through Telegram commands.

### Same Broker Multiple Reports

- Notification display should group same-broker repeats as `broker_name(count)`.
- Representative target price for the same broker uses the maximum parsed value.
- Representative opinion for the same broker uses the most recent report.

### Target Price Summary

- Daily stock target price summary uses the minimum and maximum parsed values from that day's new reports.
- Missing or non-numeric target prices are not aggregate values.
- If no numeric target price is available, summary/detail display uses `-`, while raw/detail views still make it clear that the source report had no target price.

### Opinion Normalization

- Normalize opinions into:
- `buy`
- `neutral`
- `sell`
- `N/A`

- Daily dominant opinion uses the mode of valid normalized values.
- `N/A` is excluded from dominant-opinion voting and is used only when no valid opinion exists.
- Tie-break priority for valid opinions is `buy > neutral > sell`.

### Data Quality Boundary

- Raw/source values, parsed/storage values, aggregate values, and display values must be reviewed separately.
- `N/A`, `NA`, `NULL`, `NONE`, `-`, and blank numeric fields are missing markers, not numeric or ranking values.
- Missing values may be preserved in stock detail or stock search output, but must not distort target ranges, representative opinions, rankings, or market summaries.
- Display placeholders such as `목표가 -`, `의견 없음`, and `KRX 기준값 없음` are surface-specific presentation text and must not overwrite stored facts.
- Report identity is based on `source_id` or `identity_key`, not display text.
- `broker_display` is display-only derived text; do not parse it back as canonical broker data.
- `published_at`, `business_date`, and `collected_at` have separate meanings; archive and summary grouping use `business_date`.
- The persistent checklist is [data-quality-checklist.md](/docs/codex/data-quality-checklist.md).

### Technical Direction

- Recommended MVP stack is `Python + Playwright + SQLite + Telegram Bot + Windows Task Scheduler`.
- The first implementation can run on the main Windows PC, but the operating model should remain portable to a separate always-on Windows mini PC without major redesign.
- Environment-based configuration, local scheduler scripts, and self-contained SQLite storage are preferred because they lower the cost of later host migration.

### Telegram Summary Paging

- Summary notifications should support `다음`, `전부`, and `처음` commands in the Telegram chat.
- The system tracks how many stocks have already been delivered for the active business date.

### Notification Modes

- There are two intended notification modes:
- next-business-day daily summary
- intraday monitoring during the configured poll window

- Intraday alerts are emitted per polling batch of newly inserted reports.
- Intraday alert delivery is backed by a durable outbox so failed sends can be retried on the next processing run.

### Telegram Command Surface

- The current Telegram command surface is intentionally minimal and text-based.
- Daily summary paging currently accepts:
- `다음`, `더`, `더보기`
- `전부`, `전체`
- `처음`, `처음부터`
- Slash aliases are also accepted for paging:
- `/다음`
- `/전부`
- `/처음`

- Stock-specific lookup is supported as:
- `/종목검색 017670`
- `/종목코드 삼성전자`

- `/종목검색` now acts as the main stock-query entry point:
- stock-code input resolves directly
- stock-name input returns numbered candidates first
- numeric follow-up input selects the target stock

- `/종목코드` remains as a helper command for explicit stock-code discovery.
- Slash commands such as `/다음목록` are accepted as operator ergonomics aliases.

### Stock Query Backlog

- The stock query version uses the stock-specific Naver research API and summarizes recent reports within a `D-15` window.
- `/종목검색` should always favor user confirmation when a stock-name query can map to multiple plausible listed names.
- Numeric follow-up selection is stored in Telegram control state with expiry so the polling-style command processor can complete the 2-step flow safely.
- Stock-query responses may include current price at the time of the lookup, but this is a query-time aid rather than part of the scheduled daily summary.
- Future enhancements can add richer pagination, broader historical windows, or quote freshness labels when needed.

### Future Sector View Direction

- A later phase may extend beyond per-stock alerts into sector-level accumulation and ranking.
- The first sector goal is to infer which sectors are leading on a given day by aggregating report counts and recency at the sector level.
- A second sector goal is to compare representative stocks within the same sector and later pair those names with daily demand or flow-style signals.
- This should be treated as a later data-product layer on top of the existing report collector rather than mixed into the MVP alert format immediately.
- Future UI work may expose this data through a lightweight web view once the stored data shape and operator preferences are stable enough.

### Future Operator Workflow

- The intended medium-term workflow is:
- Telegram for morning summary and intraday alerts
- a later web view for after-market review, browsing, and thinking
- That means the web layer does not need to replace Telegram; it should complement the notification flow with richer read-oriented views after the market session.
- Until several live-market days have validated the current batches and stored data, web-view work should remain in memo/backlog mode rather than active implementation.
- The `example/report_*.jpg` references are useful as layout and information-architecture inspiration, but the project should not copy unsupported trading-signal semantics directly.
- Useful reference patterns include market mood, strong/weak lists, category rotation, and next-watch candidates.
- `example/Cycle.jpg` should be treated as a conceptual reference for a future sector/theme rotation view, showing possible attention movement across broad market groups.
- Any rotation-cycle view should be descriptive and data-backed by accumulated report/sector/theme history, not a hard-coded prediction that money must move in a fixed order.
- Score, grade, and conviction-style displays should wait until there is enough historical data and a clear calculation rule.

### Future Operator/Admin Program

- A local admin surface is likely useful once the system moves toward N100 or other always-on operation.
- `admin-gui` must remain a local control surface. If a mini PC or remote access path is added, the read-only shared/web-view surface must be separate from the control admin surface.
- This separation is a permission/API boundary, not only a UI boundary.
- Do not implement the shared user page by adding a read-only mode to `admin-gui`.
- The `web-view` uses a separate page/server handler and GET-only read model.
- `web-view` can share SQLite, repository queries, and summary logic, but it must not expose admin control handlers or raw `build_operator_status_snapshot()` output.
- Remote access should use private access paths such as VPN, mesh networking, restricted tunnel, or remote desktop rather than directly exposing the control admin page.
- The read-only `web-view` must not include POST controls for scheduler execution, scheduler enable/disable, shutdown, pause/resume, `.env`, or token/config changes.
- Telegram shortcuts that open or expose `admin-gui`, such as `/관리자페이지 열기`, are deferred.
- Future Telegram operator shortcuts should prefer read-only status and guidance, such as `/상태`, `/오늘돌아?`, `/스케줄상태`, and `/웹뷰주소`.
- KRDS (Korea Design System) should be the primary design reference for the local admin program and later web-view, so the project has a consistent baseline for layout, components, patterns, accessibility, and feedback.
- The admin surface should prioritize operator confidence over feature density: scheduler state, run-now controls, pause/resume controls, next run time, and recent errors matter first.
- It should also expose human-review surfaces such as local memos, pending ideas, data freshness, and last successful Telegram delivery.
- Configuration editing should be constrained to safe operational knobs at first, such as poll windows, default display limits, shutdown enablement, and holiday overrides.
- The first admin version should stay local-only and avoid turning into a public web service until security and deployment boundaries are deliberate.
- Backlog priority should favor operational confidence before richer analytics: admin/status visibility first, sector and mood summaries second, advanced scoring or flow-based alerts later.
- The initial admin view does not need a polished public web stack; a local-only page, simple server, or even a focused CLI/TUI is acceptable if it makes scheduler and data state visible.
- Holiday override management should be operator-editable because temporary holidays, personal off-days, and ad-hoc no-run days cannot be covered reliably by a static yearly holiday list.
- The admin view should expose recent operational logs in a visible status area, especially batch sends, skips, Telegram command-worker activity, and errors, because hidden scheduled work is hard to trust without feedback.
- A later admin/worker architecture should aim to avoid visible CMD/PowerShell windows by running tasks through direct Python calls, no-window subprocess options, or a service-style background worker. Task Scheduler shell wrappers can remain as a fallback, but the preferred operator experience is status in the admin panel rather than flashing console windows.
- KRDS should be adapted as a usability/design system, not copied as a government identity: official masthead or government-service wording is unnecessary for this private local tool, but KRDS-style consistency, readable typography, feedback, form, list, filter, error, and confirmation patterns should be followed.

### Future Data Preparation

- Keep per-report sector labels stable and available in stored views so sector rollups can be rebuilt historically.
- Sector/theme history should eventually use dated mapping snapshots. Until then, any historical sector/theme rollup should be treated as "latest mapping applied" rather than guaranteed historical classification.
- Be prepared to add a separate derived table for sector-day aggregates instead of recalculating everything only from Telegram-facing summary output.
- If representative-stock demand or flow signals are later added, they should likely live in their own ingest path and join onto the report-derived sector summary rather than overloading the current report schema directly.
- ETF data should use a separate ingest and display model rather than being inserted into company-report summaries.
- Report count is an attention signal, not supply/demand flow. Flow, volume, and trading-value data should be collected through a separate market-data ingest before rotation or interest-alert features rely on it.
- Naver industry/theme pages are the preferred domestic taxonomy source for industry/theme labels. KRX remains the preferred source for market data such as price, volume, turnover, ETF, and index context.
- Industry refresh should remain explicit and slow first (`refresh-industry <code>`), not broad automatic crawling, until source stability and rate behavior are observed.
- Store industry as the representative sector-like label in `stock_metadata`; keep theme membership as a separate many-to-many layer because one stock can belong to multiple themes.

### Future Target-Price Progress View

- A later web view may show how far each stock has progressed toward report target prices after the first target-bearing report is observed.
- A candidate display idea is `목표가의 N% 도달 (M일차)`.
- This is mainly a review/interest feature, not a trading signal by itself.
- The baseline should be the first observed report date with a numeric target price for the stock.
- The comparison price should use a clearly defined price source and timestamp, because current price and close price can tell different stories.
- This feature should wait until enough history exists to avoid over-interpreting a very short collection window.

### Future Follow-Up Interest Alert

- A later notification idea is to watch stocks that had reports today and then review supply/demand behavior through report day plus the next trading day.
- On the third trading day, the system could send a separate `관심종목` style alert if the follow-up conditions look notable.
- Foreign/institution/individual flow is a candidate input because the operator values supply/demand, but it should remain a supporting indicator rather than a standalone conclusion.
- The report collector should not be overloaded with this data; supply/demand or volume data should be collected through a separate ingest path and joined later.
- The exact trigger rules should be decided after studying a few live examples and any supplementary indicators that may help avoid noisy alerts.

### Host Operation

- Windows Task Scheduler registration is now part of the active operating model rather than a future task.
- The host only needs to be powered on and connected before the scheduled windows; the monitor does not require a permanently running foreground shell.
- Current weekday scheduler windows are `KrxDailyBackfill 08:10`, `Notify 08:20`, `Poll 08:30~16:30`, and `TelegramCommands 08:00~16:30`.
- During the live validation period, `StockMonitor-Shutdown` shuts the host down at `17:10` with a 60-second delay, so the `16:45` KRX login reminder and `16:50` flow validation window can complete first.
- The shutdown task should not use missed-run catch-up, because a delayed shutdown after a later boot would be more harmful than a missed same-day shutdown.
- Windows Task Scheduler itself is weekday-based and does not know Korean market holidays, so command processing and shutdown must use scheduled Python wrappers with internal business-day guards.
- Telegram command processing should use a single hidden daily worker loop rather than one Task Scheduler launch per minute, because per-minute launches can create visible console flicker even when each run immediately skips on holidays.
- Manual Telegram test sends must not share the same successful-delivery channel as production scheduled summaries.
- Production morning summaries use the `telegram` delivery channel.
- Manual operator test sends use the `telegram_test` delivery channel so weekend or ad-hoc testing cannot block the next weekday `08:20` briefing summary.
- Operator ideas sent through `/메모` are stored as local Markdown under `data/operator_memos.md`, not in source-controlled docs, so rough ideas can be captured quickly without turning into committed requirements too early.

### Known Documentation Issue

- `stock_research_monitor_mvp.md` appears with garbled Korean text in current shell output.
- Treat encoding verification as an explicit follow-up task before heavy editing.
