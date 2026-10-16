#!/usr/bin/env python3
"""Read or explicitly control the local Chart Lab pattern monitor."""

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


BASE_URL = "http://127.0.0.1:3010"
STATUS_URL = f"{BASE_URL}/api/chart-lab/monitor"
SYMBOL_RE = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.^=_-]{0,23}$")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def monitor_status_url():
    return STATUS_URL


def _watch_item(value):
    if not isinstance(value, str) or "=" not in value:
        raise ValueError("관심 종목은 종목코드=이름 형식이어야 합니다.")
    symbol, name = (part.strip() for part in value.split("=", 1))
    if not SYMBOL_RE.fullmatch(symbol) or not name or len(name) > 120 or any(ord(char) < 32 for char in name):
        raise ValueError("종목 코드나 이름 형식을 확인하세요.")
    return {"symbol": symbol, "name": name, "focus": False}


def build_control_request(action, watch=None, focus=None):
    watch = list(watch or [])
    focus = list(focus or [])
    if action in {"start", "pause"}:
        if watch or focus:
            raise ValueError("종목 목록 변경은 configure 명령을 사용하세요.")
        body = {"action": action}
    elif action == "configure":
        if not 1 <= len(watch) <= 20:
            raise ValueError("감시 종목은 1~20개여야 합니다.")
        if len(focus) > 3 or len(set(focus)) != len(focus):
            raise ValueError("집중 종목은 중복 없이 최대 3개여야 합니다.")
        symbols = [_watch_item(value) for value in watch]
        identities = [item["symbol"] for item in symbols]
        if len(set(identities)) != len(identities):
            raise ValueError("감시 종목에 중복 코드가 있습니다.")
        if any(not SYMBOL_RE.fullmatch(symbol) for symbol in focus) or any(symbol not in identities for symbol in focus):
            raise ValueError("집중 종목은 감시 목록 안에서 선택하세요.")
        for item in symbols:
            item["focus"] = item["symbol"] in focus
        body = {"action": action, "symbols": symbols}
    else:
        raise ValueError("명령은 status, events, configure, start, pause 중 하나여야 합니다.")
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(data) > 16 * 1024:
        raise ValueError("감시 설정 크기가 허용 범위를 넘었습니다.")
    return Request(STATUS_URL, data=data, headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
    }, method="POST")


def _text(value, limit=140):
    text = " ".join(str(value or "").split())[:limit]
    return text.replace("|", "\\|").replace("`", "\\`") or "자료 없음"


def _time(value):
    return _text(value, 40)


def render_status(payload, events_only=False, limit=20):
    if not isinstance(payload, dict) or not isinstance(payload.get("state"), dict):
        raise ValueError("감시 API 응답 형식이 아닙니다.")
    state = payload["state"]
    symbols = state.get("symbols") if isinstance(state.get("symbols"), list) else []
    events = state.get("events") if isinstance(state.get("events"), list) else []
    lines = [] if events_only else [
        "## Chart Lab 로컬 감시",
        "",
        f"- 상태: {'실행 중' if state.get('running') is True else '중지됨'} · 시작 {_time(state.get('startedAt'))} · 마지막 조회 {_time(state.get('lastPollAt'))}",
        f"- 주기: 일반 5분 · 집중 30초 · 다음 재시도/오류 {_text(state.get('lastError'), 120)}",
        "- 감시 종목: " + (" / ".join(f"{_text(item.get('name'), 40)} ({_text(item.get('symbol'), 24)}){' · 집중' if item.get('focus') is True else ''}" for item in symbols if isinstance(item, dict)) or "없음"),
        "",
        f"### 저장 사건 · {len(events)}개",
    ]
    if not events:
        lines.append("감지된 사건이 없습니다.")
    else:
        for event in reversed(events[-max(1, min(limit, 100)):]):
            if not isinstance(event, dict):
                continue
            lines.append(
                f"- {_text(event.get('name'), 50)} · {_text(event.get('kind'), 40)} · {_text(event.get('status'), 32)} · 기준 {_time(event.get('basis_end_time'))}"
            )
            lines.append(
                f"  출처 {_text(event.get('source'), 80)} · 조회 {_time(event.get('source_fetched_at'))} · 봉 상태 {_text(event.get('bar_status'), 20)} · 규칙 {_text(event.get('rule_version'), 48)}"
            )
    return "\n".join(lines)


def fetch_json(request):
    with urlopen(request, timeout=20) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("감시 응답이 허용 크기를 넘었습니다.")
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "events", "configure", "start", "pause"])
    parser.add_argument("--watch", action="append", default=[], help="configure 전용: 코드=이름, 최대 20회")
    parser.add_argument("--focus", action="append", default=[], help="configure 전용: 감시 종목 중 코드, 최대 3회")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    try:
        if args.command in {"status", "events"}:
            if args.watch or args.focus:
                raise ValueError("status/events에는 종목 목록을 지정하지 않습니다.")
            payload = fetch_json(Request(STATUS_URL, headers={"Accept": "application/json"}, method="GET"))
        else:
            payload = fetch_json(build_control_request(args.command, args.watch, args.focus))
            if "state" in payload and "intervals" not in payload:
                payload = {"state": payload["state"]}
        print(render_status(payload, events_only=args.command == "events", limit=args.limit))
    except HTTPError as error:
        print(f"로컬 감시 요청이 HTTP {error.code}로 실패했습니다.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError):
        print("Next 미리보기 3010에 연결하지 못했습니다. 기존 서버 상태를 확인하세요.", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as error:
        print(f"감시 요청을 처리하지 못했습니다: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
