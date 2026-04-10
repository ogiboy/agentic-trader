from rich.console import Console
import pytest

from agentic_trader.runtime_status import build_agent_activity_view, build_runtime_status_view
from agentic_trader.schemas import ServiceEvent, ServiceStateSnapshot
from agentic_trader.tui import _runtime_state_table


def test_build_runtime_status_view_marks_terminal_failure_as_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agentic_trader.runtime_status.is_process_alive", lambda pid: False
    )
    state = ServiceStateSnapshot(
        service_name="orchestrator",
        state="failed",
        updated_at="2026-03-31T22:34:47.305178+00:00",
        started_at="2026-03-31T22:33:58.259795+00:00",
        last_heartbeat_at="2026-03-31T22:34:47.305178+00:00",
        continuous=False,
        poll_seconds=300,
        cycle_count=1,
        current_symbol=None,
        last_error="Invalid JSON",
        pid=64059,
        stop_requested=False,
        message="Orchestrator failed.",
    )

    view = build_runtime_status_view(state)

    assert view.runtime_state == "inactive"
    assert view.last_recorded_state == "failed"
    assert view.live_process is False
    assert "last recorded runtime state" in view.status_message.lower()


def test_runtime_state_table_surfaces_last_recorded_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentic_trader.runtime_status.is_process_alive", lambda pid: False
    )
    state = ServiceStateSnapshot(
        service_name="orchestrator",
        state="failed",
        updated_at="2026-03-31T22:34:47.305178+00:00",
        started_at="2026-03-31T22:33:58.259795+00:00",
        last_heartbeat_at="2026-03-31T22:34:47.305178+00:00",
        continuous=False,
        poll_seconds=300,
        cycle_count=1,
        current_symbol=None,
        last_error="Invalid JSON",
        pid=64059,
        stop_requested=False,
        message="Orchestrator failed.",
    )

    renderable = _runtime_state_table(state)
    console = Console(record=True, width=140)
    console.print(renderable)
    output = console.export_text()

    assert "Runtime" in output
    assert "inactive" in output
    assert "Last Recorded State" in output
    assert "failed" in output
    assert "Last Recorded Error" in output


def test_build_agent_activity_view_summarizes_stage_progress() -> None:
    state = ServiceStateSnapshot(
        service_name="orchestrator",
        state="running",
        updated_at="2026-04-09T10:00:05+00:00",
        last_heartbeat_at="2026-04-09T10:00:05+00:00",
        cycle_count=2,
        current_symbol="AAPL",
        pid=1234,
        message="Manager agent is combining specialist outputs for AAPL.",
    )
    events = [
        ServiceEvent(
            event_id="evt-5",
            created_at="2026-04-09T10:00:05+00:00",
            level="info",
            event_type="agent_manager_started",
            message="Manager agent is combining specialist outputs for AAPL.",
            cycle_count=2,
            symbol="AAPL",
        ),
        ServiceEvent(
            event_id="evt-4",
            created_at="2026-04-09T10:00:04+00:00",
            level="info",
            event_type="agent_consensus_completed",
            message="Specialist consensus assessed as mixed.",
            cycle_count=2,
            symbol="AAPL",
        ),
        ServiceEvent(
            event_id="evt-3",
            created_at="2026-04-09T10:00:03+00:00",
            level="info",
            event_type="agent_risk_completed",
            message="Risk steward set size 5.00% and RR 2.00.",
            cycle_count=2,
            symbol="AAPL",
        ),
        ServiceEvent(
            event_id="evt-2",
            created_at="2026-04-09T10:00:02+00:00",
            level="info",
            event_type="agent_strategy_completed",
            message="Strategy selector chose trend_following with action buy.",
            cycle_count=2,
            symbol="AAPL",
        ),
        ServiceEvent(
            event_id="evt-1",
            created_at="2026-04-09T10:00:01+00:00",
            level="info",
            event_type="cycle_started",
            message="Cycle 2 started for 1 symbol(s).",
            cycle_count=2,
            symbol=None,
        ),
    ]

    view = build_agent_activity_view(state, events)

    assert view.current_stage == "manager"
    assert view.current_stage_status == "running"
    assert view.last_completed_stage == "consensus"
    assert view.stage_statuses[0].stage == "coordinator"
    assert view.stage_statuses[0].status == "pending"
    assert any(stage.stage == "strategy" and stage.status == "completed" for stage in view.stage_statuses)


def test_build_agent_activity_view_closes_running_stage_after_failure() -> None:
    state = ServiceStateSnapshot(
        service_name="orchestrator",
        state="failed",
        updated_at="2026-04-09T10:00:06+00:00",
        last_heartbeat_at="2026-04-09T10:00:06+00:00",
        cycle_count=2,
        current_symbol="AAPL",
        pid=1234,
        message="Orchestrator failed.",
    )
    events = [
        ServiceEvent(
            event_id="evt-2",
            created_at="2026-04-09T10:00:06+00:00",
            level="error",
            event_type="service_failed",
            message="LLM structured output validation failed.",
            cycle_count=2,
            symbol="AAPL",
        ),
        ServiceEvent(
            event_id="evt-1",
            created_at="2026-04-09T10:00:05+00:00",
            level="info",
            event_type="agent_risk_started",
            message="Risk steward is sizing the candidate trade.",
            cycle_count=2,
            symbol="AAPL",
        ),
    ]

    view = build_agent_activity_view(state, events)

    assert view.current_stage == "risk"
    assert view.current_stage_status == "failed"
    assert "service_failed" in (view.current_stage_message or "")
    assert any(stage.stage == "risk" and stage.status == "failed" for stage in view.stage_statuses)
