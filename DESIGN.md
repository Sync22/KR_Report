# Stock Monitor UI Design

An independent editorial direction for the Next.js public research brief. The Wise influence is limited to its recognizable green family and clear hierarchy; the page composition is a Stock Monitor research front page. Project `AGENTS.md`, `docs/codex/data-governance.md`, and `docs/codex/surface-guide.md` remain authoritative for behavior and data.

Source: [VoltAgent/awesome-design-md — Wise](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/wise/DESIGN.md). This project uses selected visual ideas and color values, not Wise marks or assets. It is an independent Stock Monitor interface and is not affiliated with Wise.

## Visual tone

Use a newsroom “research front page” rather than a repeated card dashboard. Pair a deep-green masthead with warm paper, hard rules, large editorial type, and a compact evidence ledger. The first screen should read in this order: the stored briefing headline, the server-ordered Top2 evidence rows, explicit reference actions, then provenance and news detail.

The Top2 ledger is a comparison surface, not a new analysis. Its rows may only rearrange existing candidate order, reason, saved news state, Toss selected-date baseline, and missing-information labels. Use whitespace and typography to distinguish those facts; do not invent a combined verdict.

## Tokens

| Role | Value |
| --- | --- |
| Page canvas | `#f3f0e6` |
| Paper surface | `#fffdf7` |
| Soft surface | `#e2f6d5` |
| Main text | `#0e0f0c` |
| Body text | `#454745` |
| Muted text | `#686b67` |
| Border | `#d3d0c4` |
| Masthead / section ink | `#163300` |
| Primary control | `#9fe870` with `#0e0f0c` text |
| Positive data | `#2ead4b` / `#054d28` |
| Negative data | `#d03238` |
| Warning data | `#ffd11a` with `#4a3b1c` text |

Lime is a brand accent for the masthead mark and primary user actions. It never signals a gain, loss, success, or candidate quality. Positive, negative, and warning values retain their existing semantic colors and labels.

## Components and layout

- Use one full-width masthead, one editorial headline, and a ruled two-row candidate ledger. Avoid repeating the same rounded container for every section.
- Keep search guidance on the label row and keep every daily tab aligned to the same 42px control height as the search field.
- Keep Main current-price, flow, and market calls below the ledger as separate explicit actions. Full multi-symbol chart controls belong to the separate Chart Explorer tab.
- Show a clear active treatment only while a requested result is displayed. Keep secondary flow values and detailed indicator values in native disclosures so the condition summary and chart remain the first read.
- Place saved-news matching across the full first row. In the second row, give the reading memo about 60% width and the source/freshness ledger about 40%; stack all three in the same order on mobile, keeping each source and timestamp next to the values it qualifies.
- Keep historical saved market, ETF, and rotation panels on the selected-date overview or their dedicated reference routes; Main shows its explicitly requested Top2 reads only.
- Tables stay readable. On mobile, the candidate ledger becomes ordered rows with its column labels retained; other wide tables may scroll inside their own wrapper.
- Use existing Korean system fonts, with Inter as an optional installed fallback. Do not load proprietary Wise Sans or remote fonts.
- Keep clear focus indicators, sufficient contrast, labeled controls, and text alongside color-coded statuses.
- This composition applies to the Next public surface. `admin-gui` remains a separate operator surface with its own layout and controls.

## Surface rules

- `admin-gui` stays operator-only. Its scheduler, settings, recovery, and audit controls remain in their current locations and keep their confirmation behavior.
- `web-view` stays a public-safe, stored-data-first, GET-only surface. Do not add operator controls, credentials, score/grade, generic buy/sell advice, or ranking changes. The user-requested Chart Explorer may make only its bounded, explicit fixed-provider GET described by the Chart Explorer data contract; it cannot write data or affect stored candidate order.
- The local Next preview follows the same visual system while retaining its preview-only and read-only data behavior.
- Do not copy Wise's wordmark, logo, currency converter, marketing copy, or claims of affiliation.

## Attribution and license

Adapted from the Wise design analysis in [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md), licensed under MIT. Copyright (c) 2026 VoltAgent.

MIT License notice for the source material:

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
