import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "chart_assistant_control.py"
SPEC = importlib.util.spec_from_file_location("chart_assistant_control", SCRIPT)
assert SPEC and SPEC.loader
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


class ChartAssistantControlTests(unittest.TestCase):
    def test_monitor_status_url_is_fixed_to_loopback(self):
        self.assertEqual(control.monitor_status_url(), "http://127.0.0.1:3010/api/chart-lab/monitor")

    def test_mutations_use_same_origin_and_bounded_local_config(self):
        request = control.build_control_request("start")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Origin"), "http://127.0.0.1:3010")
        self.assertEqual(json.loads(request.data), {"action": "start"})
        configure = control.build_control_request("configure", ["005930=삼성전자", "000660=SK하이닉스"], ["000660"])
        self.assertEqual(json.loads(configure.data), {"action": "configure", "symbols": [
            {"symbol": "005930", "name": "삼성전자", "focus": False},
            {"symbol": "000660", "name": "SK하이닉스", "focus": True},
        ]})

    def test_mutations_reject_bad_limits_and_unknown_actions(self):
        with self.assertRaises(ValueError):
            control.build_control_request("start", ["SYM" + str(index) + "=x" for index in range(21)])
        with self.assertRaises(ValueError):
            control.build_control_request("configure", ["005930=삼성전자"], ["000660"])
        with self.assertRaises(ValueError):
            control.build_control_request("delete-db")

    def test_render_status_preserves_source_and_unknown_finality(self):
        text = control.render_status({"state": {
            "running": True, "startedAt": "2026-10-16T00:00:00Z", "lastPollAt": "2026-10-16T00:01:00Z", "lastError": None,
            "symbols": [{"symbol": "005930", "name": "삼성전자", "focus": True}],
            "events": [{"event_id": "event-1", "symbol": "005930", "name": "삼성전자", "kind": "ascending-triangle", "status": "forming", "basis_end_time": "2026-10-15", "source": "Yahoo Finance", "source_fetched_at": "2026-10-16T00:00:00Z", "bar_status": "unknown"}],
        }})
        self.assertIn("실행 중", text)
        self.assertIn("Yahoo Finance", text)
        self.assertIn("unknown", text)


if __name__ == "__main__":
    unittest.main()
