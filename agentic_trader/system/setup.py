"""Read-only setup and optional tool readiness contracts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.researchd.crewai_setup import crewai_setup_status
from agentic_trader.security import is_loopback_host, redact_sensitive_text
from agentic_trader.system.camofox_service import build_camofox_service_status
from agentic_trader.system.model_service import build_model_service_status
from agentic_trader.system.tool_ownership import (
    ToolOwnershipPayload,
    ownership_tool_for_local_tool,
    read_tool_ownership_payload,
)
from agentic_trader.system.tool_roots import (
    LocalToolId,
    local_tool_definition,
    local_tool_manifest_notes,
    repo_root,
    resolve_configured_tool_path,
)
from agentic_trader.system.webgui_service import build_webgui_service_status

ToolCategory = Literal["core", "runtime_optional", "developer_optional"]
CAMOFOX_TOOL_ID: LocalToolId = "camofox-browser"


class ToolStatus(BaseModel):
    """Setup/readiness state for one local tool."""

    tool_id: str
    label: str
    category: ToolCategory
    available: bool
    required_for_core: bool = False
    path: str | None = None
    version: str | None = None
    status: str = "missing"
    notes: list[str] = Field(default_factory=list)
    install_hint: str | None = None
    ownership_tool: str | None = None
    ownership_mode: str | None = None
    ownership_note: str | None = None


class SetupStatus(BaseModel):
    """Operator-facing workspace and side-application readiness."""

    platform: str
    workspace_root: str
    core_ready: bool
    optional_ready: bool
    tools: list[ToolStatus]
    tool_ownership: ToolOwnershipPayload | None = None
    model_service: dict[str, object]
    camofox_service: dict[str, object]
    webgui_service: dict[str, object]
    recommended_commands: list[str]


def _repo_root() -> Path:
    return repo_root()


def _command_version(command: str, args: list[str] | None = None) -> str | None:
    path = shutil.which(command)
    if path is None:
        return None
    try:
        completed = subprocess.run(
            [path, *(args or ["--version"])],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        return f"version check failed: {redact_sensitive_text(exc, max_length=120)}"
    output = (completed.stdout or completed.stderr).strip()
    return redact_sensitive_text(
        output.splitlines()[0] if output else "", max_length=160
    )


def _command_tool(
    *,
    tool_id: str,
    label: str,
    category: ToolCategory,
    command: str,
    required_for_core: bool = False,
    install_hint: str | None = None,
    version_args: list[str] | None = None,
) -> ToolStatus:
    path = shutil.which(command)
    return ToolStatus(
        tool_id=tool_id,
        label=label,
        category=category,
        available=path is not None,
        required_for_core=required_for_core,
        path=path,
        version=_command_version(command, version_args) if path else None,
        status="available" if path else "missing",
        install_hint=install_hint,
    )


def _firecrawl_tool() -> ToolStatus:
    definition = local_tool_definition("firecrawl")
    tool = _command_tool(
        tool_id=definition.status_tool_id,
        label=definition.label,
        category="runtime_optional",
        command="firecrawl",
        install_hint=definition.install_hint,
        version_args=["--version"],
    )
    tool = _with_manifest_note(tool, "firecrawl")
    if not tool.available:
        return tool
    try:
        completed = subprocess.run(
            [tool.path or "firecrawl", "--status"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        status_text = redact_sensitive_text(
            (completed.stdout or completed.stderr).strip(),
            max_length=500,
        )
        authenticated = "Authenticated" in status_text or "Logged in" in status_text
        notes = [*tool.notes]
        if status_text:
            notes.append(status_text)
        return tool.model_copy(
            update={
                "status": "authenticated" if authenticated else "needs_auth",
                "notes": notes,
            }
        )
    except Exception as exc:
        return tool.model_copy(
            update={
                "status": "status_failed",
                "notes": [
                    *tool.notes,
                    f"firecrawl status failed: {redact_sensitive_text(exc, max_length=160)}",
                ],
            }
        )


def _with_manifest_note(tool: ToolStatus, tool_id: LocalToolId) -> ToolStatus:
    """
    Append manifest-derived notes for the given local tool identifier to a ToolStatus and return an updated copy.

    Parameters:
        tool (ToolStatus): The original tool status to augment; unchanged by this function.
        tool_id (LocalToolId): Identifier of the local tool whose manifest notes will be appended.

    Returns:
        ToolStatus: A copy of `tool` with `notes` extended by the manifest-derived notes for `tool_id`.
    """
    return tool.model_copy(
        update={"notes": [*tool.notes, *local_tool_manifest_notes(tool_id)]}
    )


def _with_ownership_note(
    tool: ToolStatus,
    tool_id: LocalToolId,
    ownership: ToolOwnershipPayload,
) -> ToolStatus:
    """
    Attach ownership decision metadata to a ToolStatus and return an updated copy.

    Parameters:
        tool (ToolStatus): Existing tool status to augment.
        tool_id (LocalToolId): Local tool identifier used to look up the ownership decision.
        ownership (ToolOwnershipPayload): Ownership payload containing decisions indexed by ownership tool id.

    Returns:
        ToolStatus: A copy of `tool` with `ownership_tool`, `ownership_mode`, and `ownership_note` set from the decision,
        and with ownership-related entries appended to the `notes` list.
    """
    ownership_tool = ownership_tool_for_local_tool(tool_id)
    decision = ownership.decisions_by_tool[ownership_tool]
    return tool.model_copy(
        update={
            "ownership_tool": decision.tool,
            "ownership_mode": decision.mode,
            "ownership_note": decision.note,
            "notes": [
                *tool.notes,
                f"ownership={decision.mode}",
                f"ownership_source={decision.source}",
                decision.note,
            ],
        }
    )


def _ollama_tool() -> ToolStatus:
    """
    Report readiness and metadata for the Ollama CLI tool.

    Builds a ToolStatus representing whether the local `ollama` executable is available, its resolved path/version if present, and any manifest-derived notes relevant to the tool.

    Returns:
        ToolStatus: Readiness and metadata for the Ollama CLI, including availability, path, version, status, notes, and manifest notes when applicable.
    """
    definition = local_tool_definition("ollama")
    tool = _command_tool(
        tool_id=definition.status_tool_id,
        label=definition.label,
        category="runtime_optional",
        command="ollama",
        install_hint=definition.install_hint,
    )
    return _with_manifest_note(tool, "ollama")


def _camofox_tool(settings: Settings) -> ToolStatus:
    definition = local_tool_definition(CAMOFOX_TOOL_ID)
    root = resolve_configured_tool_path(
        settings.research_camofox_tool_dir,
        default_tool=CAMOFOX_TOOL_ID,
    )
    package_json = root / "package.json"
    server_js = root / "server.js"
    available = package_json.exists() and server_js.exists()
    status = "available" if available else "missing"
    version, notes = _camofox_package_version(package_json)
    if available:
        notes.extend(
            _camofox_manifest_notes(definition.status_tool_id, definition.label)
        )
        status, health_notes = _camofox_health_status(settings)
        notes.extend(health_notes)
    return ToolStatus(
        tool_id=definition.status_tool_id,
        label=definition.label,
        category="runtime_optional",
        available=available,
        path=str(root) if available else None,
        version=version or None,
        status=status,
        notes=notes,
        install_hint=definition.install_hint,
    )


def build_camofox_tool_status(settings: Settings) -> ToolStatus:
    """Build the setup/readiness status for the optional Camofox helper."""
    return _camofox_tool(settings)


def _camofox_package_version(package_json: Path) -> tuple[str | None, list[str]]:
    if not package_json.exists():
        return None, []
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except Exception:
        return None, ["package_json_unreadable"]
    return str(payload.get("version") or "") or None, []


def _camofox_manifest_notes(tool_id: str, label: str) -> list[str]:
    return _with_manifest_note(
        ToolStatus(
            tool_id=tool_id,
            label=label,
            category="runtime_optional",
            available=True,
        ),
        CAMOFOX_TOOL_ID,
    ).notes


def _camofox_access_key_configured(settings: Settings) -> bool:
    return bool(
        settings.camofox_access_key
        or os.environ.get("CAMOFOX_ACCESS_KEY", "").strip()
        or settings.camofox_api_key
        or os.environ.get("CAMOFOX_API_KEY", "").strip()
    )


def _camofox_health_status(settings: Settings) -> tuple[str, list[str]]:
    notes: list[str] = []
    host = urlparse(settings.research_camofox_base_url).hostname or ""
    if not is_loopback_host(host):
        return "unsafe_base_url", ["health_probe_skipped_non_loopback_base_url"]
    try:
        response = httpx.get(
            f"{settings.research_camofox_base_url.rstrip('/')}/health",
            timeout=2,
        )
    except Exception:
        return "available", ["health_endpoint_unreachable"]
    if 200 <= response.status_code < 300:
        notes.append("health_endpoint_reachable")
        if _camofox_access_key_configured(settings):
            return "healthy", notes
        notes.append("access_key_not_configured_start_with_wrapper")
        return "healthy_unkeyed", notes
    return "unhealthy", [f"health_status={response.status_code}"]


def _agentic_trader_entrypoint() -> ToolStatus:
    tool = _command_tool(
        tool_id="agentic_trader_entrypoint",
        label="agentic-trader PATH entrypoint",
        category="core",
        command="agentic-trader",
        required_for_core=False,
        install_hint="Run `uv sync --locked --python 3.13 --all-extras --group dev`; optionally symlink .venv/bin/agentic-trader into ~/.local/bin.",
        version_args=["--help"],
    )
    if tool.available:
        expected = _repo_root() / ".venv" / "bin" / "agentic-trader"
        resolved = Path(str(tool.path)).expanduser()
        notes = ["entrypoint_resolves_on_path"]
        status = "available"
        if expected.exists():
            try:
                path_drift = resolved.resolve() != expected.resolve()
            except OSError:
                path_drift = str(resolved) != str(expected)
            if path_drift:
                status = "path_drift"
                notes.append(f"expected_repo_entrypoint={expected}")
        else:
            notes.append("repo_entrypoint_not_installed_yet")
        return tool.model_copy(
            update={"version": None, "status": status, "notes": notes}
        )
    return tool


def build_agentic_trader_entrypoint_status() -> ToolStatus:
    """Build the setup/readiness status for the repo CLI entrypoint."""
    return _agentic_trader_entrypoint()


def _ownership_mode(ownership: ToolOwnershipPayload, tool: str) -> str:
    decision = ownership.decisions_by_tool.get(tool)
    return decision.mode if decision is not None else "undecided"


def _model_service_ready(
    settings: Settings,
    ownership: ToolOwnershipPayload,
    model_service: dict[str, object],
) -> bool:
    if settings.llm_provider != "ollama":
        return True
    mode = _ownership_mode(ownership, "ollama")
    if mode in {"undecided", "skipped"}:
        return False
    return bool(model_service.get("service_reachable")) and bool(
        model_service.get("model_available")
    )


def _camofox_service_ready(
    ownership: ToolOwnershipPayload,
    camofox_service: dict[str, object],
) -> bool:
    mode = _ownership_mode(ownership, "camofox")
    if mode in {"app-owned", "host-owned"}:
        return bool(camofox_service.get("service_reachable"))
    return mode != "undecided"


def _single_line_optional(value: object, *, max_length: int = 160) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    first_line = next((line.strip() for line in value.splitlines() if line.strip()), "")
    return redact_sensitive_text(first_line, max_length=max_length) or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in cast(list[object], value)]


def build_setup_status(settings: Settings) -> SetupStatus:
    """
    Build an operator-facing read-only setup and readiness report for the current workspace.

    Constructs a snapshot of platform and workspace information, per-tool readiness (core, runtime-optional, developer-optional), optional tool ownership metadata, and service status summaries without installing, mutating, or performing persistent changes.

    Parameters:
        settings (Settings): Runtime configuration used to resolve tool locations, service endpoints, and ownership payloads.

    Returns:
        SetupStatus: Aggregated readiness report containing platform and workspace root, booleans `core_ready` and `optional_ready`, a list of `ToolStatus` entries (including ownership fields when available), optional `tool_ownership` payload, JSON-serializable service status objects for model/camofox/webgui, and recommended operator commands.
    """

    root = _repo_root()
    ownership = read_tool_ownership_payload(settings)
    tools = _setup_tools(settings, ownership)
    core_ready = all(tool.available for tool in tools if tool.required_for_core)
    model_service = build_model_service_status(settings).model_dump(mode="json")
    camofox_service = build_camofox_service_status(settings).model_dump(mode="json")
    webgui_service = build_webgui_service_status(settings).model_dump(mode="json")
    optional_ready = _model_service_ready(
        settings, ownership, model_service
    ) and _camofox_service_ready(ownership, camofox_service)
    return SetupStatus(
        platform=platform.system(),
        workspace_root=str(root),
        core_ready=core_ready,
        optional_ready=optional_ready,
        tools=tools,
        tool_ownership=ownership,
        model_service=model_service,
        camofox_service=camofox_service,
        recommended_commands=_recommended_setup_commands(),
        webgui_service=webgui_service,
    )


def _setup_tools(
    settings: Settings, ownership: ToolOwnershipPayload
) -> list[ToolStatus]:
    crewai = crewai_setup_status(settings)
    crewai_notes = _string_list(crewai.get("notes"))
    return [
        _command_tool(
            tool_id="uv",
            label="uv",
            category="core",
            command="uv",
            required_for_core=True,
            install_hint="Install uv from https://docs.astral.sh/uv/ before running Python setup.",
        ),
        _command_tool(
            tool_id="pnpm",
            label="pnpm",
            category="core",
            command="pnpm",
            required_for_core=True,
            install_hint="Install pnpm through Corepack or Homebrew, then run `pnpm run setup`.",
        ),
        _command_tool(
            tool_id="node",
            label="Node.js",
            category="core",
            command="node",
            required_for_core=True,
            install_hint="Install Node.js >=22 for the WebGUI, docs, and Ink TUI workspace.",
            version_args=["--version"],
        ),
        build_agentic_trader_entrypoint_status(),
        _with_ownership_note(_ollama_tool(), "ollama", ownership),
        ToolStatus(
            tool_id="research_flow_sidecar",
            label="CrewAI Flow sidecar",
            category="runtime_optional",
            available=bool(crewai.get("environment_exists")),
            path=str(crewai.get("flow_dir")),
            version=_single_line_optional(crewai.get("version")),
            status="installed" if crewai.get("environment_exists") else "needs_setup",
            notes=crewai_notes,
            install_hint="Run `pnpm run setup:research-flow`.",
        ),
        _with_ownership_note(_firecrawl_tool(), "firecrawl", ownership),
        _with_ownership_note(
            build_camofox_tool_status(settings), CAMOFOX_TOOL_ID, ownership
        ),
        _command_tool(
            tool_id="ruflo",
            label="RuFlo advisory CLI",
            category="developer_optional",
            command="ruflo",
            install_hint="Install globally when desired; do not run repo-local init unless explicitly requested.",
        ),
        _command_tool(
            tool_id="docker",
            label="Docker",
            category="developer_optional",
            command="docker",
            install_hint="Install Docker only for optional Sonar/Camofox container workflows.",
        ),
    ]


def _recommended_setup_commands() -> list[str]:
    return [
        "make bootstrap",
        "make setup",
        "agentic-trader setup-status --json",
        "agentic-trader model-service status --json",
        "agentic-trader model-service start",
        "agentic-trader model-service pull qwen3:8b",
        "agentic-trader camofox-service status --json",
        "agentic-trader camofox-service start",
        "agentic-trader webgui-service status --json",
        "agentic-trader webgui-service start",
    ]
