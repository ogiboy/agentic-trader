import json
import threading
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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
    assert "financeOps" in dashboard
    assert "providerDiagnostics" in dashboard
    assert "v1Readiness" in dashboard

    status_code, broker = build_observer_api_payload(settings, path="/broker")
    assert status_code == 200
    assert broker["backend"] == "paper"

    status_code, finance_ops = build_observer_api_payload(settings, path="/finance-ops")
    assert status_code == 200
    assert finance_ops["backend"] == "paper"
    assert "checks" in finance_ops

    status_code, provider = build_observer_api_payload(
        settings, path="/provider-diagnostics"
    )
    assert status_code == 200
    market_data = cast(dict[str, object], provider["market_data"])
    assert market_data["selected_provider"] == "yahoo_market"

    status_code, readiness = build_observer_api_payload(settings, path="/v1-readiness")
    assert status_code == 200
    paper_operations = cast(dict[str, object], readiness["paper_operations"])
    assert paper_operations["allowed"] is False

    status_code, research = build_observer_api_payload(settings, path="/research")
    assert status_code == 200
    assert research["status"] == "disabled"
    assert "provider_health" in research

    status_code, supervisor = build_observer_api_payload(settings, path="/supervisor")
    assert status_code == 200
    assert "runtime_state" in supervisor
    assert "stdout_tail" in supervisor
    assert "stderr_tail" in supervisor


def test_observer_research_payload_does_not_create_database(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    status_code, research = build_observer_api_payload(settings, path="/research")

    assert status_code == 200
    assert research["status"] == "disabled"
    assert "provider_health" in research
    assert settings.database_path.exists() is False


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


def test_observer_api_rejects_nonlocal_bind_by_default() -> None:
    def resolver(path: str) -> tuple[int, dict[str, object]]:
        return 200, {"path": path}

    try:
        create_observer_server(host="0.0.0.0", port=0, resolver=resolver)
    except ValueError as exc:
        assert "local-only" in str(exc)
    else:
        raise AssertionError("non-loopback observer bind should be rejected")


def test_observer_api_supports_optional_local_token(tmp_path) -> None:
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
        token="observer-secret",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = server.server_address
    host = str(address[0])
    port = int(address[1])
    try:
        try:
            with urlopen(f"http://{host}:{port}/health", timeout=2):
                pass
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("observer token should be required")

        request = Request(
            f"http://{host}:{port}/health?ignored=true",
            headers={"X-Agentic-Trader-Observer-Token": "observer-secret"},
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = response.headers
        assert payload["ok"] is True
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
