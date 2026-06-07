from __future__ import annotations

from collections.abc import Mapping

from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console
from agentic_trader.json_utils import object_mapping, object_mapping_list


def render_finance_ops(payload: dict[str, object]) -> None:
    checks = payload.get("checks", [])
    accounting = object_mapping(payload.get("accounting"))
    console.print(
        Panel(
            str(payload.get("summary", ui_t("message.finance_operations_unavailable"))),
            title=ui_t("title.finance_operations"),
            border_style="green" if payload.get("ready") else "yellow",
        )
    )
    console.print(finance_checks_table(checks))
    console.print(finance_accounting_table(accounting))
    ledger_table = finance_ledger_table(accounting.get("ledger_categories", []))
    if ledger_table is not None:
        console.print(ledger_table)


def render_position_plan_repair(payload: dict[str, object]) -> None:
    applied = bool(payload.get("applied"))
    table = Table(title=ui_t("title.position_plan_repair"))
    table.add_column(ui_t("label.symbol"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.proposal"))
    table.add_column(ui_t("label.entry"))
    table.add_column(ui_t("label.stop"))
    table.add_column(ui_t("label.take"))
    table.add_column(ui_t("label.reason"))
    for item in object_mapping_list(payload.get("repairs", [])):
        table.add_row(
            str(item.get("symbol", "-")),
            str(item.get("status", "-")),
            str(item.get("proposal_id", "-")),
            format_optional_float(item.get("entry_price")),
            format_optional_float(item.get("stop_loss")),
            format_optional_float(item.get("take_profit")),
            str(item.get("reason", "")),
        )
    console.print(
        Panel(
            str(
                payload.get(
                    "summary",
                    ui_t("message.position_plan_repair_unavailable"),
                )
            ),
            title=ui_t("title.position_plan_repair"),
            border_style="green" if applied else "yellow",
        )
    )
    console.print(table)


def format_optional_float(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "-"


def finance_checks_table(checks: object) -> Table:
    table = Table(title=ui_t("title.finance_operations_checks"))
    table.add_column(ui_t("label.check"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.blocking"))
    table.add_column(ui_t("label.details"))
    for check in object_mapping_list(checks):
        table.add_row(
            str(check.get("name", "-")),
            "[green]pass[/green]" if check.get("passed") else "[red]fail[/red]",
            str(check.get("blocking", True)),
            str(check.get("details", "")),
        )
    return table


def finance_accounting_table(accounting: Mapping[str, object]) -> Table:
    cost_model = object_mapping(accounting.get("cost_model"))
    mark_source = str(accounting.get("mark_source") or "-")
    mark_status = str(accounting.get("mark_status") or "-")
    context = Table(title=ui_t("title.desk_accounting_context"))
    context.add_column(ui_t("label.field"))
    context.add_column(ui_t("label.value"))
    context.add_row(ui_t("label.currency"), str(accounting.get("currency", "USD")))
    context.add_row(
        ui_t("label.marked_at"),
        str(accounting.get("mark_created_at") or ui_t("message.mark_time_unavailable")),
    )
    context.add_row(ui_t("label.mark_source"), mark_source)
    context.add_row(ui_t("label.mark_status"), mark_status)
    context.add_row(ui_t("label.fees"), str(cost_model.get("fees", "-")))
    context.add_row(
        ui_t("label.slippage"),
        (
            "-"
            if cost_model.get("slippage_bps") is None
            else f"{cost_model.get('slippage_bps')} bps"
        ),
    )
    context.add_row(
        ui_t("label.rejection_evidence"),
        str(accounting.get("rejection_evidence") or "-"),
    )
    return context


def finance_ledger_table(ledger_categories: object) -> Table | None:
    rows = object_mapping_list(ledger_categories)
    if not rows:
        return None
    ledger_table = Table(title=ui_t("title.finance_ledger_categories"))
    ledger_table.add_column(ui_t("label.category"))
    ledger_table.add_column(ui_t("label.v1_source"))
    ledger_table.add_column(ui_t("label.purpose"))
    for item in rows:
        ledger_table.add_row(
            str(item.get("name", "-")),
            str(item.get("v1_source", "-")),
            str(item.get("purpose", "-")),
        )
    return ledger_table
