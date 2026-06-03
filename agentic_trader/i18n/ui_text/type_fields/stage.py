"""Stage UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageTextFields:
    """Typed stage copy fields for UITextCatalog."""

    stage_coordinator: str
    stage_consensus: str
    stage_execution: str
    stage_fundamental: str
    stage_manager: str
    stage_regime: str
    stage_risk: str
    stage_strategy: str


__all__ = ("StageTextFields",)
