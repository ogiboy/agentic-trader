import os
import signal
import shutil
import subprocess
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentic_trader.config import get_settings, Settings
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.backtest.walk_forward import (
    run_memory_ablation_backtest,
    run_backtest_comparison,
    run_walk_forward_backtest,
)
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.calendar import infer_market_session
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.memory.policy import memory_write_policy_snapshot
from agentic_trader.runtime_feed import (
    append_chat_history,
    read_service_events,
    read_service_state,
    read_chat_history,
    request_stop,
)
from agentic_trader.runtime_status import (
    build_agent_activity_view,
    build_runtime_status_view,
    is_process_alive,
)
from agentic_trader.schemas import (
    ChatPersona,
    DailyRiskReport,
    HistoricalMemoryMatch,
    InvestmentPreferences,
    MarketSessionStatus,
    OperatorInstruction,
    BacktestReport,
    BacktestAblationReport,
    BacktestComparisonReport,
    ChatHistoryEntry,
    ManagerDecision,
    PositionSnapshot,
    PortfolioSnapshot,
    RunRecord,
    RunReplay,
    RunReplayStage,
    RunArtifacts,
    ServiceEvent,
    ServiceStateSnapshot,
    TradeContextRecord,
    TradeJournalEntry,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui import build_monitor_renderable, run_live_monitor, run_main_menu
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import (
    ensure_llm_ready,
    restart_background_service,
    run_service,
    start_background_service,
)

app = typer.Typer(help="Agentic Trader CLI", invoke_without_command=True)
console = Console()

# Constants for CLI help text and labels (avoid duplication)
HELP_JSON = "Emit machine-readable JSON."
LABEL_STRUCTURED_LLM = "Structured LLM response"
LABEL_MARKET_VALUE = "Market Value"
LABEL_UNREALIZED_PNL = "Unrealized PnL"
LABEL_WIN_RATE = "Win Rate"
LABEL_OBSERVER_MODE = "Observer Mode"
HELP_SYMBOL = "Ticker symbol, for example AAPL or BTC-USD"
HELP_INTERVAL = "yfinance interval, for example 1d or 1h"
HELP_LOOKBACK = "Lookback window accepted by yfinance"
HELP_RUN_ID = "Run id to inspect. Defaults to the latest recorded run."
DB_LOCKED_MSG = "The runtime writer currently owns the database."


def _read_text_tail(path: Path | None, *, limit: int = 12) -> list[str]:
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


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
    pipeline.add_row(
        "Coordinator",
        artifacts.coordinator.source,
        artifacts.coordinator.fallback_reason or "Structured LLM response",
    )
    pipeline.add_row(
        "Regime",
        artifacts.regime.source,
        artifacts.regime.fallback_reason or "Structured LLM response",
    )
    pipeline.add_row(
        "Strategy",
        artifacts.strategy.source,
        artifacts.strategy.fallback_reason or "Structured LLM response",
    )
    pipeline.add_row(
        "Risk",
        artifacts.risk.source,
        artifacts.risk.fallback_reason or "Structured LLM response",
    )
    pipeline.add_row(
        "Manager",
        artifacts.manager.source,
        artifacts.manager.fallback_reason or "Structured LLM response",
    )
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
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                "No runtime state recorded yet.",
                title="Service Status",
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title="Service Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Service", snapshot.service_name)
    table.add_row("Runtime", view.runtime_state)
    table.add_row("Live Process", "yes" if view.live_process else "no")
    table.add_row("Last Recorded State", view.last_recorded_state or "-")
    table.add_row("Updated", snapshot.updated_at)
    table.add_row("Started", snapshot.started_at or "-")
    table.add_row("Heartbeat", snapshot.last_heartbeat_at or "-")
    table.add_row(
        "Heartbeat Age", f"{view.age_seconds}s" if view.age_seconds is not None else "-"
    )
    table.add_row("Continuous", str(snapshot.continuous))
    table.add_row(
        "Poll Seconds",
        str(snapshot.poll_seconds) if snapshot.poll_seconds is not None else "-",
    )
    table.add_row("Cycle Count", str(snapshot.cycle_count))
    table.add_row("Symbols", ", ".join(snapshot.symbols) or "-")
    table.add_row("Interval", snapshot.interval or "-")
    table.add_row("Lookback", snapshot.lookback or "-")
    table.add_row(
        "Max Cycles", str(snapshot.max_cycles) if snapshot.max_cycles is not None else "-"
    )
    table.add_row("Current Symbol", snapshot.current_symbol or "-")
    table.add_row("PID", str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row("Stop Requested", str(snapshot.stop_requested))
    table.add_row("Status Note", view.status_message)
    table.add_row("Last Recorded Message", snapshot.message or "-")
    table.add_row("Last Recorded Error", snapshot.last_error or "-")
    console.print(table)


def _render_service_events(events: list[ServiceEvent]) -> None:
    if not events:
        console.print(
            Panel(
                "No runtime events recorded yet.",
                title="Runtime Events",
                border_style="yellow",
            )
        )
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
        console.print(
            Panel(
                "No trade journal entries recorded yet.",
                title="Trade Journal",
                border_style="yellow",
            )
        )
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
        console.print(
            Panel(
                "No elevated portfolio risk warnings for this report.",
                title="Risk Warnings",
                border_style="green",
            )
        )


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
    analysis.add_row(
        "Coordinator",
        record.artifacts.coordinator.market_focus,
        record.artifacts.coordinator.summary,
    )
    analysis.add_row(
        "Regime", record.artifacts.regime.regime, record.artifacts.regime.reasoning
    )
    analysis.add_row(
        "Strategy",
        record.artifacts.strategy.strategy_family,
        record.artifacts.strategy.entry_logic,
    )
    analysis.add_row(
        "Risk",
        f"size={record.artifacts.risk.position_size_pct:.2%}",
        record.artifacts.risk.notes,
    )
    analysis.add_row(
        "Consensus",
        record.artifacts.consensus.alignment_level,
        record.artifacts.consensus.summary or "-",
    )
    analysis.add_row(
        "Manager",
        record.artifacts.manager.action_bias,
        record.artifacts.manager.rationale,
    )
    analysis.add_row(
        "Execution",
        record.artifacts.execution.side,
        record.artifacts.execution.rationale,
    )
    console.print(Columns([metadata, analysis]))
    console.print(
        Panel(
            "\n".join(f"- {note}" for note in _manager_override_notes(record.artifacts)),
            title="Manager Override Notes",
            border_style="yellow",
        )
    )
    console.print(_manager_conflicts_panel(record.artifacts.manager))
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
        "## Consensus",
        f"- Alignment: {artifacts.consensus.alignment_level}",
        f"- Summary: {artifacts.consensus.summary or '-'}",
        f"- Supporting Roles: {', '.join(artifacts.consensus.supporting_roles) or '-'}",
        f"- Dissenting Roles: {', '.join(artifacts.consensus.dissenting_roles) or '-'}",
        f"- Reasons: {', '.join(artifacts.consensus.reasons) or '-'}",
        "",
        "## Manager",
        f"- Action Bias: {artifacts.manager.action_bias}",
        f"- Confidence Cap: {artifacts.manager.confidence_cap:.2f}",
        f"- Size Multiplier: {artifacts.manager.size_multiplier:.2f}",
        f"- Rationale: {artifacts.manager.rationale}",
        f"- Override Applied: {artifacts.manager.override_applied}",
        "",
        "## Manager Conflicts",
    ]
    if artifacts.manager.conflicts:
        for conflict in artifacts.manager.conflicts:
            lines.append(
                f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
            )
            lines.append(f"  - Specialist: {conflict.specialist_view}")
            lines.append(f"  - Manager: {conflict.manager_resolution}")
    else:
        lines.append("- None detected.")
    lines.extend(
        [
            "",
            "## Manager Resolution Notes",
            *(
                [f"- {note}" for note in _manager_resolution_notes(artifacts)]
                if _manager_resolution_notes(artifacts)
                else ["- No additional manager resolution notes."]
            ),
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
    )
    return "\n".join(lines)


def _manager_override_notes(artifacts: RunArtifacts) -> list[str]:
    notes: list[str] = []
    if artifacts.manager.action_bias != artifacts.strategy.action:
        notes.append(
            f"Manager bias {artifacts.manager.action_bias} diverged from strategy action {artifacts.strategy.action}."
        )
    if artifacts.manager.confidence_cap < artifacts.strategy.confidence:
        notes.append(
            f"Manager confidence cap {artifacts.manager.confidence_cap:.2f} tightened strategy confidence {artifacts.strategy.confidence:.2f}."
        )
    if artifacts.manager.size_multiplier < 1.0:
        notes.append(
            f"Manager size multiplier {artifacts.manager.size_multiplier:.2f} reduced the planned position size."
        )
    if artifacts.execution.approved != artifacts.manager.approved:
        notes.append(
            f"Execution approval {artifacts.execution.approved} differed from manager approval {artifacts.manager.approved}."
        )
    if not notes:
        notes.append("Manager accepted the specialist plan without additional overrides.")
    return notes


def _manager_resolution_notes(artifacts: RunArtifacts) -> list[str]:
    return artifacts.manager.resolution_notes or _manager_override_notes(artifacts)


def _manager_conflicts_panel(manager: ManagerDecision) -> Panel:
    if not manager.conflicts:
        body = "\n".join(f"- {note}" for note in manager.resolution_notes) or (
            "- Manager accepted the specialist plan without additional overrides."
        )
        return Panel(body, title="Manager Conflicts", border_style="green")

    lines: list[str] = []
    for conflict in manager.conflicts:
        lines.append(
            f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
        )
        lines.append(f"  Specialist: {conflict.specialist_view}")
        lines.append(f"  Manager: {conflict.manager_resolution}")
    if manager.resolution_notes:
        lines.append("")
        lines.append("Resolution Notes:")
        lines.extend(f"- {note}" for note in manager.resolution_notes)
    return Panel("\n".join(lines), title="Manager Conflicts", border_style="yellow")


def _render_run_trace(record: RunRecord) -> None:
    table = Table(title=f"Agent Trace / {record.run_id}")
    table.add_column("Role")
    table.add_column("Model")
    table.add_column("Fallback")
    table.add_column("Output Preview")
    for trace in record.artifacts.agent_traces:
        preview = trace.output_json.replace("\n", " ")[:120]
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback), preview)
    console.print(table)
    for trace in record.artifacts.agent_traces:
        console.print(
            Panel(
                f"[bold]Context[/bold]\n{trace.context_json}\n\n[bold]Output[/bold]\n{trace.output_json}",
                title=f"Trace / {trace.role}",
                border_style="cyan" if not trace.used_fallback else "yellow",
            )
        )


def _render_run_replay(replay: RunReplay) -> None:
    summary = Table(title=f"Memory-Aware Replay / {replay.run_id}")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Created", replay.created_at)
    summary.add_row("Symbol", replay.symbol)
    summary.add_row("Interval", replay.interval)
    summary.add_row("Approved", str(replay.approved))
    summary.add_row("Final Side", replay.final_side)
    summary.add_row("Final Rationale", replay.final_rationale)
    summary.add_row("Consensus", replay.consensus.alignment_level)
    summary.add_row(
        "Multi-Timeframe",
        f"{replay.snapshot.mtf_alignment} @ {replay.snapshot.higher_timeframe} ({replay.snapshot.mtf_confidence:.2f})",
    )
    console.print(summary)
    console.print(
        Panel(
            "\n".join(f"- {note}" for note in replay.manager_override_notes),
            title="Manager Override Notes",
            border_style="yellow",
        )
    )
    if replay.manager_conflicts:
        lines: list[str] = []
        for conflict in replay.manager_conflicts:
            lines.append(
                f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
            )
            lines.append(f"  Specialist: {conflict.specialist_view}")
            lines.append(f"  Manager: {conflict.manager_resolution}")
        if replay.manager_resolution_notes:
            lines.append("")
            lines.append("Resolution Notes:")
            lines.extend(f"- {note}" for note in replay.manager_resolution_notes)
        console.print(
            Panel(
                "\n".join(lines),
                title="Manager Conflict Replay",
                border_style="yellow",
            )
        )

    stage_table = Table(title="Replay Stages")
    stage_table.add_column("Role")
    stage_table.add_column("Model")
    stage_table.add_column("Fallback")
    stage_table.add_column("Memories")
    stage_table.add_column("Tools")
    stage_table.add_column("Output Preview")
    for stage in replay.stages:
        output_preview = (
            json.dumps(stage.output, indent=2)
            if isinstance(stage.output, dict)
            else stage.output
        ).replace("\n", " ")[:120]
        stage_table.add_row(
            stage.role,
            stage.model_name,
            str(stage.used_fallback),
            str(len(stage.retrieved_memories)),
            str(len(stage.tool_outputs)),
            output_preview,
        )
    console.print(stage_table)


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


def _render_backtest_comparison(report: BacktestComparisonReport) -> None:
    table = Table(title=f"Backtest Comparison / {report.symbol}")
    table.add_column("Metric")
    table.add_column("Agent")
    table.add_column("Baseline")
    table.add_column("Delta")
    table.add_row(
        "Trades",
        str(report.agent.total_trades),
        str(report.baseline.total_trades),
        str(report.agent.total_trades - report.baseline.total_trades),
    )
    table.add_row(
        "Closed Trades",
        str(report.agent.closed_trades),
        str(report.baseline.closed_trades),
        str(report.agent.closed_trades - report.baseline.closed_trades),
    )
    table.add_row(
        "Win Rate",
        f"{report.agent.win_rate:.2%}",
        f"{report.baseline.win_rate:.2%}",
        f"{report.agent.win_rate - report.baseline.win_rate:.2%}",
    )
    table.add_row(
        "Expectancy",
        f"{report.agent.expectancy:.2f}",
        f"{report.baseline.expectancy:.2f}",
        f"{report.agent.expectancy - report.baseline.expectancy:.2f}",
    )
    table.add_row(
        "Return",
        f"{report.agent.total_return_pct:.2%}",
        f"{report.baseline.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        "Max Drawdown",
        f"{report.agent.max_drawdown_pct:.2%}",
        f"{report.baseline.max_drawdown_pct:.2%}",
        f"{report.agent.max_drawdown_pct - report.baseline.max_drawdown_pct:.2%}",
    )
    table.add_row(
        "Exposure",
        f"{report.agent.exposure_pct:.2%}",
        f"{report.baseline.exposure_pct:.2%}",
        f"{report.agent.exposure_pct - report.baseline.exposure_pct:.2%}",
    )
    table.add_row(
        "Ending Equity",
        f"{report.agent.ending_equity:.2f}",
        f"{report.baseline.ending_equity:.2f}",
        f"{report.ending_equity_delta:.2f}",
    )
    console.print(table)


def _render_backtest_ablation(report: BacktestAblationReport) -> None:
    table = Table(title=f"Backtest Memory Ablation / {report.symbol}")
    table.add_column("Metric")
    table.add_column("With Memory")
    table.add_column("Without Memory")
    table.add_column("Delta")
    table.add_row(
        "Trades",
        str(report.with_memory.total_trades),
        str(report.without_memory.total_trades),
        str(report.with_memory.total_trades - report.without_memory.total_trades),
    )
    table.add_row(
        "Win Rate",
        f"{report.with_memory.win_rate:.2%}",
        f"{report.without_memory.win_rate:.2%}",
        f"{report.with_memory.win_rate - report.without_memory.win_rate:.2%}",
    )
    table.add_row(
        "Expectancy",
        f"{report.with_memory.expectancy:.2f}",
        f"{report.without_memory.expectancy:.2f}",
        f"{report.with_memory.expectancy - report.without_memory.expectancy:.2f}",
    )
    table.add_row(
        "Return",
        f"{report.with_memory.total_return_pct:.2%}",
        f"{report.without_memory.total_return_pct:.2%}",
        f"{report.total_return_delta_pct:.2%}",
    )
    table.add_row(
        "Ending Equity",
        f"{report.with_memory.ending_equity:.2f}",
        f"{report.without_memory.ending_equity:.2f}",
        f"{report.ending_equity_delta:.2f}",
    )
    console.print(table)


def _render_memory_matches(matches) -> None:
    if not matches:
        console.print(
            Panel(
                "No historical memories are available yet.",
                title="Memory Explorer",
                border_style="yellow",
            )
        )
        return
    table = Table(title="Memory Explorer")
    table.add_column("Created")
    table.add_column("Symbol")
    table.add_column("Score")
    table.add_column("Source")
    table.add_column("Regime")
    table.add_column("Strategy")
    table.add_column("Bias")
    table.add_column("Approved")
    for match in matches:
        table.add_row(
            match.created_at,
            match.symbol,
            f"{match.similarity_score:.2f}",
            match.retrieval_source,
            match.regime,
            match.strategy_family,
            match.manager_bias,
            str(match.approved),
        )
    console.print(table)


def _emit_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2))


def _open_db(settings: Settings, *, read_only: bool = False) -> TradingDatabase:
    return TradingDatabase(settings, read_only=read_only)


def _portfolio_payload(settings: Settings) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            snapshot = db.get_account_snapshot()
            positions = db.list_positions()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        snapshot = PortfolioSnapshot(
            cash=0.0,
            market_value=0.0,
            equity=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_positions=0,
        )
        positions = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "snapshot": snapshot.model_dump(mode="json"),
        "positions": [position.model_dump(mode="json") for position in positions],
    }


def _preferences_payload(settings: Settings) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        preferences = InvestmentPreferences()
        available = False
        error = str(exc)
    payload = preferences.model_dump(mode="json")
    payload["available"] = available
    payload["error"] = error
    return payload


def _journal_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            entries = db.list_trade_journal(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def _risk_report_payload(
    settings: Settings, *, report_date: str | None = None
) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            report = db.build_daily_risk_report(report_date=report_date)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        report = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "report": report.model_dump(mode="json") if report is not None else None,
    }


def _run_record_payload(settings: Settings, *, run_id: str | None = None) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = db.get_run(run_id) if run_id is not None else db.latest_run()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


def _trade_context_payload(
    settings: Settings, *, trade_id: str | None = None
) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = (
                db.get_trade_context(trade_id)
                if trade_id is not None
                else db.latest_trade_context()
            )
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


def _service_supervisor_payload(settings: Settings) -> dict[str, object]:
    state = read_service_state(settings)
    view = build_runtime_status_view(state)
    stdout_path = Path(state.stdout_log_path) if state and state.stdout_log_path else None
    stderr_path = Path(state.stderr_log_path) if state and state.stderr_log_path else None
    return {
        "runtime_state": view.runtime_state,
        "live_process": view.live_process,
        "is_stale": view.is_stale,
        "age_seconds": view.age_seconds,
        "status_message": view.status_message,
        "state": state.model_dump(mode="json") if state is not None else None,
        "stdout_tail": _read_text_tail(stdout_path),
        "stderr_tail": _read_text_tail(stderr_path),
    }


def _broker_payload(settings: Settings) -> dict[str, object]:
    return broker_runtime_payload(settings)


def _default_symbol_from_preferences(preferences: InvestmentPreferences) -> str:
    if "BIST" in preferences.exchanges or "TR" in preferences.regions:
        return "THYAO.IS"
    if (
        "NASDAQ" in preferences.exchanges
        or "NYSE" in preferences.exchanges
        or "US" in preferences.regions
    ):
        return "AAPL"
    return "BTC-USD"


def _calendar_payload(settings: Settings, *, symbol: str | None = None) -> dict[str, object]:
    try:
        preferences = InvestmentPreferences()
        record = None
        db = _open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
            record = db.latest_run()
        finally:
            db.close()
        resolved_symbol = symbol or (
            record.symbol
            if record is not None
            else _default_symbol_from_preferences(preferences)
        )
        session = infer_market_session(symbol=resolved_symbol, preferences=preferences)
        available = True
        error = None
    except Exception as exc:
        session = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "session": session.model_dump(mode="json") if session is not None else None,
    }


def _news_payload(settings: Settings, *, symbol: str | None = None) -> dict[str, object]:
    try:
        preferences = InvestmentPreferences()
        record = None
        db = _open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
            record = db.latest_run()
        finally:
            db.close()
        resolved_symbol = symbol or (
            record.symbol
            if record is not None
            else _default_symbol_from_preferences(preferences)
        )
        headlines = fetch_news_brief(resolved_symbol, settings)
        available = True
        error = None
    except Exception as exc:
        resolved_symbol = symbol
        headlines = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "mode": settings.news_mode,
        "symbol": resolved_symbol,
        "headlines": [item.model_dump(mode="json") for item in headlines],
    }


def _market_cache_payload(settings: Settings) -> dict[str, object]:
    settings.ensure_directories()
    cache_dir = settings.market_data_cache_dir
    entries = []
    for path in sorted(
        cache_dir.glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True
    ):
        entries.append(
            {
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
            }
        )
    return {
        "mode": settings.market_data_mode,
        "cache_dir": str(cache_dir),
        "count": len(entries),
        "entries": entries,
    }


def _memory_explorer_payload(
    settings: Settings,
    *,
    symbol: str | None = None,
    interval: str | None = None,
    lookback: str = "180d",
    limit: int = 5,
    use_latest_run: bool = False,
) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            snapshot = None
            resolved_symbol = symbol
            resolved_interval = interval
            if use_latest_run or resolved_symbol is None:
                record = db.latest_run()
                if record is not None:
                    snapshot = record.artifacts.snapshot
                    resolved_symbol = snapshot.symbol
                    resolved_interval = snapshot.interval
            if snapshot is None:
                if resolved_symbol is None or resolved_interval is None:
                    raise ValueError(
                        "A symbol and interval are required when no latest run snapshot is available."
                    )
                frame = fetch_ohlcv(
                    resolved_symbol,
                    interval=resolved_interval,
                    lookback=lookback,
                    settings=settings,
                )
                snapshot = build_snapshot(
                    frame, symbol=resolved_symbol, interval=resolved_interval
                )
            matches = retrieve_similar_memories(db, snapshot, limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        snapshot = None
        matches = []
        available = False
        error = str(exc)

    return {
        "available": available,
        "error": error,
        "snapshot": snapshot.model_dump(mode="json") if snapshot is not None else None,
        "matches": [match.model_dump(mode="json") for match in matches],
    }


def _retrieval_inspection_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    record_payload = _run_record_payload(settings, run_id=run_id)
    record_json = record_payload["record"]
    if record_payload["available"] is False or record_json is None:
        return {
            "available": bool(record_payload["available"]),
            "error": record_payload["error"],
            "run_id": (
                record_json["run_id"]
                if isinstance(record_json, dict) and "run_id" in record_json
                else None
            ),
            "stages": [],
        }

    record = RunRecord.model_validate(record_json)
    stages: list[dict[str, object]] = []
    for trace in record.artifacts.agent_traces:
        context = json.loads(trace.context_json)
        stages.append(
            {
                "role": trace.role,
                "model_name": trace.model_name,
                "used_fallback": trace.used_fallback,
                "retrieved_memories": context.get("retrieved_memories", []),
                "memory_notes": context.get("memory_notes", []),
                "shared_memory_bus": context.get("shared_memory_bus", []),
                "recent_runs": context.get("recent_runs", []),
                "tool_outputs": context.get("tool_outputs", []),
            }
        )

    return {
        "available": True,
        "error": None,
        "run_id": record.run_id,
        "symbol": record.symbol,
        "interval": record.interval,
        "stages": stages,
    }


def _chat_history_payload(settings: Settings, *, limit: int = 12) -> dict[str, object]:
    try:
        entries = read_chat_history(settings, limit=limit)
        available = True
        error = None
    except Exception as exc:
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def _run_replay_payload(settings: Settings, *, run_id: str | None = None) -> dict[str, object]:
    record_payload = _run_record_payload(settings, run_id=run_id)
    record_json = record_payload["record"]
    if record_payload["available"] is False or record_json is None:
        return {
            "available": bool(record_payload["available"]),
            "error": record_payload["error"],
            "replay": None,
        }

    record = RunRecord.model_validate(record_json)
    stages: list[RunReplayStage] = []
    for trace in record.artifacts.agent_traces:
        context = json.loads(trace.context_json)
        try:
            output: dict[str, object] | str = json.loads(trace.output_json)
        except json.JSONDecodeError:
            output = trace.output_json
        stages.append(
            RunReplayStage(
                role=trace.role,
                model_name=trace.model_name,
                used_fallback=trace.used_fallback,
                market_session=context.get("market_session"),
                retrieved_memories=context.get("retrieved_memories", []),
                memory_notes=context.get("memory_notes", []),
                shared_memory_bus=context.get("shared_memory_bus", []),
                recent_runs=context.get("recent_runs", []),
                tool_outputs=context.get("tool_outputs", []),
                upstream_context=context.get("upstream_context", {}),
                output=output,
            )
        )

    replay = RunReplay(
        run_id=record.run_id,
        created_at=record.created_at,
        symbol=record.symbol,
        interval=record.interval,
        approved=record.approved,
        final_side=record.artifacts.execution.side,
        final_rationale=record.artifacts.execution.rationale,
        snapshot=record.artifacts.snapshot,
        consensus=record.artifacts.consensus,
        manager_override_notes=_manager_override_notes(record.artifacts),
        manager_conflicts=record.artifacts.manager.conflicts,
        manager_resolution_notes=_manager_resolution_notes(record.artifacts),
        stages=stages,
    )
    return {
        "available": True,
        "error": None,
        "replay": replay.model_dump(mode="json"),
    }


@app.callback()
def app_entry(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ink_tui()


@app.command()
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Validate local configuration and print runtime settings."""
    settings = get_settings()
    latest: str
    db_status = "ok"
    try:
        db = _open_db(settings, read_only=True)
        latest = str(db.latest_order())
    except Exception as exc:
        latest = "unavailable"
        db_status = f"Database unavailable: {exc}"

    llm = LocalLLM(settings)
    health = llm.health_check()
    payload = {
        "model": settings.model_name,
        "base_url": settings.base_url,
        "runtime_dir": str(settings.runtime_dir),
        "database": str(settings.database_path),
        "db_status": db_status,
        "model_routing": settings.model_routing(),
        "ollama_reachable": health.service_reachable,
        "model_available": health.model_available,
        "llm_status": health.message,
        "latest_order": latest,
    }
    if json_output:
        _emit_json(payload)
        return

    table = Table(title="Environment Check")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Model", settings.model_name)
    table.add_row("Base URL", settings.base_url)
    table.add_row("Runtime Dir", str(settings.runtime_dir))
    table.add_row("Database", str(settings.database_path))
    table.add_row("DB Status", db_status)
    table.add_row("Model Routing", json.dumps(settings.model_routing(), indent=2))
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
    symbols: str = typer.Option(
        ..., help="Comma-separated symbols, for example AAPL,MSFT,BTC-USD"
    ),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h"),
    lookback: str = typer.Option("180d", help="Lookback window accepted by yfinance"),
    poll_seconds: int = typer.Option(
        300, help="Sleep between cycles in continuous mode."
    ),
    continuous: bool = typer.Option(False, help="Keep the orchestrator running."),
    max_cycles: int | None = typer.Option(
        None, help="Optional cap for continuous mode."
    ),
    background: bool = typer.Option(
        False, help="Spawn the orchestrator as a background service."
    ),
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
                continuous=continuous,
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
def portfolio(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Show the current paper portfolio and open positions."""
    settings = get_settings()
    payload = _portfolio_payload(settings)
    snapshot = PortfolioSnapshot.model_validate(payload["snapshot"])
    positions = [
        PositionSnapshot.model_validate(position) for position in payload["positions"]
    ]
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Portfolio view is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

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
        console.print(
            Panel("No open positions.", title="Positions", border_style="yellow")
        )


@app.command()
def status(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Show the current orchestrator runtime state."""
    settings = get_settings()
    state = read_service_state(settings)
    if json_output:
        view = build_runtime_status_view(state)
        _emit_json(
            {
                "runtime_state": view.runtime_state,
                "live_process": view.live_process,
                "is_stale": view.is_stale,
                "age_seconds": view.age_seconds,
                "status_message": view.status_message,
                "state": (
                    view.state.model_dump(mode="json")
                    if view.state is not None
                    else None
                ),
            }
        )
        return
    _render_service_state(state)


@app.command("supervisor-status")
def supervisor_status(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Show daemon supervision metadata and recent background log tails."""
    settings = get_settings()
    payload = _service_supervisor_payload(settings)
    if json_output:
        _emit_json(payload)
        return

    state_json = payload["state"]
    if state_json is None:
        console.print(
            Panel(
                "No runtime state has been recorded yet.",
                title="Service Supervisor",
                border_style="yellow",
            )
        )
        return

    state = ServiceStateSnapshot.model_validate(state_json)
    table = Table(title="Service Supervisor")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Runtime", str(payload["runtime_state"]))
    table.add_row("Live Process", "yes" if payload["live_process"] else "no")
    table.add_row("Background Mode", str(state.background_mode))
    table.add_row("Launch Count", str(state.launch_count))
    table.add_row("Restart Count", str(state.restart_count))
    table.add_row("Last Terminal State", state.last_terminal_state or "-")
    table.add_row("Last Terminal At", state.last_terminal_at or "-")
    table.add_row("Stdout Log", state.stdout_log_path or "-")
    table.add_row("Stderr Log", state.stderr_log_path or "-")
    table.add_row("Status Note", str(payload["status_message"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stdout_tail"])) or "No stdout log lines yet.",
            title="Service Stdout Tail",
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stderr_tail"])) or "No stderr log lines yet.",
            title="Service Stderr Tail",
            border_style="yellow",
        )
    )


@app.command("broker-status")
def broker_status(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Show the active broker backend and execution safety gates."""
    settings = get_settings()
    payload = _broker_payload(settings)
    if json_output:
        _emit_json(payload)
        return

    table = Table(title="Broker Status")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Backend", str(payload["backend"]))
    table.add_row("State", str(payload["state"]))
    table.add_row("Live Execution Enabled", str(payload["live_execution_enabled"]))
    table.add_row("Kill Switch Active", str(payload["kill_switch_active"]))
    table.add_row("Live Requested", str(payload["live_requested"]))
    table.add_row("Live Ready", str(payload["live_ready"]))
    table.add_row("Message", str(payload["message"]))
    console.print(table)


@app.command()
def logs(
    limit: int = typer.Option(
        20, min=1, max=200, help="Maximum number of runtime events to show."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show recent orchestrator runtime events."""
    settings = get_settings()
    events = read_service_events(settings, limit=limit)
    if json_output:
        _emit_json([event.model_dump(mode="json") for event in events])
        return
    _render_service_events(events)


@app.command("dashboard-snapshot")
def dashboard_snapshot(
    log_limit: int = typer.Option(
        14, min=1, max=100, help="Maximum number of runtime events to include."
    ),
) -> None:
    """Emit the full Ink dashboard snapshot as a single JSON payload."""
    settings = get_settings()
    llm = LocalLLM(settings)
    health = llm.health_check()
    state = read_service_state(settings)
    view = build_runtime_status_view(state)

    latest: str
    db_status = "ok"
    try:
        db = _open_db(settings, read_only=True)
        try:
            latest = str(db.latest_order())
        finally:
            db.close()
    except Exception as exc:
        latest = "unavailable"
        db_status = f"Database unavailable: {exc}"

    doctor_payload = {
        "model": settings.model_name,
        "base_url": settings.base_url,
        "runtime_dir": str(settings.runtime_dir),
        "database": str(settings.database_path),
        "db_status": db_status,
        "model_routing": settings.model_routing(),
        "ollama_reachable": health.service_reachable,
        "model_available": health.model_available,
        "llm_status": health.message,
        "latest_order": latest,
    }
    status_payload = {
        "runtime_state": view.runtime_state,
        "live_process": view.live_process,
        "is_stale": view.is_stale,
        "age_seconds": view.age_seconds,
        "status_message": view.status_message,
        "state": view.state.model_dump(mode="json") if view.state is not None else None,
    }

    events = read_service_events(settings, limit=log_limit)
    activity = build_agent_activity_view(view.state, events)

    _emit_json(
        {
            "doctor": doctor_payload,
            "status": status_payload,
            "supervisor": _service_supervisor_payload(settings),
            "broker": _broker_payload(settings),
            "logs": [event.model_dump(mode="json") for event in events],
            "agentActivity": {
                "cycle_count": activity.cycle_count,
                "current_symbol": activity.current_symbol,
                "current_stage": activity.current_stage,
                "current_stage_status": activity.current_stage_status,
                "current_stage_message": activity.current_stage_message,
                "last_completed_stage": activity.last_completed_stage,
                "last_completed_message": activity.last_completed_message,
                "last_outcome_type": activity.last_outcome_type,
                "last_outcome_message": activity.last_outcome_message,
                "stage_statuses": [
                    {
                        "stage": stage.stage,
                        "status": stage.status,
                        "message": stage.message,
                        "created_at": stage.created_at,
                        "cycle_count": stage.cycle_count,
                        "symbol": stage.symbol,
                    }
                    for stage in activity.stage_statuses
                ],
                "recent_stage_events": [
                    {
                        "stage": stage.stage,
                        "status": stage.status,
                        "message": stage.message,
                        "created_at": stage.created_at,
                        "cycle_count": stage.cycle_count,
                        "symbol": stage.symbol,
                    }
                    for stage in activity.recent_stage_events
                ],
            },
            "portfolio": _portfolio_payload(settings),
            "preferences": _preferences_payload(settings),
            "journal": _journal_payload(settings, limit=8),
            "riskReport": _risk_report_payload(settings),
            "review": _run_record_payload(settings),
            "trace": _run_record_payload(settings),
            "tradeContext": _trade_context_payload(settings),
            "replay": _run_replay_payload(settings),
            "memoryExplorer": _memory_explorer_payload(
                settings, use_latest_run=True, limit=5
            ),
            "retrievalInspection": _retrieval_inspection_payload(settings),
            "memoryPolicy": memory_write_policy_snapshot(),
            "chatHistory": _chat_history_payload(settings),
            "calendar": _calendar_payload(settings),
            "news": _news_payload(settings),
            "marketCache": _market_cache_payload(settings),
        }
    )


@app.command("calendar-status")
def calendar_status(
    symbol: str | None = typer.Option(
        None,
        help="Optional ticker symbol. Defaults to the latest run symbol or preference-derived default.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show the inferred market session state for a symbol."""
    settings = get_settings()
    payload = _calendar_payload(settings, symbol=symbol)
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"] or payload["session"] is None:
        console.print(
            Panel(
                f"Calendar status is temporarily unavailable.\n\n{payload['error']}",
                title="Calendar Status",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    session = MarketSessionStatus.model_validate(payload["session"])
    table = Table(title=f"Market Session / {session.symbol}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Venue", session.venue)
    table.add_row("Asset Class", session.asset_class)
    table.add_row("Timezone", session.timezone)
    table.add_row("State", session.session_state)
    table.add_row("Tradable Now", str(session.tradable_now))
    table.add_row("Note", session.note)
    console.print(table)


@app.command("news-brief")
def news_brief(
    symbol: str | None = typer.Option(None, help="Optional symbol override."),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show news tool output for the resolved symbol."""
    settings = get_settings()
    payload = _news_payload(settings, symbol=symbol)
    if json_output:
        _emit_json(payload)
        return
    table = Table(title=f"News Brief / {payload['symbol'] or '-'}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Mode", str(payload["mode"]))
    table.add_row("Available", str(payload["available"]))
    table.add_row("Headlines", str(len(payload["headlines"])))
    console.print(table)
    headlines = payload["headlines"]
    if not headlines:
        console.print(
            Panel(
                "No tool-driven news headlines are available for this symbol.",
                title="News Tool",
                border_style="yellow",
            )
        )
        return
    for headline in headlines:
        console.print(
            Panel(
                f"{headline['publisher']} | {headline['title']}",
                title=headline["symbol"],
                border_style="cyan",
            )
        )


@app.command("cache-market-data")
def cache_market_data(
    symbol: str = typer.Option(
        ..., help="Ticker symbol, for example AAPL or THYAO.IS."
    ),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h."),
    lookback: str = typer.Option("180d", help="Lookback window accepted by yfinance."),
) -> None:
    """Fetch and save a repeatable market snapshot CSV into the runtime cache."""
    settings = get_settings()
    refresh_settings = settings.model_copy(update={"market_data_mode": "refresh_cache"})
    frame = fetch_ohlcv(
        symbol, interval=interval, lookback=lookback, settings=refresh_settings
    )
    payload = _market_cache_payload(refresh_settings)
    console.print(
        Panel(
            f"Cached {len(frame)} bars for {symbol} {interval} {lookback}.\n\nCache Dir: {payload['cache_dir']}\nSnapshots: {payload['count']}",
            title="Market Snapshot Cached",
            border_style="green",
        )
    )


@app.command("market-cache")
def market_cache(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """List saved repeatable market snapshots."""
    settings = get_settings()
    payload = _market_cache_payload(settings)
    if json_output:
        _emit_json(payload)
        return
    table = Table(title="Market Snapshot Cache")
    table.add_column("Filename")
    table.add_column("Size")
    table.add_column("Modified")
    if not payload["entries"]:
        table.add_row("-", "-", "-")
    else:
        for entry in payload["entries"][:20]:
            table.add_row(
                str(entry["filename"]),
                str(entry["size_bytes"]),
                str(entry["modified_at"]),
            )
    console.print(table)
    console.print(
        Panel(
            f"Mode: {payload['mode']}\nCache Dir: {payload['cache_dir']}\nSnapshot Count: {payload['count']}",
            title="Cache Status",
            border_style="cyan",
        )
    )


@app.command("preferences")
def preferences_command(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    )
) -> None:
    """Show the saved investment preferences."""
    settings = get_settings()
    payload = _preferences_payload(settings)
    preferences = InvestmentPreferences.model_validate(payload)
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Preferences are temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    table = Table(title="Investment Preferences")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("Regions", ", ".join(preferences.regions) or "-")
    table.add_row("Exchanges", ", ".join(preferences.exchanges) or "-")
    table.add_row("Currencies", ", ".join(preferences.currencies) or "-")
    table.add_row("Sectors", ", ".join(preferences.sectors) or "-")
    table.add_row("Risk Profile", preferences.risk_profile)
    table.add_row("Trade Style", preferences.trade_style)
    table.add_row("Behavior Preset", preferences.behavior_preset)
    table.add_row("Agent Profile", preferences.agent_profile)
    table.add_row("Agent Tone", preferences.agent_tone)
    table.add_row("Strictness", preferences.strictness_preset)
    table.add_row("Intervention", preferences.intervention_style)
    table.add_row("Notes", preferences.notes or "-")
    console.print(table)


@app.command("journal")
def journal(
    limit: int = typer.Option(
        20, min=1, max=200, help="Maximum number of journal entries to show."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show the latest trade journal entries."""
    settings = get_settings()
    payload = _journal_payload(settings, limit=limit)
    entries = [TradeJournalEntry.model_validate(entry) for entry in payload["entries"]]
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Trade journal is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_trade_journal(entries)


@app.command("risk-report")
def risk_report(
    report_date: str | None = typer.Option(
        None, help="UTC date in YYYY-MM-DD format. Defaults to today."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show a compact daily risk report for the paper portfolio."""
    settings = get_settings()
    payload = _risk_report_payload(settings, report_date=report_date)
    report = (
        DailyRiskReport.model_validate(payload["report"])
        if payload["report"] is not None
        else None
    )
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available or report is None:
        console.print(
            Panel(
                f"Risk report is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_risk_report(report)


@app.command("review-run")
def review_run(
    run_id: str | None = typer.Option(
        None, help="Run id to inspect. Defaults to the latest recorded run."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Inspect the latest or a specific persisted run in detail."""
    settings = get_settings()
    payload = _run_record_payload(settings, run_id=run_id)
    record = (
        RunRecord.model_validate(payload["record"])
        if payload["record"] is not None
        else None
    )
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Run review is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if record is None:
        console.print(
            Panel(
                "No persisted runs are available to review.",
                title="Run Review",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_run_review(record)


@app.command("trace-run")
def trace_run(
    run_id: str | None = typer.Option(
        None, help="Run id to inspect. Defaults to the latest recorded run."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show the persisted per-stage agent trace for a run."""
    settings = get_settings()
    payload = _run_record_payload(settings, run_id=run_id)
    record = (
        RunRecord.model_validate(payload["record"])
        if payload["record"] is not None
        else None
    )
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Run trace is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if record is None:
        console.print(
            Panel(
                "No persisted runs are available to trace.",
                title="Trace Viewer",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_run_trace(record)


@app.command("trade-context")
def trade_context(
    trade_id: str | None = typer.Option(
        None, help="Trade id to inspect. Defaults to the latest recorded trade context."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Inspect the persisted market, memory, and reasoning context for a trade."""
    settings = get_settings()
    payload = _trade_context_payload(settings, trade_id=trade_id)
    record = (
        TradeContextRecord.model_validate(payload["record"])
        if payload["record"] is not None
        else None
    )
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"]:
        console.print(
            Panel(
                f"Trade context is temporarily unavailable while the runtime writer owns the database.\n\n{payload['error']}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if record is None:
        console.print(
            Panel(
                "No persisted trade context is available yet.",
                title="Trade Context",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    summary = Table(title=f"Trade Context / {record.trade_id}")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Created", record.created_at)
    summary.add_row("Run ID", record.run_id or "-")
    summary.add_row("Symbol", record.symbol)
    summary.add_row("Consensus", record.consensus.alignment_level)
    summary.add_row("Manager Rationale", record.manager_rationale)
    summary.add_row("Execution Rationale", record.execution_rationale)
    summary.add_row("Review Summary", record.review_summary)
    console.print(summary)

    routed_models = Table(title="Routed Models")
    routed_models.add_column("Role")
    routed_models.add_column("Model")
    if not record.routed_models:
        routed_models.add_row("-", "-")
    else:
        for role, model_name in sorted(record.routed_models.items()):
            routed_models.add_row(role, model_name)
    console.print(routed_models)

    context_lines = [
        f"Retrieved Memory Roles: {', '.join(sorted(record.retrieved_memory_summary)) or '-'}",
        f"Tool Output Roles: {', '.join(sorted(record.tool_outputs)) or '-'}",
        f"Shared Bus Roles: {', '.join(sorted(record.shared_memory_summary)) or '-'}",
        f"Review Warnings: {', '.join(record.review_warnings) or '-'}",
    ]
    console.print(
        Panel(
            "\n".join(context_lines),
            title="Context Summary",
            border_style="cyan",
        )
    )


@app.command("replay-run")
def replay_run(
    run_id: str | None = typer.Option(
        None, help="Run id to replay. Defaults to the latest recorded run."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Replay what the system knew at decision time using persisted traces."""
    settings = get_settings()
    payload = _run_replay_payload(settings, run_id=run_id)
    replay = (
        RunReplay.model_validate(payload["replay"])
        if payload["replay"] is not None
        else None
    )
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"]:
        console.print(
            Panel(
                f"Run replay is temporarily unavailable while the runtime writer owns the database.\n\n{payload['error']}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if replay is None:
        console.print(
            Panel(
                "No persisted runs are available to replay.",
                title="Run Replay",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_run_replay(replay)


@app.command("export-report")
def export_report(
    output: str = typer.Option(
        ..., help="Output file path for the exported run review."
    ),
    run_id: str | None = typer.Option(
        None, help="Run id to export. Defaults to the latest recorded run."
    ),
) -> None:
    """Export a run review as Markdown."""
    settings = get_settings()
    db = _open_db(settings, read_only=True)
    record = db.get_run(run_id) if run_id is not None else db.latest_run()
    if record is None:
        console.print(
            Panel(
                "No persisted runs are available to export.",
                title="Export Blocked",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1)
    rendered = _render_run_markdown(record)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    console.print(
        Panel(
            f"Run report written to {output}.", title="Exported", border_style="green"
        )
    )


@app.command("backtest")
def backtest(
    symbol: str = typer.Option(..., help="Ticker symbol, for example AAPL or BTC-USD"),
    interval: str = typer.Option("1d", help="yfinance interval, for example 1d or 1h"),
    lookback: str = typer.Option("2y", help="Lookback window accepted by yfinance"),
    warmup_bars: int = typer.Option(
        120, min=60, help="Warmup bars before replay begins."
    ),
    compare_baseline: bool = typer.Option(
        False, help="Also compare the agent replay against a deterministic baseline."
    ),
    compare_memory: bool = typer.Option(
        False, help="Also compare the agent replay with memory enabled versus disabled."
    ),
    output: str | None = typer.Option(
        None, help="Optional Markdown output path for a compact backtest summary."
    ),
) -> None:
    """Run a walk-forward replay using the current agent pipeline."""
    settings = get_settings()
    ensure_llm_ready(settings)
    if compare_baseline and compare_memory:
        raise typer.BadParameter(
            "Choose either --compare-baseline or --compare-memory for a single run."
        )
    if compare_baseline:
        comparison = run_backtest_comparison(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=False,
        )
        _render_backtest_comparison(comparison)
        if output is not None:
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
            Path(output).write_text(rendered, encoding="utf-8")
            console.print(
                Panel(
                    f"Backtest comparison written to {output}.",
                    title="Exported",
                    border_style="green",
                )
            )
        return

    if compare_memory:
        ablation = run_memory_ablation_backtest(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=False,
        )
        _render_backtest_ablation(ablation)
        if output is not None:
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
            Path(output).write_text(rendered, encoding="utf-8")
            console.print(
                Panel(
                    f"Backtest memory ablation written to {output}.",
                    title="Exported",
                    border_style="green",
                )
            )
        return

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
        console.print(
            Panel(
                f"Backtest summary written to {output}.",
                title="Exported",
                border_style="green",
            )
        )


@app.command("memory-explorer")
def memory_explorer(
    symbol: str | None = typer.Option(
        None, help="Ticker symbol, for example AAPL or BTC-USD"
    ),
    interval: str | None = typer.Option(
        None, help="yfinance interval, for example 1d or 1h"
    ),
    lookback: str = typer.Option("180d", help="Lookback window accepted by yfinance"),
    limit: int = typer.Option(
        5, min=1, max=20, help="Maximum number of retrieved historical memories."
    ),
    use_latest_run: bool = typer.Option(
        True, help="Use the latest recorded run snapshot when available."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Inspect historically similar recorded runs for the current market snapshot."""
    settings = get_settings()
    payload = _memory_explorer_payload(
        settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        limit=limit,
        use_latest_run=use_latest_run,
    )
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"]:
        console.print(
            Panel(
                f"Memory explorer is temporarily unavailable.\n\n{payload['error']}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    matches = [
        HistoricalMemoryMatch.model_validate(match) for match in payload["matches"]
    ]
    _render_memory_matches(matches)


@app.command("retrieval-inspection")
def retrieval_inspection(
    run_id: str | None = typer.Option(
        None, help="Run id to inspect. Defaults to the latest recorded run."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Inspect which memories and context bundles were injected into each agent stage."""
    settings = get_settings()
    payload = _retrieval_inspection_payload(settings, run_id=run_id)
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"]:
        console.print(
            Panel(
                f"Retrieval inspection is temporarily unavailable.\n\n{payload['error']}",
                title="Observer Mode",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if not payload["stages"]:
        console.print(
            Panel(
                "No agent trace contexts are available for retrieval inspection yet.",
                title="Retrieval Inspection",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    table = Table(title=f"Retrieval Inspection / {payload['run_id']}")
    table.add_column("Role")
    table.add_column("Retrieved Memories")
    table.add_column("Trade Memory")
    table.add_column("Shared Bus")
    table.add_column("Recent Runs")
    for stage in payload["stages"]:
        table.add_row(
            str(stage["role"]),
            str(len(stage["retrieved_memories"])),
            str(len(stage["memory_notes"])),
            str(len(stage["shared_memory_bus"])),
            str(len(stage["recent_runs"])),
        )
    console.print(table)
    for stage in payload["stages"]:
        lines = []
        if stage["retrieved_memories"]:
            lines.extend(
                ["Retrieved Similar Memories:"]
                + [f"- {line}" for line in stage["retrieved_memories"]]
            )
        if stage["memory_notes"]:
            lines.extend(
                ["", "Trade Memory:"] + [f"- {line}" for line in stage["memory_notes"]]
            )
        if stage["recent_runs"]:
            lines.extend(
                ["", "Recent Runs:"] + [f"- {line}" for line in stage["recent_runs"]]
            )
        if stage["shared_memory_bus"]:
            lines.extend(
                ["", "Shared Memory Bus:"]
                + [
                    f"- {entry['role']}: {entry['summary']}"
                    for entry in stage["shared_memory_bus"]
                ]
            )
        if stage["tool_outputs"]:
            lines.extend(
                ["", "Tool Outputs:"] + [f"- {line}" for line in stage["tool_outputs"]]
            )
        if not lines:
            lines.append("No retrieval or memory context was attached for this stage.")
        console.print(
            Panel(
                "\n".join(lines), title=f"Stage / {stage['role']}", border_style="cyan"
            )
        )


@app.command("memory-policy")
def memory_policy(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Show policy-controlled memory write permissions by domain."""
    payload = memory_write_policy_snapshot()
    if json_output:
        _emit_json(payload)
        return

    table = Table(title="Memory Write Policy")
    table.add_column("Domain")
    table.add_column("Allowed Actors")
    table.add_column("Note")
    for domain, policy in payload.items():
        table.add_row(
            domain,
            ", ".join(policy["allowed_actors"]),
            str(policy["note"]),
        )
    console.print(table)


@app.command()
def chat(
    persona: ChatPersona = typer.Option(
        "operator_liaison", help="Which agent persona should answer."
    ),
    message: str | None = typer.Option(
        None, help="Optional message. If omitted, an interactive prompt is shown."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON."
    ),
) -> None:
    """Talk to the read-only operator chat surface."""
    settings = get_settings()
    ensure_llm_ready(settings)
    db = _open_db(settings, read_only=True)
    prompt = message or typer.prompt("Message")
    response = chat_with_persona(
        llm=LocalLLM(settings),
        db=db,
        settings=settings,
        persona=persona,
        user_message=prompt,
    )
    db.close()
    append_chat_history(
        settings,
        ChatHistoryEntry(
            entry_id=f"chat-{uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            persona=persona,
            user_message=prompt,
            response_text=response,
        ),
    )
    if json_output:
        _emit_json(
            {
                "persona": persona,
                "message": prompt,
                "response": response,
            }
        )
        return
    console.print(Panel(response, title=f"Chat / {persona}", border_style="cyan"))


@app.command()
def instruct(
    message: str = typer.Option(..., help="Natural-language operator instruction."),
    apply: bool = typer.Option(
        False, help="Apply the parsed preference update if one is proposed."
    ),
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
def monitor(
    refresh_seconds: float = typer.Option(
        1.0, min=0.2, help="Dashboard refresh interval in seconds."
    )
) -> None:
    """Attach to the live runtime monitor."""
    settings = get_settings()
    console.print(build_monitor_renderable(settings))
    run_live_monitor(settings, refresh_seconds=refresh_seconds)


@app.command("tui")
def ink_tui() -> None:
    """Launch the Ink-based control room."""
    tui_dir = Path(__file__).resolve().parent.parent / "tui"
    if not tui_dir.exists():
        console.print(
            _render_health_panel(
                "TUI Missing", "The Ink UI directory was not found.", border_style="red"
            )
        )
        raise typer.Exit(code=1)

    npm = shutil.which("npm")
    if npm is None:
        console.print(
            _render_health_panel(
                "Node Missing",
                "npm is required to run the Ink control room.",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    node_modules = tui_dir / "node_modules"
    if not node_modules.exists():
        console.print(
            _render_health_panel(
                "Installing TUI Dependencies",
                "First launch detected. Installing Ink dependencies with npm.",
                border_style="yellow",
            )
        )
        subprocess.run([npm, "install"], cwd=tui_dir, check=True)

    cli_exec = shutil.which("agentic-trader") or "agentic-trader"
    env = {
        **os.environ,
        "AGENTIC_TRADER_CLI": cli_exec,
        "AGENTIC_TRADER_PYTHON": sys.executable,
    }
    subprocess.run([npm, "run", "start"], cwd=tui_dir, check=True, env=env)


@app.command("stop-service")
def stop_service(
    force: bool = typer.Option(False, help="Send SIGTERM after marking stop requested.")
) -> None:
    """Request a graceful stop for the background orchestrator."""
    settings = get_settings()
    state = read_service_state(settings)
    if state is None or state.pid is None:
        console.print(
            _render_health_panel(
                "Not Running",
                "No managed service is currently active.",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    if not is_process_alive(state.pid):
        console.print(
            _render_health_panel(
                "Stale State Cleared",
                f"Dead PID {state.pid} is no longer alive. The next service start will recover the stale runtime state automatically.",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    request_stop(settings)
    try:
        db = TradingDatabase(settings)
        try:
            db.request_stop_service()
        finally:
            db.close()
    except Exception:
        pass
    if force:
        os.kill(state.pid, signal.SIGTERM)
    console.print(
        _render_health_panel(
            "Stop Requested",
            f"Service PID {state.pid} was asked to stop gracefully via the runtime control channel.",
            border_style="yellow",
        )
    )


@app.command("restart-service")
def restart_service(
    grace_seconds: float = typer.Option(
        3.0, min=0.0, help="How long to wait for a graceful stop before relaunch."
    )
) -> None:
    """Restart the managed background orchestrator using its last recorded launch config."""
    settings = get_settings()
    try:
        pid = restart_background_service(settings=settings, grace_seconds=grace_seconds)
    except Exception as exc:
        console.print(
            _render_health_panel(
                "Restart Blocked",
                str(exc),
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    console.print(
        _render_health_panel(
            "Service Restarted",
            f"Background orchestrator restarted with PID {pid}.",
            border_style="green",
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
