from __future__ import annotations

from collections import UserDict

from agentic_trader.json_utils import object_list, object_mapping, object_mapping_list


def test_json_utils_accept_abstract_mappings_and_sequences() -> None:
    mapping = UserDict({"symbol": "AAPL", "score": 1})
    rows = (mapping, {"symbol": "MSFT"}, "not-a-row")

    assert object_mapping(mapping)["symbol"] == "AAPL"
    assert object_list(("AAPL", "MSFT")) == ["AAPL", "MSFT"]
    assert object_list("AAPL") == []
    assert [row["symbol"] for row in object_mapping_list(rows)] == ["AAPL", "MSFT"]
