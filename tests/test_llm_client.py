from typing import Any

from pydantic import BaseModel

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM


class _StructuredEcho(BaseModel):
    value: str


class _FakeResponse:
    def __init__(self, payload: Any):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def test_complete_structured_retries_after_empty_response(monkeypatch) -> None:
    settings = Settings(max_retries=1)
    llm = LocalLLM(settings)
    payloads = iter(
        [
            {"response": ""},
            {"response": "{\"value\":\"ok\"}"},
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


def test_complete_text_retries_after_error_payload(monkeypatch) -> None:
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


def test_complete_structured_reports_payload_preview_when_exhausted(monkeypatch) -> None:
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
        raise AssertionError("Expected RuntimeError for exhausted empty structured response")
