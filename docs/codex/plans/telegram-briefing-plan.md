# Telegram Briefing Plan

## Purpose

Upgrade the previous-business-day Telegram summary into an optional morning briefing format.

This is not a new real-time market bot. It reuses stored report, KRX, and quote context and stays inside the existing daily summary delivery pipeline.

## Scope

| Item | Decision |
| --- | --- |
| Current batch | TB-1 through TB-5.5 |
| Default production format | Temporarily use `briefing` for `scheduled-notify` readability checks |
| New format selector | Add `--format briefing` to test and scheduled notification commands |
| Data basis | Previous business day's reports plus stored/available quote, KRX Open API index/market context, and investor-flow context |
| Default briefing stock count | Show top 5 stocks unless `--limit` or a safe setting explicitly overrides the item count |
| Blocked wording | No trading recommendation, buy/sell, strategy proposal, one-pick, or public numeric score wording. Observation-candidate wording is allowed only when it stays factual and read-only. |

## Briefing Shape

```text
국장 시작 전 리포트 브리핑 · 26.05.14
기준: 전일 리포트 / KRX 저장값은 항목별 기준일 표시

리포트 집중
- 반도체와반도체장비 00건
- 화장품 00건

지수 참고 · 26.05.13 KRX 저장값
- KOSPI 0,000.00 +0.00% / KOSDAQ 0,000.00 -0.00%

수급 참고 · 26.05.12 KOSPI 저장값 / 리포트일 전 최신
- 개인 매수 우위 0.0조 / 외국인 매도 우위 0.0조 / 기관 매도 우위 0.0조

핵심 포인트
- KOSPI 상승, KOSDAQ 보합권으로 시장 방향이 엇갈림
- 리포트 집중 1위: 반도체와반도체장비 00건

주요 종목
삼성전자(005930) | 현재가 000,000원 | 반도체와반도체장비
00건 | 대표증권사 외 N곳
목표가 000,000원 ~ 000,000원 | 매수

확인 포인트
- 리포트가 몰린 업종과 수급 방향이 같은지 확인
- 목표가 괴리율이 큰 종목은 웹뷰 관찰탭에서 세부 확인
```

## Implementation Stages

| Stage | Work | Completion |
| --- | --- | --- |
| TB-1 | Document this design | This file exists and is linked from current docs later if the format is adopted |
| TB-2 | Add formatter | Unit tests prove briefing sections, safe wording, split behavior |
| TB-3 | Add CLI option | `send-test-notification` and `scheduled-notify` accept `--format summary|briefing` |
| TB-4 | Dry-run verification | Dry-run prints briefing text without sending Telegram |
| TB-5 | Temporary scheduled default switch | `scheduled-notify` defaults to `briefing`; `send-test-notification` keeps `summary` by default |
| TB-5.5 | Stored flow reference | Briefing includes concise stored KOSPI investor-flow direction when KRX Data Marketplace rows exist |
| TB-6 | Stored index and core points | Briefing includes stored KRX KOSPI/KOSDAQ reference and neutral core-point sentences |

## Guardrails

- Keep `send-test-notification` default as `summary` for comparison.
- `scheduled-notify --format summary` remains available as a rollback path.
- Production `scheduled-notify` should run at `08:20`, after the official next-business-day `08:00` KRX Open API publication window and the `08:10` previous-business-day Open API fill.
- The top basis line should not imply that every KRX value has the same date as the report date. Each KRX section must carry its own stored reference date.
- Flow reference must show the stored flow date. If it is earlier than the report date, label it as `리포트일 전 최신`.
- Index reference must use stored KRX rows for the report business date only. Do not infer real-time market state.
- Core points must remain descriptive and neutral. Do not convert them into `전략 제안`.
- Keep Telegram parse mode as plain text first. HTML styling can be a later pass if needed.
- Use neutral copy: `확인 포인트`, `관찰`, `참고`.
- Do not produce `전략 제안`, `매수 기회`, `매수 추천`, `매도 추천`, public numeric `점수`, or `투자등급`. `오늘의 관찰 후보` and `우선 확인` are allowed only as observation-candidate labels.
