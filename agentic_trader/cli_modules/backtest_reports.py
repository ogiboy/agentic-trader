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
from agentic_trader.ui_text import t as ui_t

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
        raise typer.BadParameter(ui_t("message.backtest_choose_one_comparison"))
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
                ui_t("message.training_diagnostic_fallback").format(error=exc),
                title=ui_t("title.training_diagnostic_mode"),
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
            ui_t("message.backtest_comparison_written").format(output=output)
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
            ui_t("message.backtest_memory_ablation_written").format(output=output)
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
        _print_backtest_exported(
            ui_t("message.backtest_summary_written").format(output=output)
        )


def _print_backtest_exported(message: str) -> None:
    console.print(Panel(message, title=ui_t("title.exported"), border_style="green"))


def render_backtest_report(report: BacktestReport) -> None:
    summary = Table(title=ui_t("title.walk_forward_backtest") + " / " + report.symbol)
    summary.add_column(ui_t("label.field"))
    summary.add_column(ui_t("label.value"))
    summary.add_row(ui_t("label.interval"), report.interval)
    summary.add_row(ui_t("label.lookback"), report.lookback)
    summary.add_row(ui_t("label.warmup_bars"), str(report.warmup_bars))
    summary.add_row(ui_t("label.cycles"), str(report.total_cycles))
    summary.add_row(ui_t("label.trades"), str(report.total_trades))
    summary.add_row(ui_t("label.closed_trades"), str(report.closed_trades))
    summary.add_row(ui_t("label.win_rate"), f"{report.win_rate:.2%}")
    summary.add_row(ui_t("label.expectancy"), f"{report.expectancy:.2f}")
    summary.add_row(ui_t("label.total_return"), f"{report.total_return_pct:.2%}")
    summary.add_row(ui_t("label.max_drawdown"), f"{report.max_drawdown_pct:.2%}")
    summary.add_row(ui_t("label.exposure"), f"{report.exposure_pct:.2%}")
    summary.add_row(ui_t("label.fallback_cycles"), str(report.fallback_cycles))
    console.print(summary)
    _render_backtest_trades(report)


def _render_backtest_trades(report: BacktestReport) -> None:
    trades = Table(title=ui_t("title.backtest_trades"))
    trades.add_column(ui_t("label.entry"))
    trades.add_column(ui_t("label.exit"))
    trades.add_column(ui_t("label.side"))
    trades.add_column(ui_t("label.entry_px"))
    trades.add_column(ui_t("label.exit_px"))
    trades.add_column(ui_t("label.pnl"))
    trades.add_column(ui_t("label.reason"))
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
    table = Table(title=ui_t("title.backtest_comparison") + " / " + report.symbol)
    table.add_column(ui_t("label.metric"))
    table.add_column(ui_t("label.agent"))
    table.add_column(ui_t("label.baseline"))
    table.add_column(ui_t("label.delta"))
    table.add_row(
        ui_t("label.trades"),
        str(report.agent.total_trades),
        str(report.baseline.total_trades),
        str(report.agent.total_trades - report.baseline.total_trades),
    )
    table.add_row(
        ui_t("label.closed_trades"),
        str(report.agent.closed_trades),
        str(report.baseline.closed_trades),
        str(report.agent.closed_trades - report.baseline.closed_trades),
    )
    table.add_row(
        ui_t("label.win_rate"),
        f"{report.agent.win_rate:.2%}",
        f"{report.baseline.win_rate:.2%}",
        f"{report.agent.win_rate - report.baseline.win_rate:.2%}",
    )
    table.add_row(
        ui_t("label.expectancy"),
        f"{report.agent.expectancy:.2f}",
        f"{report.baseline.expectancy:.2f}",
        f"{report.agent.expectancy - report.baseline.expectancy:.2f}",
    )
    table.add_row(
        ui_t("label.return"),
        f"{report.agent.total_return_pct:.2%}",
        f"{report.baseline.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        ui_t("label.max_drawdown"),
        f"{report.agent.max_drawdown_pct:.2%}",
        f"{report.baseline.max_drawdown_pct:.2%}",
        f"{report.agent.max_drawdown_pct - report.baseline.max_drawdown_pct:.2%}",
    )
    table.add_row(
        ui_t("label.exposure"),
        f"{report.agent.exposure_pct:.2%}",
        f"{report.baseline.exposure_pct:.2%}",
        f"{report.agent.exposure_pct - report.baseline.exposure_pct:.2%}",
    )
    table.add_row(
        ui_t("label.ending_equity"),
        f"{report.agent.ending_equity:.2f}",
        f"{report.baseline.ending_equity:.2f}",
        f"{report.ending_equity_delta:.2f}",
    )
    console.print(table)


def render_backtest_ablation(report: BacktestAblationReport) -> None:
    table = Table(title=ui_t("title.backtest_memory_ablation") + " / " + report.symbol)
    table.add_column(ui_t("label.metric"))
    table.add_column(ui_t("label.with_memory"))
    table.add_column(ui_t("label.without_memory"))
    table.add_column(ui_t("label.delta"))
    table.add_row(
        ui_t("label.trades"),
        str(report.with_memory.total_trades),
        str(report.without_memory.total_trades),
        str(report.with_memory.total_trades - report.without_memory.total_trades),
    )
    table.add_row(
        ui_t("label.win_rate"),
        f"{report.with_memory.win_rate:.2%}",
        f"{report.without_memory.win_rate:.2%}",
        f"{report.with_memory.win_rate - report.without_memory.win_rate:.2%}",
    )
    table.add_row(
        ui_t("label.expectancy"),
        f"{report.with_memory.expectancy:.2f}",
        f"{report.without_memory.expectancy:.2f}",
        f"{report.with_memory.expectancy - report.without_memory.expectancy:.2f}",
    )
    table.add_row(
        ui_t("label.return"),
        f"{report.with_memory.total_return_pct:.2%}",
        f"{report.without_memory.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        ui_t("label.ending_equity"),
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
            f"# {ui_t('title.walk_forward_backtest')}: {report.symbol}",
            "",
            f"- {ui_t('label.interval')}: {report.interval}",
            f"- {ui_t('label.lookback')}: {report.lookback}",
            f"- {ui_t('label.warmup_bars')}: {report.warmup_bars}",
            f"- {ui_t('label.cycles')}: {report.total_cycles}",
            f"- {ui_t('label.trades')}: {report.total_trades}",
            f"- {ui_t('label.closed_trades')}: {report.closed_trades}",
            f"- {ui_t('label.win_rate')}: {report.win_rate:.2%}",
            f"- {ui_t('label.expectancy')}: {report.expectancy:.2f}",
            f"- {ui_t('label.total_return')}: {report.total_return_pct:.2%}",
            f"- {ui_t('label.max_drawdown')}: {report.max_drawdown_pct:.2%}",
            f"- {ui_t('label.exposure')}: {report.exposure_pct:.2%}",
        ]
    )
    return _write_summary(output, rendered)


def _write_summary(output: str | Path, rendered: str) -> str:
    path = Path(output)
    path.write_text(rendered, encoding="utf-8")
    return str(path)
