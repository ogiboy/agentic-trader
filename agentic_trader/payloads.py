"""Shared payload helpers for small dataclass-backed contracts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, cast


def dataclass_payload(value: object) -> dict[str, object]:
    """Return a JSON-oriented dictionary for a dataclass instance."""

    if isinstance(value, type) or not is_dataclass(value):
        raise TypeError(f"expected dataclass instance, got {type(value).__name__}")
    return cast(dict[str, object], asdict(cast(Any, value)))
