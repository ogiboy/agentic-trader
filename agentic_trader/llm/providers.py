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


def build_provider(settings: Settings, *, model_name: str | None = None) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings, model_name=model_name)
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
