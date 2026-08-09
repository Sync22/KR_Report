# Web-View Evidence Composition Design

## Goal

Make the current five-tab web-view read as one connected stored-evidence product without adding a new source, score, schema, or API family.

## Evidence roles

- Reports create the dated candidate pool and its existing order.
- Saved news observations explain whether current news strengthens, cautions, or does not directly connect to a candidate.
- Toss current price and same-day provisional investor flow provide current reference for the fixed Top2; Naver intraday overlap remains an explicit user-triggered comparison.
- Toss 20:00, KRX market/ETF, and `[12009]` investor flow are dated stored reference points. Missing or stale data is a freshness state, not negative evidence.

## Surface journey

1. `메인`: show what to inspect first and the freshest evidence currently available.
2. `관찰`: compare the full candidate pool compactly and select one stock.
3. `종목`: explain the selected stock using reports, targets, news, price, flow, and related market context.
4. `시장` / `순환매`: provide broad and selected-stock context without changing candidate order.

## Minimal corrections

- Restore the web-view boundary to GET-only stored projection. News collection remains in the existing scheduler/CLI path; rendering a page must not silently fetch and write observations.
- Reuse one Top2 Toss request for the same date and cohort until the user explicitly refreshes it.
- Remove contradictory labels: a current Toss quote satisfies the generic current-price gap; target revisions display the actual range; stock detail does not repeat `뉴스 근거`.
- Wait for the mobile watch selector deterministically in browser smoke.
- Delete JavaScript left behind by removed observation/backtest cards when it has no live caller or DOM target.

## Non-goals

- No candidate reordering or new scoring.
- No schema or data migration.
- No scheduler, Telegram, admin-gui, or provider expansion.
- No React/Reflex rewrite.

## Verification

- Route/API tests prove write methods remain blocked.
- Focused web-view and browser-smoke tests pass.
- Desktop and mobile browser checks confirm Top2, watch-to-stock navigation, live quote coherence, and no duplicate Toss request for an unchanged cohort.
- `web-view-value-qa` remains clean.
