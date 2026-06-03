"""Database UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseTextFields:
    """Typed db copy fields for UITextCatalog."""

    db_locked_msg: str


__all__ = ("DatabaseTextFields",)
