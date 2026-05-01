import pytest

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    AlpacaPaperBrokerAdapter,
    PaperBrokerAdapter,
    broker_runtime_payload,
    get_broker_adapter,
)
from agentic_trader.execution.intent import ExecutionIntent
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


def test_get_broker_adapter_returns_alpaca_paper_adapter(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    adapter = get_broker_adapter(db=db, settings=settings)

    assert isinstance(adapter, AlpacaPaperBrokerAdapter)
    assert adapter.backend_name == "alpaca_paper"


def test_broker_runtime_payload_reports_alpaca_paper_blockers(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_paper_trading_enabled=False,
    )

    payload = broker_runtime_payload(settings)

    assert payload["backend"] == "alpaca_paper"
    assert payload["external_paper"] is True
    assert payload["state"] == "blocked"
    assert payload["alpaca_credentials_configured"] is False
    healthcheck = payload["healthcheck"]
    assert isinstance(healthcheck, dict)
    assert "explicit_enablement_missing" in healthcheck["message"]


def test_alpaca_paper_adapter_blocks_non_us_symbol_without_network(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_api_key="key",
        alpaca_secret_key="secret",
        alpaca_paper_trading_enabled=True,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = AlpacaPaperBrokerAdapter(db=db, settings=settings)
    intent = ExecutionIntent(
        symbol="AKBNK.IS",
        side="buy",
        notional=1000.0,
        reference_price=100.0,
        confidence=0.8,
        thesis="Unsupported regional symbol.",
        approved=True,
        execution_backend="alpaca_paper",
        adapter_name="alpaca_paper",
    )

    outcome = adapter.place_order(intent)

    assert outcome.status == "blocked"
    assert outcome.rejection_reason == "unsupported_symbol_scope"


def test_alpaca_paper_adapter_returns_rejected_outcome_on_api_error(tmp_path) -> None:
    class FailingClient:
        def submit_order(self, *, order_data):
            raise RuntimeError("paper api failed")

    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_api_key="key",
        alpaca_secret_key="secret",
        alpaca_paper_trading_enabled=True,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = AlpacaPaperBrokerAdapter(db=db, settings=settings)
    adapter._client = FailingClient()
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        notional=1000.0,
        reference_price=100.0,
        confidence=0.8,
        thesis="External paper submission.",
        approved=True,
        execution_backend="alpaca_paper",
        adapter_name="alpaca_paper",
    )

    outcome = adapter.place_order(intent)

    assert outcome.status == "rejected"
    assert outcome.rejection_reason == "alpaca_api_error"
    assert outcome.order_id is not None
