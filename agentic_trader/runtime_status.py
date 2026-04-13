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
    """
    Parse an ISO 8601 timestamp string into an aware datetime.
    
    Parses `value` using datetime.fromisoformat. If `value` is None or cannot be parsed, returns `None`. If the parsed datetime has no timezone information, attaches UTC (`timezone.utc`) before returning.
    
    Parameters:
        value (str | None): ISO 8601 timestamp string, or `None`.
    
    Returns:
        datetime | None: A timezone-aware `datetime` (UTC assigned if input was naive), or `None` if input is missing or invalid.
    """
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
    """
    Selects the effective cycle count to use when assembling per-cycle stage information.
    
    Parameters:
        state (ServiceStateSnapshot | None): Optional runtime state whose positive `cycle_count` is preferred.
        stage_events (list[AgentStageStatusView]): Ordered stage events; the first event's `cycle_count` is used as a fallback.
    
    Returns:
        int | None: The chosen cycle count, or `None` if neither the state nor the events provide a value.
    """
    if state is not None and state.cycle_count > 0:
        return state.cycle_count
    if stage_events:
        return stage_events[0].cycle_count
    return None


def _effective_current_symbol(
    state: ServiceStateSnapshot | None, stage_events: list[AgentStageStatusView]
) -> str | None:
    """
    Determine the effective current symbol for an agent by preferring the runtime state value and falling back to recent stage events.
    
    Parameters:
        state (ServiceStateSnapshot | None): Optional runtime snapshot whose `current_symbol`, if present, takes precedence.
        stage_events (list[AgentStageStatusView]): Recent per-stage status events; the first event's `symbol` is used as a fallback.
    
    Returns:
        str | None: The chosen symbol string if available, otherwise `None`.
    """
    if state is not None and state.current_symbol is not None:
        return state.current_symbol
    if stage_events:
        return stage_events[0].symbol
    return None


def _events_for_cycle(
    stage_events: list[AgentStageStatusView], cycle_count: int | None
) -> list[AgentStageStatusView]:
    """
    Selects stage events that belong to the specified cycle.
    
    Parameters:
        stage_events (list[AgentStageStatusView]): Sequence of parsed stage events to filter.
        cycle_count (int | None): Cycle number to filter by; when `None`, no filtering is applied.
    
    Returns:
        list[AgentStageStatusView]: Events whose `cycle_count` equals `cycle_count`, or all events if `cycle_count` is `None`.
    """
    if cycle_count is None:
        return stage_events
    return [event for event in stage_events if event.cycle_count == cycle_count]


def _latest_outcome_event(
    events: list[ServiceEvent], cycle_count: int | None
) -> ServiceEvent | None:
    """
    Finds the first terminal outcome ServiceEvent, optionally restricted to a given cycle.
    
    Parameters:
        events (list[ServiceEvent]): Sequence of service events to search in, in chronological order.
        cycle_count (int | None): If provided, only consider events whose `cycle_count` equals this value.
    
    Returns:
        ServiceEvent | None: The first event whose `event_type` is a terminal outcome (as defined in TERMINAL_STATUS_BY_OUTCOME) and that matches `cycle_count` when provided, or `None` if no such event exists.
    """
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
    """
    Create an override stage status when a started stage is interrupted by a terminal outcome event.
    
    Returns an AgentStageStatusView that mirrors the started stage but with a terminal `status`, a message indicating the stage was interrupted by the outcome event (including the outcome's type and message), `created_at` taken from the outcome event, and the original stage's `cycle_count` and `symbol`. Returns `None` if no override should be produced.
    
    Parameters:
        latest_stage_event: The most recent stage event for the agent (may be None).
        latest_outcome: The most recent terminal outcome ServiceEvent (may be None).
    
    Returns:
        AgentStageStatusView or `None`: The override stage view when the latest stage is currently `"started"` and `latest_outcome.event_type` maps to a terminal status; otherwise `None`.
    """
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
    """
    Builds the complete per-stage status list for a single cycle in STAGE_ORDER.
    
    Parameters:
        relevant_stage_events (list[AgentStageStatusView]): Stage event snapshots to consider; later entries override earlier ones for the same stage.
        terminal_override (AgentStageStatusView | None): Optional override that, if provided, forces the given stage to the override value.
        cycle_count (int | None): Cycle number to attach to generated pending stage entries when no snapshot exists.
        current_symbol (str | None): Symbol to attach to generated pending stage entries when no snapshot exists.
    
    Returns:
        list[AgentStageStatusView]: A list of stage status views in the order of STAGE_ORDER. For stages without a provided snapshot or override, returns a pending AgentStageStatusView with `status="pending"`, `message=PENDING_STAGE_MESSAGE`, `created_at="-"`, and the supplied `cycle_count` and `current_symbol`.
    """
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
    """
    Select the current stage name, preferring a terminal override when present.
    
    Returns:
        str: Stage name from `terminal_override` if provided; otherwise the stage from `latest_stage_event`; `None` if neither is available.
    """
    if terminal_override is not None:
        return terminal_override.stage
    if latest_stage_event is not None:
        return latest_stage_event.stage
    return None


def _current_stage_status(
    terminal_override: AgentStageStatusView | None,
    latest_stage_event: AgentStageStatusView | None,
) -> str | None:
    """
    Determine the effective status for the current stage, applying a terminal override when present.
    
    Parameters:
        terminal_override (AgentStageStatusView | None): If provided, its `status` takes precedence.
        latest_stage_event (AgentStageStatusView | None): Most recent stage event to derive status from when no override exists.
    
    Returns:
        str | None: The effective stage status (maps an event status of `"started"` to `"running"`), or `None` if no status is available.
    """
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
    """
    Selects the message text for the current stage, preferring a terminal override when present.
    
    Parameters:
        terminal_override (AgentStageStatusView | None): An override stage status whose `message` should take precedence if provided.
        latest_stage_event (AgentStageStatusView | None): The most recent stage event to use when no terminal override exists.
    
    Returns:
        str | None: The chosen message string from `terminal_override` or `latest_stage_event`, or `None` if neither is available.
    """
    if terminal_override is not None:
        return terminal_override.message
    if latest_stage_event is not None:
        return latest_stage_event.message
    return None


def is_process_alive(pid: int | None) -> bool:
    """
    Determine whether a process with the given PID is alive.
    
    Parameters:
        pid (int | None): Process ID to probe; if None, considered not alive.
    
    Returns:
        bool: True if the process exists (or exists but cannot be signaled due to permissions), False otherwise.
    """
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
    """
    Builds an AgentActivityView summarizing an agent's per-stage activity for the effective cycle.
    
    Parses agent stage events from `events`, selects an effective cycle and symbol (preferring state values when present), filters events to that cycle, and computes current/last-completed stage information, a terminal outcome override if applicable, the per-stage statuses for the cycle, and up to eight recent stage events.
    
    Parameters:
        state (ServiceStateSnapshot | None): Optional runtime snapshot used to prefer authoritative cycle_count and current_symbol.
        events (list[ServiceEvent]): Timeline of service events from which agent stage events and terminal outcomes are extracted.
    
    Returns:
        AgentActivityView: View containing:
          - cycle_count and current_symbol for the selected cycle,
          - current_stage, current_stage_status, and current_stage_message,
          - last_completed_stage and last_completed_message (or None),
          - last_outcome_type and last_outcome_message (or None),
          - stage_statuses: tuple of AgentStageStatusView for every stage in STAGE_ORDER (pending stages populated with PENDING_STAGE_MESSAGE),
          - recent_stage_events: tuple of up to 8 most-recent stage events for the selected cycle.
    """
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
