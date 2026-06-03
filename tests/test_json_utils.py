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
    assert object_mapping("AAPL") == {}
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


# ---------------------------------------------------------------------------
# object_mapping edge cases
# ---------------------------------------------------------------------------


def test_object_mapping_returns_empty_for_none() -> None:
    assert object_mapping(None) == {}


def test_object_mapping_returns_empty_for_integer() -> None:
    assert object_mapping(42) == {}


def test_object_mapping_returns_empty_for_list() -> None:
    assert object_mapping([{"key": "value"}]) == {}


def test_object_mapping_returns_empty_dict_as_mapping() -> None:
    result = object_mapping({})
    assert result == {}


def test_object_mapping_or_none_returns_none_for_none() -> None:
    assert object_mapping_or_none(None) is None


def test_object_mapping_or_none_returns_none_for_integer() -> None:
    assert object_mapping_or_none(0) is None


# ---------------------------------------------------------------------------
# object_list edge cases
# ---------------------------------------------------------------------------


def test_object_list_returns_empty_for_none() -> None:
    assert object_list(None) == []


def test_object_list_returns_empty_for_bytes() -> None:
    assert object_list(b"binary") == []


def test_object_list_returns_empty_for_bytearray() -> None:
    assert object_list(bytearray(b"data")) == []


def test_object_list_handles_empty_list() -> None:
    assert object_list([]) == []


def test_object_list_handles_empty_tuple() -> None:
    assert object_list(()) == []


def test_object_list_converts_generator_like_sequences() -> None:
    result = object_list([1, 2, 3])
    assert result == [1, 2, 3]


def test_object_list_returns_fresh_copy() -> None:
    original = [1, 2, 3]
    result = object_list(original)
    result.append(4)
    assert original == [1, 2, 3]


# ---------------------------------------------------------------------------
# object_mapping_list edge cases
# ---------------------------------------------------------------------------


def test_object_mapping_list_returns_empty_for_empty_sequence() -> None:
    assert object_mapping_list([]) == []


def test_object_mapping_list_filters_out_non_mapping_items() -> None:
    items = [{"key": "a"}, "string", 42, None, {"key": "b"}]
    result = object_mapping_list(items)
    assert len(result) == 2
    assert result[0]["key"] == "a"
    assert result[1]["key"] == "b"


def test_object_mapping_list_returns_empty_for_all_non_mapping() -> None:
    assert object_mapping_list(["a", "b", 1, 2]) == []


def test_object_mapping_list_handles_none_input() -> None:
    assert object_mapping_list(None) == []


def test_object_mapping_list_preserves_order() -> None:
    items = [{"order": 3}, {"order": 1}, {"order": 2}]
    result = object_mapping_list(items)
    assert [r["order"] for r in result] == [3, 1, 2]


# ---------------------------------------------------------------------------
# object_dict_or_none edge cases
# ---------------------------------------------------------------------------


def test_object_dict_or_none_returns_none_for_none() -> None:
    assert object_dict_or_none(None) is None


def test_object_dict_or_none_returns_none_for_abstract_mapping() -> None:
    # UserDict is a Mapping but not a concrete dict
    assert object_dict_or_none(UserDict({"a": 1})) is None


def test_object_dict_or_none_returns_none_for_string() -> None:
    assert object_dict_or_none("hello") is None


# ---------------------------------------------------------------------------
# object_dict_list edge cases
# ---------------------------------------------------------------------------


def test_object_dict_list_excludes_abstract_mappings() -> None:
    items = [{"concrete": True}, UserDict({"abstract": True}), {"also_concrete": True}]
    result = object_dict_list(items)
    # Only concrete dicts pass through
    assert len(result) == 2
    assert result[0] == {"concrete": True}
    assert result[1] == {"also_concrete": True}


def test_object_dict_list_returns_empty_for_empty_input() -> None:
    assert object_dict_list([]) == []
