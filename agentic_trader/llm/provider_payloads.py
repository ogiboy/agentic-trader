"""JSON payload coercion helpers for LLM providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from agentic_trader.json_utils import object_list

JsonObject = dict[str, object]


def json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise RuntimeError(f"LLM provider returned a non-object payload: {value!r}")
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def json_object_or_none(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    for item in object_list(value):
        row = json_object_or_none(item)
        if row is not None:
            rows.append(row)
    return rows
