import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from agentic_trader.config import get_settings, Settings
from agentic_trader.diagnostics import (
    provider_diagnostics_payload,
    v1_readiness_payload,
)
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.finance.ideas import (
    IdeaCandidate,
    IdeaPresetName,
    PRESET_DESCRIPTIONS,
    rank_candidates,
)
from agentic_trader.finance.proposals import (
    approve_trade_proposal,
    create_trade_proposal,
    reconcile_trade_proposal,
    reject_trade_proposal,
)
from agentic_trader.finance.strategy_catalog import (
    StrategyStatus,
    finance_reconciliation_contract_payload,
    get_strategy_profile,
    score_strategy_context,
    strategy_catalog_payload,
    strategy_profile_for_preset,
)
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
    read_latest_research_snapshot,
    read_service_events,
    read_service_state,
    read_chat_history,
    request_stop,
)
from agentic_trader.runtime_status import (
    build_agent_activity_view,
    build_runtime_status_view,
    is_process_alive,
    RuntimeStatusView,
)
from agentic_trader.observer_api import serve_observer_api
from agentic_trader.researchd.crewai_setup import crewai_setup_status
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.cycle_runner import run_research_cycle
from agentic_trader.researchd.news_intelligence import (
    classify_source_tier,
    news_research_plan,
)
from agentic_trader.researchd.orchestrator import ResearchSidecar
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.researchd.status import build_research_sidecar_state
from agentic_trader.security import is_loopback_host, redact_sensitive_text
from agentic_trader.system.camofox_service import (
    build_camofox_service_status,
    start_camofox_service,
    stop_camofox_service,
)
from agentic_trader.system.model_service import (
    build_model_service_status,
    pull_model,
    start_model_service,
    stop_model_service,
)
from agentic_trader.system.operator_launcher import (
    build_operator_launcher_status,
    start_default_background_runtime,
    start_operator_webgui,
)
from agentic_trader.system.setup import build_setup_status
from agentic_trader.system.webgui_service import (
    build_webgui_service_status,
    stop_webgui_service,
)
from agentic_trader.schemas import (
    ChatPersona,
    CanonicalAnalysisSnapshot,
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
    RuntimeMode,
    RuntimeModeTransitionCheck,
    RuntimeModeTransitionPlan,
    ServiceEvent,
    ServiceStateSnapshot,
    TradeContextRecord,
    TradeJournalEntry,
    TradeProposalRecord,
    TradeProposalStatus,
    TradeSide,
)
from agentic_trader.storage.db import OrderRow, TradingDatabase
from agentic_trader.tui import build_monitor_renderable, run_live_monitor, run_main_menu
from agentic_trader.ui_text import (
    HELP_INTERVAL,
    HELP_JSON,
    HELP_LOOKBACK,
    HELP_RUN_ID,
    HELP_SYMBOL,
    LABEL_MARKET_VALUE,
    LABEL_OBSERVER_MODE,
    LABEL_STRUCTURED_LLM,
    LABEL_UNREALIZED_PNL,
    LABEL_WIN_RATE,
    TITLE_RUNTIME_EVENTS,
    TITLE_SERVICE_STATUS,
)
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import (
    ensure_llm_ready,
    restart_background_service,
    run_service,
    start_background_service,
    terminate_service_process,
)

app = typer.Typer(
    help="Agentic Trader CLI",
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()
model_service_app = typer.Typer(
    help="Manage the optional app-owned local model service."
)
app.add_typer(model_service_app, name="model-service")
webgui_service_app = typer.Typer(
    help="Manage the optional app-owned local Web GUI service."
)
app.add_typer(webgui_service_app, name="webgui-service")
camofox_service_app = typer.Typer(
    help="Manage the optional app-owned local Camofox browser helper."
)
app.add_typer(camofox_service_app, name="camofox-service")

TUI_PACKAGE_NAME = "agentic-trader-tui"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_ARTIFACTS_ROOT = PROJECT_ROOT / ".ai" / "qa" / "artifacts"
HELP_RUNTIME_EVENT_LIMIT = "Maximum number of runtime events to include."
HELP_PROVIDER_CHECK = "Actively check the configured LLM provider/model readiness."
ProposalOrderType = Literal["market", "limit"]


type NodeCommandSet = tuple[list[str], list[str], Path, str]


def _resolve_tui_node_commands(tui_dir: Path) -> NodeCommandSet | None:
    """
    Resolve package-manager install and start command vectors and a working directory for the bundled Ink TUI.
    
    Parameters:
        tui_dir (Path): Path to the bundled TUI directory.
    
    Returns:
        NodeCommandSet | None: A tuple (install_command, start_command, command_cwd, manager_name) where
            - install_command (list[str]) is the package-manager install command to run,
            - start_command (list[str]) is the command to start the TUI,
            - command_cwd (Path) is the directory where the start command should be executed,
            - manager_name (str) is a short identifier for the chosen package manager/workflow.
        Returns `None` if no supported Node package manager can be resolved.
    """
    repo_root = tui_dir.parent
    pnpm = shutil.which("pnpm")
    if pnpm and (repo_root / "pnpm-workspace.yaml").exists():
        return (
            [pnpm, "install"],
            [pnpm, "--filter", TUI_PACKAGE_NAME, "run", "start"],
            repo_root,
            "pnpm workspace",
        )
    if pnpm and (tui_dir / "pnpm-lock.yaml").exists():
        return (
            [pnpm, "install"],
            [pnpm, "run", "start"],
            tui_dir,
            "pnpm",
        )

    npm = shutil.which("npm")
    if npm and (tui_dir / "package-lock.json").exists():
        return (
            [npm, "install"],
            [npm, "run", "start"],
            tui_dir,
            "npm",
        )
    if npm:
        return (
            [npm, "install", "--no-package-lock"],
            [npm, "run", "start"],
            tui_dir,
            "npm",
        )

    yarn = shutil.which("yarn")
    if yarn and (tui_dir / "yarn.lock").exists():
        return (
            [yarn, "install", "--frozen-lockfile"],
            [yarn, "start"],
            tui_dir,
            "yarn",
        )
    if yarn:
        return (
            [yarn, "install", "--no-lockfile"],
            [yarn, "start"],
            tui_dir,
            "yarn",
        )

    return None


def _tui_dependencies_installed(tui_dir: Path, command_cwd: Path) -> bool:
    """
    Check whether TUI-specific Node dependencies appear installed.

    Parameters:
        tui_dir (Path): Path to the bundled TUI directory.
        command_cwd (Path): Working directory where the resolved package-manager commands will run; root workspace dependencies alone are not sufficient.

    Returns:
        bool: `True` only when the TUI package has its own `node_modules` link directory, `False` otherwise.
    """
    _ = command_cwd
    return (tui_dir / "node_modules").exists()


def _read_text_tail(path: Path | None, *, limit: int = 12) -> list[str]:
    """
    Read up to the last `limit` lines from a UTF-8 text file and return them as a list of lines.
    
    If `path` is None or the file does not exist, an empty list is returned. Lines are decoded using UTF-8 with replacement for invalid bytes.
    
    Parameters:
        path (Path | None): Path to the text file to read, or None to indicate absence.
        limit (int): Maximum number of trailing lines to return (default 12).
    
    Returns:
        list[str]: The last up to `limit` lines from the file, or an empty list if unavailable.
    """
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [redact_sensitive_text(line, max_length=1_000) for line in lines[-limit:]]


def _format_latest_order(order: OrderRow | None) -> str:
    """
    Format an OrderRow into a single-line human-readable summary.
    
    Parameters:
        order (OrderRow | None): An order tuple or None.
    
    Returns:
        str: A single-line summary for the given order in the form
        "order_id | SYMBOL SIDE | approved=<bool> | entry=<price> | size=<pct> | confidence=<score>",
        or the literal string "None" when `order` is None.
    """
    if order is None:
        return "None"
    (
        order_id,
        _created_at,
        symbol,
        side,
        approved,
        entry_price,
        _stop_loss,
        _take_profit,
        position_size_pct,
        confidence,
    ) = order
    return (
        f"{order_id} | {symbol} {side} | approved={approved} | "
        f"entry={entry_price:.4f} | size={position_size_pct:.2%} | "
        f"confidence={confidence:.2f}"
    )


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    """
    Create a rich Panel with the given title text and border style.
    
    Parameters:
        status (str): Text to use as the panel title.
        body (str): Text content to display inside the panel.
        border_style (str): Rich style string applied to the panel border.
    
    Returns:
        panel (Panel): A `rich.panel.Panel` containing `body`, titled with `status`, and using `border_style`.
    """
    return Panel(body, title=status, border_style=border_style)


def _render_execution_panels(order_id: str, artifacts: RunArtifacts) -> None:
    """
    Render execution summary panels for a completed run to the console.
    
    Displays an "Execution Summary" table (order id, approval, side, confidence, entry/stop/take-profit, and decision path), a "Pipeline" table showing each agent stage's source and any fallback reason, a warning panel if any fallbacks occurred (otherwise a green LLM-status panel), and a JSON panel containing the serialized run artifacts.
    
    Parameters:
        order_id (str): The identifier of the order to display in the summary.
        artifacts (RunArtifacts): RunArtifacts object containing coordinator, regime, strategy, risk, manager, and execution details used to populate the panels.
    """
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
        artifacts.coordinator.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        "Regime",
        artifacts.regime.source,
        artifacts.regime.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        "Strategy",
        artifacts.strategy.source,
        artifacts.strategy.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        "Risk",
        artifacts.risk.source,
        artifacts.risk.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        "Manager",
        artifacts.manager.source,
        artifacts.manager.fallback_reason or LABEL_STRUCTURED_LLM,
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
    """
    Render the service runtime status to the console.
    
    If `state` is None or contains no recorded runtime state, prints a yellow panel indicating no runtime state is recorded. Otherwise prints a table summarizing runtime fields such as service name, runtime mode/state, live process flag, heartbeat and its age, start/updated times, polling/cycle settings, symbol/interval/lookback configuration, PID and stop-requested flag, and the last recorded message/error.
    
    Parameters:
        state (ServiceStateSnapshot | None): Snapshot of the supervisor/service runtime state; pass `None` to indicate no recorded runtime state.
    """
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                "No runtime state recorded yet.",
                title=TITLE_SERVICE_STATUS,
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=TITLE_SERVICE_STATUS)
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Service", snapshot.service_name)
    table.add_row("Mode", snapshot.runtime_mode)
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
        "Max Cycles",
        str(snapshot.max_cycles) if snapshot.max_cycles is not None else "-",
    )
    table.add_row("Current Symbol", snapshot.current_symbol or "-")
    table.add_row("PID", str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row("Stop Requested", str(snapshot.stop_requested))
    table.add_row("Status Note", view.status_message)
    table.add_row("Last Recorded Message", snapshot.message or "-")
    table.add_row("Last Recorded Error", snapshot.last_error or "-")
    console.print(table)


def _render_service_events(events: list[ServiceEvent]) -> None:
    """
    Render a list of runtime service events as a rich table, or show a yellow placeholder panel when no events exist.
    
    Parameters:
        events (list[ServiceEvent]): Sequence of service event records to display; each event should provide created time, level, type, cycle count, symbol, and message.
    """
    if not events:
        console.print(
            Panel(
                "No runtime events recorded yet.",
                title=TITLE_RUNTIME_EVENTS,
                border_style="yellow",
            )
        )
        return

    table = Table(title=TITLE_RUNTIME_EVENTS)
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
    """
    Render a DailyRiskReport to the console as a formatted table and a risk-warnings panel.
    
    Displays a table titled with the report date containing generated time, cash, market value, equity, realized/unrealized PnL, counts (open positions, fills, marks), daily realized PnL, exposure metrics, largest position, and drawdown. After the table, prints a yellow "Risk Warnings" panel listing each warning if any exist, otherwise prints a green panel indicating no elevated warnings.
    
    Parameters:
        report (DailyRiskReport): The risk report data to render.
    """
    table = Table(title=f"Daily Risk Report / {report.report_date}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Generated", report.generated_at)
    table.add_row("Cash", f"{report.cash:.2f}")
    table.add_row(LABEL_MARKET_VALUE, f"{report.market_value:.2f}")
    table.add_row("Equity", f"{report.equity:.2f}")
    table.add_row("Realized PnL", f"{report.realized_pnl:.2f}")
    table.add_row(LABEL_UNREALIZED_PNL, f"{report.unrealized_pnl:.2f}")
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
    """
    Render a human-readable run review to the console, showing metadata, agent decisions, manager override notes, manager conflicts, and the structured review note.
    
    Parameters:
        record (RunRecord): Persisted run record whose metadata and artifacts will be rendered.
    """
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
        "Fundamental",
        record.artifacts.fundamental.overall_bias,
        (
            f"{record.artifacts.fundamental.summary} | "
            f"red_flags={', '.join(record.artifacts.fundamental.red_flags) or '-'}"
        ),
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
            "\n".join(
                f"- {note}" for note in _manager_override_notes(record.artifacts)
            ),
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
    """
    Builds a Markdown-formatted run review document from a persisted RunRecord.
    
    Generates a human-readable Markdown summary that includes metadata, coordinator,
    fundamental analysis, regime, strategy, risk, consensus, manager decisions and
    conflicts, execution details, and reviewer notes derived from the record's
    artifacts.
    
    Parameters:
        record (RunRecord): Persisted run record containing artifacts to serialize.
    
    Returns:
        markdown (str): A Markdown document string summarizing the run review.
    """
    artifacts = record.artifacts
    fundamental_evidence = artifacts.fundamental.evidence_vs_inference
    manager_resolution_notes = _manager_resolution_notes(artifacts)
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
        "## Fundamental",
        f"- Overall Bias: {artifacts.fundamental.overall_bias}",
        f"- Growth Quality: {artifacts.fundamental.growth_quality}",
        f"- Profitability Quality: {artifacts.fundamental.profitability_quality}",
        f"- Cash Flow Quality: {artifacts.fundamental.cash_flow_quality}",
        f"- Balance Sheet Quality: {artifacts.fundamental.balance_sheet_quality}",
        f"- FX Risk: {artifacts.fundamental.fx_risk}",
        f"- Business Quality: {artifacts.fundamental.business_quality}",
        f"- Macro Fit: {artifacts.fundamental.macro_fit}",
        f"- Forward Outlook: {artifacts.fundamental.forward_outlook}",
        f"- Red Flags: {_join_or_dash(artifacts.fundamental.red_flags)}",
        f"- Strengths: {_join_or_dash(artifacts.fundamental.strengths)}",
        f"- Evidence: {_join_or_dash(fundamental_evidence.evidence)}",
        f"- Inference: {_join_or_dash(fundamental_evidence.inference)}",
        f"- Uncertainty: {_join_or_dash(fundamental_evidence.uncertainty)}",
        f"- Summary: {artifacts.fundamental.summary}",
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
        f"- Summary: {_value_or_dash(artifacts.consensus.summary)}",
        f"- Supporting Roles: {_join_or_dash(artifacts.consensus.supporting_roles)}",
        f"- Dissenting Roles: {_join_or_dash(artifacts.consensus.dissenting_roles)}",
        f"- Reasons: {_join_or_dash(artifacts.consensus.reasons)}",
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
            *_markdown_bullets(
                manager_resolution_notes,
                fallback="No additional manager resolution notes.",
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
            f"- Strengths: {_join_or_dash(artifacts.review.strengths)}",
            f"- Warnings: {_join_or_dash(artifacts.review.warnings)}",
            f"- Next Checks: {_join_or_dash(artifacts.review.next_checks)}",
            "",
        ]
    )
    return "\n".join(lines)


def _value_or_dash(value: object) -> str:
    return str(value) if value else "-"


def _join_or_dash(values: list[str] | tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _markdown_bullets(values: list[str], *, fallback: str) -> list[str]:
    if not values:
        return [f"- {fallback}"]
    return [f"- {value}" for value in values]


def _manager_override_notes(artifacts: RunArtifacts) -> list[str]:
    """
    Produce a list of human-readable notes describing any manager overrides present in the run artifacts.
    
    Parameters:
        artifacts (RunArtifacts): Run artifacts containing manager, strategy, and execution decisions to inspect.
    
    Returns:
        list[str]: A list of note strings describing each detected override. If no overrides are detected, returns a single-item list with an acceptance message.
    """
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
        notes.append(
            "Manager accepted the specialist plan without additional overrides."
        )
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
    """
    Render a walk-forward backtest summary and a table of recent trades to the console using rich tables.
    
    The summary table shows key backtest metadata and aggregated metrics (interval, lookback, warmup bars, cycle and trade counts, win rate, expectancy, total return, max drawdown, exposure, and fallback cycles). The trades table lists up to the last 12 trades with entry/exit times, side, entry/exit prices, PnL, and exit reason.
    
    Parameters:
        report (BacktestReport): Backtest results and associated trade records to display.
    """
    summary = Table(title=f"Walk-Forward Backtest / {report.symbol}")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Interval", report.interval)
    summary.add_row("Lookback", report.lookback)
    summary.add_row("Warmup Bars", str(report.warmup_bars))
    summary.add_row("Cycles", str(report.total_cycles))
    summary.add_row("Trades", str(report.total_trades))
    summary.add_row("Closed Trades", str(report.closed_trades))
    summary.add_row(LABEL_WIN_RATE, f"{report.win_rate:.2%}")
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
    """
    Render a Rich table comparing agent and baseline backtest metrics for the report's symbol.
    
    Parameters:
        report (BacktestComparisonReport): Comparison report containing the agent and baseline metrics and symbol.
    """
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
        LABEL_WIN_RATE,
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
    """
    Render a memory-ablation backtest comparison table to the console.
    
    Parameters:
        report (BacktestAblationReport): Backtest results containing `with_memory` and `without_memory` metrics and the tested symbol; used to populate metric rows (trades, win rate, expectancy, return, ending equity).
    """
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
        LABEL_WIN_RATE,
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
    table.add_column("Why")
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
            match.explanation.eligibility_reason,
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
            latest_marks = db.list_account_marks(limit=1)
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
        latest_marks = []
        available = False
        error = str(exc)
    currency = _primary_account_currency(settings)
    latest_mark = latest_marks[0].model_dump(mode="json") if latest_marks else None
    return {
        "available": available,
        "error": error,
        "snapshot": snapshot.model_dump(mode="json"),
        "positions": [position.model_dump(mode="json") for position in positions],
        "accounting": {
            "currency": currency,
            "mark_created_at": latest_mark["created_at"] if latest_mark else None,
            "mark_source": latest_mark["source"] if latest_mark else None,
            "mark_note": latest_mark["note"] if latest_mark else None,
            "mark_status": "marked" if latest_mark else "mark_time_unavailable",
        },
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


def _primary_account_currency(settings: Settings) -> str:
    try:
        db = _open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
        finally:
            db.close()
    except Exception:
        preferences = InvestmentPreferences()
    return (preferences.currencies[0] if preferences.currencies else "USD").upper()


def _execution_cost_model(settings: Settings) -> dict[str, object]:
    if settings.execution_backend == "simulated_real":
        return {
            "fees": "not modeled",
            "slippage_bps": settings.simulated_slippage_bps,
            "spread_bps": settings.simulated_spread_bps,
            "latency_ms": settings.simulated_latency_ms,
            "partial_fill_probability": settings.simulated_partial_fill_probability,
            "rejection_probability": settings.simulated_order_rejection_probability,
        }
    if settings.execution_backend == "alpaca_paper":
        return {
            "fees": "reported by external paper broker when available",
            "slippage_bps": None,
            "spread_bps": None,
            "latency_ms": None,
            "partial_fill_probability": None,
            "rejection_probability": None,
        }
    return {
        "fees": "not modeled",
        "slippage_bps": 0.0,
        "spread_bps": 0.0,
        "latency_ms": 0,
        "partial_fill_probability": 0.0,
        "rejection_probability": 0.0,
    }


def _journal_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    """
    Builds a JSON-serializable payload containing recent trade journal entries.
    
    Parameters:
        limit (int): Maximum number of journal entries to include, ordered from newest to oldest.
    
    Returns:
        dict: A payload with:
            - `available` (bool): `True` when the database read succeeded, `False` on error.
            - `error` (str | None): Error message when `available` is `False`, otherwise `None`.
            - `entries` (list[dict]): List of journal entries serialized with `model_dump(mode="json")`.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            entries = db.list_trade_journal(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def _trade_proposals_payload(
    settings: Settings, *, status: TradeProposalStatus | None = None, limit: int = 50
) -> dict[str, object]:
    try:
        db = _open_db(settings, read_only=True)
        try:
            proposals = db.list_trade_proposals(status=status, limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        proposals = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "status": status,
        "proposals": [
            proposal.model_dump(mode="json") for proposal in proposals
        ],
    }


def _parse_trade_side(value: str) -> TradeSide:
    normalized = value.strip().lower()
    if normalized not in {"buy", "sell"}:
        raise typer.BadParameter("side must be buy or sell")
    return cast(TradeSide, normalized)


def _parse_order_type(value: str) -> ProposalOrderType:
    normalized = value.strip().lower()
    if normalized not in {"market", "limit"}:
        raise typer.BadParameter("proposal order type must be market or limit")
    return cast(ProposalOrderType, normalized)


def _parse_proposal_status(value: str | None) -> TradeProposalStatus | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in {
        "pending",
        "approved",
        "rejected",
        "executed",
        "failed",
        "expired",
    }:
        raise typer.BadParameter("status is not a known proposal state")
    return cast(TradeProposalStatus, normalized)


def _parse_idea_preset(value: str) -> IdeaPresetName:
    normalized = value.strip().lower()
    if normalized not in PRESET_DESCRIPTIONS:
        raise typer.BadParameter("preset is not a known idea scanner preset")
    return cast(IdeaPresetName, normalized)


def _parse_strategy_status(value: str | None) -> StrategyStatus | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in {"implemented", "research_candidate", "v2_deferred"}:
        raise typer.BadParameter(
            "status must be implemented, research-candidate, or v2-deferred"
        )
    return cast(StrategyStatus, normalized)


def _render_trade_proposals(proposals: list[TradeProposalRecord]) -> None:
    if not proposals:
        console.print(
            Panel(
                "No trade proposals recorded yet.",
                title="Trade Proposals",
                border_style="yellow",
            )
        )
        return
    table = Table(title="Trade Proposals")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Symbol")
    table.add_column("Side")
    table.add_column("Size")
    table.add_column("Ref")
    table.add_column("Confidence")
    table.add_column("Source")
    for proposal in proposals:
        size = (
            f"qty {proposal.quantity:.6f}"
            if proposal.quantity is not None
            else f"${proposal.notional or 0.0:.2f}"
        )
        table.add_row(
            proposal.proposal_id,
            proposal.status,
            proposal.symbol,
            proposal.side,
            size,
            f"{proposal.reference_price:.4f}",
            f"{proposal.confidence:.2f}",
            proposal.source,
        )
    console.print(table)


def _recent_runs_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    """
    Builds a JSON-serializable payload of recent run metadata for CLI/observer consumption.
    
    Parameters:
        settings (Settings): Application settings used to open the database.
        limit (int): Maximum number of recent runs to include.
    
    Returns:
        dict: A mapping with keys:
            - `available` (bool): `True` when runs were loaded successfully, `False` on error.
            - `error` (str | None): Error message when `available` is `False`, otherwise `None`.
            - `runs` (list[dict]): List of run summaries. Each entry contains:
                - `run_id` (str): Persisted run identifier.
                - `created_at` (str): Run creation timestamp.
                - `symbol` (str): Traded symbol for the run.
                - `interval` (str): Market interval used for the run.
                - `approved` (bool): Whether the run/execution was approved.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            runs = db.list_recent_runs(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        runs = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "runs": [
            {
                "run_id": run_id,
                "created_at": created_at,
                "symbol": symbol,
                "interval": interval,
                "approved": approved,
            }
            for run_id, created_at, symbol, interval, approved in runs
        ],
    }


def _risk_report_payload(
    settings: Settings, *, report_date: str | None = None
) -> dict[str, object]:
    """
    Builds a payload containing the daily risk report (or an error indicator) for CLI/observer use.
    
    Parameters:
        report_date (str | None): ISO date string (YYYY-MM-DD) to generate the report for. If None, uses the default/latest date.
    
    Returns:
        dict: A mapping with keys:
            - "available" (bool): `True` if the report was produced, `False` on error.
            - "error" (str | None): Error message when `available` is `False`, otherwise `None`.
            - "report" (dict | None): JSON-serializable representation of the daily risk report when available, otherwise `None`.
    """
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


def _run_record_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    """
    Builds a payload containing a persisted run record (or the latest run) and availability metadata.
    
    Parameters:
        run_id (str | None): Optional run identifier; when None the latest persisted run is loaded.
    
    Returns:
        dict[str, object]: Payload with keys:
            - "available": `True` if the database read succeeded, `False` on error.
            - "error": Error message string when unavailable, otherwise `None`.
            - "record": JSON-serializable dict of the run record when available, otherwise `None`.
    """
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
    """
    Builds a payload containing a persisted trade context record for observer output or APIs.
    
    Parameters:
        settings (Settings): Application settings used to open the read-only database.
        trade_id (str | None): Optional trade identifier; when provided, returns the matching trade context, otherwise returns the latest trade context.
    
    Returns:
        dict: A JSON-serializable mapping with keys:
            - "available" (bool): `True` if the record was loaded successfully, `False` on error.
            - "error" (str | None): Error message when loading failed, otherwise `None`.
            - "record" (dict | None): The trade context serialized for JSON when available, otherwise `None`.
    """
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


def _market_context_payload(settings: Settings) -> dict[str, object]:
    """
    Produce the latest persisted market context pack used by the most recent completed run.
    
    Returns:
        payload (dict): A JSON-serializable mapping with keys:
            - "available" (bool): `true` if a persisted context pack was found, `false` otherwise.
            - "error" (str | None): Error message when unavailable, otherwise `None`.
            - "contextPack" (dict | None): The context pack serialized as a JSON-like dict when available, otherwise `None`.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = db.latest_run()
        finally:
            db.close()
        context_pack = (
            record.artifacts.snapshot.context_pack if record is not None else None
        )
        available = context_pack is not None
        error = None if available else "No persisted market context pack is available."
    except Exception as exc:
        context_pack = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "contextPack": (
            context_pack.model_dump(mode="json") if context_pack is not None else None
        ),
    }


def _canonical_analysis_payload(settings: Settings) -> dict[str, object]:
    """
    Retrieve the most recently persisted canonical provider aggregation snapshot, if any.
    
    Returns:
        dict: A payload with keys:
            - available (bool): `True` if a canonical snapshot was found, `False` otherwise.
            - error (str | None): An error message when unavailable or on failure; `None` when `available` is `True`.
            - snapshot (dict | None): The canonical snapshot serialized to a JSON-compatible dict when available, otherwise `None`.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = db.latest_run()
            canonical_snapshot = (
                record.artifacts.canonical_snapshot if record is not None else None
            )
            if canonical_snapshot is None:
                trade_context = db.latest_trade_context()
                canonical_snapshot = (
                    trade_context.canonical_snapshot
                    if trade_context is not None
                    else None
                )
        finally:
            db.close()
        available = canonical_snapshot is not None
        error = None if available else "No canonical analysis snapshot is available."
    except Exception as exc:
        canonical_snapshot = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "snapshot": (
            canonical_snapshot.model_dump(mode="json")
            if canonical_snapshot is not None
            else None
        ),
    }


def _canonical_analysis_lines(
    canonical_snapshot: CanonicalAnalysisSnapshot | None,
) -> list[str]:
    """
    Builds a list of human-readable lines summarizing a canonical analysis snapshot for terminal display.
    
    Parameters:
        canonical_snapshot (CanonicalAnalysisSnapshot | None): The canonical analysis snapshot to summarize; pass None when no snapshot is attached.
    
    Returns:
        list[str]: Ordered lines suitable for printing or panel rendering. If `canonical_snapshot` is None, returns a single-line message indicating no snapshot is attached.
    """
    if canonical_snapshot is None:
        return ["No canonical analysis snapshot is attached to this trade context."]
    source_lines = [
        f"{item.provider_type}:{item.source_name} role={item.source_role} freshness={item.freshness}"
        for item in canonical_snapshot.source_attributions
    ]
    return [
        f"Summary: {canonical_snapshot.summary or '-'}",
        f"Completeness: {canonical_snapshot.completeness_score:.2f}",
        f"Missing Sections: {', '.join(canonical_snapshot.missing_sections) or '-'}",
        (
            "Primary Sources: "
            f"market={canonical_snapshot.market.attribution.source_name} | "
            f"fundamental={canonical_snapshot.fundamental.attribution.source_name} | "
            f"macro={canonical_snapshot.macro.attribution.source_name}"
        ),
        (
            "Event Counts: "
            f"news={len(canonical_snapshot.news_events)} | "
            f"disclosures={len(canonical_snapshot.disclosures)}"
        ),
        "Sources:",
        *(source_lines or ["-"]),
    ]


def _service_supervisor_payload(settings: Settings) -> dict[str, object]:
    """
    Builds a JSON-serializable supervisor payload describing the orchestrator runtime status, recent log tails, and the serialized service state.
    
    Parameters:
        settings (Settings): Application settings used to locate persisted service state and log files.
    
    Returns:
        dict[str, object]: Dictionary with the following keys:
            - runtime_state: Short runtime status identifier for the service view.
            - live_process: Metadata for the running service process, or `None` if not running.
            - is_stale: `true` if the last heartbeat is considered stale, `false` otherwise.
            - age_seconds: Age of the last heartbeat in seconds, or `None` if unavailable.
            - status_message: Human-readable status message for the runtime view.
            - state: Serialized snapshot of the full service state as JSON-compatible dict, or `None` if unavailable.
            - stdout_tail: List of last lines from the service stdout log (empty list if unavailable).
            - stderr_tail: List of last lines from the service stderr log (empty list if unavailable).
    """
    state = read_service_state(settings)
    view = build_runtime_status_view(state)
    stdout_path = (
        Path(state.stdout_log_path) if state and state.stdout_log_path else None
    )
    stderr_path = (
        Path(state.stderr_log_path) if state and state.stderr_log_path else None
    )
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
    """
    Build a JSON-serializable payload describing the broker runtime and safety-gate state.
    
    Returns:
        dict: A dictionary containing broker runtime metadata and safety gate flags.
    """
    return broker_runtime_payload(settings)


def _finance_check(
    name: str, passed: bool, details: str, *, blocking: bool = True
) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
        "blocking": blocking,
    }


def _finance_ops_payload(settings: Settings) -> dict[str, object]:
    """Build a read-only trading-desk view of broker, account, PnL, and evidence truth."""
    broker = _broker_payload(settings)
    portfolio = _portfolio_payload(settings)
    risk_report = _risk_report_payload(settings)
    readiness = v1_readiness_payload(settings, check_provider=False)
    reconciliation = finance_reconciliation_contract_payload()
    snapshot = portfolio.get("snapshot") if isinstance(portfolio, dict) else None
    accounting = (
        portfolio.get("accounting") if isinstance(portfolio, dict) else {}
    )
    if not isinstance(accounting, dict):
        accounting = {}
    checks = [
        _finance_check(
            "paper_or_external_paper_only",
            settings.execution_backend in {"paper", "alpaca_paper"}
            and not settings.live_execution_enabled,
            f"backend={settings.execution_backend} live_execution_enabled={settings.live_execution_enabled}",
        ),
        _finance_check(
            "broker_health_visible",
            isinstance(broker.get("healthcheck"), dict),
            str(broker.get("message", "")),
        ),
        _finance_check(
            "account_snapshot_visible",
            bool(portfolio.get("available")) and isinstance(snapshot, dict),
            str(portfolio.get("error") or "account snapshot available"),
        ),
        _finance_check(
            "pnl_and_exposure_fields_visible",
            _finance_snapshot_fields_visible(snapshot),
            "cash/equity/PnL/position fields are present on the portfolio snapshot.",
        ),
        _finance_check(
            "risk_report_visible",
            bool(risk_report.get("available")) and risk_report.get("report") is not None,
            str(risk_report.get("error") or "daily risk report available"),
            blocking=False,
        ),
        _finance_check(
            "paper_evidence_visible",
            isinstance(readiness.get("paper_evidence"), dict),
            "v1-readiness exposes source attribution, context-pack, review artifact, and no-live evidence.",
        ),
    ]
    blocking_passed = all(
        bool(check["passed"]) for check in checks if bool(check.get("blocking", True))
    )
    return {
        "ready": blocking_passed,
        "mode": settings.runtime_mode,
        "backend": settings.execution_backend,
        "checks": checks,
        "broker": broker,
        "portfolio": portfolio,
        "riskReport": risk_report,
        "paperEvidence": readiness.get("paper_evidence"),
        "reconciliation": reconciliation,
        "accounting": {
            "currency": accounting.get("currency", _primary_account_currency(settings)),
            "mark_created_at": accounting.get("mark_created_at"),
            "mark_source": accounting.get("mark_source"),
            "mark_note": accounting.get("mark_note"),
            "mark_status": accounting.get("mark_status", "mark_time_unavailable"),
            "cost_model": _execution_cost_model(settings),
            "ledger_categories": reconciliation["ledger_categories"],
            "rejection_evidence": (
                "Execution rejections are surfaced from execution_outcomes, "
                "trade context, broker-status, and run review payloads."
            ),
        },
        "summary": (
            "Finance operations checks have the broker/account/evidence truth needed for local paper review."
            if blocking_passed
            else "Finance operations checks are missing broker/account/evidence truth."
        ),
    }


def _finance_snapshot_fields_visible(snapshot: object) -> bool:
    if not isinstance(snapshot, dict):
        return False
    required_fields = {
        "cash",
        "equity",
        "realized_pnl",
        "unrealized_pnl",
        "open_positions",
    }
    return required_fields.issubset(snapshot)


def _render_finance_ops(payload: dict[str, object]) -> None:
    checks = payload.get("checks", [])
    accounting = payload.get("accounting", {})
    if not isinstance(accounting, dict):
        accounting = {}
    cost_model = accounting.get("cost_model", {})
    if not isinstance(cost_model, dict):
        cost_model = {}
    console.print(
        Panel(
            str(payload.get("summary", "Finance operations status unavailable.")),
            title="Finance Operations",
            border_style="green" if payload.get("ready") else "yellow",
        )
    )
    table = Table(title="Finance Operations Checks")
    table.add_column("Check")
    table.add_column("State")
    table.add_column("Blocking")
    table.add_column("Details")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, dict):
                table.add_row(
                    str(check.get("name", "-")),
                    "[green]pass[/green]" if check.get("passed") else "[red]fail[/red]",
                    str(check.get("blocking", True)),
                    str(check.get("details", "")),
                )
    console.print(table)
    context = Table(title="Desk Accounting Context")
    context.add_column("Field")
    context.add_column("Value")
    context.add_row("Currency", str(accounting.get("currency", "USD")))
    context.add_row(
        "Marked At", str(accounting.get("mark_created_at") or "mark time unavailable")
    )
    context.add_row("Mark Source", str(accounting.get("mark_source") or "-"))
    context.add_row("Mark Status", str(accounting.get("mark_status") or "-"))
    context.add_row("Fees", str(cost_model.get("fees", "-")))
    context.add_row(
        "Slippage",
        "-"
        if cost_model.get("slippage_bps") is None
        else f"{cost_model.get('slippage_bps')} bps",
    )
    context.add_row(
        "Rejection Evidence", str(accounting.get("rejection_evidence") or "-")
    )
    console.print(context)
    ledger_categories = accounting.get("ledger_categories", [])
    if isinstance(ledger_categories, list):
        ledger_table = Table(title="Finance Ledger Categories")
        ledger_table.add_column("Category")
        ledger_table.add_column("V1 Source")
        ledger_table.add_column("Purpose")
        for item in ledger_categories:
            if isinstance(item, dict):
                ledger_table.add_row(
                    str(item.get("name", "-")),
                    str(item.get("v1_source", "-")),
                    str(item.get("purpose", "-")),
                )
        console.print(ledger_table)


def _training_backtest_allow_fallback(settings: Settings) -> bool:
    """
    Determine whether a backtest running under the current settings may use deterministic diagnostic fallbacks.
    
    Attempts to verify LLM readiness; if the readiness check fails and the configured runtime mode is "training", a training diagnostic panel is displayed and fallback execution is permitted. In any other mode the readiness failure is propagated and fallbacks are not allowed.
    
    Parameters:
        settings (Settings): Runtime configuration used to determine the current mode and for contextual diagnostics.
    
    Returns:
        bool: `True` if fallback execution is permitted for this backtest, `False` otherwise.
    """
    try:
        ensure_llm_ready(settings)
    except RuntimeError as exc:
        if settings.runtime_mode != "training":
            raise
        console.print(
            Panel(
                (
                    "Training mode is continuing this evaluation with deterministic "
                    f"diagnostic fallbacks because the LLM gate failed:\n\n{exc}"
                ),
                title="Training Diagnostic Mode",
                border_style="yellow",
            )
        )
        return True
    return False


def _runtime_mode_transition_plan(
    settings: Settings, *, target_mode: RuntimeMode, check_provider: bool
) -> RuntimeModeTransitionPlan:
    """
    Builds a checklist of preconditions required to transition the runtime to the given target mode.
    
    Evaluates mode-specific conditions (for "operation" this includes strict-LLM, provider/model health when requested, execution backend and kill-switch state; for "training" this includes diagnostic constraints and operator-safety requirements). Each checklist entry indicates its name, pass/fail state, human-readable details, and whether it is blocking. The plan's `allowed` field is true only if all blocking checks pass, and the returned `RuntimeModeTransitionPlan` contains the current and target modes, the computed `allowed` flag, the list of checks, and a short summary.
    
    Parameters:
        settings (Settings): Runtime configuration used to read current mode and relevant flags.
        target_mode (RuntimeMode): Desired runtime mode to transition to.
        check_provider (bool): If true, perform LLM provider health checks (reachability and model availability); if false, provider checks are added as blocking unknowns.
    
    Returns:
        RuntimeModeTransitionPlan: A plan object containing `current_mode`, `target_mode`, `allowed`, `checks`, and `summary`.
    """
    checks: list[RuntimeModeTransitionCheck] = []

    def add_check(
        name: str, passed: bool, details: str, *, blocking: bool = True
    ) -> None:
        """
        Append a runtime mode transition check to the module-level checklist.
        
        Parameters:
            name (str): Human-readable name of the check.
            passed (bool): `True` if the check passed, `False` otherwise.
            details (str): Operator-facing explanation or diagnostic message for the check.
            blocking (bool): If `True`, a failing check blocks the transition; defaults to `True`.
        
        Side effects:
            Appends a `RuntimeModeTransitionCheck` instance to the `checks` list.
        """
        checks.append(
            RuntimeModeTransitionCheck(
                name=name,
                passed=passed,
                details=details,
                blocking=blocking,
            )
        )

    if target_mode == "operation":
        add_check(
            "strict_llm_enabled",
            settings.strict_llm,
            "Operation mode requires AGENTIC_TRADER_STRICT_LLM=true.",
        )
        if check_provider:
            health = LocalLLM(settings).health_check(include_generation=True)
            add_check(
                "provider_reachable",
                health.service_reachable,
                health.message,
            )
            add_check(
                "model_available",
                health.model_available,
                f"Configured model: {health.model_name}",
            )
            add_check(
                "model_generation_ready",
                health.generation_available is not False,
                health.generation_message or health.message,
            )
        else:
            add_check(
                "provider_reachable",
                False,
                "Provider check skipped; run doctor before Operation mode.",
            )
        add_check(
            "non_live_execution_backend",
            settings.execution_backend in {"paper", "simulated_real"},
            f"Configured backend: {settings.execution_backend}",
        )
        add_check(
            "live_execution_disabled",
            not settings.live_execution_enabled,
            "Live execution must remain disabled until a real adapter and approvals exist.",
        )
        add_check(
            "kill_switch_clear",
            not settings.execution_kill_switch_active,
            "Execution kill switch must be clear for production-like paper operation.",
        )
    else:
        add_check(
            "diagnostic_scope",
            True,
            "Training mode is limited to replay, walk-forward, ablation, and diagnostic evaluation flows.",
        )
        add_check(
            "runtime_no_hidden_trades",
            True,
            "`run`, `launch`, and service orchestration remain strict and do not silently trade with fallback outputs.",
        )
        add_check(
            "operator_confirmation_required",
            True,
            "Mode changes must be applied through explicit configuration, not chat side effects.",
        )

    allowed = all(check.passed for check in checks if check.blocking)
    summary = (
        f"Runtime mode transition {settings.runtime_mode} -> {target_mode} is allowed."
        if allowed
        else f"Runtime mode transition {settings.runtime_mode} -> {target_mode} is blocked."
    )
    return RuntimeModeTransitionPlan(
        current_mode=settings.runtime_mode,
        target_mode=target_mode,
        allowed=allowed,
        checks=checks,
        summary=summary,
    )


def _render_runtime_mode_transition_plan(plan: RuntimeModeTransitionPlan) -> None:
    """
    Render a runtime-mode transition checklist and summary to the console for operator review.
    
    Prints a table of each transition check (name, whether it passed, whether it is blocking, and details) and a summary panel showing the current mode, target mode, whether the transition is allowed, and the plan summary.
    
    Parameters:
        plan (RuntimeModeTransitionPlan): Plan containing the current and target modes, computed checks, overall allowance flag, and a human-readable summary.
    """
    table = Table(title="Runtime Mode Transition Checklist")
    table.add_column("Check")
    table.add_column("Passed")
    table.add_column("Blocking")
    table.add_column("Details")
    for check in plan.checks:
        table.add_row(
            check.name,
            "yes" if check.passed else "no",
            "yes" if check.blocking else "no",
            check.details,
        )
    console.print(
        Panel(
            f"Current: {plan.current_mode}\nTarget: {plan.target_mode}\nAllowed: {plan.allowed}\n\n{plan.summary}",
            title="Runtime Mode",
            border_style="green" if plan.allowed else "yellow",
        )
    )
    console.print(table)


def _runtime_status_payload(
    view: RuntimeStatusView, settings: Settings
) -> dict[str, object]:
    """Serialize the shared runtime status contract used by CLI and observer surfaces."""
    return {
        "runtime_mode": (
            view.state.runtime_mode if view.state is not None else settings.runtime_mode
        ),
        "runtime_state": view.runtime_state,
        "live_process": view.live_process,
        "is_stale": view.is_stale,
        "age_seconds": view.age_seconds,
        "status_message": view.status_message,
        "state": view.state.model_dump(mode="json") if view.state is not None else None,
    }


def _default_symbol_from_preferences(preferences: InvestmentPreferences) -> str:
    """
    Selects a sensible default trading symbol based on the given investment preferences.
    
    Prefers a Turkish exchange symbol ("THYAO.IS") when preferences indicate BIST or TR; prefers a US equity ("AAPL") when NASDAQ/NYSE or US region is present; otherwise returns a crypto USD symbol ("BTC-USD").
    
    Parameters:
        preferences (InvestmentPreferences): Saved investment preferences with `exchanges` and `regions` used to determine a representative default symbol.
    
    Returns:
        str: A default symbol string chosen from "THYAO.IS", "AAPL", or "BTC-USD".
    """
    if "BIST" in preferences.exchanges or "TR" in preferences.regions:
        return "THYAO.IS"
    if (
        "NASDAQ" in preferences.exchanges
        or "NYSE" in preferences.exchanges
        or "US" in preferences.regions
    ):
        return "AAPL"
    return "BTC-USD"


def _calendar_payload(
    settings: Settings, *, symbol: str | None = None
) -> dict[str, object]:
    """
    Builds a payload describing the market session for a resolved symbol and whether it could be retrieved.
    
    Parameters:
        symbol (str | None): Optional explicit symbol to use. If None, the function uses the latest run's symbol when available, otherwise derives a default from saved investment preferences.
    
    Returns:
        dict[str, object]: A dictionary with:
            - "available" (bool): True when a session was successfully inferred, False on error.
            - "error" (str | None): The exception message when unavailable, otherwise None.
            - "session" (dict | None): JSON-serializable market session data when available, otherwise None.
    """
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


def _news_payload(
    settings: Settings, *, symbol: str | None = None
) -> dict[str, object]:
    """
    Builds a payload containing recent news headlines for a resolved trading symbol.
    
    Parameters:
        settings (Settings): Application settings used to determine news mode and I/O behavior.
        symbol (str | None): Optional explicit symbol to fetch headlines for; when omitted the symbol is resolved from the latest run record or from saved preferences.
    
    Returns:
        dict[str, object]: A mapping with keys:
            - "available": `True` if headlines were retrieved, `False` otherwise.
            - "error": Error message string when unavailable, or `None` on success.
            - "mode": The configured news mode from `settings`.
            - "symbol": The resolved symbol used to fetch headlines (may be `None` if unresolved).
            - "headlines": A list of headline objects serialized as JSON-compatible dicts.
    """
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
    """
    Builds a payload containing a market snapshot and similar memory matches for a symbol/interval.
    
    Parameters:
        settings (Settings): Application settings and environment.
        symbol (str | None): Optional symbol to build or fetch the snapshot for. If omitted and
            `use_latest_run` is True or a latest run exists, the latest run's snapshot symbol is used.
        interval (str | None): Optional interval (e.g., "1d", "1h"). If omitted and a latest run
            snapshot is used, the latest run's interval is used.
        lookback (str): Historical range to include when building the snapshot (e.g., "180d").
        limit (int): Maximum number of similar memories to retrieve.
        use_latest_run (bool): When True, prefer the latest persisted run snapshot instead of
            fetching/building a new market snapshot.
    
    Returns:
        dict: A JSON-serializable payload with keys:
            - "available" (bool): `True` if the payload was built successfully, `False` on error.
            - "error" (str | None): Error message when `available` is `False`, otherwise `None`.
            - "snapshot" (dict | None): Snapshot serialized to JSON-compatible dict, or `None` if unavailable.
            - "matches" (list[dict]): List of retrieved memory matches serialized as JSON-compatible dicts.
    """
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
                    frame,
                    symbol=resolved_symbol,
                    interval=resolved_interval,
                    lookback=lookback,
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
                "retrieval_explanations": context.get(
                    "retrieval_explanations", []
                ),
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
    """
    Builds a payload containing recent chat history entries for observer/CLI consumption.
    
    Parameters:
        limit (int): Maximum number of most-recent chat history entries to include.
    
    Returns:
        dict: A mapping with keys:
            - "available": `True` if chat history was read successfully, `False` otherwise.
            - "error": Error message string when unavailable, or `None` on success.
            - "entries": List of chat history entries serialized to JSON-compatible dicts.
    """
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


def _run_replay_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    """
    Builds a JSON-serializable replay payload for a persisted run record for observer and CLI use.
    
    If a run record is not available or an error occurs while loading it, the payload will indicate availability as `False`, include the error message, and set `replay` to `None`.
    
    Parameters:
        run_id (str | None): Optional run identifier; when `None`, the latest persisted run is used.
    
    Returns:
        dict[str, object]: A payload containing:
            - `available` (bool): `True` when the replay was successfully built, `False` otherwise.
            - `error` (str | None): Error message when unavailable, otherwise `None`.
            - `replay` (dict | None): The replay data serialized to plain JSON-serializable structures when available; `None` if unavailable.
    """
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
        _operator_launcher()


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help=HELP_JSON)) -> None:
    """
    Check local environment and present LLM and database runtime status.
    
    When not emitting JSON, prints a table of environment fields and a readiness panel indicating whether the trading runtime can start with full LLM access. When `json_output` is true, emits an equivalent JSON payload instead of rendering terminal output.
    
    Parameters:
        json_output (bool): If true, emit the environment payload as JSON rather than rendering terminal output.
    """
    settings = get_settings()
    latest: str
    db_status = "ok"
    try:
        db = _open_db(settings, read_only=True)
        try:
            latest = _format_latest_order(db.latest_order())
        finally:
            db.close()
    except Exception as exc:
        latest = "unavailable"
        db_status = f"Database unavailable: {exc}"

    llm = LocalLLM(settings)
    health = llm.health_check()
    payload = {
        "model": settings.model_name,
        "base_url": settings.base_url,
        "runtime_dir": str(settings.runtime_dir),
        "runtime_mode": settings.runtime_mode,
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
    table.add_row("Runtime Mode", settings.runtime_mode)
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


def _render_setup_status(payload: dict[str, object]) -> None:
    """Render local workspace and optional side-application readiness."""

    summary = Table(title="Setup Status")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Platform", str(payload["platform"]))
    summary.add_row("Workspace", str(payload["workspace_root"]))
    summary.add_row("Core Ready", str(payload["core_ready"]))
    summary.add_row("Optional Runtime Ready", str(payload["optional_ready"]))
    model_service = cast(dict[str, object], payload.get("model_service", {}))
    camofox_service = cast(dict[str, object], payload.get("camofox_service", {}))
    webgui_service = cast(dict[str, object], payload.get("webgui_service", {}))
    summary.add_row("Model Service", str(model_service.get("message", "-")))
    summary.add_row("Camofox", str(camofox_service.get("message", "-")))
    summary.add_row("Web GUI", str(webgui_service.get("message", "-")))
    console.print(summary)

    tools = cast(list[dict[str, object]], payload["tools"])
    table = Table(title="Tool Readiness")
    table.add_column("Tool")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Path")
    table.add_column("Notes")
    for tool in tools:
        notes = ", ".join(cast(list[str], tool.get("notes", [])))
        table.add_row(
            str(tool["label"]),
            str(tool["category"]),
            str(tool["status"]),
            str(tool.get("path") or "-"),
            notes or str(tool.get("install_hint") or "-"),
        )
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["recommended_commands"])),
            title="Recommended Next Commands",
            border_style="cyan",
        )
    )


def _render_model_service_status(payload: dict[str, object]) -> None:
    """Render app-owned model-service state and log tails."""

    table = Table(title="Model Service")
    table.add_column("Field")
    table.add_column("Value")
    for key in (
        "provider",
        "command_available",
        "command_path",
        "configured_base_url",
        "configured_model",
        "service_reachable",
        "model_available",
        "generation_checked",
        "generation_available",
        "generation_message",
        "app_owned",
        "pid",
        "base_url",
        "message",
        "runtime_base_url_matches_app_service",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload.get("available_models", []))) or "-",
            title="Available Models",
            border_style="green",
        )
    )
    stderr_tail = cast(list[str], payload.get("stderr_tail", []))
    if stderr_tail:
        console.print(
            Panel(
                "\n".join(stderr_tail),
                title="Model Service Stderr Tail",
                border_style="yellow",
            )
        )


def _render_webgui_service_status(payload: dict[str, object]) -> None:
    """Render app-owned Web GUI state and log tails."""

    table = Table(title="Web GUI Service")
    table.add_column("Field")
    table.add_column("Value")
    for key in (
        "command_available",
        "command_path",
        "package_available",
        "service_reachable",
        "app_owned",
        "pid",
        "host",
        "port",
        "url",
        "message",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    stderr_tail = cast(list[str], payload.get("stderr_tail", []))
    if stderr_tail:
        console.print(
            Panel(
                "\n".join(stderr_tail),
                title="Web GUI Stderr Tail",
                border_style="yellow",
            )
        )


def _render_camofox_service_status(payload: dict[str, object]) -> None:
    """Render app-owned Camofox helper state and log tails."""

    table = Table(title="Camofox Browser Helper")
    table.add_column("Field")
    table.add_column("Value")
    for key in (
        "command_available",
        "command_path",
        "package_available",
        "dependency_available",
        "access_key_configured",
        "service_reachable",
        "health_ok",
        "app_owned",
        "pid",
        "host",
        "port",
        "base_url",
        "tool_dir",
        "message",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    stderr_tail = cast(list[str], payload.get("stderr_tail", []))
    if stderr_tail:
        console.print(
            Panel(
                "\n".join(stderr_tail),
                title="Camofox Stderr Tail",
                border_style="yellow",
            )
        )


def _render_operator_launcher_status(payload: dict[str, object]) -> None:
    """Render the primary no-argument operator launcher status."""

    plan = cast(dict[str, object], payload["default_runtime_plan"])
    model_service = cast(dict[str, object], payload["model_service"])
    camofox_service = cast(dict[str, object], payload["camofox_service"])
    webgui_service = cast(dict[str, object], payload["webgui_service"])
    setup = cast(dict[str, object], payload["setup"])
    table = Table(title="Agentic Trader Operator Launcher")
    table.add_column("Surface")
    table.add_column("Status")
    table.add_column("Next")
    table.add_row(
        "Runtime Daemon",
        "active" if payload["runtime_active"] else str(payload["runtime_state"]),
        (
            f"{', '.join(cast(list[str], plan['symbols']))} "
            f"{plan['interval']} {plan['lookback']} / poll {plan['poll_seconds']}s"
        ),
    )
    table.add_row(
        "Web GUI",
        (
            "app-owned"
            if webgui_service.get("app_owned")
            else "external"
            if webgui_service.get("service_reachable")
            else str(webgui_service.get("message"))
        ),
        str(webgui_service.get("url") or "agentic-trader webgui-service start"),
    )
    table.add_row(
        "Model Service",
        "ready" if model_service.get("model_available") else str(model_service.get("message")),
        str(model_service.get("base_url") or model_service.get("configured_base_url")),
    )
    table.add_row(
        "Camofox",
        "ready" if camofox_service.get("health_ok") else str(camofox_service.get("message")),
        str(camofox_service.get("base_url") or "agentic-trader camofox-service start"),
    )
    table.add_row(
        "Setup",
        "ready" if setup.get("core_ready") else "needs attention",
        "agentic-trader setup-status --json",
    )
    console.print(table)
    console.print(
        Panel(
            "\n".join(
                [
                    "1  Open/start the local Web GUI command center",
                    "2  Start the default strict paper daemon",
                    "3  Open the Ink terminal control room",
                    "4  Open the Rich/admin fallback menu",
                    "5  Show local model-service status",
                    "6  Show Camofox browser helper status",
                    "7  Show setup/tool readiness",
                    "8  Exit",
                ]
            ),
            title="Choose A Surface",
            border_style="cyan",
        )
    )


def _operator_launcher() -> None:
    """Interactive no-argument product launcher."""

    settings = get_settings()
    payload = build_operator_launcher_status(settings).model_dump(mode="json")
    _render_operator_launcher_status(payload)
    choice = Prompt.ask(
        "Select action",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "q"],
        default="3",
    )
    if choice == "1":
        try:
            status = start_operator_webgui(settings)
        except Exception as exc:
            console.print(
                _render_health_panel(
                    "Web GUI Start Failed",
                    redact_sensitive_text(exc, max_length=240),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
        _render_webgui_service_status(status.model_dump(mode="json"))
        return
    if choice == "2":
        try:
            pid = start_default_background_runtime(settings)
        except Exception as exc:
            console.print(
                _render_health_panel(
                    "Daemon Start Blocked",
                    redact_sensitive_text(exc, max_length=240),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
        console.print(
            _render_health_panel(
                "Background Daemon Started",
                f"Paper-runtime daemon is running with PID {pid}.",
                border_style="green",
            )
        )
        return
    if choice == "3":
        ink_tui()
        return
    if choice == "4":
        run_main_menu()
        return
    if choice == "5":
        _render_model_service_status(
            build_model_service_status(settings).model_dump(mode="json")
        )
        return
    if choice == "6":
        _render_camofox_service_status(
            build_camofox_service_status(settings).model_dump(mode="json")
        )
        return
    if choice == "7":
        _render_setup_status(build_setup_status(settings).model_dump(mode="json"))
        return
    console.print(_render_health_panel("Exit", "No action selected.", border_style="blue"))


@app.command("setup-status")
def setup_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show source setup, optional tool, and model-service readiness."""

    settings = get_settings()
    payload = build_setup_status(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_setup_status(payload)


@app.command("setup")
def setup_command(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Report setup status. Use make bootstrap for interactive installs.",
    ),
) -> None:
    """Report the recommended local setup path without hidden installs."""

    settings = get_settings()
    status = build_setup_status(settings).model_dump(mode="json")
    payload = {
        "dry_run": dry_run,
        "mutated": False,
        "status": status,
        "message": "Run `make bootstrap` for the interactive system-tool installer.",
    }
    if json_output:
        _emit_json(payload)
        return
    _render_setup_status(status)
    console.print(
        _render_health_panel(
            "Setup Guidance",
            str(payload["message"]),
            border_style="cyan",
        )
    )


@model_service_app.command("status")
def model_service_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    probe_generation: bool = typer.Option(
        False,
        "--probe-generation",
        help=(
            "Run a tiny Ollama generation probe in addition to lightweight "
            "service/model checks."
        ),
    ),
) -> None:
    """Show local model-service and configured-model readiness."""

    settings = get_settings()
    payload = build_model_service_status(
        settings,
        include_generation=probe_generation,
    ).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_model_service_status(payload)


@model_service_app.command("start")
def model_service_start(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    host: str | None = typer.Option(
        None,
        "--host",
        help="Loopback bind host for app-managed Ollama.",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        min=1,
        max=65535,
        help="Preferred app-managed Ollama port.",
    ),
) -> None:
    """Start app-owned Ollama on loopback without touching external services."""

    settings = get_settings()
    try:
        payload = start_model_service(
            settings,
            host=host,
            port=port,
        ).model_dump(mode="json")
    except Exception as exc:
        error_payload = {
            "started": False,
            "error": redact_sensitive_text(exc, max_length=240),
        }
        if json_output:
            _emit_json(error_payload)
        else:
            console.print(
                _render_health_panel(
                    "Model Service Start Failed",
                    str(error_payload["error"]),
                    border_style="red",
                )
            )
        raise typer.Exit(code=1) from exc
    if json_output:
        _emit_json(payload)
        return
    _render_model_service_status(payload)


@model_service_app.command("stop")
def model_service_stop(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Stop only the app-owned model-service process recorded in runtime state."""

    settings = get_settings()
    payload = stop_model_service(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_model_service_status(payload)


@model_service_app.command("pull")
def model_service_pull(
    model_name: str = typer.Argument(..., help="Ollama model name to pull."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Pull an Ollama model for the configured or app-owned local service."""

    settings = get_settings()
    try:
        payload = pull_model(settings, model_name)
    except Exception as exc:
        payload = {
            "model": model_name,
            "exit_code": 1,
            "stderr": redact_sensitive_text(exc, max_length=240),
        }
    if json_output:
        _emit_json(payload)
    else:
        table = Table(title="Model Pull")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Model", str(payload["model"]))
        table.add_row("Exit Code", str(payload["exit_code"]))
        table.add_row("Stdout", str(payload.get("stdout", "")) or "-")
        table.add_row("Stderr", str(payload.get("stderr", "")) or "-")
        console.print(table)
    exit_code_value = payload.get("exit_code", 1)
    exit_code = exit_code_value if isinstance(exit_code_value, int) else 1
    if exit_code != 0:
        raise typer.Exit(code=1)


@webgui_service_app.command("status")
def webgui_service_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show app-owned local Web GUI readiness and log tails."""

    settings = get_settings()
    payload = build_webgui_service_status(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_webgui_service_status(payload)


@webgui_service_app.command("start")
def webgui_service_start(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    open_browser: bool = typer.Option(
        True,
        "--open-browser/--no-open-browser",
        help="Ask the OS to open the Web GUI URL after starting.",
    ),
) -> None:
    """Start the app-owned loopback Web GUI process."""

    settings = get_settings()
    try:
        payload = start_operator_webgui(
            settings,
            open_browser=open_browser,
        ).model_dump(mode="json")
    except Exception as exc:
        error_payload = {
            "started": False,
            "error": redact_sensitive_text(exc, max_length=240),
        }
        if json_output:
            _emit_json(error_payload)
        else:
            console.print(
                _render_health_panel(
                    "Web GUI Start Failed",
                    str(error_payload["error"]),
                    border_style="red",
                )
            )
        raise typer.Exit(code=1) from exc
    if json_output:
        _emit_json(payload)
        return
    _render_webgui_service_status(payload)


@webgui_service_app.command("stop")
def webgui_service_stop(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Stop only the app-owned local Web GUI process."""

    settings = get_settings()
    payload = stop_webgui_service(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_webgui_service_status(payload)


@camofox_service_app.command("status")
def camofox_service_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show app-owned Camofox browser helper readiness and log tails."""

    settings = get_settings()
    payload = build_camofox_service_status(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_camofox_service_status(payload)


@camofox_service_app.command("start")
def camofox_service_start(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    host: str | None = typer.Option(
        None,
        "--host",
        help="Loopback bind host for app-managed Camofox.",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        min=1,
        max=65535,
        help="Preferred app-managed Camofox port.",
    ),
) -> None:
    """Start app-owned Camofox on loopback without touching external helpers."""

    settings = get_settings()
    try:
        payload = start_camofox_service(
            settings,
            host=host,
            port=port,
        ).model_dump(mode="json")
    except Exception as exc:
        error_payload = {
            "started": False,
            "error": redact_sensitive_text(exc, max_length=240),
        }
        if json_output:
            _emit_json(error_payload)
        else:
            console.print(
                _render_health_panel(
                    "Camofox Start Failed",
                    str(error_payload["error"]),
                    border_style="red",
                )
            )
        raise typer.Exit(code=1) from exc
    if json_output:
        _emit_json(payload)
        return
    _render_camofox_service_status(payload)


@camofox_service_app.command("stop")
def camofox_service_stop(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Stop only the app-owned Camofox process recorded in runtime state."""

    settings = get_settings()
    payload = stop_camofox_service(settings).model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    _render_camofox_service_status(payload)


@app.command("runtime-mode-checklist")
def runtime_mode_checklist(
    target_mode: RuntimeMode = typer.Argument(
        ..., help="Target runtime mode: training or operation."
    ),
    check_provider: bool = typer.Option(
        True,
        "--provider-check/--skip-provider-check",
        help="Check local provider/model readiness for Operation mode.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the approved checklist for a Training/Operation mode transition."""
    settings = get_settings()
    plan = _runtime_mode_transition_plan(
        settings,
        target_mode=target_mode,
        check_provider=check_provider,
    )
    if json_output:
        _emit_json(plan.model_dump(mode="json"))
        return
    _render_runtime_mode_transition_plan(plan)


def _research_sidecar_payload(
    settings: Settings, *, probe: bool = False
) -> dict[str, object]:
    payload = build_research_sidecar_state(settings, probe=probe).model_dump(
        mode="json"
    )
    payload["latestSnapshot"] = _latest_research_snapshot_payload(settings)
    return payload


def _latest_research_snapshot_payload(settings: Settings) -> dict[str, object]:
    try:
        record = read_latest_research_snapshot(settings)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
        }
    if record is None:
        return {
            "available": False,
            "error": "no_research_snapshot_recorded",
        }
    return {
        "available": True,
        "record": record.model_dump(mode="json"),
    }


def _render_research_sidecar_state(payload: dict[str, object]) -> None:
    table = Table(title="Research Sidecar Status")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Mode", str(payload["mode"]))
    table.add_row("Enabled", str(payload["enabled"]))
    table.add_row("Backend", str(payload["backend"]))
    table.add_row("Status", str(payload["status"]))
    table.add_row("Updated At", str(payload["updated_at"]))
    table.add_row(
        "Watched Symbols",
        ", ".join(cast(list[str], payload["watched_symbols"])) or "-",
    )
    last_success = payload.get("last_successful_update_at")
    table.add_row("Last Successful Update", str(last_success or "-"))
    last_error = payload.get("last_error")
    table.add_row("Last Error", str(last_error or "-"))
    console.print(table)

    providers = cast(list[dict[str, object]], payload["provider_health"])
    provider_table = Table(title="Research Source Health")
    provider_table.add_column("Provider")
    provider_table.add_column("Type")
    provider_table.add_column("Enabled")
    provider_table.add_column("Freshness")
    provider_table.add_column("Message")
    for provider in providers:
        provider_table.add_row(
            str(provider["provider_id"]),
            str(provider["provider_type"]),
            str(provider["enabled"]),
            str(provider["freshness"]),
            str(provider["message"]),
        )
    console.print(provider_table)


@app.command("research-status")
def research_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    probe: bool = typer.Option(
        False,
        "--probe/--no-probe",
        help="Run one isolated sidecar provider probe before reporting status.",
    ),
) -> None:
    """Show optional research sidecar mode, backend, and source health."""
    settings = get_settings()
    payload = _research_sidecar_payload(settings, probe=probe)
    if json_output:
        _emit_json(payload)
        return
    _render_research_sidecar_state(payload)


@app.command("research-refresh")
def research_refresh(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    persist: bool = typer.Option(
        True,
        "--persist/--no-persist",
        help="Persist the sidecar snapshot to the runtime research JSON feed.",
    ),
) -> None:
    """Run one isolated research sidecar pass without touching broker execution."""
    settings = get_settings()
    result = ResearchSidecar(settings).collect_once()
    record_payload: dict[str, object] | None = None
    if persist:
        record = persist_research_result(settings, result)
        record_payload = record.model_dump(mode="json")
    payload = {
        "state": result.state.model_dump(mode="json"),
        "world_state": (
            result.world_state.model_dump(mode="json")
            if result.world_state is not None
            else None
        ),
        "memory_update": result.memory_update,
        "persisted": record_payload is not None,
        "record": record_payload,
    }
    if json_output:
        _emit_json(payload)
        return
    _render_research_sidecar_state(result.state.model_dump(mode="json"))
    if record_payload is not None:
        console.print(
            _render_health_panel(
                "Research Snapshot Persisted",
                f"Snapshot {record_payload['snapshot_id']} recorded in the research feed.",
                border_style="green",
            )
        )


def _render_research_flow_setup(payload: dict[str, object]) -> None:
    """Render optional CrewAI Flow setup state."""
    table = Table(title="Research CrewAI Flow Setup")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("CLI Available", str(payload["available"]))
    table.add_row("CLI Path", str(payload["cli_path"] or "-"))
    table.add_row("Version", str(payload["version"] or "-"))
    table.add_row("uv Available", str(payload["uv_available"]))
    table.add_row("Flow Dir", str(payload["flow_dir"]))
    table.add_row("Scaffold Exists", str(payload["flow_scaffold_exists"]))
    table.add_row("Environment Exists", str(payload["environment_exists"]))
    table.add_row("Python Version", str(payload["python_version"] or "-"))
    table.add_row("Lockfile Exists", str(payload["lockfile_exists"]))
    table.add_row("Core Dependency", str(payload["core_dependency"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["recommended_commands"])),
            title="Recommended Commands",
            border_style="cyan",
        )
    )


@app.command("research-flow-setup")
def research_flow_setup(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show optional CrewAI Flow setup status for the research sidecar backend."""
    settings = get_settings()
    payload = crewai_setup_status(settings)
    if json_output:
        _emit_json(payload)
        return
    _render_research_flow_setup(payload)


@app.command("research-crewai-setup")
def research_crewai_setup(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Compatibility alias for `research-flow-setup`."""
    settings = get_settings()
    payload = crewai_setup_status(settings)
    if json_output:
        _emit_json(payload)
        return
    _render_research_flow_setup(payload)


@app.command()
def run(
    symbol: str = typer.Option(..., help=HELP_SYMBOL),
    interval: str = typer.Option("1d", help=HELP_INTERVAL),
    lookback: str = typer.Option("180d", help=HELP_LOOKBACK),
) -> None:
    """Run one strict paper cycle and record its reviewable decision evidence."""
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
    interval: str = typer.Option("1d", help=HELP_INTERVAL),
    lookback: str = typer.Option("180d", help=HELP_LOOKBACK),
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
    """Start a foreground or managed background paper-runtime loop."""
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
) -> None:
    """Show the current paper portfolio and open positions."""
    settings = get_settings()
    payload = _portfolio_payload(settings)
    snapshot = PortfolioSnapshot.model_validate(
        cast(dict[str, object], payload["snapshot"])
    )
    position_payloads = cast(list[dict[str, object]], payload["positions"])
    positions = [
        PositionSnapshot.model_validate(position) for position in position_payloads
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
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    summary = Table(title="Portfolio")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Cash", f"{snapshot.cash:.2f}")
    summary.add_row(LABEL_MARKET_VALUE, f"{snapshot.market_value:.2f}")
    summary.add_row("Equity", f"{snapshot.equity:.2f}")
    summary.add_row("Realized PnL", f"{snapshot.realized_pnl:.2f}")
    summary.add_row(LABEL_UNREALIZED_PNL, f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row("Open Positions", str(snapshot.open_positions))
    console.print(summary)

    positions_table = Table(title="Positions")
    positions_table.add_column("Symbol")
    positions_table.add_column("Quantity")
    positions_table.add_column("Average Price")
    positions_table.add_column("Market Price")
    positions_table.add_column(LABEL_MARKET_VALUE)
    positions_table.add_column(LABEL_UNREALIZED_PNL)
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
def status(json_output: bool = typer.Option(False, "--json", help=HELP_JSON)) -> None:
    """
    Show the current orchestrator runtime state.
    
    When json_output is True, emit a JSON payload containing keys
    `runtime_state`, `live_process`, `is_stale`, `age_seconds`,
    `status_message`, and `state`. Otherwise render a human-readable
    runtime status view to the terminal.
    
    Parameters:
        json_output (bool): If True, output the status as machine-readable JSON; if False, render rich terminal panels.
    """
    settings = get_settings()
    state = read_service_state(settings)
    if json_output:
        view = build_runtime_status_view(state)
        _emit_json(_runtime_status_payload(view, settings))
        return
    _render_service_state(state)


@app.command("supervisor-status")
def supervisor_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
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
            "\n".join(cast(list[str], payload["stdout_tail"]))
            or "No stdout log lines yet.",
            title="Service Stdout Tail",
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stderr_tail"]))
            or "No stderr log lines yet.",
            title="Service Stderr Tail",
            border_style="yellow",
        )
    )


@app.command("broker-status")
def broker_status(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
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
    table.add_row("Adapter", str(payload["adapter_name"]))
    table.add_row("State", str(payload["state"]))
    table.add_row("Simulated", str(payload["simulated"]))
    table.add_row("Live Execution Enabled", str(payload["live_execution_enabled"]))
    table.add_row("Kill Switch Active", str(payload["kill_switch_active"]))
    table.add_row("Live Requested", str(payload["live_requested"]))
    table.add_row("Live Ready", str(payload["live_ready"]))
    table.add_row("Message", str(payload["message"]))
    healthcheck = payload.get("healthcheck")
    if isinstance(healthcheck, dict):
        table.add_row("Healthcheck", str(healthcheck.get("message", "-")))
    console.print(table)


def _render_readiness_checks(title: str, payload: dict[str, object]) -> None:
    checks = payload.get("checks", [])
    table = Table(title=title)
    table.add_column("Check")
    table.add_column("State")
    table.add_column("Blocking")
    table.add_column("Details")
    if isinstance(checks, list):
        for item in checks:
            if not isinstance(item, dict):
                continue
            passed = bool(item.get("passed"))
            table.add_row(
                str(item.get("name", "-")),
                "[green]pass[/green]" if passed else "[red]fail[/red]",
                str(item.get("blocking", True)),
                str(item.get("details", "")),
            )
    console.print(table)


@app.command("provider-diagnostics")
def provider_diagnostics(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
) -> None:
    """Show configured model, market, research, and data-provider readiness."""
    settings = get_settings()
    payload = provider_diagnostics_payload(settings)
    if json_output:
        _emit_json(payload)
        return

    summary = Table(title="Provider Diagnostics")
    summary.add_column("Field")
    summary.add_column("Value")
    llm = payload.get("llm", {})
    market_data = payload.get("market_data", {})
    news = payload.get("news", {})
    alpaca = payload.get("alpaca", {})
    if isinstance(llm, dict):
        summary.add_row("LLM Provider", str(llm.get("provider", "-")))
        summary.add_row("Default Model", str(llm.get("default_model", "-")))
        summary.add_row("Base URL", str(llm.get("base_url", "-")))
    if isinstance(market_data, dict):
        summary.add_row(
            "Market Provider", str(market_data.get("selected_provider", "-"))
        )
        summary.add_row("Market Role", str(market_data.get("selected_role", "-")))
    if isinstance(news, dict):
        summary.add_row("News Mode", str(news.get("mode", "-")))
    if isinstance(alpaca, dict):
        summary.add_row("Alpaca Paper Endpoint", str(alpaca.get("paper_endpoint", "-")))
        summary.add_row("Alpaca Feed", str(alpaca.get("data_feed", "-")))
        summary.add_row(
            "Alpaca Credentials Configured",
            str(alpaca.get("credentials_configured", False)),
        )
    console.print(summary)

    provider_table = Table(title="Provider Source Ladder")
    provider_table.add_column("Provider")
    provider_table.add_column("Type")
    provider_table.add_column("Role")
    provider_table.add_column("Enabled")
    provider_table.add_column("API Key")
    provider_table.add_column("Freshness")
    provider_table.add_column("Notes")
    providers = payload.get("providers", [])
    if isinstance(providers, list):
        for row in providers:
            if not isinstance(row, dict):
                continue
            provider_table.add_row(
                str(row.get("provider_id", "-")),
                str(row.get("provider_type", "-")),
                str(row.get("role", "-")),
                str(row.get("enabled", False)),
                str(row.get("api_key_ready", "-")),
                str(row.get("freshness", "-")),
                ", ".join(str(note) for note in row.get("notes", [])),
            )
    console.print(provider_table)


@app.command("v1-readiness")
def v1_readiness(
    check_provider: bool = typer.Option(
        False,
        "--provider-check/--skip-provider-check",
        help="Check local model/provider readiness; may call the configured LLM service.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the V1 paper-operation and Alpaca paper-readiness checklist."""
    settings = get_settings()
    payload = v1_readiness_payload(settings, check_provider=check_provider)
    if json_output:
        _emit_json(payload)
        return

    paper = payload.get("paper_operations", {})
    alpaca = payload.get("alpaca_paper", {})
    paper_allowed = isinstance(paper, dict) and bool(paper.get("allowed"))
    console.print(
        Panel(
            str(payload.get("summary", "V1 readiness status unavailable.")),
            title="V1 Readiness",
            border_style="green" if paper_allowed else "yellow",
        )
    )
    if isinstance(paper, dict):
        _render_readiness_checks("Paper Operation Checks", paper)
    if isinstance(alpaca, dict):
        _render_readiness_checks("Alpaca Paper Checks", alpaca)


@app.command("finance-ops")
def finance_ops(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show read-only broker/account/PnL/exposure/evidence checks for paper operation."""
    settings = get_settings()
    payload = _finance_ops_payload(settings)
    if json_output:
        _emit_json(payload)
        return
    _render_finance_ops(payload)


@app.command("trade-proposals")
def trade_proposals(
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by proposal state: pending, approved, rejected, executed, failed, expired.",
    ),
    limit: int = typer.Option(
        50, min=1, max=200, help="Maximum number of trade proposals to show."
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the manual-review trade proposal queue."""
    settings = get_settings()
    parsed_status = _parse_proposal_status(status)
    payload = _trade_proposals_payload(settings, status=parsed_status, limit=limit)
    if json_output:
        _emit_json(payload)
        return
    proposals = [
        TradeProposalRecord.model_validate(item)
        for item in cast(list[dict[str, object]], payload["proposals"])
    ]
    if not payload["available"]:
        console.print(
            Panel(
                f"Trade proposals are temporarily unavailable while the runtime writer owns the database.\n\n{payload['error']}",
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_trade_proposals(proposals)


@app.command("proposal-create")
def proposal_create(
    symbol: str = typer.Option(..., help=HELP_SYMBOL),
    side: str = typer.Option("buy", help="Trade side: buy or sell."),
    quantity: float | None = typer.Option(
        None, min=0.0, help="Share quantity. Either quantity or notional is required."
    ),
    notional: float | None = typer.Option(
        None, min=0.0, help="Dollar notional. Either quantity or notional is required."
    ),
    reference_price: float = typer.Option(
        ..., min=0.01, help="Reference price used for the proposal."
    ),
    confidence: float = typer.Option(
        0.5, min=0.0, max=1.0, help="Proposal confidence from 0.0 to 1.0."
    ),
    thesis: str = typer.Option(..., help="Short operator-readable proposal thesis."),
    order_type: str = typer.Option(
        "market", help="Proposal order type. V1 supports market or limit."
    ),
    stop_loss: float | None = typer.Option(None, min=0.01, help="Optional stop loss."),
    take_profit: float | None = typer.Option(
        None, min=0.01, help="Optional take profit."
    ),
    invalidation_condition: str | None = typer.Option(
        None, help="Optional condition that invalidates the trade idea."
    ),
    source: str = typer.Option(
        "manual", help="Source label such as manual, scanner, or research-sidecar."
    ),
    review_notes: str = typer.Option("", help="Optional review notes."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Create a pending trade proposal; this does not execute an order."""
    settings = get_settings()
    try:
        db = _open_db(settings)
        try:
            proposal = create_trade_proposal(
                db=db,
                symbol=symbol,
                side=_parse_trade_side(side),
                order_type=_parse_order_type(order_type),
                quantity=quantity,
                notional=notional,
                reference_price=reference_price,
                confidence=confidence,
                thesis=thesis,
                stop_loss=stop_loss,
                take_profit=take_profit,
                invalidation_condition=invalidation_condition,
                source=source,
                review_notes=review_notes,
            )
        finally:
            db.close()
    except ValueError as exc:
        console.print(Panel(str(exc), title="Proposal Rejected", border_style="red"))
        raise typer.Exit(code=2) from exc
    payload = proposal.model_dump(mode="json")
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            f"{proposal.proposal_id} queued for manual review.\n\n"
            f"{proposal.symbol} {proposal.side.upper()} @ {proposal.reference_price:.4f}",
            title="Trade Proposal Created",
            border_style="green",
        )
    )


@app.command("proposal-approve")
def proposal_approve(
    proposal_id: str = typer.Argument(..., help="Trade proposal id to approve."),
    review_notes: str = typer.Option("", help="Optional approval notes."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Approve a pending proposal and submit it to the configured paper broker."""
    settings = get_settings()
    try:
        db = _open_db(settings)
        try:
            proposal, outcome = approve_trade_proposal(
                db=db,
                settings=settings,
                proposal_id=proposal_id,
                review_notes=review_notes,
            )
        finally:
            db.close()
    except (RuntimeError, ValueError) as exc:
        console.print(Panel(str(exc), title="Approval Blocked", border_style="red"))
        raise typer.Exit(code=2) from exc
    payload = {
        "proposal": proposal.model_dump(mode="json"),
        "outcome": outcome.model_dump(mode="json"),
    }
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            f"{proposal.proposal_id} -> {proposal.status}\n"
            f"order={proposal.execution_order_id or '-'} status={outcome.status}",
            title="Trade Proposal Approved",
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


@app.command("proposal-reconcile")
def proposal_reconcile(
    proposal_id: str = typer.Argument(
        ..., help="In-flight approved proposal id to reconcile."
    ),
    review_notes: str = typer.Option("", help="Optional reconciliation notes."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Repair an approved proposal from a recorded execution outcome without resubmitting."""
    settings = get_settings()
    try:
        db = _open_db(settings)
        try:
            proposal, execution_record = reconcile_trade_proposal(
                db=db,
                proposal_id=proposal_id,
                review_notes=review_notes,
            )
        finally:
            db.close()
    except ValueError as exc:
        console.print(
            Panel(str(exc), title="Reconciliation Blocked", border_style="red")
        )
        raise typer.Exit(code=2) from exc
    payload = {
        "proposal": proposal.model_dump(mode="json"),
        "execution_record": execution_record,
        "resubmitted": False,
    }
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            f"{proposal.proposal_id} -> {proposal.status}\n"
            f"order={proposal.execution_order_id or '-'} "
            f"status={proposal.execution_outcome_status or '-'}\n"
            "No broker resubmission was attempted.",
            title="Trade Proposal Reconciled",
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


@app.command("proposal-reject")
def proposal_reject(
    proposal_id: str = typer.Argument(..., help="Trade proposal id to reject."),
    reason: str = typer.Option(..., help="Human-readable rejection reason."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Reject a pending proposal and make the terminal decision auditable."""
    settings = get_settings()
    try:
        db = _open_db(settings)
        try:
            proposal = reject_trade_proposal(
                db=db, proposal_id=proposal_id, reason=reason
            )
        finally:
            db.close()
    except ValueError as exc:
        console.print(Panel(str(exc), title="Rejection Blocked", border_style="red"))
        raise typer.Exit(code=2) from exc
    if json_output:
        _emit_json(proposal.model_dump(mode="json"))
        return
    console.print(
        Panel(
            f"{proposal.proposal_id} rejected.\n\nReason: {proposal.rejection_reason}",
            title="Trade Proposal Rejected",
            border_style="yellow",
        )
    )


@app.command("idea-presets")
def idea_presets(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show V1 idea-scanner presets and their operator intent."""
    payload = {
        "presets": [
            {
                "name": name,
                "description": description,
                "strategy_profile": strategy_profile_for_preset(name).to_payload(),
            }
            for name, description in PRESET_DESCRIPTIONS.items()
        ],
        "execution_policy": "scanner ideas must become proposals and require manual approval",
    }
    if json_output:
        _emit_json(payload)
        return
    table = Table(title="Idea Scanner Presets")
    table.add_column("Preset")
    table.add_column("Intent")
    for item in cast(list[dict[str, str]], payload["presets"]):
        table.add_row(item["name"], item["description"])
    console.print(table)


@app.command("idea-score")
def idea_score(
    symbol: str = typer.Option(..., help=HELP_SYMBOL),
    preset: str = typer.Option("momentum", help="Idea preset to apply."),
    price: float = typer.Option(..., min=0.01, help="Last or reference price."),
    volume: float = typer.Option(..., min=0.0, help="Latest volume."),
    change_pct: float = typer.Option(..., help="Percent change over the scan window."),
    relative_volume: float = typer.Option(0.0, min=0.0, help="Relative volume."),
    gap_pct: float = typer.Option(0.0, help="Opening gap percent."),
    range_pct: float = typer.Option(0.0, min=0.0, help="Intraday range percent."),
    rsi: float | None = typer.Option(None, min=0.0, max=100.0, help="RSI value."),
    ema_9: float | None = typer.Option(None, min=0.0, help="9 EMA value."),
    sma_20: float | None = typer.Option(None, min=0.0, help="20 SMA value."),
    sma_50: float | None = typer.Option(None, min=0.0, help="50 SMA value."),
    vwap: float | None = typer.Option(None, min=0.0, help="VWAP value."),
    spread_pct: float = typer.Option(0.0, min=0.0, help="Bid/ask spread percent."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Score a single scanner candidate without creating or executing a proposal."""
    candidate = IdeaCandidate(
        symbol=symbol,
        price=price,
        volume=volume,
        change_pct=change_pct,
        relative_volume=relative_volume,
        gap_pct=gap_pct,
        range_pct=range_pct,
        rsi=rsi,
        ema_9=ema_9,
        sma_20=sma_20,
        sma_50=sma_50,
        vwap=vwap,
        spread_pct=spread_pct,
    )
    parsed_preset = _parse_idea_preset(preset)
    ranked = rank_candidates([candidate], preset=parsed_preset, limit=1)
    if not ranked:
        raise typer.BadParameter(
            f"No score could be produced for {symbol!r} with preset {parsed_preset!r}."
        )
    result = ranked[0]
    payload = {
        "score": result.__dict__,
        "strategy": score_strategy_context(result),
        "execution_policy": "score output is research only; use proposal-create for manual review",
    }
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            f"{result.symbol} {result.signal.upper()} score={result.score:.2f}\n\n"
            f"Reasons: {', '.join(result.reasons) or '-'}\n"
            f"Warnings: {', '.join(result.warnings) or '-'}",
            title=f"Idea Score: {result.preset}",
            border_style="cyan",
        )
    )


@app.command("strategy-catalog")
def strategy_catalog(
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by implemented, research-candidate, or v2-deferred.",
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="Filter by an idea-scanner preset such as momentum or breakout.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show repo-native strategy profiles and their V1 readiness gates."""
    parsed_status = _parse_strategy_status(status)
    parsed_preset = _parse_idea_preset(preset) if preset else None
    payload = strategy_catalog_payload(status=parsed_status, preset=parsed_preset)
    if json_output:
        _emit_json(payload)
        return
    table = Table(title="V1 Strategy Catalog")
    table.add_column("Profile")
    table.add_column("Family")
    table.add_column("Status")
    table.add_column("V1 Path")
    table.add_column("Summary")
    for item in cast(list[dict[str, object]], payload["profiles"]):
        table.add_row(
            str(item.get("name", "-")),
            str(item.get("family", "-")),
            str(item.get("status", "-")),
            str(item.get("v1_path", "-")),
            str(item.get("summary", "-")),
        )
    console.print(table)


@app.command("strategy-profile")
def strategy_profile(
    name: str = typer.Argument(..., help="Strategy profile name."),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show one strategy profile with evidence, risk, and validation gates."""
    try:
        profile = get_strategy_profile(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = {
        "profile": profile.to_payload(),
        "execution_policy": "profile is read-only research metadata; it cannot execute trades",
    }
    if json_output:
        _emit_json(payload)
        return
    profile_payload = payload["profile"]
    assert isinstance(profile_payload, dict)
    body = (
        f"{profile_payload['summary']}\n\n"
        f"Evidence: {', '.join(cast(list[str], profile_payload['evidence_requirements'])) or '-'}\n"
        f"Risk: {', '.join(cast(list[str], profile_payload['risk_controls'])) or '-'}\n"
        f"Validation: {', '.join(cast(list[str], profile_payload['validation_checks'])) or '-'}"
    )
    console.print(
        Panel(body, title=f"Strategy Profile: {profile.name}", border_style="cyan")
    )


@app.command("news-intelligence")
def news_intelligence(
    symbol: str = typer.Option(..., help=HELP_SYMBOL),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Optional company name for ticker disambiguation."
    ),
    sector: str | None = typer.Option(
        None, "--sector", help="Optional sector for sector-level news checks."
    ),
    classify_source: str | None = typer.Option(
        None,
        "--classify-source",
        help="Optionally classify a source domain or URL into the source tier policy.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Build a source-attributed news research plan without fetching the web."""
    try:
        payload = news_research_plan(
            symbol=symbol, company_name=company_name, sector=sector
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if classify_source:
        payload["classified_source"] = {
            "source": classify_source,
            "tier": classify_source_tier(classify_source),
        }
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            str(payload["prompt_policy"]),
            title=f"News Intelligence: {payload['symbol']}",
            border_style="cyan",
        )
    )
    table = Table(title="News Query Plan")
    table.add_column("Kind")
    table.add_column("Query")
    table.add_column("Materiality")
    for query in cast(list[dict[str, str]], payload["query_templates"]):
        table.add_row(
            query["kind"], query["query"], query["materiality_hint"]
        )
    console.print(table)


@app.command("research-cycle-plan")
def research_cycle_plan(
    symbols: str = typer.Option(
        "AAPL",
        "--symbols",
        help="Comma-separated watchlist symbols for the research cycle plan.",
    ),
    cadence_seconds: int = typer.Option(
        900,
        "--cadence-seconds",
        min=60,
        help="Target cadence for future daemonized research checks.",
    ),
    max_proposals_per_cycle: int = typer.Option(
        1,
        "--max-proposals-per-cycle",
        min=0,
        max=10,
        help="Maximum pending proposals the plan should allow per cycle.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the safe continuous research cycle contract without starting a daemon."""
    symbol_list = [
        item.strip().upper() for item in symbols.split(",") if item.strip()
    ]
    try:
        payload = research_cycle_plan_payload(
            symbols=symbol_list,
            cadence_seconds=cadence_seconds,
            max_proposals_per_cycle=max_proposals_per_cycle,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            str(payload["safety_policy"]),
            title=f"Research Cycle Plan: {payload['cycle']}",
            border_style="cyan",
        )
    )
    table = Table(title="Research Cycle Phases")
    table.add_column("Phase")
    table.add_column("Purpose")
    table.add_column("Produces")
    for phase in cast(list[dict[str, object]], payload["phases"]):
        produce = cast(list[str] | tuple[str, ...], phase.get("produce", []))
        table.add_row(
            str(phase.get("name", "-")),
            str(phase.get("purpose", "-")),
            ", ".join(str(item) for item in produce),
        )
    console.print(table)


@app.command("research-cycle-run")
def research_cycle_run(
    symbols: str = typer.Option(
        ..., "--symbols", help="Comma-separated watchlist symbols for this cycle."
    ),
    cycles: int = typer.Option(1, min=1, max=24, help="Bounded cycle count to run."),
    cadence_seconds: int = typer.Option(
        60,
        "--cadence-seconds",
        min=1,
        help="Seconds between cycles when --sleep is enabled.",
    ),
    max_proposals_per_cycle: int = typer.Option(
        1,
        "--max-proposals-per-cycle",
        min=0,
        max=10,
        help="Maximum pending proposals the run should allow in its plan only.",
    ),
    persist: bool = typer.Option(
        True,
        "--persist/--no-persist",
        help="Persist each research snapshot to the runtime research JSON feed.",
    ),
    sleep_between_cycles: bool = typer.Option(
        True,
        "--sleep/--no-sleep",
        help="Wait cadence_seconds between cycles. Use --no-sleep for QA smoke.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Run a bounded evidence-only research cycle without broker authority."""
    settings = get_settings()
    symbol_list = [
        item.strip().upper() for item in symbols.split(",") if item.strip()
    ]
    try:
        payload = run_research_cycle(
            settings,
            symbols=symbol_list,
            cycles=cycles,
            cadence_seconds=cadence_seconds,
            max_proposals_per_cycle=max_proposals_per_cycle,
            persist=persist,
            sleep_between_cycles=sleep_between_cycles,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if json_output:
        _emit_json(payload)
        return
    console.print(
        Panel(
            f"Executed {payload['executed_cycles']} evidence-only research cycle(s).\n"
            "Broker access, proposal approval, and raw web prompt injection stayed disabled.",
            title="Research Cycle Run",
            border_style="green",
        )
    )


@app.command()
def logs(
    limit: int = typer.Option(
        20, min=1, max=200, help="Maximum number of runtime events to show."
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Display recent orchestrator runtime events.
    
    Parameters:
        limit (int): Maximum number of runtime events to return.
        json_output (bool): If True, output the events as JSON instead of rendering rich panels.
    """
    settings = get_settings()
    events = read_service_events(settings, limit=limit)
    if json_output:
        _emit_json([event.model_dump(mode="json") for event in events])
        return
    _render_service_events(events)


@app.command("dashboard-snapshot")
def dashboard_snapshot(
    log_limit: int = typer.Option(
        14, min=1, max=100, help=HELP_RUNTIME_EVENT_LIMIT
    ),
    provider_check: bool = typer.Option(
        False,
        "--provider-check/--no-provider-check",
        help=HELP_PROVIDER_CHECK,
    ),
) -> None:
    """Emit the full Ink dashboard snapshot as a single JSON payload."""
    settings = get_settings()
    _emit_json(
        build_dashboard_snapshot_payload(
            settings,
            log_limit=log_limit,
            check_provider=provider_check,
        )
    )


def build_dashboard_snapshot_payload(
    settings: Settings, *, log_limit: int = 14, check_provider: bool = False
) -> dict[str, object]:
    """
    Assembles a JSON-serializable dashboard snapshot containing runtime, service, agent activity, and persisted payloads for the observer API.
    
    Builds health/doctor info, runtime status, supervisor, broker, model-service, and Web GUI payloads, recent service events and agent activity summary, and a collection of read-only payloads (portfolio, preferences, recent runs, journal, risk report, run review/trace/replay, trade/market context, canonical analysis, memory inspection, retrieval inspection, memory policy, chat history, calendar, news, and market cache).
    
    Parameters:
        settings (Settings): Application settings used to read service state, access the database, and resolve runtime paths.
        log_limit (int): Maximum number of recent service events to include in the `logs` section (default 14).
    
    Returns:
        dict[str, object]: A JSON-serializable snapshot keyed by sections including (but not limited to) `doctor`, `status`, `supervisor`, `broker`, `modelService`, `webGui`, `logs`, `agentActivity`, `portfolio`, `preferences`, `recentRuns`, `journal`, `riskReport`, `review`, `trace`, `tradeContext`, `marketContext`, `canonicalAnalysis`, `replay`, `memoryExplorer`, `retrievalInspection`, `memoryPolicy`, `chatHistory`, `calendar`, `news`, and `marketCache`.
    """
    llm = LocalLLM(settings)
    health = llm.health_check()
    state = read_service_state(settings)
    view = build_runtime_status_view(state)

    latest: str
    db_status = "ok"
    try:
        db = _open_db(settings, read_only=True)
        try:
            latest = _format_latest_order(db.latest_order())
        finally:
            db.close()
    except Exception as exc:
        latest = "unavailable"
        db_status = f"Database unavailable: {exc}"

    doctor_payload = {
        "model": settings.model_name,
        "runtime_mode": settings.runtime_mode,
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
    status_payload = _runtime_status_payload(view, settings)

    events = read_service_events(settings, limit=log_limit)
    activity = build_agent_activity_view(view.state, events)

    return {
        "doctor": doctor_payload,
        "status": status_payload,
        "supervisor": _service_supervisor_payload(settings),
        "broker": _broker_payload(settings),
        "modelService": build_model_service_status(settings).model_dump(mode="json"),
        "camofoxService": build_camofox_service_status(settings).model_dump(mode="json"),
        "webGui": build_webgui_service_status(settings).model_dump(mode="json"),
        "financeOps": _finance_ops_payload(settings),
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
        "recentRuns": _recent_runs_payload(settings, limit=8),
        "tradeProposals": _trade_proposals_payload(settings, limit=8),
        "journal": _journal_payload(settings, limit=8),
        "riskReport": _risk_report_payload(settings),
        "review": _run_record_payload(settings),
        "trace": _run_record_payload(settings),
        "tradeContext": _trade_context_payload(settings),
        "marketContext": _market_context_payload(settings),
        "canonicalAnalysis": _canonical_analysis_payload(settings),
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
        "research": _research_sidecar_payload(settings),
        "providerDiagnostics": provider_diagnostics_payload(settings),
        "v1Readiness": v1_readiness_payload(settings, check_provider=check_provider),
    }


def _claim_timestamped_dir(root: Path, label: str) -> Path:
    """Create a unique artifact directory using label or label-N."""
    root.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 1000):
        suffix = "" if attempt == 1 else f"-{attempt}"
        candidate = root / f"{label}{suffix}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    msg = f"Unable to create a unique artifact directory for {label!r}"
    raise RuntimeError(msg)


def _write_bundle_json(bundle_dir: Path, filename: str, payload: object) -> str:
    path = bundle_dir / filename
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def _latest_smoke_artifact_dir(artifacts_root: Path) -> Path | None:
    if not artifacts_root.exists():
        return None
    candidates = [
        path
        for path in artifacts_root.glob("smoke-*")
        if path.is_dir() and (path / "smoke-summary.json").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _run_probe_command(command: list[str], *, timeout: float = 2.0) -> str | None:
    try:
        proc = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    output = proc.stdout.strip()
    return output or None


def _total_memory_bytes() -> int | None:
    if sys.platform == "darwin":
        output = _run_probe_command(["sysctl", "-n", "hw.memsize"])
        if output and output.isdigit():
            return int(output)
    sysconf_total = _sysconf_total_memory_bytes()
    if sysconf_total is not None:
        return sysconf_total
    return _linux_meminfo_total_memory_bytes()


def _sysconf_total_memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        pages = page_size = None
    if (
        isinstance(pages, int)
        and isinstance(page_size, int)
        and pages > 0
        and page_size > 0
    ):
        return pages * page_size
    return None


def _linux_meminfo_total_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        lines = meminfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        total = _parse_memtotal_line(line)
        if total is not None:
            return total
    return None


def _parse_memtotal_line(line: str) -> int | None:
    if not line.startswith("MemTotal:"):
        return None
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1]) * 1024
    return None


def _model_size_billions(model_name: str) -> float | None:
    normalized = model_name.lower()
    for index, char in enumerate(normalized):
        if char != "b":
            continue
        next_char = normalized[index + 1] if index + 1 < len(normalized) else ""
        if next_char.isalnum():
            continue
        cursor = index - 1
        while cursor >= 0 and normalized[cursor].isspace():
            cursor -= 1
        end = cursor + 1
        while cursor >= 0 and (
            normalized[cursor].isdigit() or normalized[cursor] == "."
        ):
            cursor -= 1
        token = normalized[cursor + 1 : end]
        if not token or token.startswith(".") or token.endswith("."):
            continue
        try:
            return float(token)
        except ValueError:
            continue
    return None


def _accelerator_payload() -> dict[str, object]:
    if sys.platform == "darwin" and platform.machine().lower() == "arm64":
        return {
            "type": "apple_silicon",
            "detail": "Apple Silicon unified-memory accelerator available to supported local runtimes.",
        }
    if shutil.which("nvidia-smi"):
        output = _run_probe_command(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ]
        )
        if output:
            return {"type": "nvidia", "detail": output.splitlines()}
    return {
        "type": "unknown",
        "detail": "No accelerator probe succeeded with stdlib-safe local checks.",
    }


def _recommended_parallel_agents(
    cpu_count: int, memory_gb: float | None, model_b: float | None
) -> int:
    cpu_floor = max(1, cpu_count // 4)
    if memory_gb is None:
        recommended = min(2, cpu_floor)
    elif memory_gb < 24:
        recommended = 1
    elif memory_gb < 48:
        recommended = min(2, cpu_floor)
    else:
        recommended = min(4, cpu_floor)
    if model_b is not None and model_b >= 13 and (memory_gb is None or memory_gb < 48):
        recommended = 1
    return max(1, recommended)


def build_hardware_profile_payload(settings: Settings) -> dict[str, object]:
    """Build a local, read-only hardware/runtime capacity snapshot."""
    cpu_count = os.cpu_count() or 1
    memory_bytes = _total_memory_bytes()
    memory_gb = round(memory_bytes / (1024**3), 2) if memory_bytes else None
    model_b = _model_size_billions(settings.model_name)
    safe_parallel_agents = _recommended_parallel_agents(cpu_count, memory_gb, model_b)
    constrained = safe_parallel_agents == 1
    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
        },
        "hardware": {
            "cpu_count": cpu_count,
            "memory_bytes": memory_bytes,
            "memory_gb": memory_gb,
            "accelerator": _accelerator_payload(),
        },
        "configured_runtime": {
            "model_name": settings.model_name,
            "estimated_model_size_b": model_b,
            "max_output_tokens": settings.max_output_tokens,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_retries": settings.max_retries,
        },
        "recommendations": {
            "safe_parallel_agents": safe_parallel_agents,
            "max_output_tokens": min(settings.max_output_tokens, 2048)
            if constrained
            else settings.max_output_tokens,
            "request_timeout_seconds": max(settings.request_timeout_seconds, 180.0),
            "profile": "constrained-local" if constrained else "standard-local",
        },
        "notes": [
            "This is an operator hint, not an automatic runtime override.",
            "Use the lower of configured and recommended limits before long paper-operation runs.",
        ],
    }


def build_operator_workflow_payload(settings: Settings) -> dict[str, object]:
    """Return the canonical V1 operator review workflow without executing it."""
    steps = [
        {
            "order": 1,
            "name": "environment_doctor",
            "command": "agentic-trader doctor",
            "purpose": "Verify model, runtime directory, database path, and basic provider reachability.",
            "required_before_long_run": True,
        },
        {
            "order": 2,
            "name": "hardware_profile",
            "command": "agentic-trader hardware-profile",
            "purpose": "Inspect local CPU, memory, accelerator hints, model size, and safe parallelism recommendations.",
            "required_before_long_run": True,
        },
        {
            "order": 3,
            "name": "provider_diagnostics",
            "command": "agentic-trader provider-diagnostics",
            "purpose": "Inspect source ladder, API-key readiness, and fallback warnings without leaking secrets.",
            "required_before_long_run": True,
        },
        {
            "order": 4,
            "name": "v1_readiness",
            "command": "agentic-trader v1-readiness --provider-check",
            "purpose": "Verify paper-operation gates and Alpaca external-paper readiness before longer operation.",
            "required_before_long_run": True,
        },
        {
            "order": 5,
            "name": "fast_smoke",
            "command": "pnpm run qa",
            "purpose": "Run CLI/Rich/Ink smoke QA and produce smoke-summary.json plus qa-report.md.",
            "required_before_long_run": True,
        },
        {
            "order": 6,
            "name": "one_cycle",
            "command": "pnpm run qa -- --include-runtime-cycle --runtime-symbol AAPL --runtime-interval 1d --runtime-lookback 180d",
            "purpose": "Optionally prove one strict foreground agent cycle with isolated runtime storage.",
            "required_before_long_run": False,
        },
        {
            "order": 7,
            "name": "review_outputs",
            "command": "agentic-trader review-run && agentic-trader trace-run && agentic-trader trade-context",
            "purpose": "Inspect decision, stage trace, context pack, broker outcome, and reviewable rationale.",
            "required_before_long_run": True,
        },
        {
            "order": 8,
            "name": "evidence_bundle",
            "command": "agentic-trader evidence-bundle",
            "purpose": "Package shared runtime truth, readiness payloads, logs, hardware profile, and latest smoke report.",
            "required_before_long_run": True,
        },
        {
            "order": 9,
            "name": "background_paper_operation",
            "command": "agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background",
            "purpose": "Start longer paper operation only after the readiness and evidence steps are understood.",
            "required_before_long_run": False,
        },
    ]
    return {
        "workflow_version": "operator-workflow.v1",
        "runtime_mode": settings.runtime_mode,
        "execution_backend": settings.execution_backend,
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "paper_first": settings.execution_backend == "paper"
        and not settings.live_execution_enabled,
        "steps": steps,
        "safety_notes": [
            "This workflow is descriptive and does not execute runtime actions.",
            "Live execution remains blocked until explicitly approved and implemented.",
            "Paper evidence and operator review should precede any longer background run.",
        ],
    }


@app.command("operator-workflow")
def operator_workflow_command(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the canonical V1 operator review workflow without executing it."""
    settings = get_settings()
    payload = build_operator_workflow_payload(settings)
    if json_output:
        _emit_json(payload)
        return
    table = Table(title="V1 Operator Workflow")
    table.add_column("#", style="cyan")
    table.add_column("Step")
    table.add_column("Command")
    table.add_column("Purpose")
    for step in cast(list[dict[str, object]], payload["steps"]):
        table.add_row(
            str(step["order"]),
            str(step["name"]),
            str(step["command"]),
            str(step["purpose"]),
        )
    console.print(
        Panel(
            "Read-only workflow guide. Review readiness and evidence before long paper operation.",
            title="Operator Workflow",
            border_style="cyan",
        )
    )
    console.print(table)


@app.command("hardware-profile")
def hardware_profile_command(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show local hardware and model-capacity hints before long paper runs."""
    settings = get_settings()
    payload = build_hardware_profile_payload(settings)
    if json_output:
        _emit_json(payload)
        return

    hardware = cast(dict[str, object], payload["hardware"])
    configured = cast(dict[str, object], payload["configured_runtime"])
    recommendations = cast(dict[str, object], payload["recommendations"])
    table = Table(title="Hardware Profile")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("CPU Count", str(hardware["cpu_count"]))
    table.add_row("Memory GB", str(hardware["memory_gb"]))
    accelerator = cast(dict[str, object], hardware["accelerator"])
    table.add_row("Accelerator", str(accelerator.get("type", "unknown")))
    table.add_row("Model", str(configured["model_name"]))
    table.add_row("Estimated Model Size", str(configured["estimated_model_size_b"]))
    table.add_row("Safe Parallel Agents", str(recommendations["safe_parallel_agents"]))
    table.add_row("Token Hint", str(recommendations["max_output_tokens"]))
    table.add_row("Profile", str(recommendations["profile"]))
    console.print(table)


def build_evidence_bundle(
    settings: Settings,
    *,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    """Create a read-only QA evidence bundle from shared runtime contracts."""
    artifacts_root = output_dir.expanduser() if output_dir is not None else QA_ARTIFACTS_ROOT
    if not artifacts_root.is_absolute():
        artifacts_root = PROJECT_ROOT / artifacts_root
    run_label = label or f"evidence-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    bundle_dir = _claim_timestamped_dir(artifacts_root, run_label)

    state = read_service_state(settings)
    status_view = build_runtime_status_view(state)
    operation_plan = _runtime_mode_transition_plan(
        settings, target_mode="operation", check_provider=False
    )
    events = read_service_events(settings, limit=log_limit)
    files: dict[str, str] = {}
    files["dashboard"] = _write_bundle_json(
        bundle_dir,
        "dashboard-snapshot.json",
        build_dashboard_snapshot_payload(
            settings,
            log_limit=log_limit,
            check_provider=check_provider,
        ),
    )
    files["status"] = _write_bundle_json(
        bundle_dir,
        "status.json",
        _runtime_status_payload(status_view, settings),
    )
    files["broker"] = _write_bundle_json(
        bundle_dir,
        "broker-status.json",
        _broker_payload(settings),
    )
    files["finance_ops"] = _write_bundle_json(
        bundle_dir,
        "finance-ops.json",
        _finance_ops_payload(settings),
    )
    files["provider_diagnostics"] = _write_bundle_json(
        bundle_dir,
        "provider-diagnostics.json",
        provider_diagnostics_payload(settings),
    )
    files["v1_readiness"] = _write_bundle_json(
        bundle_dir,
        "v1-readiness.json",
        v1_readiness_payload(settings, check_provider=check_provider),
    )
    files["supervisor"] = _write_bundle_json(
        bundle_dir,
        "supervisor-status.json",
        _service_supervisor_payload(settings),
    )
    files["logs"] = _write_bundle_json(
        bundle_dir,
        "logs.json",
        {"logs": [event.model_dump(mode="json") for event in events]},
    )
    files["runtime_mode_operation"] = _write_bundle_json(
        bundle_dir,
        "runtime-mode-operation-checklist.json",
        operation_plan.model_dump(mode="json"),
    )
    files["operator_workflow"] = _write_bundle_json(
        bundle_dir,
        "operator-workflow.json",
        build_operator_workflow_payload(settings),
    )
    files["research"] = _write_bundle_json(
        bundle_dir,
        "research-status.json",
        _research_sidecar_payload(settings),
    )
    files["hardware_profile"] = _write_bundle_json(
        bundle_dir,
        "hardware-profile.json",
        build_hardware_profile_payload(settings),
    )

    latest_smoke_dir: Path | None = None
    if include_latest_smoke:
        latest_smoke_dir = _latest_smoke_artifact_dir(artifacts_root)
        if latest_smoke_dir is not None:
            for source_name, target_name, key in (
                ("smoke-summary.json", "latest-smoke-summary.json", "latest_smoke_summary"),
                ("qa-report.md", "latest-qa-report.md", "latest_qa_report"),
            ):
                source = latest_smoke_dir / source_name
                if source.exists():
                    target = bundle_dir / target_name
                    shutil.copyfile(source, target)
                    files[key] = str(target)

    manifest: dict[str, object] = {
        "bundle_version": "qa-evidence.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(bundle_dir),
        "runtime_dir": str(settings.runtime_dir),
        "database_path": str(settings.database_path),
        "log_limit": log_limit,
        "latest_smoke_dir": str(latest_smoke_dir) if latest_smoke_dir else None,
        "files": files,
    }
    manifest_path = bundle_dir / "manifest.json"
    files["manifest"] = str(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    return manifest


@app.command("evidence-bundle")
def evidence_bundle_command(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Artifact root. Defaults to .ai/qa/artifacts.",
    ),
    label: str | None = typer.Option(
        None,
        "--label",
        help="Bundle directory label. Defaults to evidence-YYYYMMDD-HHMMSS.",
    ),
    log_limit: int = typer.Option(
        20, min=1, max=200, help=HELP_RUNTIME_EVENT_LIMIT
    ),
    include_latest_smoke: bool = typer.Option(
        True,
        "--include-latest-smoke/--no-latest-smoke",
        help="Copy the latest smoke summary/report into the bundle when available.",
    ),
    provider_check: bool = typer.Option(
        False,
        "--provider-check/--no-provider-check",
        help=HELP_PROVIDER_CHECK,
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Collect read-only runtime, broker, readiness, and QA evidence into a bundle."""
    settings = get_settings()
    manifest = build_evidence_bundle(
        settings,
        output_dir=output_dir,
        label=label,
        log_limit=log_limit,
        include_latest_smoke=include_latest_smoke,
        check_provider=provider_check,
    )
    if json_output:
        _emit_json(manifest)
        return
    files = cast(dict[str, str], manifest["files"])
    table = Table(title="QA Evidence Bundle")
    table.add_column("Artifact", style="cyan")
    table.add_column("Path")
    for key, path in files.items():
        table.add_row(key, path)
    console.print(
        Panel(
            f"Bundle written to {manifest['bundle_dir']}",
            title="Evidence Bundle",
            border_style="green",
        )
    )
    console.print(table)


def build_observer_api_payload(
    settings: Settings, *, path: str, log_limit: int = 14
) -> tuple[int, dict[str, object]]:
    """
    Resolve an observer API request path into an HTTP status code and a JSON-serializable payload.
    
    Supported paths:
    - "/" or "/dashboard": returns a full dashboard snapshot payload.
    - "/health": returns service name, basic OK flag, and the runtime status sub-object.
    - "/status": returns a detailed runtime status view (runtime_state, live_process, is_stale, age_seconds, status_message, state).
    - "/logs": returns a list of recent service events under the "logs" key.
    - "/supervisor": returns supervisor status plus stdout/stderr log tails.
    - "/broker": returns broker runtime payload.
    - "/finance-ops": returns read-only broker/account/PnL/evidence checks.
    - "/provider-diagnostics": returns network-free provider/source readiness.
    - "/v1-readiness": returns V1 paper-operation and Alpaca paper-readiness gates.
    - "/research": returns optional research sidecar mode and provider health.
    - "/trade-proposals": returns the read-only manual-review proposal queue.
    - any other path: returns 404 with {"error": "not_found", "path": <requested path>}.
    
    Parameters:
        path (str): The requested API path.
        log_limit (int): Maximum number of log events to include for the "/logs" path.
    
    Returns:
        tuple[int, dict[str, object]]: A pair of (HTTP status code, payload dictionary) appropriate for the given path.
    """
    if path in {"/", "/dashboard"}:
        return 200, build_dashboard_snapshot_payload(settings, log_limit=log_limit)
    if path == "/health":
        return 200, {
            "service": "agentic-trader-observer-api",
            "ok": True,
            "runtime": build_runtime_status_view(
                read_service_state(settings)
            ).runtime_state,
        }
    if path == "/status":
        state = read_service_state(settings)
        view = build_runtime_status_view(state)
        return 200, _runtime_status_payload(view, settings)
    if path == "/logs":
        return 200, {
            "logs": [
                event.model_dump(mode="json")
                for event in read_service_events(settings, limit=log_limit)
            ]
        }
    if path == "/supervisor":
        return 200, _service_supervisor_payload(settings)
    if path == "/broker":
        return 200, _broker_payload(settings)
    if path == "/finance-ops":
        return 200, _finance_ops_payload(settings)
    if path == "/provider-diagnostics":
        return 200, provider_diagnostics_payload(settings)
    if path == "/v1-readiness":
        return 200, v1_readiness_payload(settings, check_provider=False)
    if path == "/research":
        return 200, _research_sidecar_payload(settings)
    if path == "/trade-proposals":
        return 200, _trade_proposals_payload(settings, limit=50)
    return 404, {"error": "not_found", "path": path}


@app.command("observer-api")
def observer_api_command(
    host: str = typer.Option(
        "127.0.0.1", help="Bind address for the local observer API."
    ),
    port: int = typer.Option(
        8765, min=1, max=65535, help="Bind port for the local observer API."
    ),
    log_limit: int = typer.Option(
        14, min=1, max=100, help=HELP_RUNTIME_EVENT_LIMIT
    ),
    allow_nonlocal: bool = typer.Option(
        False,
        "--allow-nonlocal",
        help=(
            "Allow binding the observer API to a non-loopback host. "
            "Requires AGENTIC_TRADER_OBSERVER_API_TOKEN."
        ),
    ),
) -> None:
    """Start the local read-only observer API with loopback-first safety gates."""
    settings = get_settings()
    nonlocal_bind = not is_loopback_host(host)
    if nonlocal_bind and (
        not allow_nonlocal or not settings.observer_api_token
    ):
        console.print(
            Panel(
                (
                    "Observer API is local-only by default. Use a loopback host "
                    "or set AGENTIC_TRADER_OBSERVER_API_TOKEN and pass "
                    "--allow-nonlocal for an intentional nonlocal read-only bind."
                ),
                title="Observer API Blocked",
                border_style="red",
            )
        )
        raise typer.Exit(code=2)
    console.print(
        Panel(
            f"Observer API listening on http://{host}:{port}\n\nAvailable endpoints:\n- /health\n- /dashboard\n- /status\n- /logs\n- /broker\n- /finance-ops\n- /provider-diagnostics\n- /v1-readiness\n- /research\n- /trade-proposals",
            title="Observer API",
            border_style="cyan",
        )
    )
    try:
        serve_observer_api(
            host=host,
            port=port,
            resolver=lambda path: build_observer_api_payload(
                settings, path=path, log_limit=log_limit
            ),
            allow_nonlocal=allow_nonlocal,
            token=settings.observer_api_token,
        )
    except ValueError as exc:
        console.print(
            Panel(str(exc), title="Observer API Blocked", border_style="red")
        )
        raise typer.Exit(code=2) from exc


@app.command("calendar-status")
def calendar_status(
    symbol: str | None = typer.Option(
        None,
        help="Optional ticker symbol. Defaults to the latest run symbol or preference-derived default.",
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Display the inferred market session status for a symbol.
    
    If `symbol` is omitted the function resolves a symbol from the latest run or user preferences. If `json_output` is true the command emits the raw payload as JSON. When session data is unavailable the command prints a notice and exits with code 0.
    
    Parameters:
        symbol (str | None): Optional ticker symbol; if None the latest run symbol or a preference-derived default is used.
        json_output (bool): When true, emit the raw payload as JSON instead of rendering a table.
    """
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Show a news brief for a resolved trading symbol or emit the raw payload as JSON.
    
    If no symbol is provided, the CLI resolves one from saved preferences or the latest run. With --json the function prints the underlying payload; otherwise it renders a short summary table and one panel per headline.
    @param symbol: Optional symbol override; when omitted the command resolves a default symbol from preferences or the latest run.
    @param json_output: When true, emit the raw payload as JSON instead of human-readable tables and panels.
    """
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
    headlines = cast(list[dict[str, object]], payload["headlines"])
    table.add_row("Headlines", str(len(headlines)))
    console.print(table)
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
                title=str(headline["symbol"]),
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
) -> None:
    """
    Show cached market snapshot metadata as a human-readable table or, when requested, emit the full payload as JSON.
    
    If the `--json` option is provided, the function emits the observer-style payload produced by the market cache payload builder; otherwise it prints a summarized table of recent cache entries and a compact cache status panel.
    """
    settings = get_settings()
    payload = _market_cache_payload(settings)
    if json_output:
        _emit_json(payload)
        return
    table = Table(title="Market Snapshot Cache")
    table.add_column("Filename")
    table.add_column("Size")
    table.add_column("Modified")
    entries = cast(list[dict[str, object]], payload["entries"])
    if not entries:
        table.add_row("-", "-", "-")
    else:
        for entry in entries[:20]:
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON)
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
                title=LABEL_OBSERVER_MODE,
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Display recent trade journal entries.
    
    Emits a formatted terminal table of up to `limit` journal entries, or emits the raw payload as JSON when `json_output` is true. If the journal is unavailable because the runtime writer owns the database, prints an observer-mode panel containing the error and exits.
    
    Parameters:
        limit (int): Maximum number of journal entries to show.
        json_output (bool): If true, output the full payload as JSON instead of rendering the table.
    
    Raises:
        typer.Exit: Raised with exit code 0 when the journal is unavailable.
    """
    settings = get_settings()
    payload = _journal_payload(settings, limit=limit)
    entry_payloads = cast(list[dict[str, object]], payload["entries"])
    entries = [TradeJournalEntry.model_validate(entry) for entry in entry_payloads]
    available = bool(payload["available"])
    error = payload["error"]
    if json_output:
        _emit_json(payload)
        return
    if not available:
        console.print(
            Panel(
                f"Trade journal is temporarily unavailable while the runtime writer owns the database.\n\n{error}",
                title=LABEL_OBSERVER_MODE,
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Display the daily risk report for the paper portfolio.
    
    Parameters:
        report_date (str | None): UTC date in `YYYY-MM-DD` format to report on. If None, uses today.
        json_output (bool): If true, emit the raw observer payload as JSON instead of rendering a human-readable report.
    """
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
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    _render_risk_report(report)


@app.command("review-run")
def review_run(
    run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Show a detailed review of the latest persisted run or a specific run by ID.
    
    If run data is temporarily unavailable because the runtime writer owns the database, prints an observer-mode panel and exits with code 0. If no persisted run is found, prints a notice panel and exits with code 0. When `json_output` is true, emits the raw payload as JSON instead of rendering the human-friendly review.
    
    Parameters:
        run_id (str | None): Optional run identifier; when omitted the latest run is used.
        json_output (bool): If true, output the underlying payload as JSON rather than rendering panels.
    """
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
                title=LABEL_OBSERVER_MODE,
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
    run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                title=LABEL_OBSERVER_MODE,
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Inspect persisted market, memory, model-routing, and rationale evidence."""
    settings = get_settings()
    payload = _trade_context_payload(settings, trade_id=trade_id)
    record = _trade_context_record_from_payload(payload)
    if json_output:
        _emit_json(payload)
        return
    if _render_unavailable_trade_context(payload, record):
        raise typer.Exit(code=0)
    assert record is not None
    _render_trade_context(record)


def _trade_context_record_from_payload(
    payload: dict[str, object],
) -> TradeContextRecord | None:
    if payload["record"] is None:
        return None
    return TradeContextRecord.model_validate(payload["record"])


def _render_unavailable_trade_context(
    payload: dict[str, object], record: TradeContextRecord | None
) -> bool:
    if not payload["available"]:
        console.print(
            Panel(
                f"Trade context is temporarily unavailable while the runtime writer owns the database.\n\n{payload['error']}",
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        return True
    if record is None:
        console.print(
            Panel(
                "No persisted trade context is available yet.",
                title="Trade Context",
                border_style="yellow",
            )
        )
        return True
    return False


def _render_trade_context(record: TradeContextRecord) -> None:
    summary = Table(title=f"Trade Context / {record.trade_id}")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Created", record.created_at)
    summary.add_row("Run ID", _value_or_dash(record.run_id))
    summary.add_row("Symbol", record.symbol)
    summary.add_row("Consensus", record.consensus.alignment_level)
    summary.add_row("Manager Rationale", record.manager_rationale)
    summary.add_row("Execution Rationale", record.execution_rationale)
    summary.add_row("Execution Backend", _value_or_dash(record.execution_backend))
    summary.add_row("Execution Adapter", _value_or_dash(record.execution_adapter))
    summary.add_row("Execution Outcome", _value_or_dash(record.execution_outcome_status))
    summary.add_row("Rejection Reason", _value_or_dash(record.execution_rejection_reason))
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
        f"Retrieved Memory Roles: {_join_or_dash(sorted(record.retrieved_memory_summary))}",
        f"Tool Output Roles: {_join_or_dash(sorted(record.tool_outputs))}",
        f"Shared Bus Roles: {_join_or_dash(sorted(record.shared_memory_summary))}",
        f"Review Warnings: {_join_or_dash(record.review_warnings)}",
    ]
    console.print(
        Panel(
            "\n".join(context_lines),
            title="Context Summary",
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(_canonical_analysis_lines(record.canonical_snapshot)),
            title="Canonical Analysis",
            border_style="blue",
        )
    )


@app.command("replay-run")
def replay_run(
    run_id: str | None = typer.Option(
        None, help="Run id to replay. Defaults to the latest recorded run."
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                title=LABEL_OBSERVER_MODE,
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
    symbol: str = typer.Option(..., help=HELP_SYMBOL),
    interval: str = typer.Option("1d", help=HELP_INTERVAL),
    lookback: str = typer.Option("2y", help=HELP_LOOKBACK),
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
    """
    Run a backtest using the agent pipeline in one of three modes: walk‑forward, baseline comparison, or memory ablation.
    
    Exactly one mode is executed per call: baseline comparison (when --compare-baseline), memory ablation (when --compare-memory), or the default walk‑forward backtest. Raises a parameter error if both comparison flags are set. When `output` is provided, writes a compact Markdown summary of the selected report to the given file path.
    
    Parameters:
        symbol (str): Ticker or symbol to backtest.
        interval (str): OHLCV interval (e.g., "1d").
        lookback (str): Historical lookback window (e.g., "2y").
        warmup_bars (int): Number of warmup bars to seed replay before metrics are collected (minimum 60).
        compare_baseline (bool): Run an agent vs deterministic baseline comparison.
        compare_memory (bool): Run an ablation comparing agent performance with memory enabled vs disabled.
        output (str | None): Optional file path to write a compact Markdown summary of the generated backtest report.
    """
    settings = get_settings()
    allow_diagnostic_fallback = _training_backtest_allow_fallback(settings)
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
            allow_fallback=allow_diagnostic_fallback,
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
            allow_fallback=allow_diagnostic_fallback,
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
        allow_fallback=allow_diagnostic_fallback,
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
                f"- {LABEL_WIN_RATE}: {report.win_rate:.2%}",
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
    symbol: str | None = typer.Option(None, help=HELP_SYMBOL),
    interval: str | None = typer.Option(None, help=HELP_INTERVAL),
    lookback: str = typer.Option("180d", help=HELP_LOOKBACK),
    limit: int = typer.Option(
        5, min=1, max=20, help="Maximum number of retrieved historical memories."
    ),
    use_latest_run: bool = typer.Option(
        True, help="Use the latest recorded run snapshot when available."
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Display historically similar recorded market memories for a resolved market snapshot.
    
    Resolves a symbol/interval/lookback snapshot (optionally using the latest run snapshot), retrieves up to `limit` similar historical memory matches, and renders them to the terminal. If `json_output` is true, emits the raw payload as JSON instead of rendering. If the explorer is unavailable, prints an observer-mode panel and exits the CLI with code 0.
    
    Parameters:
        symbol (str | None): Symbol override for the snapshot; when None the command will attempt to infer a symbol.
        interval (str | None): Time interval for the snapshot (e.g., "1d", "1h"); when None a default or inferred interval is used.
        lookback (str): Lookback window for the snapshot (e.g., "180d").
        limit (int): Maximum number of historical memory matches to retrieve (1–20).
        use_latest_run (bool): When true, prefer the latest recorded run snapshot if available.
        json_output (bool): If true, emit the raw payload as JSON instead of rendering terminal panels.
    """
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
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    match_payloads = cast(list[dict[str, object]], payload["matches"])
    matches = [HistoricalMemoryMatch.model_validate(match) for match in match_payloads]
    _render_memory_matches(matches)


def _retrieval_stage_counts(
    stage: dict[str, object],
) -> tuple[str, str, str, str, str, str]:
    """
    Extracts display-ready string values for a retrieval stage's role and counts of various retrieval-related lists.
    
    Parameters:
    	stage (dict[str, object]): A stage mapping expected to contain the keys:
    		- "role": role identifier
    		- "retrieved_memories": list of retrieved memory ids/entries
    		- "memory_notes": list of memory note strings
    		- "shared_memory_bus": list of shared-memory entry dicts
    		- "recent_runs": list of recent run identifiers
    
    Returns:
    	tuple[str, str, str, str, str]: A 5-tuple of strings:
    		(role, retrieved_memories_count, memory_notes_count, shared_memory_bus_count, recent_runs_count)
    """
    return (
        str(stage["role"]),
        str(len(cast(list[str], stage["retrieved_memories"]))),
        str(len(cast(list[dict[str, object]], stage["retrieval_explanations"]))),
        str(len(cast(list[str], stage["memory_notes"]))),
        str(len(cast(list[dict[str, object]], stage["shared_memory_bus"]))),
        str(len(cast(list[str], stage["recent_runs"]))),
    )


def _retrieval_stage_lines(stage: dict[str, object]) -> list[str]:
    """
    Builds human-readable lines describing retrieval and memory-related fields for a single retrieval stage.
    
    The input mapping is expected to contain the following keys:
    - "retrieved_memories": list[str] — similar memories retrieved for the stage.
    - "memory_notes": list[str] — notes derived from trade memory for the stage.
    - "shared_memory_bus": list[dict] — entries with at least "role" and "summary" keys describing shared memory items.
    - "recent_runs": list[str] — identifiers or summaries of recent runs relevant to the stage.
    - "tool_outputs": list[str] — outputs produced by tools during the stage.
    
    Parameters:
        stage (dict[str, object]): A stage payload containing retrieval/memory/tool fields as described above.
    
    Returns:
        list[str]: A list of formatted text lines suitable for display. If no relevant fields are present, returns a single-item list with the message "No retrieval or memory context was attached for this stage."
    """
    retrieved_memories = cast(list[str], stage["retrieved_memories"])
    retrieval_explanations = cast(
        list[dict[str, object]], stage["retrieval_explanations"]
    )
    memory_notes = cast(list[str], stage["memory_notes"])
    shared_memory_bus = cast(list[dict[str, object]], stage["shared_memory_bus"])
    recent_runs = cast(list[str], stage["recent_runs"])
    tool_outputs = cast(list[str], stage["tool_outputs"])
    sections = [
        ("Retrieved Similar Memories:", retrieved_memories),
        ("Why These Memories:", _retrieval_explanation_lines(retrieval_explanations)),
        ("Trade Memory:", memory_notes),
        ("Recent Runs:", recent_runs),
        (
            "Shared Memory Bus:",
            [f"{entry['role']}: {entry['summary']}" for entry in shared_memory_bus],
        ),
        ("Tool Outputs:", tool_outputs),
    ]
    lines: list[str] = []
    for title, values in sections:
        if not values:
            continue
        if lines:
            lines.append("")
        lines.append(title)
        lines.extend(f"- {line}" for line in values)
    return lines or ["No retrieval or memory context was attached for this stage."]


def _retrieval_explanation_lines(
    explanations: list[dict[str, object]],
) -> list[str]:
    lines: list[str] = []
    for item in explanations:
        run_id = str(item.get("run_id") or "-")
        explanation = item.get("explanation", {})
        if not isinstance(explanation, dict):
            continue
        reason = str(explanation.get("eligibility_reason") or "-")
        freshness = str(explanation.get("freshness") or "-")
        outcome = str(explanation.get("outcome_tag") or "-")
        bucket = str(explanation.get("diversity_bucket") or "-")
        lines.append(
            f"{run_id}: reason={reason} freshness={freshness} "
            f"outcome={outcome} bucket={bucket}"
        )
    return lines


def _render_retrieval_inspection(stages: list[dict[str, object]], run_id: object) -> None:
    """
    Render a retrieval-inspection summary and detailed panels for each agent stage to the console.
    
    Prints a table titled with the run identifier that summarizes retrieval counts per stage, then prints a detailed panel for each stage containing retrieval lines and context information.
    
    Parameters:
        stages (list[dict[str, object]]): A list of stage records where each dict represents an agent stage (each must include a 'role' key and the retrieval-related fields used to build the summary and detail lines).
        run_id (object): Identifier of the run displayed in the table title.
    """
    table = Table(title=f"Retrieval Inspection / {run_id}")
    table.add_column("Role")
    table.add_column("Retrieved Memories")
    table.add_column("Why")
    table.add_column("Trade Memory")
    table.add_column("Shared Bus")
    table.add_column("Recent Runs")
    for stage in stages:
        table.add_row(*_retrieval_stage_counts(stage))
    console.print(table)
    for stage in stages:
        console.print(
            Panel(
                "\n".join(_retrieval_stage_lines(stage)),
                title=f"Stage / {stage['role']}",
                border_style="cyan",
            )
        )


@app.command("retrieval-inspection")
def retrieval_inspection(
    run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Render an inspection of which memories and context bundles were injected into each agent stage for a given run.
    
    If --json is passed, emit the raw payload as JSON instead of rendering. When no run or stages are available the command prints a yellow observer-mode panel and exits with code 0.
    
    Parameters:
        run_id (str | None): Optional run identifier to inspect; when None the latest run is used.
        json_output (bool): If True, output the inspection payload as JSON rather than rendered panels.
    """
    settings = get_settings()
    payload = _retrieval_inspection_payload(settings, run_id=run_id)
    if json_output:
        _emit_json(payload)
        return
    if not payload["available"]:
        console.print(
            Panel(
                f"Retrieval inspection is temporarily unavailable.\n\n{payload['error']}",
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    stages = cast(list[dict[str, object]], payload["stages"])
    if not stages:
        console.print(
            Panel(
                "No agent trace contexts are available for retrieval inspection yet.",
                title="Retrieval Inspection",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    _render_retrieval_inspection(stages, payload["run_id"])


@app.command("memory-policy")
def memory_policy(
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Send a message to a chosen operator persona and display or emit the persona's reply.
    
    If `message` is omitted an interactive prompt is shown. The interaction is recorded
    in persistent chat history. Output is printed as a terminal panel unless
    `json_output` is true, in which case a JSON payload containing `persona`,
    `message`, and `response` is emitted.
    
    Parameters:
    	persona (ChatPersona): Which agent persona should answer.
    	message (str | None): Optional message text; when None an interactive prompt is used.
    	json_output (bool): When true, emit a JSON payload instead of printing a panel.
    """
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Interpret an operator instruction and optionally apply any parsed preference update.
    
    Processes a natural-language operator instruction using the configured LLM and the trading
    database. If the parsed instruction proposes a preference update and `apply` is True,
    the update is persisted to the database. When `json_output` is True, emits a JSON object
    with keys `instruction` (the interpreted instruction), `applied` (true if an update was
    persisted), and `updated_preferences` (the new preferences or `null`). Otherwise the
    instruction is rendered to the console and any updated preferences are displayed.
    The database connection opened for this operation is closed before the function exits.
    
    Parameters:
        message (str): Natural-language operator instruction to interpret.
        apply (bool): If True, persist the parsed preference update when one is proposed.
        json_output (bool): If True, emit a JSON payload instead of rendering console output.
    """
    settings = get_settings()
    ensure_llm_ready(settings)
    db = TradingDatabase(settings)
    try:
        llm = LocalLLM(settings)
        instruction = interpret_operator_instruction(
            llm=llm,
            db=db,
            settings=settings,
            user_message=message,
            allow_fallback=True,
        )
        updated: InvestmentPreferences | None = None
        if apply and instruction.should_update_preferences:
            updated = apply_preference_update(db, instruction.preference_update)
        if json_output:
            _emit_json(
                {
                    "instruction": instruction.model_dump(mode="json"),
                    "applied": updated is not None,
                    "updated_preferences": (
                        updated.model_dump(mode="json") if updated is not None else None
                    ),
                }
            )
            return
        _render_instruction(instruction)
        if updated is not None:
            console.print(
                Panel(
                    updated.model_dump_json(indent=2),
                    title="Updated Preferences",
                    border_style="green",
                )
            )
    finally:
        db.close()


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
    """Open the primary Ink control room, with Rich fallback if needed."""
    tui_dir = Path(__file__).resolve().parent.parent / "tui"
    if not tui_dir.exists():
        console.print(
            _render_health_panel(
                "TUI Missing",
                "The Ink UI directory was not found. Falling back to the Rich control room.",
                border_style="yellow",
            )
        )
        run_main_menu()
        return

    node_commands = _resolve_tui_node_commands(tui_dir)
    if node_commands is None:
        console.print(
            _render_health_panel(
                "Node Missing",
                "A Node package manager is required to run the Ink control room. Falling back to the Rich control room.",
                border_style="yellow",
            )
        )
        run_main_menu()
        return
    install_command, start_command, command_cwd, package_manager = node_commands

    if not _tui_dependencies_installed(tui_dir, command_cwd):
        console.print(
            _render_health_panel(
                "Installing TUI Dependencies",
                f"First launch detected. Installing Ink dependencies with {package_manager}.",
                border_style="yellow",
            )
        )
        subprocess.run(install_command, cwd=command_cwd, check=True)

    cli_exec = shutil.which("agentic-trader") or "agentic-trader"
    env = {
        **os.environ,
        "AGENTIC_TRADER_CLI": cli_exec,
        "AGENTIC_TRADER_PYTHON": sys.executable,
    }
    subprocess.run(start_command, cwd=command_cwd, check=True, env=env)


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
        db = TradingDatabase(settings)
        try:
            db.upsert_service_state(
                state="stopped",
                continuous=state.continuous,
                poll_seconds=state.poll_seconds,
                cycle_count=state.cycle_count,
                symbols=state.symbols,
                interval=state.interval,
                lookback=state.lookback,
                max_cycles=state.max_cycles,
                current_symbol=None,
                message=f"Recovered stale runtime state from dead PID {state.pid}.",
                last_error=state.last_error,
                pid=None,
                clear_pid=True,
                stop_requested=False,
            )
            db.insert_service_event(
                level="warning",
                event_type="stale_service_recovered",
                message=f"Recovered stale runtime state from dead PID {state.pid}.",
                cycle_count=state.cycle_count if state.cycle_count > 0 else None,
                symbol=state.current_symbol,
            )
        finally:
            db.close()
        console.print(
            _render_health_panel(
                "Stale State Recovered",
                f"Dead PID {state.pid} is no longer alive. Runtime state was marked stopped and the stale PID was cleared.",
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
        terminate_service_process(state.pid)
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
