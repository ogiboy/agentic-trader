"""App-owned local Camofox Browser helper process.

Camofox is optional browser infrastructure for research evidence collection.
This module starts and stops only an app-owned loopback process, records
owner-only state/logs, and avoids inheriting trading/broker/provider secrets.
"""

from __future__ import annotations

import os
import signal
import shutil
import socket
import subprocess
import time
from pathlib import Path
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
from agentic_trader.system.tool_roots import (
    local_tool_status_payload,
    resolve_configured_tool_path,
)

DEFAULT_CAMOFOX_HOST = "127.0.0.1"
DEFAULT_CAMOFOX_PORT = 9377
CAMOFOX_PORT_CANDIDATES = (9377, *range(9378, 9398))
LOCAL_HTTP_SCHEME = "http"
LSOF_LISTEN_FILTER = "-sTCP:LISTEN"
SERVER_SCRIPT_NAME = "server.js"
MINIMAL_CAMOFOX_ENV_KEYS = (
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
CAMOFOX_SECRET_KEYS = (
    "CAMOFOX_ACCESS_KEY",
    "CAMOFOX_API_KEY",
    "CAMOFOX_ADMIN_KEY",
)
CAMOFOX_DATA_KEYS = (
    "CAMOFOX_COOKIES_DIR",
    "CAMOFOX_PROFILE_DIR",
    "CAMOFOX_TRACES_DIR",
    "CAMOFOX_TRACES_MAX_BYTES",
    "CAMOFOX_TRACES_TTL_HOURS",
)
CAMOFOX_PROXY_KEYS = (
    "PROXY_HOST",
    "PROXY_PORT",
    "PROXY_PORTS",
    "PROXY_USER",
    "PROXY_PASS",
    "PROXY_BACKCONNECT_HOST",
    "PROXY_BACKCONNECT_PORT",
)


class CamofoxServiceState(BaseModel):
    """Persisted state for an app-owned Camofox process."""

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
    install_hint: str = ""
    notes: list[str] = Field(default_factory=list)
    command_available: bool
    command_path: str | None = None
    package_available: bool
    dependency_available: bool = False
    dependency_path: str | None = None
    access_key_configured: bool
    app_owned: bool = False
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


def camofox_service_dir(settings: Settings) -> Path:
    return settings.runtime_dir / "camofox_service"


def camofox_service_state_path(settings: Settings) -> Path:
    return camofox_service_dir(settings) / "camofox_service.json"


def camofox_tool_dir(settings: Settings) -> Path:
    return resolve_configured_tool_path(
        settings.research_camofox_tool_dir,
        default_tool="camofox-browser",
    )


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _read_state(settings: Settings) -> CamofoxServiceState | None:
    path = camofox_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return CamofoxServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_state(settings: Settings, state: CamofoxServiceState) -> None:
    write_private_text(
        camofox_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def _remove_state(settings: Settings) -> None:
    try:
        camofox_service_state_path(settings).unlink()
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


def _tail_contains_browser_launch_failure(state: CamofoxServiceState | None) -> bool:
    if state is None:
        return False
    recent_lines = [
        *_tail_text(state.stdout_log_path, limit=20),
        *_tail_text(state.stderr_log_path, limit=20),
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


def _node_command_path() -> str | None:
    return shutil.which("node")


def _package_available(tool_dir: Path) -> bool:
    return (tool_dir / "package.json").exists() and (
        tool_dir / SERVER_SCRIPT_NAME
    ).exists()


def _dependency_available(tool_dir: Path) -> bool:
    return (tool_dir / "node_modules").exists()


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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


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
    configured = {
        "CAMOFOX_ACCESS_KEY": settings.camofox_access_key,
        "CAMOFOX_API_KEY": settings.camofox_api_key,
        "CAMOFOX_ADMIN_KEY": settings.camofox_admin_key,
    }.get(key)
    return configured or os.environ.get(key)


def _camofox_access_token(settings: Settings) -> str | None:
    """Return the token used to globally gate the app-owned helper."""

    return _camofox_secret(settings, "CAMOFOX_ACCESS_KEY") or _camofox_secret(
        settings,
        "CAMOFOX_API_KEY",
    )


def _camofox_env(settings: Settings, *, host: str, port: int) -> dict[str, str]:
    """Return a narrowed Camofox subprocess env."""

    env = {
        key: os.environ[key] for key in MINIMAL_CAMOFOX_ENV_KEYS if key in os.environ
    }
    for key in CAMOFOX_SECRET_KEYS:
        value = _camofox_secret(settings, key)
        if value:
            env[key] = value
    if "CAMOFOX_ACCESS_KEY" not in env:
        access_token = _camofox_access_token(settings)
        if access_token:
            env["CAMOFOX_ACCESS_KEY"] = access_token
    for key in (*CAMOFOX_DATA_KEYS, *CAMOFOX_PROXY_KEYS):
        if key in os.environ:
            env[key] = os.environ[key]
    env["CAMOFOX_HOST"] = host
    env["CAMOFOX_PORT"] = str(port)
    env["CAMOFOX_CRASH_REPORT_ENABLED"] = os.environ.get(
        "CAMOFOX_CRASH_REPORT_ENABLED",
        "false",
    )
    env["CAMOFOX_BROWSER_PREWARM"] = os.environ.get("CAMOFOX_BROWSER_PREWARM", "false")
    return env


def _runtime_command(tool_dir: Path) -> list[str]:
    node_path = _node_command_path()
    if node_path is None:
        raise RuntimeError("node is not installed or not on PATH.")
    if not _package_available(tool_dir):
        raise RuntimeError(f"Camofox browser helper is missing at {tool_dir}.")
    if not _dependency_available(tool_dir):
        raise RuntimeError(
            "Camofox dependencies are missing. Run "
            "`pnpm --dir tools/camofox-browser install --ignore-scripts`."
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
    ok = bool(payload.get("ok")) if isinstance(payload, dict) else False
    if not ok:
        return True, False, "Camofox health is not ok."
    browser_running = (
        payload.get("browserRunning") if isinstance(payload, dict) else None
    )
    browser_connected = (
        payload.get("browserConnected") if isinstance(payload, dict) else None
    )
    if browser_running is False or browser_connected is False:
        return True, True, "Camofox server is reachable; browser launches on demand."
    return True, True, "Camofox is reachable."


def _process_command_line(pid: int) -> str | None:
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


def _listen_port_owner_pid(host: str, port: int) -> int | None:
    query_host = "127.0.0.1" if host == "localhost" else host.strip("[]")
    try:
        completed = subprocess.run(
            [
                "lsof",
                "-nP",
                "-a",
                f"-iTCP@{query_host}:{port}",
                LSOF_LISTEN_FILTER,
                "-Fp",
            ],
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


def _process_cwd(pid: int) -> Path | None:
    try:
        completed = subprocess.run(
            ["lsof", "-nP", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        if line.startswith("n") and len(line) > 1:
            return Path(line[1:]).resolve()
    return None


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
) -> str | None:
    if not is_loopback_host(probe_host):
        return "Camofox base URL must remain loopback."
    if not package_available:
        return "Camofox browser helper is missing."
    if command_path is None:
        return "node is not installed or not on PATH."
    if not dependency_available:
        return (
            "Camofox dependencies are missing. Run "
            "`pnpm --dir tools/camofox-browser install --ignore-scripts`."
        )
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
    """Build a read-only Camofox service status payload."""

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
    """Start an app-owned loopback Camofox process."""

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
