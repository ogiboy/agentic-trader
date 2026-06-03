"""Broker adapter contracts and read-only wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

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


class BrokerAdapter(Protocol):
    backend_name: str

    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome:
        """
        Submit an execution intent and return the broker outcome.

        Parameters:
            intent: Order intent containing symbol, side, sizing, pricing, and execution metadata.

        Returns:
            Snapshot of the accepted, filled, rejected, cancelled, blocked, or no-fill order state.
        """
        ...

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetch the latest execution outcome for a previously submitted order.

        Parameters:
            order_id: Broker-assigned identifier for the order to refresh.
            intent: Original execution intent used as lookup context.

        Returns:
            ExecutionOutcome: The canonical execution outcome record for the given order and intent.
        """
        ...

    def cancel_order(self, order_id: str) -> bool:
        """
        Attempt to cancel an order by its identifier.

        Parameters:
            order_id: Broker-specific order identifier to cancel.

        Returns:
            True when the order was successfully cancelled, otherwise false.
        """
        ...

    def get_positions(self) -> list[PositionSnapshot]:
        """
        Return current account position snapshots.

        Returns:
            Current position snapshots, or an empty list when there are no positions.
        """
        ...

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

    def close_position(self, decision: PositionExitDecision) -> str:
        """
        Perform a requested position exit and return the close-action identifier.

        Parameters:
            decision: Exit decision containing the symbol and whether an exit is required.

        Returns:
            No-op, blocked, broker-provided, or fallback identifier for the close action.
        """
        ...


class OrderOutcomeReader(Protocol):
    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetch the latest execution outcome for a previously submitted order.

        Parameters:
            order_id: Broker-assigned identifier for the order to refresh.
            intent: Original execution intent used as lookup context.

        Returns:
            ExecutionOutcome: The canonical execution outcome record for the given order and intent.
        """
        ...


@dataclass(slots=True)
class ReadOnlyOrderOutcomeReader:
    _get_order_outcome: Callable[..., ExecutionOutcome]

    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome:
        """
        Fetches the latest execution outcome for the specified order and intent.

        Parameters:
            order_id (str): Broker order identifier to refresh.
            intent (ExecutionIntent): The original execution intent associated with the order.

        Returns:
            ExecutionOutcome: The persisted or refreshed execution outcome for the specified order.
        """
        return self._get_order_outcome(order_id=order_id, intent=intent)
