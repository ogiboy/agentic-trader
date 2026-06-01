"""Paper broker adapter implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentic_trader.config import Settings
from agentic_trader.engine.broker_utils import PAPER_BROKER_ACTIVE_MESSAGE
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
class PaperBrokerAdapter:
    db: TradingDatabase
    settings: Settings
    backend_name: str = "paper"
    _broker: PaperBroker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._broker = PaperBroker(self.db, self.settings)

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Submit the given execution intent to the paper broker after tagging it with this adapter and the paper execution backend.

        Parameters:
            intent (ExecutionIntent): The execution intent to place; a copy will be created with `adapter_name` set to this adapter's backend name and `execution_backend` set to "paper" before submission.

        Returns:
            ExecutionOutcome: The recorded outcome of the placed order.
        """
        return self._broker.place_order(
            intent.model_copy(
                update={
                    "adapter_name": self.backend_name,
                    "execution_backend": "paper",
                }
            )
        )

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Refreshes and returns the persisted ExecutionOutcome for a paper order after validating the stored execution record matches the provided order id.

        Parameters:
            order_id (str): The broker order identifier to match against the stored execution record.
            intent (ExecutionIntent): The execution intent whose intent_id is used to locate the persisted execution record.

        Returns:
            ExecutionOutcome: The outcome reconstructed from the persisted outcome payload.

        Raises:
            RuntimeError: If there is no execution record matching the intent and order_id, or if the persisted outcome payload is not a dictionary.
        """
        record = self.db.get_execution_record(intent.intent_id)
        if record is None or record.get("order_id") != order_id:
            raise RuntimeError("Paper order refresh has no matching execution record.")
        outcome_payload = record.get("outcome")
        if not isinstance(outcome_payload, dict):
            raise RuntimeError("Paper order refresh has no persisted outcome payload.")
        return ExecutionOutcome.model_validate(outcome_payload)

    def submit(self, decision: ExecutionDecision) -> str:
        """
        Submit an execution decision to the configured broker.

        Parameters:
            decision (ExecutionDecision): The execution decision describing the action to perform.

        Returns:
            str: Broker-provided identifier for the submitted execution (e.g., an order id or a unique token).
        """
        return self._broker.submit(decision)

    def cancel_order(self, order_id: str) -> bool:
        # Paper orders are immediate-fill/no-fill records, so there is nothing open to cancel.
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
            execution_backend="paper",
            ok=True,
            simulated=False,
            live=False,
            blocked=False,
            message=PAPER_BROKER_ACTIVE_MESSAGE,
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
