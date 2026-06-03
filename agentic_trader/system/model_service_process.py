"""Process, port, and environment helpers for app-managed Ollama."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from agentic_trader.runtime_status import is_process_alive
from agentic_trader.security import is_loopback_host
from agentic_trader.system.model_service_state import ModelServiceState

DEFAULT_APP_MANAGED_PORT = 11435
APP_MANAGED_ORPHAN_PORTS = (DEFAULT_APP_MANAGED_PORT, *range(11436, 11466))
KNOWN_OLLAMA_SERVICE_PORTS = (11434, *APP_MANAGED_ORPHAN_PORTS)
LSOF_LISTEN_FILTER = "-sTCP:LISTEN"
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


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def minimal_process_env(*, ollama_host: str | None = None) -> dict[str, str]:
    """Return a subprocess env that does not inherit provider/broker secrets."""

    env = {key: os.environ[key] for key in MINIMAL_ENV_KEYS if key in os.environ}
    if ollama_host:
        env["OLLAMA_HOST"] = ollama_host
    return env


def process_command_line(pid: int) -> str | None:
    if sys.platform.startswith("win"):
        return windows_process_command_line(pid)
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


def external_ollama_serve_pids(command_path: str | None) -> list[int]:
    if sys.platform.startswith("win"):
        return []
    executable_names = {"ollama"}
    if command_path:
        executable_names.add(Path(command_path).name)
    try:
        completed = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return ollama_listener_pids_from_lsof()
    if completed.returncode != 0:
        return ollama_listener_pids_from_lsof()
    pids: list[int] = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command_line = stripped.partition(" ")
        if not pid_text.isdigit():
            continue
        if is_ollama_serve_command(command_line, executable_names):
            pids.append(int(pid_text))
    return sorted(set(pids) | set(ollama_listener_pids_from_lsof()))


def is_ollama_serve_command(command_line: str, executable_names: set[str]) -> bool:
    parts = command_line.replace("\\", "/").lower().split()
    if len(parts) < 2:
        return False
    return Path(parts[0]).name in executable_names and parts[1] == "serve"


def ollama_listener_pids_from_lsof() -> list[int]:
    """Return Ollama listener PIDs without relying on process-list permissions."""

    output = run_lsof_listener_scan()
    if output is None:
        return []
    return sorted(parse_ollama_listener_pids(output))


def run_lsof_listener_scan() -> str | None:
    if sys.platform.startswith("win"):
        return None
    try:
        completed = subprocess.run(
            ["lsof", "-nP", "-iTCP", LSOF_LISTEN_FILTER, "-Fpcn"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def parse_ollama_listener_pids(output: str) -> set[int]:
    current_pid: int | None = None
    current_command: str | None = None
    pids: set[int] = set()
    for line in output.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current_pid = int(line[1:])
            current_command = None
            continue
        if line.startswith("c"):
            current_command = line[1:].strip().lower()
            continue
        if not line.startswith("n") or current_pid is None:
            continue
        endpoint = line[1:].strip()
        host, _, port_text = endpoint.rpartition(":")
        if is_known_ollama_listener(current_command, host, port_text):
            pids.add(current_pid)
    return pids


def is_known_ollama_listener(
    command: str | None,
    host: str,
    port_text: str,
) -> bool:
    port = int(port_text) if port_text.isdigit() else None
    return (
        command == "ollama"
        and port in KNOWN_OLLAMA_SERVICE_PORTS
        and is_loopback_host(host)
    )


def listening_loopback_ports_for_pid(pid: int) -> set[int]:
    try:
        completed = subprocess.run(
            ["lsof", "-nP", "-a", "-p", str(pid), "-iTCP", LSOF_LISTEN_FILTER, "-FpPn"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return set()
    if completed.returncode != 0:
        return set()
    ports: set[int] = set()
    for line in completed.stdout.splitlines():
        if not line.startswith("n"):
            continue
        endpoint = line[1:].strip()
        host, _, port_text = endpoint.rpartition(":")
        if not port_text.isdigit() or not is_loopback_host(host):
            continue
        ports.add(int(port_text))
    return ports


def orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    """Return stale app-managed Ollama PIDs without touching host/default 11434."""

    active_pid = active_state.pid if active_state is not None else None
    orphan_pids: list[int] = []
    managed_ports = set(APP_MANAGED_ORPHAN_PORTS)
    for pid in external_ollama_serve_pids(command_path):
        if pid == active_pid:
            continue
        if listening_loopback_ports_for_pid(pid) & managed_ports:
            orphan_pids.append(pid)
    return sorted(set(orphan_pids))


def cleanup_orphan_app_managed_ollama_pids(
    command_path: str | None,
    active_state: ModelServiceState | None,
) -> list[int]:
    """Best-effort cleanup for stale app-managed Ollama listeners."""

    stopped_pids: list[int] = []
    for pid in orphan_app_managed_ollama_pids(command_path, active_state):
        if stop_pid(pid):
            stopped_pids.append(pid)
    return stopped_pids


def wait_for_pid_exit(pid: int, *, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not is_process_alive(pid):
            return True
        time.sleep(0.2)
    return not is_process_alive(pid)


def stop_pid(pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
        stopped = wait_for_pid_exit(pid, timeout_seconds=5)
        if not stopped and is_process_alive(pid):
            os.kill(pid, signal.SIGKILL)
            stopped = wait_for_pid_exit(pid, timeout_seconds=2)
    except OSError:
        stopped = not is_process_alive(pid)
    return stopped or not is_process_alive(pid)


def windows_process_command_line(pid: int) -> str | None:
    query = (
        "Get-CimInstance Win32_Process "
        f'-Filter "ProcessId = {pid}" | Select-Object -ExpandProperty CommandLine'
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


def listen_port_owner_pid(host: str, port: int) -> int | None:
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


def process_matches_state(state: ModelServiceState) -> bool:
    port_owner_pid = listen_port_owner_pid(state.host, state.port)
    if port_owner_pid == state.pid:
        return True
    if port_owner_pid is not None:
        return False
    command_line = process_command_line(state.pid)
    if not command_line:
        return False
    executable = Path(state.command[0]).name if state.command else "ollama"
    if executable not in command_line or "serve" not in command_line:
        return False
    return True


def state_process_alive(state: ModelServiceState | None) -> bool:
    return bool(
        state is not None
        and is_process_alive(state.pid)
        and process_matches_state(state)
    )


def wait_for_state_process_exit(
    state: ModelServiceState,
    *,
    timeout_seconds: float,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not state_process_alive(state):
            return True
        time.sleep(0.2)
    return not state_process_alive(state)


def choose_app_managed_port(host: str, preferred_port: int) -> int:
    """Choose a loopback port, avoiding already-running external services."""

    if not is_loopback_host(host):
        raise ValueError("model_service_host_must_be_loopback")
    for port in [preferred_port, DEFAULT_APP_MANAGED_PORT, *range(11436, 11466)]:
        if is_port_available(host, port):
            return port
    raise RuntimeError("no_free_model_service_port_found")
