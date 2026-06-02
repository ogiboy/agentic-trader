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
from agentic_trader.ui_text import (
    LABEL_CONTINUOUS,
    LABEL_CURRENT_SYMBOL,
    LABEL_CYCLE_COUNT,
    LABEL_HEARTBEAT,
    LABEL_HEARTBEAT_AGE,
    LABEL_INTERVAL,
    LABEL_KEY,
    LABEL_LAST_RECORDED_ERROR,
    LABEL_LAST_RECORDED_MESSAGE,
    LABEL_LAST_RECORDED_STATE,
    LABEL_LIVE_PROCESS,
    LABEL_LOOKBACK,
    LABEL_MAX_CYCLES,
    LABEL_MODE,
    LABEL_NO,
    LABEL_PID,
    LABEL_POLL_SECONDS,
    LABEL_RUNTIME,
    LABEL_SERVICE,
    LABEL_STARTED,
    LABEL_STATUS_NOTE,
    LABEL_STOP_REQUESTED,
    LABEL_SYMBOLS,
    LABEL_UPDATED,
    LABEL_VALUE,
    LABEL_YES,
    MESSAGE_NO_RUNTIME_STATE,
    TITLE_SERVICE_STATUS,
    UI_LIST_SEPARATOR,
)


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
                MESSAGE_NO_RUNTIME_STATE,
                title=TITLE_SERVICE_STATUS,
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=TITLE_SERVICE_STATUS)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_SERVICE, snapshot.service_name)
    table.add_row(LABEL_MODE, snapshot.runtime_mode)
    table.add_row(LABEL_RUNTIME, view.runtime_state)
    table.add_row(LABEL_LIVE_PROCESS, LABEL_YES if view.live_process else LABEL_NO)
    table.add_row(LABEL_LAST_RECORDED_STATE, view.last_recorded_state or "-")
    table.add_row(LABEL_UPDATED, snapshot.updated_at)
    table.add_row(LABEL_STARTED, snapshot.started_at or "-")
    table.add_row(LABEL_HEARTBEAT, snapshot.last_heartbeat_at or "-")
    table.add_row(
        LABEL_HEARTBEAT_AGE,
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(LABEL_CONTINUOUS, str(snapshot.continuous))
    table.add_row(
        LABEL_POLL_SECONDS,
        str(snapshot.poll_seconds) if snapshot.poll_seconds is not None else "-",
    )
    table.add_row(LABEL_CYCLE_COUNT, str(snapshot.cycle_count))
    table.add_row(LABEL_SYMBOLS, UI_LIST_SEPARATOR.join(snapshot.symbols) or "-")
    table.add_row(LABEL_INTERVAL, snapshot.interval or "-")
    table.add_row(LABEL_LOOKBACK, snapshot.lookback or "-")
    table.add_row(
        LABEL_MAX_CYCLES,
        str(snapshot.max_cycles) if snapshot.max_cycles is not None else "-",
    )
    table.add_row(LABEL_CURRENT_SYMBOL, snapshot.current_symbol or "-")
    table.add_row(LABEL_PID, str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row(LABEL_STOP_REQUESTED, str(snapshot.stop_requested))
    table.add_row(LABEL_STATUS_NOTE, view.status_message)
    table.add_row(LABEL_LAST_RECORDED_MESSAGE, snapshot.message or "-")
    table.add_row(LABEL_LAST_RECORDED_ERROR, snapshot.last_error or "-")
    console.print(table)
