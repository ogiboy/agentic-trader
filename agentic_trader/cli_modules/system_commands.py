from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Never

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text
from agentic_trader.ui_text import t as ui_t

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
    """
    Register CLI commands for setup-related actions.
    
    Adds two commands to `app`:
    - `setup-status`: obtains the current setup status and either emits it as JSON or renders it for terminal display.
    - `setup`: builds a setup response containing `dry_run`, `mutated` (always `False`), `status`, and a UI guidance `message`; either emits the response as JSON or renders the status and prints a guidance panel.
    
    Parameters:
        app (typer.Typer): Typer application to which the commands will be registered.
        deps (SystemCommandDeps): Injected dependencies used by the commands (settings accessor, JSON emitter, status builder, and UI renderers).
    """
    @app.command("setup-status")
    def setup_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.build_setup_status(settings).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_setup_status(payload)

    @app.command("setup")
    def setup_command(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--no-dry-run",
            help=ui_t("help.setup_dry_run"),
        ),
    ) -> None:
        """
        Perform a system setup check and present the resulting status and guidance.
        
        Builds a payload that reflects the provided dry_run flag and the computed setup status. If json_output is True, the payload is emitted as JSON; otherwise the setup status is rendered and a guidance panel is printed.
        
        Parameters:
            json_output: When True, emit the full payload as JSON instead of rendering human-readable output.
            dry_run: When True, indicate that the operation is a simulation and no persistent mutations were performed.
        """
        settings = deps.get_settings()
        status = deps.build_setup_status(settings).model_dump(mode="json")
        payload: dict[str, object] = {
            "dry_run": dry_run,
            "mutated": False,
            "status": status,
            "message": ui_t("message.setup_bootstrap_guidance"),
        }
        if json_output:
            deps.emit_json(payload)
            return
        render_setup_status(status)
        console.print(
            Panel(
                str(payload["message"]),
                title=ui_t("title.setup_guidance"),
                border_style="cyan",
            )
        )


def _register_tool_ownership_commands(
    tool_ownership_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    """
    Register CLI commands for inspecting and modifying tool ownership decisions.
    
    This function adds two subcommands to the provided Typer app:
    - `status`: Show the current tool-ownership payload (renders human-readable output or emits JSON with `--json`).
    - `set`: Update ownership decisions for `ollama`, `firecrawl`, and/or `camofox` (each provided via its respective flag); writes changes and outputs the resulting payload (renders or emits JSON with `--json`).
    
    Parameters:
        tool_ownership_app (typer.Typer): Typer application to which the commands will be registered.
        deps (SystemCommandDeps): Injected dependencies used to read, validate, write, render, and emit tool-ownership payloads.
    """
    @tool_ownership_app.command("status")
    def tool_ownership_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
            help=ui_t("help.ollama_owner"),
        ),
        firecrawl_owner: str | None = typer.Option(
            None,
            "--firecrawl-owner",
            help=ui_t("help.firecrawl_owner"),
        ),
        camofox_owner: str | None = typer.Option(
            None,
            "--camofox-owner",
            help=ui_t("help.camofox_owner"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Set ownership decisions for Ollama, Firecrawl, and Camofox and persist the updates to settings.
        
        Only provided (non-None) owner values are applied; omitted options leave existing ownership unchanged. When `json_output` is true the resulting persisted ownership payload is emitted as JSON, otherwise it is rendered for human-readable output.
        
        Parameters:
            ollama_owner (str | None): Desired owner mode for Ollama (omit to keep current).
            firecrawl_owner (str | None): Desired owner mode for Firecrawl (omit to keep current).
            camofox_owner (str | None): Desired owner mode for Camofox (omit to keep current).
            json_output (bool): Emit the resulting payload as JSON when true.
        """
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
    """
    Register the "status" CLI command under the provided Typer app to show model-service status.
    
    The registered `status` command fetches current settings and builds a model-service status payload; when `--probe-generation` is provided it also runs a small generation probe. If `--json` is set the command emits the raw JSON payload via the injected emitter, otherwise it renders a human-friendly view with `render_model_service_status`.
    
    Parameters:
        model_service_app (typer.Typer): Typer application to which the `status` command is registered.
        deps (SystemCommandDeps): Dependency container used to obtain settings, build the status payload, and emit or render output.
    """
    @model_service_app.command("status")
    def model_service_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
    """
    Register the CLI "start" command for the model service.
    
    The registered command starts the model service using optional host and port overrides, then either emits the resulting service status as JSON or renders it for human-friendly output. On failure the command emits a redacted error payload (or a red error panel) and exits with status code 1.
    
    Parameters:
        model_service_app: The Typer application to which the `start` command will be added.
        deps: Injected command dependencies providing settings, start/stop helpers, JSON emission, and rendering utilities.
    """
    @model_service_app.command("start")
    def model_service_start(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        host: str | None = typer.Option(
            None, "--host", help=ui_t("help.model_service_host")
        ),
        port: int | None = typer.Option(
            None,
            "--port",
            min=1,
            max=65535,
            help=ui_t("help.model_service_port"),
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
                title=ui_t("title.model_service_start_failed"),
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_model_service_status(payload)


def _register_model_stop_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    """
    Register the "stop" CLI command for the model service.
    
    The registered command stops the model service using injected dependencies, converts the resulting status to a JSON-serializable payload, and either emits JSON or renders the model service status for human-readable output.
    
    Parameters:
        model_service_app (typer.Typer): Typer application to which the "stop" command will be added.
        deps (SystemCommandDeps): Dependency container providing `get_settings`, `stop_model_service`, `emit_json`, and rendering helpers.
    """
    @model_service_app.command("stop")
    def model_service_stop(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        payload = deps.stop_model_service(deps.get_settings()).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_model_service_status(payload)


def _register_model_pull_command(
    model_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    """
    Register the "pull" subcommand on the model service CLI group.
    
    Adds a `pull` command that attempts to pull a model by name, then either emits the raw JSON payload or renders a human-friendly table; if the resulting payload indicates a non-zero exit code (or an error occurs), the CLI exits with a non-zero status. On error the payload will include `exit_code: 1` and a redacted `stderr` entry.
    """
    @model_service_app.command("pull")
    def model_service_pull(
        model_name: str = typer.Argument(..., help=ui_t("help.model_name_to_pull")),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
    """
    Register the Web GUI service CLI commands ("status", "start", "stop") on the provided Typer application.
    
    Each command supports a `--json` option to emit JSON payloads. The `start` command also accepts an `--open-browser/--no-open-browser` flag to control whether the operator web GUI should be opened after starting.
    
    Parameters:
        webgui_service_app (typer.Typer): Typer application to which the commands will be attached.
        deps (SystemCommandDeps): Injected dependencies used by the commands (settings retrieval, service control, JSON emission, etc.).
    """
    @webgui_service_app.command("status")
    def webgui_service_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        open_browser: bool = typer.Option(
            True,
            "--open-browser/--no-open-browser",
            help=ui_t("help.webgui_open_browser"),
        ),
    ) -> None:
        """
        Start the operator web GUI service and report its resulting status.
        
        Parameters:
            json_output (bool): If true, emit the service status as JSON; otherwise render a human-readable status.
            open_browser (bool): If true, open the web GUI in the default browser after starting; if false, do not open a browser.
        
        On failure, an error payload or error panel is emitted and the process exits with code 1.
        """
        try:
            payload = deps.start_operator_webgui(
                deps.get_settings(),
                open_browser=open_browser,
            ).model_dump(mode="json")
        except Exception as exc:
            _emit_start_error(
                json_output=json_output,
                deps=deps,
                title=ui_t("title.web_gui_start_failed"),
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_webgui_service_status(payload)

    @webgui_service_app.command("stop")
    def webgui_service_stop(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Stop the web GUI service and present the resulting status.
        
        Parameters:
            json_output (bool): If True, emit the status as JSON; otherwise render a human-readable status.
        """
        payload = deps.stop_webgui_service(deps.get_settings()).model_dump(mode="json")
        if json_output:
            deps.emit_json(payload)
            return
        render_webgui_service_status(payload)


def _register_camofox_service_commands(
    camofox_service_app: typer.Typer, deps: SystemCommandDeps
) -> None:
    """
    Register camofox-related CLI commands on the given Typer application.
    
    Adds three commands to camofox_service_app:
    - status: report the camofox service status (accepts --json).
    - start: start the camofox service (accepts --json, --host, --port).
    - stop: stop the camofox service (accepts --json).
    
    Parameters:
        camofox_service_app (typer.Typer): Typer application to register the commands on.
        deps (SystemCommandDeps): Dependency container for retrieving settings, controlling the camofox service, and emitting output.
    """
    @camofox_service_app.command("status")
    def camofox_service_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        host: str | None = typer.Option(
            None, "--host", help=ui_t("help.camofox_service_host")
        ),
        port: int | None = typer.Option(
            None,
            "--port",
            min=1,
            max=65535,
            help=ui_t("help.camofox_service_port"),
        ),
    ) -> None:
        """
        Start the Camofox service using current settings, optionally overriding host and port.
        
        Parameters:
            json_output (bool): If true, emit the resulting status payload as JSON instead of rendering a UI.
            host (str | None): Optional hostname or IP address to bind the service to; when None, use configured default.
            port (int | None): Optional TCP port to bind the service to; when None, use configured default.
        
        Notes:
            On failure to start, an error payload is emitted or rendered and the command exits with code 1.
        """
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
                title=ui_t("title.camofox_start_failed"),
                exc=exc,
            )
        if json_output:
            deps.emit_json(payload)
            return
        render_camofox_service_status(payload)

    @camofox_service_app.command("stop")
    def camofox_service_stop(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Stop the camofox service and present its resulting status.
        
        If `json_output` is True, emit the status payload as JSON; otherwise render a human-readable service status in the CLI.
        
        Parameters:
            json_output (bool): When True, emit JSON output instead of rendering the status.
        """
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
    """
    Render model pull results as a two-column table and print it to the console.
    
    Parameters:
        payload (dict[str, object]): Result payload containing:
            - "model": the model name (required).
            - "exit_code": process exit code (required).
            - "stdout": captured standard output (optional; empty or missing -> displayed as "-").
            - "stderr": captured standard error (optional; empty or missing -> displayed as "-").
    """
    stdout = str(payload.get("stdout", "")) or "-"
    stderr = str(payload.get("stderr", "")) or "-"
    table = Table(title=ui_t("title.model_pull"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.model"), str(payload["model"]))
    table.add_row(ui_t("label.exit_code"), str(payload["exit_code"]))
    table.add_row(ui_t("label.stdout"), stdout)
    table.add_row(ui_t("label.stderr"), stderr)
    console.print(table)
