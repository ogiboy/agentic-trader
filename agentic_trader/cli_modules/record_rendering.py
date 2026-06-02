from __future__ import annotations

from collections.abc import Callable

from rich.panel import Panel
from rich.table import Table

from agentic_trader import ui_text as text
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
    table = Table(title=text.TITLE_INVESTMENT_PREFERENCES)
    table.add_column(text.LABEL_SETTING)
    table.add_column(text.LABEL_VALUE)
    table.add_row(
        text.LABEL_REGIONS,
        text.UI_LIST_SEPARATOR.join(preferences.regions) or "-",
    )
    table.add_row(
        text.LABEL_EXCHANGES,
        text.UI_LIST_SEPARATOR.join(preferences.exchanges) or "-",
    )
    table.add_row(
        text.LABEL_CURRENCIES,
        text.UI_LIST_SEPARATOR.join(preferences.currencies) or "-",
    )
    table.add_row(
        text.LABEL_SECTORS,
        text.UI_LIST_SEPARATOR.join(preferences.sectors) or "-",
    )
    table.add_row(text.LABEL_RISK_PROFILE, preferences.risk_profile)
    table.add_row(text.LABEL_TRADE_STYLE, preferences.trade_style)
    table.add_row(text.LABEL_BEHAVIOR_PRESET, preferences.behavior_preset)
    table.add_row(text.LABEL_AGENT_PROFILE, preferences.agent_profile)
    table.add_row(text.LABEL_AGENT_TONE, preferences.agent_tone)
    table.add_row(text.LABEL_STRICTNESS, preferences.strictness_preset)
    table.add_row(text.LABEL_INTERVENTION, preferences.intervention_style)
    table.add_row(text.LABEL_NOTES, preferences.notes or "-")
    console.print(table)


def render_trade_journal(entries: list[TradeJournalEntry]) -> None:
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


def render_risk_report(report: DailyRiskReport) -> None:
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


def render_unavailable_trade_context(
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


def render_trade_context(
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
