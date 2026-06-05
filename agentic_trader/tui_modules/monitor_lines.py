from collections.abc import Mapping

from agentic_trader.config import Settings
from agentic_trader.runtime_status import AgentActivityView, RuntimeStatusView
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.ui_text import (
    UI_LIST_SEPARATOR,
    UITextCatalog,
    get_ui_text,
    t,
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
        label_line(t("label.runtime"), view.runtime_state),
        label_line(
            t("title.runtime.mode"),
            state.runtime_mode if state is not None else settings.runtime_mode,
        ),
        label_line(
            t("label.watched.symbols"),
            (
                UI_LIST_SEPARATOR.join(state.symbols)
                if state is not None and state.symbols
                else "-"
            ),
        ),
        label_line(
            t("label.current.symbol"),
            (
                view.state.current_symbol
                if view.state is not None and view.state.current_symbol
                else "-"
            ),
        ),
        label_line(
            t("label.cycle"),
            view.state.cycle_count if view.state is not None else "-",
        ),
        label_line(
            f"{t('label.interval')} / {t('label.lookback')}",
            (
                f"{state.interval if state is not None and state.interval else '-'} / "
                f"{state.lookback if state is not None and state.lookback else '-'}"
            ),
        ),
        label_line(
            t("label.current.note"),
            (
                view.state.message
                if view.state is not None and view.state.message
                else "-"
            ),
        ),
    ]


def agent_activity_lines(activity: AgentActivityView) -> list[str]:
    return [
        label_line(t("label.current.stage"), activity.current_stage or "-"),
        label_line(t("label.stage.status"), activity.current_stage_status or "-"),
        label_line(
            t("label.stage.message"),
            activity.current_stage_message or t("message.no.agent.activity.recorded"),
        ),
        label_line(
            t("label.last.completed.stage"), activity.last_completed_stage or "-"
        ),
        label_line(t("label.completed.note"), activity.last_completed_message or "-"),
    ]


def broker_gate_lines(
    *,
    broker: Mapping[str, object],
    paper_operations: Mapping[str, object],
    copy: UITextCatalog | None = None,
) -> list[str]:
    text = copy or get_ui_text()
    return [
        label_line(t("label.broker.backend", catalog=text), broker.get("backend", "-")),
        label_line(t("label.broker.state", catalog=text), broker.get("state", "-")),
        label_line(
            t("label.kill.switch", catalog=text),
            (
                text.status_active
                if broker.get("kill_switch_active")
                else text.status_inactive
            ),
        ),
        label_line(
            t("label.v1.paper.gate", catalog=text),
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
            label_line(t("label.last.outcome.type"), activity.last_outcome_type or "-"),
            label_line(t("label.last.outcome"), activity.last_outcome_message),
        ]
    return [label_line(t("label.last.outcome"), t("message.waiting.for.last.outcome"))]


__all__ = (
    "agent_activity_lines",
    "broker_gate_lines",
    "label_line",
    "last_outcome_lines",
    "runtime_cycle_lines",
)
