from __future__ import annotations

from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.llm.providers import (
    OllamaProvider,
    OpenAICompatibleProvider,
    build_provider,
)


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
        """
        Initialize a FakeClient used by tests to simulate HTTP interactions.
        
        Creates:
        - `posts`: an empty list that records copies of JSON payloads sent to `post`.
        - `get_response`: default `FakeResponse` returned by `get` calls, initialized with `{"models": []}`.
        - `post_responses`: an empty list acting as a FIFO queue of `FakeResponse` objects to be returned by `post`.
        """
        self.posts: list[dict[str, Any]] = []
        self.get_response: FakeResponse = FakeResponse({"models": []})
        self.post_responses: list[FakeResponse] = []

    def get(self, _url: str, **_kwargs: Any) -> FakeResponse:
        """
        Return the client's configured FakeResponse for any GET request.
        
        Parameters:
        	_url (str): The requested URL (ignored by this fake client).
        	_kwargs (Any): Additional request options (ignored by this fake client).
        
        Returns:
        	FakeResponse: The preconfigured response object stored on the client.
        """
        return self.get_response

    def post(self, _url: str, *, json: dict[str, Any], **_kwargs: Any) -> FakeResponse:
        """
        Record the posted JSON payload and return the next queued fake response or a default success response.
        
        Parameters:
            _url (str): Ignored request URL.
            json (dict[str, Any]): JSON body to record; a shallow copy is appended to the client's recorded posts.
            _kwargs: Ignored keyword arguments.
        
        Returns:
            FakeResponse: The next response from the client's response queue if available; otherwise a default FakeResponse with payload {"response": "OK"}.
        """
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


def test_openai_compatible_provider_generates_and_checks_health() -> None:
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai-compatible",
            base_url="http://127.0.0.1:8080/v1",
            model_name="local-qwen",
            openai_compatible_api_key="local-token",
        )
    )
    client = FakeClient()
    client.get_response = FakeResponse({"data": [{"id": "local-qwen"}]})
    client.post_responses = [
        FakeResponse({"choices": [{"message": {"content": "OK"}}]}),
        FakeResponse({"choices": [{"message": {"content": "{\"ok\": true}"}}]}),
    ]
    object.__setattr__(provider, "client", client)

    health = provider.health_check(include_generation=True)
    payload = provider.generate(prompt="Return JSON.", json_mode=True)

    assert health.provider == "openai-compatible"
    assert health.service_reachable is True
    assert health.model_available is True
    assert health.generation_available is True
    assert payload["response"] == '{"ok": true}'
    assert client.posts[1]["response_format"] == {"type": "json_object"}


def test_openai_compatible_provider_uses_schema_and_content_parts() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="local-qwen")
    )
    client = FakeClient()
    client.post_responses = [
        FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "{\"ok\":"},
                                {"type": "text", "text": " true}"},
                                {"type": "ignored", "value": "no text"},
                            ]
                        }
                    }
                ]
            }
        )
    ]
    object.__setattr__(provider, "client", client)

    payload = provider.generate(
        prompt="Return JSON.",
        json_mode=True,
        json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert payload["response"] == '{"ok": true}'
    assert client.posts[0]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "agentic_trader_response",
            "schema": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
            },
        },
    }


def test_openai_compatible_provider_reports_missing_model() -> None:
    """
    Verifies health_check reports a missing model when the configured model ID is not present in the OpenAI-compatible service response.
    
    Asserts that the service is reachable, that the configured model is reported as unavailable, that generation is skipped, and that the health message indicates the model is not listed.
    """
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="missing-model")
    )
    client = FakeClient()
    client.get_response = FakeResponse({"data": [{"id": "other-model"}]})
    object.__setattr__(provider, "client", client)

    health = provider.health_check(include_generation=True)

    assert health.service_reachable is True
    assert health.model_available is False
    assert health.generation_available is False
    assert "not listed" in health.message


def test_openai_compatible_provider_surfaces_errors_without_network() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="local-qwen")
    )
    client = FakeClient()
    client.get_response = FakeResponse(
        {"error": {"message": "secret-free failure"}},
        raise_error=RuntimeError("models unavailable"),
    )
    client.post_responses = [
        FakeResponse({"error": {"message": "model load failed"}}, status_code=500),
        FakeResponse({"choices": []}),
    ]
    object.__setattr__(provider, "client", client)

    health = provider.health_check(include_generation=True)
    http_ok, http_message = provider._probe_generation(model_available=True)
    malformed_ok, malformed_message = provider._probe_generation(
        model_available=True
    )

    assert health.service_reachable is False
    assert health.generation_available is False
    assert "models unavailable" in health.message
    assert http_ok is False
    assert http_message == "model load failed"
    assert malformed_ok is False
    assert "no choices" in malformed_message


def test_build_provider_accepts_openai_compatible_adapter() -> None:
    provider = build_provider(Settings(llm_provider="openai-compatible"))

    assert provider.provider_name == "openai-compatible"


def test_build_provider_rejects_unknown_provider() -> None:
    settings = Settings()
    object.__setattr__(settings, "llm_provider", "anthropic")

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        build_provider(settings)
