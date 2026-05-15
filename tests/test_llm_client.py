import pytest
from typing import Any

from pydantic import BaseModel

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import RegimeAssessment, StrategyPlan


class _StructuredEcho(BaseModel):
    value: str


class _FakeResponse:
    def __init__(self, payload: Any, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        """
        Return the stored payload provided when the fake response was created.

        Returns:
            Any: The payload originally passed to the _FakeResponse constructor.
        """
        return self._payload


def test_complete_structured_retries_after_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=1)
    llm = LocalLLM(settings)
    payloads = iter(
        [
            {"response": ""},
            {"response": '{"value":"ok"}'},
        ]
    )

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(next(payloads)),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=_StructuredEcho,
    )

    assert parsed.value == "ok"


def test_complete_structured_requests_provider_json_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)
    request_bodies: list[dict[str, Any]] = []

    def _capture_post(*_args: object, **kwargs: Any) -> _FakeResponse:
        request_bodies.append(kwargs["json"])
        return _FakeResponse({"response": '{"value":"ok"}'})

    monkeypatch.setattr(llm.client, "post", _capture_post)

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=_StructuredEcho,
    )

    assert parsed.value == "ok"
    assert request_bodies[0]["format"]["required"] == ["value"]
    assert "value" in request_bodies[0]["format"]["properties"]


def test_complete_text_retries_after_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=1)
    llm = LocalLLM(settings)
    payloads = iter(
        [
            {"error": "temporary model hiccup"},
            {"response": "healthy text"},
        ]
    )

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(next(payloads)),
    )

    text = llm.complete_text(
        system_prompt="Be concise.",
        user_prompt="Hello",
    )

    assert text == "healthy text"


def test_complete_structured_reports_payload_preview_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse({"response": ""}),
    )

    try:
        llm.complete_structured(
            system_prompt="Return JSON.",
            user_prompt="Test",
            schema=_StructuredEcho,
        )
    except RuntimeError as exc:
        assert "empty response body" in str(exc).lower()
        assert "response" in str(exc).lower()
    else:
        raise AssertionError(
            "Expected RuntimeError for exhausted empty structured response"
        )


def test_complete_structured_redacts_provider_thinking_from_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {"response": "", "thinking": "private chain of thought"}
        ),
    )

    with pytest.raises(RuntimeError) as exc_info:
        llm.complete_structured(
            system_prompt="Return JSON.",
            user_prompt="Test",
            schema=_StructuredEcho,
        )

    message = str(exc_info.value)
    assert "private chain of thought" not in message
    assert '"thinking": "<redacted>"' in message


def test_complete_structured_reports_concise_validation_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse({"response": '{"unexpected":"shape"}'}),
    )

    with pytest.raises(RuntimeError) as exc_info:
        llm.complete_structured(
            system_prompt="Return JSON.",
            user_prompt="Test",
            schema=_StructuredEcho,
        )

    message = str(exc_info.value)
    assert message == (
        "LLM structured output validation failed for _StructuredEcho: "
        "missing required fields: value"
    )
    captured = capsys.readouterr()
    assert "LLM structured validation failed on attempt" not in captured.err


def test_complete_structured_accepts_wrapped_strategy_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "response": (
                    '{"strategy":{"family":"no_trade","action":"hold",'
                    '"timeframe":"flat","entry":"No entry.",'
                    '"invalidation":"Wait for clearer evidence.",'
                    '"confidence":0.42}}'
                )
            }
        ),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=StrategyPlan,
    )

    assert parsed.strategy_family == "no_trade"
    assert parsed.entry_logic == "No entry."
    assert parsed.invalidation_logic == "Wait for clearer evidence."


def test_complete_structured_normalizes_common_regime_value_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "response": (
                    '{"regime":"sideways","direction_bias":"neutral",'
                    '"confidence":0.54,"reasoning":"Range behavior dominates."}'
                )
            }
        ),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=RegimeAssessment,
    )

    assert parsed.regime == "range"
    assert parsed.direction_bias == "flat"


def test_complete_structured_maps_regime_explanation_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "response": (
                    '{"regime":"no_trade","direction_bias":"flat",'
                    '"confidence":0.35,'
                    '"notes":"Evidence is too weak for a trade."}'
                )
            }
        ),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=RegimeAssessment,
    )

    assert parsed.reasoning == "Evidence is too weak for a trade."
    assert parsed.source == "llm"
    assert parsed.fallback_reason is None


def test_complete_structured_conservatively_sanitizes_missing_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "response": (
                    '{"regime":"mixed low conviction","directional_bias":"neutral",'
                    '"notes":"Evidence is mixed."}'
                )
            }
        ),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=RegimeAssessment,
    )

    assert parsed.regime == "range"
    assert parsed.direction_bias == "flat"
    assert parsed.confidence == pytest.approx(0.0)
    assert parsed.reasoning == "Evidence is mixed."


def test_complete_structured_coerces_qualitative_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(max_retries=0)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "response": (
                    '{"regime":"range","direction_bias":"flat",'
                    '"confidence":"low","reasoning":"Weak evidence."}'
                )
            }
        ),
    )

    parsed = llm.complete_structured(
        system_prompt="Return JSON.",
        user_prompt="Test",
        schema=RegimeAssessment,
    )

    assert parsed.confidence == pytest.approx(0.25)


def test_local_llm_uses_configured_provider_defaults() -> None:
    settings = Settings(llm_provider="ollama", model_name="qwen3:8b")

    llm = LocalLLM(settings)

    assert llm.provider.provider_name == "ollama"
    assert llm.model_name == "qwen3:8b"
    assert llm.base_url.endswith("localhost:11434")


def test_health_check_generation_probe_reports_model_load_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(llm_provider="ollama", model_name="qwen3:8b")
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm.client,
        "get",
        lambda *_args, **_kwargs: _FakeResponse(
            {"models": [{"name": "qwen3:8b"}]}
        ),
    )
    monkeypatch.setattr(
        llm.client,
        "post",
        lambda *_args, **_kwargs: _FakeResponse(
            {
                "error": (
                    "model failed to load, this may be due to resource limitations"
                )
            },
            status_code=500,
        ),
    )

    health = llm.health_check(include_generation=True)

    assert health.service_reachable is True
    assert health.model_available is True
    assert health.generation_available is False
    assert "generation probe failed" in health.message
    assert "resource limitations" in (health.generation_message or "")
