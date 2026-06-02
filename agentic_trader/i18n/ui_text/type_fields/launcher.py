"""Launcher UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LauncherTextFields:
    """Typed launcher copy fields for UITextCatalog."""

    launcher_option_open_web_gui: str
    launcher_option_continue_tui: str
    launcher_option_refresh: str
    launcher_option_exit: str


__all__ = ("LauncherTextFields",)
