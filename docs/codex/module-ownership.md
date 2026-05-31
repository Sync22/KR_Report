# Module Ownership

## Purpose

This document proposes role boundaries for future implementation work.

The project is small enough that one developer can still edit across modules, but the work axes are now distinct enough that subagents should be assigned by responsibility instead of by generic availability.

## Ownership Map

| Module / Axis | Primary Role | Supporting Role | Scope |
| --- | --- | --- | --- |
| Naver report collection | `backend-developer` | `python-pro`, `test-engineer` | Fetch, parse, normalize, dedupe, and parser drift tests. |
| Summary aggregation | `python-pro` | `sql-pro`, `reviewer` | Daily summaries, stock-code-first grouping, target/opinion aggregation, output filters. |
| SQLite schema/repository | `sql-pro` | `backend-developer`, `test-engineer` | Migrations, FK integrity, upserts, replay safety, backup/verify/cleanup contracts. |
| Telegram notifications | `backend-developer` | `cli-developer`, `test-engineer` | Daily summary delivery, fragment resume, intraday outbox, command parsing, paging, memo replay safety. |
| Scheduler/CLI operations | `cli-developer` | `debugger`, `reviewer` | Task Scheduler wrappers, `operator-status`, `operator-control`, health exits, scheduled guards. |
| Admin GUI | `admin-ui-engineer` | `cli-developer`, `reviewer` | Local operator controls, scheduler cards, no-run calendar, safe settings, audit display, recovery controls. |
| User web-view | `web-ui-engineer` | `backend-developer`, `test-engineer` | GET-only friend-facing page, public-safe DTOs, archive/calendar, selected-stock display, market reference UI. |
| KRX Open API market data | `market-data-engineer` | `sql-pro`, `backend-developer` | Stock/ETF/index snapshots, field validation, backfill safety, KRX source ownership. |
| KRX Data Marketplace flow | `market-data-engineer` | `debugger`, `sql-pro`, `test-engineer` | `[12008]`, `[12009]`, `[12010]` request validation, sample capture, import, scheduled-ingest design. |
| Category/taxonomy | `market-data-engineer` | `sql-pro`, `web-ui-engineer` | 업종/테마 source rules, category snapshots, fallback handling, display naming. |
| Candidate evidence | `market-data-engineer` | `sql-pro`, `web-ui-engineer`, `reviewer` | Read-only candidate evidence DTO, evidence separation, exclusion rules, no-scoring boundary. |
| Future intraday observation reference | `market-data-engineer` | `web-ui-engineer`, `security-hardening`, `reviewer`, `test-engineer` | Lab/staging read-only quote/turnover/index source review, top-2 `우선 확인` priority impact, freshness/failure behavior, no broker execution. |
| Future operator decision/execution lane | `market-data-engineer` + `security-hardening` | `reviewer`, `sql-pro`, `test-engineer`, `cli-developer` | Only after stable real-time source proof. Operator-only decision support and execution-lab safety; never collapse into public `web-view`. |
| Rotation overlay | `web-ui-engineer` | `market-data-engineer`, `admin-ui-engineer` | Cycle image overlay, alias mapping, coordinate map, future calibration UI. |
| Access gate / public-safe boundary | `security-hardening` | `web-ui-engineer`, `admin-ui-engineer`, `reviewer` | Entry-code gate, GET-only regression, admin/web-view separation, external-sharing safety checks. |
| External sharing / mini PC | `documentation-engineer` | `reviewer`, `cli-developer` | Handoff docs, access gate, Cloudflare/Tailscale boundary, operation profile notes. |
| Documentation consistency | `documentation-engineer` | `reviewer` | Canonical docs, roadmap/current-work sync, stale plan cleanup. |

## Current Role Split Candidates

| Near-Term Work | Recommended Owner | Why |
| --- | --- | --- |
| User web-view search bar | `web-ui-engineer` | UI/navigation change on the friend-facing surface. |
| `candidate_evidence` DTO | `market-data-engineer` + `sql-pro` | Requires source separation and stable joins across report/KRX/flow/category data. |
| Candidate evidence web-view preview | `web-ui-engineer` | Should preserve the no-trading-recommendation boundary and compact layout while allowing observation-candidate wording. |
| Rotation image text alias table | `market-data-engineer` | Needs taxonomy mapping discipline before UI polish. |
| Rotation overlay calibration UI | `admin-ui-engineer` | Calibration is operator-facing, not friend-facing. |
| KRX scheduled-ingest design | `market-data-engineer` + `debugger` | Requires login/session, skip, retry, and audit/event thinking. |
| Live scheduler review | `debugger` | Focus is root-cause isolation and unattended-run evidence. |
| DB backup/restore/cleanup policy | `sql-pro` | Data safety and retention boundaries. |
| Access-code/public sharing hardening | `security-hardening` | Should review exposed DTOs, blocked routes, and external-sharing assumptions before Cloudflare/Tailscale work. |

## Module Boundaries To Preserve

| Boundary | Rule |
| --- | --- |
| `admin-gui` vs `web-view` | Do not merge them. Admin has controls; web-view is read-only. |
| Reports vs KRX data | Do not store market data in report tables or overwrite report facts with market facts. |
| Category labels vs KRX market data | Do not call current 업종/테마 labels KRX-owned taxonomy unless verified. |
| Candidate evidence vs scoring | Evidence rows and observation-candidate recommendation can be built now; public numeric scoring and trading recommendation require later policy approval. |
| Real-time reference vs execution | Future intraday data may affect observation priority after approval, but must stay separate from broker secrets, order routing, production DB writes, and Telegram/scheduler automation until separately approved. |
| Public observation vs operator decision | Public `web-view` can recommend what to observe. Trading-decision support, if pursued later, is operator-only and requires a separate source/audit/safety contract. |
| Flow samples vs scheduled ingest | Manual/sample/import path exists. The only automatic flow path is the narrow anchor-date mentioned-stock `[12009]` 31-day backfill; broad scheduled ingest remains disabled until separate approval. |
| Access gate vs real auth | Entry-code gate is a lightweight layer, not enterprise authentication. |

## Escalation Points

Pause and ask for user approval before:

- destructive DB migration, broad deletion, or real VACUUM without explicit confirmation
- enabling scheduled KRX Data Marketplace ingest
- connecting a real-time/broker source to production writes, Telegram, scheduler, admin controls, broker secrets, or order routing
- exposing `admin-gui` beyond loopback/private owner access
- adding trading recommendation, public numeric score, investment grade, or buy/sell wording
- silently copying today's category mapping backward into historical dates
- storing new secret material outside `.env` or approved local files

## Suggested Subagent Use

Default operating rule:

- Keep small and obvious single-surface edits local.
- For non-trivial work, prefer a subagent split before implementing.
- Use investigation -> implementation -> review as the default shape when the task touches data, DB, scheduler, Telegram, `admin-gui`, `web-view`, external sharing, or candidate evidence.

| Situation | Use |
| --- | --- |
| UI rendering bug, layout density, public-safe copy | `web-ui-engineer` |
| Admin controls, status cards, operator actions | `admin-ui-engineer` |
| DB schema/upsert/verify/backup concerns | `sql-pro` |
| Parser/runtime/typing failures | `python-pro` |
| Scheduled run or worker heartbeat failure | `debugger` |
| Access gate, GET-only, or public-safe exposure review | `security-hardening` |
| KRX/ETF/flow field or source question | `market-data-engineer` |
| Regression test expansion | `test-engineer` |
| Design/roadmap/doc drift | `documentation-engineer` |
| Risk review before exposing or enabling automation | `reviewer` |
