"""Service and runtime rendering helpers for the CLI facade."""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.runtime_status import build_runtime_status_view
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import OrderRow
from agentic_trader.ui_text import t as ui_t


def read_text_tail(path: Path | None, *, limit: int = 12) -> list[str]:
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [redact_sensitive_text(line, max_length=1_000) for line in lines[-limit:]]


def format_latest_order(order: OrderRow | None) -> str:
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


def render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(body, title=status, border_style=border_style)


def render_service_state(state: ServiceStateSnapshot | None) -> None:
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                ui_t("message.no_runtime_state"),
                title=ui_t("title.service_status"),
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=ui_t("title.service_status"))
    table.add_column(ui_t("label.key"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.service"), snapshot.service_name)
    table.add_row(ui_t("label.mode"), snapshot.runtime_mode)
    table.add_row(ui_t("label.runtime"), view.runtime_state)
    table.add_row(
        ui_t("label.live_process"),
        ui_t("label.yes") if view.live_process else ui_t("label.no"),
    )
    table.add_row(ui_t("label.last_recorded_state"), view.last_recorded_state or "-")
    table.add_row(ui_t("label.updated"), snapshot.updated_at)
    table.add_row(ui_t("label.started"), snapshot.started_at or "-")
    table.add_row(ui_t("label.heartbeat"), snapshot.last_heartbeat_at or "-")
    table.add_row(
        ui_t("label.heartbeat_age"),
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(ui_t("label.continuous"), str(snapshot.continuous))
    table.add_row(
        ui_t("label.poll_seconds"),
        str(snapshot.poll_seconds) if snapshot.poll_seconds is not None else "-",
    )
    table.add_row(ui_t("label.cycle_count"), str(snapshot.cycle_count))
    table.add_row(
        ui_t("label.symbols"), ui_t("list.separator").join(snapshot.symbols) or "-"
    )
    table.add_row(ui_t("label.interval"), snapshot.interval or "-")
    table.add_row(ui_t("label.lookback"), snapshot.lookback or "-")
    table.add_row(
        ui_t("label.max_cycles"),
        str(snapshot.max_cycles) if snapshot.max_cycles is not None else "-",
    )
    table.add_row(ui_t("label.current_symbol"), snapshot.current_symbol or "-")
    table.add_row(
        ui_t("label.pid"), str(snapshot.pid) if snapshot.pid is not None else "-"
    )
    table.add_row(ui_t("label.stop_requested"), str(snapshot.stop_requested))
    table.add_row(ui_t("label.status_note"), view.status_message)
    table.add_row(ui_t("label.last_recorded_message"), snapshot.message or "-")
    table.add_row(ui_t("label.last_recorded_error"), snapshot.last_error or "-")
    console.print(table)
