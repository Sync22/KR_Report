from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PUBLIC_DOC_PATTERNS = (
    re.compile(r"C:\\Users\\[^\\\s`]+|C:/Users/[^/\s`]+|/[cC]:/Users/[^/\s`]+|Users\\[^\\\s`]+"),
    re.compile(r"report\.kr-stock\.site"),
    re.compile(r"https?://(?:127\.0\.0\.1|localhost):\d+\b"),
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
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    root_docs = {
        Path("README.md"),
        Path("AGENTS.md"),
        Path("CHANGELOG.md"),
        Path("stock_research_monitor_mvp.md"),
    }
    docs: list[Path] = []
    for raw_path in result.stdout.splitlines():
        rel_path = Path(raw_path)
        if rel_path in root_docs or (
            rel_path.parts and rel_path.parts[0] == "docs" and rel_path.suffix == ".md"
        ):
            docs.append(ROOT / rel_path)
    return sorted(path for path in docs if path.exists())


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
