from rich.console import Console

from agentic_trader.runtime_status import build_runtime_status_view
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.tui import _runtime_state_table


def test_build_runtime_status_view_marks_terminal_failure_as_inactive(monkeypatch) -> None:
    monkeypatch.setattr("agentic_trader.runtime_status._is_process_alive", lambda pid: False)
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


def test_runtime_state_table_surfaces_last_recorded_failure(monkeypatch) -> None:
    monkeypatch.setattr("agentic_trader.runtime_status._is_process_alive", lambda pid: False)
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
