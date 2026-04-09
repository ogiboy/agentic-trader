import pytest

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    PaperBrokerAdapter,
    broker_runtime_payload,
    get_broker_adapter,
)
from agentic_trader.storage.db import TradingDatabase


def test_get_broker_adapter_returns_paper_adapter(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    adapter = get_broker_adapter(db=db, settings=settings)

    assert isinstance(adapter, PaperBrokerAdapter)
    assert adapter.backend_name == "paper"


def test_get_broker_adapter_blocks_live_backend_without_enablement(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=False,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    with pytest.raises(RuntimeError, match="live execution is disabled"):
        get_broker_adapter(db=db, settings=settings)


def test_get_broker_adapter_respects_kill_switch(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_kill_switch_active=True,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    with pytest.raises(RuntimeError, match="kill switch"):
        get_broker_adapter(db=db, settings=settings)


def test_broker_runtime_payload_reports_blocked_live_backend(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=False,
    )
    settings.ensure_directories()

    payload = broker_runtime_payload(settings)

    assert payload["backend"] == "live"
    assert payload["state"] == "blocked"
    assert payload["live_requested"] is True
