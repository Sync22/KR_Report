#!/usr/bin/env python3
"""Read one Stock Monitor Chart Explorer snapshot from the local GET API."""

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


BASE_URL = "http://127.0.0.1:3010"
TIMEFRAMES = {"1d", "1w", "4h", "1mo"}
SYMBOL_RE = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.^=_-]{0,23}$")
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
STATUS_LABELS = {
    "ready": "계산됨",
    "partial-data": "일부 계산 가능",
    "insufficient-data": "자료 부족",
    "unavailable": "계산 자료 없음",
    "no-geometry": "조건에 맞는 구조 없음",
}


def build_snapshot_url(as_of: str, symbol: str, timeframe: str) -> str:
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("기준일은 YYYY-MM-DD 형식이어야 합니다.") from None
    if not isinstance(symbol, str) or not SYMBOL_RE.fullmatch(symbol):
        raise ValueError("종목 코드는 지원되는 문자 형식이어야 합니다.")
    if timeframe not in TIMEFRAMES:
        raise ValueError("주기는 1d, 1w, 4h, 1mo 중 하나여야 합니다.")
    return f"{BASE_URL}/api/chart-explorer?{urlencode({'date': as_of, 'symbol': symbol, 'timeframe': timeframe})}"


def build_analysis_url(as_of: str, symbol: str, timeframe: str, as_of_bar=None, selected=None, mode="all", max_atr=0.5) -> str:
    build_snapshot_url(as_of, symbol, timeframe)
    strategies = ["F"] if selected is None else list(selected)
    if not 1 <= len(strategies) <= 4 or any(item not in {"A", "B", "C", "F"} for item in strategies) or len(set(strategies)) != len(strategies):
        raise ValueError("전략은 A, B, C, F 중 하나 이상 선택해야 합니다.")
    if mode not in {"all", "any"}:
        raise ValueError("조합 방식은 all 또는 any여야 합니다.")
    if isinstance(max_atr, bool) or not isinstance(max_atr, (int, float)) or not math.isfinite(max_atr) or not 0.1 <= max_atr <= 5:
        raise ValueError("추격 상한은 0.1~5 ATR 범위여야 합니다.")
    params = {"date": as_of, "symbol": symbol, "timeframe": timeframe, "selected": ",".join(strategies), "mode": mode, "maxAtr": str(max_atr)}
    if as_of_bar is not None:
        if not isinstance(as_of_bar, str) or len(as_of_bar) > 40:
            raise ValueError("기준 봉은 ISO 날짜 또는 시각이어야 합니다.")
        try:
            if date.fromisoformat(as_of_bar).isoformat() != as_of_bar:
                datetime.fromisoformat(as_of_bar.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("기준 봉은 ISO 날짜 또는 시각이어야 합니다.") from None
        params["asOf"] = as_of_bar
    return f"{BASE_URL}/api/chart-lab/analysis?{urlencode(params)}"


def _record(value):
    return value if isinstance(value, dict) else {}


def _text(value, limit=160):
    text = " ".join(str(value or "").split())[:limit]
    return text.replace("|", "\\|").replace("`", "\\`") or "자료 없음"


def _number(value, digits=4):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "자료 없음"
    return f"{value:,.{digits}f}".rstrip("0").rstrip(".") if digits else f"{value:,.0f}"


def _state(group):
    status = _text(_record(group).get("status"), 48)
    label = STATUS_LABELS.get(status, status)
    return f"{label} ({status})" if label != status else status


def _value_and_state(group, key="value"):
    item = _record(group)
    return f"{_number(item.get(key))} · {_state(item)}"


def render_snapshot(payload):
    if not isinstance(payload, dict) or payload.get("surface") != "web-view-chart-explorer" or payload.get("read_only") is not True or payload.get("writes_stock_monitor_db") is not False:
        raise ValueError("Chart Explorer 읽기 전용 응답이 아닙니다.")
    if payload.get("available") is not True:
        return "## 차트 자료 조회 불가\n\n- 상태: " + _text(payload.get("reason"), 80)

    snapshot = _record(payload.get("snapshot"))
    price = _record(snapshot.get("price"))
    indicators = _record(snapshot.get("indicators"))
    moving = _record(indicators.get("movingAverages"))
    currency = _text(payload.get("currency"), 8)
    lines = [
        f"## {_text(payload.get('display_name'))} ({_text(payload.get('symbol'), 24)}) · {_text(payload.get('timeframe'), 8)}",
        "",
        f"- 기준일: 요청 { _text(payload.get('requested_as_of'), 10) } · 실제 봉 { _text(snapshot.get('barAsOf'), 32) } · 제공처 기준일 { _text(payload.get('source_date'), 10) }",
        f"- 출처: {_text(payload.get('source'))} · 제공처 조회 시각 { _text(payload.get('source_fetched_at'), 40) }",
        f"- 봉 상태: {_text(payload.get('bar_status'), 20)} · 가격 조정: {'수정주가' if payload.get('adjusted') else '미조정 가격'} · 통화: {currency}",
        "",
        "### 기준 봉 값",
        f"- 시가 {_number(price.get('open'))} · 고가 {_number(price.get('high'))} · 저가 {_number(price.get('low'))} · 종가 {_number(price.get('close'))} {currency} · 거래량 {_number(price.get('volume'), 0)}",
        "",
        "### 지표 근거",
    ]
    close = price.get("close")
    for period in (20, 60, 120, 200):
        value = moving.get(f"sma{period}")
        relation = ""
        if isinstance(close, (int, float)) and not isinstance(close, bool) and isinstance(value, (int, float)) and not isinstance(value, bool):
            relation = " · 종가 위" if close > value else " · 종가 아래" if close < value else " · 종가와 같음"
        lines.append(f"- SMA {period}: {_number(value)} {currency}{relation} · {_state(moving)}")
    lines.extend([
        f"- RSI 14: {_value_and_state(indicators.get('rsi14'))}",
        f"- MACD / Signal / Histogram: {_number(_record(indicators.get('macd129')).get('macd'))} / {_number(_record(indicators.get('macd129')).get('signal'))} / {_number(_record(indicators.get('macd129')).get('histogram'))} · {_state(indicators.get('macd129'))}",
        f"- ATR 14: {_value_and_state(indicators.get('atr14'))}",
        f"- OBV / 5봉 변화: {_number(_record(indicators.get('obv')).get('value'), 0)} / {_number(_record(indicators.get('obv')).get('delta5'), 0)} · {_state(indicators.get('obv'))}",
        f"- 거래량 / 20봉 평균: {_number(_record(indicators.get('volume')).get('barVolume'), 0)} / {_number(_record(indicators.get('volume')).get('ratio20'), 2)}배 · {_state(indicators.get('volume'))}",
    ])

    profile = _record(indicators.get("volumeProfile12"))
    bins = [item for item in profile.get("bins", []) if isinstance(item, dict)] if isinstance(profile.get("bins"), list) else []
    bins.sort(key=lambda item: item.get("volume", 0) if isinstance(item.get("volume"), (int, float)) else 0, reverse=True)
    if bins:
        lines.extend(["", f"### 가격 구간 거래량 참고 · HLC3 추정 · { _text(profile.get('from'), 32) }–{ _text(profile.get('to'), 32) } · { _number(profile.get('count'), 0) }봉"])
        for item in bins[:3]:
            share = item.get("share")
            share_text = f"{share * 100:.1f}%" if isinstance(share, (int, float)) and not isinstance(share, bool) and math.isfinite(share) else "비중 자료 없음"
            lines.append(f"- {_number(item.get('low'))}–{_number(item.get('high'))} {currency} · 거래량 비중 {share_text}")
        lines.append("- 실제 체결별 매물 분포가 아닌 HLC3 기반 참고 추정입니다.")

    structures = snapshot.get("structures") if isinstance(snapshot.get("structures"), list) else []
    status = _record(snapshot.get("structureStatus"))
    lines.extend(["", "### 가격 구조 참고"])
    if structures:
        for item in structures[:8]:
            row = _record(item)
            measurements = row.get("measurements") if isinstance(row.get("measurements"), list) else []
            values = [f"{_text(_record(measurement).get('label'), 48)} {_text(_record(measurement).get('value'), 48)}" for measurement in measurements[:6]]
            lines.append(f"- {_text(row.get('family'), 20)} · {_text(row.get('status'), 20)} · 봉 {_text(row.get('barTime'), 32)}" + (" · " + " / ".join(values) if values else ""))
    else:
        lines.append("- 출력 구조 없음 · 수평 " + _state({"status": status.get("horizontal")}) + " · 깃대 " + _state({"status": status.get("flag")}) + " · 삼각 " + _state({"status": status.get("triangle")}))
    lines.extend(["", "출처와 기준 시점을 보존한 차트 참고 자료입니다. 매수·매도·주문 권고가 아닙니다. 지표 값을 채우려고 추가 시세 조회를 하지는 않았습니다."])
    return "\n".join(lines)


def render_analysis_snapshot(payload):
    if not isinstance(payload, dict) or payload.get("surface") != "chart-lab-local" or payload.get("read_only") is not True or payload.get("writes_stock_monitor_db") is not False:
        raise ValueError("Chart Lab 로컬 읽기 전용 응답이 아닙니다.")
    chart = _record(payload.get("chart"))
    analysis = _record(payload.get("analysis"))
    if not analysis:
        return render_snapshot(chart) if chart else "## Chart Lab 분석 불가\n\n- 상태: 자료 없음"

    lines = [render_snapshot(chart), "", "## 전략 조건 검토 · Stock-Newbby rules", ""]
    basis = _text(analysis.get("basis"), 40)
    historical = analysis.get("historical") is True
    entry = _record(analysis.get("entry"))
    mode = "모두 충족" if entry.get("mode") == "all" else "하나 이상"
    lines.append(f"- 분석 기준 봉: {basis} · {'과거 기준' if historical else '가장 최근 기준'} · 계산 봉 { _number(analysis.get('barCount'), 0) }개")
    lines.append(f"- A/B/C/F: { _text(entry.get('label'), 80) } · 확정 상태 {_text(entry.get('judgmentMode'), 24)} · 조합 {mode}")
    if entry.get("reason"):
        lines.append(f"- 최종 판정 사유: {_text(entry.get('reason'), 180)}")
    setup = _record(entry.get("setupDecision"))
    if setup:
        lines.append(f"- 원조건 계산: {_text(setup.get('label'), 80)} · {_text(setup.get('reason'), 180)}")
    for row in entry.get("rows", []) if isinstance(entry.get("rows"), list) else []:
        item = _record(row)
        readiness = _record(item.get("readiness"))
        missing = readiness.get("missing") if isinstance(readiness.get("missing"), list) else []
        missing_text = " · 누락 " + " / ".join(_text(value, 50) for value in missing[:5]) if missing else ""
        lines.append(f"- {_text(item.get('id'), 2)} {_text(item.get('name'), 60)} · 원신호 {_text(item.get('signal'), 20)} · 상태 {_text(item.get('phase'), 24)}{missing_text}")

    low = _record(analysis.get("lowEntry"))
    lines.extend(["", "## 저점 구조 · R/H", f"- {_text(low.get('label'), 80)} · 상태 {_text(low.get('reviewStatus'), 24)} · 기준 {_text(low.get('basis') or basis, 40)}"])
    if low.get("reason"):
        lines.append(f"- 확인 사유: {_text(low.get('reason'), 180)}")
    for row in low.get("rows", []) if isinstance(low.get("rows"), list) else []:
        item = _record(row)
        description = _record(item.get("description"))
        lines.append(f"- {_text(item.get('id'), 2)} {_text(item.get('name'), 60)} · {_text(item.get('label'), 80)} · {_text(description.get('reason'), 160)}")

    lines.extend(["", "## 패턴 기준과 과거 이력"])
    patterns = analysis.get("patterns") if isinstance(analysis.get("patterns"), list) else []
    label = {"bull-flag": "상승 깃대", "bear-flag": "하락 깃대", "ascending-triangle": "상승 삼각형", "descending-triangle": "하락 삼각형", "symmetrical-triangle": "대칭 삼각형", "support-breakout": "지지 이탈 관측", "resistance-breakout": "저항 돌파 관측", "diagnostic": "탐지 상태"}
    if patterns:
        for pattern in patterns[:12]:
            item = _record(pattern)
            basis_data = _record(item.get("basis"))
            measurements = _record(item.get("measurements"))
            evidence = " · ".join(f"{_text(key, 32)} {_text(value, 48)}" for key, value in list(measurements.items())[:4])
            kind = label.get(item.get("kind"), _text(item.get("kind"), 40))
            lines.append(f"- {kind} · {_text(item.get('status'), 32)} · {_text(basis_data.get('startTime'), 24)}–{_text(basis_data.get('endTime'), 24)} · {_text(item.get('ruleVersion'), 40)}" + (f" · {evidence}" if evidence else ""))
    else:
        lines.append("- 선택 기준 봉까지 탐지된 패턴이 없습니다. 없음은 반대 방향 신호가 아닙니다.")
    lines.extend(["", "결과는 출처가 표시된 차트 규칙 검토입니다. 알 수 없는 봉 확정 상태를 유지하며, 매매 지시·주문·수익성 주장이 아닙니다."])
    return "\n".join(lines)


def fetch_url(url: str):
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    with urlopen(request, timeout=20) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("차트 응답이 허용 크기를 넘었습니다.")
    return json.loads(body)


def fetch_snapshot(as_of: str, symbol: str, timeframe: str):
    return fetch_url(build_snapshot_url(as_of, symbol, timeframe))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="선택 기준일 YYYY-MM-DD")
    parser.add_argument("--symbol", required=True, help="국내 6자리 코드 또는 허용 Yahoo 티커")
    parser.add_argument("--timeframe", choices=sorted(TIMEFRAMES), default="1d")
    parser.add_argument("--analysis", action="store_true", help="전략·저점 구조·패턴 검토까지 포함")
    parser.add_argument("--as-of", help="과거 기준 봉 YYYY-MM-DD 또는 ISO 시각")
    parser.add_argument("--selected", default="F", help="선택 전략 조합 예: A,F")
    parser.add_argument("--mode", choices=["all", "any"], default="all")
    parser.add_argument("--max-atr", type=float, default=0.5)
    args = parser.parse_args()
    try:
        if args.analysis:
            payload = fetch_url(build_analysis_url(args.date, args.symbol, args.timeframe, args.as_of, args.selected.split(","), args.mode, args.max_atr))
            print(render_analysis_snapshot(payload))
        else:
            print(render_snapshot(fetch_snapshot(args.date, args.symbol, args.timeframe)))
    except HTTPError as error:
        print(f"차트 GET 요청이 HTTP {error.code}로 실패했습니다.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError):
        print("Next 미리보기 3010에 연결하지 못했습니다. 기존 서버 상태를 확인하세요.", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as error:
        print(f"차트 스냅샷을 처리하지 못했습니다: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
