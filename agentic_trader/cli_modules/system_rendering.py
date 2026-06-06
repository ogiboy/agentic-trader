from __future__ import annotations

from typing import cast

from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.ui_text import (
    t,
)

MODEL_SERVICE_LABEL = t("label.model_service")


def render_setup_status(payload: dict[str, object]) -> None:
    summary = Table(title=t("title.setup_status"))
    summary.add_column(t("label.field"))
    summary.add_column(t("label.value"))
    summary.add_row(t("label.platform"), str(payload["platform"]))
    summary.add_row(t("label.workspace"), str(payload["workspace_root"]))
    summary.add_row(t("label.core_ready"), str(payload["core_ready"]))
    summary.add_row(t("label.optional_runtime_ready"), str(payload["optional_ready"]))
    model_service = cast(dict[str, object], payload.get("model_service", {}))
    camofox_service = cast(dict[str, object], payload.get("camofox_service", {}))
    webgui_service = cast(dict[str, object], payload.get("webgui_service", {}))
    summary.add_row(MODEL_SERVICE_LABEL, str(model_service.get("message", "-")))
    summary.add_row(t("label.camofox"), str(camofox_service.get("message", "-")))
    summary.add_row(t("label.web_gui"), str(webgui_service.get("message", "-")))
    console.print(summary)

    ownership = cast(dict[str, object] | None, payload.get("tool_ownership"))
    if ownership is not None:
        render_tool_ownership(ownership)
    _render_tool_readiness(payload)


def _render_tool_readiness(payload: dict[str, object]) -> None:
    tools = cast(list[dict[str, object]], payload["tools"])
    table = Table(title=t("title.tool_readiness"))
    table.add_column(t("label.tool"))
    table.add_column(t("label.category"))
    table.add_column(t("label.ownership"))
    table.add_column(t("label.status"))
    table.add_column(t("label.path"))
    table.add_column(t("label.notes"))
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
            title=t("title.recommended_next_commands"),
            border_style="cyan",
        )
    )


def render_tool_ownership(payload: dict[str, object]) -> None:
    table = Table(title=t("title.tool_ownership"))
    table.add_column(t("label.tool"))
    table.add_column(t("label.mode"))
    table.add_column(t("label.source"))
    table.add_column(t("label.updated"))
    table.add_column(t("label.meaning"))
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
    table = Table(title=MODEL_SERVICE_LABEL)
    table.add_column(t("label.field"))
    table.add_column(t("label.value"))
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
            title=t("title.available_models"),
            border_style="green",
        )
    )
    _render_tail(payload, key="stderr_tail", title=t("title.model_service_stderr_tail"))


def render_webgui_service_status(payload: dict[str, object]) -> None:
    table = Table(title=t("title.web_gui_service"))
    table.add_column(t("label.field"))
    table.add_column(t("label.value"))
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
    _render_tail(payload, key="stderr_tail", title=t("title.web_gui_stderr_tail"))


def render_camofox_service_status(payload: dict[str, object]) -> None:
    table = Table(title=t("title.camofox_browser_helper"))
    table.add_column(t("label.field"))
    table.add_column(t("label.value"))
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
    _render_tail(payload, key="stderr_tail", title=t("title.camofox_stderr_tail"))


def render_operator_launcher_status(payload: dict[str, object]) -> None:
    plan = cast(dict[str, object], payload["default_runtime_plan"])
    model_service = cast(dict[str, object], payload["model_service"])
    camofox_service = cast(dict[str, object], payload["camofox_service"])
    webgui_service = cast(dict[str, object], payload["webgui_service"])
    setup = cast(dict[str, object], payload["setup"])
    table = Table(title=t("title.operator_launcher"))
    table.add_column(t("label.surface"))
    table.add_column(t("label.status"))
    table.add_column(t("label.next"))
    table.add_row(
        t("label.runtime_daemon"),
        (
            t("status.active")
            if payload["runtime_active"]
            else str(payload["runtime_state"])
        ),
        (
            f"{', '.join(cast(list[str], plan['symbols']))} "
            f"{plan['interval']} {plan['lookback']} / poll {plan['poll_seconds']}s"
        ),
    )
    table.add_row(
        t("label.web_gui"),
        _webgui_status_label(webgui_service),
        str(webgui_service.get("url") or "agentic-trader webgui-service start"),
    )
    table.add_row(
        MODEL_SERVICE_LABEL,
        (
            t("status.ready")
            if model_service.get("model_available")
            else str(model_service.get("message"))
        ),
        str(model_service.get("base_url") or model_service.get("configured_base_url")),
    )
    table.add_row(
        t("label.camofox"),
        (
            t("status.ready")
            if camofox_service.get("health_ok")
            else str(camofox_service.get("message"))
        ),
        str(camofox_service.get("base_url") or "agentic-trader camofox-service start"),
    )
    table.add_row(
        t("label.setup"),
        t("status.ready") if setup.get("core_ready") else t("status.needs_attention"),
        "agentic-trader setup-status --json",
    )
    console.print(table)
    console.print(
        Panel(
            "\n".join(
                [
                    t("launcher.option_open_web_gui"),
                    t("launcher.option_continue_tui"),
                    t("launcher.option_refresh"),
                    t("launcher.option_exit"),
                ]
            ),
            title=t("title.choose_surface"),
            border_style="cyan",
        )
    )


def _webgui_status_label(webgui_service: dict[str, object]) -> str:
    if webgui_service.get("app_owned"):
        return t("status.app_owned")
    if webgui_service.get("service_reachable"):
        return t("status.external")
    return str(webgui_service.get("message"))


def _render_tail(payload: dict[str, object], *, key: str, title: str) -> None:
    tail = cast(list[str], payload.get(key, []))
    if tail:
        console.print(Panel("\n".join(tail), title=title, border_style="yellow"))
