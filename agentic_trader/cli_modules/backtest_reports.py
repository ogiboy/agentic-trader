from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.schemas import (
    BacktestAblationReport,
    BacktestComparisonReport,
    BacktestReport,
)
from agentic_trader.ui_text import (
    LABEL_AGENT,
    LABEL_BASELINE,
    LABEL_CLOSED_TRADES,
    LABEL_CYCLES,
    LABEL_DELTA,
    LABEL_ENDING_EQUITY,
    LABEL_ENTRY,
    LABEL_ENTRY_PX,
    LABEL_EXPECTANCY,
    LABEL_EXIT,
    LABEL_EXIT_PX,
    LABEL_EXPOSURE,
    LABEL_FALLBACK_CYCLES,
    LABEL_FIELD,
    LABEL_INTERVAL,
    LABEL_LOOKBACK,
    LABEL_MAX_DRAWDOWN,
    LABEL_METRIC,
    LABEL_PNL,
    LABEL_REASON,
    LABEL_RETURN,
    LABEL_SIDE,
    LABEL_TOTAL_RETURN,
    LABEL_TRADES,
    LABEL_VALUE,
    LABEL_WARMUP_BARS,
    LABEL_WIN_RATE,
    LABEL_WITH_MEMORY,
    LABEL_WITHOUT_MEMORY,
    MESSAGE_BACKTEST_CHOOSE_ONE_COMPARISON,
    MESSAGE_BACKTEST_COMPARISON_WRITTEN,
    MESSAGE_BACKTEST_MEMORY_ABLATION_WRITTEN,
    MESSAGE_BACKTEST_SUMMARY_WRITTEN,
    MESSAGE_TRAINING_DIAGNOSTIC_FALLBACK,
    TITLE_BACKTEST_COMPARISON,
    TITLE_BACKTEST_MEMORY_ABLATION,
    TITLE_BACKTEST_TRADES,
    TITLE_EXPORTED,
    TITLE_TRAINING_DIAGNOSTIC_MODE,
    TITLE_WALK_FORWARD_BACKTEST,
)

EnsureReady = Callable[[Settings], object]
RunComparison = Callable[..., BacktestComparisonReport]
RunAblation = Callable[..., BacktestAblationReport]
RunWalkForward = Callable[..., BacktestReport]


def run_backtest_command(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    compare_baseline: bool,
    compare_memory: bool,
    output: str | None,
    ensure_ready: EnsureReady,
    run_comparison: RunComparison,
    run_ablation: RunAblation,
    run_walk_forward: RunWalkForward,
) -> None:
    """Run the selected CLI backtest mode and render/write its report."""
    allow_diagnostic_fallback = _training_backtest_allow_fallback(
        settings,
        ensure_ready=ensure_ready,
    )
    if compare_baseline and compare_memory:
        raise typer.BadParameter(MESSAGE_BACKTEST_CHOOSE_ONE_COMPARISON)
    if compare_baseline:
        _run_baseline_comparison(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=allow_diagnostic_fallback,
            output=output,
            run_comparison=run_comparison,
        )
        return

    if compare_memory:
        _run_memory_ablation(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=allow_diagnostic_fallback,
            output=output,
            run_ablation=run_ablation,
        )
        return

    _run_walk_forward(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_diagnostic_fallback,
        output=output,
        run_walk_forward=run_walk_forward,
    )


def _training_backtest_allow_fallback(
    settings: Settings, *, ensure_ready: EnsureReady
) -> bool:
    try:
        ensure_ready(settings)
    except RuntimeError as exc:
        if settings.runtime_mode != "training":
            raise
        console.print(
            Panel(
                MESSAGE_TRAINING_DIAGNOSTIC_FALLBACK.format(error=exc),
                title=TITLE_TRAINING_DIAGNOSTIC_MODE,
                border_style="yellow",
            )
        )
        return True
    return False


def _run_baseline_comparison(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    allow_fallback: bool,
    output: str | None,
    run_comparison: RunComparison,
) -> None:
    comparison = run_comparison(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
    )
    render_backtest_comparison(comparison)
    if output is not None:
        write_backtest_comparison_summary(output, comparison)
        _print_backtest_exported(
            MESSAGE_BACKTEST_COMPARISON_WRITTEN.format(output=output)
        )


def _run_memory_ablation(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    allow_fallback: bool,
    output: str | None,
    run_ablation: RunAblation,
) -> None:
    ablation = run_ablation(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
    )
    render_backtest_ablation(ablation)
    if output is not None:
        write_backtest_ablation_summary(output, ablation)
        _print_backtest_exported(
            MESSAGE_BACKTEST_MEMORY_ABLATION_WRITTEN.format(output=output)
        )


def _run_walk_forward(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int,
    allow_fallback: bool,
    output: str | None,
    run_walk_forward: RunWalkForward,
) -> None:
    report = run_walk_forward(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
    )
    render_backtest_report(report)
    if output is not None:
        write_walk_forward_backtest_summary(output, report)
        _print_backtest_exported(MESSAGE_BACKTEST_SUMMARY_WRITTEN.format(output=output))


def _print_backtest_exported(message: str) -> None:
    console.print(Panel(message, title=TITLE_EXPORTED, border_style="green"))


def render_backtest_report(report: BacktestReport) -> None:
    summary = Table(title=TITLE_WALK_FORWARD_BACKTEST + " / " + report.symbol)
    summary.add_column(LABEL_FIELD)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_INTERVAL, report.interval)
    summary.add_row(LABEL_LOOKBACK, report.lookback)
    summary.add_row(LABEL_WARMUP_BARS, str(report.warmup_bars))
    summary.add_row(LABEL_CYCLES, str(report.total_cycles))
    summary.add_row(LABEL_TRADES, str(report.total_trades))
    summary.add_row(LABEL_CLOSED_TRADES, str(report.closed_trades))
    summary.add_row(LABEL_WIN_RATE, f"{report.win_rate:.2%}")
    summary.add_row(LABEL_EXPECTANCY, f"{report.expectancy:.2f}")
    summary.add_row(LABEL_TOTAL_RETURN, f"{report.total_return_pct:.2%}")
    summary.add_row(LABEL_MAX_DRAWDOWN, f"{report.max_drawdown_pct:.2%}")
    summary.add_row(LABEL_EXPOSURE, f"{report.exposure_pct:.2%}")
    summary.add_row(LABEL_FALLBACK_CYCLES, str(report.fallback_cycles))
    console.print(summary)
    _render_backtest_trades(report)


def _render_backtest_trades(report: BacktestReport) -> None:
    trades = Table(title=TITLE_BACKTEST_TRADES)
    trades.add_column(LABEL_ENTRY)
    trades.add_column(LABEL_EXIT)
    trades.add_column(LABEL_SIDE)
    trades.add_column(LABEL_ENTRY_PX)
    trades.add_column(LABEL_EXIT_PX)
    trades.add_column(LABEL_PNL)
    trades.add_column(LABEL_REASON)
    if not report.trades:
        trades.add_row("-", "-", "-", "-", "-", "-", "-")
    else:
        for trade in report.trades[-12:]:
            trades.add_row(
                trade.entry_at,
                trade.exit_at or "-",
                trade.side,
                f"{trade.entry_price:.4f}",
                f"{trade.exit_price:.4f}" if trade.exit_price is not None else "-",
                f"{trade.pnl:.2f}" if trade.pnl is not None else "-",
                trade.exit_reason or "-",
            )
    console.print(trades)


def render_backtest_comparison(report: BacktestComparisonReport) -> None:
    table = Table(title=TITLE_BACKTEST_COMPARISON + " / " + report.symbol)
    table.add_column(LABEL_METRIC)
    table.add_column(LABEL_AGENT)
    table.add_column(LABEL_BASELINE)
    table.add_column(LABEL_DELTA)
    table.add_row(
        LABEL_TRADES,
        str(report.agent.total_trades),
        str(report.baseline.total_trades),
        str(report.agent.total_trades - report.baseline.total_trades),
    )
    table.add_row(
        LABEL_CLOSED_TRADES,
        str(report.agent.closed_trades),
        str(report.baseline.closed_trades),
        str(report.agent.closed_trades - report.baseline.closed_trades),
    )
    table.add_row(
        LABEL_WIN_RATE,
        f"{report.agent.win_rate:.2%}",
        f"{report.baseline.win_rate:.2%}",
        f"{report.agent.win_rate - report.baseline.win_rate:.2%}",
    )
    table.add_row(
        LABEL_EXPECTANCY,
        f"{report.agent.expectancy:.2f}",
        f"{report.baseline.expectancy:.2f}",
        f"{report.agent.expectancy - report.baseline.expectancy:.2f}",
    )
    table.add_row(
        LABEL_RETURN,
        f"{report.agent.total_return_pct:.2%}",
        f"{report.baseline.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        LABEL_MAX_DRAWDOWN,
        f"{report.agent.max_drawdown_pct:.2%}",
        f"{report.baseline.max_drawdown_pct:.2%}",
        f"{report.agent.max_drawdown_pct - report.baseline.max_drawdown_pct:.2%}",
    )
    table.add_row(
        LABEL_EXPOSURE,
        f"{report.agent.exposure_pct:.2%}",
        f"{report.baseline.exposure_pct:.2%}",
        f"{report.agent.exposure_pct - report.baseline.exposure_pct:.2%}",
    )
    table.add_row(
        LABEL_ENDING_EQUITY,
        f"{report.agent.ending_equity:.2f}",
        f"{report.baseline.ending_equity:.2f}",
        f"{report.ending_equity_delta:.2f}",
    )
    console.print(table)


def render_backtest_ablation(report: BacktestAblationReport) -> None:
    table = Table(title=TITLE_BACKTEST_MEMORY_ABLATION + " / " + report.symbol)
    table.add_column(LABEL_METRIC)
    table.add_column(LABEL_WITH_MEMORY)
    table.add_column(LABEL_WITHOUT_MEMORY)
    table.add_column(LABEL_DELTA)
    table.add_row(
        LABEL_TRADES,
        str(report.with_memory.total_trades),
        str(report.without_memory.total_trades),
        str(report.with_memory.total_trades - report.without_memory.total_trades),
    )
    table.add_row(
        LABEL_WIN_RATE,
        f"{report.with_memory.win_rate:.2%}",
        f"{report.without_memory.win_rate:.2%}",
        f"{report.with_memory.win_rate - report.without_memory.win_rate:.2%}",
    )
    table.add_row(
        LABEL_EXPECTANCY,
        f"{report.with_memory.expectancy:.2f}",
        f"{report.without_memory.expectancy:.2f}",
        f"{report.with_memory.expectancy - report.without_memory.expectancy:.2f}",
    )
    table.add_row(
        LABEL_RETURN,
        f"{report.with_memory.total_return_pct:.2%}",
        f"{report.without_memory.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        LABEL_ENDING_EQUITY,
        f"{report.with_memory.ending_equity:.2f}",
        f"{report.without_memory.ending_equity:.2f}",
        f"{report.ending_equity_delta:.2f}",
    )
    console.print(table)


def write_backtest_comparison_summary(
    output: str | Path, comparison: BacktestComparisonReport
) -> str:
    rendered = "\n".join(
        [
            f"# Backtest Comparison: {comparison.symbol}",
            "",
            f"- Agent Return: {comparison.agent.total_return_pct:.2%}",
            f"- Baseline Return: {comparison.baseline.total_return_pct:.2%}",
            f"- Return Delta: {comparison.total_return_delta_pct:.2%}",
            f"- Agent Ending Equity: {comparison.agent.ending_equity:.2f}",
            f"- Baseline Ending Equity: {comparison.baseline.ending_equity:.2f}",
            f"- Ending Equity Delta: {comparison.ending_equity_delta:.2f}",
        ]
    )
    return _write_summary(output, rendered)


def write_backtest_ablation_summary(
    output: str | Path, ablation: BacktestAblationReport
) -> str:
    rendered = "\n".join(
        [
            f"# Backtest Memory Ablation: {ablation.symbol}",
            "",
            f"- With Memory Return: {ablation.with_memory.total_return_pct:.2%}",
            f"- Without Memory Return: {ablation.without_memory.total_return_pct:.2%}",
            f"- Return Delta: {ablation.total_return_delta_pct:.2%}",
            f"- With Memory Ending Equity: {ablation.with_memory.ending_equity:.2f}",
            f"- Without Memory Ending Equity: {ablation.without_memory.ending_equity:.2f}",
            f"- Ending Equity Delta: {ablation.ending_equity_delta:.2f}",
        ]
    )
    return _write_summary(output, rendered)


def write_walk_forward_backtest_summary(
    output: str | Path, report: BacktestReport
) -> str:
    rendered = "\n".join(
        [
            f"# Walk-Forward Backtest: {report.symbol}",
            "",
            f"- Interval: {report.interval}",
            f"- Lookback: {report.lookback}",
            f"- Warmup Bars: {report.warmup_bars}",
            f"- Cycles: {report.total_cycles}",
            f"- Trades: {report.total_trades}",
            f"- Closed Trades: {report.closed_trades}",
            f"- {LABEL_WIN_RATE}: {report.win_rate:.2%}",
            f"- Expectancy: {report.expectancy:.2f}",
            f"- Total Return: {report.total_return_pct:.2%}",
            f"- Max Drawdown: {report.max_drawdown_pct:.2%}",
            f"- Exposure: {report.exposure_pct:.2%}",
        ]
    )
    return _write_summary(output, rendered)


def _write_summary(output: str | Path, rendered: str) -> str:
    path = Path(output)
    path.write_text(rendered, encoding="utf-8")
    return str(path)
