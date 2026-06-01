from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import (
    ExecutionSide,
    PositionExitReason,
    RuntimeMode,
    ServiceEventLevel,
    ServiceState,
    TradeSide,
)

class AccountMark(BaseModel):
    mark_id: str
    created_at: str
    source: str
    note: str
    cycle_count: int | None = None
    symbol: str | None = None
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int

class ServiceStateSnapshot(BaseModel):
    service_name: str
    state: ServiceState
    runtime_mode: RuntimeMode = "operation"
    updated_at: str
    started_at: str | None = None
    last_heartbeat_at: str | None = None
    continuous: bool = False
    poll_seconds: int | None = None
    cycle_count: int = 0
    symbols: list[str] = Field(default_factory=list[str])
    interval: str | None = None
    lookback: str | None = None
    max_cycles: int | None = None
    current_symbol: str | None = None
    last_error: str | None = None
    pid: int | None = None
    stop_requested: bool = False
    background_mode: bool = False
    launch_count: int = 0
    restart_count: int = 0
    last_terminal_state: str | None = None
    last_terminal_at: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    message: str = ""

class ServiceEvent(BaseModel):
    event_id: str
    created_at: str
    level: ServiceEventLevel
    event_type: str
    message: str
    cycle_count: int | None = None
    symbol: str | None = None

class PositionSnapshot(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float

class PositionPlanSnapshot(BaseModel):
    symbol: str
    side: TradeSide
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    holding_bars: int
    invalidation_logic: str
    updated_at: str

class PositionExitDecision(BaseModel):
    should_exit: bool
    side: ExecutionSide
    symbol: str
    reason: PositionExitReason
    rationale: str
    exit_price: float
