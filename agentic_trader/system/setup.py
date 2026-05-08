"""Read-only setup and optional tool readiness contracts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.researchd.crewai_setup import crewai_setup_status
from agentic_trader.security import is_loopback_host, redact_sensitive_text
from agentic_trader.system.camofox_service import build_camofox_service_status
from agentic_trader.system.model_service import build_model_service_status
from agentic_trader.system.tool_roots import (
    LocalToolId,
    local_tool_definition,
    local_tool_manifest_notes,
    repo_root,
    resolve_configured_tool_path,
)
from agentic_trader.system.webgui_service import build_webgui_service_status

ToolCategory = Literal["core", "runtime_optional", "developer_optional"]


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


class SetupStatus(BaseModel):
    """Operator-facing workspace and side-application readiness."""

    platform: str
    workspace_root: str
    core_ready: bool
    optional_ready: bool
    tools: list[ToolStatus]
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
    return redact_sensitive_text(output.splitlines()[0] if output else "", max_length=160)


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
    return tool.model_copy(update={"notes": [*tool.notes, *local_tool_manifest_notes(tool_id)]})


def _ollama_tool() -> ToolStatus:
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
    definition = local_tool_definition("camofox-browser")
    root = resolve_configured_tool_path(
        settings.research_camofox_tool_dir,
        default_tool="camofox-browser",
    )
    package_json = root / "package.json"
    server_js = root / "server.js"
    available = package_json.exists() and server_js.exists()
    notes: list[str] = []
    status = "available" if available else "missing"
    version: str | None = None
    if package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            version = str(payload.get("version") or "")
        except Exception:
            notes.append("package_json_unreadable")
    if available:
        notes.extend(_with_manifest_note(
            ToolStatus(
                tool_id=definition.status_tool_id,
                label=definition.label,
                category="runtime_optional",
                available=True,
            ),
            "camofox-browser",
        ).notes)
        access_key_configured = bool(
            settings.camofox_access_key or os.environ.get("CAMOFOX_ACCESS_KEY", "").strip()
            or settings.camofox_api_key
            or os.environ.get("CAMOFOX_API_KEY", "").strip()
        )
        parsed = urlparse(settings.research_camofox_base_url)
        host = parsed.hostname or ""
        if not is_loopback_host(host):
            notes.append("health_probe_skipped_non_loopback_base_url")
            return ToolStatus(
                tool_id=definition.status_tool_id,
                label=definition.label,
                category="runtime_optional",
                available=available,
                path=str(root),
                version=version or None,
                status="unsafe_base_url",
                notes=notes,
                install_hint=definition.install_hint,
            )
        try:
            response = httpx.get(
                f"{settings.research_camofox_base_url.rstrip('/')}/health",
                timeout=2,
            )
            if 200 <= response.status_code < 300:
                status = "healthy" if access_key_configured else "healthy_unkeyed"
                notes.append("health_endpoint_reachable")
                if not access_key_configured:
                    notes.append("access_key_not_configured_start_with_wrapper")
            else:
                status = "unhealthy"
                notes.append(f"health_status={response.status_code}")
        except Exception:
            notes.append("health_endpoint_unreachable")
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
        return tool.model_copy(update={"version": None, "status": status, "notes": notes})
    return tool


def build_setup_status(settings: Settings) -> SetupStatus:
    """Build the setup status without installing or mutating anything."""

    root = _repo_root()
    crewai = crewai_setup_status(settings)
    crewai_notes = crewai.get("notes")
    tools = [
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
        _agentic_trader_entrypoint(),
        _ollama_tool(),
        ToolStatus(
            tool_id="research_flow_sidecar",
            label="CrewAI Flow sidecar",
            category="runtime_optional",
            available=bool(crewai.get("environment_exists")),
            path=str(crewai.get("flow_dir")),
            version=str(crewai.get("version") or "") or None,
            status="installed" if crewai.get("environment_exists") else "needs_setup",
            notes=(
                [str(note) for note in crewai_notes]
                if isinstance(crewai_notes, list)
                else []
            ),
            install_hint="Run `pnpm run setup:research-flow`.",
        ),
        _firecrawl_tool(),
        _camofox_tool(settings),
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
    core_ready = all(tool.available for tool in tools if tool.required_for_core)
    optional_ready = all(
        tool.available
        for tool in tools
        if tool.category == "runtime_optional"
        and tool.tool_id in {local_tool_definition("ollama").status_tool_id}
    )
    return SetupStatus(
        platform=platform.system(),
        workspace_root=str(root),
        core_ready=core_ready,
        optional_ready=optional_ready,
        tools=tools,
        model_service=build_model_service_status(settings).model_dump(mode="json"),
        camofox_service=build_camofox_service_status(settings).model_dump(mode="json"),
        recommended_commands=[
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
        ],
        webgui_service=build_webgui_service_status(settings).model_dump(mode="json"),
    )
