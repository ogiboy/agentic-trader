import time

from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import read_service_events, read_service_state
from agentic_trader.schemas import (
    LLMHealthStatus,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_monitor_sections import (
    _agent_activity_table,
    _current_activity_panel,
    _observer_mode_panel,
    _portfolio_renderable,
    _recent_runs_table,
    _render_preferences,
    _risk_report_table,
    _runtime_events_table,
    _runtime_state_table,
    _safe_open_read_db,
    _system_status_table,
    _trade_journal_table,
)
from agentic_trader.ui_text import (
    MESSAGE_MONITOR_RETURN_SHORTCUT,
    STYLE_KEY_COLUMN,
)

console = Console()




def build_monitor_renderable(
    settings: Settings,
    db: TradingDatabase | None = None,
    *,
    health: LLMHealthStatus | None = None,
) -> Group:
    """
    Assembles the live-monitor UI as a Rich Group of panels and tables.

    Attempts a safe read-only database open when `db` is None; database-backed panels show actual data when a readable DB is available and show observer-mode placeholders otherwise.

    Parameters:
        settings (Settings): Application settings used to read runtime state and events.
        db (TradingDatabase | None): Optional database connection. If None, a safe read-only open is attempted and panels that require DB data will fall back to observer-mode when unavailable.
        health (LLMHealthStatus | None): Optional cached LLM health information to display in the system status panel; when omitted the system status panel may perform its own health check.

    Returns:
        Group: A rich.Group containing the assembled header, activity panels, runtime/system status, preferences/portfolio, recent runs/trade journal, runtime events, and risk report.
    """
    db = db if db is not None else _safe_open_read_db(settings)
    runtime_state = read_service_state(settings)
    events = read_service_events(settings, limit=20)
    header = Panel(
        Text("Agentic Trader Live Monitor", style=STYLE_KEY_COLUMN),
        subtitle=MESSAGE_MONITOR_RETURN_SHORTCUT,
        border_style="bright_blue",
    )
    top = Columns(
        [
            _current_activity_panel(settings, runtime_state, events),
            Panel(
                _agent_activity_table(runtime_state, events),
                border_style="bright_magenta",
            ),
        ],
        equal=True,
        expand=True,
    )
    middle = Columns(
        [
            Panel(_runtime_state_table(runtime_state), border_style="magenta"),
            Panel(
                _system_status_table(
                    settings,
                    db,
                    runtime_state=runtime_state,
                    health=health,
                ),
                border_style="cyan",
            ),
        ],
        equal=True,
        expand=True,
    )
    bottom = Columns(
        [
            (
                Panel(_render_preferences(db.load_preferences()), border_style="green")
                if db is not None
                else _observer_mode_panel("Preferences")
            ),
            (
                Panel(_portfolio_renderable(db), border_style="yellow")
                if db is not None
                else _observer_mode_panel("Portfolio")
            ),
        ],
        equal=True,
        expand=True,
    )
    footer = Columns(
        [
            (
                Panel(
                    Group(_recent_runs_table(db), _trade_journal_table(db, limit=5)),
                    border_style="white",
                )
                if db is not None
                else _observer_mode_panel("Run review and trade journal")
            ),
            Panel(_runtime_events_table(events), border_style="bright_blue"),
        ],
        equal=True,
        expand=True,
    )
    extra = (
        Panel(_risk_report_table(db), border_style="red")
        if db is not None
        else _observer_mode_panel("Risk report")
    )
    return Group(header, top, middle, bottom, footer, extra)


def run_live_monitor(
    settings: Settings,
    db: TradingDatabase | None = None,
    *,
    refresh_seconds: float = 1.0,
) -> None:
    """
    Launch a live terminal monitor that renders runtime, portfolio, and system views and updates periodically.

    Runs a rich Live rendering loop that refreshes the UI every `refresh_seconds`, polling LLM health approximately every 30 seconds and updating the display accordingly. The monitor uses `settings` to build views and, if provided, reads DB-backed panels from `db`. The loop continues until interrupted (KeyboardInterrupt).

    Parameters:
        settings (Settings): Application settings used to build monitor renderables and perform health checks.
        db (TradingDatabase | None): Optional read-only database used to populate portfolio and run/event panels; when None a safe read attempt may be performed internally.
        refresh_seconds (float): Seconds to sleep between UI updates (controls update frequency).
    """
    health = LocalLLM(settings).health_check()
    last_health_refresh = time.monotonic()
    with Live(
        build_monitor_renderable(settings, db, health=health),
        console=console,
        refresh_per_second=max(
            1, int(1 / refresh_seconds) if refresh_seconds < 1 else 1
        ),
        screen=True,
    ) as live:
        try:
            while True:
                if time.monotonic() - last_health_refresh >= 30:
                    health = LocalLLM(settings).health_check()
                    last_health_refresh = time.monotonic()
                live.update(build_monitor_renderable(settings, db, health=health))
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            return
