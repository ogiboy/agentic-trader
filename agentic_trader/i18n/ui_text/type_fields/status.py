"""Status UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusTextFields:
    """Typed status copy fields for UITextCatalog."""

    status_active: str
    status_allowed: str
    status_app_owned: str
    status_available: str
    status_blocked: str
    status_configured: str
    status_external: str
    status_fail: str
    status_inactive: str
    status_missing: str
    status_needs_attention: str
    status_pass: str
    status_readable: str
    status_ready: str


__all__ = ("StatusTextFields",)
