"""Repo-owned optional local tool root helpers.

This module keeps product helper locations explicit. It does not install or
start tools; setup/runtime surfaces use it to resolve repo-local helpers before
falling back to configured host-system tools.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal, TypedDict

LocalToolId = Literal["camofox-browser", "ollama", "firecrawl"]
LocalToolConsumer = Literal[
    "setup",
    "researchd",
    "model-service",
    "camofox-service",
    "webgui-service",
    "operator-launcher",
    "qa",
    "docs",
]
LocalToolCategory = Literal["runtime_optional", "developer_optional"]

TOOLS_DIR_NAME = "tools"
CAMOFOX_TOOL_DIR_NAME = "camofox-browser"
OLLAMA_TOOL_DIR_NAME = "ollama"
FIRECRAWL_TOOL_DIR_NAME = "firecrawl"
TOOL_MANIFEST_FILE = "agentic-tool.json"
LOCAL_TOOL_OWNERSHIP_MODES = (
    "undecided",
    "host-owned",
    "app-owned",
    "api-key-only",
    "skipped",
)

TOOL_FALLBACK_ORDER: dict[LocalToolId, tuple[str, ...]] = {
    "camofox-browser": (
        "repo_tools",
        "configured_loopback_endpoint",
        "degraded_readiness",
    ),
    "ollama": (
        "app_managed_repo_config",
        "configured_host_ollama",
        "system_ollama_cli",
        "degraded_readiness",
    ),
    "firecrawl": (
        "repo_tools",
        "firecrawl_api_key",
        "system_firecrawl_cli",
        "pure_python_or_js_fetcher",
        "degraded_readiness",
    ),
}


@dataclass(frozen=True)
class LocalToolDefinition:
    """Repo-level contract for one optional helper tool."""

    tool_id: LocalToolId
    status_tool_id: str
    label: str
    category: LocalToolCategory
    consumers: tuple[LocalToolConsumer, ...]
    install_hint: str

    @property
    def fallback_order(self) -> tuple[str, ...]:
        """Return the safe resolution order for this tool."""

        return TOOL_FALLBACK_ORDER[self.tool_id]


class LocalToolStatusPayload(TypedDict):
    """Typed metadata shared by optional tool status surfaces."""

    tool_id: str
    tool_status_id: str
    tool_consumers: list[str]
    tool_fallback_order: list[str]
    tool_ownership_modes: list[str]
    install_hint: str
    notes: list[str]


LOCAL_TOOL_DEFINITIONS: dict[LocalToolId, LocalToolDefinition] = {
    "camofox-browser": LocalToolDefinition(
        tool_id="camofox-browser",
        status_tool_id="camofox_browser",
        label="Camofox Browser",
        category="runtime_optional",
        consumers=("setup", "researchd", "camofox-service", "operator-launcher", "qa", "docs"),
        install_hint=(
            "Keep the optional browser helper under tools/camofox-browser, run "
            "`pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts`, "
            "fetch the browser binary explicitly with `make fetch-camofox`, and start "
            "it with CAMOFOX_ACCESS_KEY before enabling it."
        ),
    ),
    "ollama": LocalToolDefinition(
        tool_id="ollama",
        status_tool_id="ollama_cli",
        label="Ollama CLI",
        category="runtime_optional",
        consumers=("setup", "model-service", "operator-launcher", "qa", "docs"),
        install_hint=(
            "Install Ollama, then use agentic-trader model-service start or connect "
            "to an existing local Ollama endpoint."
        ),
    ),
    "firecrawl": LocalToolDefinition(
        tool_id="firecrawl",
        status_tool_id="firecrawl_cli",
        label="Firecrawl CLI",
        category="runtime_optional",
        consumers=("setup", "researchd", "qa", "docs"),
        install_hint=(
            "Run npm install -g firecrawl-cli, then firecrawl login --browser or "
            "set FIRECRAWL_API_KEY in an ignored env file."
        ),
    ),
}


def repo_root() -> Path:
    """Return the repository root for the installed source tree."""

    return Path(__file__).resolve().parents[2]


def tools_root() -> Path:
    """Return the repo-owned optional local tool root."""

    return repo_root() / TOOLS_DIR_NAME


def repo_tool_path(tool_id: LocalToolId) -> Path:
    """Return the expected repo-local path for a known optional tool."""

    names: dict[LocalToolId, str] = {
        "camofox-browser": CAMOFOX_TOOL_DIR_NAME,
        "ollama": OLLAMA_TOOL_DIR_NAME,
        "firecrawl": FIRECRAWL_TOOL_DIR_NAME,
    }
    return tools_root() / names[tool_id]


def repo_tool_manifest_path(tool_id: LocalToolId) -> Path:
    """Return the optional Agentic Trader tool manifest path."""

    return repo_tool_path(tool_id) / TOOL_MANIFEST_FILE


def read_repo_tool_manifest(tool_id: LocalToolId) -> dict[str, Any] | None:
    """Read a repo-owned optional tool manifest when present and valid."""

    path = repo_tool_manifest_path(tool_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def iter_local_tool_definitions() -> tuple[LocalToolDefinition, ...]:
    """Return all known optional local tools in stable display order."""

    return tuple(LOCAL_TOOL_DEFINITIONS[tool_id] for tool_id in ("ollama", "firecrawl", "camofox-browser"))


def local_tool_definition(tool_id: LocalToolId) -> LocalToolDefinition:
    """Return the repo-level contract for one optional helper tool."""

    return LOCAL_TOOL_DEFINITIONS[tool_id]


def local_tool_manifest_notes(tool_id: LocalToolId) -> list[str]:
    """Return safe, non-secret manifest notes for status payloads."""

    definition = local_tool_definition(tool_id)
    notes = [
        f"local_tool_id={definition.tool_id}",
        f"consumers={','.join(definition.consumers)}",
        f"fallback_order={','.join(definition.fallback_order)}",
    ]
    manifest = read_repo_tool_manifest(tool_id)
    if not manifest:
        return notes
    notes.append(f"manifest={tool_id}/{manifest.get('schema_version', 'unknown')}")
    role = manifest.get("role")
    if isinstance(role, str) and role:
        notes.append(f"role={role}")
    entrypoints = manifest.get("entrypoints")
    if isinstance(entrypoints, dict):
        for key in sorted(entrypoints):
            value = entrypoints.get(key)
            if isinstance(value, str) and value:
                notes.append(f"{key}={value}")
    return notes


def local_tool_status_payload(tool_id: LocalToolId) -> LocalToolStatusPayload:
    """Return shared runtime/status metadata for one optional helper tool."""

    definition = local_tool_definition(tool_id)
    return {
        "tool_id": definition.tool_id,
        "tool_status_id": definition.status_tool_id,
        "tool_consumers": list(definition.consumers),
        "tool_fallback_order": list(definition.fallback_order),
        "tool_ownership_modes": list(LOCAL_TOOL_OWNERSHIP_MODES),
        "install_hint": definition.install_hint,
        "notes": local_tool_manifest_notes(tool_id),
    }


def resolve_configured_tool_path(configured_path: str | Path, *, default_tool: LocalToolId) -> Path:
    """Resolve a configured tool path relative to the repo root when needed."""

    path = Path(configured_path)
    if path.is_absolute():
        return path
    if str(path) in {"", "."}:
        return repo_tool_path(default_tool)
    return repo_root() / path
