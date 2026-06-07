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
from agentic_trader.ui_text import t as ui_t


class GetResearchControl(Protocol):
    def __call__(self, settings: Settings) -> ResearchCycleOperatorControl: ...


class SetResearchControl(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        action: ResearchCycleControlAction,
        reason: str | None = None,
    ) -> ResearchCycleOperatorControl: ...


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
        raise typer.BadParameter(ui_t("message.research_cycle_choose_one_action"))
    if reason is not None and not selected_actions:
        raise typer.BadParameter(ui_t("message.research_cycle_reason_requires_action"))
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
            ui_t("message.research_cycle_control_status").format(
                label=ui_t("label.research_cycle_control"),
                status=control.status,
                trigger_label=ui_t("label.trigger_now_requested"),
                trigger_now=(
                    ui_t("label.yes")
                    if control.trigger_now_requested
                    else ui_t("label.no")
                ),
            ),
            title=ui_t("title.research_cycle_control"),
            border_style="cyan",
        )
    )
