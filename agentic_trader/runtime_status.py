import os
from dataclasses import dataclass
from datetime import datetime, timezone

from agentic_trader.schemas import ServiceEvent, ServiceStateSnapshot

STAGE_ORDER = (
    "coordinator",
    "regime",
    "strategy",
    "risk",
    "consensus",
    "manager",
    "execution",
    "review",
)
TERMINAL_STATUS_BY_OUTCOME = {
    "symbol_completed": "completed",
    "position_closed": "completed",
    "service_completed": "completed",
    "service_failed": "failed",
    "service_stopped": "stopped",
}
PENDING_STAGE_MESSAGE = "Waiting for this stage to start."


@dataclass(frozen=True)
class RuntimeStatusView:
    runtime_state: str
    last_recorded_state: str | None
    status_message: str
    live_process: bool
    is_stale: bool
    age_seconds: int | None
    state: ServiceStateSnapshot | None


@dataclass(frozen=True)
class AgentStageStatusView:
    stage: str
    status: str
    message: str
    created_at: str
    cycle_count: int | None
    symbol: str | None


@dataclass(frozen=True)
class AgentActivityView:
    cycle_count: int | None
    current_symbol: str | None
    current_stage: str | None
    current_stage_status: str | None
    current_stage_message: str | None
    last_completed_stage: str | None
    last_completed_message: str | None
    last_outcome_type: str | None
    last_outcome_message: str | None
    stage_statuses: tuple[AgentStageStatusView, ...]
    recent_stage_events: tuple[AgentStageStatusView, ...]


def _parse_agent_stage_event(event: ServiceEvent) -> AgentStageStatusView | None:
    if not event.event_type.startswith("agent_"):
        return None
    _, _, remainder = event.event_type.partition("agent_")
    if "_" not in remainder:
        return None
    stage, status = remainder.rsplit("_", 1)
    return AgentStageStatusView(
        stage=stage,
        status=status,
        message=event.message,
        created_at=event.created_at,
        cycle_count=event.cycle_count,
        symbol=event.symbol,
    )


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


def _effective_cycle_count(
    state: ServiceStateSnapshot | None, stage_events: list[AgentStageStatusView]
) -> int | None:
    if state is not None and state.cycle_count > 0:
        return state.cycle_count
    if stage_events:
        return stage_events[0].cycle_count
    return None


def _effective_current_symbol(
    state: ServiceStateSnapshot | None, stage_events: list[AgentStageStatusView]
) -> str | None:
    if state is not None and state.current_symbol is not None:
        return state.current_symbol
    if stage_events:
        return stage_events[0].symbol
    return None


def _events_for_cycle(
    stage_events: list[AgentStageStatusView], cycle_count: int | None
) -> list[AgentStageStatusView]:
    if cycle_count is None:
        return stage_events
    return [event for event in stage_events if event.cycle_count == cycle_count]


def _latest_outcome_event(
    events: list[ServiceEvent], cycle_count: int | None
) -> ServiceEvent | None:
    return next(
        (
            event
            for event in events
            if event.event_type in TERMINAL_STATUS_BY_OUTCOME
            and (cycle_count is None or event.cycle_count == cycle_count)
        ),
        None,
    )


def _terminal_override_for_stage(
    latest_stage_event: AgentStageStatusView | None,
    latest_outcome: ServiceEvent | None,
) -> AgentStageStatusView | None:
    if latest_stage_event is None or latest_stage_event.status != "started":
        return None
    if latest_outcome is None:
        return None
    terminal_status = TERMINAL_STATUS_BY_OUTCOME.get(latest_outcome.event_type)
    if terminal_status is None:
        return None
    return AgentStageStatusView(
        stage=latest_stage_event.stage,
        status=terminal_status,
        message=(
            f"{latest_stage_event.stage} interrupted by "
            f"{latest_outcome.event_type}: {latest_outcome.message}"
        ),
        created_at=latest_outcome.created_at,
        cycle_count=latest_stage_event.cycle_count,
        symbol=latest_stage_event.symbol,
    )


def _stage_statuses_for_cycle(
    relevant_stage_events: list[AgentStageStatusView],
    terminal_override: AgentStageStatusView | None,
    cycle_count: int | None,
    current_symbol: str | None,
) -> list[AgentStageStatusView]:
    latest_by_stage: dict[str, AgentStageStatusView] = {}
    for event in relevant_stage_events:
        latest_by_stage.setdefault(event.stage, event)
    if terminal_override is not None:
        latest_by_stage[terminal_override.stage] = terminal_override

    statuses: list[AgentStageStatusView] = []
    for stage in STAGE_ORDER:
        snapshot = latest_by_stage.get(stage)
        statuses.append(
            snapshot
            if snapshot is not None
            else AgentStageStatusView(
                stage=stage,
                status="pending",
                message=PENDING_STAGE_MESSAGE,
                created_at="-",
                cycle_count=cycle_count,
                symbol=current_symbol,
            )
        )
    return statuses


def _current_stage(
    terminal_override: AgentStageStatusView | None,
    latest_stage_event: AgentStageStatusView | None,
) -> str | None:
    if terminal_override is not None:
        return terminal_override.stage
    if latest_stage_event is not None:
        return latest_stage_event.stage
    return None


def _current_stage_status(
    terminal_override: AgentStageStatusView | None,
    latest_stage_event: AgentStageStatusView | None,
) -> str | None:
    if terminal_override is not None:
        return terminal_override.status
    if latest_stage_event is None:
        return None
    if latest_stage_event.status == "started":
        return "running"
    return latest_stage_event.status


def _current_stage_message(
    terminal_override: AgentStageStatusView | None,
    latest_stage_event: AgentStageStatusView | None,
) -> str | None:
    if terminal_override is not None:
        return terminal_override.message
    if latest_stage_event is not None:
        return latest_stage_event.message
    return None


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
        age_seconds = max(
            0, int((datetime.now(timezone.utc) - heartbeat).total_seconds())
        )

    transitional = state.state in {"starting", "running", "stopping"}
    is_stale = transitional and (
        (age_seconds is not None and age_seconds > stale_after_seconds)
        or not live_process
    )

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


def build_agent_activity_view(
    state: ServiceStateSnapshot | None, events: list[ServiceEvent]
) -> AgentActivityView:
    stage_events = [
        parsed
        for event in events
        if (parsed := _parse_agent_stage_event(event)) is not None
    ]
    cycle_count = _effective_cycle_count(state, stage_events)
    current_symbol = _effective_current_symbol(state, stage_events)
    relevant_stage_events = _events_for_cycle(stage_events, cycle_count)
    latest_stage_event = relevant_stage_events[0] if relevant_stage_events else None
    last_completed_stage = next(
        (event for event in relevant_stage_events if event.status == "completed"), None
    )
    latest_outcome = _latest_outcome_event(events, cycle_count)
    terminal_override = _terminal_override_for_stage(
        latest_stage_event, latest_outcome
    )
    stage_statuses = _stage_statuses_for_cycle(
        relevant_stage_events, terminal_override, cycle_count, current_symbol
    )

    return AgentActivityView(
        cycle_count=cycle_count,
        current_symbol=current_symbol,
        current_stage=_current_stage(terminal_override, latest_stage_event),
        current_stage_status=_current_stage_status(
            terminal_override, latest_stage_event
        ),
        current_stage_message=_current_stage_message(
            terminal_override, latest_stage_event
        ),
        last_completed_stage=(
            last_completed_stage.stage if last_completed_stage is not None else None
        ),
        last_completed_message=(
            last_completed_stage.message if last_completed_stage is not None else None
        ),
        last_outcome_type=latest_outcome.event_type if latest_outcome is not None else None,
        last_outcome_message=latest_outcome.message if latest_outcome is not None else None,
        stage_statuses=tuple(stage_statuses),
        recent_stage_events=tuple(relevant_stage_events[:8]),
    )
