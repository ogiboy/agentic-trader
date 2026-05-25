from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, cast

import httpx

from agentic_trader.config import Settings
from agentic_trader.schemas import LLMHealthStatus
from agentic_trader.security import redact_sensitive_text

JsonObject = dict[str, object]


class ErrorResponsePayload(Protocol):
    status_code: int

    def json(self) -> object: ...


def _json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise RuntimeError(f"LLM provider returned a non-object payload: {value!r}")
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def _json_object_or_none(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def _object_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _object_mapping_list(value: object) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    for item in _object_list(value):
        row = _json_object_or_none(item)
        if row is not None:
            rows.append(row)
    return rows


class LLMProvider(Protocol):
    settings: Settings
    model_name: str
    provider_name: str
    base_url: str
    client: Any | None

    def generate(
        self,
        *,
        prompt: str,
        json_mode: bool = False,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a completion from the configured LLM for the given prompt.

        When `json_mode` is enabled the provider will attempt to return structured JSON output; if `json_schema` is supplied the provider will try to produce output conforming to that schema.

        Parameters:
            prompt (str): The user prompt to send to the model.
            json_mode (bool): If true, request the model produce JSON-structured output.
            json_schema (dict[str, Any] | None): Optional JSON Schema or format hint describing the desired structured output when `json_mode` is true.

        Returns:
            dict[str, Any]: The provider's parsed response payload (including generated text or structured JSON and any raw metadata).
        """
        ...

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        """
        Check reachability and availability of the LLM service.

        Parameters:
            include_generation: If true, run a lightweight generation probe.

        Returns:
            Structured LLM health information for reachability, model availability, and optional generation.
        """
        ...


class OllamaProvider:
    provider_name = "ollama"

    def __init__(self, settings: Settings, *, model_name: str | None = None):
        self.settings = settings
        self.model_name = model_name or settings.model_name
        self.base_url = settings.base_url.removesuffix("/v1").rstrip("/")
        self.client = httpx.Client(timeout=settings.request_timeout_seconds)

    def generate(
        self,
        *,
        prompt: str,
        json_mode: bool = False,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_output_tokens,
            },
        }
        if json_mode:
            body["format"] = json_schema or "json"
        response = self.client.post(f"{self.base_url}/api/generate", json=body)
        if (
            json_mode
            and json_schema is not None
            and getattr(response, "status_code", None) == 400
        ):
            body["format"] = "json"
            response = self.client.post(f"{self.base_url}/api/generate", json=body)
        response.raise_for_status()
        raw_payload: object = response.json()
        payload = _json_object_or_none(raw_payload)
        if payload is None:
            raise RuntimeError(f"Ollama returned a non-object payload: {raw_payload!r}")
        return cast(dict[str, Any], payload)

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        """
        Check Ollama service reachability and whether the configured model is listed, optionally performing a generation probe.

        Parameters:
            include_generation (bool): If True, perform a short generation request to verify the configured model can produce output; defaults to False.

        Returns:
            LLMHealthStatus: Structured health information including:
                - service_reachable: True if the /api/tags endpoint was reachable and returned successfully, False otherwise.
                - model_available: True if the configured model name appears in the returned model list, False otherwise.
                - generation_available: True if a generation probe succeeded, False if it failed, or None when `include_generation` is False.
                - generation_message: Human-readable detail from the generation probe when performed, or None.
                - message: Overall human-readable health summary.
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = _json_object(response.json())
            models = _object_mapping_list(payload.get("models"))
            available: set[str] = set()
            for item in models:
                name = item.get("name")
                if isinstance(name, str):
                    available.add(name)
            model_available = self.model_name in available
            generation_available: bool | None = None
            generation_message: str | None = None
            if include_generation:
                generation_available, generation_message = self._probe_generation(
                    model_available=model_available
                )
            message = self._health_message(
                model_available=model_available,
                generation_available=generation_available,
                generation_message=generation_message,
            )
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=True,
                model_available=model_available,
                generation_available=generation_available,
                generation_message=generation_message,
                message=message,
            )
        except Exception as exc:
            detail = _short_redacted_error(str(exc)) or type(exc).__name__
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                generation_available=False if include_generation else None,
                generation_message=(
                    f"Unable to reach Ollama: {detail}" if include_generation else None
                ),
                message=f"Unable to reach Ollama: {detail}",
            )

    def _probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        """
        Probe whether the configured model can perform a minimal generation request.

        Parameters:
                model_available (bool): Whether the configured model is listed/available; if False the probe is skipped.

        Returns:
                tuple[bool, str]: `True` and "Generation probe completed." when a generation succeeds; `False` and a diagnostic message otherwise. When skipped because the model is not listed, returns `False` and the message "Generation probe skipped because the configured model is not listed."
        """
        if not model_available:
            return (
                False,
                "Generation probe skipped because the configured model is not listed.",
            )
        body: dict[str, Any] = {
            "model": self.model_name,
            "prompt": "Reply with OK.",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 8,
            },
        }
        try:
            response = self.client.post(f"{self.base_url}/api/generate", json=body)
            status_code = getattr(response, "status_code", 200)
            if status_code >= 400:
                return False, self._error_from_response(response)
            response.raise_for_status()
            payload = _json_object_or_none(response.json())
            if payload is not None:
                error_obj = payload.get("error")
                if isinstance(error_obj, str) and error_obj.strip():
                    return False, _short_redacted_error(error_obj)
            return True, "Generation probe completed."
        except Exception as exc:
            return False, _short_redacted_error(str(exc)) or type(exc).__name__

    def probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        return self._probe_generation(model_available=model_available)

    @staticmethod
    def _error_from_response(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return f"HTTP {getattr(response, 'status_code', 'error')}"
        payload_object = _json_object_or_none(payload)
        if payload_object is not None:
            error_obj = payload_object.get("error")
            if isinstance(error_obj, str) and error_obj.strip():
                return _short_redacted_error(error_obj)
            error_mapping = _json_object_or_none(error_obj)
            if error_mapping is not None:
                message = error_mapping.get("message")
                if isinstance(message, str) and message.strip():
                    return _short_redacted_error(message)
        return f"HTTP {getattr(response, 'status_code', 'error')}"

    @staticmethod
    def _health_message(
        *,
        model_available: bool,
        generation_available: bool | None,
        generation_message: str | None,
    ) -> str:
        """
        Builds a human-readable health status message for the Ollama provider based on model listing and generation probe results.

        Parameters:
            model_available (bool): True if the configured model is present in the service's model list, False otherwise.
            generation_available (bool | None): Generation probe result: True if generation succeeded, False if it failed, or None if generation was not performed.
            generation_message (str | None): Optional detail about the generation probe outcome, included when the probe failed.

        Returns:
            str: A status string that states the service is reachable and describes model availability and, when applicable, generation probe success or failure (including the provided generation message).
        """
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


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(self, settings: Settings, *, model_name: str | None = None):
        """
        Initialize the provider with configuration, resolve the effective model name, normalize the base URL, and create an HTTP client.

        Parameters:
            settings (Settings): Configuration used by the provider (includes model_name, base_url, request timeout, temperature, and other runtime settings).
            model_name (str | None): Optional override for the configured model name; when omitted, `settings.model_name` is used.
        """
        self.settings = settings
        self.model_name = model_name or settings.model_name
        self.base_url = settings.base_url.rstrip("/")
        self.client = httpx.Client(timeout=settings.request_timeout_seconds)

    def _headers(self) -> dict[str, str] | None:
        """
        Provide an Authorization header when an OpenAI-compatible API key is configured.

        Returns:
            dict[str, str] | None: A headers dictionary containing `"Authorization": "Bearer <key>"` if the configured `openai_compatible_api_key` is present and non-empty after trimming, otherwise `None`.
        """
        api_key = (self.settings.openai_compatible_api_key or "").strip()
        if not api_key:
            return None
        return {"Authorization": f"Bearer {api_key}"}

    def headers(self) -> dict[str, str] | None:
        return self._headers()

    def generate(
        self,
        *,
        prompt: str,
        json_mode: bool = False,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a chat completion using the configured OpenAI-compatible endpoint and return the processed text plus the raw response payload.

        Parameters:
            prompt (str): The user prompt sent as the content of a single chat message.
            json_mode (bool): If true, requests the server to produce a JSON object response via `response_format`.
            json_schema (dict[str, Any] | None): Optional schema used to request provider-supported structured JSON output when `json_mode` is true.

        Returns:
            dict[str, Any]: A mapping with keys:
                - "response": the normalized string content extracted from the completion payload.
                - "raw": the full parsed JSON response payload.
        """
        body: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_output_tokens,
        }
        if json_mode:
            body["response_format"] = _openai_compatible_response_format(json_schema)
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=body,
        )
        response.raise_for_status()
        raw_payload = response.json()
        payload = _json_object_or_none(raw_payload)
        if payload is None:
            raise RuntimeError(
                f"OpenAI-compatible provider returned a non-object payload: {raw_payload!r}"
            )
        content = _openai_compatible_content(payload)
        return {"response": content, "raw": payload}

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        """
        Check OpenAI-compatible endpoint reachability and model availability.

        If `include_generation` is True, run a lightweight generation probe to verify the configured model can produce responses and capture a short diagnostic message.

        Parameters:
            include_generation (bool): If True, run a generation probe after verifying the model is listed.

        Returns:
            LLMHealthStatus: Health information with:
                service_reachable: `True` if the `/models` endpoint was reachable, `False` otherwise.
                model_available: `True` if the configured model name is listed, `False` otherwise.
                generation_available: `True` if the generation probe succeeded, `False` if it failed, or `None` if no probe was performed.
                generation_message: Diagnostic text from the generation probe on success or failure, or `None` if no probe was performed.
                message: Human-readable overall status summarizing reachability and probe results.
        """
        try:
            response = self.client.get(
                f"{self.base_url}/models", headers=self._headers()
            )
            if response.status_code >= 400:
                status_code = getattr(response, "status_code", "unknown")
                try:
                    response_text = _short_redacted_error(response.text)
                except Exception:
                    response_text = ""
                return LLMHealthStatus(
                    provider=self.provider_name,
                    base_url=self.settings.base_url,
                    model_name=self.model_name,
                    service_reachable=True,
                    model_available=False,
                    generation_available=False if include_generation else None,
                    generation_message=(
                        f"Endpoint reachable but rejected: HTTP {status_code} {response_text}".strip()
                        if include_generation
                        else None
                    ),
                    message=f"Endpoint reachable but rejected: HTTP {status_code} {response_text}".strip(),
                )
            response.raise_for_status()
            payload = _json_object(response.json())
            models = _openai_compatible_model_ids(payload)
            model_available = self.model_name in models
            generation_available: bool | None = None
            generation_message: str | None = None
            if include_generation:
                generation_available, generation_message = self._probe_generation(
                    model_available=model_available
                )
            message = self._health_message(
                model_available=model_available,
                generation_available=generation_available,
                generation_message=generation_message,
            )
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=True,
                model_available=model_available,
                generation_available=generation_available,
                generation_message=generation_message,
                message=message,
            )
        except Exception as exc:
            detail = _short_redacted_error(str(exc)) or type(exc).__name__
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                generation_available=False if include_generation else None,
                generation_message=(
                    f"Unable to reach OpenAI-compatible endpoint: {detail}"
                    if include_generation
                    else None
                ),
                message=f"Unable to reach OpenAI-compatible endpoint: {detail}",
            )

    def _probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        """
        Performs a minimal chat-completion request to verify that the configured model can produce responses.

        Parameters:
            model_available (bool): Whether the configured model is known to be listed by the service; if False the probe is skipped.

        Returns:
            tuple[bool, str]: `(True, "Generation probe completed.")` if the generation probe succeeded; otherwise `(False, <message>)` where `<message>` explains the failure (skipped because the model is not listed, an error message extracted from the service response, or a truncated exception text).
        """
        if not model_available:
            return (
                False,
                "Generation probe skipped because the configured model is not listed.",
            )
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
            )
            status_code = getattr(response, "status_code", 200)
            if status_code >= 400:
                return False, _openai_compatible_error_from_response(response)
            response.raise_for_status()
            payload = _json_object_or_none(response.json())
            if payload is not None:
                _openai_compatible_content(payload)
            return True, "Generation probe completed."
        except Exception as exc:
            return False, _short_redacted_error(str(exc)) or type(exc).__name__

    def probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        return self._probe_generation(model_available=model_available)

    @staticmethod
    def _health_message(
        *,
        model_available: bool,
        generation_available: bool | None,
        generation_message: str | None,
    ) -> str:
        """
        Builds a human-readable status message describing the OpenAI-compatible endpoint, the configured model's availability, and optional generation probe result.

        Parameters:
            model_available (bool): True if the configured model name appears in the service's model list.
            generation_available (bool | None): `True` if a generation probe succeeded, `False` if it failed, or `None` if no probe was performed.
            generation_message (str | None): Optional detail or error text from a failed generation probe.

        Returns:
            str: A single-line status message summarizing endpoint reachability, model availability, and generation probe outcome.
        """
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

    @staticmethod
    def health_message(
        *,
        model_available: bool,
        generation_available: bool | None,
        generation_message: str | None,
    ) -> str:
        return OpenAICompatibleProvider._health_message(
            model_available=model_available,
            generation_available=generation_available,
            generation_message=generation_message,
        )


def _openai_compatible_model_ids(payload: Mapping[str, object]) -> set[str]:
    """
    Extract model IDs from an OpenAI-compatible `/models` response payload.

    Parameters:
        payload (dict[str, Any]): Parsed JSON response expected to contain a top-level "data" list of model objects.

    Returns:
        set[str]: A set of model `id` strings found in `payload["data"]`. Returns an empty set if `data` is missing or not a list.
    """
    model_ids: set[str] = set()
    for item in _object_mapping_list(payload.get("data")):
        model_id = item.get("id")
        if isinstance(model_id, str):
            model_ids.add(model_id)
    return model_ids


def _openai_compatible_content(payload: Mapping[str, object]) -> str:
    """
    Extracts the textual response from an OpenAI-style chat-completions payload.

    Parameters:
        payload (dict): The raw JSON-decoded response from an OpenAI-compatible chat/completions API.

    Returns:
        str: The extracted text content, with surrounding whitespace removed.

    Raises:
        RuntimeError: If the payload contains no choices, the first choice is malformed, or no text content can be found.
    """
    choices = _object_list(payload.get("choices"))
    if not choices:
        raise RuntimeError("OpenAI-compatible provider returned no choices.")
    first = _json_object_or_none(choices[0])
    if first is None:
        raise RuntimeError("OpenAI-compatible provider returned malformed choices.")
    message = first.get("message")
    content = _openai_compatible_message_content(message)
    if content:
        return content
    text = first.get("text")
    if isinstance(text, str):
        return text.strip()
    raise RuntimeError("OpenAI-compatible provider returned no text content.")


def _openai_compatible_response_format(
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


def _openai_compatible_message_content(message: object) -> str:
    message_mapping = _json_object_or_none(message)
    if message_mapping is None:
        return ""
    content = message_mapping.get("content")
    if isinstance(content, str):
        return content.strip()
    return _openai_compatible_text_parts(_object_list(content))


def _openai_compatible_text_parts(content: list[object]) -> str:
    text_parts: list[str] = []
    for part in _object_mapping_list(content):
        text = part.get("text")
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts).strip()


def _openai_compatible_error_from_response(response: ErrorResponsePayload) -> str:
    """
    Extract a short, user-facing error message from an OpenAI-compatible HTTP response.

    Parses the response body as JSON and, if present, returns a trimmed error message from the `error` field:
    - If `error` is a non-empty string, returns that string (truncated to 240 characters).
    - If `error` is an object with a non-empty `message` string, returns that message (truncated to 240 characters).
    If the JSON cannot be parsed or no suitable error text is found, returns the fallback string `HTTP <status_code>` (or `HTTP error` if the status code is unavailable).

    Parameters:
        response (httpx.Response): The HTTP response to inspect.

    Returns:
        str: A concise error message extracted from the response or a fallback `HTTP <status_code>` string.
    """
    try:
        payload = response.json()
    except Exception:
        return f"HTTP {getattr(response, 'status_code', 'error')}"
    payload_object = _json_object_or_none(payload)
    if payload_object is not None:
        error_obj = payload_object.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            return _short_redacted_error(error_obj)
        error_mapping = _json_object_or_none(error_obj)
        if error_mapping is not None:
            message = error_mapping.get("message")
            if isinstance(message, str) and message.strip():
                return _short_redacted_error(message)
    return f"HTTP {getattr(response, 'status_code', 'error')}"


openai_compatible_model_ids = _openai_compatible_model_ids
openai_compatible_content = _openai_compatible_content
openai_compatible_error_from_response = _openai_compatible_error_from_response


def _short_redacted_error(value: str) -> str:
    return redact_sensitive_text(value).strip()[:240]


def build_provider(settings: Settings, *, model_name: str | None = None) -> LLMProvider:
    """
    Selects and constructs an LLM provider implementation based on the configured provider in `settings`.

    Parameters:
        settings (Settings): Configuration that includes `llm_provider` and provider-specific settings.
        model_name (str | None): Optional model name to override `settings.model_name`.

    Returns:
        An LLMProvider instance corresponding to `settings.llm_provider` (for example, an OllamaProvider or OpenAICompatibleProvider).

    Raises:
        RuntimeError: If `settings.llm_provider` is not a supported provider.
    """
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings, model_name=model_name)
    if settings.llm_provider == "openai-compatible":
        return OpenAICompatibleProvider(settings, model_name=model_name)
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
