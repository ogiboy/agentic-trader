# pyright: reportUnusedFunction=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.backtest_reports import (
    EnsureReady,
    RunAblation,
    RunComparison,
    RunWalkForward,
    run_backtest_command,
)
from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.memory_commands import (
    MemoryCommandDeps,
    MemoryExplorerPayload,
    MemoryWritePolicySnapshot,
    RetrievalInspectionPayload,
    register_memory_commands,
)
from agentic_trader.cli_modules.run_reports import (
    join_or_dash,
    render_run_markdown,
    render_run_replay,
    render_run_review,
    render_run_trace,
    value_or_dash,
)
from agentic_trader.config import Settings
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
    DailyRiskReport,
    InvestmentPreferences,
    RunRecord,
    RunReplay,
    TradeContextRecord,
    TradeJournalEntry,
)
from agentic_trader.storage.db import TradingDatabase


class JournalPayload(Protocol):
    def __call__(self, settings: Settings, *, limit: int) -> dict[str, object]: ...


class RiskReportPayload(Protocol):
    def __call__(
        self, settings: Settings, *, report_date: str | None = None
    ) -> dict[str, object]: ...


class RunRecordPayload(Protocol):
    def __call__(
        self, settings: Settings, *, run_id: str | None = None
    ) -> dict[str, object]: ...


class TradeContextPayload(Protocol):
    def __call__(
        self, settings: Settings, *, trade_id: str | None = None
    ) -> dict[str, object]: ...


class RunReplayPayload(Protocol):
    def __call__(
        self, settings: Settings, *, run_id: str | None = None
    ) -> dict[str, object]: ...


class OpenDb(Protocol):
    def __call__(
        self, settings: Settings, *, read_only: bool = False
    ) -> TradingDatabase: ...


@dataclass(frozen=True)
class RecordCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    preferences_payload: Callable[[Settings], dict[str, object]]
    journal_payload: JournalPayload
    risk_report_payload: RiskReportPayload
    run_record_payload: RunRecordPayload
    trade_context_payload: TradeContextPayload
    canonical_analysis_lines: Callable[[CanonicalAnalysisSnapshot | None], list[str]]
    run_replay_payload: RunReplayPayload
    memory_explorer_payload: MemoryExplorerPayload
    retrieval_inspection_payload: RetrievalInspectionPayload
    memory_write_policy_snapshot: MemoryWritePolicySnapshot
    open_db: OpenDb
    ensure_ready: EnsureReady
    run_comparison: RunComparison
    run_ablation: RunAblation
    run_walk_forward: RunWalkForward


def register_record_commands(app: typer.Typer, deps: RecordCommandDeps) -> None:
    _register_preferences_command(app, deps)
    _register_journal_command(app, deps)
    _register_risk_report_command(app, deps)
    _register_run_review_commands(app, deps)
    _register_trade_context_command(app, deps)
    _register_replay_export_commands(app, deps)
    _register_backtest_command(app, deps)
    register_memory_commands(
        app,
        MemoryCommandDeps(
            get_settings=deps.get_settings,
            emit_json=deps.emit_json,
            memory_explorer_payload=deps.memory_explorer_payload,
            retrieval_inspection_payload=deps.retrieval_inspection_payload,
            memory_write_policy_snapshot=deps.memory_write_policy_snapshot,
        ),
    )


def _register_preferences_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("preferences")
    def preferences_command(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.preferences_payload(settings)
        preferences = InvestmentPreferences.model_validate(payload)
        available = bool(payload["available"])
        error = payload["error"]
        if json_output:
            deps.emit_json(payload)
            return
        if not available:
            console.print(
                Panel(
                    text.MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        _render_preferences(preferences)


def _render_preferences(preferences: InvestmentPreferences) -> None:
    table = Table(title=text.TITLE_INVESTMENT_PREFERENCES)
    table.add_column(text.LABEL_SETTING)
    table.add_column(text.LABEL_VALUE)
    table.add_row(text.LABEL_REGIONS, text.UI_LIST_SEPARATOR.join(preferences.regions) or "-")
    table.add_row(
        text.LABEL_EXCHANGES, text.UI_LIST_SEPARATOR.join(preferences.exchanges) or "-"
    )
    table.add_row(
        text.LABEL_CURRENCIES, text.UI_LIST_SEPARATOR.join(preferences.currencies) or "-"
    )
    table.add_row(text.LABEL_SECTORS, text.UI_LIST_SEPARATOR.join(preferences.sectors) or "-")
    table.add_row(text.LABEL_RISK_PROFILE, preferences.risk_profile)
    table.add_row(text.LABEL_TRADE_STYLE, preferences.trade_style)
    table.add_row(text.LABEL_BEHAVIOR_PRESET, preferences.behavior_preset)
    table.add_row(text.LABEL_AGENT_PROFILE, preferences.agent_profile)
    table.add_row(text.LABEL_AGENT_TONE, preferences.agent_tone)
    table.add_row(text.LABEL_STRICTNESS, preferences.strictness_preset)
    table.add_row(text.LABEL_INTERVENTION, preferences.intervention_style)
    table.add_row(text.LABEL_NOTES, preferences.notes or "-")
    console.print(table)


def _register_journal_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("journal")
    def journal(
        limit: int = typer.Option(20, min=1, max=200, help=text.HELP_TRADE_JOURNAL_LIMIT),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.journal_payload(settings, limit=limit)
        entry_payloads = cast(list[dict[str, object]], payload["entries"])
        entries = [TradeJournalEntry.model_validate(entry) for entry in entry_payloads]
        available = bool(payload["available"])
        error = payload["error"]
        if json_output:
            deps.emit_json(payload)
            return
        if not available:
            console.print(
                Panel(
                    text.MESSAGE_TRADE_JOURNAL_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        _render_trade_journal(entries)


def _render_trade_journal(entries: list[TradeJournalEntry]) -> None:
    if not entries:
        console.print(
            Panel(
                text.MESSAGE_NO_TRADE_JOURNAL_ENTRIES,
                title=text.TITLE_TRADE_JOURNAL,
                border_style="yellow",
            )
        )
        return

    table = Table(title=text.TITLE_TRADE_JOURNAL)
    table.add_column(text.LABEL_OPENED)
    table.add_column(text.LABEL_SYMBOL)
    table.add_column(text.LABEL_STATUS)
    table.add_column(text.LABEL_SIDE)
    table.add_column(text.LABEL_ENTRY)
    table.add_column(text.LABEL_EXIT)
    table.add_column(text.LABEL_PNL)
    table.add_column(text.LABEL_NOTES)
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


def _register_risk_report_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("risk-report")
    def risk_report(
        report_date: str | None = typer.Option(None, help=text.HELP_RISK_REPORT_DATE),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.risk_report_payload(settings, report_date=report_date)
        report = (
            DailyRiskReport.model_validate(payload["report"])
            if payload["report"] is not None
            else None
        )
        available = bool(payload["available"])
        error = payload["error"]
        if json_output:
            deps.emit_json(payload)
            return
        if not available or report is None:
            console.print(
                Panel(
                    text.MESSAGE_RISK_REPORT_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        _render_risk_report(report)


def _render_risk_report(report: DailyRiskReport) -> None:
    table = Table(title=text.TITLE_DAILY_RISK_REPORT + " / " + report.report_date)
    table.add_column(text.LABEL_FIELD)
    table.add_column(text.LABEL_VALUE)
    table.add_row(text.LABEL_GENERATED, report.generated_at)
    table.add_row(text.LABEL_CASH, f"{report.cash:.2f}")
    table.add_row(text.LABEL_MARKET_VALUE, f"{report.market_value:.2f}")
    table.add_row(text.LABEL_EQUITY, f"{report.equity:.2f}")
    table.add_row(text.LABEL_REALIZED_PNL, f"{report.realized_pnl:.2f}")
    table.add_row(text.LABEL_UNREALIZED_PNL, f"{report.unrealized_pnl:.2f}")
    table.add_row(text.LABEL_OPEN_POSITIONS, str(report.open_positions))
    table.add_row(text.LABEL_FILLS_TODAY, str(report.fills_today))
    table.add_row(text.LABEL_MARKS_RECORDED, str(report.marks_recorded))
    table.add_row(text.LABEL_DAILY_REALIZED_PNL, f"{report.daily_realized_pnl:.2f}")
    table.add_row(text.LABEL_GROSS_EXPOSURE, f"{report.gross_exposure_pct:.2%}")
    table.add_row(text.LABEL_LARGEST_POSITION, f"{report.largest_position_pct:.2%}")
    table.add_row(text.LABEL_DRAWDOWN_FROM_PEAK, f"{report.drawdown_from_peak_pct:.2%}")
    console.print(table)
    if report.warnings:
        console.print(
            Panel(
                "\n".join(f"- {warning}" for warning in report.warnings),
                title=text.TITLE_RISK_WARNINGS,
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                text.MESSAGE_NO_ELEVATED_PORTFOLIO_RISK_WARNINGS,
                title=text.TITLE_RISK_WARNINGS,
                border_style="green",
            )
        )


def _register_run_review_commands(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("review-run")
    def review_run(
        run_id: str | None = typer.Option(None, help=text.HELP_RUN_ID),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.run_record_payload(settings, run_id=run_id)
        record = _run_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if _render_unavailable_run_record(
            payload,
            record,
            unavailable_message=text.MESSAGE_RUN_REVIEW_TEMPORARILY_UNAVAILABLE,
            empty_message=text.MESSAGE_NO_PERSISTED_RUNS_REVIEW,
            empty_title=text.TITLE_RUN_REVIEW,
        ):
            raise typer.Exit(code=0)
        assert record is not None
        render_run_review(record)

    @app.command("trace-run")
    def trace_run(
        run_id: str | None = typer.Option(None, help=text.HELP_RUN_ID),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.run_record_payload(settings, run_id=run_id)
        record = _run_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if _render_unavailable_run_record(
            payload,
            record,
            unavailable_message=text.MESSAGE_RUN_TRACE_TEMPORARILY_UNAVAILABLE,
            empty_message=text.MESSAGE_NO_PERSISTED_RUNS_TRACE,
            empty_title=text.TITLE_TRACE,
        ):
            raise typer.Exit(code=0)
        assert record is not None
        render_run_trace(record)


def _run_record_from_payload(payload: dict[str, object]) -> RunRecord | None:
    return (
        RunRecord.model_validate(payload["record"])
        if payload["record"] is not None
        else None
    )


def _render_unavailable_run_record(
    payload: dict[str, object],
    record: RunRecord | None,
    *,
    unavailable_message: str,
    empty_message: str,
    empty_title: str,
) -> bool:
    if not bool(payload["available"]):
        console.print(
            Panel(
                unavailable_message.format(error=payload["error"]),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        return True
    if record is None:
        console.print(
            Panel(
                empty_message,
                title=empty_title,
                border_style="yellow",
            )
        )
        return True
    return False


def _register_trade_context_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("trade-context")
    def trade_context(
        trade_id: str | None = typer.Option(None, help=text.HELP_TRADE_CONTEXT_ID),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.trade_context_payload(settings, trade_id=trade_id)
        record = _trade_context_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if _render_unavailable_trade_context(payload, record):
            raise typer.Exit(code=0)
        assert record is not None
        _render_trade_context(record, canonical_analysis_lines=deps.canonical_analysis_lines)


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
                text.MESSAGE_TRADE_CONTEXT_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        return True
    if record is None:
        console.print(
            Panel(
                text.MESSAGE_NO_TRADE_CONTEXT,
                title=text.TITLE_TRADE_CONTEXT,
                border_style="yellow",
            )
        )
        return True
    return False


def _render_trade_context(
    record: TradeContextRecord,
    *,
    canonical_analysis_lines: Callable[[CanonicalAnalysisSnapshot | None], list[str]],
) -> None:
    summary = Table(title=text.TITLE_TRADE_CONTEXT_DETAIL.format(trade_id=record.trade_id))
    summary.add_column(text.LABEL_FIELD)
    summary.add_column(text.LABEL_VALUE)
    summary.add_row(text.LABEL_CREATED, record.created_at)
    summary.add_row(text.LABEL_RUN_ID, value_or_dash(record.run_id))
    summary.add_row(text.LABEL_SYMBOL, record.symbol)
    summary.add_row(text.LABEL_CONSENSUS, record.consensus.alignment_level)
    summary.add_row(text.LABEL_MANAGER_RATIONALE, record.manager_rationale)
    summary.add_row(text.LABEL_EXECUTION_RATIONALE, record.execution_rationale)
    summary.add_row(text.LABEL_EXECUTION_BACKEND, value_or_dash(record.execution_backend))
    summary.add_row(text.LABEL_EXECUTION_ADAPTER, value_or_dash(record.execution_adapter))
    summary.add_row(
        text.LABEL_EXECUTION_OUTCOME, value_or_dash(record.execution_outcome_status)
    )
    summary.add_row(
        text.LABEL_REJECTION_REASON, value_or_dash(record.execution_rejection_reason)
    )
    summary.add_row(text.LABEL_REVIEW_SUMMARY, record.review_summary)
    console.print(summary)

    routed_models = Table(title=text.TITLE_ROUTED_MODELS)
    routed_models.add_column(text.LABEL_ROLE)
    routed_models.add_column(text.LABEL_MODEL)
    if not record.routed_models:
        routed_models.add_row("-", "-")
    else:
        for role, model_name in sorted(record.routed_models.items()):
            routed_models.add_row(role, model_name)
    console.print(routed_models)

    context_lines = [
        f"{text.LABEL_RETRIEVED_MEMORY_ROLES}: {join_or_dash(sorted(record.retrieved_memory_summary))}",
        f"{text.LABEL_TOOL_OUTPUT_ROLES}: {join_or_dash(sorted(record.tool_outputs))}",
        f"{text.LABEL_SHARED_BUS_ROLES}: {join_or_dash(sorted(record.shared_memory_summary))}",
        f"{text.LABEL_WARNINGS}: {join_or_dash(record.review_warnings)}",
    ]
    console.print(
        Panel(
            "\n".join(context_lines),
            title=text.TITLE_CONTEXT_SUMMARY,
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(canonical_analysis_lines(record.canonical_snapshot)),
            title=text.TITLE_CANONICAL_ANALYSIS,
            border_style="blue",
        )
    )


def _register_replay_export_commands(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("replay-run")
    def replay_run(
        run_id: str | None = typer.Option(None, help=text.HELP_RUN_REPLAY_ID),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.run_replay_payload(settings, run_id=run_id)
        replay = (
            RunReplay.model_validate(payload["replay"])
            if payload["replay"] is not None
            else None
        )
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"]:
            console.print(
                Panel(
                    text.MESSAGE_RUN_REPLAY_TEMPORARILY_UNAVAILABLE.format(
                        error=payload["error"]
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        if replay is None:
            console.print(
                Panel(
                    text.MESSAGE_NO_PERSISTED_RUNS_REPLAY,
                    title=text.TITLE_RUN_REPLAY,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        render_run_replay(replay)

    @app.command("export-report")
    def export_report(
        output: str = typer.Option(..., help=text.HELP_EXPORT_REPORT_OUTPUT),
        run_id: str | None = typer.Option(None, help=text.HELP_EXPORT_REPORT_RUN_ID),
    ) -> None:
        settings = deps.get_settings()
        db = deps.open_db(settings, read_only=True)
        record = db.get_run(run_id) if run_id is not None else db.latest_run()
        if record is None:
            console.print(
                Panel(
                    text.MESSAGE_NO_PERSISTED_RUNS_EXPORT,
                    title=text.TITLE_EXPORT_BLOCKED,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1)
        rendered = render_run_markdown(record)
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        console.print(
            Panel(
                text.MESSAGE_RUN_REPORT_WRITTEN.format(output=output),
                title=text.TITLE_EXPORTED,
                border_style="green",
            )
        )


def _register_backtest_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("backtest")
    def backtest(
        symbol: str = typer.Option(..., help=text.HELP_SYMBOL),
        interval: str = typer.Option("1d", help=text.HELP_INTERVAL),
        lookback: str = typer.Option("2y", help=text.HELP_LOOKBACK),
        warmup_bars: int = typer.Option(120, min=60, help=text.HELP_BACKTEST_WARMUP_BARS),
        compare_baseline: bool = typer.Option(
            False, help=text.HELP_BACKTEST_COMPARE_BASELINE
        ),
        compare_memory: bool = typer.Option(False, help=text.HELP_BACKTEST_COMPARE_MEMORY),
        output: str | None = typer.Option(None, help=text.HELP_BACKTEST_OUTPUT),
    ) -> None:
        settings = deps.get_settings()
        run_backtest_command(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            compare_baseline=compare_baseline,
            compare_memory=compare_memory,
            output=output,
            ensure_ready=deps.ensure_ready,
            run_comparison=deps.run_comparison,
            run_ablation=deps.run_ablation,
            run_walk_forward=deps.run_walk_forward,
        )

