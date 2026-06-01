import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast, get_args
from uuid import uuid4

import duckdb

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import append_service_event, write_service_state
from agentic_trader.schemas import (
    RuntimeMode,
    ServiceEvent,
    ServiceEventLevel,
    ServiceState,
    ServiceStateSnapshot,
)

TERMINAL_SERVICE_STATES: set[ServiceState] = {
    "stopped",
    "completed",
    "failed",
    "blocked",
}
SERVICE_STATE_VALUES = set(get_args(ServiceState))
RUNTIME_MODE_VALUES = set(get_args(RuntimeMode))


@dataclass
class ServiceStateUpdate:
    state: str
    continuous: bool
    poll_seconds: int | None
    cycle_count: int
    message: str
    service_name: str = "orchestrator"
    runtime_mode: RuntimeMode | None = None
    symbols: list[str] | None = None
    interval: str | None = None
    lookback: str | None = None
    max_cycles: int | None = None
    current_symbol: str | None = None
    last_error: str | None = None
    pid: int | None = None
    clear_pid: bool = False
    stop_requested: bool | None = None
    background_mode: bool | None = None
    launch_count: int | None = None
    restart_count: int | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None


@dataclass
class _ResolvedServiceStateValues:
    runtime_mode: RuntimeMode
    started_at: str
    pid: int | None
    stop_requested: bool
    symbols: list[str]
    interval: str | None
    lookback: str | None
    max_cycles: int | None
    background_mode: bool
    launch_count: int
    restart_count: int
    last_terminal_state: str | None
    last_terminal_at: str | None
    stdout_log_path: str | None
    stderr_log_path: str | None


def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def _int_or_none(value: Any) -> int | None:
    return int(value) if value is not None else None


def _bool_or_default(value: Any, default: bool) -> bool:
    return bool(value) if value is not None else default


def _resolve_value[T](new_value: T | None, existing_value: T | None, default: T) -> T:
    if new_value is not None:
        return new_value
    if existing_value is not None:
        return existing_value
    return default


def _resolve_optional_value[T](
    new_value: T | None, existing_value: T | None
) -> T | None:
    return new_value if new_value is not None else existing_value


def _existing_value(
    existing: ServiceStateSnapshot | None,
    attr: str,
) -> Any | None:
    if existing is None:
        return None
    return getattr(existing, attr)


def _resolve_started_at(
    *,
    update: ServiceStateUpdate,
    existing: ServiceStateSnapshot | None,
    now: str,
) -> str:
    started_at = _existing_value(existing, "started_at")
    if update.state == "starting" or started_at is None:
        return now
    return started_at


def _resolve_service_pid(
    update: ServiceStateUpdate,
    existing: ServiceStateSnapshot | None,
) -> int | None:
    if update.clear_pid:
        return None
    return _resolve_optional_value(update.pid, _existing_value(existing, "pid"))


def _resolve_symbols(
    symbols: list[str] | None,
    existing: ServiceStateSnapshot | None,
) -> list[str]:
    if symbols is not None:
        return list(symbols)
    if existing is not None:
        return existing.symbols
    return []


def _resolve_terminal_state(
    *,
    state: str,
    existing: ServiceStateSnapshot | None,
    now: str,
) -> tuple[str | None, str | None]:
    if state in TERMINAL_SERVICE_STATES:
        return state, now
    if existing is None:
        return None, None
    return existing.last_terminal_state, existing.last_terminal_at


def _coerce_service_state(value: Any) -> ServiceState:
    state = str(value)
    return cast(ServiceState, state) if state in SERVICE_STATE_VALUES else "stopped"


def _coerce_runtime_mode(value: Any) -> RuntimeMode:
    mode = str(value)
    return cast(RuntimeMode, mode) if mode in RUNTIME_MODE_VALUES else "operation"


def _decode_symbols(value: Any) -> list[str]:
    return json.loads(str(value)) if value is not None else []


def _int_or_default(value: Any, default: int) -> int:
    return int(value) if value is not None else default


def _service_state_from_row(row: tuple[Any, ...]) -> ServiceStateSnapshot:
    return ServiceStateSnapshot(
        service_name=str(row[0]),
        state=_coerce_service_state(row[1]),
        runtime_mode=_coerce_runtime_mode(row[2]),
        updated_at=str(row[3]),
        started_at=_str_or_none(row[4]),
        last_heartbeat_at=_str_or_none(row[5]),
        continuous=bool(row[6]),
        poll_seconds=_int_or_none(row[7]),
        cycle_count=int(row[8]),
        symbols=_decode_symbols(row[9]),
        interval=_str_or_none(row[10]),
        lookback=_str_or_none(row[11]),
        max_cycles=_int_or_none(row[12]),
        current_symbol=_str_or_none(row[13]),
        last_error=_str_or_none(row[14]),
        pid=_int_or_none(row[15]),
        stop_requested=_bool_or_default(row[16], False),
        background_mode=_bool_or_default(row[17], False),
        launch_count=_int_or_default(row[18], 0),
        restart_count=_int_or_default(row[19], 0),
        last_terminal_state=_str_or_none(row[20]),
        last_terminal_at=_str_or_none(row[21]),
        stdout_log_path=_str_or_none(row[22]),
        stderr_log_path=_str_or_none(row[23]),
        message=str(row[24]),
    )


def _resolve_service_state_values(
    *,
    settings: Settings,
    update: ServiceStateUpdate,
    existing: ServiceStateSnapshot | None,
    now: str,
) -> _ResolvedServiceStateValues:
    resolved_runtime_mode = cast(
        RuntimeMode,
        _resolve_value(
            update.runtime_mode,
            cast(RuntimeMode | None, _existing_value(existing, "runtime_mode")),
            settings.runtime_mode,
        ),
    )
    last_terminal_state, last_terminal_at = _resolve_terminal_state(
        state=update.state,
        existing=existing,
        now=now,
    )
    return _ResolvedServiceStateValues(
        runtime_mode=resolved_runtime_mode,
        started_at=_resolve_started_at(
            update=update,
            existing=existing,
            now=now,
        ),
        pid=_resolve_service_pid(update, existing),
        stop_requested=_resolve_value(
            update.stop_requested,
            _existing_value(existing, "stop_requested"),
            False,
        ),
        symbols=_resolve_symbols(update.symbols, existing),
        interval=_resolve_optional_value(
            update.interval,
            _existing_value(existing, "interval"),
        ),
        lookback=_resolve_optional_value(
            update.lookback,
            _existing_value(existing, "lookback"),
        ),
        max_cycles=_resolve_optional_value(
            update.max_cycles,
            _existing_value(existing, "max_cycles"),
        ),
        background_mode=_resolve_value(
            update.background_mode,
            _existing_value(existing, "background_mode"),
            False,
        ),
        launch_count=_resolve_value(
            update.launch_count,
            _existing_value(existing, "launch_count"),
            0,
        ),
        restart_count=_resolve_value(
            update.restart_count,
            _existing_value(existing, "restart_count"),
            0,
        ),
        last_terminal_state=last_terminal_state,
        last_terminal_at=last_terminal_at,
        stdout_log_path=_resolve_optional_value(
            update.stdout_log_path,
            _existing_value(existing, "stdout_log_path"),
        ),
        stderr_log_path=_resolve_optional_value(
            update.stderr_log_path,
            _existing_value(existing, "stderr_log_path"),
        ),
    )


def _upsert_service_state_row(
    conn: duckdb.DuckDBPyConnection,
    *,
    update: ServiceStateUpdate,
    resolved: _ResolvedServiceStateValues,
    now: str,
) -> None:
    conn.execute(
        """
        insert into service_state (
            service_name, state, runtime_mode, updated_at, started_at, last_heartbeat_at,
            continuous, poll_seconds, cycle_count, symbols_json, interval, lookback, max_cycles,
            current_symbol, last_error, pid, stop_requested, background_mode,
            launch_count, restart_count, last_terminal_state, last_terminal_at,
            stdout_log_path, stderr_log_path, message
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(service_name) do update set
            state = excluded.state,
            runtime_mode = excluded.runtime_mode,
            updated_at = excluded.updated_at,
            started_at = excluded.started_at,
            last_heartbeat_at = excluded.last_heartbeat_at,
            continuous = excluded.continuous,
            poll_seconds = excluded.poll_seconds,
            cycle_count = excluded.cycle_count,
            symbols_json = excluded.symbols_json,
            interval = excluded.interval,
            lookback = excluded.lookback,
            max_cycles = excluded.max_cycles,
            current_symbol = excluded.current_symbol,
            last_error = excluded.last_error,
            pid = excluded.pid,
            stop_requested = excluded.stop_requested,
            background_mode = excluded.background_mode,
            launch_count = excluded.launch_count,
            restart_count = excluded.restart_count,
            last_terminal_state = excluded.last_terminal_state,
            last_terminal_at = excluded.last_terminal_at,
            stdout_log_path = excluded.stdout_log_path,
            stderr_log_path = excluded.stderr_log_path,
            message = excluded.message
        """,
        [
            update.service_name,
            update.state,
            resolved.runtime_mode,
            now,
            resolved.started_at,
            now,
            update.continuous,
            update.poll_seconds,
            update.cycle_count,
            json.dumps(resolved.symbols),
            resolved.interval,
            resolved.lookback,
            resolved.max_cycles,
            update.current_symbol,
            update.last_error,
            resolved.pid,
            resolved.stop_requested,
            resolved.background_mode,
            resolved.launch_count,
            resolved.restart_count,
            resolved.last_terminal_state,
            resolved.last_terminal_at,
            resolved.stdout_log_path,
            resolved.stderr_log_path,
            update.message,
        ],
    )


def _write_service_state_snapshot(
    settings: Settings,
    *,
    update: ServiceStateUpdate,
    resolved: _ResolvedServiceStateValues,
    now: str,
) -> None:
    write_service_state(
        settings,
        ServiceStateSnapshot(
            service_name=update.service_name,
            state=cast(ServiceState, update.state),
            runtime_mode=resolved.runtime_mode,
            updated_at=now,
            started_at=resolved.started_at,
            last_heartbeat_at=now,
            continuous=update.continuous,
            poll_seconds=update.poll_seconds,
            cycle_count=update.cycle_count,
            symbols=resolved.symbols,
            interval=resolved.interval,
            lookback=resolved.lookback,
            max_cycles=resolved.max_cycles,
            current_symbol=update.current_symbol,
            last_error=update.last_error,
            pid=resolved.pid,
            stop_requested=resolved.stop_requested,
            background_mode=resolved.background_mode,
            launch_count=resolved.launch_count,
            restart_count=resolved.restart_count,
            last_terminal_state=resolved.last_terminal_state,
            last_terminal_at=resolved.last_terminal_at,
            stdout_log_path=resolved.stdout_log_path,
            stderr_log_path=resolved.stderr_log_path,
            message=update.message,
        ),
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
    resolved = _resolve_service_state_values(
        settings=settings,
        update=update,
        existing=existing,
        now=now,
    )
    _upsert_service_state_row(conn, update=update, resolved=resolved, now=now)
    _write_service_state_snapshot(
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
    return _service_state_from_row(row)


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
