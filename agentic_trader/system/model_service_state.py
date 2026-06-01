from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text, write_private_text


class ModelServiceState(BaseModel):
    """Persisted state for an app-owned model-service process."""

    provider: str = "ollama"
    owner: str | None = None
    pid: int
    host: str
    port: int
    base_url: str
    started_at: str
    stdout_log_path: str
    stderr_log_path: str
    command: list[str]
    app_owned: bool = True


def model_service_dir(settings: Settings) -> Path:
    return settings.runtime_dir / "model_service"


def model_service_state_path(settings: Settings) -> Path:
    return model_service_dir(settings) / "ollama_service.json"


def read_model_service_state(settings: Settings) -> ModelServiceState | None:
    path = model_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return ModelServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_model_service_state(settings: Settings, state: ModelServiceState) -> None:
    write_private_text(
        model_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def remove_model_service_state(settings: Settings) -> None:
    path = model_service_state_path(settings)
    if path.exists():
        path.unlink()


def tail_model_service_text(path: str | None, *, limit: int = 12) -> list[str]:
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
