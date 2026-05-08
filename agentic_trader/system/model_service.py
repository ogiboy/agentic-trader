"""App-managed local model-service helpers.

The core runtime remains provider-agnostic. This module only manages the
operator-owned Ollama process when the user chooses app-managed local models.
It never stops an external Ollama process and never binds outside loopback.
"""

from __future__ import annotations

import os
import signal
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from agentic_trader.config import Settings
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.security import (
    ensure_private_directory,
    is_loopback_host,
    open_private_append_binary,
    redact_sensitive_text,
    write_private_text,
)
from agentic_trader.system.tool_roots import local_tool_status_payload

DEFAULT_APP_MANAGED_PORT = 11435
DEFAULT_MODEL_CHOICES = (
    "qwen3:8b",
    "llama3.2:3b",
    "deepseek-r1:8b",
    "gemma3:4b",
)
MINIMAL_ENV_KEYS = (
    "PATH",
    "HOME",
    "TMPDIR",
    "USER",
    "LOGNAME",
    "SHELL",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "SYSTEMROOT",
    "WINDIR",
)


class ModelServiceState(BaseModel):
    """Persisted state for an app-owned model-service process."""

    provider: str = "ollama"
    pid: int
    host: str
    port: int
    base_url: str
    started_at: str
    stdout_log_path: str
    stderr_log_path: str
    command: list[str]
    app_owned: bool = True


class ModelServiceStatus(BaseModel):
    """Operator-facing local model service status."""

    tool_id: str = "ollama"
    tool_status_id: str = "ollama_cli"
    tool_consumers: list[str] = Field(default_factory=list)
    tool_fallback_order: list[str] = Field(default_factory=list)
    install_hint: str = ""
    notes: list[str] = Field(default_factory=list)
    provider: str = "ollama"
    command_available: bool
    command_path: str | None = None
    configured_base_url: str
    configured_model: str
    service_reachable: bool
    model_available: bool
    available_models: list[str] = Field(default_factory=list)
    app_owned: bool = False
    pid: int | None = None
    host: str | None = None
    port: int | None = None
    base_url: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    stdout_tail: list[str] = Field(default_factory=list)
    stderr_tail: list[str] = Field(default_factory=list)
    state_path: str
    message: str
    suggested_models: list[str] = Field(default_factory=lambda: list(DEFAULT_MODEL_CHOICES))
    runtime_base_url_matches_app_service: bool = False


def model_service_dir(settings: Settings) -> Path:
    return settings.runtime_dir / "model_service"


def model_service_state_path(settings: Settings) -> Path:
    return model_service_dir(settings) / "ollama_service.json"


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _read_state(settings: Settings) -> ModelServiceState | None:
    path = model_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return ModelServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_state(settings: Settings, state: ModelServiceState) -> None:
    write_private_text(
        model_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def _remove_state(settings: Settings) -> None:
    path = model_service_state_path(settings)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _tail_text(path: str | None, *, limit: int = 12) -> list[str]:
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


def _api_root_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/")
        trimmed = base_url.removesuffix("/")
        if path == "/v1":
            return trimmed[: -len("/v1")]
        return trimmed
    return base_url.removesuffix("/v1").rstrip("/")


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def _minimal_process_env(*, ollama_host: str | None = None) -> dict[str, str]:
    """Return a subprocess env that does not inherit provider/broker secrets."""

    env = {key: os.environ[key] for key in MINIMAL_ENV_KEYS if key in os.environ}
    if ollama_host:
        env["OLLAMA_HOST"] = ollama_host
    return env


def _process_command_line(pid: int) -> str | None:
    if sys.platform.startswith("win"):
        return _windows_process_command_line(pid)
    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _windows_process_command_line(pid: int) -> str | None:
    query = (
        "Get-CimInstance Win32_Process "
        f"-Filter \"ProcessId = {pid}\" | Select-Object -ExpandProperty CommandLine"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _listen_port_owner_pid(host: str, port: int) -> int | None:
    query_host = "127.0.0.1" if host == "localhost" else host.strip("[]")
    try:
        completed = subprocess.run(
            ["lsof", "-nP", "-a", f"-iTCP@{query_host}:{port}", "-sTCP:LISTEN", "-Fp"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    pids = {
        int(line[1:])
        for line in completed.stdout.splitlines()
        if line.startswith("p") and line[1:].isdigit()
    }
    if len(pids) != 1:
        return None
    return next(iter(pids))


def _process_matches_state(state: ModelServiceState) -> bool:
    command_line = _process_command_line(state.pid)
    if not command_line:
        return False
    executable = Path(state.command[0]).name if state.command else "ollama"
    if executable not in command_line or "serve" not in command_line:
        return False
    return _listen_port_owner_pid(state.host, state.port) == state.pid


def _state_process_alive(state: ModelServiceState | None) -> bool:
    return bool(
        state is not None
        and is_process_alive(state.pid)
        and _process_matches_state(state)
    )


def _wait_for_state_process_exit(
    state: ModelServiceState,
    *,
    timeout_seconds: float,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _state_process_alive(state):
            return True
        time.sleep(0.2)
    return not _state_process_alive(state)


def choose_app_managed_port(host: str, preferred_port: int) -> int:
    """Choose a loopback port, avoiding already-running external services."""

    if not is_loopback_host(host):
        raise ValueError("model_service_host_must_be_loopback")
    for port in [preferred_port, DEFAULT_APP_MANAGED_PORT, *range(11436, 11466)]:
        if _is_port_available(host, port):
            return port
    raise RuntimeError("no_free_model_service_port_found")


def _fetch_ollama_tags(api_root: str, *, timeout_seconds: float = 2.0) -> tuple[bool, list[str], str]:
    try:
        response = httpx.get(f"{api_root}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return False, [], f"Unable to reach Ollama: {redact_sensitive_text(exc, max_length=160)}"
    models_obj: Any = payload.get("models", []) if isinstance(payload, dict) else []
    models: list[str] = []
    if isinstance(models_obj, list):
        for item in models_obj:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                models.append(item["name"])
    return True, sorted(models), "Ollama is reachable."


def build_model_service_status(settings: Settings, *, tail_limit: int = 12) -> ModelServiceStatus:
    """Build a read-only model-service status payload."""

    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    app_owned = app_state is not None
    command_path = shutil.which("ollama")
    api_root = app_state.base_url if app_state is not None else _api_root_from_base_url(settings.base_url)
    reachable, models, message = _fetch_ollama_tags(api_root)
    model_available = settings.model_name in models
    status_message = message
    if reachable and not model_available:
        status_message = "Ollama is reachable, but the configured model is not listed."
    if app_owned:
        status_message = "App-managed Ollama is running." if reachable else message
        if _api_root_from_base_url(settings.base_url) != app_state.base_url:
            status_message = (
                "App-managed Ollama is running on a different base URL than the "
                "runtime uses; set AGENTIC_TRADER_BASE_URL to the app-owned URL "
                "with /v1 when you want cycles to use it."
            )
    return ModelServiceStatus(
        **local_tool_status_payload("ollama"),
        command_available=command_path is not None,
        command_path=command_path,
        configured_base_url=settings.base_url,
        configured_model=settings.model_name,
        service_reachable=reachable,
        model_available=model_available,
        available_models=models,
        app_owned=app_owned,
        pid=app_state.pid if app_state is not None else None,
        host=app_state.host if app_state is not None else None,
        port=app_state.port if app_state is not None else None,
        base_url=app_state.base_url if app_state is not None else api_root,
        stdout_log_path=app_state.stdout_log_path if app_state is not None else None,
        stderr_log_path=app_state.stderr_log_path if app_state is not None else None,
        stdout_tail=_tail_text(
            app_state.stdout_log_path if app_state is not None else None,
            limit=tail_limit,
        ),
        stderr_tail=_tail_text(
            app_state.stderr_log_path if app_state is not None else None,
            limit=tail_limit,
        ),
        state_path=str(model_service_state_path(settings)),
        message=status_message,
        runtime_base_url_matches_app_service=bool(
            app_state is not None
            and _api_root_from_base_url(settings.base_url) == app_state.base_url
        ),
    )


def start_model_service(
    settings: Settings,
    *,
    host: str | None = None,
    port: int | None = None,
    models_dir: Path | None = None,
) -> ModelServiceStatus:
    """Start app-owned Ollama with owner-only logs and persisted process state."""

    command_path = shutil.which("ollama")
    if command_path is None:
        raise RuntimeError("Ollama CLI is not installed or not on PATH.")
    desired_host = host or settings.model_service_host
    if not is_loopback_host(desired_host):
        raise RuntimeError("App-managed Ollama must bind to a loopback host.")

    existing = _read_state(settings)
    if _state_process_alive(existing):
        return build_model_service_status(settings)

    preferred_port = port or settings.model_service_port
    chosen_port = choose_app_managed_port(desired_host, preferred_port)
    ensure_private_directory(model_service_dir(settings))
    stdout_path = model_service_dir(settings) / "ollama.out.log"
    stderr_path = model_service_dir(settings) / "ollama.err.log"
    api_root = _base_url(desired_host, chosen_port)
    env = _minimal_process_env(ollama_host=api_root)
    resolved_models_dir = models_dir or settings.model_service_models_dir
    if resolved_models_dir is not None:
        ensure_private_directory(resolved_models_dir)
        env["OLLAMA_MODELS"] = str(resolved_models_dir)
    with (
        open_private_append_binary(stdout_path) as stdout_handle,
        open_private_append_binary(stderr_path) as stderr_handle,
    ):
        process = subprocess.Popen(
            [command_path, "serve"],
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=env,
            start_new_session=True,
        )
    state = ModelServiceState(
        pid=process.pid,
        host=desired_host,
        port=chosen_port,
        base_url=api_root,
        started_at=_utc_now_iso(),
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=[command_path, "serve"],
    )
    _write_state(settings, state)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = build_model_service_status(settings)
        if status.service_reachable:
            return status
        time.sleep(0.25)
    return build_model_service_status(settings)


def stop_model_service(settings: Settings) -> ModelServiceStatus:
    """Stop only the app-owned Ollama process, never an external service."""

    state = _read_state(settings)
    if state is None:
        return build_model_service_status(settings)
    if not _state_process_alive(state):
        _remove_state(settings)
        return build_model_service_status(settings)

    stopped = False
    try:
        os.kill(state.pid, signal.SIGTERM)
        stopped = _wait_for_state_process_exit(state, timeout_seconds=5)
        if not stopped and _state_process_alive(state):
            os.kill(state.pid, signal.SIGKILL)
            stopped = _wait_for_state_process_exit(state, timeout_seconds=2)
    except OSError:
        stopped = not _state_process_alive(state)

    if stopped or not _state_process_alive(state):
        _remove_state(settings)
    return build_model_service_status(settings)


def pull_model(settings: Settings, model_name: str) -> dict[str, object]:
    """Pull an Ollama model through the CLI with redacted output."""

    command_path = shutil.which("ollama")
    if command_path is None:
        raise RuntimeError("Ollama CLI is not installed or not on PATH.")
    env = _minimal_process_env(ollama_host=_api_root_from_base_url(settings.base_url))
    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    if app_state is not None:
        env["OLLAMA_HOST"] = app_state.base_url
    completed = subprocess.run(
        [command_path, "pull", model_name],
        text=True,
        capture_output=True,
        timeout=1800,
        check=False,
        env=env,
    )
    return {
        "model": model_name,
        "exit_code": completed.returncode,
        "stdout": redact_sensitive_text(completed.stdout, max_length=2000),
        "stderr": redact_sensitive_text(completed.stderr, max_length=2000),
    }
