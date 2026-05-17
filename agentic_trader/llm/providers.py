from __future__ import annotations

from typing import Any, Protocol, cast

import httpx

from agentic_trader.config import Settings
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
    ) -> dict[str, Any]: ...

    def health_check(
        self, *, include_generation: bool = False
    ) -> LLMHealthStatus: ...


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
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Ollama returned a non-object payload: {payload!r}")
        return cast(dict[str, Any], payload)

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            models_obj: Any = payload.get("models", [])
            models: list[dict[str, Any]] = []
            if isinstance(models_obj, list):
                for raw_item in cast(list[Any], models_obj):
                    if isinstance(raw_item, dict):
                        models.append(cast(dict[str, Any], raw_item))
            available: set[str] = set()
            for item in models:
                name: Any = item.get("name")
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
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                generation_available=False if include_generation else None,
                generation_message=f"Unable to reach Ollama: {exc}"
                if include_generation
                else None,
                message=f"Unable to reach Ollama: {exc}",
            )

    def _probe_generation(self, *, model_available: bool) -> tuple[bool, str]:
        if not model_available:
            return False, "Generation probe skipped because the configured model is not listed."
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
            payload = response.json()
            if isinstance(payload, dict):
                error_obj = payload.get("error")
                if isinstance(error_obj, str) and error_obj.strip():
                    return False, error_obj.strip()[:240]
            return True, "Generation probe completed."
        except Exception as exc:
            return False, str(exc).strip()[:240] or type(exc).__name__

    @staticmethod
    def _error_from_response(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return f"HTTP {getattr(response, 'status_code', 'error')}"
        if isinstance(payload, dict):
            error_obj = payload.get("error")
            if isinstance(error_obj, str) and error_obj.strip():
                return error_obj.strip()[:240]
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()[:240]
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
        Initialize the provider with configuration and prepare an HTTP client.
        
        Parameters:
        	settings (Settings): Configuration values used by the provider (includes model_name, base_url, request timeout, temperature, and other runtime settings).
        	model_name (str | None): Optional override for the configured model name; if omitted, the value from `settings.model_name` is used.
        
        Side effects:
        	Normalizes `settings.base_url` by stripping trailing slashes and creates an `httpx.Client` stored on the instance as `self.client`.
        """
        self.settings = settings
        self.model_name = model_name or settings.model_name
        self.base_url = settings.base_url.rstrip("/")
        self.client = httpx.Client(timeout=settings.request_timeout_seconds)

    def _headers(self) -> dict[str, str] | None:
        """
        Return authorization headers for OpenAI-compatible requests when an API key is configured.
        
        Returns:
            dict[str, str] | None: A headers dictionary with "Authorization": "Bearer <key>" if Settings.openai_compatible_api_key is set and non-empty after trimming, otherwise `None`.
        """
        api_key = (self.settings.openai_compatible_api_key or "").strip()
        if not api_key:
            return None
        return {"Authorization": f"Bearer {api_key}"}

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
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"OpenAI-compatible provider returned a non-object payload: {payload!r}"
            )
        content = _openai_compatible_content(payload)
        return {"response": content, "raw": payload}

    def health_check(self, *, include_generation: bool = False) -> LLMHealthStatus:
        """
        Check the OpenAI-compatible endpoint and determine whether the configured model and (optionally) generation are available.

        Performs an HTTP GET to the provider's /models endpoint to verify service reachability and whether the configured model is listed. If include_generation is True, performs a small generation probe to determine whether model inference is operational and captures a short diagnostic message.

        Parameters:
            include_generation (bool): If True, run a lightweight generation probe after verifying the model is listed to determine runtime generation availability.

        Returns:
            LLMHealthStatus: Health information including:
                - service_reachable: `True` if the /models endpoint was reachable and returned a 2xx response; `False` otherwise.
                - model_available: `True` if the configured model name is present in the returned model list; `False` otherwise.
                - generation_available: `True` if a generation probe succeeded, `False` if it failed, or `None` if no probe was performed.
                - generation_message: Short diagnostic text from the generation probe on success or failure, or `None` if no probe was performed.
                - message: Human-readable overall status summarizing reachability and generation probe results.
        """
        try:
            response = self.client.get(f"{self.base_url}/models", headers=self._headers())
            if response.status_code >= 400:
                status_code = getattr(response, "status_code", "unknown")
                try:
                    response_text = response.text[:240]
                except Exception:
                    response_text = ""
                return LLMHealthStatus(
                    provider=self.provider_name,
                    base_url=self.settings.base_url,
                    model_name=self.model_name,
                    service_reachable=True,
                    model_available=False,
                    generation_available=False if include_generation else None,
                    generation_message=f"Endpoint reachable but rejected: HTTP {status_code} {response_text}".strip()
                    if include_generation
                    else None,
                    message=f"Endpoint reachable but rejected: HTTP {status_code} {response_text}".strip(),
                )
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
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
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                generation_available=False if include_generation else None,
                generation_message=f"Unable to reach OpenAI-compatible endpoint: {exc}"
                if include_generation
                else None,
                message=f"Unable to reach OpenAI-compatible endpoint: {exc}",
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
            return False, "Generation probe skipped because the configured model is not listed."
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
            payload = response.json()
            if isinstance(payload, dict):
                _openai_compatible_content(payload)
            return True, "Generation probe completed."
        except Exception as exc:
            return False, str(exc).strip()[:240] or type(exc).__name__

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
        return (
            "OpenAI-compatible endpoint is reachable and the configured model is available."
        )


def _openai_compatible_model_ids(payload: dict[str, Any]) -> set[str]:
    """
    Extract model IDs from an OpenAI-compatible `/models` response payload.
    
    Parameters:
        payload (dict[str, Any]): Parsed JSON response expected to contain a top-level "data" list of model objects.
    
    Returns:
        set[str]: A set of model `id` strings found in `payload["data"]`. Returns an empty set if `data` is missing or not a list.
    """
    data = payload.get("data")
    if not isinstance(data, list):
        return set()
    model_ids: set[str] = set()
    for item in data:
        if isinstance(item, dict):
            model_id = item.get("id")
            if isinstance(model_id, str):
                model_ids.add(model_id)
    return model_ids


def _openai_compatible_content(payload: dict[str, Any]) -> str:
    """
    Extracts the textual response from an OpenAI-style chat-completions payload.
    
    Parameters:
        payload (dict): The raw JSON-decoded response from an OpenAI-compatible chat/completions API.
    
    Returns:
        str: The extracted text content, with surrounding whitespace removed.
    
    Raises:
        RuntimeError: If the payload contains no choices, the first choice is malformed, or no text content can be found.
    """
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI-compatible provider returned no choices.")
    first = choices[0]
    if not isinstance(first, dict):
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
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return _openai_compatible_text_parts(content)
    return ""


def _openai_compatible_text_parts(content: list[object]) -> str:
    text_parts = [
        part["text"]
        for part in content
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    return "".join(text_parts).strip()


def _openai_compatible_error_from_response(response: httpx.Response) -> str:
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
    if isinstance(payload, dict):
        error_obj = payload.get("error")
        if isinstance(error_obj, str) and error_obj.strip():
            return error_obj.strip()[:240]
        if isinstance(error_obj, dict):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:240]
    return f"HTTP {getattr(response, 'status_code', 'error')}"


def build_provider(settings: Settings, *, model_name: str | None = None) -> LLMProvider:
    """
    Builds an LLM provider instance based on the configured provider name in settings.
    
    Parameters:
        settings (Settings): Configuration containing `llm_provider` and other provider settings.
        model_name (str | None): Optional model name to override the one from settings.
    
    Returns:
        LLMProvider: An instance of the selected provider (e.g., OllamaProvider or OpenAICompatibleProvider).
    
    """
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings, model_name=model_name)
    if settings.llm_provider == "openai-compatible":
        return OpenAICompatibleProvider(settings, model_name=model_name)
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
