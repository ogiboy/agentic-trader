from __future__ import annotations

from collections.abc import Callable

from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import (
    LABEL_AGENT_PROFILE,
    LABEL_AGENT_TONE,
    LABEL_BEHAVIOR_PRESET,
    LABEL_CASH,
    LABEL_CONSENSUS,
    LABEL_CREATED,
    LABEL_CURRENCIES,
    LABEL_DAILY_REALIZED_PNL,
    LABEL_DRAWDOWN_FROM_PEAK,
    LABEL_ENTRY,
    LABEL_EQUITY,
    LABEL_EXCHANGES,
    LABEL_EXECUTION_ADAPTER,
    LABEL_EXECUTION_BACKEND,
    LABEL_EXECUTION_OUTCOME,
    LABEL_EXECUTION_RATIONALE,
    LABEL_EXIT,
    LABEL_FIELD,
    LABEL_FILLS_TODAY,
    LABEL_GENERATED,
    LABEL_GROSS_EXPOSURE,
    LABEL_INTERVENTION,
    LABEL_LARGEST_POSITION,
    LABEL_MANAGER_RATIONALE,
    LABEL_MARKET_VALUE,
    LABEL_MARKS_RECORDED,
    LABEL_MODEL,
    LABEL_NOTES,
    LABEL_OBSERVER_MODE,
    LABEL_OPENED,
    LABEL_OPEN_POSITIONS,
    LABEL_PNL,
    LABEL_REALIZED_PNL,
    LABEL_REGIONS,
    LABEL_REJECTION_REASON,
    LABEL_RETRIEVED_MEMORY_ROLES,
    LABEL_REVIEW_SUMMARY,
    LABEL_RISK_PROFILE,
    LABEL_ROLE,
    LABEL_RUN_ID,
    LABEL_SECTORS,
    LABEL_SETTING,
    LABEL_SHARED_BUS_ROLES,
    LABEL_SIDE,
    LABEL_STATUS,
    LABEL_STRICTNESS,
    LABEL_SYMBOL,
    LABEL_TOOL_OUTPUT_ROLES,
    LABEL_TRADE_STYLE,
    LABEL_UNREALIZED_PNL,
    LABEL_VALUE,
    LABEL_WARNINGS,
    MESSAGE_NO_ELEVATED_PORTFOLIO_RISK_WARNINGS,
    MESSAGE_NO_TRADE_CONTEXT,
    MESSAGE_NO_TRADE_JOURNAL_ENTRIES,
    MESSAGE_TRADE_CONTEXT_TEMPORARILY_UNAVAILABLE,
    TITLE_CANONICAL_ANALYSIS,
    TITLE_CONTEXT_SUMMARY,
    TITLE_DAILY_RISK_REPORT,
    TITLE_INVESTMENT_PREFERENCES,
    TITLE_RISK_WARNINGS,
    TITLE_ROUTED_MODELS,
    TITLE_TRADE_CONTEXT,
    TITLE_TRADE_CONTEXT_DETAIL,
    TITLE_TRADE_JOURNAL,
    UI_LIST_SEPARATOR,
)
from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.run_reports import join_or_dash, value_or_dash
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
    DailyRiskReport,
    InvestmentPreferences,
    RunRecord,
    TradeContextRecord,
    TradeJournalEntry,
)


def render_preferences(preferences: InvestmentPreferences) -> None:
    table = Table(title=TITLE_INVESTMENT_PREFERENCES)
    table.add_column(LABEL_SETTING)
    table.add_column(LABEL_VALUE)
    table.add_row(
        LABEL_REGIONS,
        UI_LIST_SEPARATOR.join(preferences.regions) or "-",
    )
    table.add_row(
        LABEL_EXCHANGES,
        UI_LIST_SEPARATOR.join(preferences.exchanges) or "-",
    )
    table.add_row(
        LABEL_CURRENCIES,
        UI_LIST_SEPARATOR.join(preferences.currencies) or "-",
    )
    table.add_row(
        LABEL_SECTORS,
        UI_LIST_SEPARATOR.join(preferences.sectors) or "-",
    )
    table.add_row(LABEL_RISK_PROFILE, preferences.risk_profile)
    table.add_row(LABEL_TRADE_STYLE, preferences.trade_style)
    table.add_row(LABEL_BEHAVIOR_PRESET, preferences.behavior_preset)
    table.add_row(LABEL_AGENT_PROFILE, preferences.agent_profile)
    table.add_row(LABEL_AGENT_TONE, preferences.agent_tone)
    table.add_row(LABEL_STRICTNESS, preferences.strictness_preset)
    table.add_row(LABEL_INTERVENTION, preferences.intervention_style)
    table.add_row(LABEL_NOTES, preferences.notes or "-")
    console.print(table)


def render_trade_journal(entries: list[TradeJournalEntry]) -> None:
    if not entries:
        console.print(
            Panel(
                MESSAGE_NO_TRADE_JOURNAL_ENTRIES,
                title=TITLE_TRADE_JOURNAL,
                border_style="yellow",
            )
        )
        return

    table = Table(title=TITLE_TRADE_JOURNAL)
    table.add_column(LABEL_OPENED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_SIDE)
    table.add_column(LABEL_ENTRY)
    table.add_column(LABEL_EXIT)
    table.add_column(LABEL_PNL)
    table.add_column(LABEL_NOTES)
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


def render_risk_report(report: DailyRiskReport) -> None:
    table = Table(title=TITLE_DAILY_RISK_REPORT + " / " + report.report_date)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_GENERATED, report.generated_at)
    table.add_row(LABEL_CASH, f"{report.cash:.2f}")
    table.add_row(LABEL_MARKET_VALUE, f"{report.market_value:.2f}")
    table.add_row(LABEL_EQUITY, f"{report.equity:.2f}")
    table.add_row(LABEL_REALIZED_PNL, f"{report.realized_pnl:.2f}")
    table.add_row(LABEL_UNREALIZED_PNL, f"{report.unrealized_pnl:.2f}")
    table.add_row(LABEL_OPEN_POSITIONS, str(report.open_positions))
    table.add_row(LABEL_FILLS_TODAY, str(report.fills_today))
    table.add_row(LABEL_MARKS_RECORDED, str(report.marks_recorded))
    table.add_row(LABEL_DAILY_REALIZED_PNL, f"{report.daily_realized_pnl:.2f}")
    table.add_row(LABEL_GROSS_EXPOSURE, f"{report.gross_exposure_pct:.2%}")
    table.add_row(LABEL_LARGEST_POSITION, f"{report.largest_position_pct:.2%}")
    table.add_row(LABEL_DRAWDOWN_FROM_PEAK, f"{report.drawdown_from_peak_pct:.2%}")
    console.print(table)
    if report.warnings:
        console.print(
            Panel(
                "\n".join(f"- {warning}" for warning in report.warnings),
                title=TITLE_RISK_WARNINGS,
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                MESSAGE_NO_ELEVATED_PORTFOLIO_RISK_WARNINGS,
                title=TITLE_RISK_WARNINGS,
                border_style="green",
            )
        )


def render_unavailable_run_record(
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
                title=LABEL_OBSERVER_MODE,
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


def render_unavailable_trade_context(
    payload: dict[str, object], record: TradeContextRecord | None
) -> bool:
    if not payload["available"]:
        console.print(
            Panel(
                MESSAGE_TRADE_CONTEXT_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        return True
    if record is None:
        console.print(
            Panel(
                MESSAGE_NO_TRADE_CONTEXT,
                title=TITLE_TRADE_CONTEXT,
                border_style="yellow",
            )
        )
        return True
    return False


def render_trade_context(
    record: TradeContextRecord,
    *,
    canonical_analysis_lines: Callable[[CanonicalAnalysisSnapshot | None], list[str]],
) -> None:
    summary = Table(
        title=TITLE_TRADE_CONTEXT_DETAIL.format(trade_id=record.trade_id)
    )
    summary.add_column(LABEL_FIELD)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_CREATED, record.created_at)
    summary.add_row(LABEL_RUN_ID, value_or_dash(record.run_id))
    summary.add_row(LABEL_SYMBOL, record.symbol)
    summary.add_row(LABEL_CONSENSUS, record.consensus.alignment_level)
    summary.add_row(LABEL_MANAGER_RATIONALE, record.manager_rationale)
    summary.add_row(LABEL_EXECUTION_RATIONALE, record.execution_rationale)
    summary.add_row(
        LABEL_EXECUTION_BACKEND, value_or_dash(record.execution_backend)
    )
    summary.add_row(
        LABEL_EXECUTION_ADAPTER, value_or_dash(record.execution_adapter)
    )
    summary.add_row(
        LABEL_EXECUTION_OUTCOME, value_or_dash(record.execution_outcome_status)
    )
    summary.add_row(
        LABEL_REJECTION_REASON, value_or_dash(record.execution_rejection_reason)
    )
    summary.add_row(LABEL_REVIEW_SUMMARY, record.review_summary)
    console.print(summary)

    routed_models = Table(title=TITLE_ROUTED_MODELS)
    routed_models.add_column(LABEL_ROLE)
    routed_models.add_column(LABEL_MODEL)
    if not record.routed_models:
        routed_models.add_row("-", "-")
    else:
        for role, model_name in sorted(record.routed_models.items()):
            routed_models.add_row(role, model_name)
    console.print(routed_models)

    context_lines = [
        f"{LABEL_RETRIEVED_MEMORY_ROLES}: {join_or_dash(sorted(record.retrieved_memory_summary))}",
        f"{LABEL_TOOL_OUTPUT_ROLES}: {join_or_dash(sorted(record.tool_outputs))}",
        f"{LABEL_SHARED_BUS_ROLES}: {join_or_dash(sorted(record.shared_memory_summary))}",
        f"{LABEL_WARNINGS}: {join_or_dash(record.review_warnings)}",
    ]
    console.print(
        Panel(
            "\n".join(context_lines),
            title=TITLE_CONTEXT_SUMMARY,
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(canonical_analysis_lines(record.canonical_snapshot)),
            title=TITLE_CANONICAL_ANALYSIS,
            border_style="blue",
        )
    )
