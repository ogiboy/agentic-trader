"""Shared constants and helpers for broker adapter modules."""

from __future__ import annotations

import hashlib
from typing import SupportsFloat
from urllib.parse import urlparse
from uuid import uuid4

from agentic_trader.config import Settings

ALPACA_PAPER_ENDPOINT_HOST = "paper-api.alpaca.markets"
PAPER_BROKER_ACTIVE_MESSAGE = "Paper broker adapter is active."
ALPACA_CANCELLED_STATUSES = {"canceled", "cancelled"}
ALPACA_NO_FILL_STATUSES = {"expired"}
ALPACA_REJECTED_STATUSES = {"rejected"}


def deterministic_unit_interval(seed: str, label: str) -> float:
    """
    Deterministically derive a float in the interval [0, 1) from a seed and label.

    Parameters:
        seed (str): Primary seed value used to derive the output.
        label (str): Secondary label to produce a distinct value for the same seed.

    Returns:
        float: A deterministic pseudorandom value in [0, 1).
    """
    digest = hashlib.blake2b(f"{seed}:{label}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


def deterministic_uniform(seed: str, label: str, low: float, high: float) -> float:
    """
    Map a deterministic pseudo-random value derived from `seed` and `label` into the interval [low, high).

    Parameters:
        seed (str): Primary seed string used to derive the deterministic value.
        label (str): Secondary label appended to the seed to namespace the result.
        low (float): Lower bound of the target interval (inclusive).
        high (float): Upper bound of the target interval (exclusive).

    Returns:
        A float in the interval [low, high).
    """
    return low + ((high - low) * deterministic_unit_interval(seed, label))


def alpaca_client_order_id(intent_id: str) -> str:
    """
    Produce a sanitized client order identifier suitable for Alpaca: contains only alphanumeric characters, hyphen, or underscore and is at most 48 characters long.

    Parameters:
        intent_id (str): Original intent identifier to sanitize.

    Returns:
        str: A client order id containing only letters, digits, '-' and '_' truncated to 48 characters. If `intent_id` contains no allowed characters, returns a generated identifier starting with `"intent-"`.
    """
    cleaned = "".join(
        char for char in intent_id if char.isalnum() or char in {"-", "_"}
    )
    return (cleaned or f"intent-{uuid4().hex[:12]}")[:48]


def coerce_float(value: object, *, default: float = 0.0) -> float:
    try:
        if isinstance(value, SupportsFloat) or isinstance(
            value, (str, bytes, bytearray)
        ):
            return float(value)
        return default
    except (TypeError, ValueError):
        return default


def coerce_broker_float(value: object, *, default: float = 0.0) -> float:
    """Coerce a broker/API payload value into a float with a deterministic fallback."""
    return coerce_float(value, default=default)


def alpaca_credentials_ready(settings: Settings) -> bool:
    return bool(settings.alpaca_api_key and settings.alpaca_secret_key)


def alpaca_uses_paper_endpoint(settings: Settings) -> bool:
    """
    Check whether the configured Alpaca base URL targets the Alpaca paper endpoint.

    Parameters:
        settings (Settings): Application settings containing `alpaca_base_url`.

    Returns:
        True if the `alpaca_base_url` contains the Alpaca paper endpoint host, False otherwise.
    """
    parsed = urlparse(settings.alpaca_base_url)
    return parsed.hostname == ALPACA_PAPER_ENDPOINT_HOST
