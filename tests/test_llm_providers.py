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
        self.posts: list[dict[str, Any]] = []
        self.get_response: FakeResponse = FakeResponse({"models": []})
        self.post_responses: list[FakeResponse] = []

    def get(self, _url: str, **_kwargs: Any) -> FakeResponse:
        return self.get_response

    def post(self, _url: str, *, json: dict[str, Any], **_kwargs: Any) -> FakeResponse:
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


def test_openai_compatible_provider_reports_missing_model() -> None:
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


def test_build_provider_accepts_openai_compatible_adapter() -> None:
    provider = build_provider(Settings(llm_provider="openai-compatible"))

    assert provider.provider_name == "openai-compatible"


def test_build_provider_rejects_unknown_provider() -> None:
    settings = Settings()
    object.__setattr__(settings, "llm_provider", "anthropic")

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        build_provider(settings)


def test_openai_compatible_headers_omitted_when_no_api_key() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", openai_compatible_api_key=None)
    )

    assert provider._headers() is None


def test_openai_compatible_headers_includes_bearer_when_api_key_set() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai-compatible",
            openai_compatible_api_key="my-secret-token",
        )
    )

    headers = provider._headers()
    assert headers is not None
    assert headers["Authorization"] == "Bearer my-secret-token"


def test_openai_compatible_content_extracts_from_list_content_parts() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "Hello "},
                        {"type": "text", "text": "world"},
                        {"type": "image_url"},
                    ]
                }
            }
        ]
    }

    assert _openai_compatible_content(payload) == "Hello world"


def test_openai_compatible_content_extracts_from_text_fallback() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    payload = {"choices": [{"text": "  response text  "}]}

    assert _openai_compatible_content(payload) == "response text"


def test_openai_compatible_content_raises_on_empty_choices() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    with pytest.raises(RuntimeError, match="no choices"):
        _openai_compatible_content({"choices": []})


def test_openai_compatible_content_raises_on_missing_choices_key() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    with pytest.raises(RuntimeError, match="no choices"):
        _openai_compatible_content({})


def test_openai_compatible_content_raises_on_malformed_first_choice() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    with pytest.raises(RuntimeError, match="malformed choices"):
        _openai_compatible_content({"choices": ["not-a-dict"]})


def test_openai_compatible_content_raises_when_no_text_content() -> None:
    from agentic_trader.llm.providers import _openai_compatible_content

    with pytest.raises(RuntimeError, match="no text content"):
        _openai_compatible_content({"choices": [{"message": {"content": 42}}]})


def test_openai_compatible_model_ids_returns_empty_set_for_non_list_data() -> None:
    from agentic_trader.llm.providers import _openai_compatible_model_ids

    assert _openai_compatible_model_ids({"data": "not-a-list"}) == set()
    assert _openai_compatible_model_ids({}) == set()
    assert _openai_compatible_model_ids({"data": [{"no_id": True}]}) == set()


def test_openai_compatible_model_ids_skips_non_string_ids() -> None:
    from agentic_trader.llm.providers import _openai_compatible_model_ids

    payload = {"data": [{"id": "valid-model"}, {"id": 123}, "not-a-dict", {"id": None}]}

    assert _openai_compatible_model_ids(payload) == {"valid-model"}


def test_openai_compatible_error_from_response_parses_string_error() -> None:
    from agentic_trader.llm.providers import _openai_compatible_error_from_response

    response = FakeResponse({"error": "plain error message"}, status_code=400)

    assert _openai_compatible_error_from_response(response) == "plain error message"  # type: ignore[arg-type]


def test_openai_compatible_error_from_response_parses_dict_error_message() -> None:
    from agentic_trader.llm.providers import _openai_compatible_error_from_response

    response = FakeResponse(
        {"error": {"message": "nested error detail", "code": "model_not_found"}},
        status_code=404,
    )

    assert _openai_compatible_error_from_response(response) == "nested error detail"  # type: ignore[arg-type]


def test_openai_compatible_error_from_response_falls_back_to_http_status() -> None:
    from agentic_trader.llm.providers import _openai_compatible_error_from_response

    response = FakeResponse(["not", "a", "dict"], status_code=503)

    assert _openai_compatible_error_from_response(response) == "HTTP 503"  # type: ignore[arg-type]


def test_openai_compatible_error_from_response_handles_json_parse_failure() -> None:
    from agentic_trader.llm.providers import _openai_compatible_error_from_response

    class BadJsonResponse:
        status_code = 500

        def json(self) -> object:
            raise ValueError("not json")

    assert _openai_compatible_error_from_response(BadJsonResponse()) == "HTTP 500"  # type: ignore[arg-type]


def test_openai_compatible_health_message_model_available_no_generation() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    msg = OpenAICompatibleProvider._health_message(
        model_available=True,
        generation_available=None,
        generation_message=None,
    )

    assert "reachable" in msg
    assert "available" in msg
    assert "generate" not in msg


def test_openai_compatible_health_message_generation_failed() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    msg = OpenAICompatibleProvider._health_message(
        model_available=True,
        generation_available=False,
        generation_message="GPU out of memory",
    )

    assert "generation probe failed" in msg
    assert "GPU out of memory" in msg


def test_openai_compatible_health_message_generation_succeeded() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    msg = OpenAICompatibleProvider._health_message(
        model_available=True,
        generation_available=True,
        generation_message="Generation probe completed.",
    )

    assert "can generate" in msg


def test_openai_compatible_health_message_model_not_listed() -> None:
    from agentic_trader.llm.providers import OpenAICompatibleProvider

    msg = OpenAICompatibleProvider._health_message(
        model_available=False,
        generation_available=None,
        generation_message=None,
    )

    assert "not listed" in msg


def test_openai_compatible_health_when_endpoint_unreachable() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="my-model")
    )

    class ErrorClient:
        def get(self, _url: str, **_kwargs: Any) -> object:
            raise ConnectionError("Connection refused")

        def post(self, _url: str, **_kwargs: Any) -> object:
            raise ConnectionError("Connection refused")

    object.__setattr__(provider, "client", ErrorClient())

    health = provider.health_check(include_generation=True)

    assert health.service_reachable is False
    assert health.model_available is False
    assert health.generation_available is False
    assert "Unable to reach" in health.message


def test_openai_compatible_generate_raises_on_non_dict_response() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="my-model")
    )
    client = FakeClient()
    client.post_responses = [FakeResponse(["not", "a", "dict"])]
    object.__setattr__(provider, "client", client)

    with pytest.raises(RuntimeError, match="non-object payload"):
        provider.generate(prompt="hello")


def test_openai_compatible_probe_generation_skips_when_model_unavailable() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="missing-model")
    )
    client = FakeClient()
    object.__setattr__(provider, "client", client)

    ok, msg = provider._probe_generation(model_available=False)

    assert ok is False
    assert "not listed" in msg
    assert client.posts == []


def test_openai_compatible_probe_generation_returns_false_on_http_error() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="my-model")
    )
    client = FakeClient()
    client.post_responses = [
        FakeResponse({"error": "resource exhausted"}, status_code=429)
    ]
    object.__setattr__(provider, "client", client)

    ok, msg = provider._probe_generation(model_available=True)

    assert ok is False
    assert "resource exhausted" in msg


def test_openai_compatible_model_name_override_at_construction() -> None:
    provider = OpenAICompatibleProvider(
        Settings(llm_provider="openai-compatible", model_name="default-model"),
        model_name="override-model",
    )

    assert provider.model_name == "override-model"
