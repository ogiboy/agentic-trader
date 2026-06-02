from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.prompt import Prompt

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.ui_text import (
    MESSAGE_NO_ACTION_SELECTED,
    PROMPT_SELECT_ACTION,
    TITLE_EXIT,
    TITLE_WEB_GUI_START_FAILED,
)


SettingsProvider = Callable[[], Settings]
LauncherStatusProvider = Callable[[Settings], Any]
StartWebGui = Callable[[Settings], Any]
RenderPayload = Callable[[dict[str, object]], None]
RenderHealthPanel = Callable[..., object]


def run_operator_launcher(
    *,
    settings_provider: SettingsProvider,
    launcher_status_provider: LauncherStatusProvider,
    start_webgui: StartWebGui,
    render_launcher_status: RenderPayload,
    render_webgui_status: RenderPayload,
    render_health_panel: RenderHealthPanel,
) -> None:
    """Interactive no-argument product launcher."""

    settings = settings_provider()
    while True:
        payload = launcher_status_provider(settings).model_dump(mode="json")
        render_launcher_status(payload)
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION,
            choices=["1", "2", "3", "4", "8", "q"],
            default="2",
        )
        if choice == "1":
            _start_webgui_from_launcher(
                settings=settings,
                start_webgui=start_webgui,
                render_webgui_status=render_webgui_status,
                render_health_panel=render_health_panel,
            )
            return
        if choice == "2":
            from agentic_trader.tui import run_main_menu

            run_main_menu()
            return
        if choice == "3":
            continue
        break
    console.print(
        render_health_panel(
            TITLE_EXIT,
            MESSAGE_NO_ACTION_SELECTED,
            border_style="blue",
        )
    )


def _start_webgui_from_launcher(
    *,
    settings: Settings,
    start_webgui: StartWebGui,
    render_webgui_status: RenderPayload,
    render_health_panel: RenderHealthPanel,
) -> None:
    try:
        status = start_webgui(settings)
    except Exception as exc:
        from agentic_trader.security import redact_sensitive_text

        console.print(
            render_health_panel(
                TITLE_WEB_GUI_START_FAILED,
                redact_sensitive_text(exc, max_length=240),
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc
    render_webgui_status(status.model_dump(mode="json"))
