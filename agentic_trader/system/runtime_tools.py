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
    """
    Constructs the Ollama API base URL from a model service status.
    
    Parameters:
        status (ModelServiceStatus): Service status whose `base_url` is used to build the API endpoint.
    
    Returns:
        str | None: "`{base_url_without_trailing_slash}/v1`" if `status.base_url` is set, `None` otherwise.
    """
    if not status.base_url:
        return None
    return f"{status.base_url.rstrip('/')}/v1"


def _should_adopt_model_endpoint(
    settings: Settings,
    status: ModelServiceStatus,
) -> bool:
    return (
        settings.llm_provider == "ollama"
        and ownership_mode_for_tool(settings, "ollama") == "app-owned"
        and status.app_owned
    )


def _should_adopt_camofox_endpoint(
    settings: Settings,
    status: CamofoxServiceStatus,
) -> bool:
    return (
        ownership_mode_for_tool(settings, "camofox") == "app-owned"
        and status.app_owned
    )


def apply_app_owned_service_settings(
    settings: Settings,
    *,
    include_camofox: bool = False,
) -> RuntimeToolBootstrapReport:
    """
    Point Settings at endpoints of already-running app-owned helper services.
    
    Adjusts in-memory Settings to use the base URLs of app-owned model (and optionally
    Camofox) services when those services are detected as app-owned. This function
    does not start, stop, or modify any processes or files; it only updates in-memory
    settings and returns status information suitable for dashboards or diagnostics.
    
    Parameters:
        settings (Settings): Application settings object to read from and modify in memory.
        include_camofox (bool): If true, also inspect and apply the app-owned Camofox service URL.
    
    Returns:
        RuntimeToolBootstrapReport: Contains `model_service` (ModelServiceStatus),
        `camofox_service` (CamofoxServiceStatus or None), and `messages` (list of
        human-readable status messages).
    """

    messages: list[str] = []
    model_status = build_model_service_status(settings)
    if _should_adopt_model_endpoint(settings, model_status):
        runtime_base_url = _base_url_for_ollama_api(model_status)
        if runtime_base_url is not None:
            settings.base_url = runtime_base_url
            model_status = build_model_service_status(settings)
    messages.append(model_status.message)

    camofox_status = None
    if include_camofox:
        camofox_status = build_camofox_service_status(settings)
        if _should_adopt_camofox_endpoint(settings, camofox_status):
            settings.research_camofox_base_url = camofox_status.base_url
            camofox_status = build_camofox_service_status(settings)
        messages.append(camofox_status.message)

    return RuntimeToolBootstrapReport(
        model_service=model_status,
        camofox_service=camofox_status,
        messages=messages,
    )


def ensure_model_service_if_configured(settings: Settings) -> ModelServiceStatus:
    """
    Ensure an app-owned Ollama model service is running if configured and return its status.
    
    If Ollama is the configured LLM provider and auto-start and ownership are set to app-owned, this may start the model service when the configured endpoint is unreachable or the model is unavailable. When the resulting status indicates an app-owned service with a valid runtime base URL, `settings.base_url` will be updated to point at that service.
    
    Parameters:
        settings (Settings): In-memory settings that may be modified to set `base_url` for an app-owned Ollama service.
    
    Returns:
        ModelServiceStatus: The final status of the model service after any start attempt or configuration update.
    """

    status = build_model_service_status(settings)
    if (
        settings.llm_provider == "ollama"
        and settings.runtime_auto_start_model_service
        and ownership_mode_for_tool(settings, "ollama") == "app-owned"
        and (not status.service_reachable or not status.model_available)
    ):
        status = start_model_service(settings)
    if _should_adopt_model_endpoint(settings, status):
        runtime_base_url = _base_url_for_ollama_api(status)
        if runtime_base_url is not None:
            settings.base_url = runtime_base_url
    return status


def ensure_camofox_service_if_configured(settings: Settings) -> CamofoxServiceStatus | None:
    """
    Start or adopt an app-owned Camofox research service when configured.
    
    If research Camofox is enabled and ownership is set to "app-owned", this will start the app-owned Camofox service when auto-start is enabled and the service is not reachable or its health is not OK. When the resulting status indicates the service is app-owned, the function updates `settings.research_camofox_base_url` to the service's base URL.
    
    Returns:
        CamofoxServiceStatus: The current or newly-started Camofox service status.
        `None` if research Camofox is disabled.
    """

    if not settings.research_camofox_enabled:
        return None
    status = build_camofox_service_status(settings)
    if (
        settings.runtime_auto_start_camofox
        and ownership_mode_for_tool(settings, "camofox") == "app-owned"
        and (not status.service_reachable or not status.health_ok)
    ):
        status = start_camofox_service(settings)
    if _should_adopt_camofox_endpoint(settings, status):
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
