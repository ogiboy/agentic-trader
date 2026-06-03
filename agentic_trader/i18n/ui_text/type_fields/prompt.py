"""Prompt UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTextFields:
    """Typed prompt copy fields for UITextCatalog."""

    prompt_continue: str
    prompt_select_action: str
    prompt_apply_preference_update: str
    prompt_chat_persona: str
    prompt_continuous_mode: str
    prompt_instruction: str
    prompt_max_cycles: str
    prompt_open_live_monitor_now: str
    prompt_poll_interval_seconds: str
    prompt_refresh_seconds: str
    prompt_you: str


__all__ = ("PromptTextFields",)
