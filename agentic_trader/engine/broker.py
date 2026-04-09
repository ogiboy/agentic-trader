from dataclasses import dataclass, field
from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.schemas import ExecutionDecision, PositionExitDecision, StrategyPlan
from agentic_trader.storage.db import TradingDatabase


class BrokerAdapter(Protocol):
    backend_name: str

    def submit(self, decision: ExecutionDecision) -> str: ...

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

    def submit(self, decision: ExecutionDecision) -> str:
        return self._broker.submit(decision)

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
    if not settings.live_execution_enabled:
        raise RuntimeError(
            "Live execution backend was requested but live execution is disabled."
        )
    raise RuntimeError(
        "Live execution backend is configured but no live broker adapter is implemented yet."
    )


def broker_runtime_payload(settings: Settings) -> dict[str, object]:
    backend = settings.execution_backend
    live_requested = backend == "live"
    live_ready = live_requested and settings.live_execution_enabled
    if settings.execution_kill_switch_active:
        state = "blocked"
        message = "Execution kill switch is active."
    elif backend == "paper":
        state = "paper"
        message = "Paper broker adapter is active."
    elif not settings.live_execution_enabled:
        state = "blocked"
        message = "Live backend requested but live execution is disabled."
    else:
        state = "pending_live_adapter"
        message = "Live backend requested but no live broker adapter is implemented yet."
    return {
        "backend": backend,
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "state": state,
        "message": message,
        "live_requested": live_requested,
        "live_ready": live_ready,
    }
