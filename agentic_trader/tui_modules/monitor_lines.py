from collections.abc import Mapping

from agentic_trader.config import Settings
from agentic_trader.runtime_status import AgentActivityView, RuntimeStatusView
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.ui_text import (
    LABEL_BROKER_BACKEND,
    LABEL_BROKER_STATE,
    LABEL_COMPLETED_NOTE,
    LABEL_CURRENT_NOTE,
    LABEL_CURRENT_STAGE,
    LABEL_CURRENT_SYMBOL,
    LABEL_CYCLE,
    LABEL_INTERVAL,
    LABEL_KILL_SWITCH,
    LABEL_LAST_COMPLETED_STAGE,
    LABEL_LAST_OUTCOME,
    LABEL_LAST_OUTCOME_TYPE,
    LABEL_LOOKBACK,
    LABEL_RUNTIME,
    LABEL_STAGE_MESSAGE,
    LABEL_STAGE_STATUS,
    LABEL_V1_PAPER_GATE,
    LABEL_WATCHED_SYMBOLS,
    MESSAGE_NO_AGENT_ACTIVITY_RECORDED,
    MESSAGE_WAITING_FOR_LAST_OUTCOME,
    TITLE_RUNTIME_MODE,
    UI_LIST_SEPARATOR,
    UITextCatalog,
    get_ui_text,
)


def label_line(label: str, value: object) -> str:
    return ": ".join((label, str(value)))


def runtime_cycle_lines(
    *,
    settings: Settings,
    state: ServiceStateSnapshot | None,
    view: RuntimeStatusView,
) -> list[str]:
    return [
        label_line(LABEL_RUNTIME, view.runtime_state),
        label_line(
            TITLE_RUNTIME_MODE,
            state.runtime_mode if state is not None else settings.runtime_mode,
        ),
        label_line(
            LABEL_WATCHED_SYMBOLS,
            (
                UI_LIST_SEPARATOR.join(state.symbols)
                if state is not None and state.symbols
                else "-"
            ),
        ),
        label_line(
            LABEL_CURRENT_SYMBOL,
            (
                view.state.current_symbol
                if view.state is not None and view.state.current_symbol
                else "-"
            ),
        ),
        label_line(
            LABEL_CYCLE, view.state.cycle_count if view.state is not None else "-"
        ),
        label_line(
            f"{LABEL_INTERVAL} / {LABEL_LOOKBACK}",
            (
                f"{state.interval if state is not None and state.interval else '-'} / "
                f"{state.lookback if state is not None and state.lookback else '-'}"
            ),
        ),
        label_line(
            LABEL_CURRENT_NOTE,
            (
                view.state.message
                if view.state is not None and view.state.message
                else "-"
            ),
        ),
    ]


def agent_activity_lines(activity: AgentActivityView) -> list[str]:
    return [
        label_line(LABEL_CURRENT_STAGE, activity.current_stage or "-"),
        label_line(LABEL_STAGE_STATUS, activity.current_stage_status or "-"),
        label_line(
            LABEL_STAGE_MESSAGE,
            activity.current_stage_message or MESSAGE_NO_AGENT_ACTIVITY_RECORDED,
        ),
        label_line(LABEL_LAST_COMPLETED_STAGE, activity.last_completed_stage or "-"),
        label_line(LABEL_COMPLETED_NOTE, activity.last_completed_message or "-"),
    ]


def broker_gate_lines(
    *,
    broker: Mapping[str, object],
    paper_operations: Mapping[str, object],
    copy: UITextCatalog | None = None,
) -> list[str]:
    text = copy or get_ui_text()
    return [
        label_line(LABEL_BROKER_BACKEND, broker.get("backend", "-")),
        label_line(LABEL_BROKER_STATE, broker.get("state", "-")),
        label_line(
            LABEL_KILL_SWITCH,
            (
                text.status_active
                if broker.get("kill_switch_active")
                else text.status_inactive
            ),
        ),
        label_line(
            LABEL_V1_PAPER_GATE,
            (
                text.status_allowed
                if paper_operations.get("allowed")
                else text.status_blocked
            ),
        ),
    ]


def last_outcome_lines(activity: AgentActivityView) -> list[str]:
    if activity.last_outcome_message is not None:
        return [
            label_line(LABEL_LAST_OUTCOME_TYPE, activity.last_outcome_type or "-"),
            label_line(LABEL_LAST_OUTCOME, activity.last_outcome_message),
        ]
    return [label_line(LABEL_LAST_OUTCOME, MESSAGE_WAITING_FOR_LAST_OUTCOME)]


__all__ = (
    "agent_activity_lines",
    "broker_gate_lines",
    "label_line",
    "last_outcome_lines",
    "runtime_cycle_lines",
)
