from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PUBLIC_DOC_PATTERNS = (
    re.compile(r"C:\\Users\\MING|C:/Users/MING|/[cC]:/Users/MING|Users\\MING"),
    re.compile(r"report\.kr-stock\.site"),
    re.compile(r"http://127\.0\.0\.1:8780"),
    re.compile(r"https://stock\.naver\.com/research/company"),
    re.compile(r"https://m\.stock\.naver\.com/research/company"),
    re.compile(r"https://data-dbg\.krx\.co\.kr"),
    re.compile(r"https://data\.krx\.co\.kr"),
    re.compile(r"login\.jsp\?site=mdc"),
    re.compile(r"bldAttendant/getJsonData"),
    re.compile(r"front-api"),
    re.compile(r"api/domestic"),
    re.compile(r"upjong/\{no\}"),
    re.compile(r"stock_monitor_\d{8}_\d{4}[-_A-Za-z0-9]*\.db"),
    re.compile(r"restore_smoke_\d{8}[-_A-Za-z0-9]*\.db"),
    re.compile(r"(?:AUTH_KEY|BOT_TOKEN|PASSWORD|ACCESS_CODE)[ \t]*=[ \t]*[^\s`]+"),
    re.compile(r"\d{5,}:[A-Za-z0-9_-]{20,}"),
)


def _public_docs() -> list[Path]:
    root_docs = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "CHANGELOG.md",
        ROOT / "stock_research_monitor_mvp.md",
    ]
    docs = sorted((ROOT / "docs").rglob("*.md"))
    return [path for path in root_docs + docs if path.exists()]


def test_public_docs_do_not_expose_local_operation_details() -> None:
    findings: list[str] = []
    for path in _public_docs():
        text = path.read_text(encoding="utf-8")
        for pattern in PUBLIC_DOC_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                rel_path = path.relative_to(ROOT).as_posix()
                findings.append(f"{rel_path}:{line_no}: {match.group(0)}")

    assert not findings, "\n".join(findings[:30])
