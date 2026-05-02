"""Small security helpers shared by local-first runtime surfaces."""

from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from typing import IO


_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)\b([A-Z0-9_.-]*(?:api[_-]?key|secret|token|password)"
    r"[A-Z0-9_.-]*)(\s*[:=]\s*)([^\s,;\"']+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_AUTHORIZATION_PATTERN = re.compile(
    r"(?i)\b(Authorization)(\s*[:=]\s*)(?!Bearer\s)([^\s,;\"']+)"
)
_URL_SECRET_PATTERN = re.compile(
    r"(?i)([?&](?:api[_-]?key|apikey|token|secret|password|key)=)[^&\s]+"
)
_SENSITIVE_ENV_NAME_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|secret|token|password|authorization)"
)


def redact_sensitive_text(value: object, *, max_length: int | None = None) -> str:
    """Return a bounded string with common secret shapes masked."""
    text = str(value)
    for env_name, env_value in os.environ.items():
        if (
            env_value
            and len(env_value) >= 6
            and _SENSITIVE_ENV_NAME_PATTERN.search(env_name)
        ):
            text = text.replace(env_value, "<redacted>")
    text = _SENSITIVE_KEY_PATTERN.sub(r"\1\2<redacted>", text)
    text = _BEARER_PATTERN.sub("Bearer <redacted>", text)
    text = _AUTHORIZATION_PATTERN.sub(r"\1\2<redacted>", text)
    text = _URL_SECRET_PATTERN.sub(r"\1<redacted>", text)
    if max_length is not None and len(text) > max_length:
        return f"{text[:max_length]}...<truncated>"
    return text


def safe_exception_note(source: str, exc: BaseException) -> str:
    """Format an exception for persisted provider notes without raw secrets."""
    message = redact_sensitive_text(str(exc), max_length=160)
    return f"{source}: {type(exc).__name__}: {message}"


def ensure_private_directory(path: Path) -> None:
    """Create a local runtime directory and prefer owner-only permissions."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        return


def chmod_private_file(path: Path) -> None:
    """Best-effort owner-only permissions for runtime artifacts."""
    try:
        path.chmod(0o600)
    except OSError:
        return


def write_private_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write a text runtime artifact with owner-only file permissions."""
    ensure_private_directory(path.parent)
    path.write_text(text, encoding=encoding)
    chmod_private_file(path)


def append_private_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Append a text runtime artifact with owner-only file permissions."""
    ensure_private_directory(path.parent)
    with path.open("a", encoding=encoding) as handle:
        handle.write(text)
    chmod_private_file(path)


def open_private_append_binary(path: Path) -> IO[bytes]:
    """Open a binary append handle with owner-only creation permissions."""
    ensure_private_directory(path.parent)
    file_descriptor = os.open(
        path,
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o600,
    )
    chmod_private_file(path)
    return os.fdopen(file_descriptor, "ab")


def is_loopback_host(host: str) -> bool:
    """Return whether a bind or request host is local-loopback only."""
    normalized = host.strip().strip("[]").lower()
    if normalized in {"localhost", ""} or normalized.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False
