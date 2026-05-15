"""File-backed operator controls for the optional research cycle."""

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import utc_now_iso
from agentic_trader.runtime_feed import (
    read_research_cycle_control,
    write_research_cycle_control,
)
from agentic_trader.schemas import (
    ResearchCycleControlAction,
    ResearchCycleOperatorControl,
)


def default_research_cycle_control() -> ResearchCycleOperatorControl:
    """Return the default advisory control state when no operator file exists."""
    return ResearchCycleOperatorControl(
        status="running",
        requested_action="idle",
        updated_at=utc_now_iso(),
        updated_by="system-default",
        reason="no operator control file has been written yet",
    )


def get_research_cycle_control(settings: Settings) -> ResearchCycleOperatorControl:
    """Read operator control without creating runtime state."""
    return read_research_cycle_control(settings) or default_research_cycle_control()


def set_research_cycle_control(
    settings: Settings,
    *,
    action: ResearchCycleControlAction,
    reason: str | None = None,
) -> ResearchCycleOperatorControl:
    """Persist an explicit operator action for future research-cycle runners."""
    now = utc_now_iso()
    current = get_research_cycle_control(settings)
    status = current.status
    trigger_now_requested = current.trigger_now_requested
    trigger_requested_at = current.trigger_requested_at
    paused_at = current.paused_at
    resumed_at = current.resumed_at

    if action == "pause":
        status = "paused"
        trigger_now_requested = False
        paused_at = now
    elif action == "resume":
        status = "running"
        trigger_now_requested = False
        resumed_at = now
    elif action == "trigger_now":
        trigger_now_requested = True
        trigger_requested_at = now
    elif action != "idle":
        raise ValueError(f"unsupported research cycle action: {action}")

    control = ResearchCycleOperatorControl(
        status=status,
        requested_action=action,
        updated_at=now,
        updated_by="operator",
        reason=reason,
        trigger_now_requested=trigger_now_requested,
        trigger_requested_at=trigger_requested_at,
        paused_at=paused_at,
        resumed_at=resumed_at,
    )
    write_research_cycle_control(settings, control)
    return control
