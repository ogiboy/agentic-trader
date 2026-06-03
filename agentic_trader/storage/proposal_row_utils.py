"""Row payload helpers shared by proposal storage modules."""

import json
from typing import Any, cast


def str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def decode_object_payload(value: Any) -> dict[str, object]:
    if value is None:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], payload).items()}
