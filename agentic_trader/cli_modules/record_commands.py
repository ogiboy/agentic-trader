from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel

from agentic_trader.ui_text import (
    HELP_BACKTEST_COMPARE_BASELINE,
    HELP_BACKTEST_COMPARE_MEMORY,
    HELP_BACKTEST_OUTPUT,
    HELP_BACKTEST_WARMUP_BARS,
    HELP_EXPORT_REPORT_OUTPUT,
    HELP_EXPORT_REPORT_RUN_ID,
    HELP_INTERVAL,
    HELP_JSON,
    HELP_LOOKBACK,
    HELP_RISK_REPORT_DATE,
    HELP_RUN_ID,
    HELP_RUN_REPLAY_ID,
    HELP_SYMBOL,
    HELP_TRADE_CONTEXT_ID,
    HELP_TRADE_JOURNAL_LIMIT,
    LABEL_OBSERVER_MODE,
    MESSAGE_NO_PERSISTED_RUNS_EXPORT,
    MESSAGE_NO_PERSISTED_RUNS_REPLAY,
    MESSAGE_NO_PERSISTED_RUNS_REVIEW,
    MESSAGE_NO_PERSISTED_RUNS_TRACE,
    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE,
    MESSAGE_RISK_REPORT_TEMPORARILY_UNAVAILABLE,
    MESSAGE_RUN_REPLAY_TEMPORARILY_UNAVAILABLE,
    MESSAGE_RUN_REPORT_WRITTEN,
    MESSAGE_RUN_REVIEW_TEMPORARILY_UNAVAILABLE,
    MESSAGE_RUN_TRACE_TEMPORARILY_UNAVAILABLE,
    MESSAGE_TRADE_JOURNAL_TEMPORARILY_UNAVAILABLE,
    TITLE_EXPORTED,
    TITLE_EXPORT_BLOCKED,
    TITLE_RUN_REPLAY,
    TITLE_RUN_REVIEW,
    TITLE_TRACE,
)
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
from agentic_trader.cli_modules.record_rendering import (
    render_preferences,
    render_risk_report,
    render_trade_context,
    render_trade_journal,
    render_unavailable_run_record,
    render_unavailable_trade_context,
)
from agentic_trader.cli_modules.run_reports import (
    render_run_markdown,
    render_run_replay,
    render_run_review,
    render_run_trace,
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
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        render_preferences(preferences)


def _register_journal_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("journal")
    def journal(
        limit: int = typer.Option(
            20, min=1, max=200, help=HELP_TRADE_JOURNAL_LIMIT
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                    MESSAGE_TRADE_JOURNAL_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        render_trade_journal(entries)


def _register_risk_report_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("risk-report")
    def risk_report(
        report_date: str | None = typer.Option(None, help=HELP_RISK_REPORT_DATE),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                    MESSAGE_RISK_REPORT_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        render_risk_report(report)


def _register_run_review_commands(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("review-run")
    def review_run(
        run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.run_record_payload(settings, run_id=run_id)
        record = _run_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if render_unavailable_run_record(
            payload,
            record,
            unavailable_message=MESSAGE_RUN_REVIEW_TEMPORARILY_UNAVAILABLE,
            empty_message=MESSAGE_NO_PERSISTED_RUNS_REVIEW,
            empty_title=TITLE_RUN_REVIEW,
        ):
            raise typer.Exit(code=0)
        assert record is not None
        render_run_review(record)

    @app.command("trace-run")
    def trace_run(
        run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.run_record_payload(settings, run_id=run_id)
        record = _run_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if render_unavailable_run_record(
            payload,
            record,
            unavailable_message=MESSAGE_RUN_TRACE_TEMPORARILY_UNAVAILABLE,
            empty_message=MESSAGE_NO_PERSISTED_RUNS_TRACE,
            empty_title=TITLE_TRACE,
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


def _register_trade_context_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("trade-context")
    def trade_context(
        trade_id: str | None = typer.Option(None, help=HELP_TRADE_CONTEXT_ID),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.trade_context_payload(settings, trade_id=trade_id)
        record = _trade_context_record_from_payload(payload)
        if json_output:
            deps.emit_json(payload)
            return
        if render_unavailable_trade_context(payload, record):
            raise typer.Exit(code=0)
        assert record is not None
        render_trade_context(
            record, canonical_analysis_lines=deps.canonical_analysis_lines
        )


def _trade_context_record_from_payload(
    payload: dict[str, object],
) -> TradeContextRecord | None:
    if payload["record"] is None:
        return None
    return TradeContextRecord.model_validate(payload["record"])


def _register_replay_export_commands(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("replay-run")
    def replay_run(
        run_id: str | None = typer.Option(None, help=HELP_RUN_REPLAY_ID),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
                    MESSAGE_RUN_REPLAY_TEMPORARILY_UNAVAILABLE.format(
                        error=payload["error"]
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        if replay is None:
            console.print(
                Panel(
                    MESSAGE_NO_PERSISTED_RUNS_REPLAY,
                    title=TITLE_RUN_REPLAY,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        render_run_replay(replay)

    @app.command("export-report")
    def export_report(
        output: str = typer.Option(..., help=HELP_EXPORT_REPORT_OUTPUT),
        run_id: str | None = typer.Option(None, help=HELP_EXPORT_REPORT_RUN_ID),
    ) -> None:
        settings = deps.get_settings()
        db = deps.open_db(settings, read_only=True)
        record = db.get_run(run_id) if run_id is not None else db.latest_run()
        if record is None:
            console.print(
                Panel(
                    MESSAGE_NO_PERSISTED_RUNS_EXPORT,
                    title=TITLE_EXPORT_BLOCKED,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1)
        rendered = render_run_markdown(record)
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        console.print(
            Panel(
                MESSAGE_RUN_REPORT_WRITTEN.format(output=output),
                title=TITLE_EXPORTED,
                border_style="green",
            )
        )


def _register_backtest_command(app: typer.Typer, deps: RecordCommandDeps) -> None:
    @app.command("backtest")
    def backtest(
        symbol: str = typer.Option(..., help=HELP_SYMBOL),
        interval: str = typer.Option("1d", help=HELP_INTERVAL),
        lookback: str = typer.Option("2y", help=HELP_LOOKBACK),
        warmup_bars: int = typer.Option(
            120, min=60, help=HELP_BACKTEST_WARMUP_BARS
        ),
        compare_baseline: bool = typer.Option(
            False, help=HELP_BACKTEST_COMPARE_BASELINE
        ),
        compare_memory: bool = typer.Option(
            False, help=HELP_BACKTEST_COMPARE_MEMORY
        ),
        output: str | None = typer.Option(None, help=HELP_BACKTEST_OUTPUT),
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
