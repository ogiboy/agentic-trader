"""Process and environment helpers for the app-owned Camofox service."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from collections.abc import Callable
from pathlib import Path

from agentic_trader.config import Settings

ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]

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


def node_command_path() -> str | None:
    return shutil.which("node")


def package_available(tool_dir: Path) -> bool:
    return (tool_dir / "package.json").exists() and (
        tool_dir / SERVER_SCRIPT_NAME
    ).exists()


def dependency_available(tool_dir: Path) -> bool:
    return (tool_dir / "node_modules").exists()


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def camofox_secret(settings: Settings, key: str) -> str | None:
    configured = {
        "CAMOFOX_ACCESS_KEY": settings.camofox_access_key,
        "CAMOFOX_API_KEY": settings.camofox_api_key,
        "CAMOFOX_ADMIN_KEY": settings.camofox_admin_key,
    }.get(key)
    return configured or os.environ.get(key)


def camofox_access_token(settings: Settings) -> str | None:
    """Return the token used to globally gate the app-owned helper."""

    return camofox_secret(settings, "CAMOFOX_ACCESS_KEY") or camofox_secret(
        settings,
        "CAMOFOX_API_KEY",
    )


def camofox_env(settings: Settings, *, host: str, port: int) -> dict[str, str]:
    """Return a narrowed Camofox subprocess env."""

    env = {
        key: os.environ[key] for key in MINIMAL_CAMOFOX_ENV_KEYS if key in os.environ
    }
    for key in CAMOFOX_SECRET_KEYS:
        value = camofox_secret(settings, key)
        if value:
            env[key] = value
    if "CAMOFOX_ACCESS_KEY" not in env:
        access_token = camofox_access_token(settings)
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


def process_command_line(
    pid: int,
    *,
    run: ProcessRunner = subprocess.run,
) -> str | None:
    try:
        completed = run(
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


def listen_port_owner_pid(
    host: str,
    port: int,
    *,
    run: ProcessRunner = subprocess.run,
) -> int | None:
    query_host = "127.0.0.1" if host == "localhost" else host.strip("[]")
    try:
        completed = run(
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


def process_cwd(
    pid: int,
    *,
    run: ProcessRunner = subprocess.run,
) -> Path | None:
    try:
        completed = run(
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
