import os
from dataclasses import dataclass
from datetime import datetime, timezone

from agentic_trader.schemas import ServiceStateSnapshot


@dataclass(frozen=True)
class RuntimeStatusView:
    runtime_state: str
    last_recorded_state: str | None
    status_message: str
    live_process: bool
    is_stale: bool
    age_seconds: int | None
    state: ServiceStateSnapshot | None


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_process_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def build_runtime_status_view(
    state: ServiceStateSnapshot | None,
    *,
    stale_after_seconds: int = 300,
) -> RuntimeStatusView:
    if state is None:
        return RuntimeStatusView(
            runtime_state="inactive",
            last_recorded_state=None,
            status_message="No runtime state has been recorded yet.",
            live_process=False,
            is_stale=False,
            age_seconds=None,
            state=None,
        )

    live_process = is_process_alive(state.pid)
    heartbeat = _parse_timestamp(state.last_heartbeat_at or state.updated_at)
    age_seconds: int | None = None
    if heartbeat is not None:
        age_seconds = max(0, int((datetime.now(timezone.utc) - heartbeat).total_seconds()))

    transitional = state.state in {"starting", "running", "stopping"}
    is_stale = transitional and ((age_seconds is not None and age_seconds > stale_after_seconds) or not live_process)

    if transitional and live_process and not is_stale:
        return RuntimeStatusView(
            runtime_state="active",
            last_recorded_state=state.state,
            status_message=state.message or "Orchestrator is actively running.",
            live_process=True,
            is_stale=False,
            age_seconds=age_seconds,
            state=state,
        )

    if is_stale:
        return RuntimeStatusView(
            runtime_state="stale",
            last_recorded_state=state.state,
            status_message="No live orchestrator heartbeat is active. Showing the last recorded runtime state.",
            live_process=live_process,
            is_stale=True,
            age_seconds=age_seconds,
            state=state,
        )

    return RuntimeStatusView(
        runtime_state="inactive",
        last_recorded_state=state.state,
        status_message="No live orchestrator process is active. Showing the last recorded runtime state.",
        live_process=live_process,
        is_stale=False,
        age_seconds=age_seconds,
        state=state,
    )
