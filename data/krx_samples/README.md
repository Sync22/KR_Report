# KRX Data Marketplace Raw Samples

Local-only folder for manually captured KRX Data Marketplace JSON samples.

Do not store credentials, cookies, tokens, or personal login data here.
Save only the JSON response body from the target data request.

Recommended filenames:

- `12008_market_YYYYMMDD.local.json`
- `12008_market_YYYYMMDD.manifest.local.json`
- `12009_STOCKCODE_YYYYMMDD.local.json`
- `12009_STOCKCODE_YYYYMMDD.manifest.local.json`
- `12010_top_YYYYMMDD_INVESTOR.local.json`
- `12010_top_YYYYMMDD_INVESTOR.manifest.local.json`

Manifest templates:

- `templates/12009_stock.manifest.template.json`
- `templates/12008_market.manifest.template.json`
- `templates/12010_top.manifest.template.json`

You can also generate a manifest scaffold directly:

```powershell
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --stock-code 329180 --market STK --top-investor foreign
python -m stock_monitor krx-flow-sample-scaffold --date 2026-05-08 --from-candidates --candidate-limit 5 --market STK --top-investor foreign
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 329180 --manifest-output data\krx_samples\12009_329180_20260508.manifest.local.json
```

Prefer `krx-flow-sample-scaffold` when preparing a full capture set because it creates `[12009]`, `[12008]`, and `[12010]` manifest scaffolds together.
Use `--from-candidates` to generate `[12009]` stock manifests from the local leadership-candidate preview.

Validation examples:

```powershell
python -m stock_monitor krx-flow-dry-run --view market --date 2026-05-08 --sample-file data\krx_samples\12008_market_20260508.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 329180 --sample-file data\krx_samples\12009_329180_20260508.local.json --show-first-row
python -m stock_monitor krx-flow-dry-run --view top --date 2026-05-08 --sample-file data\krx_samples\12010_top_20260508_all.local.json --show-first-row
```

If the captured screen used a unit other than shares/KRW, pass it explicitly:

```powershell
python -m stock_monitor krx-flow-dry-run --view stock --date 2026-05-08 --stock-code 329180 --sample-file data\krx_samples\12009_329180_20260508.local.json --volume-unit 천주 --amount-unit 백만원 --show-first-row
```

For repeatable validation, prefer a manifest file next to the raw JSON:

```json
{
  "sample_file": "12009_329180_20260508.local.json",
  "view": "stock",
  "business_date": "2026-05-08",
  "stock_code": "329180",
  "query": "period",
  "market": "ALL",
  "investor": "all",
  "value": "volume",
  "side": "net-buy",
  "volume_unit": "주",
  "amount_unit": "원",
  "expected_min_rows": 1,
  "expected_min_normalized_rows": 1,
  "expected_investors": ["외국인", "기관합계", "개인"]
}
```

Then run:

```powershell
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_329180_20260508.manifest.local.json --show-first-row
```

To keep a normalized validation artifact, add `--normalized-output`:

```powershell
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_329180_20260508.manifest.local.json --normalized-output data\krx_samples\12009_329180_20260508.normalized.local.json --show-first-row
```

Before using a sample as an ingest reference, run strict validation:

```powershell
python -m stock_monitor krx-flow-dry-run --date 2026-05-08 --sample-manifest data\krx_samples\12009_329180_20260508.manifest.local.json --normalized-output data\krx_samples\12009_329180_20260508.normalized.local.json --strict-sample --show-first-row
```

Strict mode returns exit code `2` when the sample has quality warnings, such as zero raw rows or zero normalized rows.
It also checks manifest expectations such as `expected_min_rows`, `expected_min_normalized_rows`, and `expected_investors`.

Batch validation:

```powershell
python -m stock_monitor krx-flow-capture-checklist --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-sample-status --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-validate-samples --manifest-dir data\krx_samples --normalized-dir data\krx_samples\normalized
python -m stock_monitor krx-flow-import-preview --manifest-dir data\krx_samples
python -m stock_monitor krx-flow-import-samples --manifest-dir data\krx_samples --confirm --i-validated
```

`krx-flow-capture-checklist` prints the screen, condition, raw filename, manifest path, and validation command for each manifest.
`krx-flow-sample-status` shows whether stock, market, and top-ranking sample coverage is ready and lists the missing raw files to capture.
This scans `*.manifest.local.json` in the target directory and validates each manifest with strict sample rules.
`--normalized-dir` writes one normalized validation artifact per manifest.
`krx-flow-import-preview` shows the target table row counts that would be produced, still without DB writes.
`krx-flow-import-samples` writes to SQLite only after explicit confirmation and only when no validation warnings remain.
Use `--allow-warnings` only for exploratory checks; do not use warning samples as ingest references.
