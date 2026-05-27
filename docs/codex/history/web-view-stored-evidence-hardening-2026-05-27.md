# Web-View Stored Evidence Hardening Handoff

## Intent

This dev-branch change hardens the friend-facing `web-view` around stored-data observation.

The goal is not to add live trading, broker integration, real-time quote logic, or a new data-ingest lane. The goal is to make the existing stored Naver report, KRX reference, and investor-flow evidence easier to read, safer to expose, and easier to review before an operation-side sync.

## Main Changes

- Main `web-view` candidate cards emphasize stored evidence rather than internal diagnostic signals.
- Public candidate labels stay limited to visible `why_notable` and `missing_information`.
- Internal candidate signals remain available through operator/readiness output.
- Public `/api/candidate-evidence` rows are thinner than internal readiness rows.
- Public candidate rows no longer expose `quality_flags`, `evidence_notes`, `opinion_summary`, `report_summary.broker_count`, `report_summary.broker_display`, or `report_summary.dominant_opinion`.
- Candidate card display no longer shows broker breadth or dominant opinion wording in the public card body.
- Mobile candidate cards keep the current three-box evidence structure, but compress inner metric grids for narrow viewports.
- `국장 시장 분위기` remains an interpretation block.
- `시장 참고` remains a stored-data evidence block.
- Broker/OpenAPI work remains future lab/staging only.

## Boundaries

No changes are intended for:

- production DB contents
- schema or migrations
- Telegram send behavior
- scheduler registration or timing
- `admin-gui` control behavior
- broker/OpenAPI integration
- external tunnel/provider setup

## Public-Safe Rules

This change keeps:

- `web-view` GET-only
- no public numeric score
- no public recommendation
- no buy/sell signal wording
- no broker/execution hookup
- no scheduler/admin/env/DB-path exposure

## Validation

Passed locally on `2026-05-27`:

- `python -m pytest tests\test_web_view.py -q` -> `49 passed`
- `python -m pytest tests\test_cli_commands.py -q` -> `277 passed`
- `python -m stock_monitor candidate-evidence-readiness --recent-report-dates 5 --stock-limit 20 --json`
  - `review_ready_count=5`
  - `qa_issue_date_count=0`
  - `qa_warning_date_count=0`
  - visible/public label counts and internal signal counts are separated
- `python -m stock_monitor web-view-browser-smoke --date latest --json`
  - `issue_count=0`
  - desktop/tablet/large-mobile/mobile horizontal overflow all `0`
  - `POST /api/daily/2026-05-15` returned `405`
  - `/api/status` returned `404`
- `python -m stock_monitor web-view-value-qa --recent-business-days 5 --stock-limit 20 --json`
  - `issue_count=0`
  - `warning_count=5`

Known warning:

- `web-view-value-qa` reports `krx_snapshot_not_yet_available` for dates newer than latest stored KRX snapshot `2026-05-19`.
- This is expected under the stored-data model and does not imply live intraday support.

## Operation-Side Review Checklist

After pulling this dev branch, review:

1. Latest report-date main page in a browser.
2. Candidate cards on desktop and mobile.
3. Public `/api/candidate-evidence` payload shape.
4. `candidate-evidence-readiness` visible/internal counts.
5. Whether top-2 candidate duplication is still useful in daily use.

Do not connect this branch to broker/OpenAPI, Telegram scheduling, admin controls, or production DB write paths without a separate reviewed goal.

## Notes For Merge Review

- `data/` runtime, sample, log, backup, and local intake files are intentionally not part of this handoff.
- `AGENTS.md` is already dirty in the dev worktree and appears as a broader project-instruction rewrite. Review it separately from the web-view hardening code if merging to another branch.
