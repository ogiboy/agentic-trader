"""Core UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoreTextFields:
    """Typed core copy fields for UITextCatalog."""

    cli_app_help: str
    list_separator: str


__all__ = ("CoreTextFields",)
