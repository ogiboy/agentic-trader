import os
import signal

import json
from pathlib import Path

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentic_trader.config import get_settings
from agentic_trader.agents.operator_chat import apply_preference_update, chat_with_persona, interpret_operator_instruction
from agentic_trader.backtest.walk_forward import run_walk_forward_backtest
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    ChatPersona,
    DailyRiskReport,
    OperatorInstruction,
    BacktestReport,
    RunRecord,
    RunArtifacts,
    ServiceEvent,
    ServiceStateSnapshot,
    TradeJournalEntry,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui import build_monitor_renderable, run_live_monitor, run_main_menu
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, run_service, start_background_service

app = typer.Typer(help="Agentic Trader CLI")
console = Console()


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(body, title=status, border_style=border_style)


def _render_execution_panels(order_id: str, artifacts: RunArtifacts) -> None:
    fallback_components: list[str] = artifacts.fallback_components()
    summary = Table(title="Execution Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Order ID", order_id)
    summary.add_row("Approved", str(artifacts.execution.approved))
    summary.add_row("Side", artifacts.execution.side)
    summary.add_row("Confidence", f"{artifacts.execution.confidence:.2f}")
    summary.add_row("Entry", f"{artifacts.execution.entry_price:.4f}")
    summary.add_row("Stop", f"{artifacts.execution.stop_loss:.4f}")
    summary.add_row("Take Profit", f"{artifacts.execution.take_profit:.4f}")
    summary.add_row(
        "Decision Path",
        "Fallback" if fallback_components else "LLM",
    )

    pipeline = Table(title="Pipeline")
    pipeline.add_column("Stage")
    pipeline.add_column("Source")
    pipeline.add_column("Notes")
    pipeline.add_row("Coordinator", artifacts.coordinator.source, artifacts.coordinator.fallback_reason or "Structured LLM response")
    pipeline.add_row("Regime", artifacts.regime.source, artifacts.regime.fallback_reason or "Structured LLM response")
    pipeline.add_row("Strategy", artifacts.strategy.source, artifacts.strategy.fallback_reason or "Structured LLM response")
    pipeline.add_row("Risk", artifacts.risk.source, artifacts.risk.fallback_reason or "Structured LLM response")
    pipeline.add_row("Manager", artifacts.manager.source, artifacts.manager.fallback_reason or "Structured LLM response")
    console.print(Columns([summary, pipeline]))

    if fallback_components:
        console.print(
            Panel(
                Text(
                    f"Fallback was used in: {', '.join(fallback_components)}",
                    style="yellow",
                ),
                title="Warning",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                Text("All agent stages completed through the LLM path.", style="green"),
                title="LLM Status",
                border_style="green",
            )
        )
    console.print(
        Panel(
            json.dumps(artifacts.model_dump(mode="json"), indent=2),
            title="Run Artifacts",
        )
    )


def _render_instruction(instruction: OperatorInstruction) -> None:
    table = Table(title="Operator Instruction")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Summary", instruction.summary)
    table.add_row("Update Preferences", str(instruction.should_update_preferences))
    table.add_row("Requires Confirmation", str(instruction.requires_confirmation))
    table.add_row("Rationale", instruction.rationale)
    table.add_row(
        "Preference Update",
        json.dumps(instruction.preference_update.model_dump(mode="json"), indent=2),
    )
    console.print(table)


def _render_service_state(state: ServiceStateSnapshot | None) -> None:
    if state is None:
        console.print(Panel("No runtime state recorded yet.", title="Service Status", border_style="yellow"))
        return

    table = Table(title="Service Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Service", state.service_name)
    table.add_row("State", state.state)
    table.add_row("Updated", state.updated_at)
    table.add_row("Started", state.started_at or "-")
    table.add_row("Heartbeat", state.last_heartbeat_at or "-")
    table.add_row("Continuous", str(state.continuous))
    table.add_row("Poll Seconds", str(state.poll_seconds) if state.poll_seconds is not None else "-")
    table.add_row("Cycle Count", str(state.cycle_count))
    table.add_row("Current Symbol", state.current_symbol or "-")
    table.add_row("PID", str(state.pid) if state.pid is not None else "-")
    table.add_row("Stop Requested", str(state.stop_requested))
    table.add_row("Message", state.message or "-")
    table.add_row("Last Error", state.last_error or "-")
    console.print(table)


def _render_service_events(events: list[ServiceEvent]) -> None:
    if not events:
        console.print(Panel("No runtime events recorded yet.", title="Runtime Events", border_style="yellow"))
        return

    table = Table(title="Runtime Events")
    table.add_column("Created")
    table.add_column("Level")
    table.add_column("Type")
    table.add_column("Cycle")
    table.add_column("Symbol")
    table.add_column("Message")
    for event in events:
        table.add_row(
            event.created_at,
            event.level,
            event.event_type,
            str(event.cycle_count) if event.cycle_count is not None else "-",
            event.symbol or "-",
            event.message,
        )
    console.print(table)


def _render_trade_journal(entries: list[TradeJournalEntry]) -> None:
    if not entries:
        console.print(Panel("No trade journal entries recorded yet.", title="Trade Journal", border_style="yellow"))
        return

    table = Table(title="Trade Journal")
    table.add_column("Opened")
    table.add_column("Symbol")
    table.add_column("Status")
    table.add_column("Side")
    table.add_column("Entry")
    table.add_column("Exit")
    table.add_column("PnL")
    table.add_column("Notes")
    for entry in entries:
        table.add_row(
            entry.opened_at,
            entry.symbol,
            entry.journal_status,
            entry.planned_side,
            f"{entry.entry_price:.4f}",
            f"{entry.exit_price:.4f}" if entry.exit_price is not None else "-",
            f"{entry.realized_pnl:.2f}" if entry.realized_pnl is not None else "-",
            entry.exit_reason or entry.notes or "-",
        )
    console.print(table)


def _render_risk_report(report: DailyRiskReport) -> None:
    table = Table(title=f"Daily Risk Report / {report.report_date}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Generated", report.generated_at)
    table.add_row("Cash", f"{report.cash:.2f}")
    table.add_row("Market Value", f"{report.market_value:.2f}")
    table.add_row("Equity", f"{report.equity:.2f}")
    table.add_row("Realized PnL", f"{report.realized_pnl:.2f}")
    table.add_row("Unrealized PnL", f"{report.unrealized_pnl:.2f}")
    table.add_row("Open Positions", str(report.open_positions))
    table.add_row("Fills Today", str(report.fills_today))
    table.add_row("Marks Recorded", str(report.marks_recorded))
    table.add_row("Daily Realized PnL", f"{report.daily_realized_pnl:.2f}")
    table.add_row("Gross Exposure", f"{report.gross_exposure_pct:.2%}")
    table.add_row("Largest Position", f"{report.largest_position_pct:.2%}")
    table.add_row("Drawdown From Peak", f"{report.drawdown_from_peak_pct:.2%}")
    console.print(table)
    if report.warnings:
        console.print(
            Panel(
                "\n".join(f"- {warning}" for warning in report.warnings),
                title="Risk Warnings",
                border_style="yellow",
            )
        )
    else:
        console.print(Panel("No elevated portfolio risk warnings for this report.", title="Risk Warnings", border_style="green"))


def _render_run_review(record: RunRecord) -> None:
    metadata = Table(title=f"Run Review / {record.run_id}")
    metadata.add_column("Field")
    metadata.add_column("Value")
    metadata.add_row("Created", record.created_at)
    metadata.add_row("Symbol", record.symbol)
    metadata.add_row("Interval", record.interval)
    metadata.add_row("Approved", str(record.approved))

    analysis = Table(title="Agent Decisions")
    analysis.add_column("Stage")
    analysis.add_column("Decision")
    analysis.add_column("Notes")
    analysis.add_row("Coordinator", record.artifacts.coordinator.market_focus, record.artifacts.coordinator.summary)
    analysis.add_row("Regime", record.artifacts.regime.regime, record.artifacts.regime.reasoning)
    analysis.add_row("Strategy", record.artifacts.strategy.strategy_family, record.artifacts.strategy.entry_logic)
    analysis.add_row("Risk", f"size={record.artifacts.risk.position_size_pct:.2%}", record.artifacts.risk.notes)
    analysis.add_row("Manager", record.artifacts.manager.action_bias, record.artifacts.manager.rationale)
    analysis.add_row("Execution", record.artifacts.execution.side, record.artifacts.execution.rationale)
    console.print(Columns([metadata, analysis]))
    console.print(
        Panel(
            record.artifacts.review.model_dump_json(indent=2),
            title="Review Note",
            border_style="cyan",
        )
    )


def _render_run_markdown(record: RunRecord) -> str:
    artifacts = record.artifacts
    lines = [
        f"# Run Review: {record.run_id}",
        "",
        "## Metadata",
        f"- Created: {record.created_at}",
        f"- Symbol: {record.symbol}",
        f"- Interval: {record.interval}",
        f"- Approved: {record.approved}",
        "",
        "## Coordinator",
        f"- Focus: {artifacts.coordinator.market_focus}",
        f"- Summary: {artifacts.coordinator.summary}",
        "",
        "## Regime",
        f"- Regime: {artifacts.regime.regime}",
        f"- Direction Bias: {artifacts.regime.direction_bias}",
        f"- Reasoning: {artifacts.regime.reasoning}",
        "",
        "## Strategy",
        f"- Family: {artifacts.strategy.strategy_family}",
        f"- Action: {artifacts.strategy.action}",
        f"- Entry Logic: {artifacts.strategy.entry_logic}",
        f"- Invalidation Logic: {artifacts.strategy.invalidation_logic}",
        "",
        "## Risk",
        f"- Position Size: {artifacts.risk.position_size_pct:.2%}",
        f"- Stop Loss: {artifacts.risk.stop_loss:.4f}",
        f"- Take Profit: {artifacts.risk.take_profit:.4f}",
        f"- Notes: {artifacts.risk.notes}",
        "",
        "## Manager",
        f"- Action Bias: {artifacts.manager.action_bias}",
        f"- Confidence Cap: {artifacts.manager.confidence_cap:.2f}",
        f"- Size Multiplier: {artifacts.manager.size_multiplier:.2f}",
        f"- Rationale: {artifacts.manager.rationale}",
        "",
        "## Execution",
        f"- Approved: {artifacts.execution.approved}",
        f"- Side: {artifacts.execution.side}",
        f"- Entry Price: {artifacts.execution.entry_price:.4f}",
        f"- Rationale: {artifacts.execution.rationale}",
        "",
        "## Review",
        f"- Summary: {artifacts.review.summary}",
        f"- Strengths: {', '.join(artifacts.review.strengths) or '-'}",
        f"- Warnings: {', '.join(artifacts.review.warnings) or '-'}",
        f"- Next Checks: {', '.join(artifacts.review.next_checks) or '-'}",
        "",
    ]
    return "\n".join(lines)


def _render_backtest_report(report: BacktestReport) -> None:
    summary = Table(title=f"Walk-Forward Backtest / {report.symbol}")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Interval", report.interval)
    summary.add_row("Lookback", report.lookback)
    summary.add_row("Warmup Bars", str(report.warmup_bars))
    summary.add_row("Cycles", str(report.total_cycles))
    summary.add_row("Trades", str(report.total_trades))
    summary.add_row("Closed Trades", str(report.closed_trades))
    summary.add_row("Win Rate", f"{report.win_rate:.2%}")
    summary.add_row("Expectancy", f"{report.expectancy:.2f}")
    summary.add_row("Total Return", f"{report.total_return_pct:.2%}")
    summary.add_row("Max Drawdown", f"{report.max_drawdown_pct:.2%}")
    summary.add_row("Exposure", f"{report.exposure_pct:.2%}")
    summary.add_row("Fallback Cycles", str(report.fallback_cycles))
    console.print(summary)

    trades = Table(title="Backtest Trades")
    trades.add_column("Entry")
    trades.add_column("Exit")
    trades.add_column("Side")
    trades.add_column("Entry Px")
    trades.add_column("Exit Px")
    trades.add_column("PnL")
    trades.add_column("Reason")
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


@app.command()
def doctor() -> None:
    """Validate local configuration and print runtime settings."""
    settings = get_settings()
    latest: str
    db_status = "ok"
    try:
        db = TradingDatabase(settings)
        latest = str(db.latest_order())
    except Exception as exc:
        latest = "unavailable"
        db_status = f"Database unavailable: {exc}"

    llm = LocalLLM(settings)
    health = llm.health_check()
    table = Table(title="Environment Check")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Model", settings.model_name)
    table.add_row("Base URL", settings.base_url)
    table.add_row("Runtime Dir", str(settings.runtime_dir))
    table.add_row("Database", str(settings.database_path))
    table.add_row("DB Status", db_status)
    table.add_row(
        "Ollama Reachable",
        "[green]yes[/green]" if health.service_reachable else "[red]no[/red]",
    )
    table.add_row(
        "Model Available",
        "[green]yes[/green]" if health.model_available else "[yellow]no[/yellow]",
    )
    table.add_row("LLM Status", health.message)
    table.add_row("Latest Order", latest)
    console.print(table)
    if health.service_reachable and health.model_available:
        console.print(
            _render_health_panel(
                "Ready",
                "Trading runtime can start with full LLM access.",
                border_style="green",
            )
        )
    else:
        console.print(
            _render_health_panel(
                "Blocked",
                "Trading runtime should not start until Ollama and the configured model are available.",
                border_style="red",
            )
        )


@app.command()
def run(
    symbol: str = typer.Option(..., help="Ticker symbol, for example AAPL or BTC-USD"),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h"),
    lookback: str = typer.Option("180d", help="Lookback window accepted by yfinance"),
) -> None:
    """Run one strict LLM-backed agent cycle and log a paper order."""
    settings = get_settings()
    try:
        ensure_llm_ready(settings)
        artifacts = run_once(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            allow_fallback=False,
        )
        order_id = persist_run(settings=settings, artifacts=artifacts)
        _render_execution_panels(order_id, artifacts)
    except Exception as exc:
        console.print(
            _render_health_panel(
                "Run Blocked",
                str(exc),
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


@app.command()
def launch(
    symbols: str = typer.Option(..., help="Comma-separated symbols, for example AAPL,MSFT,BTC-USD"),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h"),
    lookback: str = typer.Option("180d", help="Lookback window accepted by yfinance"),
    poll_seconds: int = typer.Option(300, help="Sleep between cycles in continuous mode."),
    continuous: bool = typer.Option(False, help="Keep the orchestrator running."),
    max_cycles: int | None = typer.Option(None, help="Optional cap for continuous mode."),
    background: bool = typer.Option(False, help="Spawn the orchestrator as a background service."),
) -> None:
    """Start the strict paper-trading runtime from the project root."""
    settings = get_settings()
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not symbol_list:
        raise typer.BadParameter("At least one symbol is required.")

    try:
        health = ensure_llm_ready(settings)
        console.print(
            _render_health_panel(
                "Runtime Gate Open",
                f"Ollama reachable at {health.base_url} and model {health.model_name} is available.",
                border_style="green",
            )
        )
        console.print(
            Panel(
                f"Symbols: {', '.join(symbol_list)}\nInterval: {interval}\nLookback: {lookback}\nContinuous: {continuous}\nPoll Seconds: {poll_seconds}\nBackground: {background}",
                title="Launch Plan",
                border_style="cyan",
            )
        )
        if background:
            if not continuous:
                raise typer.BadParameter("Background mode requires --continuous.")
            pid = start_background_service(
                settings=settings,
                symbols=symbol_list,
                interval=interval,
                lookback=lookback,
                poll_seconds=poll_seconds,
                max_cycles=max_cycles,
            )
            console.print(
                _render_health_panel(
                    "Background Service Started",
                    f"Orchestrator is running in the background with PID {pid}.",
                    border_style="green",
                )
            )
            return
        results = run_service(
            settings=settings,
            symbols=symbol_list,
            interval=interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            continuous=continuous,
            max_cycles=max_cycles,
        )
        if not results:
            console.print(
                _render_health_panel(
                    "Service Stopped",
                    "No new results were produced before the orchestrator stopped.",
                    border_style="yellow",
                )
            )
            return
        latest_result = results[-1]
        _render_execution_panels(latest_result.order_id, latest_result.artifacts)
    except Exception as exc:
        console.print(
            _render_health_panel(
                "Launch Blocked",
                str(exc),
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


@app.command()
def portfolio() -> None:
    """Show the current paper portfolio and open positions."""
    settings = get_settings()
    db = TradingDatabase(settings)
    snapshot = db.get_account_snapshot()
    positions = db.list_positions()

    summary = Table(title="Portfolio")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Cash", f"{snapshot.cash:.2f}")
    summary.add_row("Market Value", f"{snapshot.market_value:.2f}")
    summary.add_row("Equity", f"{snapshot.equity:.2f}")
    summary.add_row("Realized PnL", f"{snapshot.realized_pnl:.2f}")
    summary.add_row("Unrealized PnL", f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row("Open Positions", str(snapshot.open_positions))
    console.print(summary)

    positions_table = Table(title="Positions")
    positions_table.add_column("Symbol")
    positions_table.add_column("Quantity")
    positions_table.add_column("Average Price")
    positions_table.add_column("Market Price")
    positions_table.add_column("Market Value")
    positions_table.add_column("Unrealized PnL")
    for position in positions:
        positions_table.add_row(
            position.symbol,
            f"{position.quantity:.6f}",
            f"{position.average_price:.4f}",
            f"{position.market_price:.4f}",
            f"{position.market_value:.2f}",
            f"{position.unrealized_pnl:.2f}",
        )
    if positions:
        console.print(positions_table)
    else:
        console.print(Panel("No open positions.", title="Positions", border_style="yellow"))


@app.command()
def status() -> None:
    """Show the current orchestrator runtime state."""
    settings = get_settings()
    db = TradingDatabase(settings)
    _render_service_state(db.get_service_state())


@app.command()
def logs(limit: int = typer.Option(20, min=1, max=200, help="Maximum number of runtime events to show.")) -> None:
    """Show recent orchestrator runtime events."""
    settings = get_settings()
    db = TradingDatabase(settings)
    _render_service_events(db.list_service_events(limit=limit))


@app.command("journal")
def journal(limit: int = typer.Option(20, min=1, max=200, help="Maximum number of journal entries to show.")) -> None:
    """Show the latest trade journal entries."""
    settings = get_settings()
    db = TradingDatabase(settings)
    _render_trade_journal(db.list_trade_journal(limit=limit))


@app.command("risk-report")
def risk_report(
    report_date: str | None = typer.Option(None, help="UTC date in YYYY-MM-DD format. Defaults to today."),
) -> None:
    """Show a compact daily risk report for the paper portfolio."""
    settings = get_settings()
    db = TradingDatabase(settings)
    _render_risk_report(db.build_daily_risk_report(report_date=report_date))


@app.command("review-run")
def review_run(
    run_id: str | None = typer.Option(None, help="Run id to inspect. Defaults to the latest recorded run."),
) -> None:
    """Inspect the latest or a specific persisted run in detail."""
    settings = get_settings()
    db = TradingDatabase(settings)
    record = db.get_run(run_id) if run_id is not None else db.latest_run()
    if record is None:
        console.print(Panel("No persisted runs are available to review.", title="Run Review", border_style="yellow"))
        raise typer.Exit(code=0)
    _render_run_review(record)


@app.command("export-report")
def export_report(
    output: str = typer.Option(..., help="Output file path for the exported run review."),
    run_id: str | None = typer.Option(None, help="Run id to export. Defaults to the latest recorded run."),
) -> None:
    """Export a run review as Markdown."""
    settings = get_settings()
    db = TradingDatabase(settings)
    record = db.get_run(run_id) if run_id is not None else db.latest_run()
    if record is None:
        console.print(Panel("No persisted runs are available to export.", title="Export Blocked", border_style="yellow"))
        raise typer.Exit(code=1)
    rendered = _render_run_markdown(record)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    console.print(Panel(f"Run report written to {output}.", title="Exported", border_style="green"))


@app.command("backtest")
def backtest(
    symbol: str = typer.Option(..., help="Ticker symbol, for example AAPL or BTC-USD"),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h"),
    lookback: str = typer.Option("2y", help="Lookback window accepted by yfinance"),
    warmup_bars: int = typer.Option(120, min=60, help="Warmup bars before replay begins."),
    output: str | None = typer.Option(None, help="Optional Markdown output path for a compact backtest summary."),
) -> None:
    """Run a walk-forward replay using the current agent pipeline."""
    settings = get_settings()
    ensure_llm_ready(settings)
    report = run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=False,
    )
    _render_backtest_report(report)
    if output is not None:
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
                f"- Win Rate: {report.win_rate:.2%}",
                f"- Expectancy: {report.expectancy:.2f}",
                f"- Total Return: {report.total_return_pct:.2%}",
                f"- Max Drawdown: {report.max_drawdown_pct:.2%}",
                f"- Exposure: {report.exposure_pct:.2%}",
            ]
        )
        Path(output).write_text(rendered, encoding="utf-8")
        console.print(Panel(f"Backtest summary written to {output}.", title="Exported", border_style="green"))


@app.command()
def chat(
    persona: ChatPersona = typer.Option("operator_liaison", help="Which agent persona should answer."),
    message: str | None = typer.Option(None, help="Optional message. If omitted, an interactive prompt is shown."),
) -> None:
    """Talk to the read-only operator chat surface."""
    settings = get_settings()
    ensure_llm_ready(settings)
    db = TradingDatabase(settings)
    prompt = message or typer.prompt("Message")
    response = chat_with_persona(
        llm=LocalLLM(settings),
        db=db,
        settings=settings,
        persona=persona,
        user_message=prompt,
    )
    console.print(Panel(response, title=f"Chat / {persona}", border_style="cyan"))


@app.command()
def instruct(
    message: str = typer.Option(..., help="Natural-language operator instruction."),
    apply: bool = typer.Option(False, help="Apply the parsed preference update if one is proposed."),
) -> None:
    """Interpret a safe operator instruction and optionally apply it."""
    settings = get_settings()
    ensure_llm_ready(settings)
    db = TradingDatabase(settings)
    llm = LocalLLM(settings)
    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=message,
        allow_fallback=True,
    )
    _render_instruction(instruction)
    if apply and instruction.should_update_preferences:
        updated = apply_preference_update(db, instruction.preference_update)
        console.print(
            Panel(
                updated.model_dump_json(indent=2),
                title="Updated Preferences",
                border_style="green",
            )
        )


@app.command()
def monitor(refresh_seconds: float = typer.Option(1.0, min=0.2, help="Dashboard refresh interval in seconds.")) -> None:
    """Attach to the live runtime monitor."""
    settings = get_settings()
    db = TradingDatabase(settings)
    console.print(build_monitor_renderable(settings, db))
    run_live_monitor(settings, db, refresh_seconds=refresh_seconds)


@app.command("stop-service")
def stop_service(force: bool = typer.Option(False, help="Send SIGTERM after marking stop requested.")) -> None:
    """Request a graceful stop for the background orchestrator."""
    settings = get_settings()
    db = TradingDatabase(settings)
    state = db.get_service_state()
    if state is None or state.pid is None:
        console.print(_render_health_panel("Not Running", "No managed service is currently active.", border_style="yellow"))
        raise typer.Exit(code=0)

    db.request_stop_service()
    db.insert_service_event(
        level="warning",
        event_type="stop_requested",
        message="Stop requested by operator from the CLI.",
        cycle_count=state.cycle_count,
        symbol=state.current_symbol,
    )
    if force:
        os.kill(state.pid, signal.SIGTERM)
        db.insert_service_event(
            level="warning",
            event_type="signal_sent",
            message=f"SIGTERM sent to PID {state.pid}.",
            cycle_count=state.cycle_count,
            symbol=state.current_symbol,
        )
    console.print(
        _render_health_panel(
            "Stop Requested",
            f"Service PID {state.pid} was asked to stop gracefully.",
            border_style="yellow",
        )
    )


@app.command("service-run", hidden=True)
def service_run(
    symbols: str = typer.Option(...),
    interval: str = typer.Option("1d"),
    lookback: str = typer.Option("180d"),
    poll_seconds: int = typer.Option(300),
    max_cycles: int | None = typer.Option(None),
    continuous: bool = typer.Option(True),
) -> None:
    """Internal background worker entrypoint."""
    settings = get_settings()
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not symbol_list:
        raise typer.BadParameter("At least one symbol is required.")
    run_service(
        settings=settings,
        symbols=symbol_list,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )


@app.command()
def menu() -> None:
    """Open the interactive terminal control room."""
    run_main_menu()


@app.command("latest-order")
def latest_order() -> None:
    """Show the latest paper order."""
    settings = get_settings()
    db = TradingDatabase(settings)
    order = db.latest_order()
    if order is None:
        console.print("[yellow]No orders recorded yet.[/yellow]")
        raise typer.Exit(code=0)

    columns: list[str] = [
        "order_id",
        "created_at",
        "symbol",
        "side",
        "approved",
        "entry_price",
        "stop_loss",
        "take_profit",
        "position_size_pct",
        "confidence",
    ]
    table = Table(title="Latest Order")
    for column in columns:
        table.add_column(column)
    rendered_order = [str(value) for value in order]
    table.add_row(*rendered_order)
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
