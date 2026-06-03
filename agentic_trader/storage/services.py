from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

import duckdb

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import append_service_event, write_service_state
from agentic_trader.schemas import (
    ServiceEvent,
    ServiceEventLevel,
    ServiceStateSnapshot,
)
from agentic_trader.storage.service_state_records import (
    ServiceStateUpdate,
    resolve_service_state_values,
    service_state_from_row,
    upsert_service_state_row,
    write_service_state_snapshot,
)


def upsert_service_state(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    update: ServiceStateUpdate | None = None,
    **fields: Any,
) -> None:
    if update is None:
        update = ServiceStateUpdate(**fields)
    elif fields:
        raise TypeError("Pass either ServiceStateUpdate or keyword fields, not both.")

    now = datetime.now(timezone.utc).isoformat()
    existing = get_service_state(conn, update.service_name)
    resolved = resolve_service_state_values(
        settings=settings,
        update=update,
        existing=existing,
        now=now,
    )
    upsert_service_state_row(conn, update=update, resolved=resolved, now=now)
    write_service_state_snapshot(
        settings,
        update=update,
        resolved=resolved,
        now=now,
    )


def get_service_state(
    conn: duckdb.DuckDBPyConnection,
    service_name: str = "orchestrator",
) -> ServiceStateSnapshot | None:
    row = conn.execute(
        """
        select service_name, state, runtime_mode, updated_at, started_at, last_heartbeat_at,
               continuous, poll_seconds, cycle_count, symbols_json, interval, lookback, max_cycles,
               current_symbol, last_error, pid, stop_requested, background_mode,
               launch_count, restart_count, last_terminal_state, last_terminal_at,
               stdout_log_path, stderr_log_path, message
        from service_state
        where service_name = ?
        """,
        [service_name],
    ).fetchone()
    if row is None:
        return None
    return service_state_from_row(row)


def request_stop_service(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    service_name: str = "orchestrator",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        update service_state
        set stop_requested = true,
            state = 'stopping',
            updated_at = ?,
            last_heartbeat_at = ?,
            message = 'Stop requested by operator.'
        where service_name = ?
        """,
        [now, now, service_name],
    )
    state = get_service_state(conn, service_name)
    if state is not None:
        write_service_state(settings, state)


def clear_stop_request(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    service_name: str = "orchestrator",
) -> None:
    conn.execute(
        """
        update service_state
        set stop_requested = false
        where service_name = ?
        """,
        [service_name],
    )
    state = get_service_state(conn, service_name)
    if state is not None:
        write_service_state(settings, state)


def insert_service_event(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    *,
    service_name: str = "orchestrator",
    level: ServiceEventLevel,
    event_type: str,
    message: str,
    cycle_count: int | None = None,
    symbol: str | None = None,
) -> str:
    event_id = f"evt-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        insert into service_events (
            event_id, created_at, service_name, level, event_type, message, cycle_count, symbol
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            event_id,
            created_at,
            service_name,
            level,
            event_type,
            message,
            cycle_count,
            symbol,
        ],
    )
    append_service_event(
        settings,
        ServiceEvent(
            event_id=event_id,
            created_at=created_at,
            level=level,
            event_type=event_type,
            message=message,
            cycle_count=cycle_count,
            symbol=symbol,
        ),
    )
    return event_id


def list_service_events(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
    service_name: str = "orchestrator",
) -> list[ServiceEvent]:
    rows = conn.execute(
        """
        select event_id, created_at, level, event_type, message, cycle_count, symbol
        from service_events
        where service_name = ?
        order by created_at desc
        limit ?
        """,
        [service_name, limit],
    ).fetchall()
    events: list[ServiceEvent] = []
    for row in rows:
        events.append(
            ServiceEvent(
                event_id=str(row[0]),
                created_at=str(row[1]),
                level=cast(ServiceEventLevel, str(row[2])),
                event_type=str(row[3]),
                message=str(row[4]),
                cycle_count=int(row[5]) if row[5] is not None else None,
                symbol=str(row[6]) if row[6] is not None else None,
            )
        )
    return events
