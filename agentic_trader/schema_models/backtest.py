from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import TradeSide


class BacktestTrade(BaseModel):
    symbol: str
    entry_at: str
    exit_at: str | None = None
    side: TradeSide
    entry_price: float
    exit_price: float | None = None
    quantity: float
    status: Literal["open", "closed"]
    exit_reason: str | None = None
    pnl: float | None = None
    used_fallback: bool = False


class BacktestReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    data_start_at: str | None = None
    data_end_at: str | None = None
    first_decision_at: str | None = None
    last_decision_at: str | None = None
    total_cycles: int
    total_trades: int
    closed_trades: int
    win_rate: float
    expectancy: float
    total_return_pct: float
    max_drawdown_pct: float
    exposure_pct: float
    fallback_cycles: int
    starting_equity: float
    ending_equity: float
    trades: list[BacktestTrade] = Field(default_factory=list[BacktestTrade])


class BacktestSummary(BaseModel):
    label: str
    total_trades: int
    closed_trades: int
    win_rate: float
    expectancy: float
    total_return_pct: float
    max_drawdown_pct: float
    exposure_pct: float
    starting_equity: float
    ending_equity: float


class BacktestComparisonReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    agent: BacktestSummary
    baseline: BacktestSummary
    ending_equity_delta: float
    total_return_delta_pct: float


class BacktestAblationReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    with_memory: BacktestSummary
    without_memory: BacktestSummary
    ending_equity_delta: float
    total_return_delta_pct: float
