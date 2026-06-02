from collections.abc import Callable
from dataclasses import dataclass

from agentic_trader.config import Settings
from agentic_trader.schemas import BacktestTrade, MarketSnapshot, RunArtifacts, TradeSide


@dataclass
class OpenTradeState:
    side: TradeSide
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    holding_bars: int
    invalidation_logic: str
    trade_index: int


@dataclass
class BacktestState:
    cash: float
    starting_equity: float
    equity_curve: list[float]
    trades: list[BacktestTrade]
    open_trade: OpenTradeState | None = None
    fallback_cycles: int = 0
    bars_in_market: int = 0
    total_cycles: int = 0


@dataclass(frozen=True)
class BacktestRunContext:
    settings: Settings
    symbol: str
    interval: str
    lookback: str
    artifact_provider: Callable[[MarketSnapshot], RunArtifacts]
