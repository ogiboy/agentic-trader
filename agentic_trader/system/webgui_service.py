"""App-owned local Web GUI process helpers.

The Web GUI is a thin operator shell over the Python runtime. This module
starts and stops only an app-owned local Next.js process, records owner-only
state/logs, and keeps the bind host loopback-only.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import httpx

from agentic_trader.config import Settings
from agentic_trader.runtime_status import is_process_alive
from agentic_trader.security import (
    ensure_private_directory,
    is_loopback_host,
    open_private_append_binary,
    redact_sensitive_text,
)
from agentic_trader.system import webgui_service_process as _process_helpers
from agentic_trader.system import webgui_service_status as _status_helpers
from agentic_trader.system.webgui_service_state import (
    WebGUIServiceState,
    WebGUIServiceStatus,
    read_webgui_service_state as _state_read_webgui_service_state,
    remove_webgui_service_state as _state_remove_webgui_service_state,
    tail_webgui_service_text,
    webgui_service_dir,
    webgui_service_state_path,
    write_webgui_service_state as _state_write_webgui_service_state,
)
from agentic_trader.time_utils import utc_now_iso as _utc_now_iso

DEFAULT_WEBGUI_HOST = "127.0.0.1"
DEFAULT_WEBGUI_PORT = 3210
WEBGUI_PORT_CANDIDATES = (3210, *range(3211, 3221))
LOCAL_HTTP_SCHEME = "http"
LSOF_LISTEN_FILTER = _process_helpers.LSOF_LISTEN_FILTER
MINIMAL_WEBGUI_ENV_KEYS = _process_helpers.MINIMAL_WEBGUI_ENV_KEYS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def webgui_dir() -> Path:
    return _repo_root() / "webgui"


def _read_state(settings: Settings) -> WebGUIServiceState | None:
    return _state_read_webgui_service_state(settings)


def _write_state(settings: Settings, state: WebGUIServiceState) -> None:
    _state_write_webgui_service_state(settings, state)


def _remove_state(settings: Settings) -> None:
    _state_remove_webgui_service_state(settings)


def read_webgui_service_state(settings: Settings) -> WebGUIServiceState | None:
    return _read_state(settings)


def write_webgui_service_state(settings: Settings, state: WebGUIServiceState) -> None:
    _write_state(settings, state)


def remove_webgui_service_state(settings: Settings) -> None:
    _remove_state(settings)


def _tail_text(path: str | None, *, limit: int = 12) -> list[str]:
    return tail_webgui_service_text(path, limit=limit)


def _is_port_available(host: str, port: int) -> bool:
    return _process_helpers.is_port_available(host, port)


def choose_webgui_port(host: str, preferred_port: int = DEFAULT_WEBGUI_PORT) -> int:
    """Choose a loopback Web GUI port without taking over other processes."""

    if not is_loopback_host(host):
        raise ValueError("webgui_host_must_be_loopback")
    candidates = [preferred_port, *WEBGUI_PORT_CANDIDATES]
    seen: set[int] = set()
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        if _is_port_available(host, port):
            return port
    raise RuntimeError("no_free_webgui_port_found")


def _webgui_url(host: str, port: int) -> str:
    return f"{LOCAL_HTTP_SCHEME}://{host}:{port}"


def _webgui_package_available() -> bool:
    root = webgui_dir()
    return (root / "package.json").exists() and (root / "src").exists()


def _node_command_path() -> str | None:
    return shutil.which("node")


def _next_cli_path() -> Path | None:
    next_cli = webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next"
    if next_cli.exists():
        return next_cli
    return None


def _webgui_runtime_command(host: str, port: int) -> list[str]:
    node_path = _node_command_path()
    next_cli = _next_cli_path()
    if node_path is None:
        raise RuntimeError("node is not installed or not on PATH.")
    if next_cli is None:
        raise RuntimeError("Web GUI dependencies are missing. Run pnpm install first.")
    return [
        node_path,
        str(next_cli),
        "dev",
        "--hostname",
        host,
        "-p",
        str(port),
    ]


def _webgui_reachable(url: str) -> tuple[bool, str]:
    try:
        response = httpx.get(url, timeout=2.0)
        if response.status_code < 500:
            return True, "Web GUI is reachable."
        return False, f"Web GUI returned HTTP {response.status_code}."
    except Exception as exc:
        return (
            False,
            f"Unable to reach Web GUI: {redact_sensitive_text(exc, max_length=160)}",
        )


def _webgui_env() -> dict[str, str]:
    """Return the subprocess env for the local Web GUI dev server."""

    return _process_helpers.webgui_env()


def _process_command_line(pid: int) -> str | None:
    return _process_helpers.process_command_line(pid)


def webgui_process_command_line(pid: int) -> str | None:
    return _process_command_line(pid)


def _listen_port_owner_pid(host: str, port: int) -> int | None:
    return _process_helpers.listen_port_owner_pid(host, port)


def webgui_listen_port_owner_pid(host: str, port: int) -> int | None:
    return _listen_port_owner_pid(host, port)


def _process_cwd(pid: int) -> Path | None:
    return _process_helpers.process_cwd(pid)


def _command_line_matches_webgui(command_line: str, state: WebGUIServiceState) -> bool:
    normalized = command_line.replace("\\", "/").lower()
    return (
        "node" in normalized
        and "next" in normalized
        and str(state.port) in normalized
        and ("webgui" in normalized or "node_modules/next" in normalized)
    )


def _process_looks_like_webgui(pid: int) -> bool:
    process_cwd = _process_cwd(pid)
    if process_cwd == webgui_dir().resolve():
        return True
    command_line = _process_command_line(pid)
    if not command_line:
        return False
    normalized = command_line.replace("\\", "/").lower()
    return "node" in normalized and "next" in normalized and "webgui" in normalized


def _process_matches_state(state: WebGUIServiceState) -> bool:
    """
    Verify that the persisted WebGUIServiceState corresponds to a running Web GUI process.

    Parameters:
        state (WebGUIServiceState): Persisted state record containing expected PID, host, and port.

    Returns:
        bool: `True` if the recorded PID is currently a listener for the configured host/port and either the process's working directory is the Web GUI directory or its command line matches expected Web GUI markers; `False` otherwise.
    """
    if _listen_port_owner_pid(state.host, state.port) != state.pid:
        return False
    process_cwd = _process_cwd(state.pid)
    if process_cwd == webgui_dir().resolve():
        return True
    command_line = _process_command_line(state.pid)
    if command_line:
        return _command_line_matches_webgui(command_line, state)
    return True


def webgui_process_matches_state(state: WebGUIServiceState) -> bool:
    return _process_matches_state(state)


def _state_process_alive(state: WebGUIServiceState | None) -> bool:
    """
    Return whether the persisted Web GUI state corresponds to a running process that matches the recorded state.

    Parameters:
        state (WebGUIServiceState | None): Persisted runtime state to verify; may be None.

    Returns:
        True if state is not None, the recorded PID is alive, and the running process matches the recorded state; False otherwise.
    """
    return bool(
        state is not None
        and is_process_alive(state.pid)
        and _process_matches_state(state)
    )


def _send_process_signal(
    pid: int, signal_number: int, *, process_group: bool = False
) -> bool:
    """
    Send a POSIX signal to a process or its process group.

    Attempts to send `signal_number` to the process group of `pid` when `process_group=True` and the platform supports process-group signaling; otherwise sends the signal to the single process `pid`. Treats a missing process (ProcessLookupError) as success. Returns `True` if the signal was delivered or the target process was already absent, `False` if an operating-system error prevented sending the signal.

    Parameters:
        pid (int): PID of the target process.
        signal_number (int): Numeric signal to send (e.g., `signal.SIGTERM`).
        process_group (bool): If `True`, attempt to signal the process group of `pid` instead of the single process; falls back to signaling the single process on failure.

    Returns:
        bool: `True` if the signal was sent or the process was not found, `False` if an error prevented sending the signal.
    """
    if process_group and hasattr(os, "killpg") and hasattr(os, "getpgid"):
        try:
            os.killpg(os.getpgid(pid), signal_number)
            return True
        except ProcessLookupError:
            return True
        except OSError:
            pass
    try:
        os.kill(pid, signal_number)
        return True
    except ProcessLookupError:
        return True
    except OSError:
        return False


def _verified_stop_pids(state: WebGUIServiceState) -> list[int]:
    """
    Identify PIDs associated with the recorded app-owned Web GUI that are safe to signal individually.

    Inspects the provided persisted state and returns PIDs that are verified to belong to the Web GUI process:
    - Includes `state.pid` when the recorded process is alive and still matches the recorded state.
    - Includes `state.launcher_pid` when its command line indicates it belongs to the Web GUI and it is not already included.

    Parameters:
        state (WebGUIServiceState): Persisted Web GUI service state to verify.

    Returns:
        list[int]: Verified PIDs safe to signal individually; may be empty.
    """

    pids: list[int] = []
    if _state_process_alive(state):
        pids.append(state.pid)
    if state.launcher_pid is not None and state.launcher_pid not in pids:
        launcher_line = _process_command_line(state.launcher_pid)
        if launcher_line and _command_line_matches_webgui(launcher_line, state):
            pids.append(state.launcher_pid)
    return pids


def _send_state_signal(state: WebGUIServiceState, signal_number: int) -> bool:
    """
    Send the given signal to the recorded service process group and to any additional verified PIDs.

    Parameters:
        state (WebGUIServiceState): Persisted service state containing the primary PID and optional launcher PID.
        signal_number (int): Numeric signal value to send (e.g., signal.SIGTERM, signal.SIGKILL).

    Returns:
        `true` if any signal was successfully sent, `false` otherwise.
    """

    verified_pids = _verified_stop_pids(state)
    sent = _send_process_signal(state.pid, signal_number, process_group=True)
    for pid in verified_pids:
        sent = _send_process_signal(pid, signal_number) or sent
    return sent


def _wait_for_state_exit(state: WebGUIServiceState, *, timeout: float) -> bool:
    """
    Waits until the recorded Web GUI process is no longer alive or the timeout elapses.

    Parameters:
        state (WebGUIServiceState): Persisted app-owned Web GUI state whose `pid` and process ownership are checked.
        timeout (float): Maximum number of seconds to wait.

    Returns:
        bool: `true` if the process is no longer alive by the end of the wait, `false` otherwise.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _state_process_alive(state):
        time.sleep(0.2)
    return not _state_process_alive(state)


def _webgui_runtime_status_fields() -> tuple[str | None, Path | None, bool]:
    command_path = _node_command_path()
    dependency_path = _next_cli_path()
    package_available = _webgui_package_available()
    return command_path, dependency_path, package_available


def _status_url(
    *,
    app_state: WebGUIServiceState | None,
    state: WebGUIServiceState | None,
) -> str:
    return _status_helpers.status_url(
        app_state=app_state,
        state=state,
        default_url=_webgui_url(DEFAULT_WEBGUI_HOST, DEFAULT_WEBGUI_PORT),
    )


def _webgui_status_message(
    *,
    package_available: bool,
    command_path: str | None,
    dependency_path: Path | None,
    app_state: WebGUIServiceState | None,
    state: WebGUIServiceState | None,
    reachable: bool,
    reachability_message: str,
) -> str:
    return _status_helpers.status_message(
        package_available=package_available,
        command_path=command_path,
        dependency_path=dependency_path,
        app_state=app_state,
        state=state,
        reachable=reachable,
        reachability_message=reachability_message,
    )


def build_webgui_service_status(
    settings: Settings, *, tail_limit: int = 12
) -> WebGUIServiceStatus:
    """Build a read-only Web GUI service status payload."""

    state = _read_state(settings)
    app_state = state if _state_process_alive(state) else None
    if app_state is None and state is None:
        external_status = _external_webgui_status(settings)
        if external_status is not None:
            return external_status
    url = _status_url(app_state=app_state, state=state)
    reachable, reachability_message = _webgui_reachable(url)
    command_path, dependency_path, package_available = _webgui_runtime_status_fields()
    message = _webgui_status_message(
        package_available=package_available,
        command_path=command_path,
        dependency_path=dependency_path,
        app_state=app_state,
        state=state,
        reachable=reachable,
        reachability_message=reachability_message,
    )
    return _status_helpers.state_status(
        app_state=app_state,
        url=url,
        reachable=reachable,
        runtime_fields=(command_path, dependency_path, package_available),
        state_path=webgui_service_state_path(settings),
        message=message,
        tail_reader=lambda path, limit: _tail_text(path, limit=limit),
        tail_limit=tail_limit,
    )


def _build_unverified_start_status(
    settings: Settings,
    state: WebGUIServiceState,
    *,
    service_reachable: bool,
    message: str,
    tail_limit: int = 12,
) -> WebGUIServiceStatus:
    command_path, dependency_path, package_available = _webgui_runtime_status_fields()
    return _status_helpers.unverified_start_status(
        state=state,
        service_reachable=service_reachable,
        runtime_fields=(command_path, dependency_path, package_available),
        state_path=webgui_service_state_path(settings),
        message=message,
        tail_reader=lambda path, limit: _tail_text(path, limit=limit),
        tail_limit=tail_limit,
    )


def _external_webgui_status(settings: Settings) -> WebGUIServiceStatus | None:
    command_path, dependency_path, package_available = _webgui_runtime_status_fields()
    return _status_helpers.external_status(
        default_host=DEFAULT_WEBGUI_HOST,
        ports=WEBGUI_PORT_CANDIDATES,
        runtime_fields=(command_path, dependency_path, package_available),
        state_path=webgui_service_state_path(settings),
        listen_port_owner_pid=_listen_port_owner_pid,
        process_looks_like_webgui=_process_looks_like_webgui,
        url_for=_webgui_url,
        reachability_probe=_webgui_reachable,
    )


def _spawn_webgui_process(
    settings: Settings,
    *,
    host: str,
    port: int,
) -> WebGUIServiceState:
    url = _webgui_url(host, port)
    ensure_private_directory(webgui_service_dir(settings))
    stdout_path = webgui_service_dir(settings) / "webgui.out.log"
    stderr_path = webgui_service_dir(settings) / "webgui.err.log"
    command = _webgui_runtime_command(host, port)
    with (
        open_private_append_binary(stdout_path) as stdout_handle,
        open_private_append_binary(stderr_path) as stderr_handle,
    ):
        process = subprocess.Popen(
            command,
            cwd=webgui_dir(),
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=_webgui_env(),
            start_new_session=True,
        )
    state = WebGUIServiceState(
        pid=process.pid,
        launcher_pid=process.pid,
        host=host,
        port=port,
        url=url,
        started_at=_utc_now_iso(),
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=command,
    )
    _write_state(settings, state)
    return state


def _wait_for_webgui_start(
    settings: Settings,
    state: WebGUIServiceState,
) -> WebGUIServiceStatus:
    deadline = time.monotonic() + 15
    last_reachable = False
    last_message = "Web GUI did not become reachable before the startup timeout."
    while time.monotonic() < deadline:
        listener_pid = _listen_port_owner_pid(state.host, state.port)
        if listener_pid is not None and listener_pid != state.pid:
            state = state.model_copy(
                update={
                    "pid": listener_pid,
                    "launcher_pid": state.launcher_pid,
                }
            )
            _write_state(settings, state)
        last_reachable, last_message = _webgui_reachable(state.url)
        status = build_webgui_service_status(settings)
        if status.app_owned and status.service_reachable and status.url == state.url:
            return status
        time.sleep(0.4)
    return _build_unverified_start_status(
        settings,
        state,
        service_reachable=last_reachable,
        message=(
            "Web GUI is reachable, but process ownership could not be verified."
            if last_reachable
            else last_message
        ),
    )


def start_webgui_service(
    settings: Settings,
    *,
    host: str = DEFAULT_WEBGUI_HOST,
    port: int = DEFAULT_WEBGUI_PORT,
) -> WebGUIServiceStatus:
    """Start an app-owned loopback Web GUI process."""

    if not is_loopback_host(host):
        raise RuntimeError("App-managed Web GUI must bind to a loopback host.")
    if not _webgui_package_available():
        raise RuntimeError("Web GUI package is missing.")
    _ = _webgui_runtime_command(host, port)
    existing = _read_state(settings)
    if _state_process_alive(existing):
        return build_webgui_service_status(settings)
    if existing is not None:
        _remove_state(settings)
    external_status = _external_webgui_status(settings)
    if external_status is not None:
        return external_status

    chosen_port = choose_webgui_port(host, port)
    state = _spawn_webgui_process(settings, host=host, port=chosen_port)
    return _wait_for_webgui_start(
        settings,
        state,
    )


def stop_webgui_service(settings: Settings) -> WebGUIServiceStatus:
    """
    Stop the app-owned Web GUI process recorded in persisted runtime state.

    Attempts a graceful shutdown of the recorded app-owned process; if the process does not exit, escalates to a stronger signal. If the process cannot be stopped, the persisted state is left intact so the operation can be retried later.

    Parameters:
        settings (Settings): Runtime settings that determine where the service state and logs are stored.

    Returns:
        WebGUIServiceStatus: Current service status after the stop attempt. If shutdown failed, the status message indicates the persisted state was preserved for retry.
    """

    state = _read_state(settings)
    if state is None:
        return build_webgui_service_status(settings)
    if _state_process_alive(state):
        _send_state_signal(state, signal.SIGTERM)
        stopped = _wait_for_state_exit(state, timeout=5)
        if not stopped:
            _send_state_signal(state, getattr(signal, "SIGKILL", signal.SIGTERM))
            stopped = _wait_for_state_exit(state, timeout=1)
        if not stopped:
            return build_webgui_service_status(settings).model_copy(
                update={
                    "message": (
                        "Unable to stop app-owned Web GUI; state preserved for retry."
                    )
                }
            )
    _remove_state(settings)
    return build_webgui_service_status(settings)
