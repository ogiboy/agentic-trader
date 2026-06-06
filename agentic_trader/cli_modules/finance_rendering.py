from __future__ import annotations

from collections.abc import Mapping

from rich.panel import Panel
from rich.table import Table

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.common import console
from agentic_trader.json_utils import object_mapping, object_mapping_list


def render_finance_ops(payload: dict[str, object]) -> None:
    checks = payload.get("checks", [])
    accounting = object_mapping(payload.get("accounting"))
    console.print(
        Panel(
            str(payload.get("summary", text.MESSAGE_FINANCE_OPERATIONS_UNAVAILABLE)),
            title=text.TITLE_FINANCE_OPERATIONS,
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
    table = Table(title=text.TITLE_POSITION_PLAN_REPAIR)
    table.add_column(text.LABEL_SYMBOL)
    table.add_column(text.LABEL_STATUS)
    table.add_column(text.LABEL_PROPOSAL)
    table.add_column(text.LABEL_ENTRY)
    table.add_column(text.LABEL_STOP)
    table.add_column(text.LABEL_TAKE)
    table.add_column(text.LABEL_REASON)
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
                    text.MESSAGE_POSITION_PLAN_REPAIR_UNAVAILABLE,
                )
            ),
            title=text.TITLE_POSITION_PLAN_REPAIR,
            border_style="green" if applied else "yellow",
        )
    )
    console.print(table)


def format_optional_float(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "-"


def finance_checks_table(checks: object) -> Table:
    table = Table(title=text.TITLE_FINANCE_OPERATIONS_CHECKS)
    table.add_column(text.LABEL_CHECK)
    table.add_column(text.LABEL_STATUS)
    table.add_column(text.LABEL_BLOCKING)
    table.add_column(text.LABEL_DETAILS)
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
    context = Table(title=text.TITLE_DESK_ACCOUNTING_CONTEXT)
    context.add_column(text.LABEL_FIELD)
    context.add_column(text.LABEL_VALUE)
    context.add_row(text.LABEL_CURRENCY, str(accounting.get("currency", "USD")))
    context.add_row(
        text.LABEL_MARKED_AT,
        str(accounting.get("mark_created_at") or text.MESSAGE_MARK_TIME_UNAVAILABLE),
    )
    context.add_row(text.LABEL_MARK_SOURCE, mark_source)
    context.add_row(text.LABEL_MARK_STATUS, mark_status)
    context.add_row(text.LABEL_FEES, str(cost_model.get("fees", "-")))
    context.add_row(
        text.LABEL_SLIPPAGE,
        (
            "-"
            if cost_model.get("slippage_bps") is None
            else f"{cost_model.get('slippage_bps')} bps"
        ),
    )
    context.add_row(
        text.LABEL_REJECTION_EVIDENCE,
        str(accounting.get("rejection_evidence") or "-"),
    )
    return context


def finance_ledger_table(ledger_categories: object) -> Table | None:
    rows = object_mapping_list(ledger_categories)
    if not rows:
        return None
    ledger_table = Table(title=text.TITLE_FINANCE_LEDGER_CATEGORIES)
    ledger_table.add_column(text.LABEL_CATEGORY)
    ledger_table.add_column(text.LABEL_V1_SOURCE)
    ledger_table.add_column(text.LABEL_PURPOSE)
    for item in rows:
        ledger_table.add_row(
            str(item.get("name", "-")),
            str(item.get("v1_source", "-")),
            str(item.get("purpose", "-")),
        )
    return ledger_table
