"""Runtime gates and position lifecycle helpers for service workflows."""

from __future__ import annotations

from agentic_trader.config import Settings
from agentic_trader.engine.broker import BrokerAdapter
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import stop_requested
from agentic_trader.schemas import LLMHealthStatus, RunArtifacts
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.system.runtime_tools import ensure_model_service_if_configured


def service_stop_requested(db: TradingDatabase) -> bool:
    """
    Check whether a stop of the service has been requested.

    Returns:
        True if a stop has been requested via settings or the persisted service state, False otherwise.
    """
    if stop_requested(db.settings):
        return True
    state = db.get_service_state()
    return bool(state and state.stop_requested)


def is_nonfatal_symbol_error(exc: Exception) -> bool:
    """
    Determine whether an exception represents a non-fatal symbol-level market-data error.

    Inspect the exception message and classify it as non-fatal when it indicates missing or incomplete market data.

    Parameters:
        exc (Exception): The exception whose message will be inspected.

    Returns:
        bool: `True` if the exception message describes symbol-scoped data absence, invalid market data, or lookback undercoverage; `False` otherwise.
    """
    message = str(exc)
    return (
        message.startswith("No market data returned for ")
        or message.startswith("Missing columns from market data:")
        or "coverage is too thin" in message
        or "Refusing to run agents" in message
    )


def manage_open_position(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    artifacts: RunArtifacts,
    cycle_count: int,
) -> str | None:
    """
    Close an open position for the given symbol when its position plan indicates an exit and record the closure.

    If a non-zero position and a corresponding position plan exist, increments the plan's holding bars, re-evaluates exit conditions against the latest plan and snapshot, and when an exit is required uses the broker to close the position and records a `position_closed` service event.

    Parameters:
        artifacts (RunArtifacts): Run artifacts containing the snapshot with the symbol to check.
        cycle_count (int): Current service cycle number to attach to the recorded event.

    Returns:
        str | None: The broker order id for the exit if a position was closed, `None` otherwise.
    """
    position = db.get_position(artifacts.snapshot.symbol)
    if position is None or position.quantity == 0:
        return None
    plan = db.get_position_plan(artifacts.snapshot.symbol)
    if plan is None:
        return None

    db.update_position_plan_holding(plan.symbol, plan.holding_bars + 1)
    refreshed_plan = db.get_position_plan(plan.symbol)
    if refreshed_plan is None:
        return None
    exit_decision = evaluate_position_exit(artifacts.snapshot, position, refreshed_plan)
    if not exit_decision.should_exit:
        return None

    exit_order_id = broker.close_position(exit_decision)
    db.insert_service_event(
        level="info",
        event_type="position_closed",
        message=f"{artifacts.snapshot.symbol} exited via {exit_decision.reason} with order {exit_order_id}.",
        cycle_count=cycle_count,
        symbol=artifacts.snapshot.symbol,
    )
    return exit_order_id


def ensure_llm_ready(settings: Settings) -> LLMHealthStatus:
    """
    Ensure the local LLM service is reachable, the required model is listed, and
    strict operation mode can complete a lightweight generation probe.

    Parameters:
        settings (Settings): Application settings. When `settings.runtime_mode == "operation"`, `settings.strict_llm` must be True.

    Returns:
        LLMHealthStatus: Health report returned by the local LLM.

    Raises:
        RuntimeError: If operation mode is configured without `strict_llm`, if the LLM service is not reachable (message provided by the health check), if `strict_llm` is True but the required model is unavailable, or if the generation probe fails.
    """
    if settings.runtime_mode == "operation" and not settings.strict_llm:
        raise RuntimeError("Operation mode requires strict LLM gating.")
    ensure_model_service_if_configured(settings)
    health = LocalLLM(settings).health_check(include_generation=settings.strict_llm)
    if not health.service_reachable:
        raise RuntimeError(health.message)
    if settings.strict_llm and not health.model_available:
        raise RuntimeError(health.message)
    if settings.strict_llm and health.generation_available is False:
        raise RuntimeError(health.message)
    return health
