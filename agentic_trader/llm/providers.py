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

    def generate(self, *, prompt: str, json_mode: bool = False) -> dict[str, Any]: ...

    def health_check(self) -> LLMHealthStatus: ...


class OllamaProvider:
    provider_name = "ollama"

    def __init__(self, settings: Settings, *, model_name: str | None = None):
        self.settings = settings
        self.model_name = model_name or settings.model_name
        self.base_url = settings.base_url.removesuffix("/v1").rstrip("/")
        self.client = httpx.Client(timeout=settings.request_timeout_seconds)

    def generate(self, *, prompt: str, json_mode: bool = False) -> dict[str, Any]:
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
            body["format"] = "json"
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json=body,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Ollama returned a non-object payload: {payload!r}")
        return cast(dict[str, Any], payload)

    def health_check(self) -> LLMHealthStatus:
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
            message = (
                "Ollama is reachable and the configured model is available."
                if model_available
                else "Ollama is reachable, but the configured model is not listed."
            )
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=True,
                model_available=model_available,
                message=message,
            )
        except Exception as exc:
            return LLMHealthStatus(
                provider=self.provider_name,
                base_url=self.settings.base_url,
                model_name=self.model_name,
                service_reachable=False,
                model_available=False,
                message=f"Unable to reach Ollama: {exc}",
            )


def build_provider(settings: Settings, *, model_name: str | None = None) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings, model_name=model_name)
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
