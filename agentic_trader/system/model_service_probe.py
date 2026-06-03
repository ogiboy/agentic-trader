from __future__ import annotations

from typing import Any, Mapping, cast
from urllib.parse import urlparse

import httpx

from agentic_trader.json_utils import object_list as _object_list
from agentic_trader.security import is_loopback_host, redact_sensitive_text

LOCAL_HTTP_SCHEME = "http"


def json_object_or_none(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    for item in _object_list(value):
        row = json_object_or_none(item)
        if row is not None:
            rows.append(row)
    return rows


def model_service_api_root_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/")
        trimmed = base_url.removesuffix("/")
        if path == "/v1":
            return trimmed[: -len("/v1")]
        return trimmed
    return base_url.removesuffix("/v1").rstrip("/")


def same_loopback_api_root(left: str, right: str) -> bool:
    left_parsed = urlparse(left)
    right_parsed = urlparse(right)
    if not left_parsed.scheme or not right_parsed.scheme:
        return left.rstrip("/") == right.rstrip("/")
    if left_parsed.scheme != right_parsed.scheme:
        return False
    left_host = left_parsed.hostname or ""
    right_host = right_parsed.hostname or ""
    left_port = left_parsed.port or (443 if left_parsed.scheme == "https" else 80)
    right_port = right_parsed.port or (443 if right_parsed.scheme == "https" else 80)
    if left_port != right_port:
        return False
    if left_parsed.path.rstrip("/") != right_parsed.path.rstrip("/"):
        return False
    if left_host == right_host:
        return True
    return is_loopback_host(left_host) and is_loopback_host(right_host)


def base_url(host: str, port: int) -> str:
    return f"{LOCAL_HTTP_SCHEME}://{host}:{port}"


def fetch_ollama_tags(
    api_root: str, *, timeout_seconds: float = 2.0
) -> tuple[bool, list[str], str]:
    try:
        response = httpx.get(f"{api_root}/api/tags", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return (
            False,
            [],
            f"Unable to reach Ollama: {redact_sensitive_text(exc, max_length=160)}",
        )
    models: list[str] = []
    payload_object = json_object_or_none(payload)
    for item in object_mapping_list(
        payload_object.get("models") if payload_object is not None else None
    ):
        name = item.get("name")
        if isinstance(name, str):
            models.append(name)
    return True, sorted(models), "Ollama is reachable."


def ollama_error_from_response(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return f"HTTP {getattr(response, 'status_code', 'error')}"
    payload_object = json_object_or_none(payload)
    if payload_object is not None:
        error_obj = payload_object.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            return error_obj.strip()[:240]
        error_mapping = json_object_or_none(error_obj)
        if error_mapping is not None:
            message = error_mapping.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:240]
    return f"HTTP {getattr(response, 'status_code', 'error')}"


def probe_ollama_generation(
    api_root: str,
    model_name: str,
    *,
    timeout_seconds: float = 20.0,
) -> tuple[bool, str]:
    body: dict[str, Any] = {
        "model": model_name,
        "prompt": "Reply with OK.",
        "stream": False,
        "options": {"num_predict": 4},
    }
    try:
        response = httpx.post(
            f"{api_root}/api/generate",
            json=body,
            timeout=timeout_seconds,
        )
        if response.status_code >= 400:
            return False, ollama_error_from_response(response)
        payload = response.json()
    except Exception as exc:
        return False, redact_sensitive_text(exc, max_length=240)
    payload_object = json_object_or_none(payload)
    if payload_object is None:
        return False, "Ollama generation response was not a JSON object."
    error = payload_object.get("error")
    if isinstance(error, str) and error.strip():
        return False, redact_sensitive_text(error, max_length=240)
    generated = payload_object.get("response")
    if isinstance(generated, str):
        return True, "Generation probe succeeded."
    return False, "Ollama generation response did not include text."
