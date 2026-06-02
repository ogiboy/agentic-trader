from __future__ import annotations

from typing import Protocol

import typer
from rich.panel import Panel

from agentic_trader.cli_modules.common import console, emit_json
from agentic_trader.config import Settings
from agentic_trader.schemas import (
    ResearchCycleControlAction,
    ResearchCycleOperatorControl,
)
from agentic_trader.ui_text import (
    LABEL_NO,
    LABEL_RESEARCH_CYCLE_CONTROL,
    LABEL_TRIGGER_NOW_REQUESTED,
    LABEL_YES,
    MESSAGE_RESEARCH_CYCLE_CHOOSE_ONE_ACTION,
    MESSAGE_RESEARCH_CYCLE_CONTROL_STATUS,
    MESSAGE_RESEARCH_CYCLE_REASON_REQUIRES_ACTION,
    TITLE_RESEARCH_CYCLE_CONTROL,
)


class GetResearchControl(Protocol):
    def __call__(self, settings: Settings) -> ResearchCycleOperatorControl:
        ...


class SetResearchControl(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        action: ResearchCycleControlAction,
        reason: str | None = None,
    ) -> ResearchCycleOperatorControl:
        ...


def run_research_cycle_control_command(
    *,
    settings: Settings,
    pause: bool,
    resume: bool,
    trigger_now: bool,
    reason: str | None,
    json_output: bool,
    get_control: GetResearchControl,
    set_control: SetResearchControl,
) -> None:
    action = _selected_research_action(
        pause=pause,
        resume=resume,
        trigger_now=trigger_now,
        reason=reason,
    )
    control = (
        set_control(settings, action=action, reason=reason)
        if action is not None
        else get_control(settings)
    )
    payload = research_cycle_control_payload(control, persisted=action is not None)
    if json_output:
        emit_json(payload)
        return
    render_research_cycle_control(control)


def _selected_research_action(
    *,
    pause: bool,
    resume: bool,
    trigger_now: bool,
    reason: str | None,
) -> ResearchCycleControlAction | None:
    selected_actions: list[ResearchCycleControlAction] = []
    if pause:
        selected_actions.append("pause")
    if resume:
        selected_actions.append("resume")
    if trigger_now:
        selected_actions.append("trigger_now")
    if len(selected_actions) > 1:
        raise typer.BadParameter(MESSAGE_RESEARCH_CYCLE_CHOOSE_ONE_ACTION)
    if reason is not None and not selected_actions:
        raise typer.BadParameter(MESSAGE_RESEARCH_CYCLE_REASON_REQUIRES_ACTION)
    return selected_actions[0] if selected_actions else None


def research_cycle_control_payload(
    control: ResearchCycleOperatorControl, *, persisted: bool
) -> dict[str, object]:
    return {
        "control": control.model_dump(mode="json"),
        "persisted": persisted,
        "execution_policy": {
            "broker_access": False,
            "proposal_creation": False,
            "manual_review_required": True,
        },
    }


def render_research_cycle_control(control: ResearchCycleOperatorControl) -> None:
    console.print(
        Panel(
            MESSAGE_RESEARCH_CYCLE_CONTROL_STATUS.format(
                label=LABEL_RESEARCH_CYCLE_CONTROL,
                status=control.status,
                trigger_label=LABEL_TRIGGER_NOW_REQUESTED,
                trigger_now=(LABEL_YES if control.trigger_now_requested else LABEL_NO),
            ),
            title=TITLE_RESEARCH_CYCLE_CONTROL,
            border_style="cyan",
        )
    )
