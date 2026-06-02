"""Style UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleTextFields:
    """Typed style copy fields for UITextCatalog."""

    style_key_column: str


__all__ = ("StyleTextFields",)
