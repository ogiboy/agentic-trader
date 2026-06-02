"""App-managed local model-service helpers.

The core runtime remains provider-agnostic. This module only manages the
operator-owned Ollama process when the user chooses app-managed local models.
It never stops an external Ollama process and never binds outside loopback.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.security import (
    ensure_private_directory,
    is_loopback_host,
    open_private_append_binary,
    redact_sensitive_text,
)
from agentic_trader.system import model_service_process as _process_helpers
from agentic_trader.system.model_service_probe import base_url as _base_url
from agentic_trader.system.model_service_probe import (
    fetch_ollama_tags,
    model_service_api_root_from_base_url,
    ollama_error_from_response,
    probe_ollama_generation,
    same_loopback_api_root,
)
from agentic_trader.system.model_service_report import (
    ModelServiceStatusProbe,
    generation_probe_status as _report_generation_probe_status,
    model_service_status_from_probe as _report_model_service_status_from_probe,
    model_service_status_message_for_probe as _report_status_message_for_probe,
)
from agentic_trader.system.model_service_state import (
    ModelServiceState,
    model_service_dir,
    model_service_state_path,
    read_model_service_state,
    remove_model_service_state,
    tail_model_service_text,
    write_model_service_state,
)
from agentic_trader.system.model_service_status import (
    ModelServiceStatus,
    app_owned_model_status_message,
    base_url_mismatch_message,
    host_model_status_message,
    model_service_status_message,
    model_status_notes,
)
from agentic_trader.time_utils import utc_now_iso as _utc_now_iso

_api_root_from_base_url = model_service_api_root_from_base_url
_fetch_ollama_tags = fetch_ollama_tags
_read_state = read_model_service_state
_remove_state = remove_model_service_state
_same_loopback_api_root = same_loopback_api_root
sys = _process_helpers.sys
_tail_text = tail_model_service_text
_write_state = write_model_service_state

__all__ = [
    "ModelServiceState",
    "ModelServiceStatus",
    "app_owned_model_status_message",
    "base_url_mismatch_message",
    "fetch_ollama_tags",
    "generation_probe_status",
    "host_model_status_message",
    "model_service_api_root_from_base_url",
    "model_service_state_path",
    "model_service_status_message",
    "model_status_notes",
    "ollama_error_from_response",
    "probe_ollama_generation",
    "same_loopback_api_root",
]

DEFAULT_APP_MANAGED_PORT = _process_helpers.DEFAULT_APP_MANAGED_PORT
APP_MANAGED_ORPHAN_PORTS = _process_helpers.APP_MANAGED_ORPHAN_PORTS
KNOWN_OLLAMA_SERVICE_PORTS = _process_helpers.KNOWN_OLLAMA_SERVICE_PORTS
LSOF_LISTEN_FILTER = _process_helpers.LSOF_LISTEN_FILTER
MINIMAL_ENV_KEYS = _process_helpers.MINIMAL_ENV_KEYS


def _is_port_available(host: str, port: int) -> bool:
    return _process_helpers.is_port_available(host, port)


def model_service_port_available(host: str, port: int) -> bool:
    return _is_port_available(host, port)


def _minimal_process_env(*, ollama_host: str | None = None) -> dict[str, str]:
    return _process_helpers.minimal_process_env(ollama_host=ollama_host)


def minimal_model_service_process_env(
    *, ollama_host: str | None = None
) -> dict[str, str]:
    return _minimal_process_env(ollama_host=ollama_host)


def _process_command_line(pid: int) -> str | None:
    return _process_helpers.process_command_line(pid)


def model_service_process_command_line(pid: int) -> str | None:
    return _process_command_line(pid)


def _external_ollama_serve_pids(command_path: str | None) -> list[int]:
    return _process_helpers.external_ollama_serve_pids(command_path)


def external_ollama_serve_pids(command_path: str | None) -> list[int]:
    return _external_ollama_serve_pids(command_path)


def _ollama_listener_pids_from_lsof() -> list[int]:
    return _process_helpers.ollama_listener_pids_from_lsof()


def ollama_listener_pids_from_lsof() -> list[int]:
    return _ollama_listener_pids_from_lsof()


def _listening_loopback_ports_for_pid(pid: int) -> set[int]:
    return _process_helpers.listening_loopback_ports_for_pid(pid)


def listening_loopback_ports_for_pid(pid: int) -> set[int]:
    return _listening_loopback_ports_for_pid(pid)


def _orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    """Return stale app-managed Ollama PIDs without touching host/default 11434."""

    active_pid = active_state.pid if active_state is not None else None
    orphan_pids: list[int] = []
    managed_ports = set(APP_MANAGED_ORPHAN_PORTS)
    for pid in _external_ollama_serve_pids(command_path):
        if pid == active_pid:
            continue
        if _listening_loopback_ports_for_pid(pid) & managed_ports:
            orphan_pids.append(pid)
    return sorted(set(orphan_pids))


def orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    return _orphan_app_managed_ollama_pids(command_path, active_state)


def _cleanup_orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    """Best-effort cleanup for stale app-managed Ollama listeners."""

    stopped_pids: list[int] = []
    for pid in _orphan_app_managed_ollama_pids(command_path, active_state):
        if _stop_pid(pid):
            stopped_pids.append(pid)
    return stopped_pids


def cleanup_orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    return _cleanup_orphan_app_managed_ollama_pids(command_path, active_state)


def _wait_for_pid_exit(pid: int, *, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_process_alive(pid):
            return True
        time.sleep(0.2)
    return not is_process_alive(pid)


def wait_for_model_service_pid_exit(pid: int, *, timeout_seconds: float) -> bool:
    return _wait_for_pid_exit(pid, timeout_seconds=timeout_seconds)


def _stop_pid(pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
        stopped = _wait_for_pid_exit(pid, timeout_seconds=5)
        if not stopped and is_process_alive(pid):
            os.kill(pid, signal.SIGKILL)
            stopped = _wait_for_pid_exit(pid, timeout_seconds=2)
    except OSError:
        stopped = not is_process_alive(pid)
    return stopped or not is_process_alive(pid)


def _listen_port_owner_pid(host: str, port: int) -> int | None:
    return _process_helpers.listen_port_owner_pid(host, port)


def model_service_listen_port_owner_pid(host: str, port: int) -> int | None:
    return _listen_port_owner_pid(host, port)


def _process_matches_state(state: ModelServiceState) -> bool:
    port_owner_pid = _listen_port_owner_pid(state.host, state.port)
    if port_owner_pid == state.pid:
        return True
    if port_owner_pid is not None:
        return False
    command_line = _process_command_line(state.pid)
    if not command_line:
        return False
    executable = Path(state.command[0]).name if state.command else "ollama"
    if executable not in command_line or "serve" not in command_line:
        return False
    return True


def model_service_process_matches_state(state: ModelServiceState) -> bool:
    return _process_matches_state(state)


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


def wait_for_model_service_state_process_exit(
    state: ModelServiceState,
    *,
    timeout_seconds: float,
) -> bool:
    return _wait_for_state_process_exit(state, timeout_seconds=timeout_seconds)


def choose_app_managed_port(host: str, preferred_port: int) -> int:
    """Choose a loopback port, avoiding already-running external services."""

    if not is_loopback_host(host):
        raise ValueError("model_service_host_must_be_loopback")
    for port in [preferred_port, DEFAULT_APP_MANAGED_PORT, *range(11436, 11466)]:
        if _is_port_available(host, port):
            return port
    raise RuntimeError("no_free_model_service_port_found")


def _generation_probe_status(
    *,
    include_generation: bool,
    reachable: bool,
    model_available: bool,
    api_root: str,
    model_name: str,
) -> tuple[bool | None, str | None]:
    return _report_generation_probe_status(
        include_generation=include_generation,
        reachable=reachable,
        model_available=model_available,
        api_root=api_root,
        model_name=model_name,
    )


def generation_probe_status(
    *,
    include_generation: bool,
    reachable: bool,
    model_available: bool,
    api_root: str,
    model_name: str,
) -> tuple[bool | None, str | None]:
    return _generation_probe_status(
        include_generation=include_generation,
        reachable=reachable,
        model_available=model_available,
        api_root=api_root,
        model_name=model_name,
    )


def _model_service_status_message_for_probe(
    *,
    app_owned: bool,
    reachable: bool,
    model_available: bool,
    include_generation: bool,
    generation_available: bool | None,
    generation_message: str | None,
    fetch_message: str,
    runtime_base_url_matches_app_service: bool,
    ollama_serve_pids: list[int],
    orphan_app_managed_pids: list[int],
) -> str:
    return _report_status_message_for_probe(
        app_owned=app_owned,
        reachable=reachable,
        model_available=model_available,
        include_generation=include_generation,
        generation_available=generation_available,
        generation_message=generation_message,
        fetch_message=fetch_message,
        runtime_base_url_matches_app_service=runtime_base_url_matches_app_service,
        ollama_serve_pids=ollama_serve_pids,
        orphan_app_managed_pids=orphan_app_managed_pids,
    )


def _model_service_status_probe(
    settings: Settings,
    *,
    include_generation: bool,
) -> ModelServiceStatusProbe:
    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    app_owned = app_state is not None
    command_path = shutil.which("ollama")
    ollama_serve_pids = _external_ollama_serve_pids(command_path)
    orphan_app_managed_pids = _orphan_app_managed_ollama_pids(
        command_path,
        app_state,
    )
    api_root = (
        app_state.base_url
        if app_state is not None
        else _api_root_from_base_url(settings.base_url)
    )
    reachable, models, fetch_message = _fetch_ollama_tags(api_root)
    model_available = settings.model_name in models
    generation_available, generation_message = _generation_probe_status(
        include_generation=include_generation,
        reachable=reachable,
        model_available=model_available,
        api_root=api_root,
        model_name=settings.model_name,
    )
    runtime_base_url_matches_app_service = bool(
        app_state is not None
        and _same_loopback_api_root(
            _api_root_from_base_url(settings.base_url),
            app_state.base_url,
        )
    )
    status_message = _model_service_status_message_for_probe(
        app_owned=app_owned,
        reachable=reachable,
        model_available=model_available,
        include_generation=include_generation,
        generation_available=generation_available,
        generation_message=generation_message,
        fetch_message=fetch_message,
        runtime_base_url_matches_app_service=runtime_base_url_matches_app_service,
        ollama_serve_pids=ollama_serve_pids,
        orphan_app_managed_pids=orphan_app_managed_pids,
    )
    return ModelServiceStatusProbe(
        app_state=app_state,
        app_owned=app_owned,
        command_path=command_path,
        ollama_serve_pids=ollama_serve_pids,
        orphan_app_managed_pids=orphan_app_managed_pids,
        api_root=api_root,
        reachable=reachable,
        models=models,
        fetch_message=fetch_message,
        model_available=model_available,
        generation_available=generation_available,
        generation_message=generation_message,
        runtime_base_url_matches_app_service=runtime_base_url_matches_app_service,
        status_message=status_message,
    )


def _model_service_status_from_probe(
    settings: Settings,
    *,
    probe: ModelServiceStatusProbe,
    tail_limit: int,
    include_generation: bool,
) -> ModelServiceStatus:
    return _report_model_service_status_from_probe(
        settings,
        probe=probe,
        tail_limit=tail_limit,
        include_generation=include_generation,
    )


def build_model_service_status(
    settings: Settings,
    *,
    tail_limit: int = 12,
    include_generation: bool = False,
) -> ModelServiceStatus:
    """Assemble the operator-facing Ollama model-service status."""
    probe = _model_service_status_probe(
        settings,
        include_generation=include_generation,
    )
    return _model_service_status_from_probe(
        settings,
        probe=probe,
        tail_limit=tail_limit,
        include_generation=include_generation,
    )


def start_model_service(
    settings: Settings,
    *,
    host: str | None = None,
    port: int | None = None,
    models_dir: Path | None = None,
) -> ModelServiceStatus:
    """Start and persist an app-managed Ollama serve process on loopback."""
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
        owner=settings.host_id,
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
        if _state_process_alive(state):
            reachable, _models, _message = _fetch_ollama_tags(api_root)
            if reachable:
                return build_model_service_status(settings)
        time.sleep(0.25)
    return build_model_service_status(settings)


def stop_model_service(settings: Settings) -> ModelServiceStatus:
    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    if state is None:
        return build_model_service_status(settings)
    if app_state is None:
        _remove_state(settings)
        return build_model_service_status(settings)

    stopped = _stop_pid(app_state.pid)
    if stopped or not _state_process_alive(app_state):
        _remove_state(settings)
    return build_model_service_status(settings)


def pull_model(settings: Settings, model_name: str) -> dict[str, object]:
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
