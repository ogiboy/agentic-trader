from __future__ import annotations

from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.llm.providers import OllamaProvider, build_provider


class FakeResponse:
    def __init__(
        self,
        payload: object,
        *,
        status_code: int = 200,
        raise_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self._raise_error = raise_error

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self._raise_error is not None:
            raise self._raise_error


class FakeClient:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.get_response: FakeResponse = FakeResponse({"models": []})
        self.post_responses: list[FakeResponse] = []

    def get(self, _url: str) -> FakeResponse:
        return self.get_response

    def post(self, _url: str, *, json: dict[str, Any]) -> FakeResponse:
        self.posts.append(dict(json))
        if self.post_responses:
            return self.post_responses.pop(0)
        return FakeResponse({"response": "OK"})


def _provider(settings: Settings | None = None) -> tuple[OllamaProvider, FakeClient]:
    provider = OllamaProvider(settings or Settings())
    client = FakeClient()
    object.__setattr__(provider, "client", client)
    return provider, client


def test_generate_retries_schema_format_as_json_on_ollama_400() -> None:
    provider, client = _provider()
    client.post_responses = [
        FakeResponse({"error": "schema unsupported"}, status_code=400),
        FakeResponse({"response": "{\"ok\": true}"}),
    ]

    payload = provider.generate(
        prompt="Return JSON.",
        json_mode=True,
        json_schema={"type": "object"},
    )

    assert payload["response"] == "{\"ok\": true}"
    assert client.posts[0]["format"] == {"type": "object"}
    assert client.posts[1]["format"] == "json"


def test_generate_rejects_non_object_ollama_payload() -> None:
    provider, client = _provider()
    client.post_responses = [FakeResponse(["not", "an", "object"])]

    with pytest.raises(RuntimeError, match="non-object payload"):
        provider.generate(prompt="hello")


def test_health_check_reports_generation_states_without_network() -> None:
    provider, client = _provider(Settings(model_name="qwen3:8b"))
    client.get_response = FakeResponse(
        {"models": [{"name": "qwen3:8b"}, {"name": 123}, "ignored"]}
    )
    client.post_responses = [FakeResponse({"response": "OK"})]

    healthy = provider.health_check(include_generation=True)

    assert healthy.service_reachable is True
    assert healthy.model_available is True
    assert healthy.generation_available is True
    assert healthy.message == "Ollama is reachable and the configured model can generate."

    provider_missing, client_missing = _provider(Settings(model_name="missing-model"))
    client_missing.get_response = FakeResponse({"models": [{"name": "qwen3:8b"}]})

    missing = provider_missing.health_check(include_generation=True)

    assert missing.model_available is False
    assert missing.generation_available is False
    assert missing.generation_message == (
        "Generation probe skipped because the configured model is not listed."
    )


def test_probe_generation_surfaces_http_and_payload_errors() -> None:
    provider, client = _provider()
    client.post_responses = [
        FakeResponse({"error": {"message": "model load failed"}}, status_code=500),
        FakeResponse({"error": "runtime refused"}),
    ]

    first_ok, first_message = provider._probe_generation(model_available=True)
    second_ok, second_message = provider._probe_generation(model_available=True)

    assert first_ok is False
    assert first_message == "model load failed"
    assert second_ok is False
    assert second_message == "runtime refused"


def test_build_provider_rejects_unknown_provider() -> None:
    settings = Settings()
    object.__setattr__(settings, "llm_provider", "anthropic")

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        build_provider(settings)
