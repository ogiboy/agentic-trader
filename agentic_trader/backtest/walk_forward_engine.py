from collections.abc import Callable
from typing import cast

import pandas as pd

from agentic_trader.backtest.walk_forward_state import (
    BacktestRunContext,
    BacktestState,
    OpenTradeState,
)
from agentic_trader.config import Settings
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import (
    BacktestReport,
    BacktestSummary,
    BacktestTrade,
    MarketSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    RunArtifacts,
    TradeSide,
)


def _timestamp_at(frame: pd.DataFrame, index: int) -> str:
    raw_value = frame.index[index]
    iso_value = getattr(raw_value, "isoformat", None)
    return str(iso_value() if callable(iso_value) else raw_value)


def _mark_to_market_equity(
    cash: float, open_trade: OpenTradeState | None, current_price: float
) -> float:
    if open_trade is None:
        return cash
    signed_quantity = (
        open_trade.quantity if open_trade.side == "buy" else -open_trade.quantity
    )
    return cash + (signed_quantity * current_price)


def _compute_drawdown(equity_curve: list[float]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown


def summarize_report(label: str, report: BacktestReport) -> BacktestSummary:
    return BacktestSummary(
        label=label,
        total_trades=report.total_trades,
        closed_trades=report.closed_trades,
        win_rate=report.win_rate,
        expectancy=report.expectancy,
        total_return_pct=report.total_return_pct,
        max_drawdown_pct=report.max_drawdown_pct,
        exposure_pct=report.exposure_pct,
        starting_equity=report.starting_equity,
        ending_equity=report.ending_equity,
    )


def _signed_quantity(open_trade: OpenTradeState) -> float:
    return open_trade.quantity if open_trade.side == "buy" else -open_trade.quantity


def _cash_and_pnl_after_exit(
    cash: float, open_trade: OpenTradeState, exit_price: float
) -> tuple[float, float]:
    if open_trade.side == "buy":
        return (
            cash + (open_trade.quantity * exit_price),
            (exit_price - open_trade.entry_price) * open_trade.quantity,
        )
    return (
        cash - (open_trade.quantity * exit_price),
        (open_trade.entry_price - exit_price) * open_trade.quantity,
    )


def _close_trade_record(
    trades: list[BacktestTrade],
    open_trade: OpenTradeState,
    *,
    exit_at: str,
    exit_price: float,
    exit_reason: str,
    pnl: float,
) -> None:
    trades[open_trade.trade_index] = trades[open_trade.trade_index].model_copy(
        update={
            "exit_at": exit_at,
            "exit_price": exit_price,
            "status": "closed",
            "exit_reason": exit_reason,
            "pnl": pnl,
        }
    )


def _open_trade_position(
    *, symbol: str, open_trade: OpenTradeState, current_price: float
) -> PositionSnapshot:
    signed_quantity = _signed_quantity(open_trade)
    return PositionSnapshot(
        symbol=symbol,
        quantity=signed_quantity,
        average_price=open_trade.entry_price,
        market_price=current_price,
        market_value=signed_quantity * current_price,
        unrealized_pnl=(current_price - open_trade.entry_price) * signed_quantity,
    )


def _open_trade_plan(
    open_trade: OpenTradeState, *, symbol: str, current_timestamp: str
) -> PositionPlanSnapshot:
    return PositionPlanSnapshot(
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


def _evaluate_open_trade_exit(
    *,
    state: BacktestState,
    symbol: str,
    snapshot: MarketSnapshot,
    current_price: float,
    current_timestamp: str,
) -> bool:
    open_trade = state.open_trade
    if open_trade is None:
        return False

    state.bars_in_market += 1
    open_trade.holding_bars += 1
    exit_decision = evaluate_position_exit(
        snapshot,
        _open_trade_position(
            symbol=symbol,
            open_trade=open_trade,
            current_price=current_price,
        ),
        _open_trade_plan(
            open_trade,
            symbol=symbol,
            current_timestamp=current_timestamp,
        ),
    )
    if not exit_decision.should_exit:
        return False

    state.cash, pnl = _cash_and_pnl_after_exit(
        state.cash,
        open_trade,
        exit_decision.exit_price,
    )
    _close_trade_record(
        state.trades,
        open_trade,
        exit_at=current_timestamp,
        exit_price=exit_decision.exit_price,
        exit_reason=exit_decision.reason,
        pnl=pnl,
    )
    state.open_trade = None
    return True


def _record_open_trade(
    *,
    state: BacktestState,
    symbol: str,
    current_timestamp: str,
    current_price: float,
    decision_side: TradeSide,
    artifacts: RunArtifacts,
) -> None:
    decision = artifacts.execution
    base_equity = _mark_to_market_equity(
        state.cash,
        state.open_trade,
        current_price,
    )
    notional = max(0.0, base_equity * decision.position_size_pct)
    quantity = round(notional / decision.entry_price, 6)
    if quantity <= 0:
        return

    if decision_side == "buy":
        state.cash -= quantity * decision.entry_price
    else:
        state.cash += quantity * decision.entry_price

    state.trades.append(
        BacktestTrade(
            symbol=symbol,
            entry_at=current_timestamp,
            side=decision_side,
            entry_price=decision.entry_price,
            quantity=quantity,
            status="open",
            used_fallback=artifacts.used_fallback(),
        )
    )
    state.open_trade = OpenTradeState(
        side=decision_side,
        quantity=quantity,
        entry_price=decision.entry_price,
        stop_loss=decision.stop_loss,
        take_profit=decision.take_profit,
        max_holding_bars=artifacts.risk.max_holding_bars,
        holding_bars=0,
        invalidation_logic=artifacts.strategy.invalidation_logic,
        trade_index=len(state.trades) - 1,
    )


def _maybe_open_trade(
    *,
    state: BacktestState,
    settings: Settings,
    symbol: str,
    current_timestamp: str,
    current_price: float,
    snapshot: MarketSnapshot,
    artifact_provider: Callable[[MarketSnapshot], RunArtifacts],
) -> bool:
    artifacts = artifact_provider(snapshot)
    if artifacts.used_fallback():
        state.fallback_cycles += 1

    decision = artifacts.execution
    if not decision.approved or decision.side not in {"buy", "sell"}:
        return False

    decision_side = cast(TradeSide, decision.side)
    if decision_side == "sell" and not settings.allow_short:
        state.equity_curve.append(state.cash)
        return True

    _record_open_trade(
        state=state,
        symbol=symbol,
        current_timestamp=current_timestamp,
        current_price=current_price,
        decision_side=decision_side,
        artifacts=artifacts,
    )
    return False


def _finalize_open_trade(
    *,
    state: BacktestState,
    history: pd.DataFrame,
) -> None:
    open_trade = state.open_trade
    if open_trade is None:
        return

    final_price = float(history["close"].iloc[-1])
    final_timestamp = _timestamp_at(history, len(history) - 1)
    state.cash, pnl = _cash_and_pnl_after_exit(state.cash, open_trade, final_price)
    _close_trade_record(
        state.trades,
        open_trade,
        exit_at=final_timestamp,
        exit_price=final_price,
        exit_reason="end_of_data",
        pnl=pnl,
    )
    state.open_trade = None
    state.equity_curve.append(state.cash)


def _build_backtest_report(
    *,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    history: pd.DataFrame,
    state: BacktestState,
) -> BacktestReport:
    closed_trades = [
        trade
        for trade in state.trades
        if trade.status == "closed" and trade.pnl is not None
    ]
    wins = [trade for trade in closed_trades if trade.pnl is not None and trade.pnl > 0]
    ending_equity = state.cash
    return BacktestReport(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        data_start_at=_timestamp_at(history, 0),
        data_end_at=_timestamp_at(history, len(history) - 1),
        first_decision_at=_timestamp_at(history, warmup_bars),
        last_decision_at=_timestamp_at(history, len(history) - 1),
        total_cycles=state.total_cycles,
        total_trades=len(state.trades),
        closed_trades=len(closed_trades),
        win_rate=(len(wins) / len(closed_trades)) if closed_trades else 0.0,
        expectancy=(
            (sum(trade.pnl or 0.0 for trade in closed_trades) / len(closed_trades))
            if closed_trades
            else 0.0
        ),
        total_return_pct=(
            ((ending_equity - state.starting_equity) / state.starting_equity)
            if state.starting_equity
            else 0.0
        ),
        max_drawdown_pct=_compute_drawdown(state.equity_curve),
        exposure_pct=(
            (state.bars_in_market / state.total_cycles) if state.total_cycles else 0.0
        ),
        fallback_cycles=state.fallback_cycles,
        starting_equity=state.starting_equity,
        ending_equity=ending_equity,
        trades=state.trades,
    )


def _validated_backtest_history(frame: pd.DataFrame, *, warmup_bars: int) -> pd.DataFrame:
    history = frame.copy()
    if len(history) <= warmup_bars:
        raise ValueError("Not enough bars for walk-forward backtest")
    return history


def _initial_backtest_state(settings: Settings) -> BacktestState:
    return BacktestState(
        cash=settings.default_cash,
        starting_equity=settings.default_cash,
        equity_curve=[settings.default_cash],
        trades=[],
    )


def _snapshot_for_bar(
    history: pd.DataFrame, *, index: int, context: BacktestRunContext
) -> MarketSnapshot:
    return build_snapshot(
        history.iloc[: index + 1],
        symbol=context.symbol,
        interval=context.interval,
        lookback=context.lookback,
        enforce_lookback_coverage=False,
    )


def _process_backtest_bar(
    *,
    state: BacktestState,
    history: pd.DataFrame,
    index: int,
    context: BacktestRunContext,
) -> None:
    state.total_cycles += 1
    snapshot = _snapshot_for_bar(history, index=index, context=context)
    current_price = snapshot.last_close
    current_timestamp = _timestamp_at(history, index)
    closed_this_bar = _evaluate_open_trade_exit(
        state=state,
        symbol=context.symbol,
        snapshot=snapshot,
        current_price=current_price,
        current_timestamp=current_timestamp,
    )
    equity_recorded = False
    if state.open_trade is None and not closed_this_bar:
        equity_recorded = _maybe_open_trade(
            state=state,
            settings=context.settings,
            symbol=context.symbol,
            current_timestamp=current_timestamp,
            current_price=current_price,
            snapshot=snapshot,
            artifact_provider=context.artifact_provider,
        )

    if not equity_recorded:
        state.equity_curve.append(
            _mark_to_market_equity(state.cash, state.open_trade, current_price)
        )


def run_backtest_with_provider(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    frame: pd.DataFrame,
    artifact_provider: Callable[[MarketSnapshot], RunArtifacts],
) -> BacktestReport:
    history = _validated_backtest_history(frame, warmup_bars=warmup_bars)
    state = _initial_backtest_state(settings)
    context = BacktestRunContext(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        artifact_provider=artifact_provider,
    )

    for index in range(warmup_bars, len(history)):
        _process_backtest_bar(
            state=state,
            history=history,
            index=index,
            context=context,
        )

    _finalize_open_trade(state=state, history=history)

    return _build_backtest_report(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        history=history,
        state=state,
    )
