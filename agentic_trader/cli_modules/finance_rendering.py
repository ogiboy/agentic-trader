from __future__ import annotations

from collections.abc import Mapping

from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console
from agentic_trader.json_utils import object_mapping, object_mapping_list


def render_finance_ops(payload: dict[str, object]) -> None:
    """
    Render the finance operations summary and related tables to the console.
    
    Prints a titled Panel showing `payload["summary"]` (falls back to a localized unavailable message) with a green border when `payload["ready"]` is truthy, otherwise a yellow border. Then prints the finance checks table, the accounting context table, and—if present—the ledger categories table.
    
    Parameters:
    	payload (dict[str, object]): Input mapping that may contain:
    		- checks: Iterable of check objects (defaults to []).
    		- accounting: Mapping (or object convertible via `object_mapping`) with accounting details and optional `ledger_categories`.
    		- summary: Summary string to display in the Panel.
    		- ready: Truthy value to indicate successful readiness (controls Panel border color).
    """
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
    """
    Render a position-plan repair summary panel and a detailed repairs table to the console.
    
    Renders a titled summary Panel whose border is green when `payload["applied"]` is truthy and yellow otherwise, followed by a table of repairs with columns: symbol, status, proposal, entry, stop, take, and reason. Numeric price fields are formatted with `format_optional_float`; the summary text falls back to a localized "unavailable" message when `payload["summary"]` is not provided.
    
    Parameters:
    	payload (dict[str, object]): Payload containing:
    		- "applied": optional flag indicating whether repairs were applied (truthy => green border).
    		- "repairs": optional iterable of repair objects to display; each object may include "symbol", "status", "proposal_id", "entry_price", "stop_loss", "take_profit", and "reason".
    		- "summary": optional summary text to show in the Panel; when absent a localized fallback message is used.
    """
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
    """
    Builds a rich.Table summarizing finance operation checks.
    
    Parameters:
        checks (object): Iterable or mapping of check records. Each record may contain:
            - "name": display name (defaults to "-")
            - "passed": truthy value to render a green "pass", otherwise a red "fail"
            - "blocking": shown as-is (defaults to True)
            - "details": additional information (defaults to "")
    
    Returns:
        Table: A rich.Table titled with the localized finance checks title and columns
        for check, status, blocking, and details; one row is added per input record.
    """
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
    """
    Builds a two-column table summarizing accounting context for finance operations.
    
    Parameters:
    	accounting (Mapping[str, object]): Mapping with accounting details. Expected keys include
    		- "currency": currency code (defaults to "USD")
    		- "mark_created_at": timestamp or None
    		- "mark_source": source identifier
    		- "mark_status": status string
    		- "cost_model": mapping with "fees" and optional "slippage_bps"
    		- "rejection_evidence": any rejection details
    
    Returns:
    	Table: A rich Table with "Field" and "Value" columns containing rows for currency, marked at time,
    	mark source, mark status, fees, slippage (formatted as "<n> bps" or "-" if unavailable),
    	and rejection evidence.
    """
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
    """
    Builds a rich Table of ledger categories.
    
    Parameters:
        ledger_categories (object): Data to be mapped into ledger category rows (accepted formats handled by object_mapping_list).
    
    Returns:
        Table | None: A `rich.Table` with columns `category`, `v1_source`, and `purpose` containing one row per mapped category, or `None` if no categories are present.
    """
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
