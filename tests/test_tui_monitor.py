from pathlib import Path

from rich.console import Console

from agentic_trader.config import Settings
from agentic_trader.runtime_status import (
    AgentActivityView,
    AgentStageStatusView,
    RuntimeStatusView,
)
from agentic_trader.schemas import (
    HistoricalMemoryMatch,
    LLMHealthStatus,
    ServiceStateSnapshot,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui import (
    TuiMenuAction,
    _agent_activity_lines,
    _agent_activity_table,
    _broker_gate_lines,
    _last_outcome_lines,
    _main_menu_actions,
    _main_menu_table,
    _memory_explorer_table,
    _menu_table,
    _run_main_menu_action,
    _runtime_cycle_lines,
    _runtime_state_table,
    _split_csv,
    _style_key,
    _system_status_table,
    build_monitor_renderable,
)


def test_build_monitor_renderable_contains_core_sections(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=60,
        cycle_count=3,
        current_symbol="AAPL",
        message="Monitoring AAPL",
    )
    db.insert_service_event(
        level="info",
        event_type="cycle_started",
        message="Cycle started",
        cycle_count=3,
        symbol="AAPL",
    )
    db.insert_service_event(
        level="info",
        event_type="agent_regime_started",
        message="Regime analyst started.",
        cycle_count=3,
        symbol="AAPL",
    )

    renderable = build_monitor_renderable(settings, db)
    console = Console(record=True, width=140)
    console.print(renderable)
    output = console.export_text()

    assert "Agentic Trader Live Monitor" in output
    assert "Current Cycle" in output
    assert "Interval / Lookback" in output
    assert "Broker Backend" in output
    assert "V1 Paper Gate" in output
    assert "Current Stage" in output
    assert "Stage Status" in output
    assert "System Status" in output
    assert "Runtime Status" in output
    assert "Portfolio" in output
    assert "Runtime Events" in output
    assert "Decision Workflow" in output
    assert "Cash (USD)" in output
    assert "Marked At" in output


def test_agent_activity_table_filters_to_current_runtime_cycle(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=60,
        cycle_count=3,
        current_symbol="AAPL",
        message="Cycle 3 is active.",
    )
    db.insert_service_event(
        level="info",
        event_type="agent_regime_started",
        message="Old cycle regime event.",
        cycle_count=2,
        symbol="AAPL",
    )

    state = db.get_service_state()
    events = db.list_service_events(limit=20)
    console = Console(record=True, width=120)
    console.print(_agent_activity_table(state, events))
    output = console.export_text()

    assert "Old cycle regime event." not in output
    assert "Waiting for this stage to start." in output


def test_terminal_tui_pure_helpers_render_status_lines(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        runtime_mode="operation",
    )
    settings.ensure_directories()
    state = ServiceStateSnapshot(
        service_name="agentic_trader",
        state="running",
        runtime_mode="operation",
        updated_at="2026-05-15T00:00:00+00:00",
        continuous=True,
        cycle_count=4,
        current_symbol="AAPL",
        interval="1d",
        lookback="90d",
        message="Working.",
        pid=1234,
        symbols=["AAPL", "MSFT"],
    )
    view = RuntimeStatusView(
        runtime_state="active",
        last_recorded_state="running",
        status_message="Runtime active.",
        live_process=True,
        is_stale=False,
        age_seconds=2,
        state=state,
    )
    activity = AgentActivityView(
        cycle_count=4,
        current_symbol="AAPL",
        current_stage="manager",
        current_stage_status="running",
        current_stage_message="Sizing order.",
        last_completed_stage="risk",
        last_completed_message="Risk plan complete.",
        last_outcome_type="symbol_completed",
        last_outcome_message="Cycle complete.",
        stage_statuses=(
            AgentStageStatusView(
                stage="manager",
                status="running",
                message="Sizing order.",
                created_at="2026-05-15T00:00:00+00:00",
                cycle_count=4,
                symbol="AAPL",
            ),
        ),
        recent_stage_events=(),
    )

    assert _style_key("7") == "[bold cyan]7[/bold cyan]"
    assert _split_csv(" aapl, msft ,, ") == ["AAPL", "MSFT"]
    assert _runtime_cycle_lines(settings=settings, state=state, view=view) == [
        "Runtime: active",
        "Runtime Mode: operation",
        "Watched Symbols: AAPL, MSFT",
        "Current Symbol: AAPL",
        "Cycle: 4",
        "Interval / Lookback: 1d / 90d",
        "Current Note: Working.",
    ]
    assert _agent_activity_lines(activity)[:3] == [
        "Current Stage: manager",
        "Stage Status: running",
        "Stage Message: Sizing order.",
    ]
    assert _broker_gate_lines(
        broker={"backend": "paper", "state": "ready", "kill_switch_active": False},
        paper_operations={"allowed": True},
    ) == [
        "Broker Backend: paper",
        "Broker State: ready",
        "Kill Switch: inactive",
        "V1 Paper Gate: allowed",
    ]
    assert _last_outcome_lines(activity) == [
        "Last Outcome Type: symbol_completed",
        "Last Outcome: Cycle complete.",
    ]
    empty_activity = AgentActivityView(
        cycle_count=None,
        current_symbol=None,
        current_stage=None,
        current_stage_status=None,
        current_stage_message=None,
        last_completed_stage=None,
        last_completed_message=None,
        last_outcome_type=None,
        last_outcome_message=None,
        stage_statuses=(),
        recent_stage_events=(),
    )
    assert _last_outcome_lines(empty_activity) == [
        "Last Outcome: Waiting for a completed symbol, exit, or service result."
    ]


def test_terminal_tui_tables_and_menu_actions(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    state = ServiceStateSnapshot(
        service_name="agentic_trader",
        state="completed",
        runtime_mode="operation",
        updated_at="2026-05-15T00:00:00+00:00",
        cycle_count=1,
        message="Done.",
    )

    console = Console(record=True, width=120)
    console.print(_runtime_state_table(None))
    console.print(_runtime_state_table(state))
    console.print(
        _system_status_table(
            settings,
            None,
            runtime_state=state,
            health=LLMHealthStatus(
                provider="ollama",
                base_url=settings.base_url,
                model_name=settings.model_name,
                service_reachable=True,
                model_available=True,
                message="ready",
            ),
        )
    )
    console.print(
        _memory_explorer_table(
            [
                HistoricalMemoryMatch(
                    run_id="run-1",
                    created_at="2026-05-15T00:00:00+00:00",
                    symbol="AAPL",
                    similarity_score=0.84,
                    regime="trend",
                    strategy_family="momentum",
                    manager_bias="buy",
                    approved=True,
                    summary="prior winner",
                )
            ]
        )
    )
    console.print(
        _menu_table(
            "Test Menu",
            [TuiMenuAction("1", "Render thing", "Thing", lambda _db: None), ("2", "Back")],
        )
    )
    actions = _main_menu_actions()
    console.print(_main_menu_table(actions))
    output = console.export_text()

    assert "no runtime state recorded yet" in output
    assert "Runtime active" not in output
    assert "System Status" in output
    assert "Base URL" in output
    assert "Decision Evidence Explorer" in output
    assert "AAPL" in output
    assert "Test Menu" in output
    assert "Configure investment preferences" in output

    called: list[str] = []
    keep_running = _run_main_menu_action(
        settings,
        "1",
        actions=[
            type(actions[0])("1", "Do work", lambda _settings: called.append("work")),
            type(actions[0])("2", "Exit", lambda _settings: called.append("exit"), True),
        ],
    )
    assert keep_running is True
    assert called == ["work"]
    keep_running = _run_main_menu_action(
        settings,
        "2",
        actions=[
            type(actions[0])("1", "Do work", lambda _settings: called.append("work")),
            type(actions[0])("2", "Exit", lambda _settings: called.append("exit"), True),
        ],
    )
    assert keep_running is False
    assert called[-1] == "exit"
