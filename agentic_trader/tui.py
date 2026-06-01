import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Sequence, cast

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.status import Status
from rich.table import Table

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.config import Settings, get_settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.runtime_feed import (
    read_service_events,
    read_service_state,
    request_stop,
)
from agentic_trader.runtime_status import (
    is_process_alive,
)
from agentic_trader.schemas import (
    AgentProfile,
    AgentTone,
    BehaviorPreset,
    ChatPersona,
    HistoricalMemoryMatch,
    InterventionStyle,
    InvestmentPreferences,
    OperatorInstruction,
    RiskProfile,
    StrictnessPreset,
    TradeStyle,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_monitor import (
    build_monitor_renderable as _build_monitor_renderable,
)
from agentic_trader.tui_monitor import (
    run_live_monitor,
)
from agentic_trader.tui_monitor_sections import (
    agent_activity_lines as _export_agent_activity_lines,
)
from agentic_trader.tui_monitor_sections import (
    agent_activity_table as _export_agent_activity_table,
)
from agentic_trader.tui_monitor_sections import (
    broker_gate_lines as _export_broker_gate_lines,
)
from agentic_trader.tui_monitor_sections import (
    last_outcome_lines as _export_last_outcome_lines,
)
from agentic_trader.tui_monitor_sections import (
    observer_mode_panel,
    portfolio_renderable,
    render_preferences,
    render_recent_runs,
    render_runtime_events,
    risk_report_table,
)
from agentic_trader.tui_monitor_sections import (
    runtime_cycle_lines as _export_runtime_cycle_lines,
)
from agentic_trader.tui_monitor_sections import (
    runtime_state_table as _export_runtime_state_table,
)
from agentic_trader.tui_monitor_sections import (
    safe_open_read_db,
)
from agentic_trader.tui_monitor_sections import (
    system_status_table as _export_system_status_table,
)
from agentic_trader.tui_monitor_sections import (
    trade_journal_table,
)
from agentic_trader.tui_status import (
    render_broker_status,
    render_compact_status,
    render_provider_diagnostics,
    render_status,
    render_v1_readiness,
)
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_BIAS,
    LABEL_CREATED,
    LABEL_FALLBACK,
    LABEL_KEY,
    LABEL_MODEL,
    LABEL_OBSERVER_MODE,
    LABEL_REGIME,
    LABEL_ROLE,
    LABEL_SCORE,
    LABEL_STOP_REQUESTED,
    LABEL_STRATEGY,
    LABEL_SYMBOL,
    MENU_ACTION_BACK,
    MENU_ACTION_BROKER_STATUS,
    MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
    MENU_ACTION_DOCTOR_SYSTEM_CHECKS,
    MENU_ACTION_EXIT,
    MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
    MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
    MENU_ACTION_OPEN_LIVE_MONITOR,
    MENU_ACTION_OPEN_MEMORY_EXPLORER,
    MENU_ACTION_OPEN_OPERATOR_CHAT,
    MENU_ACTION_OPERATOR_DESK,
    MENU_ACTION_PARSE_OPERATOR_INSTRUCTION,
    MENU_ACTION_PORTFOLIO_AND_RISK,
    MENU_ACTION_PROVIDER_DIAGNOSTICS,
    MENU_ACTION_REQUEST_ORCHESTRATOR_STOP,
    MENU_ACTION_RESEARCH_AND_MEMORY,
    MENU_ACTION_REVIEW_AND_TRACE,
    MENU_ACTION_RUNTIME_CONTROL,
    MENU_ACTION_SHOW_DAILY_RISK_REPORT,
    MENU_ACTION_SHOW_PAPER_PORTFOLIO,
    MENU_ACTION_SHOW_RECENT_RUNS_AND_EVENTS,
    MENU_ACTION_SHOW_TRADE_JOURNAL,
    MENU_ACTION_START_ONE_STRICT_AGENT_CYCLE,
    MENU_ACTION_START_ORCHESTRATOR_SERVICE,
    MENU_ACTION_V1_READINESS_GATES,
    MESSAGE_ACTION_CANCELLED_RETURNING,
    MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
    MESSAGE_CHAT_EXIT_HINT,
    MESSAGE_CONTROL_ROOM_CLOSED,
    MESSAGE_FINAL_STAGE_UPDATE,
    MESSAGE_NO_PERSISTED_RUNS_REVIEW,
    MESSAGE_NO_PERSISTED_RUNS_TRACE,
    MESSAGE_PREFERENCES_SAVED,
    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE,
    MESSAGE_PREPARING_SYMBOL,
    MESSAGE_SERVICE_SPAWNED_BACKGROUND,
    MESSAGE_SERVICE_STOP_REQUESTED,
    MESSAGE_STAGE_UPDATE,
    MESSAGE_STALE_RUNTIME_PID,
    PROMPT_APPLY_PREFERENCE_UPDATE,
    PROMPT_CHAT_PERSONA,
    PROMPT_CONTINUE,
    PROMPT_CONTINUOUS_MODE,
    PROMPT_INSTRUCTION,
    PROMPT_MAX_CYCLES,
    PROMPT_OPEN_LIVE_MONITOR_NOW,
    PROMPT_POLL_INTERVAL_SECONDS,
    PROMPT_REFRESH_SECONDS,
    PROMPT_SELECT_ACTION,
    PROMPT_YOU,
    STYLE_KEY_COLUMN,
    TITLE_ACTION_FAILED,
    TITLE_AGENT_TRACE_FOR_RUN,
    TITLE_CANCELLED,
    TITLE_CHAT,
    TITLE_DAILY_RISK_REPORT,
    TITLE_DECISION_EVIDENCE_EXPLORER,
    TITLE_EXIT,
    TITLE_INSTRUCTION_APPLICATION,
    TITLE_LATEST_RUN_REVIEW,
    TITLE_MAIN_MENU,
    TITLE_MEMORY_EXPLORER,
    TITLE_NOT_RUNNING,
    TITLE_OPERATOR_CHAT_MEMORY_CONTEXT,
    TITLE_OPERATOR_DESK,
    TITLE_PAPER_PORTFOLIO,
    TITLE_PARSED_OPERATOR_INSTRUCTION,
    TITLE_PORTFOLIO_AND_RISK,
    TITLE_PREFERENCE_EDITING,
    TITLE_RECENT_RUNS,
    TITLE_RESEARCH_AND_MEMORY,
    TITLE_REVIEW_AND_TRACE,
    TITLE_RUN_COMPLETED,
    TITLE_RUN_REVIEW,
    TITLE_RUNTIME_CONTROL,
    TITLE_SAVED,
    TITLE_SERVICE_SPAWNED,
    TITLE_STALE_RUNTIME,
    TITLE_TRACE,
    TITLE_TRADE_JOURNAL,
    TITLE_UPDATED_PREFERENCES,
)
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, start_background_service

console = Console()


@dataclass(frozen=True, slots=True)
class TuiMenuAction:
    key: str
    label: str
    observer_title: str
    renderer: Callable[[TradingDatabase], None]


@dataclass(frozen=True, slots=True)
class TuiMainMenuAction:
    key: str
    label: str
    handler: Callable[[Settings], None]
    exits_menu: bool = False


def _open_db(settings: Settings, *, read_only: bool) -> TradingDatabase:
    """
    Open a TradingDatabase configured from the provided Settings.

    Parameters:
        read_only (bool): If true, open the database in read-only mode; otherwise open for read/write.

    Returns:
        TradingDatabase: Database instance initialized with the given settings and read-only flag.
    """
    return TradingDatabase(settings, read_only=read_only)


def _style_key(text: str) -> str:
    """
    Format a string as a styled key using the STYLE_KEY_COLUMN Rich markup.

    Parameters:
        text (str): The text to format as a styled key.

    Returns:
        str: The input string wrapped in STYLE_KEY_COLUMN Rich markup tags.
    """
    return f"[{STYLE_KEY_COLUMN}]{text}[/{STYLE_KEY_COLUMN}]"


def _banner() -> Panel:
    """
    Render the top banner panel for the Agentic Trader TUI.

    When the console width is less than 120 characters, uses a compact single-line banner; otherwise uses an ASCII-art header with a subtitle.

    Returns:
        Panel: A Rich Panel containing the banner renderable.
    """
    if console.width < 120:
        compact = (
            "[bold green]AGENTIC TRADER[/bold green] "
            "[cyan]// CONTROL ROOM[/cyan]\n"
            "[dim]Strict LLM gate, portfolio state, runtime controls.[/dim]"
        )
        return Panel(Align.center(compact), border_style="bright_blue")

    art = r"""
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗    ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║            ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║            ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗       ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
"""
    subtitle = (
        "[bold cyan]Agentic Trader control room[/bold cyan]\n"
        "[dim]Strict LLM gate, saved preferences, portfolio state, recent runs, and launch controls.[/dim]"
    )
    return Panel(f"[green]{art}[/green]\n{subtitle}", border_style="bright_blue")


def _exit_cleanly() -> None:
    """
    Display an exit panel indicating the control room closed cleanly.

    Prints a panel using the standard exit title and message.
    """
    console.print(
        Panel(MESSAGE_CONTROL_ROOM_CLOSED, title=TITLE_EXIT, border_style="blue")
    )


def _split_csv(value: str) -> list[str]:
    """
    Parse a comma-separated string into a list of trimmed, uppercased tokens.

    Parameters:
        value (str): Comma-separated input string.

    Returns:
        list[str]: Tokens from `value` with surrounding whitespace removed, converted to uppercase, and with empty segments omitted.
    """
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _configure_preferences(db: TradingDatabase) -> None:
    """
    Prompt the operator to review and update investment preferences and save the changes.

    Prompts for each preference field (list fields accept comma-separated values; choice fields present fixed options), preserves existing list values when a list input is left empty, constructs an InvestmentPreferences object from the responses, and persists it to the provided TradingDatabase.
    """
    current = db.load_preferences()
    console.print(render_preferences(current))
    regions = Prompt.ask(
        "Regions (comma-separated)", default=", ".join(current.regions)
    )
    exchanges = Prompt.ask(
        "Exchanges (comma-separated)", default=", ".join(current.exchanges)
    )
    currencies = Prompt.ask(
        "Currencies (comma-separated)", default=", ".join(current.currencies)
    )
    sectors = Prompt.ask(
        "Sectors (comma-separated, optional)",
        default=", ".join(current.sectors),
    )
    risk_profile = Prompt.ask(
        "Risk profile",
        choices=["conservative", "balanced", "aggressive"],
        default=current.risk_profile,
    )
    trade_style = Prompt.ask(
        "Trade style",
        choices=["swing", "position", "intraday"],
        default=current.trade_style,
    )
    behavior_preset = Prompt.ask(
        "Behavior preset",
        choices=["balanced_core", "trend_biased", "contrarian", "capital_preservation"],
        default=current.behavior_preset,
    )
    agent_profile = Prompt.ask(
        "Agent profile",
        choices=["neutral", "disciplined", "aggressive", "explanatory"],
        default=current.agent_profile,
    )
    agent_tone = Prompt.ask(
        "Agent tone",
        choices=["neutral", "supportive", "direct", "forensic"],
        default=current.agent_tone,
    )
    strictness_preset = Prompt.ask(
        "Strictness preset",
        choices=["standard", "strict", "paranoid"],
        default=current.strictness_preset,
    )
    intervention_style = Prompt.ask(
        "Intervention style",
        choices=["hands_off", "balanced", "protective"],
        default=current.intervention_style,
    )
    notes = Prompt.ask("Notes", default=current.notes)
    updated = InvestmentPreferences(
        regions=_split_csv(regions) or current.regions,
        exchanges=_split_csv(exchanges) or current.exchanges,
        currencies=_split_csv(currencies) or current.currencies,
        sectors=_split_csv(sectors),
        risk_profile=cast(RiskProfile, risk_profile),
        trade_style=cast(TradeStyle, trade_style),
        behavior_preset=cast(BehaviorPreset, behavior_preset),
        agent_profile=cast(AgentProfile, agent_profile),
        agent_tone=cast(AgentTone, agent_tone),
        strictness_preset=cast(StrictnessPreset, strictness_preset),
        intervention_style=cast(InterventionStyle, intervention_style),
        notes=notes,
    )
    db.save_preferences(updated)
    console.print(
        Panel(MESSAGE_PREFERENCES_SAVED, title=TITLE_SAVED, border_style="green")
    )


def _show_portfolio(db: TradingDatabase) -> None:
    """
    Render the portfolio summary, positions list, and daily risk report to the console.

    Prints a combined portfolio renderable (summary plus positions, with a placeholder when no open positions exist) followed by the account risk report.
    """
    console.print(portfolio_renderable(db))
    console.print(risk_report_table(db))


def _show_trade_journal(db: TradingDatabase) -> None:
    console.print(trade_journal_table(db, limit=20))


def _show_risk_report(db: TradingDatabase) -> None:
    console.print(risk_report_table(db))


def _show_latest_run_review(db: TradingDatabase) -> None:
    """
    Display the latest persisted run review or a notice if none exists.

    If a persisted run is available, prints the run's artifacts as pretty-printed JSON with the run id in the panel title. If no persisted run exists, prints a notice indicating there are no persisted runs to review.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                MESSAGE_NO_PERSISTED_RUNS_REVIEW,
                title=TITLE_RUN_REVIEW,
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            record.artifacts.model_dump_json(indent=2),
            title=TITLE_LATEST_RUN_REVIEW.format(run_id=record.run_id),
            border_style="cyan",
        )
    )


def _memory_explorer_table(matches: Sequence[HistoricalMemoryMatch]) -> Table:
    """
    Builds a Rich Table showing historical memory matches for the decision evidence explorer.

    Parameters:
        matches (Sequence[HistoricalMemoryMatch]): Sequence of memory match records to display. When empty, the table contains a single placeholder row.

    Returns:
        Table: A Rich Table with columns "Created", "Symbol", "Score", "Regime", "Strategy", and "Bias". The `Score` column is formatted to two decimal places.
    """
    table = Table(title=TITLE_DECISION_EVIDENCE_EXPLORER)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_SCORE)
    table.add_column(LABEL_REGIME)
    table.add_column(LABEL_STRATEGY)
    table.add_column(LABEL_BIAS)
    if not matches:
        table.add_row("-", "-", "-", "-", "-", "-")
        return table

    for match in matches:
        table.add_row(
            match.created_at,
            match.symbol,
            f"{match.similarity_score:.2f}",
            match.regime,
            match.strategy_family,
            match.manager_bias,
        )
    return table


def _show_memory_explorer(_settings: Settings, db: TradingDatabase) -> None:
    """
    Launch an interactive memory explorer that prompts for symbol, interval, lookback, and match limit, then prints a table of similar historical memories.

    Parameters:
        _settings (Settings): Unused in this view; kept for API symmetry.
        db (TradingDatabase): Database used to retrieve and rank matching memories; results are printed to the console.
    """
    symbol = Prompt.ask("Symbol", default="AAPL").strip().upper()
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    limit = IntPrompt.ask("Matches", default=5)
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(
        frame, symbol=symbol, interval=interval, lookback=lookback
    )
    matches = retrieve_similar_memories(db, snapshot, limit=limit)

    console.print(_memory_explorer_table(matches))


def _show_latest_run_trace(db: TradingDatabase) -> None:
    """
    Display the most recent run's agent trace or an informational panel when none exists.

    Prints a table listing each agent trace's role, model name, and whether a fallback was used for the latest recorded run; if no persisted run is available, prints a yellow panel stating that no run trace is present.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                MESSAGE_NO_PERSISTED_RUNS_TRACE,
                title=TITLE_TRACE,
                border_style="yellow",
            )
        )
        return
    table = Table(title=TITLE_AGENT_TRACE_FOR_RUN.format(run_id=record.run_id))
    table.add_column(LABEL_ROLE)
    table.add_column(LABEL_MODEL)
    table.add_column(LABEL_FALLBACK)
    for trace in record.artifacts.agent_traces:
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback))
    console.print(table)


def _select_chat_persona() -> ChatPersona:
    """
    Prompt the operator to choose a chat persona for agent responses.

    Returns:
        ChatPersona: The chosen persona key; one of "operator_liaison", "regime_analyst", "strategy_selector", "risk_steward", or "portfolio_manager" (defaults to "operator_liaison").
    """
    return cast(
        ChatPersona,
        Prompt.ask(
            PROMPT_CHAT_PERSONA,
            choices=[
                "operator_liaison",
                "regime_analyst",
                "strategy_selector",
                "risk_steward",
                "portfolio_manager",
            ],
            default="operator_liaison",
        ),
    )


def _render_chat_transcript(
    *, persona: ChatPersona, transcript: Sequence[tuple[str, str]]
) -> None:
    """
    Render the chat transcript and an exit hint panel for the given persona to the console.

    Clears the terminal, prints a banner and an exit-hint panel titled with the persona, then displays up to the last eight messages from the transcript as role-labeled panels.

    Parameters:
        persona (ChatPersona): The chat persona used for the exit-hint panel title.
        transcript (Sequence[tuple[str, str]]): Sequence of (role, message) pairs; each role (e.g., "operator") is used as the panel title for its message.
    """
    console.clear()
    console.print(_banner())
    console.print(
        Panel(
            MESSAGE_CHAT_EXIT_HINT,
            title=TITLE_CHAT.format(persona=persona),
            border_style="cyan",
        )
    )
    for role, message in transcript[-8:]:
        border = "bright_blue" if role == "operator" else "green"
        console.print(Panel(message, title=role, border_style=border))


def _chat_screen(settings: Settings, db: TradingDatabase) -> None:
    """
    Open an interactive operator chat session with a selectable persona.

    Displays the chat transcript, prompts the operator for input, sends messages to the configured LLM persona (via the chat backend), and appends persona replies to the transcript. The session ends when the operator enters "/exit", "exit", or "quit".
    """
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    persona = _select_chat_persona()
    transcript: list[tuple[str, str]] = []
    while True:
        _render_chat_transcript(persona=persona, transcript=transcript)
        user_message = Prompt.ask(PROMPT_YOU)
        if user_message.strip().lower() in {"/exit", "exit", "quit"}:
            return
        transcript.append(("operator", user_message))
        response = chat_with_persona(
            llm=llm,
            db=db,
            settings=settings,
            persona=persona,
            user_message=user_message,
        )
        transcript.append((persona, response))


def _render_instruction_result(instruction: OperatorInstruction) -> None:
    """
    Render the parsed operator instruction as a JSON panel in the console.

    Parameters:
        instruction (OperatorInstruction): The parsed operator instruction to display.
    """
    console.print(
        Panel(
            instruction.model_dump_json(indent=2),
            title=TITLE_PARSED_OPERATOR_INSTRUCTION,
            border_style="cyan",
        )
    )


def _apply_instruction_update_if_confirmed(
    instruction: OperatorInstruction, db: TradingDatabase
) -> None:
    """
    Apply the parsed operator instruction's preference update when the instruction requests it and the operator confirms.

    If `instruction.should_update_preferences` is true and the operator confirms the prompt, persists the preference update to `db` and prints the updated preferences as a JSON panel.

    Parameters:
        instruction (OperatorInstruction): Parsed operator instruction containing `should_update_preferences` and `preference_update`.
    """
    if not instruction.should_update_preferences:
        return
    if not Confirm.ask(PROMPT_APPLY_PREFERENCE_UPDATE, default=False):
        return

    updated = apply_preference_update(db, instruction.preference_update)
    console.print(
        Panel(
            updated.model_dump_json(indent=2),
            title=TITLE_UPDATED_PREFERENCES,
            border_style="green",
        )
    )


def _instruction_screen(settings: Settings, db: TradingDatabase) -> None:
    """
    Parse an operator instruction from the prompt, display the interpreted result, and apply any confirmed preference update.

    Prompts the operator for a free-form instruction, interprets it using the local LLM and the provided database, renders the parsed `OperatorInstruction`, and—if the interpretation indicates a preferences update and the operator confirms—applies that update to the database.
    """
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    message = Prompt.ask(PROMPT_INSTRUCTION)
    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=message,
        allow_fallback=True,
    )
    _render_instruction_result(instruction)
    _apply_instruction_update_if_confirmed(instruction, db)


def _strict_one_shot(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    """
    Execute a single strict agent trading cycle for each given symbol and persist and display the resulting run artifacts.

    Parameters:
        settings (Settings): Application settings and environment configuration.
        symbols (Sequence[str]): Symbols to run the cycle for.
        interval (str): Price data interval identifier (e.g., "1m", "5m", "1d").
        lookback (str): Lookback window specification for historical data (format depends on caller).
    """
    ensure_llm_ready(settings)
    for symbol in symbols:
        _run_one_shot_symbol(settings, symbol, interval, lookback)


def _run_one_shot_symbol(
    settings: Settings, symbol: str, interval: str, lookback: str
) -> None:
    """
    Execute a strict one-shot trading cycle for a single symbol and display the results.

    Runs a single strict trading cycle using the provided settings, symbol, interval, and lookback, persists the resulting run artifacts, and prints a completion panel that includes the final status message, run artifacts, and the persisted order id.

    Parameters:
        settings (Settings): Application settings used to configure the run and persistence.
        symbol (str): Trading symbol to execute the cycle for.
        interval (str): Time interval/granularity for the trading cycle (e.g., "1m", "1h").
        lookback (str): Lookback window used by the trading cycle (format depends on application conventions).
    """
    latest_message = MESSAGE_PREPARING_SYMBOL.format(symbol=symbol)
    with console.status(_style_key(latest_message), spinner="dots") as status:

        def _progress(
            stage: str,
            event: str,
            message: str,
            current_status: Status = status,
        ) -> None:
            """
            Update the live progress status and record the latest stage message.

            Parameters:
                stage (str): Human-readable name of the current processing stage.
                event (str): Event identifier associated with the progress update (accepted but not used).
                message (str): Short message describing the current progress or state within the stage.
                current_status (Status): Rich `Status` object whose display text will be updated.
            """
            nonlocal latest_message
            latest_message = MESSAGE_STAGE_UPDATE.format(stage=stage, message=message)
            current_status.update(_style_key(latest_message))

        artifacts = run_once(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            allow_fallback=False,
            progress_callback=_progress,
        )

    order_id = persist_run(settings=settings, artifacts=artifacts)
    console.print(
        Panel(
            MESSAGE_FINAL_STAGE_UPDATE.format(
                latest_message=latest_message,
                artifacts_json=json.dumps(artifacts.model_dump(mode="json"), indent=2),
            ),
            title=TITLE_RUN_COMPLETED.format(symbol=symbol, order_id=order_id),
            border_style="green",
        )
    )


def _launch_service(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    """
    Start the background orchestrator service for the given symbols and optionally open the live monitor.

    Prompts the operator for launch options (continuous mode, poll interval, and optional max cycles), starts the background service with those options, prints a panel showing the spawned process PID, and then asks whether to open the live monitor.

    Parameters:
        settings (Settings): Application settings used to configure and launch the service.
        symbols (Sequence[str]): Symbols to monitor/trade when the service runs.
        interval (str): Time interval string to use for trading cycles (e.g., "1m", "5m").
        lookback (str): Lookback duration string used for data/context during each cycle.
    """
    continuous, poll_seconds, max_cycles = _prompt_service_launch_options(settings)
    pid = start_background_service(
        settings=settings,
        symbols=list(symbols),
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    console.print(
        Panel(
            MESSAGE_SERVICE_SPAWNED_BACKGROUND.format(pid=pid),
            title=TITLE_SERVICE_SPAWNED,
            border_style="green",
        )
    )
    _open_live_monitor_if_requested(settings)


def _prompt_service_launch_options(settings: Settings) -> tuple[bool, int, int | None]:
    """
    Prompt the operator for background service launch options.

    Prompts for continuous mode, a poll interval (defaults to settings.default_poll_seconds), and—when continuous mode is selected—an optional maximum cycle count.

    Parameters:
        settings (Settings): Application settings used to provide the default poll interval.

    Returns:
        tuple[bool, int, int | None]: A tuple (continuous, poll_seconds, max_cycles) where
            `continuous` is True when continuous mode was chosen,
            `poll_seconds` is the chosen poll interval in seconds,
            and `max_cycles` is the parsed maximum number of cycles when provided in continuous mode, or `None` when not set or when continuous is False.
    """
    continuous = Confirm.ask(PROMPT_CONTINUOUS_MODE, default=False)
    poll_seconds = IntPrompt.ask(
        PROMPT_POLL_INTERVAL_SECONDS,
        default=settings.default_poll_seconds,
    )
    if not continuous:
        return continuous, poll_seconds, None

    max_cycles_input = Prompt.ask(PROMPT_MAX_CYCLES, default="")
    max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    return continuous, poll_seconds, max_cycles


def _open_live_monitor_if_requested(settings: Settings) -> None:
    """
    Prompt the operator to open the live monitor and start it when confirmed.

    Asks the operator whether to open the live monitor now; if confirmed, launches the live monitor with a 1.0 second refresh interval.

    Parameters:
        settings (Settings): Application settings used to configure and run the live monitor.
    """
    if Confirm.ask(PROMPT_OPEN_LIVE_MONITOR_NOW, default=True):
        run_live_monitor(settings, refresh_seconds=1.0)


def _runtime_control_table() -> Table:
    """
    Builds a menu table of runtime control actions.

    Returns:
        Table: A Rich Table titled for runtime control with two columns (key and action) and rows for the available runtime control options (1–9).
    """
    table = Table(title=TITLE_RUNTIME_CONTROL)
    table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_ACTION)
    for key, action in (
        ("1", MENU_ACTION_DOCTOR_SYSTEM_CHECKS),
        ("2", MENU_ACTION_START_ONE_STRICT_AGENT_CYCLE),
        ("3", MENU_ACTION_START_ORCHESTRATOR_SERVICE),
        ("4", MENU_ACTION_REQUEST_ORCHESTRATOR_STOP),
        ("5", MENU_ACTION_OPEN_LIVE_MONITOR),
        ("6", MENU_ACTION_PROVIDER_DIAGNOSTICS),
        ("7", MENU_ACTION_V1_READINESS_GATES),
        ("8", MENU_ACTION_BROKER_STATUS),
        ("9", MENU_ACTION_BACK),
    ):
        table.add_row(key, action)
    return table


def _runtime_status_action(settings: Settings) -> None:
    db = safe_open_read_db(settings)
    try:
        render_status(settings, db)
    finally:
        if db is not None:
            db.close()


def _load_runtime_preferences(settings: Settings) -> InvestmentPreferences | None:
    """
    Load investment preferences from a read-only database and display an observer-mode panel when the database is unavailable.

    Parameters:
        settings (Settings): Application settings used to open the read-only trading database.

    Returns:
        InvestmentPreferences | None: The loaded investment preferences, or `None` if the database could not be opened.
    """
    db = safe_open_read_db(settings)
    try:
        if db is None:
            console.print(
                Panel(
                    MESSAGE_PREFERENCES_TEMPORARILY_UNAVAILABLE.format(error="-"),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            return None
        return db.load_preferences()
    finally:
        if db is not None:
            db.close()


def _runtime_one_shot_action(settings: Settings) -> None:
    prefs = _load_runtime_preferences(settings)
    if prefs is None:
        return
    default_symbols = "AAPL,MSFT" if "US" in prefs.regions else "BTC-USD"
    symbols = _split_csv(Prompt.ask("Symbols", default=default_symbols))
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    _strict_one_shot(settings, symbols, interval, lookback)


def _runtime_launch_action(settings: Settings) -> None:
    symbols = _split_csv(Prompt.ask("Symbols", default="AAPL,MSFT"))
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    _launch_service(settings, symbols, interval, lookback)


def _persist_stop_request(settings: Settings) -> None:
    try:
        db = _open_db(settings, read_only=False)
        try:
            db.request_stop_service()
        finally:
            db.close()
    except Exception:
        pass


def _runtime_stop_action(settings: Settings) -> None:
    """
    Requests the background runtime service to stop and reports status to the console.

    If no runtime service is active or the stored PID is missing, prints a "not running" panel.
    If the stored PID exists but the process is not alive, prints a "stale pid" panel.
    If the process appears active, issues a stop request, persists the stop request, and prints a "stop requested" panel including the PID.

    Parameters:
        settings (Settings): Application settings used to locate and control the runtime service.
    """
    state = read_service_state(settings)
    if state is None or state.pid is None:
        console.print(
            Panel(
                MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
                title=TITLE_NOT_RUNNING,
                border_style="yellow",
            )
        )
        return
    if not is_process_alive(state.pid):
        console.print(
            Panel(
                MESSAGE_STALE_RUNTIME_PID.format(pid=state.pid),
                title=TITLE_STALE_RUNTIME,
                border_style="yellow",
            )
        )
        return

    request_stop(settings)
    _persist_stop_request(settings)
    console.print(
        Panel(
            MESSAGE_SERVICE_STOP_REQUESTED.format(pid=state.pid),
            title=LABEL_STOP_REQUESTED,
            border_style="yellow",
        )
    )


def _runtime_monitor_action(settings: Settings) -> None:
    """
    Open a live monitoring UI for the runtime with a user-specified refresh interval.

    Prompts the operator for a refresh interval in seconds, clamps invalid or non-positive inputs to 1.0 second, and launches the live monitor.

    Parameters:
        settings (Settings): Application settings used to build the monitor UI.
    """
    try:
        refresh_seconds = float(Prompt.ask(PROMPT_REFRESH_SECONDS, default="1.0"))
        if refresh_seconds <= 0.0:
            refresh_seconds = 1.0
    except ValueError:
        refresh_seconds = 1.0
    run_live_monitor(settings, refresh_seconds=refresh_seconds)


def _provider_diagnostics_action(settings: Settings) -> None:
    render_provider_diagnostics(settings)


def _v1_readiness_action(settings: Settings) -> None:
    render_v1_readiness(settings)


def _broker_status_action(settings: Settings) -> None:
    render_broker_status(settings)


def _runtime_menu(settings: Settings) -> None:
    """
    Present an interactive runtime control menu for managing the orchestrator, one-shot cycles, and monitoring.
    """
    actions = {
        "1": _runtime_status_action,
        "2": _runtime_one_shot_action,
        "3": _runtime_launch_action,
        "4": _runtime_stop_action,
        "5": _runtime_monitor_action,
        "6": _provider_diagnostics_action,
        "7": _v1_readiness_action,
        "8": _broker_status_action,
    }
    while True:
        console.clear()
        console.print(_banner())
        console.print(_runtime_control_table())
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION,
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )
        if choice == "9":
            return
        actions[choice](settings)
        Prompt.ask(PROMPT_CONTINUE, default="")


def _operator_menu(settings: Settings) -> None:
    """
    Present an interactive Operator Desk menu that lets the operator open a chat session or parse/apply an instruction.

    Displays a simple menu with choices to (1) open operator chat, (2) parse operator instruction, or (3) go back. Opening chat attempts to read the database in safe/read-only mode and shows an observer-mode notice if the runtime writer prevents DB access; parsing an instruction requires a writable DB and shows an observer-mode notice on failure to open the DB. The menu loop continues until the user selects "Back".
    Parameters:
        settings (Settings): Application settings used to access the trading database and LLM configuration.
    """
    while True:
        console.clear()
        console.print(_banner())
        table = Table(title=TITLE_OPERATOR_DESK)
        table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
        table.add_column(LABEL_ACTION)
        table.add_row("1", MENU_ACTION_OPEN_OPERATOR_CHAT)
        table.add_row("2", MENU_ACTION_PARSE_OPERATOR_INSTRUCTION)
        table.add_row("3", MENU_ACTION_BACK)
        console.print(table)
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "1":
            db = safe_open_read_db(settings)
            if db is None:
                console.print(observer_mode_panel(TITLE_OPERATOR_CHAT_MEMORY_CONTEXT))
            else:
                try:
                    _chat_screen(settings, db)
                finally:
                    db.close()
        elif choice == "2":
            try:
                db = _open_db(settings, read_only=False)
            except Exception as exc:
                console.print(
                    observer_mode_panel(TITLE_INSTRUCTION_APPLICATION, str(exc))
                )
                Prompt.ask(PROMPT_CONTINUE, default="")
                continue
            try:
                _instruction_screen(settings, db)
            finally:
                db.close()
        else:
            return


def _menu_table(title: str, items: Sequence[TuiMenuAction | tuple[str, str]]) -> Table:
    """
    Build a Rich Table listing menu entries with key and action label columns.

    Parameters:
        title (str): Table title displayed above the menu.
        items (Sequence[TuiMenuAction | tuple[str, str]]): Sequence of menu entries; each entry is either a TuiMenuAction or a (key, label) tuple.

    Returns:
        Table: A Rich Table with two columns (key, action label) and one row per item.
    """
    table = Table(title=title)
    table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_ACTION)
    for item in items:
        if isinstance(item, TuiMenuAction):
            table.add_row(item.key, item.label)
        else:
            table.add_row(item[0], item[1])
    return table


def _run_readonly_db_menu_action(settings: Settings, action: TuiMenuAction) -> None:
    db = safe_open_read_db(settings)
    if db is None:
        console.print(observer_mode_panel(action.observer_title))
        return
    try:
        action.renderer(db)
    finally:
        db.close()


def _portfolio_menu(settings: Settings) -> None:
    """
    Present an interactive "Portfolio and Risk" menu that lets the operator view the paper portfolio, trade journal, or daily risk report.

    Opens a read-only database when a selected view requires persisted data, displays an observer-mode notice if the database is unavailable, closes the database after each view, and returns when the user selects "Back".
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_SHOW_PAPER_PORTFOLIO,
            TITLE_PAPER_PORTFOLIO,
            _show_portfolio,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_SHOW_TRADE_JOURNAL,
            TITLE_TRADE_JOURNAL,
            _show_trade_journal,
        ),
        "3": TuiMenuAction(
            "3",
            MENU_ACTION_SHOW_DAILY_RISK_REPORT,
            TITLE_DAILY_RISK_REPORT,
            _show_risk_report,
        ),
    }
    while True:
        console.clear()
        console.print(
            _menu_table(
                TITLE_PORTFOLIO_AND_RISK,
                [*actions.values(), ("4", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION, choices=["1", "2", "3", "4"], default="1"
        )
        if choice == "4":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")


def _research_menu(settings: Settings) -> None:
    """
    Display the Research and Memory menu and handle the operator's selection loop.

    Presents options to open the memory explorer, show recent runs (followed by a short runtime events list), or return to the previous menu. When a readable database is required the function attempts a safe read-only open and displays an observer-mode notice if the runtime writer prevents access; any opened database is closed before continuing.

    Parameters:
        settings (Settings): Application settings used to locate and open the trading database and service state.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_OPEN_MEMORY_EXPLORER,
            TITLE_MEMORY_EXPLORER,
            lambda db: _show_memory_explorer(settings, db),
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_SHOW_RECENT_RUNS_AND_EVENTS,
            TITLE_RECENT_RUNS,
            render_recent_runs,
        ),
    }
    while True:
        console.clear()
        console.print(
            _menu_table(
                TITLE_RESEARCH_AND_MEMORY,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        if choice == "2":
            render_runtime_events(read_service_events(settings, limit=6))
        Prompt.ask(PROMPT_CONTINUE, default="")


def _review_menu(settings: Settings) -> None:
    """
    Present an interactive "Review and Trace" menu that lets the operator inspect the latest persisted run review or its trace.

    Displays a menu, prompts for a selection, opens a read-only database when needed to render the chosen view, and returns to the caller when the user selects "Back".

    Parameters:
        settings (Settings): Application settings used to locate and open the trading database for read-only inspection.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
            TITLE_LATEST_RUN_REVIEW,
            _show_latest_run_review,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
            TITLE_AGENT_TRACE_FOR_RUN,
            _show_latest_run_trace,
        ),
    }
    while True:
        console.clear()
        console.print(
            _menu_table(
                TITLE_REVIEW_AND_TRACE,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")


def _render_main_status(settings: Settings) -> None:
    db = safe_open_read_db(settings)
    try:
        if console.height < 40:
            render_compact_status(settings, db)
        else:
            render_status(settings, db)
    finally:
        if db is not None:
            db.close()


def _edit_preferences_action(settings: Settings) -> None:
    """
    Open the writable database and launch the interactive preference editor, handling observer-mode when the DB cannot be opened.

    If opening the database fails, prints an observer-mode panel with the error and prompts the operator to continue. When the database is opened, runs the preference configuration flow and ensures the database is closed afterwards.
    """
    try:
        db = _open_db(settings, read_only=False)
    except Exception as exc:
        console.print(observer_mode_panel(TITLE_PREFERENCE_EDITING, str(exc)))
        Prompt.ask(PROMPT_CONTINUE, default="")
        return
    try:
        _configure_preferences(db)
    finally:
        db.close()


def _runtime_menu_action(settings: Settings) -> None:
    _runtime_menu(settings)


def _operator_menu_action(settings: Settings) -> None:
    _operator_menu(settings)


def _portfolio_menu_action(settings: Settings) -> None:
    _portfolio_menu(settings)


def _research_menu_action(settings: Settings) -> None:
    _research_menu(settings)


def _review_menu_action(settings: Settings) -> None:
    _review_menu(settings)


def _exit_menu_action(_settings: Settings) -> None:
    """
    Display a closing panel indicating the control room has been closed.
    """
    console.print(
        Panel(MESSAGE_CONTROL_ROOM_CLOSED, title=TITLE_EXIT, border_style="blue")
    )


def _main_menu_actions() -> tuple[TuiMainMenuAction, ...]:
    """
    Build the ordered set of main menu actions for the TUI.

    Returns:
        tuple[TuiMainMenuAction, ...]: Tuple of `TuiMainMenuAction` objects in menu order: configure investment preferences, runtime control, operator desk, portfolio and risk, research and memory, review and trace, and exit (the exit action is flagged to leave the menu).
    """
    return (
        TuiMainMenuAction(
            "1",
            MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
            _edit_preferences_action,
        ),
        TuiMainMenuAction("2", MENU_ACTION_RUNTIME_CONTROL, _runtime_menu_action),
        TuiMainMenuAction("3", MENU_ACTION_OPERATOR_DESK, _operator_menu_action),
        TuiMainMenuAction("4", MENU_ACTION_PORTFOLIO_AND_RISK, _portfolio_menu_action),
        TuiMainMenuAction("5", MENU_ACTION_RESEARCH_AND_MEMORY, _research_menu_action),
        TuiMainMenuAction("6", MENU_ACTION_REVIEW_AND_TRACE, _review_menu_action),
        TuiMainMenuAction("7", MENU_ACTION_EXIT, _exit_menu_action, exits_menu=True),
    )


def _main_menu_table(actions: Sequence[TuiMainMenuAction]) -> Table:
    """
    Builds a Rich Table representing the main menu from the given actions.

    Parameters:
        actions (Sequence[TuiMainMenuAction]): Ordered menu actions whose `key` and `label` populate each row.

    Returns:
        table (Table): A Rich Table titled with the main-menu title, containing two columns (key and action) and one row per action.
    """
    menu = Table(title=TITLE_MAIN_MENU)
    menu.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    menu.add_column(LABEL_ACTION)
    for action in actions:
        menu.add_row(action.key, action.label)
    return menu


def _run_main_menu_action(
    settings: Settings,
    choice: str,
    actions: Sequence[TuiMainMenuAction],
) -> bool:
    action_by_key = {action.key: action for action in actions}
    action = action_by_key[choice]
    action.handler(settings)
    return not action.exits_menu


def run_main_menu() -> None:
    """
    Run the interactive terminal control-room loop for the Agentic Trader UI.

    Displays the system banner and status, presents the main menu, dispatches to sub-menus (preferences, runtime control, operator desk, portfolio/risk, research/memory, review/trace), and manages opening/closing the trading database as needed. Handles EOF and interrupt signals to exit cleanly and reports action errors to the user.
    """
    settings = get_settings()
    settings.ensure_directories()
    actions = _main_menu_actions()
    choices = [action.key for action in actions]

    while True:
        console.clear()
        console.print(_banner())
        _render_main_status(settings)
        console.print(_main_menu_table(actions))

        try:
            choice = Prompt.ask(
                PROMPT_SELECT_ACTION,
                choices=choices,
                default="2",
            )
        except EOFError:
            _exit_cleanly()
            return
        try:
            if not _run_main_menu_action(settings, choice, actions):
                return
        except EOFError:
            _exit_cleanly()
            return
        except KeyboardInterrupt:
            console.print(
                Panel(
                    MESSAGE_ACTION_CANCELLED_RETURNING,
                    title=TITLE_CANCELLED,
                    border_style="yellow",
                )
            )
        except Exception as exc:
            console.print(
                Panel(str(exc), title=TITLE_ACTION_FAILED, border_style="red")
            )
        try:
            Prompt.ask(PROMPT_CONTINUE, default="")
        except EOFError:
            _exit_cleanly()
            return


split_csv = _split_csv
style_key = _style_key
system_status_table = _export_system_status_table
runtime_state_table = _export_runtime_state_table
runtime_cycle_lines = _export_runtime_cycle_lines
last_outcome_lines = _export_last_outcome_lines
broker_gate_lines = _export_broker_gate_lines
agent_activity_lines = _export_agent_activity_lines
agent_activity_table = _export_agent_activity_table
build_monitor_renderable = _build_monitor_renderable
memory_explorer_table = _memory_explorer_table
menu_table = _menu_table
main_menu_actions = _main_menu_actions
main_menu_table = _main_menu_table
run_main_menu_action = _run_main_menu_action
