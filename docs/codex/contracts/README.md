# Contract Documents

This folder contains detailed DTO, display, and data-shape contracts that support the canonical documents.

Use the root-level canonical docs first:

- `docs/codex/surface-contract.md`
- `docs/codex/data-quality-checklist.md`
- `docs/codex/data-source-policy.md`
- `docs/codex/krx-market-data-runbook.md`

Files here explain specific lower-level contracts and should not override the canonical documents.

Current contract files:

- [candidate-evidence-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/contracts/candidate-evidence-contract.md) - public-safe candidate evidence DTO and future intraday placeholder boundary.
- [news-intelligence-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/contracts/news-intelligence-contract.md) - operator-only news intelligence and public-safe stored projection boundary.
- [toss-openapi-official-api-inventory.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/contracts/toss-openapi-official-api-inventory.md) - local memory of the official Toss endpoint, schema, auth, rate-limit, and model surface.
- [toss-openapi-readonly-lab-contract.md](/C:/Users/MING/Codex/02.Stock_Moniter/docs/codex/contracts/toss-openapi-readonly-lab-contract.md) - pre-key Toss OpenAPI read-only/lab boundary, endpoint classification, and forbidden execution/account/public-surface work.

