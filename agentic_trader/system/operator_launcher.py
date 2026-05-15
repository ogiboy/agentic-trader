"""Primary operator launcher contracts.

The no-argument `agentic-trader` entrypoint should feel like an application
launcher, while all explicit subcommands continue to behave like normal CLI
commands. This module keeps default runtime/WebGUI choices out of the giant CLI
module and makes the launch plan testable.
"""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import read_service_state
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.system.camofox_service import CamofoxServiceStatus, build_camofox_service_status
from agentic_trader.system.model_service import ModelServiceStatus, build_model_service_status
from agentic_trader.system.setup import SetupStatus, build_setup_status
from agentic_trader.system.webgui_service import (
    WebGUIServiceStatus,
    build_webgui_service_status,
    start_webgui_service,
)
from agentic_trader.workflows.service import ensure_llm_ready, start_background_service

OperatorLaunchAction = Literal[
    "webgui",
    "daemon",
    "tui",
    "rich_menu",
    "model_service",
    "setup_status",
    "exit",
]

DEFAULT_OPERATOR_SYMBOLS = ("AAPL", "MSFT")
DEFAULT_OPERATOR_INTERVAL = "1d"
DEFAULT_OPERATOR_LOOKBACK = "180d"


@dataclass(frozen=True)
class RuntimeLaunchPlan:
    """Default background runtime plan used by the operator launcher."""

    symbols: tuple[str, ...] = DEFAULT_OPERATOR_SYMBOLS
    interval: str = DEFAULT_OPERATOR_INTERVAL
    lookback: str = DEFAULT_OPERATOR_LOOKBACK
    continuous: bool = True


class OperatorLauncherStatus(BaseModel):
    """Read-only status shown by the no-argument app launcher."""

    runtime_active: bool
    runtime_state: str
    runtime_pid: int | None = None
    runtime_symbols: list[str] = Field(default_factory=list)
    runtime_interval: str | None = None
    runtime_lookback: str | None = None
    setup: SetupStatus
    model_service: ModelServiceStatus
    camofox_service: CamofoxServiceStatus
    webgui_service: WebGUIServiceStatus
    default_runtime_plan: dict[str, object]


def build_operator_launcher_status(settings: Settings) -> OperatorLauncherStatus:
    """Build the status payload used by the primary launcher."""

    state = read_service_state(settings)
    runtime_active = bool(state is not None and state.pid is not None and is_process_alive(state.pid))
    plan = RuntimeLaunchPlan()
    return OperatorLauncherStatus(
        runtime_active=runtime_active,
        runtime_state=state.state if state is not None else "not_recorded",
        runtime_pid=state.pid if state is not None else None,
        runtime_symbols=list(state.symbols) if state is not None else [],
        runtime_interval=state.interval if state is not None else None,
        runtime_lookback=state.lookback if state is not None else None,
        setup=build_setup_status(settings),
        model_service=build_model_service_status(settings),
        camofox_service=build_camofox_service_status(settings),
        webgui_service=build_webgui_service_status(settings),
        default_runtime_plan={
            "symbols": list(plan.symbols),
            "interval": plan.interval,
            "lookback": plan.lookback,
            "continuous": plan.continuous,
            "poll_seconds": settings.default_poll_seconds,
        },
    )


def start_default_background_runtime(settings: Settings) -> int:
    """Start the default background runtime only after the strict LLM gate passes."""

    plan = RuntimeLaunchPlan()
    ensure_llm_ready(settings)
    return start_background_service(
        settings=settings,
        symbols=list(plan.symbols),
        interval=plan.interval,
        lookback=plan.lookback,
        poll_seconds=settings.default_poll_seconds,
        continuous=plan.continuous,
        max_cycles=None,
    )


def start_operator_webgui(
    settings: Settings,
    *,
    open_browser: bool = True,
) -> WebGUIServiceStatus:
    """Start the local Web GUI and optionally ask the OS to open it."""

    status = start_webgui_service(settings)
    if open_browser and status.url:
        webbrowser.open(status.url)
    return status
