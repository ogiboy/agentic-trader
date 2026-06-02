"""OpenAI-compatible payload parsing and error helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

from agentic_trader.json_utils import object_list
from agentic_trader.security import redact_sensitive_text

JsonObject = dict[str, object]


class ErrorResponsePayload(Protocol):
    status_code: int

    def json(self) -> object: ...


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


def openai_compatible_model_ids(payload: Mapping[str, object]) -> set[str]:
    model_ids: set[str] = set()
    for item in object_mapping_list(payload.get("data")):
        model_id = item.get("id")
        if isinstance(model_id, str):
            model_ids.add(model_id)
    return model_ids


def openai_compatible_content(payload: Mapping[str, object]) -> str:
    choices = object_list(payload.get("choices"))
    if not choices:
        raise RuntimeError("OpenAI-compatible provider returned no choices.")
    first = json_object_or_none(choices[0])
    if first is None:
        raise RuntimeError("OpenAI-compatible provider returned malformed choices.")
    message = first.get("message")
    content = openai_compatible_message_content(message)
    if content:
        return content
    text = first.get("text")
    if isinstance(text, str):
        return text.strip()
    raise RuntimeError("OpenAI-compatible provider returned no text content.")


def openai_compatible_response_format(
    json_schema: dict[str, Any] | None,
) -> dict[str, Any]:
    if json_schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "agentic_trader_response",
            "schema": json_schema,
        },
    }


def openai_compatible_message_content(message: object) -> str:
    message_mapping = json_object_or_none(message)
    if message_mapping is None:
        return ""
    content = message_mapping.get("content")
    if isinstance(content, str):
        return content.strip()
    return openai_compatible_text_parts(object_list(content))


def openai_compatible_text_parts(content: list[object]) -> str:
    text_parts: list[str] = []
    for part in object_mapping_list(content):
        text = part.get("text")
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts).strip()


def openai_compatible_error_from_response(response: ErrorResponsePayload) -> str:
    try:
        payload = response.json()
    except Exception:
        return f"HTTP {getattr(response, 'status_code', 'error')}"
    payload_object = json_object_or_none(payload)
    if payload_object is not None:
        error_obj = payload_object.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            return short_redacted_error(error_obj)
        error_mapping = json_object_or_none(error_obj)
        if error_mapping is not None:
            message = error_mapping.get("message")
            if isinstance(message, str) and message.strip():
                return short_redacted_error(message)
    return f"HTTP {getattr(response, 'status_code', 'error')}"


def short_redacted_error(value: str) -> str:
    return redact_sensitive_text(value).strip()[:240]
