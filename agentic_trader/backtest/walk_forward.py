from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from agentic_trader.config import Settings
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import (
    BacktestComparisonReport,
    BacktestReport,
    BacktestSummary,
    BacktestTrade,
    ExecutionDecision,
    ManagerDecision,
    MarketSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    StrategyPlan,
)
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


def _summarize_report(label: str, report: BacktestReport) -> BacktestSummary:
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


def _baseline_artifacts(snapshot: MarketSnapshot) -> RunArtifacts:
    trend_up = snapshot.last_close > snapshot.ema_20 > snapshot.ema_50 and snapshot.rsi_14 >= 52
    trend_down = snapshot.last_close < snapshot.ema_20 < snapshot.ema_50 and snapshot.rsi_14 <= 48
    normalized_atr = max(snapshot.atr_14, snapshot.last_close * 0.01)

    if trend_up:
        strategy = StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Baseline enters long when price is above EMA20 and EMA50 with supportive RSI.",
            invalidation_logic="Exit below EMA20 with weakening momentum.",
            confidence=0.68,
        )
        risk = RiskPlan(
            position_size_pct=0.08,
            stop_loss=round(snapshot.last_close - (1.5 * normalized_atr), 4),
            take_profit=round(snapshot.last_close + (3.0 * normalized_atr), 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Deterministic baseline risk plan for long trend setup.",
        )
        execution = ExecutionDecision(
            approved=True,
            side="buy",
            symbol=snapshot.symbol,
            entry_price=snapshot.last_close,
            stop_loss=risk.stop_loss,
            take_profit=risk.take_profit,
            position_size_pct=risk.position_size_pct,
            confidence=0.68,
            rationale="Deterministic baseline approved long trend setup.",
        )
        regime = RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.68,
            reasoning="Deterministic baseline classified an uptrend.",
        )
    elif trend_down:
        strategy = StrategyPlan(
            strategy_family="trend_following",
            action="sell",
            timeframe="swing",
            entry_logic="Baseline enters short when price is below EMA20 and EMA50 with weak RSI.",
            invalidation_logic="Exit above EMA20 with strengthening momentum.",
            confidence=0.68,
        )
        risk = RiskPlan(
            position_size_pct=0.08,
            stop_loss=round(snapshot.last_close + (1.5 * normalized_atr), 4),
            take_profit=round(snapshot.last_close - (3.0 * normalized_atr), 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Deterministic baseline risk plan for short trend setup.",
        )
        execution = ExecutionDecision(
            approved=True,
            side="sell",
            symbol=snapshot.symbol,
            entry_price=snapshot.last_close,
            stop_loss=risk.stop_loss,
            take_profit=risk.take_profit,
            position_size_pct=risk.position_size_pct,
            confidence=0.68,
            rationale="Deterministic baseline approved short trend setup.",
        )
        regime = RegimeAssessment(
            regime="trend_down",
            direction_bias="short",
            confidence=0.68,
            reasoning="Deterministic baseline classified a downtrend.",
        )
    else:
        strategy = StrategyPlan(
            strategy_family="no_trade",
            action="hold",
            timeframe="flat",
            entry_logic="Baseline found no aligned setup.",
            invalidation_logic="Wait for trend alignment.",
            confidence=0.55,
        )
        risk = RiskPlan(
            position_size_pct=0.01,
            stop_loss=round(snapshot.last_close - normalized_atr, 4),
            take_profit=round(snapshot.last_close + normalized_atr, 4),
            risk_reward_ratio=1.0,
            max_holding_bars=5,
            notes="Deterministic baseline no-trade placeholder.",
        )
        execution = ExecutionDecision(
            approved=False,
            side="hold",
            symbol=snapshot.symbol,
            entry_price=snapshot.last_close,
            stop_loss=risk.stop_loss,
            take_profit=risk.take_profit,
            position_size_pct=risk.position_size_pct,
            confidence=0.55,
            rationale="Deterministic baseline did not find a valid setup.",
        )
        regime = RegimeAssessment(
            regime="range",
            direction_bias="flat",
            confidence=0.55,
            reasoning="Deterministic baseline found mixed conditions.",
        )

    coordinator = ResearchCoordinatorBrief(
        market_focus="trend_following" if execution.side in {"buy", "sell"} else "no_trade",
        priority_signals=["trend_alignment"] if execution.side in {"buy", "sell"} else ["wait_for_clarity"],
        caution_flags=[] if execution.side in {"buy", "sell"} else ["mixed_signals"],
        summary="Deterministic baseline coordinator summary.",
    )
    manager = ManagerDecision(
        approved=execution.approved,
        action_bias=execution.side,
        confidence_cap=execution.confidence,
        size_multiplier=1.0,
        rationale="Deterministic baseline manager summary.",
    )
    review = ReviewNote(
        summary="Deterministic baseline review summary.",
        strengths=["Deterministic baseline produced a reproducible decision."],
        warnings=[] if execution.approved else ["No baseline trade was approved."],
        next_checks=["Compare against the agent-driven replay."],
    )
    return RunArtifacts(
        snapshot=snapshot,
        coordinator=coordinator,
        regime=regime,
        strategy=strategy,
        risk=risk,
        manager=manager,
        execution=execution,
        review=review,
    )


def _run_backtest_with_provider(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    frame: pd.DataFrame,
    artifact_provider: Callable[[MarketSnapshot], RunArtifacts],
) -> BacktestReport:
    history = frame.copy()
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
            artifacts = artifact_provider(snapshot)
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
        equity_curve.append(cash)

    closed_trades = [trade for trade in trades if trade.status == "closed" and trade.pnl is not None]
    wins = [trade for trade in closed_trades if trade.pnl is not None and trade.pnl > 0]
    ending_equity = cash

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
    return _run_backtest_with_provider(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        frame=history,
        artifact_provider=lambda snapshot: run_from_snapshot(
            settings=settings,
            snapshot=snapshot,
            allow_fallback=allow_fallback,
        ),
    )


def run_deterministic_baseline_backtest(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    frame: pd.DataFrame | None = None,
) -> BacktestReport:
    history = frame.copy() if frame is not None else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    return _run_backtest_with_provider(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        frame=history,
        artifact_provider=_baseline_artifacts,
    )


def run_backtest_comparison(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: pd.DataFrame | None = None,
) -> BacktestComparisonReport:
    history = frame.copy() if frame is not None else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    agent_report = run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        frame=history,
    )
    baseline_report = run_deterministic_baseline_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        frame=history,
    )
    return BacktestComparisonReport(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        agent=_summarize_report("agent", agent_report),
        baseline=_summarize_report("baseline", baseline_report),
        ending_equity_delta=round(agent_report.ending_equity - baseline_report.ending_equity, 6),
        total_return_delta_pct=round(agent_report.total_return_pct - baseline_report.total_return_pct, 6),
    )
