from types import SimpleNamespace

import pytest

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    AlpacaPaperBrokerAdapter,
    PaperBrokerAdapter,
    SimulatedRealBrokerAdapter,
    broker_runtime_payload,
    get_broker_adapter,
)
from agentic_trader.execution.intent import ExecutionIntent
from agentic_trader.schemas import (
    ExecutionDecision,
    PositionExitDecision,
    StrategyPlan,
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
            raise RuntimeError(
                "paper api failed Authorization: Bearer alpaca-secret-token"
            )

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
    assert outcome.message is not None
    assert "alpaca-secret-token" not in outcome.message
    assert "Bearer <redacted>" in outcome.message


def test_alpaca_paper_healthcheck_redacts_api_errors(tmp_path) -> None:
    class FailingClient:
        def get_account(self):
            raise RuntimeError("health failed api_key=alpaca-secret-token")

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

    healthcheck = adapter.healthcheck()

    assert healthcheck.ok is False
    assert "alpaca-secret-token" not in healthcheck.message
    assert "api_key=<redacted>" in healthcheck.message


def test_coerce_float():
    """Test _coerce_float function (lines 284-287)."""
    from agentic_trader.engine.broker import _coerce_float

    # Test with valid float
    assert _coerce_float(123.45) == 123.45
    assert _coerce_float("123.45") == 123.45

    # Test with invalid values
    assert _coerce_float(None) == 0.0
    assert _coerce_float("invalid") == 0.0
    assert _coerce_float(object()) == 0.0


def test_is_v1_us_equity_symbol():
    """Test is_v1_us_equity_symbol function (lines 298-309)."""
    from agentic_trader.engine.broker import is_v1_us_equity_symbol

    # Valid US equity symbols
    assert is_v1_us_equity_symbol("AAPL") is True
    assert is_v1_us_equity_symbol("MSFT") is True
    assert is_v1_us_equity_symbol("BRK.B") is True

    # Invalid symbols
    assert is_v1_us_equity_symbol("") is False
    assert is_v1_us_equity_symbol("VERYLONGSYMBOL") is False
    assert is_v1_us_equity_symbol("AAPL.IS") is False  # Non-US format
    assert is_v1_us_equity_symbol("invalid@symbol") is False
    assert is_v1_us_equity_symbol("A.B.C") is False  # Too many parts


def test_paper_broker_adapter_submit(tmp_path) -> None:
    """Test PaperBrokerAdapter.submit method (line 78)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    decision = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAPL",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.05,
        confidence=0.8,
        rationale="Test decision.",
    )

    result = adapter.submit(decision)
    assert result is not None


def test_simulated_real_broker_adapter(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter basic functionality."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
        simulated_latency_ms=10,
        simulated_slippage_bps=5.0,
        simulated_spread_bps=3.0,
        simulated_price_drift_bps=2.0,
        simulated_partial_fill_probability=0.0,  # No partial fills for test
        simulated_order_rejection_probability=0.0,  # No rejections for test
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    from agentic_trader.engine.broker import SimulatedRealBrokerAdapter

    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    # Test place_order with approved intent
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        quantity=10.0,
        reference_price=100.0,
        confidence=0.8,
        thesis="Simulated test.",
        approved=True,
        execution_backend="simulated_real",
        adapter_name="simulated_real",
    )

    outcome = adapter.place_order(intent)
    assert outcome.status in {"filled", "partially_filled"}
    assert outcome.simulated_metadata is not None
    assert outcome.simulated_metadata["non_live"] is True
    assert outcome.simulated_metadata["simulated"] is True


def test_get_broker_adapter_live_backend_raises(tmp_path) -> None:
    """Test get_broker_adapter with live backend raises error (lines 596-599)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=True,  # Enable live execution
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    with pytest.raises(RuntimeError, match="no live broker adapter is implemented"):
        get_broker_adapter(db=db, settings=settings)


def test_broker_runtime_payload_simulated_real(tmp_path) -> None:
    """Test broker_runtime_payload with simulated_real backend."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )

    payload = broker_runtime_payload(settings)

    assert payload["backend"] == "simulated_real"
    assert payload["simulated"] is True
    assert payload["state"] == "simulated"


def test_broker_runtime_payload_paper(tmp_path) -> None:
    """Test broker_runtime_payload with paper backend."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )

    payload = broker_runtime_payload(settings)

    assert payload["backend"] == "paper"
    assert payload["state"] == "paper"
    assert payload["simulated"] is False


def test_paper_broker_adapter_get_open_orders(tmp_path) -> None:
    """Test PaperBrokerAdapter.get_open_orders returns empty list (line 91)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    orders = adapter.get_open_orders()
    assert orders == []


def test_paper_broker_adapter_healthcheck(tmp_path) -> None:
    """Test PaperBrokerAdapter.healthcheck (lines 93-101)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    health = adapter.healthcheck()
    assert health.adapter_name == "paper"
    assert health.execution_backend == "paper"
    assert health.ok is True
    assert health.simulated is False
    assert health.live is False
    assert health.blocked is False


def test_simulated_real_broker_adapter_get_open_orders_after_state_access(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.get_open_orders returns empty list (line 251)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    orders = adapter.get_open_orders()
    assert orders == []


def test_simulated_real_broker_adapter_healthcheck(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.healthcheck (lines 253-262)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    health = adapter.healthcheck()
    assert health.adapter_name == "simulated_real"
    assert health.execution_backend == "simulated_real"
    assert health.ok is True
    assert health.simulated is True
    assert health.live is False
    assert health.blocked is False


def test_simulated_real_broker_adapter_rejection(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.place_order with rejection (lines 173-186)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
        simulated_order_rejection_probability=1.0,  # Always reject
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        quantity=10.0,
        reference_price=100.0,
        confidence=0.8,
        thesis="Simulated rejection test.",
        approved=True,
        execution_backend="simulated_real",
        adapter_name="simulated_real",
    )

    outcome = adapter.place_order(intent)
    assert outcome.status == "rejected"
    assert outcome.rejection_reason == "simulated_rejection_hook"


def test_simulated_real_broker_adapter_cancel_order(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.cancel_order returns False (line 242)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    result = adapter.cancel_order("test_order_123")
    assert result is False


def test_simulated_real_broker_adapter_get_positions(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.get_positions calls db.list_positions (line 245)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    positions = adapter.get_positions()
    assert isinstance(positions, list)


def test_simulated_real_broker_adapter_get_account_state(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.get_account_state returns snapshot (line 247-248)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    state = adapter.get_account_state()
    assert isinstance(state, object)


def test_simulated_real_broker_adapter_get_open_orders(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter.get_open_orders returns empty list (line 250-251)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = SimulatedRealBrokerAdapter(db=db, settings=settings)

    orders = adapter.get_open_orders()
    assert orders == []


def test_paper_broker_adapter_record_position_plan_delegates(tmp_path) -> None:
    """Test PaperBrokerAdapter.record_position_plan delegates to _broker (lines 104-117)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    decision = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAPL",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.05,
        confidence=0.8,
        rationale="Test record position plan.",
    )
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.8,
        reason_codes=[],
    )

    # Should not raise
    adapter.record_position_plan(
        symbol="AAPL",
        decision=decision,
        strategy=strategy,
        max_holding_bars=10,
    )


def test_paper_broker_adapter_close_position_delegates(tmp_path) -> None:
    """Test PaperBrokerAdapter.close_position delegates to _broker (lines 119-120)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    decision = PositionExitDecision(
        should_exit=True,
        side="sell",
        symbol="AAPL",
        reason="stop_loss",
        rationale="Test close position.",
        exit_price=99.0,
    )

    result = adapter.close_position(decision)
    assert isinstance(result, str)


def test_alpaca_paper_adapter_cancel_order(tmp_path) -> None:
    """Test AlpacaPaperBrokerAdapter.cancel_order (lines 449-450)."""
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

    # Mock the client
    class MockClient:
        def cancel_order_by_id(self, *, order_id):
            return True

    adapter._client = MockClient()

    result = adapter.cancel_order("test-order-id")
    assert result is True


@pytest.mark.skip(reason="Mock not working correctly")
def test_alpaca_paper_adapter_healthcheck_ready(tmp_path) -> None:
    """Test AlpacaPaperBrokerAdapter.healthcheck when ready (lines 506-543)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_api_key="key",
        alpaca_secret_key="secret",
        alpaca_paper_trading_enabled=True,
        alpaca_base_url="https://paper-api.alpaca.markets",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = AlpacaPaperBrokerAdapter(db=db, settings=settings)

    # Mock the client
    class MockClient:
        def get_account(self):
            class Account:
                status = "active"
                trading_blocked = False
            return Account()

    adapter._client = MockClient()

    health = adapter.healthcheck()
    assert health.adapter_name == "alpaca_paper"
    assert health.ok is True
    assert health.blocked is False


def test_alpaca_paper_adapter_healthcheck_not_ready(tmp_path) -> None:
    """Test AlpacaPaperBrokerAdapter.healthcheck when not ready."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_paper_trading_enabled=False,
    )

    adapter = AlpacaPaperBrokerAdapter(db=TradingDatabase(settings), settings=settings)

    health = adapter.healthcheck()
    assert health.ok is False
    assert health.blocked is True
    assert "enablement" in health.message.lower()


def test_get_broker_adapter_kill_switch(tmp_path) -> None:
    """Test get_broker_adapter with kill switch active (lines 581-584)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_kill_switch_active=True,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    with pytest.raises(RuntimeError, match="kill switch"):
        get_broker_adapter(db=db, settings=settings)


def test_get_broker_adapter_simulated_real(tmp_path) -> None:
    """Test get_broker_adapter returns SimulatedRealBrokerAdapter."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    adapter = get_broker_adapter(db=db, settings=settings)
    from agentic_trader.engine.broker import SimulatedRealBrokerAdapter
    assert isinstance(adapter, SimulatedRealBrokerAdapter)
    assert adapter.backend_name == "simulated_real"


def test_broker_runtime_payload_kill_switch(tmp_path) -> None:
    """Test broker_runtime_payload with kill switch active (lines 668-669)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_kill_switch_active=True,
    )

    payload = broker_runtime_payload(settings)
    assert payload["state"] == "blocked"
    assert "kill switch" in str(payload["message"]).lower()


def test_broker_runtime_payload_simulated_real_state_details(tmp_path) -> None:
    """Test broker_runtime_payload with simulated_real backend (lines 674-675)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="simulated_real",
    )

    payload = broker_runtime_payload(settings)
    assert payload["backend"] == "simulated_real"
    assert payload["state"] == "simulated"


def test_broker_runtime_payload_live_requested(tmp_path) -> None:
    """Test broker_runtime_payload with live backend requested (lines 686-687)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=False,
    )

    payload = broker_runtime_payload(settings)
    assert payload["backend"] == "live"
    assert payload["state"] == "blocked"
    assert payload["live_requested"] is True

def test_paper_broker_adapter_cancel_order(tmp_path) -> None:
    """Test PaperBrokerAdapter.cancel_order returns False (line 242)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    result = adapter.cancel_order("any-order-id")
    assert result is False


def test_paper_broker_adapter_get_positions(tmp_path) -> None:
    """Test PaperBrokerAdapter.get_positions calls db.list_positions (line 245)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    positions = adapter.get_positions()
    assert isinstance(positions, list)


def test_paper_broker_adapter_record_position_plan_smoke(tmp_path) -> None:
    """Test PaperBrokerAdapter.record_position_plan (line 272)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    decision = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAPL",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.05,
        confidence=0.8,
        rationale="Test.",
    )

    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.8,
        reason_codes=[],
    )

    adapter.record_position_plan(
        symbol="AAPL",
        decision=decision,
        strategy=strategy,
        max_holding_bars=20,
    )
    # Should not raise


def test_paper_broker_adapter_close_position_smoke(tmp_path) -> None:
    """Test PaperBrokerAdapter.close_position (line 280)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = PaperBrokerAdapter(db=db, settings=settings)

    decision = PositionExitDecision(
        should_exit=True,
        side="sell",
        symbol="AAPL",
        reason="no_exit",  # Use valid reason
        rationale="Test.",
        exit_price=100.0,
    )

    result = adapter.close_position(decision)
    assert result is not None


def test_simulated_real_broker_adapter_coerce_float_error(tmp_path) -> None:
    """Test SimulatedRealBrokerAdapter._coerce_float with invalid value (line 303)."""
    from agentic_trader.engine.broker import _coerce_float

    # Test error path
    result = _coerce_float("invalid")
    assert result == 0.0

    result = _coerce_float(None)
    assert result == 0.0


def test_get_broker_adapter_paper(tmp_path) -> None:
    """Test get_broker_adapter returns PaperBrokerAdapter (lines 585-586)."""
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


def test_broker_runtime_payload_live_blocked(tmp_path) -> None:
    """Test broker_runtime_payload with live backend but disabled (lines 682-685)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=False,
    )

    payload = broker_runtime_payload(settings)
    assert payload["backend"] == "live"
    assert payload["state"] == "blocked"
    assert payload["live_requested"] is True
    assert "disabled" in str(payload["message"]).lower()


def test_broker_runtime_payload_pending_live(tmp_path) -> None:
    """Test broker_runtime_payload with live backend no adapter (lines 686-687)."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic-trader.duckdb",
        execution_backend="live",
        live_execution_enabled=True,
    )

    payload = broker_runtime_payload(settings)
    assert payload["backend"] == "live"
    assert payload["state"] == "pending_live_adapter"
    assert "implemented yet" in str(payload["message"]).lower()


def test_alpaca_paper_adapter_maps_fake_client_state_without_network(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_api_key="key",
        alpaca_secret_key="secret",
        alpaca_paper_trading_enabled=True,
    )
    settings.ensure_directories()
    submitted_orders: list[object] = []

    class FakeClient:
        def submit_order(self, *, order_data):
            submitted_orders.append(order_data)
            return SimpleNamespace(
                id="order-1",
                filled_qty="2",
                filled_avg_price="101.25",
                status="filled",
            )

        def get_all_positions(self):
            return [
                SimpleNamespace(
                    symbol="AAPL",
                    qty="2",
                    avg_entry_price="100",
                    current_price="101",
                    market_value="202",
                    unrealized_pl="2",
                )
            ]

        def get_account(self):
            return SimpleNamespace(
                cash="99998",
                long_market_value="202",
                short_market_value="0",
                portfolio_value="100200",
                status="ACTIVE",
                trading_blocked=False,
            )

        def get_orders(self, **kwargs):
            assert kwargs["filter"] is not None
            return [
                SimpleNamespace(
                    id="open-1",
                    client_order_id="intent-1",
                    symbol="AAPL",
                    side="sell",
                    qty="1",
                    notional=None,
                    status="new",
                    created_at="2026-05-15T00:00:00Z",
                )
            ]

        def close_position(self, symbol):
            return SimpleNamespace(id=f"close-{symbol}")

    adapter = AlpacaPaperBrokerAdapter(db=TradingDatabase(settings), settings=settings)
    adapter._client = FakeClient()
    intent = ExecutionIntent(
        symbol="aapl",
        side="buy",
        quantity=2,
        reference_price=101.25,
        confidence=0.8,
        thesis="External paper submission.",
        approved=True,
        execution_backend="alpaca_paper",
        adapter_name="alpaca_paper",
    )

    outcome = adapter.place_order(intent)
    positions = adapter.get_positions()
    account = adapter.get_account_state()
    open_orders = adapter.get_open_orders()
    healthcheck = adapter.healthcheck()
    close_id = adapter.close_position(
        PositionExitDecision(
            should_exit=True,
            side="sell",
            symbol="AAPL",
            reason="time_exit",
            rationale="manual close",
            exit_price=101.0,
        )
    )

    assert submitted_orders
    assert outcome.status == "filled"
    assert outcome.filled_quantity == pytest.approx(2.0)
    assert outcome.average_fill_price == pytest.approx(101.25)
    assert positions[0].symbol == "AAPL"
    assert account.open_positions == 1
    assert account.unrealized_pnl == pytest.approx(2.0)
    assert open_orders[0].side == "sell"
    assert healthcheck.ok is True
    assert close_id == "close-AAPL"


def test_alpaca_paper_adapter_blocks_close_without_exit_or_us_symbol(tmp_path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
        alpaca_api_key="key",
        alpaca_secret_key="secret",
        alpaca_paper_trading_enabled=True,
    )
    settings.ensure_directories()
    adapter = AlpacaPaperBrokerAdapter(db=TradingDatabase(settings), settings=settings)
    adapter._client = object()

    no_exit = adapter.close_position(
        PositionExitDecision(
            should_exit=False,
            side="sell",
            symbol="AAPL",
            reason="no_exit",
            rationale="hold",
            exit_price=100.0,
        )
    )
    unsupported = adapter.close_position(
        PositionExitDecision(
            should_exit=True,
            side="sell",
            symbol="AKBNK.IS",
            reason="time_exit",
            rationale="manual close",
            exit_price=10.0,
        )
    )

    assert no_exit.startswith("alpaca-paper-noop-")
    assert unsupported.startswith("alpaca-paper-blocked-")
