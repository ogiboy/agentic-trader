from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from pydantic import BaseModel, Field

from agentic_trader.json_utils import object_list as _object_list

DEFAULT_MODEL_CHOICES = (
    "qwen3:8b",
    "llama3.2:3b",
    "deepseek-r1:8b",
    "gemma3:4b",
)


class ModelServiceStatus(BaseModel):
    """Operator-facing local model service status."""

    tool_id: str = "ollama"
    tool_status_id: str = "ollama_cli"
    tool_consumers: list[str] = Field(default_factory=list)
    tool_fallback_order: list[str] = Field(default_factory=list)
    tool_ownership_modes: list[str] = Field(default_factory=list)
    install_hint: str = ""
    notes: list[str] = Field(default_factory=list)
    provider: str = "ollama"
    command_available: bool
    command_path: str | None = None
    configured_base_url: str
    configured_model: str
    service_reachable: bool
    model_available: bool
    generation_checked: bool = False
    generation_available: bool | None = None
    generation_message: str | None = None
    available_models: list[str] = Field(default_factory=list)
    app_owned: bool = False
    owner: str | None = None
    pid: int | None = None
    host: str | None = None
    port: int | None = None
    base_url: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    stdout_tail: list[str] = Field(default_factory=list)
    stderr_tail: list[str] = Field(default_factory=list)
    state_path: str
    message: str
    suggested_models: list[str] = Field(
        default_factory=lambda: list(DEFAULT_MODEL_CHOICES)
    )
    runtime_base_url_matches_app_service: bool = False

    def is_owned_by_host(self, host_id: str) -> bool:
        """Return true when this payload represents an app-owned service for host_id."""

        return self.app_owned and self.owner == host_id


@dataclass(frozen=True, slots=True)
class ModelServiceToolMetadata:
    tool_id: str
    tool_status_id: str
    tool_consumers: list[str]
    tool_fallback_order: list[str]
    tool_ownership_modes: list[str]
    install_hint: str


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _string_list(value: object) -> list[str]:
    return [item for item in _object_list(value) if isinstance(item, str)]


def model_service_tool_metadata(
    tool_payload: Mapping[str, object],
) -> ModelServiceToolMetadata:
    return ModelServiceToolMetadata(
        tool_id=_string_value(tool_payload.get("tool_id")),
        tool_status_id=_string_value(tool_payload.get("tool_status_id")),
        tool_consumers=_string_list(tool_payload.get("tool_consumers")),
        tool_fallback_order=_string_list(tool_payload.get("tool_fallback_order")),
        tool_ownership_modes=_string_list(tool_payload.get("tool_ownership_modes")),
        install_hint=_string_value(tool_payload.get("install_hint")),
    )


def model_service_status_message(
    *,
    reachable: bool,
    model_available: bool,
    generation_checked: bool,
    generation_available: bool | None,
    generation_message: str | None,
    fallback_message: str,
) -> str:
    if not reachable:
        return fallback_message
    if not model_available:
        return "Ollama is reachable, but the configured model is not listed."
    if generation_checked and generation_available is False:
        detail = generation_message or "generation probe failed"
        return (
            "Ollama is reachable and the configured model is listed, but a "
            f"generation probe failed: {detail}"
        )
    if generation_checked and generation_available is True:
        return "Ollama is reachable and the configured model can generate."
    return fallback_message


def base_url_mismatch_message(
    *,
    include_generation: bool,
    generation_available: bool | None,
    generation_message: str | None,
) -> str:
    message = (
        "App-managed Ollama is running on a different base URL than the "
        "runtime uses; set AGENTIC_TRADER_BASE_URL to the app-owned URL "
        "with /v1 when you want cycles to use it."
    )
    if include_generation and generation_available is False:
        detail = generation_message or "generation probe failed"
        return f"{message} Generation probe also failed: {detail}"
    return message


def _append_stale_app_managed_message(status_message: str) -> str:
    return (
        f"{status_message} Stale app-managed Ollama processes were "
        "detected; run agentic-trader model-service stop to clean them."
    )


def app_owned_model_status_message(
    *,
    reachable: bool,
    model_available: bool,
    include_generation: bool,
    generation_available: bool | None,
    generation_message: str | None,
    fetch_message: str,
    runtime_base_url_matches_app_service: bool,
    orphan_app_managed_pids: list[int],
) -> str:
    if not reachable:
        status_message = fetch_message
    elif not runtime_base_url_matches_app_service:
        status_message = base_url_mismatch_message(
            include_generation=include_generation,
            generation_available=generation_available,
            generation_message=generation_message,
        )
    else:
        status_message = model_service_status_message(
            reachable=reachable,
            model_available=model_available,
            generation_checked=include_generation,
            generation_available=generation_available,
            generation_message=generation_message,
            fallback_message="App-managed Ollama is running.",
        )
    if orphan_app_managed_pids:
        return _append_stale_app_managed_message(status_message)
    return status_message


def host_model_status_message(
    *,
    status_message: str,
    reachable: bool,
    ollama_serve_pids: list[int],
) -> str:
    if len(ollama_serve_pids) > 1:
        return (
            f"{status_message} Multiple host/default Ollama serve processes were "
            "detected; stop duplicates or use the app-managed model service if "
            "generation fails."
        )
    if reachable and ollama_serve_pids:
        return (
            f"{status_message} This is a host/default Ollama service; "
            "model-service stop will not kill it."
        )
    return status_message


def model_status_notes(
    *,
    tool_payload: Mapping[str, object],
    ollama_serve_pids: list[int],
    orphan_app_managed_pids: list[int],
) -> list[str]:
    notes = _string_list(tool_payload.get("notes", []))
    if ollama_serve_pids:
        notes.append(f"ollama_process_count={len(ollama_serve_pids)}")
    if len(ollama_serve_pids) > 1:
        notes.append("external_ollama_duplicate_processes_detected")
    if orphan_app_managed_pids:
        notes.append(
            f"orphan_app_managed_ollama_process_count={len(orphan_app_managed_pids)}"
        )
    return notes
