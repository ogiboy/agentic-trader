import json
import threading
from urllib.request import urlopen

from agentic_trader.cli import build_observer_api_payload
from agentic_trader.config import Settings
from agentic_trader.observer_api import create_observer_server


def test_build_observer_api_payload_exposes_dashboard_and_broker(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    status_code, dashboard = build_observer_api_payload(
        settings, path="/dashboard", log_limit=5
    )
    assert status_code == 200
    assert "doctor" in dashboard
    assert "broker" in dashboard

    status_code, broker = build_observer_api_payload(settings, path="/broker")
    assert status_code == 200
    assert broker["backend"] == "paper"

    status_code, research = build_observer_api_payload(settings, path="/research")
    assert status_code == 200
    assert research["status"] == "disabled"
    assert "provider_health" in research


def test_observer_api_server_serves_local_http_payloads(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    server = create_observer_server(
        host="127.0.0.1",
        port=0,
        resolver=lambda path: build_observer_api_payload(
            settings, path=path, log_limit=5
        ),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = server.server_address
    host = str(address[0])
    port = int(address[1])
    try:
        with urlopen(f"http://{host}:{port}/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        assert "runtime" in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
