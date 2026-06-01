"""Small JSON-shape helpers shared by operator surfaces and payload adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast


def object_mapping(value: object) -> Mapping[str, object]:
    """
    Return the input as a string-keyed mapping when it is already a mapping.

    Returns:
        Mapping[str, object]: The input cast to `Mapping[str, object]` if it is a `Mapping`, otherwise an empty dict.
    """

    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def object_mapping_or_none(value: object) -> Mapping[str, object] | None:
    """
    Cast the input to a mapping with string keys when it is a Mapping, otherwise return None.

    Returns:
        Mapping[str, object] if `value` is a Mapping, `None` otherwise.
    """

    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return None


def object_dict_or_none(value: object) -> dict[str, object] | None:
    """
    Return the input if it is a concrete dict with string keys, otherwise None.

    Returns:
        dict[str, object] | None: The input as a `dict[str, object]` when it is exactly a `dict`, otherwise `None`.
    """

    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return None


def object_list(value: object) -> list[object]:
    """
    Coerce a non-string sequence into a list of objects.

    If `value` is a sequence but not a `str`, `bytes`, or `bytearray`, returns its contents as a `list[object]`; otherwise returns an empty list.

    Returns:
        list[object]: The sequence converted to a list, or an empty list if `value` is not a non-string sequence.
    """

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(cast(Sequence[object], value))
    return []


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    """
    Extract mapping elements from a value that may be a sequence and return them as a list.

    Parameters:
        value (object): The value to inspect; if it is a sequence (strings/bytes/bytearray are treated as scalars), each element is checked for being a mapping.

    Returns:
        list[Mapping[str, object]]: A list containing the mapping elements found in the input sequence, or an empty list if none were found or the input is not a non-string sequence.
    """

    rows: list[Mapping[str, object]] = []
    for item in object_list(value):
        if isinstance(item, Mapping):
            rows.append(cast(Mapping[str, object], item))
    return rows


def object_dict_list(value: object) -> list[dict[str, object]]:
    """
    Extract concrete dict objects from a non-string sequence.

    Parameters:
        value (object): Candidate value expected to be a sequence; strings, bytes and bytearray are not treated as sequences.

    Returns:
        list[dict[str, object]]: List of items from the sequence that are concrete `dict` objects, in original order.
    """

    rows: list[dict[str, object]] = []
    for item in object_list(value):
        row = object_dict_or_none(item)
        if row is not None:
            rows.append(row)
    return rows
