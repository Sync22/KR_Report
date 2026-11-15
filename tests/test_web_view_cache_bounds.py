import json
import threading
import urllib.parse
import urllib.request

from stock_monitor import cli
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository


def test_web_view_response_cache_evicts_oldest_search_key(tmp_path, monkeypatch) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    config.ensure_runtime_dirs()
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    built: list[str] = []

    def build_search(_config, _repository, *, business_date, query, limit):
        built.append(query)
        return {"business_date": business_date.isoformat(), "query": query, "limit": limit}

    monkeypatch.setattr(cli, "build_web_view_stock_search_snapshot", build_search)
    server = cli.create_web_view_server(config, repository, host="127.0.0.1", port=0, limit=5)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        for index in range(257):
            query = urllib.parse.urlencode({"date": "2026-05-08", "q": f"cache-key-{index}"})
            with urllib.request.urlopen(f"{base_url}/api/stocks/search?{query}", timeout=5) as response:
                json.loads(response.read().decode("utf-8"))

        query = urllib.parse.urlencode({"date": "2026-05-08", "q": "cache-key-0"})
        with urllib.request.urlopen(f"{base_url}/api/stocks/search?{query}", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert payload["query"] == "cache-key-0"
    assert len(built) == 258
    assert built[-1] == "cache-key-0"
