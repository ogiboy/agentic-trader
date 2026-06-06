from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.prompt import Prompt

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.ui_text import t as ui_t

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
    """
    Present an interactive launcher UI that displays current launcher status and prompts the user to select an action.
    
    Parameters:
        settings_provider (SettingsProvider): Callable that returns runtime settings.
        launcher_status_provider (LauncherStatusProvider): Callable that produces launcher status data given settings; its result will be converted to JSON for rendering.
        start_webgui (StartWebGui): Callable used to start the web GUI when the corresponding action is selected.
        render_launcher_status (RenderPayload): Callable that renders the launcher status payload.
        render_webgui_status (RenderPayload): Callable that renders the web GUI status payload returned by `start_webgui`.
        render_health_panel (RenderHealthPanel): Callable used to build/render health panel messages (used for exit and error reporting).
    """

    settings = settings_provider()
    while True:
        payload = launcher_status_provider(settings).model_dump(mode="json")
        render_launcher_status(payload)
        choice = Prompt.ask(
            ui_t("prompt.select_action"),
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
            ui_t("title.exit"),
            ui_t("message.no_action_selected"),
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
    """
    Attempt to start the web GUI and render either its status or an error health panel.
    
    Parameters:
        settings (Settings): Runtime settings passed to the web GUI starter.
        start_webgui (StartWebGui): Callable that starts the web GUI and returns a status model.
        render_webgui_status (RenderPayload): Callable to render the web GUI status payload.
        render_health_panel (RenderHealthPanel): Callable to render a health panel (title, message, ...).
    
    Raises:
        typer.Exit: Raised with code 1 if starting the web GUI fails; the original exception is chained.
    """
    try:
        status = start_webgui(settings)
    except Exception as exc:
        from agentic_trader.security import redact_sensitive_text

        console.print(
            render_health_panel(
                ui_t("title.web_gui_start_failed"),
                redact_sensitive_text(exc, max_length=240),
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc
    render_webgui_status(status.model_dump(mode="json"))
