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
    latest_message = ui_t("message.preparing_symbol").format(symbol=symbol)
    with console.status(style_key(latest_message), spinner="dots") as status:

        def progress(
            stage: str,
            event: str,
            message: str,
            current_status: Status = status,
        ) -> None:
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
    continuous = Confirm.ask(ui_t("prompt.continuous_mode"), default=False)
    poll_seconds = IntPrompt.ask(
        ui_t("prompt.poll_interval_seconds"),
        default=settings.default_poll_seconds,
    )
    if not continuous:
        return continuous, poll_seconds, None

    max_cycles_input = Prompt.ask(ui_t("prompt.max_cycles"), default="")
    max_cycles = None
    if max_cycles_input.strip():
        try:
            parsed_max_cycles = int(max_cycles_input)
            if parsed_max_cycles >= 1:
                max_cycles = parsed_max_cycles
            else:
                console.print(
                    Panel(
                        ui_t("message.invalid_max_cycles_input").format(
                            value=max_cycles_input
                        ),
                        border_style="yellow",
                    )
                )
        except ValueError:
            console.print(
                Panel(
                    ui_t("message.invalid_max_cycles_input").format(
                        value=max_cycles_input
                    ),
                    border_style="yellow",
                )
            )
    return continuous, poll_seconds, max_cycles


def open_live_monitor_if_requested(settings: Settings) -> None:
    if Confirm.ask(ui_t("prompt.open_live_monitor_now"), default=True):
        run_live_monitor(settings, refresh_seconds=1.0)


def runtime_control_table() -> Table:
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
