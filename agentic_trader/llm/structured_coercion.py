"""Coercion and sanitization helpers for structured LLM payloads."""

import re
from collections.abc import Callable
from typing import Any, cast

from agentic_trader.json_utils import object_dict_or_none as _object_mapping


def coerce_numeric_strings(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: coerce_numeric_strings(v) for k, v in cast(dict[Any, Any], obj).items()
        }
    if isinstance(obj, list):
        return [coerce_numeric_strings(item) for item in cast(list[Any], obj)]
    if isinstance(obj, str):
        text = obj.strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
            try:
                return int(text) if text.isdigit() else float(text)
            except (ValueError, TypeError):
                return obj
    return obj


def get_by_loc(obj: Any, path: tuple[str | int, ...]) -> Any:
    current: object = obj
    for part in path:
        current_mapping = _object_mapping(current)
        if current_mapping is not None and isinstance(part, str):
            current = current_mapping.get(part)
        elif isinstance(current, list) and isinstance(part, int):
            current_list = cast(list[object], current)
            if 0 <= part < len(current_list):
                current = current_list[part]
            else:
                return None
        else:
            return None
    return current


def set_by_loc(obj: Any, path: tuple[str | int, ...], value: Any) -> bool:
    if not path:
        return False
    current = obj
    for part in path[:-1]:
        next_item = navigate_one(current, part)
        if next_item is None:
            return False
        current = next_item
    last_part = path[-1]
    if isinstance(current, dict) and isinstance(last_part, str):
        current[last_part] = value
        return True
    if isinstance(current, list) and isinstance(last_part, int):
        current_list = cast(list[object], current)
        if 0 <= last_part < len(current_list):
            current_list[last_part] = value
            return True
    return False


def navigate_one(obj: Any, key: str | int) -> Any:
    if isinstance(obj, dict) and isinstance(key, str):
        if key not in cast(dict[str, Any], obj):
            cast(dict[str, Any], obj)[key] = {}
        return cast(dict[str, Any], obj)[key]
    if (
        isinstance(obj, list)
        and isinstance(key, int)
        and 0 <= key < len(cast(list[Any], obj))
    ):
        return cast(list[Any], obj)[key]
    return None


def coerce_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        normalized = value.strip().lower()
        qualitative = {
            "none": 0.0,
            "unknown": 0.0,
            "very low": 0.1,
            "low": 0.25,
            "medium": 0.5,
            "moderate": 0.5,
            "high": 0.75,
            "very high": 0.9,
        }
        if normalized in qualitative:
            return qualitative[normalized]
        if normalized.endswith("%"):
            return min(max(float(normalized[:-1]) / 100.0, 0.0), 1.0)
    return min(max(float(value), 0.0), 1.0)


SANITIZE_RULES: dict[str, Callable[[Any], float | int]] = {
    "confidence": coerce_confidence,
    "confidence_cap": coerce_confidence,
    "position_size_pct": lambda value: min(
        max(float(value) if value is not None else 0.01, 0.01), 1.0
    ),
    "size_multiplier": lambda value: min(
        max(float(value) if value is not None else 0.01, 0.01), 1.0
    ),
    "max_holding_bars": lambda value: max(int(value) if value is not None else 1, 1),
    "stop_loss": lambda value: max(
        float(value) if value is not None else 1e-6, 1e-6
    ),
    "take_profit": lambda value: max(
        float(value) if value is not None else 1e-6, 1e-6
    ),
    "risk_reward_ratio": lambda value: max(
        float(value) if value is not None else 1e-6, 1e-6
    ),
}
