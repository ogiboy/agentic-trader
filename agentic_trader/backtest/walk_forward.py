import pandas as pd

from agentic_trader.backtest.baseline import baseline_artifacts
from agentic_trader.backtest.walk_forward_engine import (
    run_backtest_with_provider,
    summarize_report,
)
from agentic_trader.config import Settings
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.schemas import (
    BacktestAblationReport,
    BacktestComparisonReport,
    BacktestReport,
)
from agentic_trader.workflows.run_once import run_from_snapshot


def run_walk_forward_backtest(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    memory_enabled: bool = True,
    frame: pd.DataFrame | None = None,
) -> BacktestReport:
    """Replay historical bars with the current agent pipeline in walk-forward mode."""
    history = (
        frame.copy()
        if frame is not None
        else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    )
    return run_backtest_with_provider(
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
            memory_enabled=memory_enabled,
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
    """Replay historical bars with the deterministic baseline artifact provider."""
    history = (
        frame.copy()
        if frame is not None
        else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    )
    return run_backtest_with_provider(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        frame=history,
        artifact_provider=baseline_artifacts,
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
    """Compare agent-assisted walk-forward results against the deterministic baseline."""
    history = (
        frame.copy()
        if frame is not None
        else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    )
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
        agent=summarize_report("agent", agent_report),
        baseline=summarize_report("baseline", baseline_report),
        ending_equity_delta=round(
            agent_report.ending_equity - baseline_report.ending_equity, 6
        ),
        total_return_delta_pct=round(
            agent_report.total_return_pct - baseline_report.total_return_pct, 6
        ),
    )


def run_memory_ablation_backtest(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: pd.DataFrame | None = None,
) -> BacktestAblationReport:
    """Compare walk-forward results with and without memory injection enabled."""
    history = (
        frame.copy()
        if frame is not None
        else fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    )
    with_memory = run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        memory_enabled=True,
        frame=history,
    )
    without_memory = run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        memory_enabled=False,
        frame=history,
    )
    return BacktestAblationReport(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        with_memory=summarize_report("with_memory", with_memory),
        without_memory=summarize_report("without_memory", without_memory),
        ending_equity_delta=round(
            with_memory.ending_equity - without_memory.ending_equity, 6
        ),
        total_return_delta_pct=round(
            with_memory.total_return_pct - without_memory.total_return_pct, 6
        ),
    )
