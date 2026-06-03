from __future__ import annotations

from typing import Any, Protocol, cast

import httpx

from agentic_trader.config import Settings
from agentic_trader.llm.ollama_provider_health import (
    ollama_error_from_response as _ollama_error_from_response,
)
from agentic_trader.llm.ollama_provider_health import (
    ollama_generation_probe as _ollama_generation_probe,
)
from agentic_trader.llm.ollama_provider_health import (
    ollama_health_message as _ollama_health_message,
)
from agentic_trader.llm.ollama_provider_health import (
    ollama_model_names as _ollama_model_names,
)
from agentic_trader.llm.openai_compat import (
    openai_compatible_content as _openai_compatible_content,
)
from agentic_trader.llm.openai_compat import (
    openai_compatible_error_from_response as _openai_compatible_error_from_response,
)
from agentic_trader.llm.openai_compat import (
    openai_compatible_model_ids as _openai_compatible_model_ids,
)
from agentic_trader.llm.openai_compat import (
    openai_compatible_response_format as _openai_compatible_response_format,
)
from agentic_trader.llm.openai_compat import (
    short_redacted_error as _short_redacted_error,
)
from agentic_trader.llm.openai_provider_health import (
    endpoint_rejected_health as _endpoint_rejected_health,
)
from agentic_trader.llm.openai_provider_health import (
    openai_compatible_generation_probe as _openai_compatible_generation_probe,
)
from agentic_trader.llm.openai_provider_health import (
    openai_compatible_health_message as _openai_compatible_health_message,
)
from agentic_trader.llm.openai_provider_health import (
    reachable_health as _reachable_health,
)
from agentic_trader.llm.openai_provider_health import (
    unreachable_health as _unreachable_health,
)
from agentic_trader.llm.provider_payloads import json_object as _json_object
from agentic_trader.llm.provider_payloads import (
    json_object_or_none as _json_object_or_none,
)
from agentic_trader.schemas import LLMHealthStatus


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
            model_available = self.model_name in _ollama_model_names(payload)
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
        return _ollama_generation_probe(
            client=self.client,
            base_url=self.base_url,
            model_name=self.model_name,
            model_available=model_available,
        )

    def probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        return self._probe_generation(model_available=model_available)

    @staticmethod
    def _error_from_response(response: httpx.Response) -> str:
        return _ollama_error_from_response(response)

    @staticmethod
    def _health_message(
        *,
        model_available: bool,
        generation_available: bool | None,
        generation_message: str | None,
    ) -> str:
        return _ollama_health_message(
            model_available=model_available,
            generation_available=generation_available,
            generation_message=generation_message,
        )


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

    def _endpoint_rejected_health(
        self,
        *,
        status_code: object,
        response_text: str,
        include_generation: bool,
    ) -> LLMHealthStatus:
        return _endpoint_rejected_health(
            provider_name=self.provider_name,
            base_url=self.settings.base_url,
            model_name=self.model_name,
            status_code=status_code,
            response_text=response_text,
            include_generation=include_generation,
        )

    def _reachable_health(
        self,
        *,
        model_available: bool,
        include_generation: bool,
    ) -> LLMHealthStatus:
        generation_available: bool | None = None
        generation_message: str | None = None
        if include_generation:
            generation_available, generation_message = self._probe_generation(
                model_available=model_available
            )
        return _reachable_health(
            provider_name=self.provider_name,
            base_url=self.settings.base_url,
            model_name=self.model_name,
            generation_available=generation_available,
            generation_message=generation_message,
            model_available=model_available,
        )

    def _unreachable_health(
        self,
        *,
        detail: str,
        include_generation: bool,
    ) -> LLMHealthStatus:
        return _unreachable_health(
            provider_name=self.provider_name,
            base_url=self.settings.base_url,
            model_name=self.model_name,
            detail=detail,
            include_generation=include_generation,
        )

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
                return self._endpoint_rejected_health(
                    status_code=status_code,
                    response_text=response_text,
                    include_generation=include_generation,
                )
            response.raise_for_status()
            payload = _json_object(response.json())
            models = _openai_compatible_model_ids(payload)
            model_available = self.model_name in models
            return self._reachable_health(
                model_available=model_available,
                include_generation=include_generation,
            )
        except Exception as exc:
            detail = _short_redacted_error(str(exc)) or type(exc).__name__
            return self._unreachable_health(
                detail=detail,
                include_generation=include_generation,
            )

    def _probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        return _openai_compatible_generation_probe(
            client=self.client,
            base_url=self.base_url,
            headers=self._headers(),
            model_name=self.model_name,
            model_available=model_available,
        )

    def probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        return self._probe_generation(model_available=model_available)

    @staticmethod
    def _health_message(
        *,
        model_available: bool,
        generation_available: bool | None,
        generation_message: str | None,
    ) -> str:
        return _openai_compatible_health_message(
            model_available=model_available,
            generation_available=generation_available,
            generation_message=generation_message,
        )

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


openai_compatible_model_ids = _openai_compatible_model_ids
openai_compatible_content = _openai_compatible_content
openai_compatible_error_from_response = _openai_compatible_error_from_response


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
