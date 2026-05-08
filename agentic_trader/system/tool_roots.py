"""Repo-owned optional local tool root helpers.

This module keeps product helper locations explicit. It does not install or
start tools; setup/runtime surfaces use it to resolve repo-local helpers before
falling back to configured host-system tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

LocalToolId = Literal["camofox-browser", "ollama", "firecrawl"]

TOOLS_DIR_NAME = "tools"
CAMOFOX_TOOL_DIR_NAME = "camofox-browser"
OLLAMA_TOOL_DIR_NAME = "ollama"
FIRECRAWL_TOOL_DIR_NAME = "firecrawl"
TOOL_MANIFEST_FILE = "agentic-tool.json"

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


def resolve_configured_tool_path(configured_path: str | Path, *, default_tool: LocalToolId) -> Path:
    """Resolve a configured tool path relative to the repo root when needed."""

    path = Path(configured_path)
    if path.is_absolute():
        return path
    if str(path) in {"", "."}:
        return repo_tool_path(default_tool)
    return repo_root() / path
