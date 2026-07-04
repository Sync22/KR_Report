# Contract Documents

This folder contains detailed DTO, display, and data-shape contracts that support the canonical documents.

Use the root-level canonical docs first:

- `docs/codex/surface-contract.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/data-source-policy.md`
- `docs/codex/krx-market-data-runbook.md`

Files here explain specific lower-level contracts and should not override the canonical documents.

Current contract files:

- [candidate-evidence-contract.md]({PROJECT_ROOT}/docs/codex/contracts/candidate-evidence-contract.md) - public-safe candidate evidence DTO and future intraday placeholder boundary.
- [decision-journal-v0-contract.md]({PROJECT_ROOT}/docs/codex/contracts/decision-journal-v0-contract.md) - read-only Decision Journal v0 dry-run JSON contract and field semantics.
- [news-intelligence-contract.md]({PROJECT_ROOT}/docs/codex/contracts/news-intelligence-contract.md) - operator-only news intelligence and public-safe stored projection boundary.
- [toss-openapi-official-api-inventory.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-official-api-inventory.md) - local memory of the official Toss endpoint, schema, auth, rate-limit, and model surface.
- [toss-openapi-postkey-readonly-lab-runbook.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-postkey-readonly-lab-runbook.md) - local key input fields, no-network plan, and bounded first live market-reference probe sequence.
- [toss-openapi-readonly-lab-contract.md]({PROJECT_ROOT}/docs/codex/contracts/toss-openapi-readonly-lab-contract.md) - pre-key Toss OpenAPI read-only/lab boundary, endpoint classification, and forbidden execution/account/public-surface work.

