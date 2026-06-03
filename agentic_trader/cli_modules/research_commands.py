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
from agentic_trader.ui_text import (
    HELP_JSON,
    HELP_RESEARCH_CYCLE_PAUSE,
    HELP_RESEARCH_CYCLE_REASON,
    HELP_RESEARCH_CYCLE_RESUME,
    HELP_RESEARCH_CYCLE_TRIGGER_NOW,
    HELP_RESEARCH_PROBE,
    HELP_RESEARCH_REFRESH_PERSIST,
    LABEL_BACKEND,
    LABEL_CORE_DEPENDENCY,
    LABEL_CYCLE_CONTROL,
    LABEL_DIGEST_REPLAY,
    LABEL_ENABLED,
    LABEL_ENVIRONMENT_EXISTS,
    LABEL_FIELD,
    LABEL_FLOW_DIR,
    LABEL_FRESHNESS,
    LABEL_LAST_ERROR,
    LABEL_LAST_SUCCESSFUL_UPDATE,
    LABEL_LOCKFILE_EXISTS,
    LABEL_MESSAGE,
    LABEL_MODE,
    LABEL_NO,
    LABEL_PROVIDER,
    LABEL_PYTHON_VERSION,
    LABEL_SCAFFOLD_EXISTS,
    LABEL_SIDECAR_AVAILABLE,
    LABEL_STATUS,
    LABEL_TRIGGER_NOW,
    LABEL_TYPE,
    LABEL_UPDATED_AT,
    LABEL_UV_AVAILABLE,
    LABEL_VALUE,
    LABEL_VERSION,
    LABEL_VERSION_SOURCE,
    LABEL_WATCHED_SYMBOLS,
    LABEL_YES,
    MESSAGE_RESEARCH_SNAPSHOT_RECORDED,
    STATUS_AVAILABLE,
    TITLE_RECOMMENDED_COMMANDS,
    TITLE_RESEARCH_CREWAI_FLOW_SETUP,
    TITLE_RESEARCH_SIDECAR_STATUS,
    TITLE_RESEARCH_SNAPSHOT_PERSISTED,
    TITLE_RESEARCH_SOURCE_HEALTH,
)


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
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        probe: bool = typer.Option(
            False,
            "--probe/--no-probe",
            help=HELP_RESEARCH_PROBE,
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
            help=HELP_RESEARCH_CYCLE_PAUSE,
        ),
        resume: bool = typer.Option(
            False,
            "--resume",
            help=HELP_RESEARCH_CYCLE_RESUME,
        ),
        trigger_now: bool = typer.Option(
            False,
            "--trigger-now",
            help=HELP_RESEARCH_CYCLE_TRIGGER_NOW,
        ),
        reason: str | None = typer.Option(
            None,
            "--reason",
            help=HELP_RESEARCH_CYCLE_REASON,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
        persist: bool = typer.Option(
            True,
            "--persist/--no-persist",
            help=HELP_RESEARCH_REFRESH_PERSIST,
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
                    TITLE_RESEARCH_SNAPSHOT_PERSISTED,
                    MESSAGE_RESEARCH_SNAPSHOT_RECORDED.format(
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
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = crewai_setup_status(settings_provider())
        if json_output:
            emit_json(payload)
            return
        render_research_flow_setup(payload)

    @app.command("research-crewai-setup")
    def research_crewai_setup(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
    table = Table(title=TITLE_RESEARCH_SIDECAR_STATUS)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_MODE, str(payload["mode"]))
    table.add_row(LABEL_ENABLED, str(payload["enabled"]))
    table.add_row(LABEL_BACKEND, str(payload["backend"]))
    table.add_row(LABEL_STATUS, str(payload["status"]))
    table.add_row(LABEL_UPDATED_AT, str(payload["updated_at"]))
    table.add_row(
        LABEL_WATCHED_SYMBOLS,
        ", ".join(cast(list[str], payload["watched_symbols"])) or "-",
    )
    last_success = payload.get("last_successful_update_at")
    table.add_row(LABEL_LAST_SUCCESSFUL_UPDATE, str(last_success or "-"))
    last_error = payload.get("last_error")
    table.add_row(LABEL_LAST_ERROR, str(last_error or "-"))
    control = cast(dict[str, object], payload.get("cycleControl", {}))
    table.add_row(LABEL_CYCLE_CONTROL, str(control.get("status", "-")))
    table.add_row(
        LABEL_TRIGGER_NOW,
        LABEL_YES if control.get("trigger_now_requested") else LABEL_NO,
    )
    replay = cast(dict[str, object], payload.get("latestDigestReplay", {}))
    table.add_row(
        LABEL_DIGEST_REPLAY,
        STATUS_AVAILABLE if replay.get("available") else "-",
    )
    console.print(table)

    providers = cast(list[dict[str, object]], payload["provider_health"])
    provider_table = Table(title=TITLE_RESEARCH_SOURCE_HEALTH)
    provider_table.add_column(LABEL_PROVIDER)
    provider_table.add_column(LABEL_TYPE)
    provider_table.add_column(LABEL_ENABLED)
    provider_table.add_column(LABEL_FRESHNESS)
    provider_table.add_column(LABEL_MESSAGE)
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
    table = Table(title=TITLE_RESEARCH_CREWAI_FLOW_SETUP)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_SIDECAR_AVAILABLE, str(payload["available"]))
    table.add_row(LABEL_VERSION_SOURCE, version_source)
    table.add_row(LABEL_VERSION, version)
    table.add_row(LABEL_UV_AVAILABLE, str(payload["uv_available"]))
    table.add_row(LABEL_FLOW_DIR, str(payload["flow_dir"]))
    table.add_row(LABEL_SCAFFOLD_EXISTS, str(payload["flow_scaffold_exists"]))
    table.add_row(LABEL_ENVIRONMENT_EXISTS, str(payload["environment_exists"]))
    table.add_row(LABEL_PYTHON_VERSION, python_version)
    table.add_row(LABEL_LOCKFILE_EXISTS, str(payload["lockfile_exists"]))
    table.add_row(LABEL_CORE_DEPENDENCY, str(payload["core_dependency"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["recommended_commands"])),
            title=TITLE_RECOMMENDED_COMMANDS,
            border_style="cyan",
        )
    )


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(
        body,
        title=f"Agentic Trader // {status}",
        border_style=border_style,
    )
