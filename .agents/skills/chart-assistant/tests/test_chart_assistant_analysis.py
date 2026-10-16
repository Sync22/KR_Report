import importlib.util
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SCRIPT = Path(__file__).parents[1] / "scripts" / "chart_assistant_snapshot.py"
SPEC = importlib.util.spec_from_file_location("chart_assistant_snapshot_analysis", SCRIPT)
assert SPEC and SPEC.loader
assistant = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assistant)


def chart_payload():
    return {
        "surface": "web-view-chart-explorer", "read_only": True, "writes_stock_monitor_db": False,
        "available": True, "requested_as_of": "2026-10-08", "symbol": "005930", "display_name": "삼성전자",
        "timeframe": "1d", "source": "Toss OpenAPI", "source_fetched_at": "2026-10-16T00:00:00Z",
        "source_date": "2026-10-08", "bar_status": "unknown", "adjusted": True, "currency": "KRW",
        "snapshot": {
            "barAsOf": "2026-10-08", "price": {"open": 70_000, "high": 71_000, "low": 69_000, "close": 70_500, "volume": 100_000},
            "indicators": {
                "movingAverages": {"sma20": 70_000, "sma60": 69_000, "sma120": None, "sma200": None, "ema20": None, "ema60": None, "ema120": None, "ema200": None, "wma20": None, "wma60": None, "wma120": None, "wma200": None, "status": "partial-data"},
                "rsi14": {"value": 52, "status": "ready"}, "macd129": {"macd": 1, "signal": 0.5, "histogram": 0.5, "status": "ready"},
                "atr14": {"value": 1_000, "status": "ready"}, "obv": {"value": 1_000_000, "delta5": 10_000, "status": "ready"},
                "volume": {"barVolume": 100_000, "ratio20": 1.1, "status": "ready"},
                "volumeProfile12": {"from": "2025-01-01", "to": "2026-10-08", "count": 100, "bins": []},
            }, "structures": [], "structureStatus": {"horizontal": "ready", "flag": "no-geometry", "triangle": "no-geometry"},
        },
    }


class ChartAssistantAnalysisTests(unittest.TestCase):
    def test_build_analysis_url_uses_local_chart_lab_and_bounded_filters(self):
        url = urlparse(assistant.build_analysis_url("2026-10-08", "005930", "1d", "2026-10-08", ["A", "F"], "any", 0.5))
        self.assertEqual((url.scheme, url.netloc, url.path), ("http", "127.0.0.1:3010", "/api/chart-lab/analysis"))
        self.assertEqual(parse_qs(url.query), {"date": ["2026-10-08"], "symbol": ["005930"], "timeframe": ["1d"], "asOf": ["2026-10-08"], "selected": ["A,F"], "mode": ["any"], "maxAtr": ["0.5"]})

    def test_build_analysis_url_rejects_invalid_strategy_or_cutoff(self):
        with self.assertRaises(ValueError):
            assistant.build_analysis_url("2026-10-08", "005930", "1d", selected=["BUY"])
        with self.assertRaises(ValueError):
            assistant.build_analysis_url("2026-10-08", "005930", "1d", as_of_bar="https://bad")

    def test_render_analysis_snapshot_preserves_unknown_finality_and_rule_state(self):
        payload = {
            "surface": "chart-lab-local", "read_only": True, "writes_stock_monitor_db": False,
            "chart": chart_payload(),
            "analysis": {
                "basis": "2026-10-08", "barCount": 200, "historical": True,
                "entry": {"status": "unconfirmed", "judgmentMode": "unknown", "label": "진입 판단 보류", "reason": "확정 봉 확인 불가", "setupDecision": {"label": "조건 충족", "reason": "F 조건 원신호"}, "rows": [{"id": "F", "name": "추세·거래량 돌파", "signal": "entry", "phase": "new", "readiness": {"ready": True, "missing": []}}]},
                "lowEntry": {"reviewStatus": "unconfirmed", "status": "unconfirmed", "label": "봉 확정 대기", "reason": "확정 기준 봉 미확인", "rows": [{"id": "R", "name": "저점 회복", "phase": "reclaimed", "label": "재시험 대기", "description": {"reason": "지지 재시험 대기"}}]},
                "patterns": [{"kind": "ascending-triangle", "status": "forming", "ruleVersion": "triangle-d-v2", "basis": {"startTime": "2026-09-01", "endTime": "2026-10-08"}, "measurements": {"heightAtr": 1.2}}],
            },
        }
        rendered = assistant.render_analysis_snapshot(payload)
        self.assertIn("봉 상태: unknown", rendered)
        self.assertIn("전략 조건", rendered)
        self.assertIn("확정 봉 확인 불가", rendered)
        self.assertIn("저점 회복", rendered)
        self.assertIn("상승 삼각형", rendered)
        self.assertIn("과거 기준", rendered)


if __name__ == "__main__":
    unittest.main()
