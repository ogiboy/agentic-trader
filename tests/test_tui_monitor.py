from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pytest import MonkeyPatch
from rich.console import Console

from agentic_trader.config import Settings
from agentic_trader.runtime_status import (
    AgentActivityView,
    AgentStageStatusView,
    RuntimeStatusView,
)
from agentic_trader.schemas import (
    HistoricalMemoryMatch,
    InvestmentPreferences,
    LLMHealthStatus,
    ServiceStateSnapshot,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui import (
    TuiMenuAction,
    agent_activity_lines,
    agent_activity_table,
    banner,
    broker_gate_lines,
    build_monitor_renderable,
    exit_cleanly,
    last_outcome_lines,
    main_menu_actions,
    main_menu_table,
    memory_explorer_table,
    menu_table,
    run_main_menu_action,
    runtime_cycle_lines,
    runtime_state_table,
    split_csv,
    style_key,
    system_status_table,
)
from agentic_trader.tui_modules import runtime as runtime_module
from agentic_trader.ui_text import UI_LOCALE_ENV, get_ui_text


def test_build_monitor_renderable_contains_core_sections(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv(UI_LOCALE_ENV, "en")
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
    console.print(agent_activity_table(state, events))
    output = console.export_text()

    assert "Old cycle regime event." not in output
    assert "Waiting for this stage to start." in output


def test_terminal_tui_pure_helpers_render_status_lines(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv(UI_LOCALE_ENV, "en")
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

    assert style_key("7") == "[bold cyan]7[/bold cyan]"
    assert split_csv(" aapl, msft ,, ") == ["AAPL", "MSFT"]
    assert runtime_cycle_lines(settings=settings, state=state, view=view) == [
        "Runtime: active",
        "Runtime Mode: operation",
        "Watched Symbols: AAPL, MSFT",
        "Current Symbol: AAPL",
        "Cycle: 4",
        "Interval / Lookback: 1d / 90d",
        "Current Note: Working.",
    ]
    assert agent_activity_lines(activity)[:3] == [
        "Current Stage: manager",
        "Stage Status: running",
        "Stage Message: Sizing order.",
    ]
    assert broker_gate_lines(
        broker={"backend": "paper", "state": "ready", "kill_switch_active": False},
        paper_operations={"allowed": True},
        copy=get_ui_text("en"),
    ) == [
        "Broker Backend: paper",
        "Broker State: ready",
        "Kill Switch: inactive",
        "V1 Paper Gate: allowed",
    ]
    assert last_outcome_lines(activity) == [
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
    assert last_outcome_lines(empty_activity) == [
        "Last Outcome: Waiting for a completed symbol, exit, or service result."
    ]


@pytest.mark.parametrize(
    ("max_cycles_input", "expected_max_cycles"),
    (("", None), ("3", 3), ("0", None), ("-1", None), ("abc", None)),
)
def test_prompt_service_launch_options_normalizes_max_cycles(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    max_cycles_input: str,
    expected_max_cycles: int | None,
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_poll_seconds=15,
    )

    def ask_continuous(*_args: object, **_kwargs: object) -> bool:
        return True

    def ask_poll_seconds(*_args: object, **_kwargs: object) -> int:
        return 15

    def ask_max_cycles(*_args: object, **_kwargs: object) -> str:
        return max_cycles_input

    monkeypatch.setattr(runtime_module.Confirm, "ask", ask_continuous)
    monkeypatch.setattr(runtime_module.IntPrompt, "ask", ask_poll_seconds)
    monkeypatch.setattr(runtime_module.Prompt, "ask", ask_max_cycles)

    assert runtime_module.prompt_service_launch_options(settings) == (
        True,
        15,
        expected_max_cycles,
    )


def test_terminal_tui_tables_and_menu_actions(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """
    Exercise TUI table rendering and main-menu action dispatch for terminal UI helpers.

    Renders runtime, system, memory explorer, and menu tables to a recorded Console and asserts presence and absence of expected output fragments. Also verifies that run_main_menu_action invokes the correct action callbacks and that it signals whether the menu loop should continue.
    """
    monkeypatch.setenv(UI_LOCALE_ENV, "en")
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
    console.print(runtime_state_table(None))
    console.print(runtime_state_table(state))
    console.print(
        system_status_table(
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
        memory_explorer_table(
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
        menu_table(
            "Test Menu",
            [
                TuiMenuAction("1", "Render thing", "Thing", lambda _db: None),
                ("2", "Back"),
            ],
        )
    )
    actions = main_menu_actions()
    console.print(main_menu_table(actions))
    output = console.export_text()

    assert "No runtime state recorded yet." in output
    assert "Runtime active" not in output
    assert "System Status" in output
    assert "Base URL" in output
    assert "Decision Evidence Explorer" in output
    assert "AAPL" in output
    assert "Test Menu" in output
    assert "Configure investment preferences" in output

    called: list[str] = []
    keep_running = run_main_menu_action(
        settings,
        "1",
        actions=[
            type(actions[0])("1", "Do work", lambda _settings: called.append("work")),
            type(actions[0])(
                "2", "Exit", lambda _settings: called.append("exit"), True
            ),
        ],
    )
    assert keep_running is True
    assert called == ["work"]
    keep_running = run_main_menu_action(
        settings,
        "2",
        actions=[
            type(actions[0])("1", "Do work", lambda _settings: called.append("work")),
            type(actions[0])(
                "2", "Exit", lambda _settings: called.append("exit"), True
            ),
        ],
    )
    assert keep_running is False
    assert called[-1] == "exit"


def test_tui_status_renderers_cover_diagnostics_and_readiness(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    import agentic_trader.tui_modules.status_diagnostics as diagnostics_module
    import agentic_trader.tui_modules.status_readiness as readiness_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    recording = Console(record=True, width=160)
    monkeypatch.setattr(diagnostics_module, "console", recording)
    monkeypatch.setattr(readiness_module, "console", recording)

    def broker_payload(_settings: Settings) -> dict[str, object]:
        return {
            "backend": "paper",
            "adapter_name": "paper-adapter",
            "state": "ready",
            "execution_mode": "paper",
            "external_paper": True,
            "live_execution_enabled": False,
            "kill_switch_active": False,
            "live_requested": False,
            "live_ready": True,
            "alpaca_paper_trading_enabled": True,
            "alpaca_paper_endpoint": "https://paper-api.alpaca.markets",
            "alpaca_data_feed": "iex",
            "alpaca_credentials_configured": True,
            "message": "ready",
            "healthcheck": {
                "message": "healthy",
                "blocking_reasons": ["none"],
            },
        }

    def provider_payload(_settings: Settings) -> dict[str, object]:
        return {
            "llm": {
                "provider": "ollama",
                "default_model": "qwen3:8b",
                "base_url": "http://localhost:11434/v1",
            },
            "market_data": {
                "selected_provider": "yahoo",
                "selected_role": "fallback",
            },
            "news": {"mode": "offline"},
            "alpaca": {
                "paper_endpoint": "paper",
                "data_feed": "iex",
                "credentials_configured": False,
            },
            "warnings": ["missing alpaca credentials"],
            "providers": [
                {
                    "provider_id": "yahoo",
                    "provider_type": "market",
                    "role": "fallback",
                    "enabled": True,
                    "api_key_ready": "n/a",
                    "freshness": "fresh",
                }
            ],
        }

    def readiness_payload(
        _settings: Settings, *, check_provider: bool
    ) -> dict[str, object]:
        assert check_provider is False
        return {
            "summary": "Paper operations ready",
            "paper_operations": {
                "allowed": True,
                "checks": [
                    {
                        "name": "paper gate",
                        "passed": True,
                        "blocking": False,
                        "details": "ready",
                    }
                ],
            },
            "alpaca_paper": {
                "checks": [
                    {
                        "name": "credentials",
                        "passed": False,
                        "blocking": True,
                        "details": "missing",
                    }
                ],
            },
        }

    monkeypatch.setattr(diagnostics_module, "broker_runtime_payload", broker_payload)
    monkeypatch.setattr(
        diagnostics_module,
        "provider_diagnostics_payload",
        provider_payload,
    )
    monkeypatch.setattr(
        readiness_module,
        "v1_readiness_payload",
        readiness_payload,
    )

    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    diagnostics_module.render_broker_status(settings)
    diagnostics_module.render_provider_diagnostics(settings)
    readiness_module.render_v1_readiness(settings)
    readiness_module.render_readiness_table(
        "Empty Checks",
        {"checks": "not-a-list"},
    )

    output = recording.export_text()
    assert "Broker Status" in output
    assert "healthy" in output
    assert "Provider Diagnostics" in output
    assert "missing alpaca credentials" in output
    assert "Provider Source Ladder" in output
    assert "V1 Readiness" in output
    assert "Paper Operation Checks" in output
    assert "Alpaca Paper Checks" in output


def test_tui_secondary_menus_dispatch_actions(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    import agentic_trader.tui_modules.portfolio as portfolio_module
    import agentic_trader.tui_modules.research as research_module
    import agentic_trader.tui_modules.review as review_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    recording = Console(record=True, width=140)
    called: list[str] = []

    def run_action(_settings: Settings, action: TuiMenuAction) -> None:
        called.append(action.key)

    for module in (portfolio_module, research_module, review_module):
        monkeypatch.setattr(module, "console", recording)
        monkeypatch.setattr(module, "run_readonly_db_menu_action", run_action)

    def portfolio_renderable_stub(_db: TradingDatabase) -> str:
        return "portfolio-renderable"

    def risk_report_table_stub(_db: TradingDatabase) -> str:
        return "risk"

    def trade_journal_table_stub(_db: TradingDatabase, *, limit: int) -> str:
        return f"journal-{limit}"

    monkeypatch.setattr(
        portfolio_module,
        "portfolio_renderable",
        portfolio_renderable_stub,
    )
    monkeypatch.setattr(
        portfolio_module,
        "risk_report_table",
        risk_report_table_stub,
    )
    monkeypatch.setattr(
        portfolio_module,
        "trade_journal_table",
        trade_journal_table_stub,
    )
    fake_trading_db = cast(TradingDatabase, object())
    portfolio_module.show_portfolio(fake_trading_db)
    portfolio_module.show_trade_journal(fake_trading_db)
    portfolio_module.show_risk_report(fake_trading_db)

    prompt_values = iter(["1", "", "4"])

    def next_portfolio_prompt(*_args: object, **_kwargs: object) -> str:
        return next(prompt_values)

    monkeypatch.setattr(
        portfolio_module.Prompt,
        "ask",
        next_portfolio_prompt,
    )
    portfolio_module.portfolio_menu(settings)

    prompt_values = iter(["2", "", "3"])

    def next_research_prompt(*_args: object, **_kwargs: object) -> str:
        return next(prompt_values)

    def read_events(_settings: Settings, *, limit: int) -> list[str]:
        return [f"event-{limit}"]

    def render_events(events: list[str]) -> None:
        called.append(f"events:{events[0]}")

    monkeypatch.setattr(
        research_module.Prompt,
        "ask",
        next_research_prompt,
    )
    monkeypatch.setattr(research_module, "read_service_events", read_events)
    monkeypatch.setattr(research_module, "render_runtime_events", render_events)
    research_module.research_menu(settings)

    prompt_values = iter(["1", "", "3"])

    def next_review_prompt(*_args: object, **_kwargs: object) -> str:
        return next(prompt_values)

    monkeypatch.setattr(
        review_module.Prompt,
        "ask",
        next_review_prompt,
    )
    review_module.review_menu(settings)

    output = recording.export_text()
    assert "portfolio-renderable" in output
    assert "journal-20" in output
    assert called == ["1", "2", "events:event-6", "1"]


def test_tui_review_and_research_renderers_handle_records(
    monkeypatch: MonkeyPatch,
) -> None:
    import agentic_trader.tui_modules.research as research_module
    import agentic_trader.tui_modules.review as review_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    recording = Console(record=True, width=140)
    monkeypatch.setattr(review_module, "console", recording)
    monkeypatch.setattr(research_module, "console", recording)

    class Artifacts:
        agent_traces = [
            SimpleNamespace(role="manager", model_name="qwen3:8b", used_fallback=False)
        ]

        def model_dump_json(self, *, indent: int) -> str:
            return f'{{\n{" " * indent}"ok": true\n}}'

    def no_latest_run() -> None:
        return None

    def latest_run() -> SimpleNamespace:
        return SimpleNamespace(run_id="run-1", artifacts=Artifacts())

    empty_db = cast(TradingDatabase, SimpleNamespace(latest_run=no_latest_run))
    record_db = cast(TradingDatabase, SimpleNamespace(latest_run=latest_run))
    review_module.show_latest_run_review(empty_db)
    review_module.show_latest_run_trace(empty_db)
    review_module.show_latest_run_review(record_db)
    review_module.show_latest_run_trace(record_db)
    console = Console(record=True, width=140)
    console.print(
        research_module.memory_explorer_table(
            [
                HistoricalMemoryMatch(
                    run_id="run-1",
                    created_at="2026-05-15T00:00:00+00:00",
                    symbol="AAPL",
                    similarity_score=0.42,
                    regime="range",
                    strategy_family="mean_reversion",
                    manager_bias="hold",
                    approved=False,
                    summary="flat tape",
                )
            ]
        )
    )

    output = recording.export_text() + console.export_text()
    assert "No persisted runs are available to review." in output
    assert "Latest Run Review / run-1" in output
    assert "Agent Trace / run-1" in output
    assert "qwen3:8b" in output
    assert "AAPL" in output


def test_configure_preferences_and_edit_action_paths(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    import agentic_trader.tui_modules.preferences as preferences_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    recording = Console(record=True, width=140)
    monkeypatch.setattr(preferences_module, "console", recording)

    class FakeDb:
        closed = False

        def __init__(self) -> None:
            self.saved: InvestmentPreferences | str | None = None

        def load_preferences(self) -> InvestmentPreferences:
            return InvestmentPreferences()

        def save_preferences(self, preferences: InvestmentPreferences) -> None:
            self.saved = preferences

        def close(self) -> None:
            self.closed = True

    fake_db = FakeDb()
    answers = iter(
        [
            "us, eu",
            "",
            "usd, eur",
            "technology, healthcare",
            "aggressive",
            "intraday",
            "trend_biased",
            "disciplined",
            "direct",
            "strict",
            "protective",
            "Prefer liquid names.",
        ]
    )
    def next_preference_prompt(*_args: object, **_kwargs: object) -> str:
        return next(answers)

    monkeypatch.setattr(preferences_module.Prompt, "ask", next_preference_prompt)
    preferences_module.configure_preferences(cast(TradingDatabase, fake_db))

    assert isinstance(fake_db.saved, InvestmentPreferences)
    assert fake_db.saved.regions == ["US", "EU"]
    assert fake_db.saved.exchanges == ["NASDAQ", "NYSE"]
    assert fake_db.saved.currencies == ["USD", "EUR"]
    assert fake_db.saved.sectors == ["TECHNOLOGY", "HEALTHCARE"]
    assert fake_db.saved.risk_profile == "aggressive"
    assert fake_db.saved.notes == "Prefer liquid names."

    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    opened_db = FakeDb()

    def open_fake_db(_settings: Settings, *, read_only: bool) -> TradingDatabase:
        assert read_only is False
        return cast(TradingDatabase, opened_db)

    def mark_edited(db: TradingDatabase) -> None:
        cast(FakeDb, db).saved = "edited"

    monkeypatch.setattr(preferences_module, "open_db", open_fake_db)
    monkeypatch.setattr(preferences_module, "configure_preferences", mark_edited)
    preferences_module.edit_preferences_action(settings)
    assert opened_db.saved == "edited"
    assert opened_db.closed is True

    def open_locked_db(_settings: Settings, *, read_only: bool) -> TradingDatabase:
        assert read_only is False
        raise RuntimeError("locked")

    def blank_prompt(*_args: object, **_kwargs: object) -> str:
        return ""

    monkeypatch.setattr(preferences_module, "open_db", open_locked_db)
    monkeypatch.setattr(preferences_module.Prompt, "ask", blank_prompt)
    preferences_module.edit_preferences_action(settings)

    output = recording.export_text()
    assert "Preferences saved." in output
    assert "locked" in output


# ---------------------------------------------------------------------------
# Tests for PR: banner() and exit_cleanly() use t() translation facade
# ---------------------------------------------------------------------------


def test_banner_wide_contains_translated_control_room_title(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    banner() in wide-terminal mode renders the translated title_control_room and
    the full subtitle from message_control_room_full_subtitle.
    """
    import agentic_trader.tui_modules.common as common_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    # Force the module-level console to report a wide width so the full art path is taken.
    fake_console = SimpleNamespace(width=140)
    monkeypatch.setattr(common_module, "console", fake_console)

    panel = banner()

    recording = Console(record=True, width=160)
    recording.print(panel)
    output = recording.export_text()

    assert "Agentic Trader Control Room" in output
    assert "Strict LLM gate, saved preferences" in output


def test_banner_narrow_contains_compact_control_room_title(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    banner() in narrow-terminal mode renders the uppercased title_control_room
    and the compact subtitle from message_control_room_compact_subtitle.
    """
    import agentic_trader.tui_modules.common as common_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    # Force the module-level console to report a narrow width so the compact path is taken.
    fake_console = SimpleNamespace(width=80)
    monkeypatch.setattr(common_module, "console", fake_console)

    panel = banner()

    recording = Console(record=True, width=100)
    recording.print(panel)
    output = recording.export_text()

    assert "AGENTIC TRADER" in output
    assert "CONTROL ROOM" in output
    assert "Strict LLM gate, portfolio state, runtime controls." in output


def test_banner_wide_turkish_locale_uses_translated_title(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    banner() wide path uses the Turkish title_control_room when locale is TR.
    """
    import agentic_trader.tui_modules.common as common_module

    monkeypatch.setenv(UI_LOCALE_ENV, "tr")
    fake_console = SimpleNamespace(width=140)
    monkeypatch.setattr(common_module, "console", fake_console)

    panel = banner()

    recording = Console(record=True, width=160)
    recording.print(panel)
    output = recording.export_text()

    assert "Agentic Trader Kontrol Odası" in output


def test_exit_cleanly_renders_closed_message_panel(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    exit_cleanly() should print a panel containing the translated
    message_control_room_closed string via the t() facade.
    """
    import agentic_trader.tui_modules.common as common_module

    monkeypatch.setenv(UI_LOCALE_ENV, "en")
    recording = Console(record=True, width=120)
    monkeypatch.setattr(common_module, "console", recording)

    exit_cleanly()

    output = recording.export_text()
    assert "Control room closed cleanly." in output


def test_exit_cleanly_turkish_locale_renders_corrected_message(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    exit_cleanly() in TR locale uses the fixed Turkish message with proper diacritics.
    """
    import agentic_trader.tui_modules.common as common_module

    monkeypatch.setenv(UI_LOCALE_ENV, "tr")
    recording = Console(record=True, width=120)
    monkeypatch.setattr(common_module, "console", recording)

    exit_cleanly()

    output = recording.export_text()
    # The PR fixed "kapandi" → "kapandı" (with dotless-i diacritic)
    assert "kapandı" in output
