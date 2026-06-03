"""Deterministic simulated-real broker adapter implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_trader.config import Settings
from agentic_trader.engine.broker_utils import (
    deterministic_uniform,
    deterministic_unit_interval,
)
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.execution.intent import (
    BrokerHealthcheck,
    ExecutionIntent,
    ExecutionOutcome,
    OpenOrderSnapshot,
)
from agentic_trader.schemas import (
    ExecutionDecision,
    PortfolioSnapshot,
    PositionExitDecision,
    PositionSnapshot,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase


@dataclass(slots=True)
class SimulatedRealBrokerAdapter:
    """Non-live adapter scaffold that applies deterministic market-friction metadata."""

    db: TradingDatabase
    settings: Settings
    backend_name: str = "simulated_real"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def _simulation_metadata(self) -> dict[str, object]:
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

    def _simulated_price(self, intent: ExecutionIntent) -> float:
        direction = 1.0 if intent.side == "buy" else -1.0
        drift_bps = deterministic_uniform(
            intent.intent_id,
            "price_drift_bps",
            -self.settings.simulated_price_drift_bps,
            self.settings.simulated_price_drift_bps,
        )
        friction_bps = direction * (
            self.settings.simulated_slippage_bps
            + (self.settings.simulated_spread_bps / 2.0)
        )
        multiplier = 1.0 + ((friction_bps + drift_bps) / 10_000.0)
        return max(0.000001, intent.reference_price * multiplier)

    def _fill_ratio(self, intent: ExecutionIntent) -> float:
        if (
            deterministic_unit_interval(intent.intent_id, "partial_fill_gate")
            >= self.settings.simulated_partial_fill_probability
        ):
            return 1.0
        return deterministic_uniform(
            intent.intent_id,
            "partial_fill_ratio",
            self.settings.simulated_partial_fill_min_ratio,
            1.0,
        )

    def _should_reject_order(self, intent: ExecutionIntent) -> bool:
        return (
            intent.approved
            and intent.side != "hold"
            and deterministic_unit_interval(intent.intent_id, "order_rejection")
            < self.settings.simulated_order_rejection_probability
        )

    def _rejected_outcome(
        self,
        intent: ExecutionIntent,
        metadata: dict[str, object],
    ) -> ExecutionOutcome:
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

    def _simulated_intent(
        self,
        intent: ExecutionIntent,
        fill_ratio: float,
    ) -> ExecutionIntent:
        return intent.model_copy(
            update={
                "adapter_name": self.backend_name,
                "execution_backend": "simulated_real",
                "reference_price": (
                    self._simulated_price(intent)
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

    @staticmethod
    def _simulated_outcome(
        outcome: ExecutionOutcome,
        *,
        fill_ratio: float,
        metadata: dict[str, object],
    ) -> ExecutionOutcome:
        if outcome.status == "filled" and fill_ratio < 1.0:
            return outcome.model_copy(
                update={
                    "status": "partially_filled",
                    "message": "Simulated-real adapter produced a partial fill.",
                    "simulated_metadata": metadata,
                }
            )
        return outcome.model_copy(update={"simulated_metadata": metadata})

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Simulates placing an order using deterministic market-friction rules and returns the resulting execution outcome.

        The method either:
        - triggers a deterministic rejection hook (when the intent is approved and not a "hold") and returns an outcome with status `"rejected"` and `rejection_reason` set to `"simulated_rejection_hook"`, or
        - computes a deterministic fill ratio and simulated execution price, submits a modified intent to the underlying paper broker, and returns the broker outcome augmented with `simulated_metadata`. If the broker reports `"filled"` but the simulated fill ratio is less than 1.0, the returned outcome is converted to `"partially_filled"`.

        Parameters:
            intent (ExecutionIntent): The execution intent to simulate; approval state, side, quantity/notional, and reference_price influence rejection gating and simulated fill behavior.

        Returns:
            ExecutionOutcome: The execution outcome representing the simulated submission, including `simulated_metadata` describing the deterministic simulation parameters and, when applicable, `rejection_reason` or a `"partially_filled"` status.
        """
        metadata = self._simulation_metadata()
        if self._should_reject_order(intent):
            return self._rejected_outcome(intent, metadata)

        fill_ratio = (
            self._fill_ratio(intent)
            if intent.approved and intent.side != "hold"
            else 1.0
        )
        metadata["fill_ratio"] = fill_ratio
        outcome = self._broker.place_order(
            self._simulated_intent(intent, fill_ratio),
            order_prefix="simulated",
            simulated_metadata=metadata,
        )
        return self._simulated_outcome(
            outcome,
            fill_ratio=fill_ratio,
            metadata=metadata,
        )

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Refresh an execution outcome by loading and validating the persisted execution record for the given intent.

        Loads the execution record for intent.intent_id from the trading database and returns an ExecutionOutcome built from the stored outcome payload.

        Returns:
            ExecutionOutcome: The outcome reconstructed from the persisted outcome payload.

        Raises:
            RuntimeError: If no execution record exists for the intent or the record's order_id does not match `order_id`.
            RuntimeError: If the persisted outcome payload is missing or not a dictionary.
        """
        record = self.db.get_execution_record(intent.intent_id)
        if record is None or record.get("order_id") != order_id:
            raise RuntimeError(
                "Simulated-real order refresh has no matching execution record."
            )
        outcome_payload = record.get("outcome")
        if not isinstance(outcome_payload, dict):
            raise RuntimeError(
                "Simulated-real order refresh has no persisted outcome payload."
            )
        return ExecutionOutcome.model_validate(outcome_payload)

    def cancel_order(self, order_id: str) -> bool:
        """
        Check whether an open order with the given order_id exists.

        Parameters:
            order_id (str): Broker order identifier to search for.

        Returns:
            `True` if an open order with `order_id` exists, `False` otherwise.
        """
        return any(order.order_id == order_id for order in self.get_open_orders())

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
