"""App-owned local Camofox Browser helper process.

Camofox is optional browser infrastructure for research evidence collection.
This module starts and stops only an app-owned loopback process, records
owner-only state/logs, and avoids inheriting trading/broker/provider secrets.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import httpx

from agentic_trader.config import Settings
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.security import (
    ensure_private_directory,
    is_loopback_host,
    open_private_append_binary,
    redact_sensitive_text,
)
from agentic_trader.system import camofox_service_process as _process_helpers
from agentic_trader.system import camofox_service_state as _state_helpers
from agentic_trader.system.camofox_service_state import (
    CamofoxServiceState,
    CamofoxServiceStatus,
)
from agentic_trader.system.tool_roots import local_tool_status_payload
from agentic_trader.time_utils import utc_now_iso as _utc_now_iso

DEFAULT_CAMOFOX_HOST = "127.0.0.1"
DEFAULT_CAMOFOX_PORT = 9377
CAMOFOX_PORT_CANDIDATES = (9377, *range(9378, 9398))
LOCAL_HTTP_SCHEME = "http"
LSOF_LISTEN_FILTER = _process_helpers.LSOF_LISTEN_FILTER
SERVER_SCRIPT_NAME = _process_helpers.SERVER_SCRIPT_NAME
MINIMAL_CAMOFOX_ENV_KEYS = _process_helpers.MINIMAL_CAMOFOX_ENV_KEYS
CAMOFOX_SECRET_KEYS = _process_helpers.CAMOFOX_SECRET_KEYS
CAMOFOX_DATA_KEYS = _process_helpers.CAMOFOX_DATA_KEYS
CAMOFOX_PROXY_KEYS = _process_helpers.CAMOFOX_PROXY_KEYS


def camofox_service_dir(settings: Settings) -> Path:
    return _state_helpers.camofox_service_dir(settings)


def camofox_service_state_path(settings: Settings) -> Path:
    return _state_helpers.camofox_service_state_path(settings)


def camofox_tool_dir(settings: Settings) -> Path:
    return _state_helpers.camofox_tool_dir(settings)


def _read_state(settings: Settings) -> CamofoxServiceState | None:
    return _state_helpers.read_state(settings)


def _write_state(settings: Settings, state: CamofoxServiceState) -> None:
    _state_helpers.write_state(settings, state)


def _remove_state(settings: Settings) -> None:
    _state_helpers.remove_state(settings)


def _tail_text(path: str | None, *, limit: int = 12) -> list[str]:
    return _state_helpers.tail_text(path, limit=limit)


def _tail_contains_browser_launch_failure(state: CamofoxServiceState | None) -> bool:
    return _state_helpers.tail_contains_browser_launch_failure(state)


def _node_command_path() -> str | None:
    return _process_helpers.node_command_path()


def _package_available(tool_dir: Path) -> bool:
    return _process_helpers.package_available(tool_dir)


def _dependency_available(tool_dir: Path) -> bool:
    return _process_helpers.dependency_available(tool_dir)


def _base_url(host: str, port: int) -> str:
    return f"{LOCAL_HTTP_SCHEME}://{host}:{port}"


def _configured_host_port(settings: Settings) -> tuple[str, int]:
    parsed = urlparse(settings.research_camofox_base_url)
    return (
        parsed.hostname or DEFAULT_CAMOFOX_HOST,
        parsed.port or DEFAULT_CAMOFOX_PORT,
    )


def _configured_base_url(settings: Settings) -> str:
    host, port = _configured_host_port(settings)
    return _base_url(host, port)


def _is_port_available(host: str, port: int) -> bool:
    return _process_helpers.is_port_available(host, port)


def choose_camofox_port(host: str, preferred_port: int = DEFAULT_CAMOFOX_PORT) -> int:
    """Choose a loopback Camofox port without taking over other processes."""

    if not is_loopback_host(host):
        raise ValueError("camofox_host_must_be_loopback")
    candidates = [preferred_port, *CAMOFOX_PORT_CANDIDATES]
    seen: set[int] = set()
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        if _is_port_available(host, port):
            return port
    raise RuntimeError("no_free_camofox_port_found")


def _camofox_secret(settings: Settings, key: str) -> str | None:
    return _process_helpers.camofox_secret(settings, key)


def _camofox_access_token(settings: Settings) -> str | None:
    return _camofox_secret(settings, "CAMOFOX_ACCESS_KEY") or _camofox_secret(
        settings,
        "CAMOFOX_API_KEY",
    )


def _camofox_env(settings: Settings, *, host: str, port: int) -> dict[str, str]:
    return _process_helpers.camofox_env(settings, host=host, port=port)


def _runtime_command(tool_dir: Path) -> list[str]:
    """
    Builds the command to launch the Camofox Node.js helper.

    Parameters:
        tool_dir (Path): Filesystem path to the Camofox tool directory.

    Returns:
        command (list[str]): The node executable path followed by the server script name.

    Raises:
        RuntimeError: If the `node` executable is not found on PATH.
        RuntimeError: If the Camofox tool package is missing at `tool_dir`.
        RuntimeError: If Camofox dependencies are missing.
    """
    node_path = _node_command_path()
    if node_path is None:
        raise RuntimeError("node is not installed or not on PATH.")
    if not _package_available(tool_dir):
        raise RuntimeError(f"Camofox browser helper is missing at {tool_dir}.")
    if not _dependency_available(tool_dir):
        raise RuntimeError(
            "Camofox dependencies are missing. Run `pnpm run setup:camofox`."
        )
    return [node_path, SERVER_SCRIPT_NAME]


def _health(base_url: str) -> tuple[bool, bool, str]:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return (
            False,
            False,
            f"Unable to reach Camofox: {redact_sensitive_text(exc, max_length=160)}",
        )
    payload_object = (
        cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    )
    ok = bool(payload_object.get("ok"))
    if not ok:
        return True, False, "Camofox health is not ok."
    browser_running = payload_object.get("browserRunning")
    browser_connected = payload_object.get("browserConnected")
    if browser_running is False or browser_connected is False:
        return True, True, "Camofox server is reachable; browser launches on demand."
    return True, True, "Camofox is reachable."


def _process_command_line(pid: int) -> str | None:
    return _process_helpers.process_command_line(pid, run=subprocess.run)


def _listen_port_owner_pid(host: str, port: int) -> int | None:
    return _process_helpers.listen_port_owner_pid(host, port, run=subprocess.run)


def _process_cwd(pid: int) -> Path | None:
    return _process_helpers.process_cwd(pid, run=subprocess.run)


def _process_matches_state(state: CamofoxServiceState) -> bool:
    command_line = _process_command_line(state.pid)
    if command_line:
        normalized = command_line.replace("\\", "/").lower()
        if "node" in normalized and SERVER_SCRIPT_NAME in normalized:
            cwd = _process_cwd(state.pid)
            if cwd is not None and cwd == Path(state.tool_dir).resolve():
                return True
    return _listen_port_owner_pid(state.host, state.port) == state.pid


def _state_process_alive(state: CamofoxServiceState | None) -> bool:
    return bool(
        state is not None
        and is_process_alive(state.pid)
        and _process_matches_state(state)
    )


def _wait_for_state_exit(state: CamofoxServiceState, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _state_process_alive(state):
        time.sleep(0.2)
    return not _state_process_alive(state)


def _camofox_blocking_status_message(
    *,
    probe_host: str,
    package_available: bool,
    command_path: str | None,
    dependency_available: bool,
    tool_dir: Path,
) -> str | None:
    """
    Determine whether startup should be blocked and provide a human-readable message for the first missing prerequisite.

    Parameters:
        probe_host (str): Host portion of the configured base URL to validate as loopback.
        package_available (bool): Whether the tool's package files (package.json, server.js) are present.
        command_path (str | None): Path to the Node.js executable, or None if not found.
        dependency_available (bool): Whether the tool's node_modules dependencies are installed.
        tool_dir (Path): The resolved Camofox tool directory path.

    Returns:
        blocking_message (str | None): A short message describing the first blocking issue, or `None` if no blocking issues are detected.
    """
    if not is_loopback_host(probe_host):
        return "Camofox base URL must remain loopback."
    if not package_available:
        return "Camofox browser helper is missing."
    if command_path is None:
        return "node is not installed or not on PATH."
    if not dependency_available:
        return "Camofox dependencies are missing. Run `pnpm run setup:camofox`."
    return None


def _camofox_probe_status(
    *,
    base_url: str,
    state: CamofoxServiceState | None,
    app_state: CamofoxServiceState | None,
) -> tuple[bool, bool, str]:
    reachable, health_ok, message = _health(base_url)
    if (
        reachable
        and app_state is not None
        and _tail_contains_browser_launch_failure(app_state)
    ):
        return (
            True,
            False,
            "Camofox server is reachable, but browser launch is failing.",
        )
    if app_state is not None and reachable and health_ok:
        return reachable, health_ok, "App-owned Camofox is running."
    if state is not None and app_state is None:
        return (
            reachable,
            health_ok,
            "Recorded Camofox state is stale or process ownership could not be verified.",
        )
    return reachable, health_ok, message


def build_camofox_service_status(
    settings: Settings, *, tail_limit: int = 12
) -> CamofoxServiceStatus:
    """
    Builds the current read-only status for the app-owned Camofox helper.

    Parameters:
        tail_limit (int): Maximum number of lines to include from each log tail.

    Returns:
        CamofoxServiceStatus: Aggregated operator-facing status including tool availability,
        ownership/process info (only when the app-owned process is verified alive),
        connectivity/health flags, log paths and tails, and a human-readable message.
    """

    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    tool_dir = camofox_tool_dir(settings)
    command_path = _node_command_path()
    package_available = _package_available(tool_dir)
    dependency_available = _dependency_available(tool_dir)
    base_url = (
        app_state.base_url if app_state is not None else _configured_base_url(settings)
    )
    host, port = _configured_host_port(settings)
    probe_host = app_state.host if app_state is not None else host
    reachable = False
    health_ok = False
    message = _camofox_blocking_status_message(
        probe_host=probe_host,
        package_available=package_available,
        command_path=command_path,
        dependency_available=dependency_available,
        tool_dir=tool_dir,
    )
    if message is None:
        reachable, health_ok, message = _camofox_probe_status(
            base_url=base_url,
            state=state,
            app_state=app_state,
        )
    return CamofoxServiceStatus(
        **local_tool_status_payload("camofox-browser"),
        command_available=command_path is not None,
        command_path=command_path,
        package_available=package_available,
        dependency_available=dependency_available,
        dependency_path=(
            str(tool_dir / "node_modules") if dependency_available else None
        ),
        access_key_configured=bool(_camofox_access_token(settings)),
        app_owned=app_state is not None,
        owner=app_state.owner if app_state is not None else None,
        pid=app_state.pid if app_state is not None else None,
        host=app_state.host if app_state is not None else host,
        port=app_state.port if app_state is not None else port,
        base_url=base_url,
        service_reachable=reachable,
        health_ok=health_ok,
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
        state_path=str(camofox_service_state_path(settings)),
        tool_dir=str(tool_dir),
        message=message,
    )


def _startup_poll_should_stop(status: CamofoxServiceStatus) -> bool:
    return (
        status.app_owned
        and status.service_reachable
        and "browser launch is failing" in status.message
    )


def _await_camofox_start(
    settings: Settings, *, timeout_seconds: float
) -> CamofoxServiceStatus | None:
    deadline = time.monotonic() + timeout_seconds
    last_status: CamofoxServiceStatus | None = None
    while time.monotonic() < deadline:
        status = build_camofox_service_status(settings)
        last_status = status
        if status.app_owned and status.health_ok:
            return status
        if _startup_poll_should_stop(status):
            return stop_camofox_service(settings)
        time.sleep(0.4)
    if last_status is not None and last_status.app_owned and not last_status.health_ok:
        return stop_camofox_service(settings)
    return None


def start_camofox_service(
    settings: Settings,
    *,
    host: str | None = None,
    port: int | None = None,
) -> CamofoxServiceStatus:
    """
    Start and persist an app-owned loopback Camofox helper process.

    Validates that the chosen host is loopback and that an access token is configured, spawns the tool subprocess in the resolved tool directory with a minimal, secret-filtered environment, persists owner-only runtime state (including PID, host, port, log paths, and command), and waits briefly for the service to become healthy. If an existing recorded app-owned process is already alive, the call returns the current service status instead of starting a new process.

    Parameters:
        settings (Settings): Application settings and runtime configuration.
        host (str | None): Optional override for the loopback host to bind; when omitted the configured host is used.
        port (int | None): Optional preferred port to bind; when omitted the configured port is used.

    Returns:
        CamofoxServiceStatus: Operator-facing status describing the service after the start attempt.

    Raises:
        RuntimeError: If the resolved host is not a loopback address or if no CAMOFOX access token is available.
    """

    desired_host, configured_port = _configured_host_port(settings)
    desired_host = host or desired_host
    preferred_port = port or configured_port
    if not is_loopback_host(desired_host):
        raise RuntimeError("App-managed Camofox must bind to a loopback host.")
    if not _camofox_access_token(settings):
        raise RuntimeError(
            "CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY is required before starting Camofox.",
        )
    tool_dir = camofox_tool_dir(settings)
    command = _runtime_command(tool_dir)
    existing = _read_state(settings)
    if _state_process_alive(existing):
        return build_camofox_service_status(settings)
    if existing is not None:
        _remove_state(settings)

    chosen_port = choose_camofox_port(desired_host, preferred_port)
    base_url = _base_url(desired_host, chosen_port)
    ensure_private_directory(camofox_service_dir(settings))
    stdout_path = camofox_service_dir(settings) / "camofox.out.log"
    stderr_path = camofox_service_dir(settings) / "camofox.err.log"
    with (
        open_private_append_binary(stdout_path) as stdout_handle,
        open_private_append_binary(stderr_path) as stderr_handle,
    ):
        process = subprocess.Popen(
            command,
            cwd=tool_dir,
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=_camofox_env(settings, host=desired_host, port=chosen_port),
            start_new_session=True,
        )
    state = CamofoxServiceState(
        owner=settings.host_id,
        pid=process.pid,
        host=desired_host,
        port=chosen_port,
        base_url=base_url,
        started_at=_utc_now_iso(),
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=command,
        tool_dir=str(tool_dir),
    )
    _write_state(settings, state)
    started_status = _await_camofox_start(settings, timeout_seconds=15)
    if started_status is not None:
        return started_status
    return build_camofox_service_status(settings)


def _stop_camofox_state_process(state: CamofoxServiceState) -> tuple[bool, str | None]:
    stop_error: str | None = None
    try:
        os.kill(state.pid, signal.SIGTERM)
        stopped = _wait_for_state_exit(state, timeout=5)
        if not stopped and _state_process_alive(state):
            os.kill(state.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
            stopped = _wait_for_state_exit(state, timeout=1)
    except OSError as exc:
        stop_error = redact_sensitive_text(exc, max_length=160)
        stopped = not _state_process_alive(state)
    return stopped or not _state_process_alive(state), stop_error


def stop_camofox_service(settings: Settings) -> CamofoxServiceStatus:
    """Stop only the app-owned Camofox process recorded in runtime state."""

    state = _read_state(settings)
    if state is None:
        return build_camofox_service_status(settings)
    if not _state_process_alive(state):
        _remove_state(settings)
        return build_camofox_service_status(settings)
    stopped, stop_error = _stop_camofox_state_process(state)
    if stopped or not _state_process_alive(state):
        _remove_state(settings)
    status = build_camofox_service_status(settings)
    if stop_error and status.app_owned:
        return status.model_copy(
            update={
                "message": f"Unable to stop app-owned Camofox: {stop_error}",
            },
        )
    return status
