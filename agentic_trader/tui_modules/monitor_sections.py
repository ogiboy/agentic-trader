"""Compatibility exports for terminal monitor helpers.

Concrete implementations live in focused monitor modules so rendering tables,
runtime panels, and compact status-line formatting can evolve independently.
"""

from agentic_trader.tui_modules.monitor_lines import (
    agent_activity_lines,
    broker_gate_lines,
    last_outcome_lines,
    runtime_cycle_lines,
)
from agentic_trader.tui_modules.monitor_runtime import (
    agent_activity_table,
    current_activity_panel,
    observer_mode_panel,
    render_runtime_events,
    render_runtime_state,
    runtime_events_table,
    runtime_state_table,
    safe_open_read_db,
    system_status_table,
)
from agentic_trader.tui_modules.monitor_tables import (
    portfolio_renderable,
    recent_runs_table,
    render_preferences,
    render_recent_runs,
    risk_report_table,
    trade_journal_table,
)

__all__ = (
    "agent_activity_lines",
    "agent_activity_table",
    "broker_gate_lines",
    "current_activity_panel",
    "last_outcome_lines",
    "observer_mode_panel",
    "portfolio_renderable",
    "recent_runs_table",
    "render_preferences",
    "render_recent_runs",
    "render_runtime_events",
    "render_runtime_state",
    "risk_report_table",
    "runtime_cycle_lines",
    "runtime_events_table",
    "runtime_state_table",
    "safe_open_read_db",
    "system_status_table",
    "trade_journal_table",
)
