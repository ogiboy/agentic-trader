"""Small JSON-shape helpers shared by operator surfaces and payload adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast


def object_mapping(value: object) -> Mapping[str, object]:
    """Return value as an object-keyed mapping when it already is one."""

    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def object_list(value: object) -> list[object]:
    """Return value as a list when it is a non-string sequence."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(cast(Sequence[object], value))
    return []


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    """Return mapping rows from a non-string sequence."""

    rows: list[Mapping[str, object]] = []
    for item in object_list(value):
        if isinstance(item, Mapping):
            rows.append(cast(Mapping[str, object], item))
    return rows
