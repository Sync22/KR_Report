# Stock Monitor Documentation

This is the documentation skeleton. Read this file first, then open only the branch that matches the task.

## Branches

| Branch | Use it for |
| --- | --- |
| [Operating guide](operating-guide.md) | Roadmap, decision history, and next work. Verify live scheduler/source contracts in the runbooks below. |
| [Architecture guide](architecture-guide.md) | Code map, ownership, agent use, risks, and decisions. |
| [Data governance](data-governance.md) | Value layers, current source ownership, and historical KRX boundary. |
| [Market-data runbook](market-data-runbook.md) | Toss close snapshot operations, parked proposals, and bounded KRX historical recovery policy. |
| [Surface guide](surface-guide.md) | `admin-gui`, GET-only `web-view`, rotation, and realtime-first display policy. |
| [Candidate evidence](candidate-evidence.md) | Candidate DTO and evidence/target-progress/operator-memo implementation rules. |
| [News intelligence](news-intelligence.md) | Operator-only news collection and future public-safe projection boundary. |
| [Decision journal](decision-journal.md) | Read-only Decision Journal v0 contract. |
| [Toss OpenAPI lab](toss-openapi-lab.md) | Approved read-only API boundaries, manually checked REST spec snapshot, and lab-only probe instructions. |
| [Mini PC runbook](mini-pc-runbook.md) | Migration, restore, scheduler handoff, Next V1 Operations-PC initial check, and weekly sync. |
| [Operations performance observation](operations-performance-observation.md) | Post-move N100 route timings, resource use, SQLite/WAL concurrency, stability, and recovery results; never fill from development-PC data. |
| [Chart alert design and status](chart-alert-proposal.md) | Report-focused 1-minute chart monitoring, local event spool, Python outbox, and dev/operations verification boundary. |
| [Research notes](research-notes.md) | Backtest, scoring hold, and Telegram briefing research. |
| [History](history.md) | Traceability only; never treat it as current operating guidance. |

## Rules

- `admin-gui` is operator-only; `web-view` is public-safe and GET-only.
- No public numeric score/grade, generic buy/sell recommendation, or broker execution. Main Top2's separate price-condition contract is owned by [Data governance](data-governance.md#main-top2-technical-indicator-projection). The user-authorized Chart Lab is a local-only experimental surface, documented separately in [Data governance](data-governance.md#chart-lab-local-test-surface) and [Surface guide](surface-guide.md#chart-lab-local-only-test-surface); its strategy/monitor fields do not become public web-view data.
- Keep raw/source, parsed/storage, aggregate, and display values separate.
- Web-view market, ETF, and flow projections use the stored Toss 20:00 close snapshot. Existing KRX rows are historical references only and no longer receive scheduled refreshes.
- Current scheduler task names and timings live in [Mini PC runbook](mini-pc-runbook.md); current market-source ownership lives in [Market-data runbook](market-data-runbook.md). Older KRX task text elsewhere is historical unless those runbooks explicitly reintroduce it.
- Lab/source probes must not connect to operating SQLite writes, Telegram, scheduler, admin GUI, or public web-view behavior. The explicitly approved local Chart Lab monitor may use only its separate per-user state file.

## Historical Material

- `docs/superpowers/plans/2026-10-16-stock-newbby-chart-lab.md` is the Chart Lab execution record; its unchecked items remain verification gaps. Current behavior is owned by [Data governance](data-governance.md#chart-lab-local-test-surface) and [Surface guide](surface-guide.md#chart-lab-local-only-test-surface).
- Other files under `docs/superpowers/plans/` and `docs/superpowers/specs/` contain dated design and execution records, not current implementation instructions.
- `stock_research_monitor_mvp.md` records product requirements and future intent. Verify present implementation in this index's canonical contracts and source.
- Use [Operating guide](operating-guide.md) for current project work, [History](history.md) for durable dated decisions, and Git for routine code-change traceability.

## Maintenance

Update an existing branch rather than creating a new Markdown file. Add a file only for a long-lived contract that cannot fit one of the branches above. Historical links in `CHANGELOG.md` intentionally remain historical records.
