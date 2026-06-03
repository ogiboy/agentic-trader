from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Never

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text
from agentic_trader.ui_text import (
    HELP_CAMOFOX_OWNER,
    HELP_CAMOFOX_SERVICE_HOST,
    HELP_CAMOFOX_SERVICE_PORT,
    HELP_FIRECRAWL_OWNER,
    HELP_JSON,
    HELP_MODEL_NAME_TO_PULL,
    HELP_MODEL_SERVICE_HOST,
    HELP_MODEL_SERVICE_PORT,
    HELP_OLLAMA_OWNER,
    HELP_SETUP_DRY_RUN,
    HELP_WEBGUI_OPEN_BROWSER,
    LABEL_EXIT_CODE,
    LABEL_FIELD,
    LABEL_MODEL,
    LABEL_STDERR,
    LABEL_STDOUT,
    LABEL_VALUE,
    MESSAGE_SETUP_BOOTSTRAP_GUIDANCE,
    TITLE_CAMOFOX_START_FAILED,
    TITLE_MODEL_PULL,
    TITLE_MODEL_SERVICE_START_FAILED,
    TITLE_SETUP_GUIDANCE,
    TITLE_WEB_GUI_START_FAILED,
)

from .common import console
from .system_rendering import (
    render_camofox_service_status,
    render_model_service_status,
    render_setup_status,
    render_tool_ownership,
    render_webgui_service_status,
)


@dataclass(frozen=True)
class SystemCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    ownership_modes: Sequence[str]
    validate_ownership_mode: Any
    build_setup_status: Any
    read_tool_ownership_payload: Any
    write_tool_ownership: Any
    build_model_service_status: Any
    start_model_service: Any
    stop_model_service: Any
    pull_model: Any
    build_webgui_service_status: Any
    start_operator_webgui: Any
    stop_webgui_service: Any
    build_camofox_service_status: Any
    start_camofox_service: Any
    stop_camofox_service: Any


def register_system_commands(
    *,
    app: typer.Typer,
    tool_ownership_app: typer.Typer,
    model_service_app: typer.Typer,
    webgui_service_app: typer.Typer,
    camofox_service_app: typer.Typer,
    deps: SystemCommandDeps,
) -> None:
    _register_setup_commands(app, deps)
    _register_tool_ownership_commands(tool_ownership_app, deps)
    _register_model_service_commands(model_service_app, deps)
    _register_webgui_service_commands(webgui_service_app, deps)
    _register_camofox_service_commands(camofox_service_app, deps)


def _register_setup_commands(app: typer.Typer, deps: SystemCommandDeps) -> None:
    @app.command("setup-status")
    def setup_status(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.build_setup_status(settings).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_setup_status(payload)

    @app.command("setup")
    def setup_command(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--no-dry-run",
            help=HELP_SETUP_DRY_RUN,
        ),
    ) -> None:
        settings = deps.get_settings()
        status = deps.build_setup_status(settings).model_dump(mode="json")
        payload: dict[str, object] = {
            "dry_run": dry_run,
            "mutated": False,
            "status": status,
            "message": MESSAGE_SETUP_BOOTSTRAP_GUIDANCE,
        }
        if json_output:
            deps.emit_json(payload)
            return
        render_setup_status(status)
        console.print(
            Panel(
                str(payload["message"]),
                title=TITLE_SETUP_GUIDANCE,
                border_style="cyan",
            )
        )


def _register_tool_ownership_commands(
    tool_ownership_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @tool_ownership_app.command("status")
    def tool_ownership_status(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.read_tool_ownership_payload(settings).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_tool_ownership(payload)

    @tool_ownership_app.command("set")
    def tool_ownership_set(
        ollama_owner: str | None = typer.Option(
            None,
            "--ollama-owner",
            help=HELP_OLLAMA_OWNER,
        ),
        firecrawl_owner: str | None = typer.Option(
            None,
            "--firecrawl-owner",
            help=HELP_FIRECRAWL_OWNER,
        ),
        camofox_owner: str | None = typer.Option(
            None,
            "--camofox-owner",
            help=HELP_CAMOFOX_OWNER,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        updates = _tool_ownership_updates(
            deps=deps,
            ollama_owner=ollama_owner,
            firecrawl_owner=firecrawl_owner,
            camofox_owner=camofox_owner,
        )
        settings = deps.get_settings()
        payload = deps.write_tool_ownership(settings, updates, source="cli").model_dump(
            mode="json"
        )
        if json_output:
            deps.emit_json(payload)
            return
        render_tool_ownership(payload)


def _tool_ownership_updates(
    *,
    deps: SystemCommandDeps,
    ollama_owner: str | None,
    firecrawl_owner: str | None,
    camofox_owner: str | None,
) -> dict[str, str]:
    updates: dict[str, str] = {}
    for tool, value in (
        ("ollama", ollama_owner),
        ("firecrawl", firecrawl_owner),
        ("camofox", camofox_owner),
    ):
        if value is None:
            continue
        try:
            updates[tool] = deps.validate_ownership_mode(value)
        except ValueError as exc:
            modes = ", ".join(
                mode for mode in deps.ownership_modes if mode != "undecided"
            )
            raise typer.BadParameter(f"{exc}; valid values: {modes}") from exc
    if not updates:
        raise typer.BadParameter("Select at least one ownership decision to persist.")
    return updates


def _register_model_service_commands(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    _register_model_status_command(model_service_app, deps)
    _register_model_start_command(model_service_app, deps)
    _register_model_stop_command(model_service_app, deps)
    _register_model_pull_command(model_service_app, deps)


def _register_model_status_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @model_service_app.command("status")
    def model_service_status(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        probe_generation: bool = typer.Option(
            False,
            "--probe-generation",
            help=(
                "Run a tiny Ollama generation probe in addition to lightweight "
                "service/model checks."
            ),
        ),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.build_model_service_status(
            settings,
            include_generation=probe_generation,
        ).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_model_service_status(payload)


def _register_model_start_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @model_service_app.command("start")
    def model_service_start(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        host: str | None = typer.Option(None, "--host", help=HELP_MODEL_SERVICE_HOST),
        port: int | None = typer.Option(
            None,
            "--port",
            min=1,
            max=65535,
            help=HELP_MODEL_SERVICE_PORT,
        ),
    ) -> None:
        try:
            payload = deps.start_model_service(
                deps.get_settings(),
                host=host,
                port=port,
            ).model_dump(mode="json")
        except Exception as exc:
            _emit_start_error(
                json_output=json_output,
                deps=deps,
                title=TITLE_MODEL_SERVICE_START_FAILED,
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_model_service_status(payload)


def _register_model_stop_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @model_service_app.command("stop")
    def model_service_stop(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.stop_model_service(deps.get_settings()).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_model_service_status(payload)


def _register_model_pull_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @model_service_app.command("pull")
    def model_service_pull(
        model_name: str = typer.Argument(..., help=HELP_MODEL_NAME_TO_PULL),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload: dict[str, object]
        try:
            payload = deps.pull_model(deps.get_settings(), model_name)
        except Exception as exc:
            payload = {
                "model": model_name,
                "exit_code": 1,
                "stderr": redact_sensitive_text(exc, max_length=240),
            }
        if json_output:
            deps.emit_json(payload)
        else:
            _render_model_pull(payload)
        exit_code = payload.get("exit_code", 1)
        if not isinstance(exit_code, int) or exit_code != 0:
            raise typer.Exit(code=1)


def _register_webgui_service_commands(
    webgui_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @webgui_service_app.command("status")
    def webgui_service_status(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.build_webgui_service_status(deps.get_settings()).model_dump(
            mode="json"
        )
        if json_output:
            deps.emit_json(payload)
            return
        render_webgui_service_status(payload)

    @webgui_service_app.command("start")
    def webgui_service_start(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        open_browser: bool = typer.Option(
            True,
            "--open-browser/--no-open-browser",
            help=HELP_WEBGUI_OPEN_BROWSER,
        ),
    ) -> None:
        try:
            payload = deps.start_operator_webgui(
                deps.get_settings(),
                open_browser=open_browser,
            ).model_dump(mode="json")
        except Exception as exc:
            _emit_start_error(
                json_output=json_output,
                deps=deps,
                title=TITLE_WEB_GUI_START_FAILED,
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_webgui_service_status(payload)

    @webgui_service_app.command("stop")
    def webgui_service_stop(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.stop_webgui_service(deps.get_settings()).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_webgui_service_status(payload)


def _register_camofox_service_commands(
    camofox_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    @camofox_service_app.command("status")
    def camofox_service_status(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.build_camofox_service_status(deps.get_settings()).model_dump(
            mode="json"
        )
        if json_output:
            deps.emit_json(payload)
            return
        render_camofox_service_status(payload)

    @camofox_service_app.command("start")
    def camofox_service_start(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        host: str | None = typer.Option(None, "--host", help=HELP_CAMOFOX_SERVICE_HOST),
        port: int | None = typer.Option(
            None,
            "--port",
            min=1,
            max=65535,
            help=HELP_CAMOFOX_SERVICE_PORT,
        ),
    ) -> None:
        try:
            payload = deps.start_camofox_service(
                deps.get_settings(),
                host=host,
                port=port,
            ).model_dump(mode="json")
        except Exception as exc:
            _emit_start_error(
                json_output=json_output,
                deps=deps,
                title=TITLE_CAMOFOX_START_FAILED,
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_camofox_service_status(payload)

    @camofox_service_app.command("stop")
    def camofox_service_stop(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.stop_camofox_service(deps.get_settings()).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_camofox_service_status(payload)


def _emit_start_error(
    *,
    json_output: bool,
    deps: SystemCommandDeps,
    title: str,
    exc: Exception,
) -> Never:
    error_payload = {
        "started": False,
        "error": redact_sensitive_text(exc, max_length=240),
    }
    if json_output:
        deps.emit_json(error_payload)
    else:
        console.print(
            Panel(str(error_payload["error"]), title=title, border_style="red")
        )
    raise typer.Exit(code=1) from exc


def _render_model_pull(payload: dict[str, object]) -> None:
    stdout = str(payload.get("stdout", "")) or "-"
    stderr = str(payload.get("stderr", "")) or "-"
    table = Table(title=TITLE_MODEL_PULL)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_MODEL, str(payload["model"]))
    table.add_row(LABEL_EXIT_CODE, str(payload["exit_code"]))
    table.add_row(LABEL_STDOUT, stdout)
    table.add_row(LABEL_STDERR, stderr)
    console.print(table)
