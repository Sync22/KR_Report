# Stock Monitor Documentation

This is the documentation skeleton. Read this file first, then open only the branch that matches the task.

## Branches

| Branch | Use it for |
| --- | --- |
| [Operating guide](operating-guide.md) | Current state, roadmap, next work, and TODOs. |
| [Architecture guide](architecture-guide.md) | Code map, ownership, agent use, risks, and decisions. |
| [Data governance](data-governance.md) | Value layers, source ownership, rebaseline, and baseline coverage. |
| [Market-data runbook](market-data-runbook.md) | Toss close snapshot operations and retained KRX historical-reference policy. |
| [Surface guide](surface-guide.md) | `admin-gui`, GET-only `web-view`, rotation, and realtime-first display policy. |
| [Candidate evidence](candidate-evidence.md) | Candidate DTO and evidence/target-progress/operator-memo implementation rules. |
| [News intelligence](news-intelligence.md) | Operator-only news collection and future public-safe projection boundary. |
| [Decision journal](decision-journal.md) | Read-only Decision Journal v0 contract. |
| [Toss OpenAPI lab](toss-openapi-lab.md) | Read-only lab boundary, inventory, and post-key probe sequence. |
| [Mini PC runbook](mini-pc-runbook.md) | Migration, restore, scheduler handoff, and weekly sync. |
| [Research notes](research-notes.md) | Backtest, scoring hold, and Telegram briefing research. |
| [History](history.md) | Traceability only; never treat it as current operating guidance. |

## Rules

- `admin-gui` is operator-only; `web-view` is public-safe and GET-only.
- No public score, grade, buy/sell recommendation, or broker execution behavior.
- Keep raw/source, parsed/storage, aggregate, and display values separate.
- Web-view market, ETF, and flow projections use the stored Toss 20:00 close snapshot. Existing KRX rows are historical references only and no longer receive scheduled refreshes.
- Lab/source probes must not connect directly to SQLite writes, Telegram, scheduler, admin GUI, or public web-view behavior.

## Maintenance

Update an existing branch rather than creating a new Markdown file. Add a file only for a long-lived contract that cannot fit one of the branches above. Historical links in `CHANGELOG.md` intentionally remain historical records.
