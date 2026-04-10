import os
from dataclasses import dataclass
from datetime import datetime, timezone

from agentic_trader.schemas import ServiceEvent, ServiceStateSnapshot


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
    cycle_count = (
        state.cycle_count
        if state is not None and state.cycle_count > 0
        else (stage_events[0].cycle_count if stage_events else None)
    )
    current_symbol = (
        state.current_symbol
        if state is not None and state.current_symbol is not None
        else (stage_events[0].symbol if stage_events else None)
    )
    relevant_stage_events = [
        event for event in stage_events if cycle_count is None or event.cycle_count == cycle_count
    ]
    latest_stage_event = relevant_stage_events[0] if relevant_stage_events else None
    last_completed_stage = next(
        (event for event in relevant_stage_events if event.status == "completed"), None
    )
    latest_outcome = next(
        (
            event
            for event in events
            if event.event_type
            in {
                "symbol_completed",
                "position_closed",
                "service_completed",
                "service_failed",
                "service_stopped",
            }
            and (cycle_count is None or event.cycle_count == cycle_count)
        ),
        None,
    )
    terminal_status_by_outcome = {
        "symbol_completed": "completed",
        "position_closed": "completed",
        "service_completed": "completed",
        "service_failed": "failed",
        "service_stopped": "stopped",
    }
    terminal_override: AgentStageStatusView | None = None
    if (
        latest_stage_event is not None
        and latest_stage_event.status == "started"
        and latest_outcome is not None
        and latest_outcome.event_type in terminal_status_by_outcome
    ):
        terminal_status = terminal_status_by_outcome[latest_outcome.event_type]
        terminal_message = (
            f"{latest_stage_event.stage} interrupted by "
            f"{latest_outcome.event_type}: {latest_outcome.message}"
        )
        terminal_override = AgentStageStatusView(
            stage=latest_stage_event.stage,
            status=terminal_status,
            message=terminal_message,
            created_at=latest_outcome.created_at,
            cycle_count=latest_stage_event.cycle_count,
            symbol=latest_stage_event.symbol,
        )

    stage_order = (
        "coordinator",
        "regime",
        "strategy",
        "risk",
        "consensus",
        "manager",
        "execution",
        "review",
    )
    latest_by_stage: dict[str, AgentStageStatusView] = {}
    for event in relevant_stage_events:
        latest_by_stage.setdefault(event.stage, event)
    if terminal_override is not None:
        latest_by_stage[terminal_override.stage] = terminal_override

    stage_statuses: list[AgentStageStatusView] = []
    for stage in stage_order:
        snapshot = latest_by_stage.get(stage)
        if snapshot is not None:
            stage_statuses.append(snapshot)
        else:
            stage_statuses.append(
                AgentStageStatusView(
                    stage=stage,
                    status="pending",
                    message="Waiting for this stage to start.",
                    created_at="-",
                    cycle_count=cycle_count,
                    symbol=current_symbol,
                )
            )

    return AgentActivityView(
        cycle_count=cycle_count,
        current_symbol=current_symbol,
        current_stage=(
            terminal_override.stage
            if terminal_override is not None
            else (latest_stage_event.stage if latest_stage_event is not None else None)
        ),
        current_stage_status=(
            terminal_override.status
            if terminal_override is not None
            else (
                "running"
                if latest_stage_event is not None
                and latest_stage_event.status == "started"
                else (
                    latest_stage_event.status
                    if latest_stage_event is not None
                    else None
                )
            )
        ),
        current_stage_message=(
            terminal_override.message
            if terminal_override is not None
            else (latest_stage_event.message if latest_stage_event is not None else None)
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
