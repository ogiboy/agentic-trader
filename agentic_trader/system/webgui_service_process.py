"""OS process helpers for the local Web GUI service."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

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


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def webgui_env() -> dict[str, str]:
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


def process_command_line(pid: int) -> str | None:
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


def listen_port_owner_pid(host: str, port: int) -> int | None:
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


def process_cwd(pid: int) -> Path | None:
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
