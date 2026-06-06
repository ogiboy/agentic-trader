"""CLI wiring for system-service command groups."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

import typer

from agentic_trader.cli_modules.system_commands import (
    SystemCommandDeps,
    register_system_commands,
)
from agentic_trader.config import Settings
from agentic_trader.system.camofox_service import (
    build_camofox_service_status,
    start_camofox_service,
    stop_camofox_service,
)
from agentic_trader.system.model_service import (
    build_model_service_status,
    pull_model,
    start_model_service,
    stop_model_service,
)
from agentic_trader.system.operator_launcher import start_operator_webgui
from agentic_trader.system.setup import build_setup_status
from agentic_trader.system.tool_ownership import (
    OWNERSHIP_MODES,
    read_tool_ownership_payload,
    validate_ownership_mode,
    write_tool_ownership,
)
from agentic_trader.system.webgui_service import (
    build_webgui_service_status,
    stop_webgui_service,
)
from agentic_trader.ui_text import t as ui_t

SettingsProvider = Callable[[], Settings]
JsonEmitter = Callable[[object], None]
ServiceRegistry = Mapping[str, Callable[..., Any]]
ServiceNamespace = object | ServiceRegistry

_DEFAULT_SERVICES: ServiceRegistry = {
    "validate_ownership_mode": validate_ownership_mode,
    "build_setup_status": build_setup_status,
    "read_tool_ownership_payload": read_tool_ownership_payload,
    "write_tool_ownership": write_tool_ownership,
    "build_model_service_status": build_model_service_status,
    "start_model_service": start_model_service,
    "stop_model_service": stop_model_service,
    "pull_model": pull_model,
    "build_webgui_service_status": build_webgui_service_status,
    "start_operator_webgui": start_operator_webgui,
    "stop_webgui_service": stop_webgui_service,
    "build_camofox_service_status": build_camofox_service_status,
    "start_camofox_service": start_camofox_service,
    "stop_camofox_service": stop_camofox_service,
}


def _service(namespace: ServiceNamespace, name: str) -> Callable[..., Any]:
    if isinstance(namespace, Mapping):
        return cast(Callable[..., Any], namespace[name])
    return cast(Callable[..., Any], getattr(namespace, name))


def _service_namespace(namespace: ServiceNamespace | None) -> ServiceNamespace:
    return namespace if namespace is not None else _DEFAULT_SERVICES


@dataclass(frozen=True)
class SystemServiceRegistry:
    services: ServiceNamespace

    def validate_ownership_mode(self, value: str) -> str:
        return cast(str, _service(self.services, "validate_ownership_mode")(value))

    def build_setup_status(self, settings: Settings) -> object:
        return _service(self.services, "build_setup_status")(settings)

    def read_tool_ownership_payload(self, settings: Settings) -> object:
        return _service(self.services, "read_tool_ownership_payload")(settings)

    def write_tool_ownership(
        self, settings: Settings, updates: dict[str, str], source: str
    ) -> object:
        return _service(self.services, "write_tool_ownership")(
            settings,
            updates,
            source=source,
        )

    def build_model_service_status(
        self, settings: Settings, *, include_generation: bool = False
    ) -> object:
        return _service(self.services, "build_model_service_status")(
            settings,
            include_generation=include_generation,
        )

    def start_model_service(
        self, settings: Settings, *, host: str | None = None, port: int | None = None
    ) -> object:
        return _service(self.services, "start_model_service")(
            settings,
            host=host,
            port=port,
        )

    def stop_model_service(self, settings: Settings) -> object:
        return _service(self.services, "stop_model_service")(settings)

    def pull_model(self, settings: Settings, model_name: str) -> dict[str, object]:
        return cast(
            dict[str, object],
            _service(self.services, "pull_model")(settings, model_name),
        )

    def build_webgui_service_status(self, settings: Settings) -> object:
        return _service(self.services, "build_webgui_service_status")(settings)

    def start_operator_webgui(
        self, settings: Settings, *, open_browser: bool = True
    ) -> object:
        return _service(self.services, "start_operator_webgui")(
            settings,
            open_browser=open_browser,
        )

    def stop_webgui_service(self, settings: Settings) -> object:
        return _service(self.services, "stop_webgui_service")(settings)

    def build_camofox_service_status(self, settings: Settings) -> object:
        return _service(self.services, "build_camofox_service_status")(settings)

    def start_camofox_service(
        self, settings: Settings, *, host: str | None = None, port: int | None = None
    ) -> object:
        return _service(self.services, "start_camofox_service")(
            settings,
            host=host,
            port=port,
        )

    def stop_camofox_service(self, settings: Settings) -> object:
        return _service(self.services, "stop_camofox_service")(settings)


def system_command_deps(
    *,
    settings_provider: SettingsProvider,
    emit_json: JsonEmitter,
    service_namespace: ServiceNamespace | None = None,
) -> SystemCommandDeps:
    registry = SystemServiceRegistry(_service_namespace(service_namespace))
    return SystemCommandDeps(
        get_settings=settings_provider,
        emit_json=emit_json,
        ownership_modes=OWNERSHIP_MODES,
        validate_ownership_mode=registry.validate_ownership_mode,
        build_setup_status=registry.build_setup_status,
        read_tool_ownership_payload=registry.read_tool_ownership_payload,
        write_tool_ownership=registry.write_tool_ownership,
        build_model_service_status=registry.build_model_service_status,
        start_model_service=registry.start_model_service,
        stop_model_service=registry.stop_model_service,
        pull_model=registry.pull_model,
        build_webgui_service_status=registry.build_webgui_service_status,
        start_operator_webgui=registry.start_operator_webgui,
        stop_webgui_service=registry.stop_webgui_service,
        build_camofox_service_status=registry.build_camofox_service_status,
        start_camofox_service=registry.start_camofox_service,
        stop_camofox_service=registry.stop_camofox_service,
    )


def register_cli_system_commands(
    app: typer.Typer,
    *,
    settings_provider: SettingsProvider,
    emit_json: JsonEmitter,
    service_namespace: ServiceNamespace | None = None,
) -> None:
    model_service_app = typer.Typer(help=ui_t("help.model_service_app"))
    app.add_typer(model_service_app, name="model-service")
    webgui_service_app = typer.Typer(help=ui_t("help.webgui_service_app"))
    app.add_typer(webgui_service_app, name="webgui-service")
    camofox_service_app = typer.Typer(help=ui_t("help.camofox_service_app"))
    app.add_typer(camofox_service_app, name="camofox-service")
    tool_ownership_app = typer.Typer(help=ui_t("help.tool_ownership_app"))
    app.add_typer(tool_ownership_app, name="tool-ownership")
    register_system_commands(
        app=app,
        tool_ownership_app=tool_ownership_app,
        model_service_app=model_service_app,
        webgui_service_app=webgui_service_app,
        camofox_service_app=camofox_service_app,
        deps=system_command_deps(
            settings_provider=settings_provider,
            emit_json=emit_json,
            service_namespace=service_namespace,
        ),
    )
