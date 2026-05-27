from __future__ import annotations

from collections import UserDict

from agentic_trader.json_utils import (
    object_dict_list,
    object_dict_or_none,
    object_list,
    object_mapping,
    object_mapping_list,
    object_mapping_or_none,
)


def test_json_utils_accept_abstract_mappings_and_sequences() -> None:
    mapping = UserDict({"symbol": "AAPL", "score": 1})
    rows = (mapping, {"symbol": "MSFT"}, "not-a-row")

    assert object_mapping(mapping)["symbol"] == "AAPL"
    optional_mapping = object_mapping_or_none(mapping)
    assert optional_mapping is not None
    assert optional_mapping["symbol"] == "AAPL"
    assert object_mapping_or_none("AAPL") is None
    assert object_dict_or_none({"symbol": "AAPL"}) == {"symbol": "AAPL"}
    assert object_dict_or_none(mapping) is None
    assert object_list(("AAPL", "MSFT")) == ["AAPL", "MSFT"]
    assert object_list("AAPL") == []
    assert [row["symbol"] for row in object_mapping_list(rows)] == ["AAPL", "MSFT"]
    assert object_dict_list(rows) == [{"symbol": "MSFT"}]
