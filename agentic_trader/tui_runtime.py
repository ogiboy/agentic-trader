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
from agentic_trader.tui_common import banner, console, open_db, split_csv, style_key
from agentic_trader.tui_monitor import run_live_monitor
from agentic_trader.tui_monitor_sections import safe_open_read_db
from agentic_trader.tui_status import (
    render_broker_status,
    render_provider_diagnostics,
    render_status,
    render_v1_readiness,
)
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_KEY,
    LABEL_OBSERVER_MODE,
    LABEL_STOP_REQUESTED,
    MENU_ACTION_BACK,
    MENU_ACTION_BROKER_STATUS,
    MENU_ACTION_DOCTOR_SYSTEM_CHECKS,
    MENU_ACTION_OPEN_LIVE_MONITOR,
    MENU_ACTION_PROVIDER_DIAGNOSTICS,
    MENU_ACTION_REQUEST_ORCHESTRATOR_STOP,
    MENU_ACTION_START_ONE_STRICT_AGENT_CYCLE,
    MENU_ACTION_START_ORCHESTRATOR_SERVICE,
    MENU_ACTION_V1_READINESS_GATES,
    MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
    MESSAGE_FINAL_STAGE_UPDATE,
    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE,
    MESSAGE_PREPARING_SYMBOL,
    MESSAGE_SERVICE_SPAWNED_BACKGROUND,
    MESSAGE_SERVICE_STOP_REQUESTED,
    MESSAGE_STAGE_UPDATE,
    MESSAGE_STALE_RUNTIME_PID,
    PROMPT_CONTINUE,
    PROMPT_CONTINUOUS_MODE,
    PROMPT_MAX_CYCLES,
    PROMPT_OPEN_LIVE_MONITOR_NOW,
    PROMPT_POLL_INTERVAL_SECONDS,
    PROMPT_REFRESH_SECONDS,
    PROMPT_SELECT_ACTION,
    STYLE_KEY_COLUMN,
    TITLE_NOT_RUNNING,
    TITLE_RUN_COMPLETED,
    TITLE_RUNTIME_CONTROL,
    TITLE_SERVICE_SPAWNED,
    TITLE_STALE_RUNTIME,
)
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
    latest_message = MESSAGE_PREPARING_SYMBOL.format(symbol=symbol)
    with console.status(style_key(latest_message), spinner="dots") as status:

        def progress(
            stage: str,
            event: str,
            message: str,
            current_status: Status = status,
        ) -> None:
            del event
            nonlocal latest_message
            latest_message = MESSAGE_STAGE_UPDATE.format(stage=stage, message=message)
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
            MESSAGE_FINAL_STAGE_UPDATE.format(
                latest_message=latest_message,
                artifacts_json=json.dumps(artifacts.model_dump(mode="json"), indent=2),
            ),
            title=TITLE_RUN_COMPLETED.format(symbol=symbol, order_id=order_id),
            border_style="green",
        )
    )


def launch_service(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
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
            MESSAGE_SERVICE_SPAWNED_BACKGROUND.format(pid=pid),
            title=TITLE_SERVICE_SPAWNED,
            border_style="green",
        )
    )
    open_live_monitor_if_requested(settings)


def prompt_service_launch_options(settings: Settings) -> tuple[bool, int, int | None]:
    continuous = Confirm.ask(PROMPT_CONTINUOUS_MODE, default=False)
    poll_seconds = IntPrompt.ask(
        PROMPT_POLL_INTERVAL_SECONDS,
        default=settings.default_poll_seconds,
    )
    if not continuous:
        return continuous, poll_seconds, None

    max_cycles_input = Prompt.ask(PROMPT_MAX_CYCLES, default="")
    max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    return continuous, poll_seconds, max_cycles


def open_live_monitor_if_requested(settings: Settings) -> None:
    if Confirm.ask(PROMPT_OPEN_LIVE_MONITOR_NOW, default=True):
        run_live_monitor(settings, refresh_seconds=1.0)


def runtime_control_table() -> Table:
    table = Table(title=TITLE_RUNTIME_CONTROL)
    table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_ACTION)
    for key, action in (
        ("1", MENU_ACTION_DOCTOR_SYSTEM_CHECKS),
        ("2", MENU_ACTION_START_ONE_STRICT_AGENT_CYCLE),
        ("3", MENU_ACTION_START_ORCHESTRATOR_SERVICE),
        ("4", MENU_ACTION_REQUEST_ORCHESTRATOR_STOP),
        ("5", MENU_ACTION_OPEN_LIVE_MONITOR),
        ("6", MENU_ACTION_PROVIDER_DIAGNOSTICS),
        ("7", MENU_ACTION_V1_READINESS_GATES),
        ("8", MENU_ACTION_BROKER_STATUS),
        ("9", MENU_ACTION_BACK),
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
    db = safe_open_read_db(settings)
    try:
        if db is None:
            console.print(
                Panel(
                    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE.format(error="-"),
                    title=LABEL_OBSERVER_MODE,
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
    state = read_service_state(settings)
    if state is None or state.pid is None:
        console.print(
            Panel(
                MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
                title=TITLE_NOT_RUNNING,
                border_style="yellow",
            )
        )
        return
    if not is_process_alive(state.pid):
        console.print(
            Panel(
                MESSAGE_STALE_RUNTIME_PID.format(pid=state.pid),
                title=TITLE_STALE_RUNTIME,
                border_style="yellow",
            )
        )
        return

    request_stop(settings)
    persist_stop_request(settings)
    console.print(
        Panel(
            MESSAGE_SERVICE_STOP_REQUESTED.format(pid=state.pid),
            title=LABEL_STOP_REQUESTED,
            border_style="yellow",
        )
    )


def runtime_monitor_action(settings: Settings) -> None:
    try:
        refresh_seconds = float(Prompt.ask(PROMPT_REFRESH_SECONDS, default="1.0"))
        if refresh_seconds <= 0.0:
            refresh_seconds = 1.0
    except ValueError:
        refresh_seconds = 1.0
    run_live_monitor(settings, refresh_seconds=refresh_seconds)


def runtime_menu(settings: Settings) -> None:
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
            PROMPT_SELECT_ACTION,
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )
        if choice == "9":
            return
        actions[choice](settings)
        Prompt.ask(PROMPT_CONTINUE, default="")
