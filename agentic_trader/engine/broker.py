from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Protocol, cast

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.execution.intent import (
    BrokerHealthcheck,
    ExecutionIntent,
    ExecutionOutcome,
    OpenOrderSnapshot,
)
from agentic_trader.schemas import (
    ExecutionBackend,
    ExecutionDecision,
    PortfolioSnapshot,
    PositionExitDecision,
    PositionSnapshot,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase


class BrokerAdapter(Protocol):
    backend_name: str

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome: ...

    def cancel_order(self, order_id: str) -> bool: ...

    def get_positions(self) -> list[PositionSnapshot]: ...

    def get_account_state(self) -> PortfolioSnapshot: ...

    def get_open_orders(self) -> list[OpenOrderSnapshot]: ...

    def healthcheck(self) -> BrokerHealthcheck: ...

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None: ...

    def close_position(self, decision: PositionExitDecision) -> str: ...


@dataclass(slots=True)
class PaperBrokerAdapter:
    db: TradingDatabase
    settings: Settings
    backend_name: str = "paper"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        return self._broker.place_order(
            intent.model_copy(
                update={
                    "adapter_name": self.backend_name,
                    "execution_backend": "paper",
                }
            )
        )

    def submit(self, decision: ExecutionDecision) -> str:
        return self._broker.submit(decision)

    def cancel_order(self, order_id: str) -> bool:
        # Paper orders are immediate-fill/no-fill records, so there is nothing open to cancel.
        return False

    def get_positions(self) -> list[PositionSnapshot]:
        return self.db.list_positions()

    def get_account_state(self) -> PortfolioSnapshot:
        return self.db.get_account_snapshot()

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        return []

    def healthcheck(self) -> BrokerHealthcheck:
        return BrokerHealthcheck(
            adapter_name=self.backend_name,
            execution_backend="paper",
            ok=True,
            simulated=False,
            live=False,
            blocked=False,
            message="Paper broker adapter is active.",
        )

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        self._broker.record_position_plan(
            symbol=symbol,
            decision=decision,
            strategy=strategy,
            max_holding_bars=max_holding_bars,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        return self._broker.close_position(decision)


@dataclass(slots=True)
class SimulatedRealBrokerAdapter:
    """Non-live adapter scaffold that applies deterministic market-friction metadata."""

    db: TradingDatabase
    settings: Settings
    backend_name: str = "simulated_real"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def _simulation_metadata(self, intent: ExecutionIntent) -> dict[str, object]:
        return {
            "non_live": True,
            "simulated": True,
            "latency_ms": self.settings.simulated_latency_ms,
            "slippage_bps": self.settings.simulated_slippage_bps,
            "spread_bps": self.settings.simulated_spread_bps,
            "price_drift_bps": self.settings.simulated_price_drift_bps,
            "partial_fill_probability": self.settings.simulated_partial_fill_probability,
            "order_rejection_probability": self.settings.simulated_order_rejection_probability,
        }

    def _simulated_price(self, intent: ExecutionIntent, rng: random.Random) -> float:
        direction = 1.0 if intent.side == "buy" else -1.0
        drift_bps = rng.uniform(
            -self.settings.simulated_price_drift_bps,
            self.settings.simulated_price_drift_bps,
        )
        friction_bps = direction * (
            self.settings.simulated_slippage_bps
            + (self.settings.simulated_spread_bps / 2.0)
        )
        multiplier = 1.0 + ((friction_bps + drift_bps) / 10_000.0)
        return max(0.000001, intent.reference_price * multiplier)

    def _fill_ratio(self, rng: random.Random) -> float:
        if rng.random() >= self.settings.simulated_partial_fill_probability:
            return 1.0
        return rng.uniform(self.settings.simulated_partial_fill_min_ratio, 1.0)

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        rng = random.Random(intent.intent_id)
        metadata = self._simulation_metadata(intent)
        if (
            intent.approved
            and intent.side != "hold"
            and rng.random() < self.settings.simulated_order_rejection_probability
        ):
            rejected_intent = intent.model_copy(
                update={
                    "approved": False,
                    "adapter_name": self.backend_name,
                    "execution_backend": "simulated_real",
                    "thesis": f"Simulated-real rejection hook blocked the order. {intent.thesis}",
                }
            )
            outcome = self._broker.place_order(
                rejected_intent,
                order_prefix="simulated",
                simulated_metadata=metadata,
            )
            return outcome.model_copy(
                update={
                    "status": "rejected",
                    "adapter_name": self.backend_name,
                    "execution_backend": "simulated_real",
                    "rejection_reason": "simulated_rejection_hook",
                    "message": "Simulated-real adapter rejected the intent before fill.",
                    "simulated_metadata": metadata,
                }
            )

        fill_ratio = (
            self._fill_ratio(rng) if intent.approved and intent.side != "hold" else 1.0
        )
        simulated_intent = intent.model_copy(
            update={
                "adapter_name": self.backend_name,
                "execution_backend": "simulated_real",
                "reference_price": (
                    self._simulated_price(intent, rng)
                    if intent.side != "hold"
                    else intent.reference_price
                ),
                "quantity": (
                    intent.quantity * fill_ratio
                    if intent.quantity is not None
                    else None
                ),
                "notional": (
                    intent.notional * fill_ratio
                    if intent.notional is not None
                    else None
                ),
                "backend_metadata": {
                    **intent.backend_metadata,
                    "simulated_fill_ratio": fill_ratio,
                },
            }
        )
        metadata["fill_ratio"] = fill_ratio
        outcome = self._broker.place_order(
            simulated_intent,
            order_prefix="simulated",
            simulated_metadata=metadata,
        )
        if outcome.status == "filled" and fill_ratio < 1.0:
            return outcome.model_copy(
                update={
                    "status": "partially_filled",
                    "message": "Simulated-real adapter produced a partial fill.",
                    "simulated_metadata": metadata,
                }
            )
        return outcome.model_copy(update={"simulated_metadata": metadata})

    def cancel_order(self, order_id: str) -> bool:
        return False

    def get_positions(self) -> list[PositionSnapshot]:
        return self.db.list_positions()

    def get_account_state(self) -> PortfolioSnapshot:
        return self.db.get_account_snapshot()

    def get_open_orders(self) -> list[OpenOrderSnapshot]:
        return []

    def healthcheck(self) -> BrokerHealthcheck:
        return BrokerHealthcheck(
            adapter_name=self.backend_name,
            execution_backend="simulated_real",
            ok=True,
            simulated=True,
            live=False,
            blocked=False,
            message="Simulated-real broker scaffold is active; no live trading is enabled.",
        )

    def record_position_plan(
        self,
        *,
        symbol: str,
        decision: ExecutionDecision,
        strategy: StrategyPlan,
        max_holding_bars: int,
    ) -> None:
        self._broker.record_position_plan(
            symbol=symbol,
            decision=decision,
            strategy=strategy,
            max_holding_bars=max_holding_bars,
        )

    def close_position(self, decision: PositionExitDecision) -> str:
        return self._broker.close_position(decision)


def get_broker_adapter(*, db: TradingDatabase, settings: Settings) -> BrokerAdapter:
    if settings.execution_kill_switch_active:
        raise RuntimeError(
            "Execution kill switch is active. No broker adapter may submit orders."
        )
    if settings.execution_backend == "paper":
        return PaperBrokerAdapter(db, settings)
    if settings.execution_backend == "simulated_real":
        return SimulatedRealBrokerAdapter(db, settings)
    if settings.execution_backend == "live":
        if not settings.live_execution_enabled:
            raise RuntimeError(
                "Live execution backend was requested but live execution is disabled."
            )
        raise RuntimeError(
            "Live execution backend is configured but no live broker adapter is implemented yet."
        )
    raise RuntimeError(f"Unsupported execution backend: {settings.execution_backend}")


def _healthcheck_payload(settings: Settings) -> dict[str, object]:
    backend = cast(ExecutionBackend, settings.execution_backend)
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
            message="Paper broker adapter is active.",
        ).model_dump(mode="json")
    if backend == "simulated_real":
        return BrokerHealthcheck(
            adapter_name="simulated_real",
            execution_backend="simulated_real",
            ok=True,
            simulated=True,
            message="Simulated-real broker scaffold is active; no live trading is enabled.",
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
    backend = settings.execution_backend
    live_requested = backend == "live"
    if settings.execution_kill_switch_active:
        state = "blocked"
        message = "Execution kill switch is active."
    elif backend == "paper":
        state = "paper"
        message = "Paper broker adapter is active."
    elif backend == "simulated_real":
        state = "simulated"
        message = (
            "Simulated-real broker scaffold is active; live trading remains disabled."
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
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "state": state,
        "message": message,
        "live_requested": live_requested,
        "live_ready": False,
        "healthcheck": _healthcheck_payload(settings),
    }
