from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import v1_readiness_payload
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_mapping
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import read_service_state
from agentic_trader.runtime_status import (
    build_agent_activity_view,
    build_runtime_status_view,
)
from agentic_trader.schemas import (
    LLMHealthStatus,
    ServiceEvent,
    ServiceStateSnapshot,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.monitor_lines import (
    agent_activity_lines,
    broker_gate_lines,
    last_outcome_lines,
    runtime_cycle_lines,
)
from agentic_trader.ui_text import (
    LABEL_BACKGROUND_MODE,
    LABEL_BASE_URL,
    LABEL_CONTINUOUS,
    LABEL_CREATED,
    LABEL_CURRENT_SYMBOL,
    LABEL_CYCLE,
    LABEL_CYCLE_COUNT,
    LABEL_HEARTBEAT,
    LABEL_HEARTBEAT_AGE,
    LABEL_KEY,
    LABEL_LAST_RECORDED_ERROR,
    LABEL_LAST_RECORDED_MESSAGE,
    LABEL_LAST_RECORDED_STATE,
    LABEL_LAST_TERMINAL_AT,
    LABEL_LAST_TERMINAL_STATE,
    LABEL_LATEST_ORDER,
    LABEL_LAUNCH_COUNT,
    LABEL_LEVEL,
    LABEL_LIVE_PROCESS,
    LABEL_MESSAGE,
    LABEL_MODEL,
    LABEL_MODEL_AVAILABLE,
    LABEL_NO,
    LABEL_OBSERVER_MODE,
    LABEL_OLLAMA_REACHABLE,
    LABEL_PID,
    LABEL_RESTART_COUNT,
    LABEL_RUNTIME,
    LABEL_RUNTIME_DIR,
    LABEL_STAGE,
    LABEL_STATE,
    LABEL_STATUS,
    LABEL_STATUS_NOTE,
    LABEL_STOP_REQUESTED,
    LABEL_STRICT_LLM,
    LABEL_SYMBOL,
    LABEL_TYPE,
    LABEL_UPDATED,
    LABEL_VALUE,
    LABEL_YES,
    MESSAGE_NO_LIVE_AGENT_STAGE_EVENTS,
    MESSAGE_NO_RUNTIME_EVENTS,
    MESSAGE_NO_RUNTIME_STATE,
    TITLE_CURRENT_CYCLE,
    TITLE_DECISION_WORKFLOW,
    TITLE_RUNTIME_EVENTS,
    TITLE_RUNTIME_MODE,
    TITLE_RUNTIME_STATUS,
    TITLE_SYSTEM_STATUS,
    t,
)

console = Console()


def safe_open_read_db(settings: Settings) -> TradingDatabase | None:
    state = read_service_state(settings)
    view = build_runtime_status_view(state)
    if view.live_process and view.last_recorded_state in {
        "starting",
        "running",
        "stopping",
    }:
        return None
    try:
        return TradingDatabase(settings, read_only=True)
    except Exception:
        return None


def observer_mode_panel(feature: str, error: str | None = None) -> Panel:
    body = t("observer.mode.temporarily_unavailable", feature=feature)
    if error:
        body += f"\n\n{error}"
    return Panel(body, title=LABEL_OBSERVER_MODE, border_style="yellow")


def render_runtime_state(state: ServiceStateSnapshot | None) -> None:
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                MESSAGE_NO_RUNTIME_STATE,
                title=TITLE_RUNTIME_STATUS,
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=TITLE_RUNTIME_STATUS)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_RUNTIME, view.runtime_state)
    table.add_row(LABEL_LIVE_PROCESS, LABEL_YES if view.live_process else LABEL_NO)
    table.add_row(LABEL_LAST_RECORDED_STATE, view.last_recorded_state or "-")
    table.add_row(LABEL_UPDATED, snapshot.updated_at)
    table.add_row(LABEL_HEARTBEAT, snapshot.last_heartbeat_at or "-")
    table.add_row(
        LABEL_HEARTBEAT_AGE,
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(LABEL_CYCLE_COUNT, str(snapshot.cycle_count))
    table.add_row(LABEL_CURRENT_SYMBOL, snapshot.current_symbol or "-")
    table.add_row(LABEL_PID, str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row(LABEL_STOP_REQUESTED, str(snapshot.stop_requested))
    table.add_row(LABEL_CONTINUOUS, str(snapshot.continuous))
    table.add_row(LABEL_BACKGROUND_MODE, str(snapshot.background_mode))
    table.add_row(LABEL_LAUNCH_COUNT, str(snapshot.launch_count))
    table.add_row(LABEL_RESTART_COUNT, str(snapshot.restart_count))
    table.add_row(LABEL_LAST_TERMINAL_STATE, snapshot.last_terminal_state or "-")
    table.add_row(LABEL_LAST_TERMINAL_AT, snapshot.last_terminal_at or "-")
    table.add_row(LABEL_STATUS_NOTE, view.status_message)
    table.add_row(LABEL_LAST_RECORDED_MESSAGE, snapshot.message or "-")
    table.add_row(LABEL_LAST_RECORDED_ERROR, snapshot.last_error or "-")
    console.print(table)


def render_runtime_events(events: list[ServiceEvent]) -> None:
    if not events:
        console.print(
            Panel(
                MESSAGE_NO_RUNTIME_EVENTS,
                title=TITLE_RUNTIME_EVENTS,
                border_style="yellow",
            )
        )
        return
    console.print(runtime_events_table(events))


def runtime_events_table(events: list[ServiceEvent]) -> Table:
    table = Table(title=TITLE_RUNTIME_EVENTS)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_LEVEL)
    table.add_column(LABEL_TYPE)
    table.add_column(LABEL_CYCLE)
    table.add_column(LABEL_SYMBOL)
    if not events:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for event in events:
        table.add_row(
            event.created_at,
            event.level,
            event.event_type,
            str(event.cycle_count) if event.cycle_count is not None else "-",
            event.symbol or "-",
        )
    return table


def agent_activity_table(
    state: ServiceStateSnapshot | None, events: list[ServiceEvent]
) -> Table:
    table = Table(title=TITLE_DECISION_WORKFLOW)
    table.add_column(LABEL_STAGE)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_MESSAGE)
    activity = build_agent_activity_view(state, events)
    if not activity.stage_statuses:
        table.add_row("-", "-", MESSAGE_NO_LIVE_AGENT_STAGE_EVENTS)
        return table
    for stage in activity.stage_statuses:
        table.add_row(stage.stage, stage.status, stage.message)
    return table


def current_activity_panel(
    settings: Settings, state: ServiceStateSnapshot | None, events: list[ServiceEvent]
) -> Panel:
    view = build_runtime_status_view(state)
    activity = build_agent_activity_view(state, events)
    broker = broker_runtime_payload(settings)
    readiness = object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper_operations = object_mapping(readiness.get("paper_operations"))
    lines = [
        *runtime_cycle_lines(settings=settings, state=state, view=view),
        "",
        *agent_activity_lines(activity),
        "",
        *broker_gate_lines(broker=broker, paper_operations=paper_operations),
        "",
        *last_outcome_lines(activity),
    ]
    body = "\n".join(lines)
    return Panel(body, title=TITLE_CURRENT_CYCLE, border_style="bright_cyan")


def runtime_state_table(state: ServiceStateSnapshot | None) -> Table:
    table = Table(title=TITLE_RUNTIME_STATUS)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    view = build_runtime_status_view(state)
    if view.state is None:
        table.add_row(LABEL_STATE, MESSAGE_NO_RUNTIME_STATE)
        return table
    snapshot = view.state
    table.add_row(LABEL_RUNTIME, view.runtime_state)
    table.add_row(LABEL_LIVE_PROCESS, LABEL_YES if view.live_process else LABEL_NO)
    table.add_row(LABEL_LAST_RECORDED_STATE, view.last_recorded_state or "-")
    table.add_row(LABEL_UPDATED, snapshot.updated_at)
    table.add_row(LABEL_HEARTBEAT, snapshot.last_heartbeat_at or "-")
    table.add_row(
        LABEL_HEARTBEAT_AGE,
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(LABEL_CYCLE_COUNT, str(snapshot.cycle_count))
    table.add_row(LABEL_CURRENT_SYMBOL, snapshot.current_symbol or "-")
    table.add_row(LABEL_PID, str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row(LABEL_STOP_REQUESTED, str(snapshot.stop_requested))
    table.add_row(LABEL_CONTINUOUS, str(snapshot.continuous))
    table.add_row(LABEL_BACKGROUND_MODE, str(snapshot.background_mode))
    table.add_row(LABEL_LAUNCH_COUNT, str(snapshot.launch_count))
    table.add_row(LABEL_RESTART_COUNT, str(snapshot.restart_count))
    table.add_row(LABEL_LAST_TERMINAL_STATE, snapshot.last_terminal_state or "-")
    table.add_row(LABEL_LAST_TERMINAL_AT, snapshot.last_terminal_at or "-")
    table.add_row(LABEL_STATUS_NOTE, view.status_message)
    table.add_row(LABEL_LAST_RECORDED_MESSAGE, snapshot.message or "-")
    table.add_row(LABEL_LAST_RECORDED_ERROR, snapshot.last_error or "-")
    return table


def system_status_table(
    settings: Settings,
    db: TradingDatabase | None,
    *,
    runtime_state: ServiceStateSnapshot | None = None,
    health: LLMHealthStatus | None = None,
) -> Table:
    health_status = health if health is not None else LocalLLM(settings).health_check()
    latest_order = db.latest_order() if db is not None else None
    table = Table(title=TITLE_SYSTEM_STATUS)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_RUNTIME_DIR, str(settings.runtime_dir))
    table.add_row(
        TITLE_RUNTIME_MODE,
        (
            runtime_state.runtime_mode
            if runtime_state is not None
            else settings.runtime_mode
        ),
    )
    table.add_row(LABEL_MODEL, settings.model_name)
    table.add_row(LABEL_BASE_URL, settings.base_url)
    table.add_row(
        LABEL_OLLAMA_REACHABLE,
        LABEL_YES if health_status.service_reachable else LABEL_NO,
    )
    table.add_row(
        LABEL_MODEL_AVAILABLE,
        LABEL_YES if health_status.model_available else LABEL_NO,
    )
    table.add_row(LABEL_STRICT_LLM, str(settings.strict_llm))
    if db is not None:
        table.add_row(
            LABEL_LATEST_ORDER, latest_order[0] if latest_order is not None else "-"
        )
    return table


__all__ = (
    "agent_activity_table",
    "current_activity_panel",
    "observer_mode_panel",
    "render_runtime_events",
    "render_runtime_state",
    "runtime_events_table",
    "runtime_state_table",
    "safe_open_read_db",
    "system_status_table",
)
