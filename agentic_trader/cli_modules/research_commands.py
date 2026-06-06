from __future__ import annotations

from collections.abc import Callable
from typing import cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.research_cycle_control import (
    run_research_cycle_control_command,
)
from agentic_trader.config import Settings
from agentic_trader.researchd.control import (
    get_research_cycle_control,
    set_research_cycle_control,
)
from agentic_trader.researchd.crewai_setup import crewai_setup_status
from agentic_trader.researchd.orchestrator import ResearchSidecar
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.researchd.status import build_research_sidecar_state
from agentic_trader.runtime_feed import (
    read_latest_research_snapshot,
    read_research_digest_replay,
)
from agentic_trader.ui_text import t as ui_t


def register_research_commands(
    app: typer.Typer,
    *,
    settings_provider: Callable[[], Settings],
    emit_json: Callable[[object], None],
) -> None:
    """
    Register research-related CLI subcommands on the provided Typer app.
    
    Registers the following commands: `research-status`, `research-cycle-control`,
    `research-refresh`, and the setup inspection commands (`research-flow-setup` /
    `research-crewai-setup`), wiring them to the given settings provider and JSON
    emitter.
    
    Parameters:
        app (typer.Typer): Typer application to attach the commands to.
        settings_provider (Callable[[], Settings]): Zero-argument callable that
            returns the current Settings when invoked.
        emit_json (Callable[[object], None]): Callable used to emit JSON payloads
            for commands that support JSON output.
    """
    _register_research_status_command(app, settings_provider, emit_json)
    _register_research_cycle_control_command(app, settings_provider)
    _register_research_refresh_command(app, settings_provider, emit_json)
    _register_research_setup_commands(app, settings_provider, emit_json)


def _register_research_status_command(
    app: typer.Typer,
    settings_provider: Callable[[], Settings],
    emit_json: Callable[[object], None],
) -> None:
    """
    Register the "research-status" CLI command on the given Typer application.
    
    The registered command builds a research sidecar payload (optionally probing external sources), then either emits the payload as JSON using `emit_json` when `--json` is set, or renders the sidecar state to the console.
    
    Parameters:
        app: Typer application to register the command on.
        settings_provider: Callable that returns current Settings; invoked when the command runs.
        emit_json: Callable that accepts a payload object and outputs JSON; used when `--json` is requested.
    """
    @app.command("research-status")
    def research_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        probe: bool = typer.Option(
            False,
            "--probe/--no-probe",
            help=ui_t("help.research_probe"),
        ),
    ) -> None:
        settings = settings_provider()
        payload = research_sidecar_payload(settings, probe=probe)
        if json_output:
            emit_json(payload)
            return
        render_research_sidecar_state(payload)


def _register_research_cycle_control_command(
    app: typer.Typer,
    settings_provider: Callable[[], Settings],
) -> None:
    """
    Register the `research-cycle-control` CLI command on the provided Typer app.
    
    The command exposes options to pause, resume, or trigger the research cycle immediately, an optional reason, and a JSON output flag. When invoked it uses the provided settings from `settings_provider` to perform the requested cycle control action.
    
    Parameters:
        settings_provider (Callable[[], Settings]): A zero-argument callable that returns current runtime settings; it is called when the CLI command executes to obtain configuration used by the cycle control operation.
    """
    @app.command("research-cycle-control")
    def research_cycle_control(
        pause: bool = typer.Option(
            False,
            "--pause",
            help=ui_t("help.research_cycle_pause"),
        ),
        resume: bool = typer.Option(
            False,
            "--resume",
            help=ui_t("help.research_cycle_resume"),
        ),
        trigger_now: bool = typer.Option(
            False,
            "--trigger-now",
            help=ui_t("help.research_cycle_trigger_now"),
        ),
        reason: str | None = typer.Option(
            None,
            "--reason",
            help=ui_t("help.research_cycle_reason"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        run_research_cycle_control_command(
            settings=settings_provider(),
            pause=pause,
            resume=resume,
            trigger_now=trigger_now,
            reason=reason,
            json_output=json_output,
            get_control=get_research_cycle_control,
            set_control=set_research_cycle_control,
        )


def _register_research_refresh_command(
    app: typer.Typer,
    settings_provider: Callable[[], Settings],
    emit_json: Callable[[object], None],
) -> None:
    """
    Register the `research-refresh` CLI command which collects the research sidecar snapshot, optionally persists it, and emits or renders the result.
    
    Registers a subcommand `research-refresh` with options:
    - `--json`: emit the assembled payload as JSON via `emit_json`.
    - `--persist/--no-persist` (default `--persist`): when enabled, persist the collected snapshot and include the persisted record in the payload.
    
    Parameters:
        app: Typer application to register the command on.
        settings_provider: Callable that returns the current Settings when invoked.
        emit_json: Callable used to emit the final payload when `--json` is specified.
    """
    @app.command("research-refresh")
    def research_refresh(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
        persist: bool = typer.Option(
            True,
            "--persist/--no-persist",
            help=ui_t("help.research_refresh_persist"),
        ),
    ) -> None:
        settings = settings_provider()
        result = ResearchSidecar(settings).collect_once()
        record_payload: dict[str, object] | None = None
        if persist:
            record = persist_research_result(settings, result)
            record_payload = record.model_dump(mode="json")
        payload = {
            "state": result.state.model_dump(mode="json"),
            "world_state": (
                result.world_state.model_dump(mode="json")
                if result.world_state is not None
                else None
            ),
            "memory_update": result.memory_update,
            "persisted": record_payload is not None,
            "record": record_payload,
        }
        if json_output:
            emit_json(payload)
            return
        render_research_sidecar_state(result.state.model_dump(mode="json"))
        if record_payload is not None:
            console.print(
                _render_health_panel(
                    ui_t("title.research_snapshot_persisted"),
                    ui_t("message.research_snapshot_recorded").format(
                        snapshot_id=record_payload["snapshot_id"]
                    ),
                    border_style="green",
                )
            )


def _register_research_setup_commands(
    app: typer.Typer,
    settings_provider: Callable[[], Settings],
    emit_json: Callable[[object], None],
) -> None:
    """
    Register two CLI subcommands for inspecting Research/CrewAI setup.
    
    Each subcommand ("research-flow-setup" and "research-crewai-setup") obtains settings via `settings_provider()`,
    computes the CrewAI setup payload, and either emits the payload as JSON using `emit_json` when `--json` is set
    or renders the setup status via `render_research_flow_setup`.
    
    Parameters:
        app (typer.Typer): Typer application to register the commands on.
        settings_provider (Callable[[], Settings]): Callable that returns the current Settings when invoked.
        emit_json (Callable[[object], None]): Function to emit a JSON-serializable payload to output.
    """
    @app.command("research-flow-setup")
    def research_flow_setup(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        payload = crewai_setup_status(settings_provider())
        if json_output:
            emit_json(payload)
            return
        render_research_flow_setup(payload)

    @app.command("research-crewai-setup")
    def research_crewai_setup(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Display the CrewAI flow setup status, emitting JSON when requested or rendering a human-readable view.
        
        Parameters:
            json_output (bool): If true, emit the setup status as JSON instead of rendering to the console.
        """
        payload = crewai_setup_status(settings_provider())
        if json_output:
            emit_json(payload)
            return
        render_research_flow_setup(payload)


def research_sidecar_payload(
    settings: Settings, *, probe: bool = False
) -> dict[str, object]:
    payload = build_research_sidecar_state(settings, probe=probe).model_dump(
        mode="json"
    )
    payload["cycleControl"] = get_research_cycle_control(settings).model_dump(
        mode="json"
    )
    payload["latestSnapshot"] = latest_research_snapshot_payload(settings)
    payload["latestDigestReplay"] = latest_research_digest_replay_payload(settings)
    return payload


def latest_research_snapshot_payload(settings: Settings) -> dict[str, object]:
    try:
        record = read_latest_research_snapshot(settings)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
        }
    if record is None:
        return {
            "available": False,
            "error": "no_research_snapshot_recorded",
        }
    return {
        "available": True,
        "record": record.model_dump(mode="json"),
    }


def latest_research_digest_replay_payload(settings: Settings) -> dict[str, object]:
    try:
        record = read_research_digest_replay(settings)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
        }
    if record is None:
        return {
            "available": False,
            "error": "no_research_digest_replay_recorded",
        }
    return {
        "available": True,
        "record": record.model_dump(mode="json"),
    }


def render_research_sidecar_state(payload: dict[str, object]) -> None:
    """
    Render research sidecar status and provider health tables to the console.
    
    Parameters:
        payload (dict[str, object]): A dictionary representing the research sidecar state. Expected keys:
            - mode: current mode name
            - enabled: whether the sidecar is enabled
            - backend: backend identifier or name
            - status: human-readable status
            - updated_at: timestamp of last update
            - watched_symbols: list[str] of symbols being watched
            - last_successful_update_at: optional timestamp of last successful update
            - last_error: optional error message or details
            - cycleControl: dict with keys:
                - status: cycle control status
                - trigger_now_requested: truthy value when a trigger-now is requested
            - latestDigestReplay: dict with key:
                - available: truthy when a digest replay is available
            - provider_health: list[dict[str, object]] where each provider dict contains:
                - provider_id, provider_type, enabled, freshness, message
    
    The function prints two rich.Table views to the global console:
    1. A summary table of sidecar fields (mode, enabled, backend, status, timestamps, watched symbols, cycle control and digest replay availability).
    2. A provider health table with one row per provider showing id, type, enabled, freshness and message.
    """
    table = Table(title=ui_t("title.research_sidecar_status"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.mode"), str(payload["mode"]))
    table.add_row(ui_t("label.enabled"), str(payload["enabled"]))
    table.add_row(ui_t("label.backend"), str(payload["backend"]))
    table.add_row(ui_t("label.status"), str(payload["status"]))
    table.add_row(ui_t("label.updated_at"), str(payload["updated_at"]))
    table.add_row(
        ui_t("label.watched_symbols"),
        ", ".join(cast(list[str], payload["watched_symbols"])) or "-",
    )
    last_success = payload.get("last_successful_update_at")
    table.add_row(ui_t("label.last_successful_update"), str(last_success or "-"))
    last_error = payload.get("last_error")
    table.add_row(ui_t("label.last_error"), str(last_error or "-"))
    control = cast(dict[str, object], payload.get("cycleControl", {}))
    table.add_row(ui_t("label.cycle_control"), str(control.get("status", "-")))
    table.add_row(
        ui_t("label.trigger_now"),
        ui_t("label.yes") if control.get("trigger_now_requested") else ui_t("label.no"),
    )
    replay = cast(dict[str, object], payload.get("latestDigestReplay", {}))
    table.add_row(
        ui_t("label.digest_replay"),
        ui_t("status.available") if replay.get("available") else "-",
    )
    console.print(table)

    providers = cast(list[dict[str, object]], payload["provider_health"])
    provider_table = Table(title=ui_t("title.research_source_health"))
    provider_table.add_column(ui_t("label.provider"))
    provider_table.add_column(ui_t("label.type"))
    provider_table.add_column(ui_t("label.enabled"))
    provider_table.add_column(ui_t("label.freshness"))
    provider_table.add_column(ui_t("label.message"))
    for provider in providers:
        provider_table.add_row(
            str(provider["provider_id"]),
            str(provider["provider_type"]),
            str(provider["enabled"]),
            str(provider["freshness"]),
            str(provider["message"]),
        )
    console.print(provider_table)


def render_research_flow_setup(payload: dict[str, object]) -> None:
    """
    Render CrewAI flow setup status and recommended commands to the console.
    
    Renders a two-part UI:
    - A table titled "research_crewai_flow_setup" showing setup fields (availability, version info,
      flow directory, environment and scaffold presence, Python version, lockfile and core dependency).
    - A panel titled "recommended_commands" listing each recommended command on its own line.
    
    Parameters:
        payload (dict[str, object]): Mapping containing setup information. Expected keys:
            - available (bool): Whether the sidecar/flow is available.
            - version_source (str | None): Source used to determine the flow version.
            - version (str | None): Detected flow version.
            - uv_available (bool): Whether the UV (unit/version) is available.
            - flow_dir (str | None): Path to the flow directory.
            - flow_scaffold_exists (bool): Whether a flow scaffold exists.
            - environment_exists (bool): Whether the runtime environment is present.
            - python_version (str | None): Detected Python version for the flow.
            - lockfile_exists (bool): Whether a lockfile is present.
            - core_dependency (str | None): Core dependency identifier/version.
            - recommended_commands (list[str]): Commands to suggest to the user.
    """
    version_source = str(payload.get("version_source") or "-")
    version = str(payload["version"] or "-")
    python_version = str(payload["python_version"] or "-")
    table = Table(title=ui_t("title.research_crewai_flow_setup"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.sidecar_available"), str(payload["available"]))
    table.add_row(ui_t("label.version_source"), version_source)
    table.add_row(ui_t("label.version"), version)
    table.add_row(ui_t("label.uv_available"), str(payload["uv_available"]))
    table.add_row(ui_t("label.flow_dir"), str(payload["flow_dir"]))
    table.add_row(ui_t("label.scaffold_exists"), str(payload["flow_scaffold_exists"]))
    table.add_row(ui_t("label.environment_exists"), str(payload["environment_exists"]))
    table.add_row(ui_t("label.python_version"), python_version)
    table.add_row(ui_t("label.lockfile_exists"), str(payload["lockfile_exists"]))
    table.add_row(ui_t("label.core_dependency"), str(payload["core_dependency"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["recommended_commands"])),
            title=ui_t("title.recommended_commands"),
            border_style="cyan",
        )
    )


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(
        body,
        title=f"Agentic Trader // {status}",
        border_style=border_style,
    )
