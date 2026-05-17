from __future__ import annotations

from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.llm.providers import (
    OllamaProvider,
    OpenAICompatibleProvider,
    _openai_compatible_content,
    _openai_compatible_error_from_response,
    _openai_compatible_model_ids,
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


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider additional coverage
# ---------------------------------------------------------------------------


def _compat_provider(
    settings: Settings | None = None,
) -> tuple[OpenAICompatibleProvider, FakeClient]:
    provider = OpenAICompatibleProvider(
        settings
        or Settings(
            llm_provider="openai-compatible",
            base_url="http://127.0.0.1:8080/v1",
            model_name="test-model",
        )
    )
    client = FakeClient()
    object.__setattr__(provider, "client", client)
    return provider, client


def test_openai_compatible_headers_returns_none_without_api_key() -> None:
    provider, _ = _compat_provider(
        Settings(llm_provider="openai-compatible", openai_compatible_api_key=None)
    )

    assert provider._headers() is None


def test_openai_compatible_headers_returns_bearer_with_api_key() -> None:
    provider, _ = _compat_provider(
        Settings(
            llm_provider="openai-compatible",
            openai_compatible_api_key="my-secret-token",
        )
    )

    headers = provider._headers()
    assert headers is not None
    assert headers["Authorization"] == "Bearer my-secret-token"


def test_openai_compatible_health_check_without_include_generation() -> None:
    provider, client = _compat_provider()
    client.get_response = FakeResponse({"data": [{"id": "test-model"}]})

    health = provider.health_check()

    assert health.service_reachable is True
    assert health.model_available is True
    assert health.generation_available is None
    assert "available" in health.message


def test_openai_compatible_health_check_when_unreachable() -> None:
    provider, client = _compat_provider()
    client.get_response = FakeResponse(
        None, raise_error=ConnectionError("refused")
    )

    health = provider.health_check()

    assert health.service_reachable is False
    assert health.model_available is False
    assert "Unable to reach" in health.message


def test_openai_compatible_health_check_unreachable_with_generation_flag() -> None:
    provider, client = _compat_provider()
    client.get_response = FakeResponse(
        None, raise_error=ConnectionError("refused")
    )

    health = provider.health_check(include_generation=True)

    assert health.service_reachable is False
    assert health.generation_available is False
    assert health.generation_message is not None
    assert "Unable to reach" in health.generation_message


def test_openai_compatible_generate_raises_on_http_error() -> None:
    provider, client = _compat_provider()
    client.post_responses = [
        FakeResponse(
            {"error": "internal error"},
            raise_error=RuntimeError("HTTP 500"),
        )
    ]

    with pytest.raises(RuntimeError):
        provider.generate(prompt="hello")


def test_openai_compatible_generate_raises_on_non_object_payload() -> None:
    provider, client = _compat_provider()
    client.post_responses = [FakeResponse(["not", "a", "dict"])]

    with pytest.raises(RuntimeError, match="non-object payload"):
        provider.generate(prompt="hello")


def test_openai_compatible_probe_generation_returns_false_for_http_error() -> None:
    provider, client = _compat_provider()
    client.post_responses = [
        FakeResponse({"error": "model overloaded"}, status_code=429)
    ]

    ok, message = provider._probe_generation(model_available=True)

    assert ok is False
    assert "model overloaded" in message


def test_openai_compatible_probe_generation_returns_false_when_exception() -> None:
    provider, client = _compat_provider()
    client.post_responses = [
        FakeResponse(None, raise_error=RuntimeError("network timeout"))
    ]

    ok, message = provider._probe_generation(model_available=True)

    assert ok is False
    assert "network timeout" in message


def test_openai_compatible_health_message_generation_failed() -> None:
    message = OpenAICompatibleProvider._health_message(
        model_available=True,
        generation_available=False,
        generation_message="model load failed",
    )

    assert "generation probe failed" in message
    assert "model load failed" in message


def test_openai_compatible_health_message_model_not_listed() -> None:
    message = OpenAICompatibleProvider._health_message(
        model_available=False,
        generation_available=None,
        generation_message=None,
    )

    assert "not listed" in message


def test_openai_compatible_health_message_available_no_generation_checked() -> None:
    message = OpenAICompatibleProvider._health_message(
        model_available=True,
        generation_available=None,
        generation_message=None,
    )

    assert "available" in message
    assert "can generate" not in message


# ---------------------------------------------------------------------------
# _openai_compatible_model_ids helper
# ---------------------------------------------------------------------------


def test_openai_compatible_model_ids_with_valid_data() -> None:
    payload = {"data": [{"id": "gpt-4"}, {"id": "gpt-3.5"}]}
    assert _openai_compatible_model_ids(payload) == {"gpt-4", "gpt-3.5"}


def test_openai_compatible_model_ids_with_missing_data_key() -> None:
    assert _openai_compatible_model_ids({}) == set()


def test_openai_compatible_model_ids_with_non_list_data() -> None:
    assert _openai_compatible_model_ids({"data": "not-a-list"}) == set()


def test_openai_compatible_model_ids_skips_non_dict_items() -> None:
    payload = {"data": [{"id": "valid-model"}, "string-item", 42, None]}
    assert _openai_compatible_model_ids(payload) == {"valid-model"}


def test_openai_compatible_model_ids_skips_items_without_id() -> None:
    payload = {"data": [{"name": "no-id-field"}, {"id": "has-id"}]}
    assert _openai_compatible_model_ids(payload) == {"has-id"}


def test_openai_compatible_model_ids_skips_non_string_id() -> None:
    payload = {"data": [{"id": 123}, {"id": "string-id"}]}
    assert _openai_compatible_model_ids(payload) == {"string-id"}


# ---------------------------------------------------------------------------
# _openai_compatible_content helper
# ---------------------------------------------------------------------------


def test_openai_compatible_content_with_string_message_content() -> None:
    payload = {"choices": [{"message": {"content": "  hello  "}}]}
    assert _openai_compatible_content(payload) == "hello"


def test_openai_compatible_content_with_list_content_format() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "part one "},
                        {"type": "text", "text": "part two"},
                        {"type": "image_url"},  # no text key, skipped
                    ]
                }
            }
        ]
    }
    assert _openai_compatible_content(payload) == "part one part two"


def test_openai_compatible_content_with_text_key_fallback() -> None:
    payload = {"choices": [{"text": " legacy text "}]}
    assert _openai_compatible_content(payload) == "legacy text"


def test_openai_compatible_content_raises_on_empty_choices() -> None:
    with pytest.raises(RuntimeError, match="no choices"):
        _openai_compatible_content({"choices": []})


def test_openai_compatible_content_raises_on_missing_choices() -> None:
    with pytest.raises(RuntimeError, match="no choices"):
        _openai_compatible_content({})


def test_openai_compatible_content_raises_on_non_dict_first_choice() -> None:
    with pytest.raises(RuntimeError, match="malformed choices"):
        _openai_compatible_content({"choices": ["string-not-dict"]})


def test_openai_compatible_content_raises_when_no_text_content() -> None:
    with pytest.raises(RuntimeError, match="no text content"):
        _openai_compatible_content({"choices": [{"message": {"role": "assistant"}}]})


def test_openai_compatible_content_raises_when_no_message_or_text() -> None:
    with pytest.raises(RuntimeError, match="no text content"):
        _openai_compatible_content({"choices": [{"finish_reason": "stop"}]})


# ---------------------------------------------------------------------------
# _openai_compatible_error_from_response helper
# ---------------------------------------------------------------------------


class _FakeHttpxResponse:
    """Minimal stand-in for httpx.Response in error-parsing tests."""

    def __init__(
        self,
        payload: object,
        *,
        status_code: int = 500,
        json_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self._json_error = json_error

    def json(self) -> object:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


def test_openai_compatible_error_from_response_string_error() -> None:
    response = _FakeHttpxResponse({"error": "quota exceeded"}, status_code=429)
    result = _openai_compatible_error_from_response(response)  # type: ignore[arg-type]
    assert result == "quota exceeded"


def test_openai_compatible_error_from_response_dict_error_with_message() -> None:
    response = _FakeHttpxResponse(
        {"error": {"message": "model not found", "code": "not_found"}},
        status_code=404,
    )
    result = _openai_compatible_error_from_response(response)  # type: ignore[arg-type]
    assert result == "model not found"


def test_openai_compatible_error_from_response_fallback_on_no_error_key() -> None:
    response = _FakeHttpxResponse({"ok": False}, status_code=503)
    result = _openai_compatible_error_from_response(response)  # type: ignore[arg-type]
    assert result == "HTTP 503"


def test_openai_compatible_error_from_response_fallback_when_json_fails() -> None:
    response = _FakeHttpxResponse(
        None,
        status_code=500,
        json_error=ValueError("invalid json"),
    )
    result = _openai_compatible_error_from_response(response)  # type: ignore[arg-type]
    assert result == "HTTP 500"


def test_openai_compatible_error_from_response_truncates_long_message() -> None:
    long_message = "x" * 300
    response = _FakeHttpxResponse({"error": long_message}, status_code=400)
    result = _openai_compatible_error_from_response(response)  # type: ignore[arg-type]
    assert len(result) <= 240
