"""Evaluate fixed, manually labeled stored summaries without database/network access."""
import argparse
import hashlib
import json
from pathlib import Path

from stock_monitor.news.evidence_review import VERSION, _claims


def evaluate(sample):
    results = []
    for case in sample["cases"]:
        claims = [c for c in _claims(case["input"]) if c["field"] == "summary"]
        actual = {c["direction"] for c in claims} - {"UNKNOWN"}
        expected = set(case["expected_directions"])
        results.append(dict(case_id=case["case_id"], category=case["category"],
                            expected=sorted(expected), actual=sorted(actual),
                            false_positive=sorted(actual - expected), missed=sorted(expected - actual),
                            unknown_segments=sum(c["direction"] == "UNKNOWN" for c in claims), claims=claims))
    return dict(version=VERSION, cases=results,
                exact_matches=sum(not r["false_positive"] and not r["missed"] for r in results),
                false_positive_cases=sum(bool(r["false_positive"]) for r in results),
                missed_cases=sum(bool(r["missed"]) for r in results),
                all_unknown_cases=sum(not r["actual"] for r in results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("tests/fixtures/evidence_review_sample.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.sample.read_bytes()
    report = evaluate(json.loads(raw))
    report["sample_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False))
