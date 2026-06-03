from __future__ import annotations

from typing import Any

from agentic_trader.llm.openai_compat import short_redacted_error
from agentic_trader.llm.provider_payloads import (
    json_object_or_none,
    object_mapping_list,
)


def ollama_model_names(payload: dict[str, Any]) -> set[str]:
    models = object_mapping_list(payload.get("models"))
    available: set[str] = set()
    for item in models:
        name = item.get("name")
        if isinstance(name, str):
            available.add(name)
    return available


def ollama_generation_probe(
    *,
    client: Any,
    base_url: str,
    model_name: str,
    model_available: bool,
) -> tuple[bool, str]:
    if not model_available:
        return (
            False,
            "Generation probe skipped because the configured model is not listed.",
        )
    body: dict[str, Any] = {
        "model": model_name,
        "prompt": "Reply with OK.",
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 8,
        },
    }
    try:
        response = client.post(f"{base_url}/api/generate", json=body)
        status_code = getattr(response, "status_code", 200)
        if status_code >= 400:
            return False, ollama_error_from_response(response)
        response.raise_for_status()
        payload = json_object_or_none(response.json())
        if payload is None:
            return False, short_redacted_error("malformed or non-object probe payload")
        error_obj = payload.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            return False, short_redacted_error(error_obj)
        return True, "Generation probe completed."
    except Exception as exc:
        return False, short_redacted_error(str(exc)) or type(exc).__name__


def ollama_error_from_response(response: Any) -> str:
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


def ollama_health_message(
    *,
    model_available: bool,
    generation_available: bool | None,
    generation_message: str | None,
) -> str:
    if not model_available:
        return "Ollama is reachable, but the configured model is not listed."
    if generation_available is False:
        detail = generation_message or "generation probe failed"
        return (
            "Ollama is reachable and the model is listed, but a generation "
            f"probe failed: {detail}"
        )
    if generation_available is True:
        return "Ollama is reachable and the configured model can generate."
    return "Ollama is reachable and the configured model is available."
