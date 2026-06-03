"""Compatibility exports for terminal status renderers."""

from agentic_trader.tui_modules.status_diagnostics import (
    render_broker_status,
    render_provider_diagnostics,
)
from agentic_trader.tui_modules.status_overview import (
    render_compact_status,
    render_status,
)
from agentic_trader.tui_modules.status_readiness import (
    render_readiness_table,
    render_v1_readiness,
)

__all__ = (
    "render_broker_status",
    "render_compact_status",
    "render_provider_diagnostics",
    "render_readiness_table",
    "render_status",
    "render_v1_readiness",
)
