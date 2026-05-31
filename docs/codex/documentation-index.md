# Documentation Index

## Purpose

This is the canonical document map for `02.Stock_Moniter`.

Use this file first when deciding which project document is authoritative. Older detailed notes are kept for traceability, but new work should update the canonical documents below before adding another planning file.

## Today Scope

Current work is the main-PC execution pass for the next-phase closeout, while excluding US market expansion, public trading recommendations, broad ingest, and automatic scheduling of the new market-briefing lane. This public-surface exclusion is not a permanent denial of the longer-term direction: if stable real-time data is later proven, operator-only decision-support or execution-lab work must be documented separately before any trading-decision or order path. Historical mini-PC provider/phone-review notes remain useful trace evidence, but the active main-PC readiness gates are separate. The `2026-05-29` read-only readiness refresh reports `completion_ready=false`: market-briefing manual review sends are `0/3`, phone review is not accepted, KRX Open API daily snapshots are missing for 6 business dates starting with `2026-05-28`, real `2026-05-29` scheduled-run evidence is missing, external `web-view` provider smoke is not recorded on this PC, and the current-user `web-view` Startup shortcut is not configured. The current public surface boundary remains `admin-gui` private/operator-only and `web-view` GET-only/read-only; public numeric scores, investment grades, trading calls, broker execution, and order routing remain out of scope.

Implementation-heavy follow-up work should use this map to avoid adding duplicate planning documents.

## Canonical Documents

| Area | Canonical document | Role |
| --- | --- | --- |
| Product requirements | [stock_research_monitor_mvp.md](/C:/Users/MING/Codex/02.Stock_Moniter/stock_research_monitor_mvp.md) | Current product requirements and explicit non-goals. This is no longer only the initial MVP memo. |
| Current status | [current-work.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/current-work.md) | Current state, active assumptions, immediate next work. |
| Next phase | [next-phase.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/next-phase.md) | Next execution axes and non-goals from the current state. |
| Progress and roadmap | [execution-roadmap.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/execution-roadmap.md) | Progress percentages, P0/P1/P2, 100% definition. |
| Project file map | [project-map.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/project-map.md) | Where important code/data/docs live. |
| Surface boundary | [surface-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/surface-contract.md) | `admin-gui` vs read-only `web-view` contract. |
| Data quality | [data-quality-checklist.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-quality-checklist.md) | Raw, parsed, aggregate, and display value rules. |
| Source ownership | [data-source-policy.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-source-policy.md) | Naver/KRX/taxonomy ownership and naming. |
| KRX and flow | [krx-market-data-runbook.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/krx-market-data-runbook.md) | KRX Open API, Data Marketplace, ETF, flow, stages, and guards in one place. |
| KRX 18-month baseline | [krx-18m-backfill-analysis.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/krx-18m-backfill-analysis.md) | 18-month OpenAPI backfill progress, source-lane comparison, skill/agent comparison, and repeatable baseline analysis commands. |
| Data rebaseline | [data-rebaseline-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/data-rebaseline-plan.md) | How to extend market-reference data before migration. |
| Architecture risk review | [architecture-risk-review.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/architecture-risk-review.md) | Current architecture snapshot, risk candidates, source/surface boundaries, performance candidates, and agent ownership for broad reviews. |
| Admin GUI | [admin-gui-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/admin-gui-plan.md) | Local operator GUI status and next safe controls. |
| Agents | [agent-guide.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/agent-guide.md) | When and how to use project subagents. |
| Module ownership | [module-ownership.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/module-ownership.md) | Proposed role boundaries by module and next work axis. |
| Agent reassessment | [agent-reassessment.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/agent-reassessment.md) | Current local `.codex/agents` keep/add/merge evaluation. |
| Rotation overlay | [rotation-overlay-plan.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/rotation-overlay-plan.md) | SVG overlay plan for the cycle image. |
| Mini PC handoff | [mini-pc-migration-handoff.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/mini-pc-migration-handoff.md) | Current Windows N100 migration, archive, restore, scheduler registration, source-desktop cutover, and external web-view readiness notes. |
| Weekly PC sync | [weekly-sync/WEEKLY_SYNC_GUIDE.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/weekly-sync/WEEKLY_SYNC_GUIDE.md) | Weekly main-PC and mini-PC sync guide/prompt docs. Generated weekly handoff notes and sync archives live under `handoff/mini_pc_changes/`. |

## Detailed Reference Documents

These files remain useful as detailed history or implementation notes, but they should not be the first source for new planning:

| Detail document | Prefer updating |
| --- | --- |
| `details/krx/*` | `krx-market-data-runbook.md` |
| `contracts/*` | `surface-contract.md`, `data-quality-checklist.md`, `data-source-policy.md`, and the relevant canonical runbook |
| `plans/*` | `current-work.md`, `next-phase.md`, and `execution-roadmap.md` |
| `plans/observation-candidate-recommendation-goal-prompt.md` | Goal prompt for the next `오늘의 관찰 후보` implementation pass; keep the product boundary in `current-work.md`, `next-phase.md`, and `surface-contract.md`. |
| `history/mini-pc-restore-change-log-2026-05-16.md` | `mini-pc-migration-handoff.md`, `current-work.md`, and `krx-market-data-runbook.md` for ongoing policy; keep this file as the source-sync record for the mini PC restore session. |
| `history/web-view-stored-evidence-hardening-2026-05-27.md` | Handoff note for the dev-branch stored-evidence `web-view` hardening pass; use `current-work.md`, `next-phase.md`, `surface-contract.md`, and `contracts/candidate-evidence-contract.md` for ongoing policy. |
| `history/web-view-five-tab-hardening-2026-05-29.md` | Handoff note for the 2026-05-29 five-tab `web-view` IA, candidate evidence boundary, public DTO leak checks, and browser-smoke hardening pass. |
| Older web-view/P2 planning notes | `execution-roadmap.md`, `next-phase.md`, and `surface-contract.md` |
| `../DOCS_ROLE_REORG_REVIEW_PROMPT.md`, `../DOCS_ROLE_REORG_REVIEW_2026-05-17.md` | Docs role reorganization prompt/review; use before any approved `docs/` path move. |

## Role Folders

| Folder | Role |
| --- | --- |
| `docs/codex/details/krx/` | Detailed KRX/Data Marketplace source notes, capture runbooks, and schema-stage references. |
| `docs/codex/contracts/` | Specific DTO/display/data-shape contracts that support canonical policy docs. |
| `docs/codex/plans/` | Detailed feature or analysis plans that remain useful but are not current-status anchors. |
| `docs/codex/history/` | Historical restore/change logs kept for traceability. |
| `docs/codex/weekly-sync/` | Weekly main-PC/mini-PC sync guide and prompt only. |

## Cleanup Policy

Do not keep duplicate Markdown files just for history when the content has already been absorbed into canonical documents.

When a file becomes superseded:

1. Keep it in place until all active links are updated.
2. Add or keep a canonical pointer in this index.
3. Delete clearly obsolete archive/detail files after a link search confirms no active document depends on them.
4. If a deleted document is mentioned only in `CHANGELOG.md`, leave the changelog line as historical record instead of restoring the file.

2026-05-14 cleanup result:

- Removed obsolete archived admin/agent planning files under `docs/codex/archive/`.
- Removed obsolete `future-webview-operation-plan.md` and `p2-execution-plan.md` after their current guidance was absorbed into `execution-roadmap.md`, `next-phase.md`, and `surface-contract.md`.
- Current admin guidance lives in `admin-gui-plan.md`.
- Current agent guidance lives in `agent-guide.md`, `agent-reassessment.md`, and `module-ownership.md`.

## Update Rule

Before creating a new `.md` file under `docs/codex`, check whether one of the canonical documents can hold the content.

New documents are allowed only when the topic needs a separate long-lived contract, runbook, or implementation stage boundary.
