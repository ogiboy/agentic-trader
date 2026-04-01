from dataclasses import dataclass

import pandas as pd

from agentic_trader.config import Settings
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import BacktestReport, BacktestTrade, PositionPlanSnapshot, PositionSnapshot
from agentic_trader.workflows.run_once import run_from_snapshot


@dataclass
class _OpenTradeState:
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    holding_bars: int
    invalidation_logic: str
    trade_index: int


def _timestamp_at(frame: pd.DataFrame, index: int) -> str:
    raw_value = frame.index[index]
    iso_value = getattr(raw_value, "isoformat", None)
    return str(iso_value() if callable(iso_value) else raw_value)


def _mark_to_market_equity(cash: float, open_trade: _OpenTradeState | None, current_price: float) -> float:
    if open_trade is None:
        return cash
    signed_quantity = open_trade.quantity if open_trade.side == "buy" else -open_trade.quantity
    return cash + (signed_quantity * current_price)


def _compute_drawdown(equity_curve: list[float]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown


def run_walk_forward_backtest(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: pd.DataFrame | None = None,
) -> BacktestReport:
    history = frame.copy() if frame is not None else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    if len(history) <= warmup_bars:
        raise ValueError("Not enough bars for walk-forward backtest")

    cash = settings.default_cash
    starting_equity = settings.default_cash
    equity_curve: list[float] = [starting_equity]
    trades: list[BacktestTrade] = []
    open_trade: _OpenTradeState | None = None
    fallback_cycles = 0
    bars_in_market = 0
    total_cycles = 0

    for index in range(warmup_bars, len(history)):
        total_cycles += 1
        window = history.iloc[: index + 1]
        snapshot = build_snapshot(window, symbol=symbol, interval=interval)
        current_price = snapshot.last_close
        current_timestamp = _timestamp_at(history, index)
        closed_this_bar = False

        if open_trade is not None:
            bars_in_market += 1
            signed_quantity = open_trade.quantity if open_trade.side == "buy" else -open_trade.quantity
            open_trade.holding_bars += 1
            position = PositionSnapshot(
                symbol=symbol,
                quantity=signed_quantity,
                average_price=open_trade.entry_price,
                market_price=current_price,
                market_value=signed_quantity * current_price,
                unrealized_pnl=(current_price - open_trade.entry_price) * signed_quantity,
            )
            plan = PositionPlanSnapshot(
                symbol=symbol,
                side=open_trade.side,
                entry_price=open_trade.entry_price,
                stop_loss=open_trade.stop_loss,
                take_profit=open_trade.take_profit,
                max_holding_bars=open_trade.max_holding_bars,
                holding_bars=open_trade.holding_bars,
                invalidation_logic=open_trade.invalidation_logic,
                updated_at=current_timestamp,
            )
            exit_decision = evaluate_position_exit(snapshot, position, plan)
            if exit_decision.should_exit:
                if open_trade.side == "buy":
                    cash += open_trade.quantity * exit_decision.exit_price
                    pnl = (exit_decision.exit_price - open_trade.entry_price) * open_trade.quantity
                else:
                    cash -= open_trade.quantity * exit_decision.exit_price
                    pnl = (open_trade.entry_price - exit_decision.exit_price) * open_trade.quantity
                trades[open_trade.trade_index] = trades[open_trade.trade_index].model_copy(
                    update={
                        "exit_at": current_timestamp,
                        "exit_price": exit_decision.exit_price,
                        "status": "closed",
                        "exit_reason": exit_decision.reason,
                        "pnl": pnl,
                    }
                )
                open_trade = None
                closed_this_bar = True

        if open_trade is None and not closed_this_bar:
            artifacts = run_from_snapshot(
                settings=settings,
                snapshot=snapshot,
                allow_fallback=allow_fallback,
            )
            if artifacts.used_fallback():
                fallback_cycles += 1
            decision = artifacts.execution
            if decision.approved and decision.side in {"buy", "sell"}:
                if decision.side == "sell" and not settings.allow_short:
                    equity_curve.append(cash)
                    continue
                base_equity = _mark_to_market_equity(cash, open_trade, current_price)
                notional = max(0.0, base_equity * decision.position_size_pct)
                quantity = round(notional / decision.entry_price, 6)
                if quantity > 0:
                    if decision.side == "buy":
                        cash -= quantity * decision.entry_price
                    else:
                        cash += quantity * decision.entry_price
                    trades.append(
                        BacktestTrade(
                            symbol=symbol,
                            entry_at=current_timestamp,
                            side=decision.side,
                            entry_price=decision.entry_price,
                            quantity=quantity,
                            status="open",
                            used_fallback=artifacts.used_fallback(),
                        )
                    )
                    open_trade = _OpenTradeState(
                        side=decision.side,
                        quantity=quantity,
                        entry_price=decision.entry_price,
                        stop_loss=decision.stop_loss,
                        take_profit=decision.take_profit,
                        max_holding_bars=artifacts.risk.max_holding_bars,
                        holding_bars=0,
                        invalidation_logic=artifacts.strategy.invalidation_logic,
                        trade_index=len(trades) - 1,
                    )

        equity_curve.append(_mark_to_market_equity(cash, open_trade, current_price))

    if open_trade is not None:
        final_price = float(history["close"].iloc[-1])
        final_timestamp = _timestamp_at(history, len(history) - 1)
        if open_trade.side == "buy":
            cash += open_trade.quantity * final_price
            pnl = (final_price - open_trade.entry_price) * open_trade.quantity
        else:
            cash -= open_trade.quantity * final_price
            pnl = (open_trade.entry_price - final_price) * open_trade.quantity
        trades[open_trade.trade_index] = trades[open_trade.trade_index].model_copy(
            update={
                "exit_at": final_timestamp,
                "exit_price": final_price,
                "status": "closed",
                "exit_reason": "end_of_data",
                "pnl": pnl,
            }
        )
        open_trade = None
        equity_curve.append(cash)

    closed_trades = [trade for trade in trades if trade.status == "closed" and trade.pnl is not None]
    wins = [trade for trade in closed_trades if trade.pnl is not None and trade.pnl > 0]
    ending_equity = cash if open_trade is None else equity_curve[-1]

    return BacktestReport(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        total_cycles=total_cycles,
        total_trades=len(trades),
        closed_trades=len(closed_trades),
        win_rate=(len(wins) / len(closed_trades)) if closed_trades else 0.0,
        expectancy=(sum(trade.pnl or 0.0 for trade in closed_trades) / len(closed_trades)) if closed_trades else 0.0,
        total_return_pct=((ending_equity - starting_equity) / starting_equity) if starting_equity else 0.0,
        max_drawdown_pct=_compute_drawdown(equity_curve),
        exposure_pct=(bars_in_market / total_cycles) if total_cycles else 0.0,
        fallback_cycles=fallback_cycles,
        starting_equity=starting_equity,
        ending_equity=ending_equity,
        trades=trades,
    )
