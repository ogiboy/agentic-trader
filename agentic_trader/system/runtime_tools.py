"""Runtime tool bootstrap helpers for local optional services."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.system.camofox_service import (
    CamofoxServiceStatus,
    build_camofox_service_status,
    start_camofox_service,
)
from agentic_trader.system.model_service import (
    ModelServiceStatus,
    build_model_service_status,
    start_model_service,
)
from agentic_trader.system.tool_ownership import ownership_mode_for_tool


class RuntimeToolBootstrapReport(BaseModel):
    """Report of app-managed side tools considered for a runtime action."""

    model_service: ModelServiceStatus | None = None
    camofox_service: CamofoxServiceStatus | None = None
    messages: list[str] = Field(default_factory=list)


def _base_url_for_ollama_api(status: ModelServiceStatus) -> str | None:
    if not status.base_url:
        return None
    return f"{status.base_url.rstrip('/')}/v1"


def apply_app_owned_service_settings(
    settings: Settings,
    *,
    include_camofox: bool = False,
) -> RuntimeToolBootstrapReport:
    """Point in-memory settings at already-running app-owned helper services.

    This is read-only with respect to processes and files. It lets dashboard,
    doctor, and other observer-style surfaces report the endpoint the app owns
    before a runtime action decides whether to auto-start anything.
    """

    messages: list[str] = []
    model_status = build_model_service_status(settings)
    if (
        settings.llm_provider == "ollama"
        and ownership_mode_for_tool(settings, "ollama") == "app-owned"
        and model_status.app_owned
    ):
        runtime_base_url = _base_url_for_ollama_api(model_status)
        if runtime_base_url is not None:
            settings.base_url = runtime_base_url
            model_status = build_model_service_status(settings)
    messages.append(model_status.message)

    camofox_status = None
    if include_camofox:
        camofox_status = build_camofox_service_status(settings)
        if (
            ownership_mode_for_tool(settings, "camofox") == "app-owned"
            and camofox_status.app_owned
        ):
            settings.research_camofox_base_url = camofox_status.base_url
            camofox_status = build_camofox_service_status(settings)
        messages.append(camofox_status.message)

    return RuntimeToolBootstrapReport(
        model_service=model_status,
        camofox_service=camofox_status,
        messages=messages,
    )


def ensure_model_service_if_configured(settings: Settings) -> ModelServiceStatus:
    """Start app-owned Ollama when configured and the current endpoint is absent."""

    status = build_model_service_status(settings)
    if (
        settings.llm_provider == "ollama"
        and settings.runtime_auto_start_model_service
        and ownership_mode_for_tool(settings, "ollama") == "app-owned"
        and (not status.service_reachable or not status.model_available)
    ):
        status = start_model_service(settings)
    if settings.llm_provider == "ollama" and status.app_owned:
        runtime_base_url = _base_url_for_ollama_api(status)
        if runtime_base_url is not None:
            settings.base_url = runtime_base_url
    return status


def ensure_camofox_service_if_configured(settings: Settings) -> CamofoxServiceStatus | None:
    """Start app-owned Camofox when the research provider is enabled."""

    if not settings.research_camofox_enabled:
        return None
    status = build_camofox_service_status(settings)
    if (
        settings.runtime_auto_start_camofox
        and ownership_mode_for_tool(settings, "camofox") == "app-owned"
        and (not status.service_reachable or not status.health_ok)
    ):
        status = start_camofox_service(settings)
    if status.app_owned:
        settings.research_camofox_base_url = status.base_url
    return status


def ensure_runtime_tools(
    settings: Settings,
    *,
    include_camofox: bool = False,
) -> RuntimeToolBootstrapReport:
    """Ensure configured runtime side tools are ready for an operator action."""

    messages: list[str] = []
    model_status = ensure_model_service_if_configured(settings)
    messages.append(model_status.message)
    camofox_status = None
    if include_camofox:
        camofox_status = ensure_camofox_service_if_configured(settings)
        if camofox_status is not None:
            messages.append(camofox_status.message)
    return RuntimeToolBootstrapReport(
        model_service=model_status,
        camofox_service=camofox_status,
        messages=messages,
    )
