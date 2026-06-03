"""Broker adapter public facade and runtime status helpers."""

from __future__ import annotations

from agentic_trader.config import Settings
from agentic_trader.engine.alpaca_adapter import AlpacaPaperBrokerAdapter
from agentic_trader.engine.broker_contracts import (
    BrokerAdapter,
    OrderOutcomeReader,
    ReadOnlyOrderOutcomeReader,
)
from agentic_trader.engine.broker_utils import (
    PAPER_BROKER_ACTIVE_MESSAGE,
    alpaca_credentials_ready,
    alpaca_uses_paper_endpoint,
    coerce_broker_float,
)
from agentic_trader.engine.paper_adapter import PaperBrokerAdapter
from agentic_trader.engine.simulated_adapter import SimulatedRealBrokerAdapter
from agentic_trader.execution.intent import BrokerHealthcheck
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.schemas import ExecutionBackend
from agentic_trader.storage.db import TradingDatabase


def _adapter_for_backend(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    """
    Selects and constructs the BrokerAdapter implementation corresponding to the configured execution backend.

    Parameters:
        db (TradingDatabase): Database used by the adapter for persistence and lookups.
        settings (Settings): Runtime settings containing `execution_backend` and related flags.

    Returns:
        BrokerAdapter: An adapter instance for the configured backend (`paper`, `simulated_real`, or `alpaca_paper`).

    Raises:
        RuntimeError: If `execution_backend` is `"live"` but `live_execution_enabled` is false.
        RuntimeError: If `execution_backend` is `"live"` and no live adapter has been implemented.
        RuntimeError: If `execution_backend` has an unsupported value.
    """
    if settings.execution_backend == "paper":
        return PaperBrokerAdapter(db, settings)
    if settings.execution_backend == "simulated_real":
        return SimulatedRealBrokerAdapter(db, settings)
    if settings.execution_backend == "alpaca_paper":
        return AlpacaPaperBrokerAdapter(db, settings)
    if settings.execution_backend == "live":
        if not settings.live_execution_enabled:
            raise RuntimeError(
                "Live execution backend was requested but live execution is disabled."
            )
        raise RuntimeError(
            "Live execution backend is configured but no live broker adapter is implemented yet."
        )
    raise RuntimeError(f"Unsupported execution backend: {settings.execution_backend}")


def get_broker_adapter(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    """
    Selects and returns the BrokerAdapter implementation appropriate for the configured execution backend.

    Determines the adapter from `settings.execution_backend` and constructs it using `db` and `settings`. If the global execution kill switch is enabled, this function raises an error to prevent any adapter that can submit orders from being created.

    Parameters:
        db: TradingDatabase used by the adapter for persistence and state lookups.
        settings: Settings that determine which execution backend to use and configure the adapter.

    Returns:
        A BrokerAdapter instance matching the configured execution backend.

    Raises:
        RuntimeError: If `settings.execution_kill_switch_active` is true, preventing adapter creation.
    """
    if settings.execution_kill_switch_active:
        raise RuntimeError(
            "Execution kill switch is active. No broker adapter may submit orders."
        )
    return _adapter_for_backend(db=db, settings=settings)


def get_broker_order_reader(
    *, db: TradingDatabase, settings: Settings
) -> OrderOutcomeReader:
    """
    Create a read-only order outcome reader for the configured execution backend.

    This constructs the appropriate backend adapter from the provided database and settings,
    then returns a wrapper that exposes only `get_order_outcome`, preventing access to mutating
    adapter methods.

    Returns:
        OrderOutcomeReader: An object that exposes `get_order_outcome(order_id, intent)` for the selected backend.
    """

    adapter = _adapter_for_backend(db=db, settings=settings)
    return ReadOnlyOrderOutcomeReader(adapter.get_order_outcome)


def _healthcheck_payload(settings: Settings) -> dict[str, object]:
    """
    Builds a broker healthcheck payload reflecting the configured execution backend and current settings.

    Parameters:
        settings (Settings): Application settings used to determine execution backend, kill switch state, Alpaca configuration, and related flags.

    Returns:
        dict[str, object]: A JSON-serializable dictionary representing the BrokerHealthcheck payload describing adapter name, execution backend, readiness flags, and a human-readable message.
    """
    backend: ExecutionBackend = settings.execution_backend
    if settings.execution_kill_switch_active:
        return BrokerHealthcheck(
            adapter_name=backend,
            execution_backend=backend,
            ok=False,
            blocked=True,
            simulated=backend == "simulated_real",
            live=backend == "live",
            message="Execution kill switch is active.",
        ).model_dump(mode="json")
    if backend == "paper":
        return BrokerHealthcheck(
            adapter_name="paper",
            execution_backend="paper",
            ok=True,
            message=PAPER_BROKER_ACTIVE_MESSAGE,
        ).model_dump(mode="json")
    if backend == "simulated_real":
        return BrokerHealthcheck(
            adapter_name="simulated_real",
            execution_backend="simulated_real",
            ok=True,
            simulated=True,
            message="Simulated-real broker scaffold is active; no live trading is enabled.",
        ).model_dump(mode="json")
    if backend == "alpaca_paper":
        blocked_reasons: list[str] = []
        if not settings.alpaca_paper_trading_enabled:
            blocked_reasons.append("explicit_enablement_missing")
        if not alpaca_credentials_ready(settings):
            blocked_reasons.append("credentials_missing")
        if not alpaca_uses_paper_endpoint(settings):
            blocked_reasons.append("paper_endpoint_missing")
        ok = not blocked_reasons
        return BrokerHealthcheck(
            adapter_name="alpaca_paper",
            execution_backend="alpaca_paper",
            ok=ok,
            blocked=not ok,
            message=(
                "Alpaca paper adapter is configured for paper trading."
                if ok
                else f"Alpaca paper adapter is blocked: {', '.join(blocked_reasons)}."
            ),
        ).model_dump(mode="json")
    live_message = (
        "Live backend requested but live execution is disabled."
        if not settings.live_execution_enabled
        else "Live backend requested but no live broker adapter is implemented yet."
    )
    return BrokerHealthcheck(
        adapter_name="live",
        execution_backend="live",
        ok=False,
        live=True,
        blocked=True,
        message=live_message,
    ).model_dump(mode="json")


def broker_runtime_payload(settings: Settings) -> dict[str, object]:
    """
    Produce a runtime status payload describing the configured broker backend, high-level readiness, and related Alpaca configuration flags.

    Parameters:
        settings (Settings): Application settings that determine execution backend, Alpaca configuration, kill switch, and related flags.

    Returns:
        dict[str, object]: A JSON-serializable dictionary containing runtime fields including:
          - "backend"/"adapter_name"/"execution_mode": configured execution backend identifier.
          - "simulated": `True` when using the simulated-real scaffold.
          - "live": `True` when a live backend was requested.
          - "external_paper": `True` when configured to use Alpaca paper.
          - Alpaca configuration flags: "alpaca_paper_trading_enabled", "alpaca_paper_endpoint", "alpaca_data_feed", "alpaca_credentials_configured".
          - "live_execution_enabled": whether live execution is permitted by settings.
          - "kill_switch_active": whether the execution kill switch is active.
          - "state": a short state token (e.g., "blocked", "paper", "simulated", "alpaca_paper_ready", "pending_live_adapter").
          - "message": a human-readable status message.
          - "live_requested": mirror of the requested live flag.
          - "live_ready": always `False` (no live adapter implemented).
          - "healthcheck": a broker healthcheck payload produced by _healthcheck_payload(settings).
    """
    backend: ExecutionBackend = settings.execution_backend
    live_requested = backend == "live"
    if settings.execution_kill_switch_active:
        state = "blocked"
        message = "Execution kill switch is active."
    elif backend == "paper":
        state = "paper"
        message = PAPER_BROKER_ACTIVE_MESSAGE
    elif backend == "simulated_real":
        state = "simulated"
        message = (
            "Simulated-real broker scaffold is active; live trading remains disabled."
        )
    elif backend == "alpaca_paper":
        healthcheck = _healthcheck_payload(settings)
        state = "alpaca_paper_ready" if healthcheck.get("ok") else "blocked"
        message = str(
            healthcheck.get("message", "Alpaca paper adapter status unknown.")
        )
    elif not settings.live_execution_enabled:
        state = "blocked"
        message = "Live backend requested but live execution is disabled."
    else:
        state = "pending_live_adapter"
        message = (
            "Live backend requested but no live broker adapter is implemented yet."
        )
    return {
        "backend": backend,
        "adapter_name": backend,
        "execution_mode": backend,
        "simulated": backend == "simulated_real",
        "live": live_requested,
        "external_paper": backend == "alpaca_paper",
        "alpaca_paper_trading_enabled": settings.alpaca_paper_trading_enabled,
        "alpaca_paper_endpoint": settings.alpaca_base_url,
        "alpaca_data_feed": settings.alpaca_data_feed,
        "alpaca_credentials_configured": alpaca_credentials_ready(settings),
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "state": state,
        "message": message,
        "live_requested": live_requested,
        "live_ready": False,
        "healthcheck": _healthcheck_payload(settings),
    }


__all__ = [
    "AlpacaPaperBrokerAdapter",
    "BrokerAdapter",
    "OrderOutcomeReader",
    "PaperBrokerAdapter",
    "SimulatedRealBrokerAdapter",
    "alpaca_credentials_ready",
    "alpaca_uses_paper_endpoint",
    "broker_runtime_payload",
    "coerce_broker_float",
    "get_broker_adapter",
    "get_broker_order_reader",
    "is_v1_us_equity_symbol",
]
