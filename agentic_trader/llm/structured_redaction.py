"""Payload redaction helpers for structured LLM diagnostics."""

from typing import Any, cast

_SENSITIVE_PAYLOAD_KEYS = {"thinking", "thought", "thoughts", "reasoning"}


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in cast(dict[Any, Any], value).items():
            key_text = str(key)
            if key_text.lower() in _SENSITIVE_PAYLOAD_KEYS:
                redacted[key_text] = "<redacted>"
            else:
                redacted[key_text] = redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in cast(list[Any], value)]
    return value
