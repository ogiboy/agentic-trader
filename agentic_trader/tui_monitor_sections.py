from collections.abc import Mapping

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import v1_readiness_payload
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_mapping as _object_mapping
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import read_service_state
from agentic_trader.runtime_status import (
    AgentActivityView,
    RuntimeStatusView,
    build_agent_activity_view,
    build_runtime_status_view,
)
from agentic_trader.schemas import (
    InvestmentPreferences,
    LLMHealthStatus,
    ServiceEvent,
    ServiceStateSnapshot,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import (
    LABEL_AGENT_PROFILE,
    LABEL_AGENT_TONE,
    LABEL_APPROVED,
    LABEL_AVERAGE_PRICE,
    LABEL_BACKGROUND_MODE,
    LABEL_BASE_URL,
    LABEL_BEHAVIOR_PRESET,
    LABEL_BROKER_BACKEND,
    LABEL_BROKER_STATE,
    LABEL_CASH,
    LABEL_COMPLETED_NOTE,
    LABEL_CONTINUOUS,
    LABEL_CREATED,
    LABEL_CURRENCIES,
    LABEL_CURRENT_NOTE,
    LABEL_CURRENT_STAGE,
    LABEL_CURRENT_SYMBOL,
    LABEL_CYCLE,
    LABEL_CYCLE_COUNT,
    LABEL_DRAWDOWN_FROM_PEAK,
    LABEL_EQUITY,
    LABEL_EXCHANGES,
    LABEL_FIELD,
    LABEL_FILLS_TODAY,
    LABEL_GROSS_EXPOSURE,
    LABEL_HEARTBEAT,
    LABEL_HEARTBEAT_AGE,
    LABEL_INTERVAL,
    LABEL_INTERVENTION,
    LABEL_KEY,
    LABEL_KILL_SWITCH,
    LABEL_LARGEST_POSITION,
    LABEL_LAST_COMPLETED_STAGE,
    LABEL_LAST_OUTCOME,
    LABEL_LAST_OUTCOME_TYPE,
    LABEL_LAST_RECORDED_ERROR,
    LABEL_LAST_RECORDED_MESSAGE,
    LABEL_LAST_RECORDED_STATE,
    LABEL_LAST_TERMINAL_AT,
    LABEL_LAST_TERMINAL_STATE,
    LABEL_LATEST_ORDER,
    LABEL_LAUNCH_COUNT,
    LABEL_LEVEL,
    LABEL_LIVE_PROCESS,
    LABEL_LOOKBACK,
    LABEL_MARK_SOURCE,
    LABEL_MARKED_AT,
    LABEL_MARKET_PRICE,
    LABEL_MARKET_VALUE,
    LABEL_MESSAGE,
    LABEL_METRIC,
    LABEL_MODEL,
    LABEL_MODEL_AVAILABLE,
    LABEL_NO,
    LABEL_NOTES,
    LABEL_OBSERVER_MODE,
    LABEL_OLLAMA_REACHABLE,
    LABEL_OPEN_POSITIONS,
    LABEL_OPENED,
    LABEL_PAPER_MARK,
    LABEL_PID,
    LABEL_PNL,
    LABEL_QUANTITY,
    LABEL_REALIZED_PNL,
    LABEL_REGIONS,
    LABEL_RESTART_COUNT,
    LABEL_RISK_PROFILE,
    LABEL_RUN_ID,
    LABEL_RUNTIME,
    LABEL_RUNTIME_DIR,
    LABEL_SECTORS,
    LABEL_SETTING,
    LABEL_SIDE,
    LABEL_STAGE,
    LABEL_STAGE_MESSAGE,
    LABEL_STAGE_STATUS,
    LABEL_STATE,
    LABEL_STATUS,
    LABEL_STATUS_NOTE,
    LABEL_STOP_REQUESTED,
    LABEL_STRICT_LLM,
    LABEL_STRICTNESS,
    LABEL_SYMBOL,
    LABEL_TRADE_STYLE,
    LABEL_TYPE,
    LABEL_UNREALIZED_PNL,
    LABEL_UPDATED,
    LABEL_V1_PAPER_GATE,
    LABEL_VALUE,
    LABEL_WARNINGS,
    LABEL_WATCHED_SYMBOLS,
    LABEL_YES,
    MESSAGE_MARK_TIME_UNAVAILABLE,
    MESSAGE_NO_AGENT_ACTIVITY_RECORDED,
    MESSAGE_NO_LIVE_AGENT_STAGE_EVENTS,
    MESSAGE_NO_RUNS_RECORDED,
    MESSAGE_NO_RUNTIME_EVENTS,
    MESSAGE_NO_RUNTIME_STATE,
    MESSAGE_WAITING_FOR_LAST_OUTCOME,
    TITLE_CURRENT_CYCLE,
    TITLE_DAILY_RISK_REPORT_FOR_DATE,
    TITLE_DECISION_WORKFLOW,
    TITLE_INVESTMENT_PREFERENCES,
    TITLE_PORTFOLIO,
    TITLE_POSITIONS,
    TITLE_RECENT_RUNS,
    TITLE_RUNTIME_EVENTS,
    TITLE_RUNTIME_MODE,
    TITLE_RUNTIME_STATUS,
    TITLE_SYSTEM_STATUS,
    TITLE_TRADE_JOURNAL,
    UI_LIST_SEPARATOR,
)

console = Console()


def _label_line(label: str, value: object) -> str:
    """
    Format a label and value into a compact "label: value" string.

    Parameters:
        label (str): Left-hand label text.
        value (object): Right-hand value; converted to its string representation.

    Returns:
        str: The combined single-line string in the form "label: value".
    """

    return ": ".join((label, str(value)))


def render_preferences(preferences: InvestmentPreferences) -> Table:
    """
    Builds a Rich Table that displays the given investment preferences as labeled rows.

    Parameters:
        preferences (InvestmentPreferences): Preferences to render; list fields are joined with the UI list separator and empty values are shown as "-".

    Returns:
        table (Table): A Rich Table containing rows for regions, exchanges, currencies, sectors, risk profile, trade style, behavior preset, agent profile, agent tone, strictness preset, intervention style, and notes.
    """
    table = Table(title=TITLE_INVESTMENT_PREFERENCES)
    table.add_column(LABEL_SETTING)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_REGIONS, UI_LIST_SEPARATOR.join(preferences.regions) or "-")
    table.add_row(LABEL_EXCHANGES, UI_LIST_SEPARATOR.join(preferences.exchanges) or "-")
    table.add_row(
        LABEL_CURRENCIES, UI_LIST_SEPARATOR.join(preferences.currencies) or "-"
    )
    table.add_row(LABEL_SECTORS, UI_LIST_SEPARATOR.join(preferences.sectors) or "-")
    table.add_row(LABEL_RISK_PROFILE, preferences.risk_profile)
    table.add_row(LABEL_TRADE_STYLE, preferences.trade_style)
    table.add_row(LABEL_BEHAVIOR_PRESET, preferences.behavior_preset)
    table.add_row(LABEL_AGENT_PROFILE, preferences.agent_profile)
    table.add_row(LABEL_AGENT_TONE, preferences.agent_tone)
    table.add_row(LABEL_STRICTNESS, preferences.strictness_preset)
    table.add_row(LABEL_INTERVENTION, preferences.intervention_style)
    table.add_row(LABEL_NOTES, preferences.notes or "-")
    return table


def render_recent_runs(db: TradingDatabase) -> None:
    """
    Render a table of the most recent runs from the trading database to the console.

    If no runs exist, prints a yellow panel titled with the recent runs title indicating that no runs have been recorded.

    Parameters:
        db (TradingDatabase): Database instance used to fetch recent runs (fetches up to 8 entries).
    """
    runs = db.list_recent_runs(limit=8)
    table = Table(title=TITLE_RECENT_RUNS)
    table.add_column(LABEL_RUN_ID)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_INTERVAL)
    table.add_column(LABEL_APPROVED)
    if not runs:
        console.print(
            Panel(
                MESSAGE_NO_RUNS_RECORDED,
                title=TITLE_RECENT_RUNS,
                border_style="yellow",
            )
        )
        return
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    console.print(table)


def recent_runs_table(db: TradingDatabase) -> Table:
    """
    Create a Rich Table showing up to eight recent runs from the database.

    The table has columns "Run ID", "Created", "Symbol", "Interval", and "Approved". If the database has no recent runs, the table contains a single placeholder row with "-" in each column.

    Returns:
        rich.table.Table: The constructed table ready for rendering.
    """
    runs = db.list_recent_runs(limit=8)
    table = Table(title=TITLE_RECENT_RUNS)
    table.add_column(LABEL_RUN_ID)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_INTERVAL)
    table.add_column(LABEL_APPROVED)
    if not runs:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    return table


def trade_journal_table(db: TradingDatabase, *, limit: int = 8) -> Table:
    """
    Builds a Rich Table listing recent trade journal entries.

    Parameters:
        limit (int): Maximum number of journal entries to include.

    Returns:
        table (rich.table.Table): Table with up to `limit` rows and columns for opened time, symbol, journal status, planned side, and realized PnL (realized PnL formatted to two decimal places or `-` when absent).
    """
    entries = db.list_trade_journal(limit=limit)
    table = Table(title=TITLE_TRADE_JOURNAL)
    table.add_column(LABEL_OPENED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_SIDE)
    table.add_column(LABEL_PNL)
    if not entries:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for entry in entries:
        table.add_row(
            entry.opened_at,
            entry.symbol,
            entry.journal_status,
            entry.planned_side,
            f"{entry.realized_pnl:.2f}" if entry.realized_pnl is not None else "-",
        )
    return table


def risk_report_table(db: TradingDatabase) -> Table:
    """
    Builds a Rich Table showing the daily risk report for the report date produced by the database.

    Parameters:
        db (TradingDatabase): Database used to generate the daily risk report.

    Returns:
        table (Table): A Rich Table with "Field" and "Value" columns containing rows for:
            - Equity (formatted to two decimal places)
            - Gross exposure (percentage)
            - Largest position (percentage)
            - Drawdown from peak (percentage)
            - Fills today (integer)
            - Warnings (count of warning entries)
    """
    report = db.build_daily_risk_report()
    table = Table(
        title=TITLE_DAILY_RISK_REPORT_FOR_DATE.format(report_date=report.report_date)
    )
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_EQUITY, f"{report.equity:.2f}")
    table.add_row(LABEL_GROSS_EXPOSURE, f"{report.gross_exposure_pct:.2%}")
    table.add_row(LABEL_LARGEST_POSITION, f"{report.largest_position_pct:.2%}")
    table.add_row(LABEL_DRAWDOWN_FROM_PEAK, f"{report.drawdown_from_peak_pct:.2%}")
    table.add_row(LABEL_FILLS_TODAY, str(report.fills_today))
    table.add_row(LABEL_WARNINGS, str(len(report.warnings)))
    return table


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
    Render a yellow "observer mode" panel indicating a feature is unavailable because the runtime writer owns the database.

    Parameters:
        feature (str): The name or short description of the unavailable feature to display.
        error (str | None): Optional additional error or diagnostic text to include in the panel body.

    Returns:
        Panel: A Rich Panel titled with LABEL_OBSERVER_MODE containing the message about unavailability, optionally followed by the provided error text; the panel uses a yellow border style.
    """
    body = f"{feature} is temporarily unavailable while the runtime writer owns the database."
    if error:
        body += f"\n\n{error}"
    return Panel(body, title=LABEL_OBSERVER_MODE, border_style="yellow")


def render_runtime_state(state: ServiceStateSnapshot | None) -> None:
    """
    Render the runtime status view: either a detailed status table or a placeholder panel when no state is available.

    Parameters:
        state (ServiceStateSnapshot | None): The latest service state snapshot to display. If `None` or if the snapshot contains no recorded state, a yellow panel indicating "No runtime state recorded yet." is printed instead of the table.
    """
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
    """
    Render a list of runtime service events to the console as a table or a notice when no events exist.

    Parameters:
        events (list[ServiceEvent]): Iterable of service event records to display. If empty, a notice panel indicating no recorded events is printed.
    """
    if not events:
        console.print(
            Panel(
                MESSAGE_NO_RUNTIME_EVENTS,
                title=TITLE_RUNTIME_EVENTS,
                border_style="yellow",
            )
        )
        return
    table = Table(title=TITLE_RUNTIME_EVENTS)
    table.add_column("Created")
    table.add_column("Level")
    table.add_column("Type")
    table.add_column("Cycle")
    table.add_column("Symbol")
    for event in events:
        table.add_row(
            event.created_at,
            event.level,
            event.event_type,
            str(event.cycle_count) if event.cycle_count is not None else "-",
            event.symbol or "-",
        )
    console.print(table)


def runtime_events_table(events: list[ServiceEvent]) -> Table:
    """
    Builds a rich Table representing runtime service events.

    Parameters:
        events (list[ServiceEvent]): Sequence of service event records to display. Each record is expected to provide
            `created_at`, `level`, `event_type`, `cycle_count`, and `symbol`.

    Returns:
        Table: A rich Table with the columns "Created", "Level", "Type", "Cycle", and "Symbol". If `events` is empty,
        the table contains a single placeholder row of "-" values; otherwise each event produces one populated row.
    """
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
    """
    Render a decision-workflow table showing agent stages, their statuses, and messages.

    When no live stage statuses are present, the table contains a single placeholder row using MESSAGE_NO_LIVE_AGENT_STAGE_EVENTS.

    Parameters:
        state: Optional service state snapshot used to derive agent activity.
        events: List of service events used to derive agent activity.

    Returns:
        A Rich Table with columns for stage, status, and message; one row per stage or a single placeholder row when empty.
    """
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
    """
    Render a cyan-bordered panel summarizing the current runtime cycle, agent activity, broker gate/readiness, and the most recent outcome.

    Parameters:
        settings (Settings): Application settings used to derive broker and readiness information.
        state (ServiceStateSnapshot | None): Current runtime state snapshot, or `None` when unavailable.
        events (list[ServiceEvent]): Recent runtime events used to build the agent activity view.

    Returns:
        Panel: A Rich Panel containing joined lines for runtime cycle details, agent activity, broker gate/readiness, and last outcome.
    """
    view = build_runtime_status_view(state)
    activity = build_agent_activity_view(state, events)
    broker = broker_runtime_payload(settings)
    readiness = _object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper_operations = _object_mapping(readiness.get("paper_operations"))
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


def runtime_cycle_lines(
    *,
    settings: Settings,
    state: ServiceStateSnapshot | None,
    view: RuntimeStatusView,
) -> list[str]:
    """
    Builds a compact list of "label: value" lines summarizing the current runtime cycle and related configuration.

    Parameters:
        settings (Settings): Global settings; used as a fallback for runtime mode when `state` is None.
        state (ServiceStateSnapshot | None): Runtime writer snapshot (may be None); supplies runtime_mode, symbols, interval, and lookback when available.
        view (RuntimeStatusView): Read-only view of runtime status used to populate runtime state, current symbol, cycle count, and current note.

    Returns:
        list[str]: Lines formatted as `label: value` for runtime state, runtime mode, watched symbols, current symbol, cycle count, interval/lookback, and current note. Missing values are represented by "-".
    """
    return [
        _label_line(LABEL_RUNTIME, view.runtime_state),
        _label_line(
            TITLE_RUNTIME_MODE,
            state.runtime_mode if state is not None else settings.runtime_mode,
        ),
        _label_line(
            LABEL_WATCHED_SYMBOLS,
            (
                UI_LIST_SEPARATOR.join(state.symbols)
                if state is not None and state.symbols
                else "-"
            ),
        ),
        _label_line(
            LABEL_CURRENT_SYMBOL,
            (
                view.state.current_symbol
                if view.state is not None and view.state.current_symbol
                else "-"
            ),
        ),
        _label_line(
            LABEL_CYCLE, view.state.cycle_count if view.state is not None else "-"
        ),
        _label_line(
            f"{LABEL_INTERVAL} / {LABEL_LOOKBACK}",
            (
                f"{state.interval if state is not None and state.interval else '-'} / "
                f"{state.lookback if state is not None and state.lookback else '-'}"
            ),
        ),
        _label_line(
            LABEL_CURRENT_NOTE,
            (
                view.state.message
                if view.state is not None and view.state.message
                else "-"
            ),
        ),
    ]


def agent_activity_lines(activity: AgentActivityView) -> list[str]:
    """
    Builds a list of labeled "label: value" lines summarizing agent activity for display.

    Parameters:
        activity (AgentActivityView): The activity view containing current and last stage data.

    Returns:
        list[str]: A list of strings where each entry is a labeled line for current stage, stage status, stage message, last completed stage, and completed note (using placeholders when values are absent).
    """
    return [
        _label_line(LABEL_CURRENT_STAGE, activity.current_stage or "-"),
        _label_line(LABEL_STAGE_STATUS, activity.current_stage_status or "-"),
        _label_line(
            LABEL_STAGE_MESSAGE,
            activity.current_stage_message or MESSAGE_NO_AGENT_ACTIVITY_RECORDED,
        ),
        _label_line(LABEL_LAST_COMPLETED_STAGE, activity.last_completed_stage or "-"),
        _label_line(LABEL_COMPLETED_NOTE, activity.last_completed_message or "-"),
    ]


def broker_gate_lines(
    *, broker: Mapping[str, object], paper_operations: Mapping[str, object]
) -> list[str]:
    """
    Builds display lines describing broker gate status for the runtime monitor.

    Parameters:
        broker (Mapping[str, object]): Broker runtime payload; expected keys include
            "backend", "state", and "kill_switch_active".
        paper_operations (Mapping[str, object]): V1 paper operations payload; expected
            key "allowed" indicates whether paper operations are permitted.

    Returns:
        list[str]: Four formatted `label: value` strings for broker backend, broker
        state, kill switch ("active" or "inactive"), and V1 paper gate ("allowed" or
        "blocked").
    """
    return [
        _label_line(LABEL_BROKER_BACKEND, broker.get("backend", "-")),
        _label_line(LABEL_BROKER_STATE, broker.get("state", "-")),
        _label_line(
            LABEL_KILL_SWITCH,
            "active" if broker.get("kill_switch_active") else "inactive",
        ),
        _label_line(
            LABEL_V1_PAPER_GATE,
            "allowed" if paper_operations.get("allowed") else "blocked",
        ),
    ]


def last_outcome_lines(activity: AgentActivityView) -> list[str]:
    """
    Builds label/value lines describing the last outcome from an agent activity view.

    Parameters:
        activity (AgentActivityView): Activity view containing `last_outcome_message` and optional `last_outcome_type`.

    Returns:
        list[str]: A list of formatted "label: value" lines. If `last_outcome_message` is present returns lines for outcome type (or "-" when missing) and outcome message; otherwise returns a single line indicating the system is waiting for the last outcome.
    """
    if activity.last_outcome_message is not None:
        return [
            _label_line(LABEL_LAST_OUTCOME_TYPE, activity.last_outcome_type or "-"),
            _label_line(LABEL_LAST_OUTCOME, activity.last_outcome_message),
        ]
    return [_label_line(LABEL_LAST_OUTCOME, MESSAGE_WAITING_FOR_LAST_OUTCOME)]


def runtime_state_table(state: ServiceStateSnapshot | None) -> Table:
    """
    Builds a rich Table summarizing the current runtime service status.

    Parameters:
        state (ServiceStateSnapshot | None): Latest runtime service snapshot or None when no state is recorded.

    Returns:
        Table: A Rich Table with keys and values for runtime properties (runtime state, live process, last recorded state, timestamps, counters, flags, PID, messages, and errors).
    """
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
    """
    Create a key/value table summarizing runtime configuration, model and LLM health, and the latest persisted order when available.

    Parameters:
        settings: Application settings used to read runtime directory, runtime mode, model name, base URL, and strict-LLM flag.
        db: Trading database instance or `None`. When provided, the table includes a "Latest Order" row; when `None`, that row is omitted.
        runtime_state: Optional service state snapshot; when provided its runtime mode is used in preference to settings.runtime_mode.
        health: Optional precomputed LLM health snapshot; when omitted a fresh health check is performed.

    Returns:
        A Rich Table containing the system status rows.
    """
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


def portfolio_renderable(db: TradingDatabase) -> Group:
    """
    Builds a Rich renderable containing a portfolio summary table and a positions table.

    Parameters:
        db (TradingDatabase): Database used to read the account snapshot, user preferences (to derive currency), latest account mark, and current positions.

    Returns:
        Group: A renderable Group containing the portfolio summary table and the positions table.
    """
    snapshot = db.get_account_snapshot()
    preferences = db.load_preferences()
    currency = (preferences.currencies[0] if preferences.currencies else "USD").upper()
    latest_marks = db.list_account_marks(limit=1)
    mark_time = (
        latest_marks[0].created_at if latest_marks else MESSAGE_MARK_TIME_UNAVAILABLE
    )
    mark_source = latest_marks[0].source if latest_marks else "-"
    currency_suffix = " (" + currency + ")"
    paper_mark_suffix = " (" + currency + ", " + LABEL_PAPER_MARK + ")"
    summary = Table(title=TITLE_PORTFOLIO)
    summary.add_column(LABEL_METRIC)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_CASH + currency_suffix, f"{snapshot.cash:.2f}")
    summary.add_row(
        LABEL_MARKET_VALUE + currency_suffix, f"{snapshot.market_value:.2f}"
    )
    summary.add_row(LABEL_EQUITY + currency_suffix, f"{snapshot.equity:.2f}")
    summary.add_row(
        LABEL_REALIZED_PNL + currency_suffix, f"{snapshot.realized_pnl:.2f}"
    )
    summary.add_row(
        LABEL_UNREALIZED_PNL + paper_mark_suffix,
        f"{snapshot.unrealized_pnl:.2f}",
    )
    summary.add_row(LABEL_OPEN_POSITIONS, str(snapshot.open_positions))
    summary.add_row(LABEL_MARKED_AT, mark_time)
    summary.add_row(LABEL_MARK_SOURCE, mark_source)

    positions = db.list_positions()
    positions_table = Table(title=TITLE_POSITIONS)
    positions_table.add_column(LABEL_SYMBOL)
    positions_table.add_column(LABEL_QUANTITY)
    positions_table.add_column(LABEL_AVERAGE_PRICE)
    positions_table.add_column(LABEL_MARKET_PRICE)
    positions_table.add_column(LABEL_MARKET_VALUE)
    positions_table.add_column(LABEL_UNREALIZED_PNL)
    if not positions:
        positions_table.add_row("-", "-", "-", "-", "-", "-")
    else:
        for position in positions:
            positions_table.add_row(
                position.symbol,
                f"{position.quantity:.6f}",
                f"{position.average_price:.4f}",
                f"{position.market_price:.4f}",
                f"{position.market_value:.2f}",
                f"{position.unrealized_pnl:.2f}",
            )
    return Group(summary, positions_table)
