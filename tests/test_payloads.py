from __future__ import annotations

from dataclasses import dataclass

import pytest

from agentic_trader.payloads import dataclass_payload


@dataclass(frozen=True)
class ExamplePayload:
    name: str
    values: tuple[str, ...]


def test_dataclass_payload_returns_plain_mapping() -> None:
    payload = dataclass_payload(ExamplePayload(name="example", values=("a", "b")))

    assert payload == {"name": "example", "values": ("a", "b")}


def test_dataclass_payload_rejects_non_dataclass_instances() -> None:
    with pytest.raises(TypeError, match="expected dataclass instance"):
        dataclass_payload({"name": "example"})
