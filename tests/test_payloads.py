from __future__ import annotations

from dataclasses import dataclass

import pytest

from agentic_trader.payloads import dataclass_payload


@dataclass(frozen=True)
class ExamplePayload:
    name: str
    values: tuple[str, ...]


@dataclass
class NestedInner:
    score: float
    tag: str


@dataclass
class NestedOuter:
    label: str
    inner: NestedInner


def test_dataclass_payload_returns_plain_mapping() -> None:
    payload = dataclass_payload(ExamplePayload(name="example", values=("a", "b")))

    assert payload == {"name": "example", "values": ("a", "b")}


def test_dataclass_payload_rejects_non_dataclass_instances() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload({"name": "example"})


def test_dataclass_payload_rejects_dataclass_class_not_instance() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload(ExamplePayload)  # type: ignore[arg-type]


def test_dataclass_payload_rejects_plain_string() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload("not-a-dataclass")


def test_dataclass_payload_rejects_none() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload(None)


def test_dataclass_payload_rejects_integer() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload(42)


def test_dataclass_payload_rejects_list() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload([1, 2, 3])


def test_dataclass_payload_handles_nested_dataclass() -> None:
    outer = NestedOuter(label="outer", inner=NestedInner(score=0.9, tag="good"))
    payload = dataclass_payload(outer)

    assert payload["label"] == "outer"
    inner_payload = payload["inner"]
    assert isinstance(inner_payload, dict)
    assert inner_payload["score"] == 0.9  # type: ignore[index]
    assert inner_payload["tag"] == "good"  # type: ignore[index]


def test_dataclass_payload_handles_empty_dataclass() -> None:
    @dataclass
    class EmptyPayload:
        pass

    payload = dataclass_payload(EmptyPayload())
    assert payload == {}


def test_dataclass_payload_preserves_none_field_values() -> None:
    @dataclass
    class OptionalPayload:
        name: str
        note: str | None = None

    payload = dataclass_payload(OptionalPayload(name="test"))
    assert payload["name"] == "test"
    assert payload["note"] is None
