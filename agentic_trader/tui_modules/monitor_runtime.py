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
    """
    Create a yellow-bordered Panel informing that a specific feature is temporarily unavailable in observer mode.
    
    Parameters:
        feature (str): Feature name inserted into the localized unavailability message.
        error (str | None): Optional error or diagnostic text appended to the panel body when provided.
    
    Returns:
        Panel: A Panel titled with `t("label.observer_mode")` whose body contains the localized unavailability message (and the appended error text if given).
    """
    body = t("observer.mode.temporarily_unavailable", feature=feature)
    if error:
        body += f"\n\n{error}"
    return Panel(body, title=t("label.observer_mode"), border_style="yellow")


def render_runtime_state(state: ServiceStateSnapshot | None) -> None:
    """
    Render the current runtime status to the module console as a rich panel or table.
    
    Parameters:
    	state (ServiceStateSnapshot | None): Current service runtime snapshot or `None` when no runtime state is available. When `None` a message panel is printed; otherwise a key/value table of runtime and snapshot fields is printed.
    """
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                t("message.no_runtime_state"),
                title=t("title.runtime_status"),
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=t("title.runtime_status"))
    table.add_column(t("label.key"))
    table.add_column(t("label.value"))
    table.add_row(t("label.runtime"), view.runtime_state)
    table.add_row(
        t("label.live_process"), t("label.yes") if view.live_process else t("label.no")
    )
    table.add_row(t("label.last_recorded_state"), view.last_recorded_state or "-")
    table.add_row(t("label.updated"), snapshot.updated_at)
    table.add_row(t("label.heartbeat"), snapshot.last_heartbeat_at or "-")
    table.add_row(
        t("label.heartbeat_age"),
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(t("label.cycle_count"), str(snapshot.cycle_count))
    table.add_row(t("label.current_symbol"), snapshot.current_symbol or "-")
    table.add_row(
        t("label.pid"), str(snapshot.pid) if snapshot.pid is not None else "-"
    )
    table.add_row(t("label.stop_requested"), str(snapshot.stop_requested))
    table.add_row(t("label.continuous"), str(snapshot.continuous))
    table.add_row(t("label.background_mode"), str(snapshot.background_mode))
    table.add_row(t("label.launch_count"), str(snapshot.launch_count))
    table.add_row(t("label.restart_count"), str(snapshot.restart_count))
    table.add_row(t("label.last_terminal_state"), snapshot.last_terminal_state or "-")
    table.add_row(t("label.last_terminal_at"), snapshot.last_terminal_at or "-")
    table.add_row(t("label.status_note"), view.status_message)
    table.add_row(t("label.last_recorded_message"), snapshot.message or "-")
    table.add_row(t("label.last_recorded_error"), snapshot.last_error or "-")
    console.print(table)


def render_runtime_events(events: list[ServiceEvent]) -> None:
    """
    Render runtime events in the console as a table or a message when none are available.
    
    Prints a table of the given ServiceEvent objects. If `events` is empty, prints a yellow panel titled with the runtime events title indicating that there are no runtime events.
    Parameters:
        events (list[ServiceEvent]): List of runtime events to display; an empty list triggers the no-events panel.
    """
    if not events:
        console.print(
            Panel(
                t("message.no_runtime_events"),
                title=t("title.runtime_events"),
                border_style="yellow",
            )
        )
        return
    console.print(runtime_events_table(events))


def runtime_events_table(events: list[ServiceEvent]) -> Table:
    """
    Builds a Rich Table representing runtime events with columns for creation time, level, type, cycle, and symbol.
    
    Parameters:
        events (list[ServiceEvent]): Sequence of runtime events to include in the table. If empty, the table contains a single row of dashes.
    
    Returns:
        Table: A configured Rich Table titled with the runtime events label. Each event becomes a row; missing `cycle_count` or `symbol` values are represented as `"-"`.
    """
    table = Table(title=t("title.runtime_events"))
    table.add_column(t("label.created"))
    table.add_column(t("label.level"))
    table.add_column(t("label.type"))
    table.add_column(t("label.cycle"))
    table.add_column(t("label.symbol"))
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
    """
    Builds a table showing agent decision workflow stages, their status, and messages.
    
    Parameters:
        state (ServiceStateSnapshot | None): Current runtime snapshot used to derive agent activity; may be `None`.
        events (list[ServiceEvent]): Ordered list of runtime events used to construct the activity view.
    
    Returns:
        Table: A rich Table titled with the decision workflow, containing columns for stage, status, and message.
            If no stage statuses are present, the table contains a single row of dashes and a localized
            message indicating there are no live agent stage events.
    """
    table = Table(title=t("title.decision_workflow"))
    table.add_column(t("label.stage"))
    table.add_column(t("label.status"))
    table.add_column(t("label.message"))
    activity = build_agent_activity_view(state, events)
    if not activity.stage_statuses:
        table.add_row("-", "-", t("message.no_live_agent_stage_events"))
        return table
    for stage in activity.stage_statuses:
        table.add_row(stage.stage, stage.status, stage.message)
    return table


def current_activity_panel(
    settings: Settings, state: ServiceStateSnapshot | None, events: list[ServiceEvent]
) -> Panel:
    """
    Render a panel summarizing the current runtime cycle, agent decision workflow, broker gate status, and last outcome.
    
    Parameters:
        settings (Settings): Application configuration and runtime settings used to gather runtime and broker payloads.
        state (ServiceStateSnapshot | None): Current service state snapshot used to build runtime and activity views; may be None.
        events (list[ServiceEvent]): Recent service events used to build the agent activity view.
    
    Returns:
        panel (Panel): A Rich Panel containing joined lines for the runtime cycle, agent activity, broker gate (including paper operations), and last outcome.
    """
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
    return Panel(body, title=t("title.current_cycle"), border_style="bright_cyan")


def runtime_state_table(state: ServiceStateSnapshot | None) -> Table:
    """
    Builds a key/value table summarizing the current runtime state.
    
    Parameters:
    	state (ServiceStateSnapshot | None): The latest service state snapshot or None when not available.
    
    Returns:
    	Table: A Rich Table containing labeled runtime fields (runtime state, live process, last recorded state, timestamps, heartbeat age, cycle count, current symbol, pid, stop/continuous/background flags, launch/restart counts, terminal state/at, status note, last recorded message and error). If `state` is absent, the table contains a single row indicating no runtime state.
    """
    table = Table(title=t("title.runtime_status"))
    table.add_column(t("label.key"))
    table.add_column(t("label.value"))
    view = build_runtime_status_view(state)
    if view.state is None:
        table.add_row(t("label.state"), t("message.no_runtime_state"))
        return table
    snapshot = view.state
    table.add_row(t("label.runtime"), view.runtime_state)
    table.add_row(
        t("label.live_process"), t("label.yes") if view.live_process else t("label.no")
    )
    table.add_row(t("label.last_recorded_state"), view.last_recorded_state or "-")
    table.add_row(t("label.updated"), snapshot.updated_at)
    table.add_row(t("label.heartbeat"), snapshot.last_heartbeat_at or "-")
    table.add_row(
        t("label.heartbeat_age"),
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(t("label.cycle_count"), str(snapshot.cycle_count))
    table.add_row(t("label.current_symbol"), snapshot.current_symbol or "-")
    table.add_row(
        t("label.pid"), str(snapshot.pid) if snapshot.pid is not None else "-"
    )
    table.add_row(t("label.stop_requested"), str(snapshot.stop_requested))
    table.add_row(t("label.continuous"), str(snapshot.continuous))
    table.add_row(t("label.background_mode"), str(snapshot.background_mode))
    table.add_row(t("label.launch_count"), str(snapshot.launch_count))
    table.add_row(t("label.restart_count"), str(snapshot.restart_count))
    table.add_row(t("label.last_terminal_state"), snapshot.last_terminal_state or "-")
    table.add_row(t("label.last_terminal_at"), snapshot.last_terminal_at or "-")
    table.add_row(t("label.status_note"), view.status_message)
    table.add_row(t("label.last_recorded_message"), snapshot.message or "-")
    table.add_row(t("label.last_recorded_error"), snapshot.last_error or "-")
    return table


def system_status_table(
    settings: Settings,
    db: TradingDatabase | None,
    *,
    runtime_state: ServiceStateSnapshot | None = None,
    health: LLMHealthStatus | None = None,
) -> Table:
    """
    Create a two-column status table summarizing system and LLM health information.
    
    Parameters:
        settings: Application runtime configuration used to read runtime directory, mode, model, base URL and strict LLM flag.
        db: Optional read-only trading database; when provided, the table includes the latest order identifier.
    
    Returns:
        Table: A table with key/value rows including runtime directory, runtime mode (from `runtime_state` when provided, otherwise from `settings`), model name, base URL, whether the LLM service is reachable, whether the model is available, the `strict_llm` setting, and the latest order ID when `db` is supplied.
    """
    health_status = health if health is not None else LocalLLM(settings).health_check()
    latest_order = db.latest_order() if db is not None else None
    table = Table(title=t("title.system_status"))
    table.add_column(t("label.key"))
    table.add_column(t("label.value"))
    table.add_row(t("label.runtime_dir"), str(settings.runtime_dir))
    table.add_row(
        t("title.runtime_mode"),
        (
            runtime_state.runtime_mode
            if runtime_state is not None
            else settings.runtime_mode
        ),
    )
    table.add_row(t("label.model"), settings.model_name)
    table.add_row(t("label.base_url"), settings.base_url)
    table.add_row(
        t("label.ollama_reachable"),
        t("label.yes") if health_status.service_reachable else t("label.no"),
    )
    table.add_row(
        t("label.model_available"),
        t("label.yes") if health_status.model_available else t("label.no"),
    )
    table.add_row(t("label.strict_llm"), str(settings.strict_llm))
    if db is not None:
        table.add_row(
            t("label.latest_order"),
            latest_order[0] if latest_order is not None else "-",
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
