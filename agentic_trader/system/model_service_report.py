"""Status report assembly for the app-managed Ollama service."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_trader.config import Settings
from agentic_trader.system.model_service_probe import probe_ollama_generation
from agentic_trader.system.model_service_state import (
    ModelServiceState,
    model_service_state_path,
    tail_model_service_text,
)
from agentic_trader.system.model_service_status import (
    ModelServiceStatus,
    app_owned_model_status_message,
    host_model_status_message,
    model_service_status_message,
    model_service_tool_metadata,
    model_status_notes,
)
from agentic_trader.system.tool_roots import local_tool_status_payload


@dataclass(frozen=True, slots=True)
class ModelServiceStatusProbe:
    app_state: ModelServiceState | None
    app_owned: bool
    command_path: str | None
    ollama_serve_pids: list[int]
    orphan_app_managed_pids: list[int]
    api_root: str
    reachable: bool
    models: list[str]
    fetch_message: str
    model_available: bool
    generation_available: bool | None
    generation_message: str | None
    runtime_base_url_matches_app_service: bool
    status_message: str


def generation_probe_status(
    *,
    include_generation: bool,
    reachable: bool,
    model_available: bool,
    api_root: str,
    model_name: str,
) -> tuple[bool | None, str | None]:
    if not include_generation:
        return None, None
    if not reachable:
        return False, "Generation probe skipped because Ollama is unreachable."
    if not model_available:
        return (
            False,
            "Generation probe skipped because the configured model is not listed.",
        )
    return probe_ollama_generation(api_root, model_name)


def model_service_status_message_for_probe(
    *,
    app_owned: bool,
    reachable: bool,
    model_available: bool,
    include_generation: bool,
    generation_available: bool | None,
    generation_message: str | None,
    fetch_message: str,
    runtime_base_url_matches_app_service: bool,
    ollama_serve_pids: list[int],
    orphan_app_managed_pids: list[int],
) -> str:
    status_message = model_service_status_message(
        reachable=reachable,
        model_available=model_available,
        generation_checked=include_generation,
        generation_available=generation_available,
        generation_message=generation_message,
        fallback_message=fetch_message,
    )
    if app_owned:
        return app_owned_model_status_message(
            reachable=reachable,
            model_available=model_available,
            include_generation=include_generation,
            generation_available=generation_available,
            generation_message=generation_message,
            fetch_message=fetch_message,
            runtime_base_url_matches_app_service=runtime_base_url_matches_app_service,
            orphan_app_managed_pids=orphan_app_managed_pids,
        )
    return host_model_status_message(
        status_message=status_message,
        reachable=reachable,
        ollama_serve_pids=ollama_serve_pids,
    )


def model_service_status_from_probe(
    settings: Settings,
    *,
    probe: ModelServiceStatusProbe,
    tail_limit: int,
    include_generation: bool,
) -> ModelServiceStatus:
    tool_payload = local_tool_status_payload("ollama")
    tool_metadata = model_service_tool_metadata(tool_payload)
    notes = model_status_notes(
        tool_payload=tool_payload,
        ollama_serve_pids=probe.ollama_serve_pids,
        orphan_app_managed_pids=probe.orphan_app_managed_pids,
    )
    app_state = probe.app_state
    return ModelServiceStatus(
        tool_id=tool_metadata.tool_id,
        tool_status_id=tool_metadata.tool_status_id,
        tool_consumers=tool_metadata.tool_consumers,
        tool_fallback_order=tool_metadata.tool_fallback_order,
        tool_ownership_modes=tool_metadata.tool_ownership_modes,
        install_hint=tool_metadata.install_hint,
        notes=notes,
        command_available=probe.command_path is not None,
        command_path=probe.command_path,
        configured_base_url=settings.base_url,
        configured_model=settings.model_name,
        service_reachable=probe.reachable,
        model_available=probe.model_available,
        generation_checked=include_generation,
        generation_available=probe.generation_available,
        generation_message=probe.generation_message,
        available_models=probe.models,
        app_owned=probe.app_owned,
        owner=app_state.owner if app_state is not None else None,
        pid=app_state.pid if app_state is not None else None,
        host=app_state.host if app_state is not None else None,
        port=app_state.port if app_state is not None else None,
        base_url=app_state.base_url if app_state is not None else probe.api_root,
        stdout_log_path=app_state.stdout_log_path if app_state is not None else None,
        stderr_log_path=app_state.stderr_log_path if app_state is not None else None,
        stdout_tail=tail_model_service_text(
            app_state.stdout_log_path if app_state is not None else None,
            limit=tail_limit,
        ),
        stderr_tail=tail_model_service_text(
            app_state.stderr_log_path if app_state is not None else None,
            limit=tail_limit,
        ),
        state_path=str(model_service_state_path(settings)),
        message=probe.status_message,
        runtime_base_url_matches_app_service=(
            probe.runtime_base_url_matches_app_service
        ),
    )
