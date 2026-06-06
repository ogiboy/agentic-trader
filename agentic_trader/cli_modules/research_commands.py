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
    _register_research_status_command(app, settings_provider, emit_json)
    _register_research_cycle_control_command(app, settings_provider)
    _register_research_refresh_command(app, settings_provider, emit_json)
    _register_research_setup_commands(app, settings_provider, emit_json)


def _register_research_status_command(
    app: typer.Typer,
    settings_provider: Callable[[], Settings],
    emit_json: Callable[[object], None],
) -> None:
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
