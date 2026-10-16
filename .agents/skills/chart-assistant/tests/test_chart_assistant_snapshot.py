import importlib.util
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SCRIPT = Path(__file__).parents[1] / "scripts" / "chart_assistant_snapshot.py"
SPEC = importlib.util.spec_from_file_location("chart_assistant_snapshot", SCRIPT)
assert SPEC and SPEC.loader
chart_assistant = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chart_assistant)


class ChartAssistantSnapshotTests(unittest.TestCase):
    def test_build_snapshot_url_is_fixed_to_the_local_next_get_route(self):
        url = urlparse(chart_assistant.build_snapshot_url("2026-10-08", "005930", "1d"))
        self.assertEqual((url.scheme, url.netloc, url.path), ("http", "127.0.0.1:3010", "/api/chart-explorer"))
        self.assertEqual(parse_qs(url.query), {"date": ["2026-10-08"], "symbol": ["005930"], "timeframe": ["1d"]})

    def test_build_snapshot_url_rejects_unbounded_query_values(self):
        for args in [("2026-10-08", "https://bad", "1d"), ("2026-02-31", "005930", "1d"), ("2026-10-08", "005930", "1y")]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                chart_assistant.build_snapshot_url(*args)

    def test_render_snapshot_keeps_source_time_and_missing_indicator_states(self):
        payload = {
            "surface": "web-view-chart-explorer",
            "read_only": True,
            "writes_stock_monitor_db": False,
            "available": True,
            "requested_as_of": "2026-10-08",
            "symbol": "005930",
            "display_name": "삼성전자",
            "timeframe": "1d",
            "source": "Toss OpenAPI · adjusted daily candles",
            "source_fetched_at": "2026-10-16T05:20:00Z",
            "source_date": "2026-10-08",
            "bar_status": "unknown",
            "adjusted": True,
            "currency": "KRW",
            "snapshot": {
                "barAsOf": "2026-10-08",
                "price": {"open": 260000, "high": 263000, "low": 258000, "close": 262500, "volume": 123456},
                "indicators": {
                    "movingAverages": {"sma20": 267200, "sma60": 258225, "sma120": None, "sma200": None},
                    "rsi14": {"value": 53.2, "status": "ready"},
                    "macd129": {"macd": 1.25, "signal": 0.9, "histogram": 0.35, "status": "ready"},
                    "atr14": {"value": None, "status": "insufficient-data"},
                    "obv": {"value": 2500000, "delta5": -12000, "status": "ready"},
                    "volume": {"barVolume": 123456, "ratio20": 0.82, "status": "ready"},
                    "volumeProfile12": {
                        "from": "2023-01-01", "to": "2026-10-08", "count": 800,
                        "bins": [{"low": 250000, "high": 260000, "volume": 500000, "share": 0.25, "peak": True}],
                    },
                },
                "structures": [],
                "structureStatus": {"horizontal": "insufficient-data", "flag": "no-geometry", "triangle": "no-geometry"},
            },
        }
        text = chart_assistant.render_snapshot(payload)
        self.assertIn("Toss OpenAPI", text)
        self.assertIn("2026-10-16T05:20:00Z", text)
        self.assertIn("SMA 20", text)
        self.assertIn("ATR 14: 자료 없음 · 자료 부족 (insufficient-data)", text)
        self.assertIn("250,000–260,000 KRW · 거래량 비중 25.0%", text)
        self.assertIn("매수·매도·주문 권고가 아닙니다.", text)

    def test_render_snapshot_rejects_non_readonly_contract(self):
        with self.assertRaises(ValueError):
            chart_assistant.render_snapshot({"surface": "web-view-chart-explorer", "read_only": True, "writes_stock_monitor_db": True})


if __name__ == "__main__":
    unittest.main()
