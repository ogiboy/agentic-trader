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
    """
    Prints a table summarizing system setup status and, if present, renders tool ownership and tool readiness sections.
    
    Parameters:
        payload (dict[str, object]): A mapping containing setup information used to populate the table. Expected keys:
            - "platform": platform identifier shown under the Platform field.
            - "workspace_root": workspace path shown under the Workspace field.
            - "core_ready": core readiness value shown under the Core Ready field.
            - "optional_ready": optional runtime readiness value shown under the Optional Runtime Ready field.
            - "model_service", "camofox_service", "webgui_service": optional dicts whose "message" values are shown under their respective service rows (falls back to "-" if missing).
            - "tool_ownership": optional dict; when present, the function will render a tool ownership section using its value.
            - other keys used later by the tool readiness renderer (e.g., "tools", "recommended_commands") may be read by the subsequent tool readiness rendering.
    """
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
    """
    Render a table of tool readiness and a panel of recommended next commands.
    
    Parameters:
        payload (dict[str, object]): Rendering context containing:
            - "tools": list[dict[str, object]] where each tool dict must include
              "label", "category", and "status"; optional keys: "notes" (list[str]),
              "ownership_mode", "path", and "install_hint".
            - "recommended_commands": list[str] of commands shown in the recommended
              next commands panel.
    
    """
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
    """
    Render a table of tool ownership decisions.
    
    Builds and prints a Rich Table titled with the localized "tool ownership" label and one row per decision.
    
    Parameters:
    	payload (dict[str, object]): Mapping that may contain a "decisions" key with a list of decision mappings. Each decision may include:
    		- "tool": display name of the tool
    		- "mode": ownership mode
    		- "source": origin of the decision
    		- "updated_at": timestamp of the last update
    		- "note": human-readable meaning or comment
    
    """
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
    """
    Render and print the model service status table, the list of available models, and the service stderr tail if present.
    
    Parameters:
        payload (dict[str, object]): Mapping with model service information. The function reads the following keys (falling back to "-" when absent): "provider", "command_available", "command_path", "configured_base_url", "configured_model", "service_reachable", "model_available", "generation_checked", "generation_available", "generation_message", "app_owned", "pid", "base_url", "message", "runtime_base_url_matches_app_service". Also reads "available_models" (iterable of model names) to display in a panel and "stderr_tail" (list of lines) to display as a tail panel when present.
    """
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
    """
    Render the web GUI service status and its stderr tail to the console.
    
    Parameters:
        payload (dict[str, object]): Status dictionary for the web GUI service. Expected keys read from
            the payload: "command_available", "command_path", "package_available", "service_reachable",
            "app_owned", "pid", "host", "port", "url", "message", and optionally "stderr_tail".
            Missing keys are represented as "-" in the output.
    """
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
    """
    Render a table summarizing the Camofox browser helper service status and its stderr tail.
    
    Parameters:
        payload (dict[str, object]): Mapping containing service status fields. Recognized keys include:
            - "command_available", "command_path", "package_available", "dependency_available",
              "access_key_configured", "service_reachable", "health_ok", "app_owned",
              "pid", "host", "port", "base_url", "tool_dir", "message"
            Missing keys are displayed as "-" in the table. If "stderr_tail" is present and non-empty,
            its lines are rendered in a separate titled panel.
    """
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
    """
    Render the operator launcher status table and present available launcher surface options.
    
    Parameters:
        payload (dict[str, object]): Status payload containing expected keys:
            - "default_runtime_plan": dict with plan fields "symbols", "interval", "lookback", "poll_seconds"
            - "model_service": dict with "model_available", "base_url", "configured_base_url", "message"
            - "camofox_service": dict with "health_ok", "base_url", "message"
            - "webgui_service": dict with "app_owned", "service_reachable", "url", "message"
            - "setup": dict with "core_ready"
            - "runtime_active": truthy when the runtime daemon is active
            - "runtime_state": fallback runtime state to display when not active
    """
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
    """
    Choose a localized status label for the web GUI service.
    
    Returns:
        str: `t("status.app_owned")` if `webgui_service["app_owned"]` is truthy, `t("status.external")` if `webgui_service["service_reachable"]` is truthy, otherwise the service's `message` coerced to a string.
    """
    if webgui_service.get("app_owned"):
        return t("status.app_owned")
    if webgui_service.get("service_reachable"):
        return t("status.external")
    return str(webgui_service.get("message"))


def _render_tail(payload: dict[str, object], *, key: str, title: str) -> None:
    tail = cast(list[str], payload.get(key, []))
    if tail:
        console.print(Panel("\n".join(tail), title=title, border_style="yellow"))
