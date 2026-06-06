from __future__ import annotations

from collections.abc import Callable

from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
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
    table = Table(title=ui_t("title.investment_preferences"))
    table.add_column(ui_t("label.setting"))
    table.add_column(ui_t("label.value"))
    table.add_row(
        ui_t("label.regions"),
        ui_t("list.separator").join(preferences.regions) or "-",
    )
    table.add_row(
        ui_t("label.exchanges"),
        ui_t("list.separator").join(preferences.exchanges) or "-",
    )
    table.add_row(
        ui_t("label.currencies"),
        ui_t("list.separator").join(preferences.currencies) or "-",
    )
    table.add_row(
        ui_t("label.sectors"),
        ui_t("list.separator").join(preferences.sectors) or "-",
    )
    table.add_row(ui_t("label.risk_profile"), preferences.risk_profile)
    table.add_row(ui_t("label.trade_style"), preferences.trade_style)
    table.add_row(ui_t("label.behavior_preset"), preferences.behavior_preset)
    table.add_row(ui_t("label.agent_profile"), preferences.agent_profile)
    table.add_row(ui_t("label.agent_tone"), preferences.agent_tone)
    table.add_row(ui_t("label.strictness"), preferences.strictness_preset)
    table.add_row(ui_t("label.intervention"), preferences.intervention_style)
    table.add_row(ui_t("label.notes"), preferences.notes or "-")
    console.print(table)


def render_trade_journal(entries: list[TradeJournalEntry]) -> None:
    if not entries:
        console.print(
            Panel(
                ui_t("message.no_trade_journal_entries"),
                title=ui_t("title.trade_journal"),
                border_style="yellow",
            )
        )
        return

    table = Table(title=ui_t("title.trade_journal"))
    table.add_column(ui_t("label.opened"))
    table.add_column(ui_t("label.symbol"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.side"))
    table.add_column(ui_t("label.entry"))
    table.add_column(ui_t("label.exit"))
    table.add_column(ui_t("label.pnl"))
    table.add_column(ui_t("label.notes"))
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
    table = Table(title=ui_t("title.daily_risk_report") + " / " + report.report_date)
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.generated"), report.generated_at)
    table.add_row(ui_t("label.cash"), f"{report.cash:.2f}")
    table.add_row(ui_t("label.market_value"), f"{report.market_value:.2f}")
    table.add_row(ui_t("label.equity"), f"{report.equity:.2f}")
    table.add_row(ui_t("label.realized_pnl"), f"{report.realized_pnl:.2f}")
    table.add_row(ui_t("label.unrealized_pnl"), f"{report.unrealized_pnl:.2f}")
    table.add_row(ui_t("label.open_positions"), str(report.open_positions))
    table.add_row(ui_t("label.fills_today"), str(report.fills_today))
    table.add_row(ui_t("label.marks_recorded"), str(report.marks_recorded))
    table.add_row(ui_t("label.daily_realized_pnl"), f"{report.daily_realized_pnl:.2f}")
    table.add_row(ui_t("label.gross_exposure"), f"{report.gross_exposure_pct:.2%}")
    table.add_row(ui_t("label.largest_position"), f"{report.largest_position_pct:.2%}")
    table.add_row(
        ui_t("label.drawdown_from_peak"), f"{report.drawdown_from_peak_pct:.2%}"
    )
    console.print(table)
    if report.warnings:
        console.print(
            Panel(
                "\n".join(f"- {warning}" for warning in report.warnings),
                title=ui_t("title.risk_warnings"),
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                ui_t("message.no_elevated_portfolio_risk_warnings"),
                title=ui_t("title.risk_warnings"),
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
                title=ui_t("label.observer_mode"),
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
                ui_t("message.trade_context_temporarily_unavailable").format(
                    error=payload["error"]
                ),
                title=ui_t("label.observer_mode"),
                border_style="yellow",
            )
        )
        return True
    if record is None:
        console.print(
            Panel(
                ui_t("message.no_trade_context"),
                title=ui_t("title.trade_context"),
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
        title=ui_t("title.trade_context_detail").format(trade_id=record.trade_id)
    )
    summary.add_column(ui_t("label.field"))
    summary.add_column(ui_t("label.value"))
    summary.add_row(ui_t("label.created"), record.created_at)
    summary.add_row(ui_t("label.run_id"), value_or_dash(record.run_id))
    summary.add_row(ui_t("label.symbol"), record.symbol)
    summary.add_row(ui_t("label.consensus"), record.consensus.alignment_level)
    summary.add_row(ui_t("label.manager_rationale"), record.manager_rationale)
    summary.add_row(ui_t("label.execution_rationale"), record.execution_rationale)
    summary.add_row(
        ui_t("label.execution_backend"), value_or_dash(record.execution_backend)
    )
    summary.add_row(
        ui_t("label.execution_adapter"), value_or_dash(record.execution_adapter)
    )
    summary.add_row(
        ui_t("label.execution_outcome"), value_or_dash(record.execution_outcome_status)
    )
    summary.add_row(
        ui_t("label.rejection_reason"), value_or_dash(record.execution_rejection_reason)
    )
    summary.add_row(ui_t("label.review_summary"), record.review_summary)
    console.print(summary)

    routed_models = Table(title=ui_t("title.routed_models"))
    routed_models.add_column(ui_t("label.role"))
    routed_models.add_column(ui_t("label.model"))
    if not record.routed_models:
        routed_models.add_row("-", "-")
    else:
        for role, model_name in sorted(record.routed_models.items()):
            routed_models.add_row(role, model_name)
    console.print(routed_models)

    context_lines = [
        f"{ui_t('label.retrieved_memory_roles')}: {join_or_dash(sorted(record.retrieved_memory_summary))}",
        f"{ui_t('label.tool_output_roles')}: {join_or_dash(sorted(record.tool_outputs))}",
        f"{ui_t('label.shared_bus_roles')}: {join_or_dash(sorted(record.shared_memory_summary))}",
        f"{ui_t('label.warnings')}: {join_or_dash(record.review_warnings)}",
    ]
    console.print(
        Panel(
            "\n".join(context_lines),
            title=ui_t("title.context_summary"),
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(canonical_analysis_lines(record.canonical_snapshot)),
            title=ui_t("title.canonical_analysis"),
            border_style="blue",
        )
    )
