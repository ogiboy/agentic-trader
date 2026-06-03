"""Persisted state and log helpers for the app-owned Camofox service."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text, write_private_text
from agentic_trader.system.tool_roots import resolve_configured_tool_path


class CamofoxServiceState(BaseModel):
    """Persisted state for an app-owned Camofox process."""

    owner: str | None = None
    pid: int
    host: str
    port: int
    base_url: str
    started_at: str
    stdout_log_path: str
    stderr_log_path: str
    command: list[str]
    tool_dir: str
    app_owned: bool = True


class CamofoxServiceStatus(BaseModel):
    """Operator-facing Camofox service status."""

    tool_id: str = "camofox-browser"
    tool_status_id: str = "camofox_browser"
    tool_consumers: list[str] = Field(default_factory=list)
    tool_fallback_order: list[str] = Field(default_factory=list)
    tool_ownership_modes: list[str] = Field(default_factory=list)
    install_hint: str = ""
    notes: list[str] = Field(default_factory=list)
    command_available: bool
    command_path: str | None = None
    package_available: bool
    dependency_available: bool = False
    dependency_path: str | None = None
    access_key_configured: bool
    app_owned: bool = False
    owner: str | None = None
    pid: int | None = None
    host: str | None = None
    port: int | None = None
    base_url: str
    service_reachable: bool
    health_ok: bool
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    stdout_tail: list[str] = Field(default_factory=list)
    stderr_tail: list[str] = Field(default_factory=list)
    state_path: str
    tool_dir: str
    message: str

    def is_owned_by_host(self, host_id: str) -> bool:
        """Return whether this app-owned status belongs to the requested host."""

        return self.app_owned and self.owner == host_id


def camofox_service_dir(settings: Settings) -> Path:
    """Return the owner-only runtime directory for Camofox service artifacts."""

    return settings.runtime_dir / "camofox_service"


def camofox_service_state_path(settings: Settings) -> Path:
    return camofox_service_dir(settings) / "camofox_service.json"


def camofox_tool_dir(settings: Settings) -> Path:
    """Resolve the configured Camofox tool directory."""

    return resolve_configured_tool_path(
        settings.research_camofox_tool_dir,
        default_tool="camofox-browser",
    )


def read_state(settings: Settings) -> CamofoxServiceState | None:
    """Read persisted Camofox state when it exists and validates."""

    path = camofox_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return CamofoxServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_state(settings: Settings, state: CamofoxServiceState) -> None:
    write_private_text(
        camofox_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def remove_state(settings: Settings) -> None:
    try:
        camofox_service_state_path(settings).unlink()
    except FileNotFoundError:
        return


def tail_text(path: str | None, *, limit: int = 12) -> list[str]:
    if not path:
        return []
    log_path = Path(path)
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [redact_sensitive_text(line, max_length=300) for line in lines[-limit:]]


def tail_contains_browser_launch_failure(state: CamofoxServiceState | None) -> bool:
    if state is None:
        return False
    recent_lines = [
        *tail_text(state.stdout_log_path, limit=20),
        *tail_text(state.stderr_log_path, limit=20),
    ]
    failure_markers = (
        "browser pre-warm failed",
        "camoufox launch attempt failed",
        "failed to launch the browser process",
    )
    return any(
        any(marker in line.lower() for marker in failure_markers)
        for line in recent_lines
    )
