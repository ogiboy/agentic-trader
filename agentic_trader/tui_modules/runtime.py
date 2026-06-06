import json
from collections.abc import Sequence

from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.status import Status
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import read_service_state, request_stop
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.tui_modules.common import (
    banner,
    console,
    open_db,
    split_csv,
    style_key,
)
from agentic_trader.tui_modules.monitor import run_live_monitor
from agentic_trader.tui_modules.monitor_runtime import safe_open_read_db
from agentic_trader.tui_modules.status import (
    render_broker_status,
    render_provider_diagnostics,
    render_status,
    render_v1_readiness,
)
from agentic_trader.ui_text import t as ui_t
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, start_background_service


def strict_one_shot(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    ensure_llm_ready(settings)
    for symbol in symbols:
        run_one_shot_symbol(settings, symbol, interval, lookback)


def run_one_shot_symbol(
    settings: Settings, symbol: str, interval: str, lookback: str
) -> None:
    """
    Run a single one-shot trading cycle for the given symbol, stream stage updates to the console, persist the run results, and display a final result panel.
    
    Parameters:
    	settings (Settings): Runtime configuration and services for executing the cycle.
    	symbol (str): Market symbol/ticker to run the cycle for (e.g., "AAPL" or "BTC-USD").
    	interval (str): Data interval to use for the run (e.g., "1d", "1h").
    	lookback (str): Lookback window used for data selection (e.g., "180d").
    """
    latest_message = ui_t("message.preparing_symbol").format(symbol=symbol)
    with console.status(style_key(latest_message), spinner="dots") as status:

        def progress(
            stage: str,
            event: str,
            message: str,
            current_status: Status = status,
        ) -> None:
            """
            Update the runtime progress message and refresh the Rich status display.
            
            Parameters:
            	stage (str): Name of the current stage.
            	event (str): Ignored; provided for callback compatibility.
            	message (str): Human-readable stage message to display.
            	current_status (Status): Rich `Status` instance to update (defaults to module `status`).
            """
            del event
            nonlocal latest_message
            latest_message = ui_t("message.stage_update").format(
                stage=stage, message=message
            )
            current_status.update(style_key(latest_message))

        artifacts = run_once(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            allow_fallback=False,
            progress_callback=progress,
        )

    order_id = persist_run(settings=settings, artifacts=artifacts)
    console.print(
        Panel(
            ui_t("message.final_stage_update").format(
                latest_message=latest_message,
                artifacts_json=json.dumps(artifacts.model_dump(mode="json"), indent=2),
            ),
            title=ui_t("title.run_completed").format(symbol=symbol, order_id=order_id),
            border_style="green",
        )
    )


def launch_service(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    """
    Start the orchestrator as a background service for the given symbols and optionally open a live monitor.
    
    Prompts the user for service launch options, starts a background orchestrator configured with the provided symbols, interval, and lookback window, displays the spawned process ID, and opens the live monitor if the user requests it.
    
    Parameters:
        settings (Settings): Application runtime configuration and environment.
        symbols (Sequence[str]): Symbols to run the service for (e.g., ["AAPL", "MSFT"]).
        interval (str): Time interval for data/candles (e.g., "1d", "1h").
        lookback (str): Lookback window for historical data (e.g., "180d").
    """
    continuous, poll_seconds, max_cycles = prompt_service_launch_options(settings)
    pid = start_background_service(
        settings=settings,
        symbols=list(symbols),
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    console.print(
        Panel(
            ui_t("message.service_spawned_background").format(pid=pid),
            title=ui_t("title.service_spawned"),
            border_style="green",
        )
    )
    open_live_monitor_if_requested(settings)


def prompt_service_launch_options(settings: Settings) -> tuple[bool, int, int | None]:
    """
    Prompt the user for service launch options and return the chosen control parameters.
    
    Parameters:
        settings (Settings): Application settings; `settings.default_poll_seconds` is used as the default poll interval.
    
    Returns:
        tuple[bool, int, int | None]: A tuple (continuous, poll_seconds, max_cycles) where
            - `continuous` is True if continuous mode was selected,
            - `poll_seconds` is the polling interval in seconds,
            - `max_cycles` is the parsed maximum cycle count when `continuous` is True, or `None` if not set.
    """
    continuous = Confirm.ask(ui_t("prompt.continuous_mode"), default=False)
    poll_seconds = IntPrompt.ask(
        ui_t("prompt.poll_interval_seconds"),
        default=settings.default_poll_seconds,
    )
    if not continuous:
        return continuous, poll_seconds, None

    max_cycles_input = Prompt.ask(ui_t("prompt.max_cycles"), default="")
    max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    return continuous, poll_seconds, max_cycles


def open_live_monitor_if_requested(settings: Settings) -> None:
    """
    Prompt the user to open the live monitor and launch it if confirmed.
    
    Parameters:
        settings (Settings): Application settings used to configure and run the live monitor.
    """
    if Confirm.ask(ui_t("prompt.open_live_monitor_now"), default=True):
        run_live_monitor(settings, refresh_seconds=1.0)


def runtime_control_table() -> Table:
    """
    Builds a Rich Table containing the runtime control menu keys and corresponding actions.
    
    The table has two columns ("key" and "action") using translated labels and styles, and is populated with rows "1" through "9" that map to the available runtime commands (system checks, one-shot cycle, orchestrator start/stop, live monitor, provider diagnostics, v1 readiness, broker status, and back).
    
    Returns:
        Table: The populated Rich Table ready for rendering.
    """
    table = Table(title=ui_t("title.runtime_control"))
    table.add_column(ui_t("label.key"), style=ui_t("style.key_column"))
    table.add_column(ui_t("label.action"))
    for key, action in (
        ("1", ui_t("menu.action_doctor_system_checks")),
        ("2", ui_t("menu.action_start_one_strict_agent_cycle")),
        ("3", ui_t("menu.action_start_orchestrator_service")),
        ("4", ui_t("menu.action_request_orchestrator_stop")),
        ("5", ui_t("menu.action_open_live_monitor")),
        ("6", ui_t("menu.action_provider_diagnostics")),
        ("7", ui_t("menu.action_v1_readiness_gates")),
        ("8", ui_t("menu.action_broker_status")),
        ("9", ui_t("menu.action_back")),
    ):
        table.add_row(key, action)
    return table


def runtime_status_action(settings: Settings) -> None:
    db = safe_open_read_db(settings)
    try:
        render_status(settings, db)
    finally:
        if db is not None:
            db.close()


def load_runtime_preferences(settings: Settings) -> InvestmentPreferences | None:
    """
    Load investment preferences from the runtime database, or show an observer-mode warning if the database is unavailable.
    
    If the runtime database cannot be opened, prints a yellow observer-mode warning panel and returns `None`.
    
    Returns:
        InvestmentPreferences: The preferences loaded from the runtime database.
        `None` if the database could not be opened.
    """
    db = safe_open_read_db(settings)
    try:
        if db is None:
            console.print(
                Panel(
                    ui_t("message.preferences_temporarily_unavailable").format(
                        error="-"
                    ),
                    title=ui_t("label.observer_mode"),
                    border_style="yellow",
                )
            )
            return None
        return db.load_preferences()
    finally:
        if db is not None:
            db.close()


def runtime_one_shot_action(settings: Settings) -> None:
    prefs = load_runtime_preferences(settings)
    if prefs is None:
        return
    default_symbols = "AAPL,MSFT" if "US" in prefs.regions else "BTC-USD"
    symbols = split_csv(Prompt.ask("Symbols", default=default_symbols))
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    strict_one_shot(settings, symbols, interval, lookback)


def runtime_launch_action(settings: Settings) -> None:
    symbols = split_csv(Prompt.ask("Symbols", default="AAPL,MSFT"))
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    launch_service(settings, symbols, interval, lookback)


def persist_stop_request(settings: Settings) -> None:
    try:
        db = open_db(settings, read_only=False)
        try:
            db.request_stop_service()
        finally:
            db.close()
    except Exception:
        pass


def runtime_stop_action(settings: Settings) -> None:
    """
    Check the running background service and request it to stop if active.
    
    If no service is recorded or the recorded PID is missing, prints a warning panel indicating the service is not active.
    If the recorded PID exists but the process is not alive, prints a warning panel about the stale runtime PID (includes the PID).
    If the process is alive, sends an in-process stop request, persists the stop request to the runtime database, and prints a confirmation panel including the PID.
    
    Parameters:
        settings (Settings): Runtime configuration/context used to read service state and persist the stop request.
    """
    state = read_service_state(settings)
    if state is None or state.pid is None:
        console.print(
            Panel(
                ui_t("message.background_service_not_active"),
                title=ui_t("title.not_running"),
                border_style="yellow",
            )
        )
        return
    if not is_process_alive(state.pid):
        console.print(
            Panel(
                ui_t("message.stale_runtime_pid").format(pid=state.pid),
                title=ui_t("title.stale_runtime"),
                border_style="yellow",
            )
        )
        return

    request_stop(settings)
    persist_stop_request(settings)
    console.print(
        Panel(
            ui_t("message.service_stop_requested").format(pid=state.pid),
            title=ui_t("label.stop_requested"),
            border_style="yellow",
        )
    )


def runtime_monitor_action(settings: Settings) -> None:
    """
    Prompt the user for a monitor refresh interval (in seconds) and start the live monitor.
    
    Prompts for a numeric refresh interval, coerces the input to a float, uses 1.0 if the value is less than or equal to 0 or cannot be parsed, and then calls the live monitor with the resolved interval.
    """
    try:
        refresh_seconds = float(
            Prompt.ask(ui_t("prompt.refresh_seconds"), default="1.0")
        )
        if refresh_seconds <= 0.0:
            refresh_seconds = 1.0
    except ValueError:
        refresh_seconds = 1.0
    run_live_monitor(settings, refresh_seconds=refresh_seconds)


def runtime_menu(settings: Settings) -> None:
    """
    Show an interactive runtime control menu and dispatch the selected runtime action.
    
    Displays the runtime control table, prompts the user to choose an action, invokes the corresponding handler with `settings`, and repeats until the user selects the "back" option (choice "9").
    
    Parameters:
        settings (Settings): Application settings and context passed to the selected runtime action handlers.
    """
    actions = {
        "1": runtime_status_action,
        "2": runtime_one_shot_action,
        "3": runtime_launch_action,
        "4": runtime_stop_action,
        "5": runtime_monitor_action,
        "6": render_provider_diagnostics,
        "7": render_v1_readiness,
        "8": render_broker_status,
    }
    while True:
        console.clear()
        console.print(banner())
        console.print(runtime_control_table())
        choice = Prompt.ask(
            ui_t("prompt.select_action"),
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )
        if choice == "9":
            return
        actions[choice](settings)
        Prompt.ask(ui_t("prompt.continue"), default="")
