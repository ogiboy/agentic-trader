"""App-owned local Web GUI process helpers.

The Web GUI is a thin operator shell over the Python runtime. This module
starts and stops only an app-owned local Next.js process, records owner-only
state/logs, and keeps the bind host loopback-only.
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

DEFAULT_WEBGUI_HOST = "127.0.0.1"
DEFAULT_WEBGUI_PORT = 3210
WEBGUI_PORT_CANDIDATES = (3210, *range(3211, 3221))
LOCAL_HTTP_SCHEME = "http"
LSOF_LISTEN_FILTER = "-sTCP:LISTEN"
MINIMAL_WEBGUI_ENV_KEYS = (
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
    "VIRTUAL_ENV",
)


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def webgui_dir() -> Path:
    return _repo_root() / "webgui"


def webgui_service_dir(settings: Settings) -> Path:
    return settings.runtime_dir / "webgui_service"


def webgui_service_state_path(settings: Settings) -> Path:
    return webgui_service_dir(settings) / "webgui_service.json"


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _read_state(settings: Settings) -> WebGUIServiceState | None:
    path = webgui_service_state_path(settings)
    if not path.exists():
        return None
    try:
        return WebGUIServiceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_state(settings: Settings, state: WebGUIServiceState) -> None:
    write_private_text(
        webgui_service_state_path(settings),
        state.model_dump_json(indent=2),
    )


def _remove_state(settings: Settings) -> None:
    try:
        webgui_service_state_path(settings).unlink()
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


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


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

    env = {key: os.environ[key] for key in MINIMAL_WEBGUI_ENV_KEYS if key in os.environ}
    env["AGENTIC_TRADER_PYTHON"] = os.environ.get(
        "AGENTIC_TRADER_PYTHON", sys.executable
    )
    env["AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY"] = "1"
    env["WATCHPACK_POLLING"] = os.environ.get("WATCHPACK_POLLING", "true")
    for key, value in os.environ.items():
        if key.startswith("AGENTIC_TRADER_"):
            env.setdefault(key, value)
    return env


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
    """Return the PID listening on a local TCP port when lsof is available."""

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
        if line.startswith("n"):
            return Path(line[1:]).resolve()
    return None


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


def _state_process_alive(state: WebGUIServiceState | None) -> bool:
    """
    Determine whether the persisted Web GUI state corresponds to a currently running, matching process.
    
    Parameters:
        state (WebGUIServiceState | None): Persisted runtime state to verify.
    
    Returns:
        `true` if `state` is not `None`, the recorded PID is alive, and the running process matches the recorded state; `false` otherwise.
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
    Send the signal to the recorded process group, then to any verified child or launcher PIDs.
    
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
    if app_state is not None:
        return app_state.url
    if state is not None:
        return state.url
    return _webgui_url(DEFAULT_WEBGUI_HOST, DEFAULT_WEBGUI_PORT)


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
    if not package_available:
        return "Web GUI package is missing."
    if command_path is None:
        return "node is not installed or not on PATH."
    if dependency_path is None:
        return "Web GUI dependencies are missing. Run pnpm install first."
    if app_state is not None and reachable:
        return "App-owned Web GUI is running."
    if state is not None and app_state is None:
        return "Recorded Web GUI state is stale or process ownership could not be verified."
    return reachability_message


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
    return WebGUIServiceStatus(
        command_available=command_path is not None,
        command_path=command_path,
        package_available=package_available,
        dependency_available=dependency_path is not None,
        dependency_path=str(dependency_path) if dependency_path is not None else None,
        app_owned=app_state is not None,
        pid=app_state.pid if app_state is not None else None,
        host=app_state.host if app_state is not None else None,
        port=app_state.port if app_state is not None else None,
        url=url,
        service_reachable=reachable,
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
        state_path=str(webgui_service_state_path(settings)),
        message=message,
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
    return WebGUIServiceStatus(
        command_available=command_path is not None,
        command_path=command_path,
        package_available=package_available,
        dependency_available=dependency_path is not None,
        dependency_path=str(dependency_path) if dependency_path is not None else None,
        app_owned=False,
        pid=None,
        host=state.host,
        port=state.port,
        url=state.url,
        service_reachable=service_reachable,
        stdout_log_path=state.stdout_log_path,
        stderr_log_path=state.stderr_log_path,
        stdout_tail=_tail_text(state.stdout_log_path, limit=tail_limit),
        stderr_tail=_tail_text(state.stderr_log_path, limit=tail_limit),
        state_path=str(webgui_service_state_path(settings)),
        message=message,
    )


def _external_webgui_status(settings: Settings) -> WebGUIServiceStatus | None:
    command_path, dependency_path, package_available = _webgui_runtime_status_fields()
    for port in WEBGUI_PORT_CANDIDATES:
        owner_pid = _listen_port_owner_pid(DEFAULT_WEBGUI_HOST, port)
        if owner_pid is None or not _process_looks_like_webgui(owner_pid):
            continue
        url = _webgui_url(DEFAULT_WEBGUI_HOST, port)
        reachable, message = _webgui_reachable(url)
        if not reachable:
            continue
        return WebGUIServiceStatus(
            command_available=command_path is not None,
            command_path=command_path,
            package_available=package_available,
            dependency_available=dependency_path is not None,
            dependency_path=(
                str(dependency_path) if dependency_path is not None else None
            ),
            app_owned=False,
            pid=None,
            host=DEFAULT_WEBGUI_HOST,
            port=port,
            url=url,
            service_reachable=True,
            state_path=str(webgui_service_state_path(settings)),
            message=(
                "A Web GUI dev server is already reachable, but it was not "
                "started by webgui-service and will not be stopped by the app."
                if message == "Web GUI is reachable."
                else message
            ),
        )
    return None


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
    url = _webgui_url(host, chosen_port)
    ensure_private_directory(webgui_service_dir(settings))
    stdout_path = webgui_service_dir(settings) / "webgui.out.log"
    stderr_path = webgui_service_dir(settings) / "webgui.err.log"
    command = _webgui_runtime_command(host, chosen_port)
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
        port=chosen_port,
        url=url,
        started_at=_utc_now_iso(),
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=command,
    )
    _write_state(settings, state)
    deadline = time.monotonic() + 15
    last_reachable = False
    last_message = "Web GUI did not become reachable before the startup timeout."
    while time.monotonic() < deadline:
        listener_pid = _listen_port_owner_pid(host, chosen_port)
        if listener_pid is not None and listener_pid != state.pid:
            state = state.model_copy(
                update={
                    "pid": listener_pid,
                    "launcher_pid": process.pid,
                }
            )
            _write_state(settings, state)
        last_reachable, last_message = _webgui_reachable(url)
        status = build_webgui_service_status(settings)
        if status.app_owned and status.service_reachable and status.url == url:
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


def stop_webgui_service(settings: Settings) -> WebGUIServiceStatus:
    """
    Stop the app-owned Web GUI process recorded in persisted runtime state.
    
    Attempts to gracefully stop the recorded app-owned process and removes the persisted state if the process is no longer alive. If the process cannot be stopped, the persisted state is preserved and the returned status contains a message indicating the preserved state for retry.
    
    Parameters:
        settings (Settings): Runtime settings that determine state and storage paths.
    
    Returns:
        WebGUIServiceStatus: Current service status after the stop attempt; when shutdown fails the status message indicates the state was preserved for retry.
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
                        "Unable to stop app-owned Web GUI; state preserved "
                        "for retry."
                    )
                }
            )
    _remove_state(settings)
    return build_webgui_service_status(settings)
