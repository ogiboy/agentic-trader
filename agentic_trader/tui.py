"""Terminal control-room facade.

The feature implementation lives under :mod:`agentic_trader.tui_modules`.
This module keeps the legacy import surface stable for tests, CLI commands,
and operators who import TUI helpers directly.
"""

from __future__ import annotations

from agentic_trader.config import get_settings as get_settings
from agentic_trader.llm.client import LocalLLM as LocalLLM
from agentic_trader.tui_modules.common import TuiMenuAction as TuiMenuAction
from agentic_trader.tui_modules.common import banner as banner
from agentic_trader.tui_modules.common import console as console
from agentic_trader.tui_modules.common import exit_cleanly as exit_cleanly
from agentic_trader.tui_modules.common import menu_table as menu_table
from agentic_trader.tui_modules.common import split_csv as split_csv
from agentic_trader.tui_modules.common import style_key as style_key
from agentic_trader.tui_modules.main_menu import TuiMainMenuAction as TuiMainMenuAction
from agentic_trader.tui_modules.main_menu import main_menu_actions as main_menu_actions
from agentic_trader.tui_modules.main_menu import main_menu_table as main_menu_table
from agentic_trader.tui_modules.main_menu import (
    render_main_status as render_main_status,
)
from agentic_trader.tui_modules.main_menu import run_main_menu as _run_main_menu
from agentic_trader.tui_modules.main_menu import (
    run_main_menu_action as run_main_menu_action,
)
from agentic_trader.tui_modules.monitor import (
    build_monitor_renderable as build_monitor_renderable,
)
from agentic_trader.tui_modules.monitor import run_live_monitor as run_live_monitor
from agentic_trader.tui_modules.monitor_lines import (
    agent_activity_lines as agent_activity_lines,
)
from agentic_trader.tui_modules.monitor_lines import (
    broker_gate_lines as broker_gate_lines,
)
from agentic_trader.tui_modules.monitor_lines import (
    last_outcome_lines as last_outcome_lines,
)
from agentic_trader.tui_modules.monitor_lines import (
    runtime_cycle_lines as runtime_cycle_lines,
)
from agentic_trader.tui_modules.monitor_runtime import (
    agent_activity_table as agent_activity_table,
)
from agentic_trader.tui_modules.monitor_runtime import (
    runtime_state_table as runtime_state_table,
)
from agentic_trader.tui_modules.monitor_runtime import (
    system_status_table as system_status_table,
)
from agentic_trader.tui_modules.research import (
    memory_explorer_table as memory_explorer_table,
)
from agentic_trader.tui_modules.status import (
    render_compact_status as render_compact_status,
)
from agentic_trader.tui_modules.status import render_status as render_status

__all__ = [
    "LocalLLM",
    "TuiMainMenuAction",
    "TuiMenuAction",
    "agent_activity_lines",
    "agent_activity_table",
    "banner",
    "broker_gate_lines",
    "build_monitor_renderable",
    "console",
    "exit_cleanly",
    "get_settings",
    "last_outcome_lines",
    "main_menu_actions",
    "main_menu_table",
    "memory_explorer_table",
    "menu_table",
    "render_compact_status",
    "render_main_status",
    "render_status",
    "run_live_monitor",
    "run_main_menu",
    "run_main_menu_action",
    "runtime_cycle_lines",
    "runtime_state_table",
    "split_csv",
    "style_key",
    "system_status_table",
]


def run_main_menu() -> None:
    _run_main_menu(settings_provider=get_settings)
