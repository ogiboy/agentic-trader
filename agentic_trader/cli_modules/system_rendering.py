from __future__ import annotations

from typing import cast

from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.ui_text import (
    LABEL_CAMOFOX,
    LABEL_CATEGORY,
    LABEL_CORE_READY,
    LABEL_FIELD,
    LABEL_MEANING,
    LABEL_MODE,
    LABEL_NEXT,
    LABEL_NOTES,
    LABEL_OPTIONAL_RUNTIME_READY,
    LABEL_OWNERSHIP,
    LABEL_PATH,
    LABEL_PLATFORM,
    LABEL_RUNTIME_DAEMON,
    LABEL_SETUP,
    LABEL_SOURCE,
    LABEL_STATUS,
    LABEL_SURFACE,
    LABEL_TOOL,
    LABEL_UPDATED,
    LABEL_VALUE,
    LABEL_WEB_GUI,
    LABEL_WORKSPACE,
    LAUNCHER_OPTION_CONTINUE_TUI,
    LAUNCHER_OPTION_EXIT,
    LAUNCHER_OPTION_OPEN_WEB_GUI,
    LAUNCHER_OPTION_REFRESH,
    STATUS_ACTIVE,
    STATUS_APP_OWNED,
    STATUS_EXTERNAL,
    STATUS_NEEDS_ATTENTION,
    STATUS_READY,
    TITLE_AVAILABLE_MODELS,
    TITLE_CAMOFOX_BROWSER_HELPER,
    TITLE_CAMOFOX_STDERR_TAIL,
    TITLE_CHOOSE_SURFACE,
    TITLE_MODEL_SERVICE_STDERR_TAIL,
    TITLE_OPERATOR_LAUNCHER,
    TITLE_RECOMMENDED_NEXT_COMMANDS,
    TITLE_SETUP_STATUS,
    TITLE_TOOL_OWNERSHIP,
    TITLE_TOOL_READINESS,
    TITLE_WEB_GUI_SERVICE,
    TITLE_WEB_GUI_STDERR_TAIL,
    t,
)

LABEL_MODEL_SERVICE = t("label.model_service")


def render_setup_status(payload: dict[str, object]) -> None:
    summary = Table(title=TITLE_SETUP_STATUS)
    summary.add_column(LABEL_FIELD)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_PLATFORM, str(payload["platform"]))
    summary.add_row(LABEL_WORKSPACE, str(payload["workspace_root"]))
    summary.add_row(LABEL_CORE_READY, str(payload["core_ready"]))
    summary.add_row(LABEL_OPTIONAL_RUNTIME_READY, str(payload["optional_ready"]))
    model_service = cast(dict[str, object], payload.get("model_service", {}))
    camofox_service = cast(dict[str, object], payload.get("camofox_service", {}))
    webgui_service = cast(dict[str, object], payload.get("webgui_service", {}))
    summary.add_row(LABEL_MODEL_SERVICE, str(model_service.get("message", "-")))
    summary.add_row(LABEL_CAMOFOX, str(camofox_service.get("message", "-")))
    summary.add_row(LABEL_WEB_GUI, str(webgui_service.get("message", "-")))
    console.print(summary)

    ownership = cast(dict[str, object] | None, payload.get("tool_ownership"))
    if ownership is not None:
        render_tool_ownership(ownership)
    _render_tool_readiness(payload)


def _render_tool_readiness(payload: dict[str, object]) -> None:
    tools = cast(list[dict[str, object]], payload["tools"])
    table = Table(title=TITLE_TOOL_READINESS)
    table.add_column(LABEL_TOOL)
    table.add_column(LABEL_CATEGORY)
    table.add_column(LABEL_OWNERSHIP)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_PATH)
    table.add_column(LABEL_NOTES)
    for tool in tools:
        notes = ", ".join(cast(list[str], tool.get("notes", [])))
        table.add_row(
            str(tool["label"]),
            str(tool["category"]),
            str(tool.get("ownership_mode") or "-"),
            str(tool["status"]),
            str(tool.get("path") or "-"),
            notes or str(tool.get("install_hint") or "-"),
        )
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["recommended_commands"])),
            title=TITLE_RECOMMENDED_NEXT_COMMANDS,
            border_style="cyan",
        )
    )


def render_tool_ownership(payload: dict[str, object]) -> None:
    table = Table(title=TITLE_TOOL_OWNERSHIP)
    table.add_column(LABEL_TOOL)
    table.add_column(LABEL_MODE)
    table.add_column(LABEL_SOURCE)
    table.add_column(LABEL_UPDATED)
    table.add_column(LABEL_MEANING)
    decisions = cast(list[dict[str, object]], payload.get("decisions", []))
    for decision in decisions:
        table.add_row(
            str(decision.get("tool", "-")),
            str(decision.get("mode", "-")),
            str(decision.get("source", "-")),
            str(decision.get("updated_at") or "-"),
            str(decision.get("note", "-")),
        )
    console.print(table)


def render_model_service_status(payload: dict[str, object]) -> None:
    table = Table(title=LABEL_MODEL_SERVICE)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    for key in (
        "provider",
        "command_available",
        "command_path",
        "configured_base_url",
        "configured_model",
        "service_reachable",
        "model_available",
        "generation_checked",
        "generation_available",
        "generation_message",
        "app_owned",
        "pid",
        "base_url",
        "message",
        "runtime_base_url_matches_app_service",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload.get("available_models", []))) or "-",
            title=TITLE_AVAILABLE_MODELS,
            border_style="green",
        )
    )
    _render_tail(payload, key="stderr_tail", title=TITLE_MODEL_SERVICE_STDERR_TAIL)


def render_webgui_service_status(payload: dict[str, object]) -> None:
    table = Table(title=TITLE_WEB_GUI_SERVICE)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    for key in (
        "command_available",
        "command_path",
        "package_available",
        "service_reachable",
        "app_owned",
        "pid",
        "host",
        "port",
        "url",
        "message",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    _render_tail(payload, key="stderr_tail", title=TITLE_WEB_GUI_STDERR_TAIL)


def render_camofox_service_status(payload: dict[str, object]) -> None:
    table = Table(title=TITLE_CAMOFOX_BROWSER_HELPER)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    for key in (
        "command_available",
        "command_path",
        "package_available",
        "dependency_available",
        "access_key_configured",
        "service_reachable",
        "health_ok",
        "app_owned",
        "pid",
        "host",
        "port",
        "base_url",
        "tool_dir",
        "message",
    ):
        table.add_row(key, str(payload.get(key, "-")))
    console.print(table)
    _render_tail(payload, key="stderr_tail", title=TITLE_CAMOFOX_STDERR_TAIL)


def render_operator_launcher_status(payload: dict[str, object]) -> None:
    plan = cast(dict[str, object], payload["default_runtime_plan"])
    model_service = cast(dict[str, object], payload["model_service"])
    camofox_service = cast(dict[str, object], payload["camofox_service"])
    webgui_service = cast(dict[str, object], payload["webgui_service"])
    setup = cast(dict[str, object], payload["setup"])
    table = Table(title=TITLE_OPERATOR_LAUNCHER)
    table.add_column(LABEL_SURFACE)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_NEXT)
    table.add_row(
        LABEL_RUNTIME_DAEMON,
        STATUS_ACTIVE if payload["runtime_active"] else str(payload["runtime_state"]),
        (
            f"{', '.join(cast(list[str], plan['symbols']))} "
            f"{plan['interval']} {plan['lookback']} / poll {plan['poll_seconds']}s"
        ),
    )
    table.add_row(
        LABEL_WEB_GUI,
        _webgui_status_label(webgui_service),
        str(webgui_service.get("url") or "agentic-trader webgui-service start"),
    )
    table.add_row(
        LABEL_MODEL_SERVICE,
        (
            STATUS_READY
            if model_service.get("model_available")
            else str(model_service.get("message"))
        ),
        str(model_service.get("base_url") or model_service.get("configured_base_url")),
    )
    table.add_row(
        LABEL_CAMOFOX,
        (
            STATUS_READY
            if camofox_service.get("health_ok")
            else str(camofox_service.get("message"))
        ),
        str(camofox_service.get("base_url") or "agentic-trader camofox-service start"),
    )
    table.add_row(
        LABEL_SETUP,
        STATUS_READY if setup.get("core_ready") else STATUS_NEEDS_ATTENTION,
        "agentic-trader setup-status --json",
    )
    console.print(table)
    console.print(
        Panel(
            "\n".join(
                [
                    LAUNCHER_OPTION_OPEN_WEB_GUI,
                    LAUNCHER_OPTION_CONTINUE_TUI,
                    LAUNCHER_OPTION_REFRESH,
                    LAUNCHER_OPTION_EXIT,
                ]
            ),
            title=TITLE_CHOOSE_SURFACE,
            border_style="cyan",
        )
    )


def _webgui_status_label(webgui_service: dict[str, object]) -> str:
    if webgui_service.get("app_owned"):
        return STATUS_APP_OWNED
    if webgui_service.get("service_reachable"):
        return STATUS_EXTERNAL
    return str(webgui_service.get("message"))


def _render_tail(payload: dict[str, object], *, key: str, title: str) -> None:
    tail = cast(list[str], payload.get(key, []))
    if tail:
        console.print(Panel("\n".join(tail), title=title, border_style="yellow"))
