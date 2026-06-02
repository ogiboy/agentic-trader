from __future__ import annotations

from typing import Any

from agentic_trader.llm.openai_compat import (
    openai_compatible_content,
    openai_compatible_error_from_response,
    short_redacted_error,
)
from agentic_trader.llm.provider_payloads import json_object_or_none
from agentic_trader.schemas import LLMHealthStatus


def openai_compatible_generation_probe(
    *,
    client: Any,
    base_url: str,
    headers: dict[str, str] | None,
    model_name: str,
    model_available: bool,
) -> tuple[bool, str]:
    if not model_available:
        return (
            False,
            "Generation probe skipped because the configured model is not listed.",
        )
    try:
        response = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "temperature": 0,
                "max_tokens": 8,
            },
        )
        status_code = getattr(response, "status_code", 200)
        if status_code >= 400:
            return False, openai_compatible_error_from_response(response)
        response.raise_for_status()
        payload = json_object_or_none(response.json())
        if payload is None:
            return False, short_redacted_error("malformed or non-object probe payload")
        openai_compatible_content(payload)
        return True, "Generation probe completed."
    except Exception as exc:
        return False, short_redacted_error(str(exc)) or type(exc).__name__


def openai_compatible_health_message(
    *,
    model_available: bool,
    generation_available: bool | None,
    generation_message: str | None,
) -> str:
    if not model_available:
        return (
            "OpenAI-compatible endpoint is reachable, but the configured "
            "model is not listed."
        )
    if generation_available is False:
        detail = generation_message or "generation probe failed"
        return (
            "OpenAI-compatible endpoint is reachable and the model is listed, "
            f"but a generation probe failed: {detail}"
        )
    if generation_available is True:
        return (
            "OpenAI-compatible endpoint is reachable and the configured model "
            "can generate."
        )
    return "OpenAI-compatible endpoint is reachable and the configured model is available."


def endpoint_rejected_health(
    *,
    provider_name: str,
    base_url: str,
    model_name: str,
    status_code: object,
    response_text: str,
    include_generation: bool,
) -> LLMHealthStatus:
    message = f"Endpoint reachable but rejected: HTTP {status_code} {response_text}".strip()
    return LLMHealthStatus(
        provider=provider_name,
        base_url=base_url,
        model_name=model_name,
        service_reachable=True,
        model_available=False,
        generation_available=False if include_generation else None,
        generation_message=message if include_generation else None,
        message=message,
    )


def reachable_health(
    *,
    provider_name: str,
    base_url: str,
    model_name: str,
    model_available: bool,
    generation_available: bool | None,
    generation_message: str | None,
) -> LLMHealthStatus:
    message = openai_compatible_health_message(
        model_available=model_available,
        generation_available=generation_available,
        generation_message=generation_message,
    )
    return LLMHealthStatus(
        provider=provider_name,
        base_url=base_url,
        model_name=model_name,
        service_reachable=True,
        model_available=model_available,
        generation_available=generation_available,
        generation_message=generation_message,
        message=message,
    )


def unreachable_health(
    *,
    provider_name: str,
    base_url: str,
    model_name: str,
    detail: str,
    include_generation: bool,
) -> LLMHealthStatus:
    message = f"Unable to reach OpenAI-compatible endpoint: {detail}"
    return LLMHealthStatus(
        provider=provider_name,
        base_url=base_url,
        model_name=model_name,
        service_reachable=False,
        model_available=False,
        generation_available=False if include_generation else None,
        generation_message=message if include_generation else None,
        message=message,
    )
