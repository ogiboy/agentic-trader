"""Shared payload helpers for small dataclass-backed contracts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, cast


def dataclass_payload(value: object) -> dict[str, object]:
    """
    Return a JSON-serializable dictionary representation of a dataclass instance.

    Parameters:
        value (object): Dataclass instance to convert.

    Returns:
        dict[str, object]: Dictionary produced from the dataclass suitable for JSON encoding.

    Raises:
        TypeError: If `value` is a dataclass type or not a dataclass instance.
    """

    if isinstance(value, type) or not is_dataclass(value):
        raise TypeError(f"expected dataclass instance, got {type(value).__name__}")
    return cast(dict[str, object], asdict(cast(Any, value)))
