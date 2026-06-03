"""HTTP utilities shared by public-source provider adapters."""

from collections.abc import Mapping
from typing import Any, Callable

import httpx

from agentic_trader.json_utils import object_dict_or_none as _object_mapping

JsonFetcher = Callable[[str, Mapping[str, str], float], dict[str, Any]]


def fetch_json(
    url: str, headers: Mapping[str, str], timeout_seconds: float
) -> dict[str, Any]:
    """Fetch a JSON object using a blocking HTTP GET request."""
    response = httpx.get(url, headers=dict(headers), timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    payload_object = _object_mapping(payload)
    if payload_object is None:
        raise ValueError("JSON response was not an object")
    return payload_object
