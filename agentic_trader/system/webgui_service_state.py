"""State models and persistence helpers for the local Web GUI service."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text, write_private_text


class WebGUIServiceState(BaseModel):
    """Persisted state for an app-owned Web GUI process."""

    pid: int
    launcher_pid: int | None = None
    host: str
    port: int
    url: str
    started_at: str
    stdout_log_path: str
    stderr_log_path: str
    command: list[str]
    app_owned: bool = True


class WebGUIServiceStatus(BaseModel):
    """Operator-facing Web GUI service status."""

    command_available: bool
    command_path: str | None = None
    package_available: bool
    dependency_available: bool = False
    dependency_path: str | None = None
    app_owned: bool = False
    pid: int | None = None
    host: str | None = None
    port: int | None = None
    url: str | None = None
    service_reachable: bool
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    stdout_tail: list[str] = Field(default_factory=list)
    stderr_tail: list[str] = Field(default_factory=list)
    state_path: str
    message: str


def webgui_service_dir(settings: Settings) -> Path:
    return settings.runtime_dir / "webgui_service"


def webgui_service_state_path(settings: Settings) -> Path:
    return webgui_service_dir(settings) / "webgui_service.json"


def read_webgui_service_state(settings: Settings) -> WebGUIServiceState | None:
    path = webgui_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return WebGUIServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_webgui_service_state(settings: Settings, state: WebGUIServiceState) -> None:
    write_private_text(
        webgui_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def remove_webgui_service_state(settings: Settings) -> None:
    try:
        webgui_service_state_path(settings).unlink()
    except FileNotFoundError:
        return


def tail_webgui_service_text(path: str | None, *, limit: int = 12) -> list[str]:
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
