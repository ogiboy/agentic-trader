"""Tests for the agentic_trader package version."""

from __future__ import annotations

import agentic_trader


def test_version_is_string() -> None:
    assert isinstance(agentic_trader.__version__, str)


def test_version_is_0_16_0() -> None:
    """Version was bumped from 0.15.0 to 0.16.0 in this PR."""
    assert agentic_trader.__version__ == "0.16.0"


def test_version_all_exports_version() -> None:
    assert "__version__" in agentic_trader.__all__


def test_version_semver_shape() -> None:
    parts = agentic_trader.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
