from collections.abc import Mapping

from agentic_trader.config import Settings
from agentic_trader.runtime_status import AgentActivityView, RuntimeStatusView
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.ui_text import (
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
    """
    Builds a list of labeled lines describing the runtime cycle and view state for UI display.

    Parameters:
        settings (Settings): Configuration used when `state` is None to supply defaults (e.g., runtime_mode).
        state (ServiceStateSnapshot | None): Current runtime snapshot; when None, fields fall back to `settings` or "-" as described below.
        view (RuntimeStatusView): Current runtime view containing runtime_state and optional nested state fields.

    Returns:
        list[str]: Lines with labels and values for:
            - runtime state (from `view.runtime_state`)
            - runtime mode (from `state.runtime_mode` or `settings.runtime_mode`)
            - watched symbols (joined by `t("list.separator")` or "-" when missing)
            - current symbol (from `view.state.current_symbol` or "-")
            - cycle count (from `view.state.cycle_count` or "-")
            - interval / lookback (formatted as "interval / lookback" with "-" for missing parts)
            - current note/message (from `view.state.message` or "-")
    """
    return [
        label_line(t("label.runtime"), view.runtime_state),
        label_line(
            t("title.runtime.mode"),
            state.runtime_mode if state is not None else settings.runtime_mode,
        ),
        label_line(
            t("label.watched.symbols"),
            (
                t("list.separator").join(state.symbols)
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
    """
    Builds five labeled lines summarizing an agent's current activity and last completed stage.

    Parameters:
        activity (AgentActivityView): View containing `current_stage`, `current_stage_status`,
            `current_stage_message`, `last_completed_stage`, and `last_completed_message`.

    Returns:
        list[str]: Five strings with localized labels and values in this order:
            1. Current stage (or "-" if missing)
            2. Stage status (or "-" if missing)
            3. Stage message (or a localized "no activity recorded" message if missing)
            4. Last completed stage (or "-" if missing)
            5. Completed note (or "-" if missing)
    """
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
    """
    Builds labeled status lines describing broker backend, broker state, kill-switch, and V1 paper gate.

    Parameters:
        broker (Mapping[str, object]): Mapping containing broker fields; expected keys include
            "backend", "state", and "kill_switch_active".
        paper_operations (Mapping[str, object]): Mapping containing paper gate fields; expected key:
            "allowed".
        copy (UITextCatalog | None): Optional UI text catalog to use for localized labels and status
            strings. If omitted, the module default UI text is used.

    Returns:
        list[str]: Four labeled lines (broker backend, broker state, kill switch status, V1 paper gate status).
    """
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
    """
    Format the last outcome information from an agent activity into labeled UI lines.

    Parameters:
        activity (AgentActivityView): Activity view containing last outcome type and message.

    Returns:
        list[str]: Two labeled lines — the last outcome type (or "-" if missing) and the last outcome message — when a last outcome message exists; otherwise a single labeled line indicating that the last outcome is still awaited.
    """
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
