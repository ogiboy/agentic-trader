import json
import os
import shutil
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import typer
from dotenv import set_key
from pandas import DataFrame
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.backtest.walk_forward import (
    run_backtest_comparison,
    run_memory_ablation_backtest,
    run_walk_forward_backtest,
)
from agentic_trader.cli_modules.common import (
    console,
)
from agentic_trader.cli_modules.common import emit_json as _emit_json
from agentic_trader.cli_modules.common import open_db as _open_db
from agentic_trader.cli_modules.dashboard_commands import (
    DashboardCommandDeps,
    register_dashboard_commands,
)
from agentic_trader.cli_modules.dashboard_commands import (
    build_dashboard_snapshot_payload as _build_dashboard_snapshot_payload,
)
from agentic_trader.cli_modules.dashboard_commands import (
    build_evidence_bundle as _build_dashboard_evidence_bundle,
)
from agentic_trader.cli_modules.dashboard_commands import (
    build_observer_api_payload as _build_observer_api_payload,
)
from agentic_trader.cli_modules.doctor import run_doctor_command
from agentic_trader.cli_modules.execution_rendering import render_execution_panels
from agentic_trader.cli_modules.finance_status import (
    broker_payload as _finance_broker_payload,
)
from agentic_trader.cli_modules.finance_status import (
    finance_ops_payload as _finance_ops_payload_impl,
)
from agentic_trader.cli_modules.finance_status import (
    portfolio_payload as _finance_portfolio_payload,
)
from agentic_trader.cli_modules.finance_status import (
    render_finance_ops as _render_finance_ops_impl,
)
from agentic_trader.cli_modules.finance_status import (
    render_position_plan_repair as _render_position_plan_repair_impl,
)
from agentic_trader.cli_modules.finance_status import (
    risk_report_payload as _finance_risk_report_payload,
)
from agentic_trader.cli_modules.launch_commands import register_launch_commands
from agentic_trader.cli_modules.market_commands import (
    MarketCommandDeps,
    register_market_commands,
)
from agentic_trader.cli_modules.observer_payloads import (
    calendar_payload as _calendar_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    canonical_analysis_lines as _canonical_analysis_lines_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    canonical_analysis_payload as _canonical_analysis_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    chat_history_payload as _chat_history_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    market_cache_payload as _market_cache_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    market_context_payload as _market_context_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    memory_explorer_payload as _memory_explorer_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    news_payload as _news_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    retrieval_inspection_payload as _retrieval_inspection_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    run_replay_payload as _run_replay_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    runtime_status_payload as _runtime_status_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    service_supervisor_payload as _service_supervisor_payload_impl,
)
from agentic_trader.cli_modules.operator_readiness import (
    accelerator_payload as _operator_accelerator_payload,
)
from agentic_trader.cli_modules.operator_readiness import (
    build_hardware_profile_payload,
    build_operator_workflow_payload,
    register_operator_readiness_commands,
)
from agentic_trader.cli_modules.operator_readiness import (
    total_memory_bytes as _operator_total_memory_bytes,
)
from agentic_trader.cli_modules.proposal_desk import (
    proposal_candidates_payload,
    register_proposal_desk_commands,
    trade_proposals_payload,
)
from agentic_trader.cli_modules.record_commands import (
    RecordCommandDeps,
    register_record_commands,
)
from agentic_trader.cli_modules.research_commands import (
    register_research_commands,
)
from agentic_trader.cli_modules.research_commands import (
    research_sidecar_payload as _research_sidecar_payload,
)
from agentic_trader.cli_modules.run_reports import (
    manager_override_notes as _manager_override_notes,
)
from agentic_trader.cli_modules.run_reports import (
    manager_resolution_notes as _manager_resolution_notes,
)
from agentic_trader.cli_modules.runtime_modes import (
    runtime_mode_transition_plan as _runtime_mode_transition_plan_impl,
)
from agentic_trader.cli_modules.service_control import run_stop_service_command
from agentic_trader.cli_modules.system_commands import (
    SystemCommandDeps,
    register_system_commands,
)
from agentic_trader.cli_modules.status_commands import (
    StatusCommandDeps,
    register_status_commands,
)
from agentic_trader.cli_modules.system_rendering import (
    render_operator_launcher_status as _render_operator_launcher_status,
)
from agentic_trader.cli_modules.system_rendering import (
    render_webgui_service_status as _render_webgui_service_status,
)
from agentic_trader.cli_modules.tui_node import (
    NodeCommandSet,
    register_tui_command,
    resolve_tui_node_commands as _resolve_tui_node_commands,
)
from agentic_trader.cli_modules.tui_node import (
    tui_dependencies_installed as tui_dependencies_installed,
)
from agentic_trader.config import Settings, get_settings
from agentic_trader.diagnostics import (
    provider_diagnostics_payload,
    v1_readiness_payload,
)
from agentic_trader.engine.broker import get_broker_adapter
from agentic_trader.execution.intent import ExecutionOutcome
from agentic_trader.finance.proposals import (
    refresh_trade_proposal_order,
    repair_missing_position_plans,
)
from agentic_trader.json_utils import object_list as _object_list
from agentic_trader.json_utils import object_mapping as _object_mapping
from agentic_trader.json_utils import object_mapping_list as _object_mapping_list
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.memory.policy import memory_write_policy_snapshot
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.cycle_runner import run_research_cycle
from agentic_trader.researchd.news_intelligence import (
    classify_source_tier,
    news_research_plan,
)
from agentic_trader.runtime_feed import (
    append_chat_history,
    read_service_events,
    read_service_state,
    request_stop,
)
from agentic_trader.runtime_status import (
    RuntimeStatusView,
    build_runtime_status_view,
    is_process_alive,
)
from agentic_trader.schemas import (
    BacktestAblationReport,
    BacktestComparisonReport,
    BacktestReport,
    CanonicalAnalysisSnapshot,
    ChatHistoryEntry,
    ChatPersona,
    InvestmentPreferences,
    OperatorInstruction,
    RuntimeMode,
    RuntimeModeTransitionPlan,
    ServiceStateSnapshot,
    TradeProposalRecord,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import OrderRow, TradingDatabase
from agentic_trader.system.camofox_service import (
    build_camofox_service_status,
    start_camofox_service,
    stop_camofox_service,
)
from agentic_trader.system.model_service import (
    build_model_service_status,
    pull_model,
    start_model_service,
    stop_model_service,
)
from agentic_trader.system.operator_launcher import (
    build_operator_launcher_status,
    start_operator_webgui,
)
from agentic_trader.system.setup import build_setup_status
from agentic_trader.system.tool_ownership import (
    OWNERSHIP_MODES,
    read_tool_ownership_payload,
    validate_ownership_mode,
    write_tool_ownership,
)
from agentic_trader.system.webgui_service import (
    build_webgui_service_status,
    stop_webgui_service,
)
from agentic_trader.tui import build_monitor_renderable, run_live_monitor, run_main_menu
from agentic_trader.ui_text import (
    HELP_CAMOFOX_SERVICE_APP,
    HELP_CHAT_MESSAGE,
    HELP_CHAT_PERSONA,
    HELP_CLI_APP,
    HELP_INSTRUCT_APPLY,
    HELP_INSTRUCT_MESSAGE,
    HELP_JSON,
    HELP_LOCALE_OVERRIDE,
    HELP_LOCALE_PERSIST,
    HELP_MODEL_SERVICE_APP,
    HELP_MONITOR_REFRESH_SECONDS,
    HELP_RESTART_SERVICE_GRACE_SECONDS,
    HELP_RUNTIME_MODE_PROVIDER_CHECK,
    HELP_RUNTIME_MODE_TARGET,
    HELP_STOP_SERVICE_FORCE,
    HELP_TOOL_OWNERSHIP_APP,
    HELP_WEBGUI_SERVICE_APP,
    LABEL_ALLOWED,
    LABEL_BLOCKING,
    LABEL_CHECK,
    LABEL_CONTINUOUS,
    LABEL_CURRENT,
    LABEL_CURRENT_SYMBOL,
    LABEL_CYCLE_COUNT,
    LABEL_DETAILS,
    LABEL_ENVIRONMENT,
    LABEL_FIELD,
    LABEL_HEARTBEAT,
    LABEL_HEARTBEAT_AGE,
    LABEL_INTERVAL,
    LABEL_KEY,
    LABEL_LAST_RECORDED_ERROR,
    LABEL_LAST_RECORDED_MESSAGE,
    LABEL_LAST_RECORDED_STATE,
    LABEL_LATEST_ORDER,
    LABEL_LIVE_PROCESS,
    LABEL_LOCALE,
    LABEL_LOOKBACK,
    LABEL_MAX_CYCLES,
    LABEL_MESSAGE,
    LABEL_MODE,
    LABEL_NO,
    LABEL_PASSED,
    LABEL_PERSISTED,
    LABEL_PID,
    LABEL_POLL_SECONDS,
    LABEL_PREFERENCE_UPDATE,
    LABEL_RATIONALE,
    LABEL_REQUIRES_CONFIRMATION,
    LABEL_RUNTIME,
    LABEL_SERVICE,
    LABEL_STARTED,
    LABEL_STATUS_NOTE,
    LABEL_STOP_REQUESTED,
    LABEL_SUMMARY,
    LABEL_SUPPORTED,
    LABEL_SYMBOLS,
    LABEL_TARGET,
    LABEL_UPDATE_PREFERENCES,
    LABEL_UPDATED,
    LABEL_VALUE,
    LABEL_YES,
    MESSAGE_BACKGROUND_SERVICE_RESTARTED,
    MESSAGE_LAUNCH_SYMBOL_REQUIRED,
    MESSAGE_NO_ACTION_SELECTED,
    MESSAGE_NO_ORDERS_RECORDED,
    MESSAGE_NO_RUNTIME_STATE,
    PROMPT_SELECT_ACTION,
    STYLE_KEY_COLUMN,
    SUPPORTED_UI_LOCALES,
    TITLE_CHAT,
    TITLE_EXIT,
    TITLE_OPERATOR_INSTRUCTION,
    TITLE_RESTART_BLOCKED,
    TITLE_RUNTIME_MODE,
    TITLE_RUNTIME_MODE_TRANSITION_CHECKLIST,
    TITLE_SERVICE_RESTARTED,
    TITLE_SERVICE_STATUS,
    TITLE_UI_LOCALE,
    TITLE_UPDATED_PREFERENCES,
    TITLE_WEB_GUI_START_FAILED,
    UI_LOCALE_ENV,
    UI_LIST_SEPARATOR,
    UILocale,
)
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import (
    ensure_llm_ready,
    restart_background_service,
    run_service,
    start_background_service,
    terminate_service_process,
)

app = typer.Typer(
    help=HELP_CLI_APP,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def object_mapping(value: object) -> Mapping[str, object]:
    """Return value as an object-keyed mapping when it already is one."""

    return _object_mapping(value)


def object_list(value: object) -> list[object]:
    """Return value as a list when it is a non-string sequence."""

    return _object_list(value)


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    """Return mapping rows from a non-string sequence."""

    return _object_mapping_list(value)


def parse_ui_locale(locale: str | None) -> UILocale | None:
    if locale is None:
        return None
    normalized = locale.strip().lower()
    if normalized in SUPPORTED_UI_LOCALES:
        return normalized
    allowed = ", ".join(SUPPORTED_UI_LOCALES)
    raise typer.BadParameter(f"Locale must be one of: {allowed}.")


def ui_payload(locale: str) -> dict[str, object]:
    return {
        "locale": locale,
        "supported_locales": list(SUPPORTED_UI_LOCALES),
        "env": UI_LOCALE_ENV,
    }


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL_FILE = PROJECT_ROOT / ".env.local"


def upsert_env_local_value(key: str, value: str) -> None:
    set_key(ENV_LOCAL_FILE, key, value, quote_mode="never")


def _accelerator_payload() -> dict[str, object]:
    return _operator_accelerator_payload()


def _total_memory_bytes() -> int | None:
    return _operator_total_memory_bytes()


def _refresh_trade_proposal_order_provider(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str,
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    return refresh_trade_proposal_order(
        db=db,
        settings=settings,
        proposal_id=proposal_id,
        review_notes=review_notes,
    )


def _validate_ownership_mode_provider(value: str) -> str:
    return validate_ownership_mode(value)


def _build_setup_status_provider(settings: Settings) -> object:
    return build_setup_status(settings)


def _read_tool_ownership_payload_provider(settings: Settings) -> object:
    return read_tool_ownership_payload(settings)


def _write_tool_ownership_provider(
    settings: Settings, updates: dict[str, str], source: str
) -> object:
    return write_tool_ownership(settings, updates, source=source)


def _build_model_service_status_provider(
    settings: Settings, *, include_generation: bool = False
) -> object:
    return build_model_service_status(settings, include_generation=include_generation)


def _start_model_service_provider(
    settings: Settings, *, host: str | None = None, port: int | None = None
) -> object:
    return start_model_service(settings, host=host, port=port)


def _stop_model_service_provider(settings: Settings) -> object:
    return stop_model_service(settings)


def _pull_model_provider(settings: Settings, model_name: str) -> dict[str, object]:
    return pull_model(settings, model_name)


def _build_webgui_service_status_provider(settings: Settings) -> object:
    return build_webgui_service_status(settings)


def _start_operator_webgui_provider(
    settings: Settings, *, open_browser: bool = True
) -> object:
    return start_operator_webgui(settings, open_browser=open_browser)


def _stop_webgui_service_provider(settings: Settings) -> object:
    return stop_webgui_service(settings)


def _build_camofox_service_status_provider(settings: Settings) -> object:
    return build_camofox_service_status(settings)


def _start_camofox_service_provider(
    settings: Settings, *, host: str | None = None, port: int | None = None
) -> object:
    return start_camofox_service(settings, host=host, port=port)


def _stop_camofox_service_provider(settings: Settings) -> object:
    return stop_camofox_service(settings)


model_service_app = typer.Typer(help=HELP_MODEL_SERVICE_APP)
app.add_typer(model_service_app, name="model-service")
webgui_service_app = typer.Typer(help=HELP_WEBGUI_SERVICE_APP)
app.add_typer(webgui_service_app, name="webgui-service")
camofox_service_app = typer.Typer(help=HELP_CAMOFOX_SERVICE_APP)
app.add_typer(camofox_service_app, name="camofox-service")
tool_ownership_app = typer.Typer(help=HELP_TOOL_OWNERSHIP_APP)
app.add_typer(tool_ownership_app, name="tool-ownership")
register_system_commands(
    app=app,
    tool_ownership_app=tool_ownership_app,
    model_service_app=model_service_app,
    webgui_service_app=webgui_service_app,
    camofox_service_app=camofox_service_app,
    deps=SystemCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        ownership_modes=OWNERSHIP_MODES,
        validate_ownership_mode=_validate_ownership_mode_provider,
        build_setup_status=_build_setup_status_provider,
        read_tool_ownership_payload=_read_tool_ownership_payload_provider,
        write_tool_ownership=_write_tool_ownership_provider,
        build_model_service_status=_build_model_service_status_provider,
        start_model_service=_start_model_service_provider,
        stop_model_service=_stop_model_service_provider,
        pull_model=_pull_model_provider,
        build_webgui_service_status=_build_webgui_service_status_provider,
        start_operator_webgui=_start_operator_webgui_provider,
        stop_webgui_service=_stop_webgui_service_provider,
        build_camofox_service_status=_build_camofox_service_status_provider,
        start_camofox_service=_start_camofox_service_provider,
        stop_camofox_service=_stop_camofox_service_provider,
    ),
)
register_proposal_desk_commands(
    app,
    settings_provider=lambda: get_settings(),
    refresh_trade_proposal_order_provider=_refresh_trade_proposal_order_provider,
)
register_operator_readiness_commands(
    app,
    settings_provider=lambda: get_settings(),
    accelerator_provider=lambda: _accelerator_payload(),
    cpu_count_provider=lambda: os.cpu_count(),
    total_memory_provider=lambda: _total_memory_bytes(),
)
register_tui_command(app)
register_research_commands(
    app,
    settings_provider=lambda: get_settings(),
    emit_json=_emit_json,
)
register_launch_commands(
    app,
    settings_provider=lambda: get_settings(),
    ensure_ready=lambda settings: ensure_llm_ready(settings),
    run_once=run_once,
    persist_run=persist_run,
    run_service=run_service,
    start_background_service=start_background_service,
    render_execution=render_execution_panels,
)
QA_ARTIFACTS_ROOT = PROJECT_ROOT / ".ai" / "qa" / "artifacts"


def resolve_tui_node_commands(tui_dir: Path) -> NodeCommandSet | None:
    return _resolve_tui_node_commands(tui_dir, which=shutil.which)


def _read_text_tail(path: Path | None, *, limit: int = 12) -> list[str]:
    """
    Return the last up to `limit` lines from a UTF-8 text file with sensitive content redacted.

    If `path` is None or the file does not exist, an empty list is returned. Lines are decoded using UTF-8 with replacement for invalid bytes and each returned line is redacted for sensitive content.

    Parameters:
        path (Path | None): Path to the text file to read, or None to indicate absence.
        limit (int): Maximum number of trailing lines to return.

    Returns:
        list[str]: Up to `limit` trailing lines from the file with sensitive content redacted, or an empty list if the file is unavailable.
    """
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [redact_sensitive_text(line, max_length=1_000) for line in lines[-limit:]]


def _format_latest_order(order: OrderRow | None) -> str:
    """
    Formats an OrderRow into a compact single-line human-readable summary.

    Returns:
        str: Single-line summary in the form
        "order_id | SYMBOL SIDE | approved=<bool> | entry=<price> | size=<pct> | confidence=<score>",
        or the literal string "None" when `order` is None.
    """
    if order is None:
        return "None"
    (
        order_id,
        _created_at,
        symbol,
        side,
        approved,
        entry_price,
        _stop_loss,
        _take_profit,
        position_size_pct,
        confidence,
    ) = order
    return (
        f"{order_id} | {symbol} {side} | approved={approved} | "
        f"entry={entry_price:.4f} | size={position_size_pct:.2%} | "
        f"confidence={confidence:.2f}"
    )


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    """
    Create a rich Panel with the given title text and border style.

    Parameters:
        status (str): Text to use as the panel title.
        body (str): Text content to display inside the panel.
        border_style (str): Rich style string applied to the panel border.

    Returns:
        panel (Panel): A `rich.panel.Panel` containing `body`, titled with `status`, and using `border_style`.
    """
    return Panel(body, title=status, border_style=border_style)


def _render_instruction(instruction: OperatorInstruction) -> None:
    table = Table(title=TITLE_OPERATOR_INSTRUCTION)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_SUMMARY, instruction.summary)
    table.add_row(LABEL_UPDATE_PREFERENCES, str(instruction.should_update_preferences))
    table.add_row(LABEL_REQUIRES_CONFIRMATION, str(instruction.requires_confirmation))
    table.add_row(LABEL_RATIONALE, instruction.rationale)
    table.add_row(
        LABEL_PREFERENCE_UPDATE,
        json.dumps(instruction.preference_update.model_dump(mode="json"), indent=2),
    )
    console.print(table)


def _render_service_state(state: ServiceStateSnapshot | None) -> None:
    """
    Render the supervisor/service runtime status to the console.

    If `state` is None or contains no recorded runtime state, prints a yellow panel indicating no runtime state is recorded. Otherwise prints a table summarizing service fields such as service name, runtime mode/state, process liveness, heartbeat and its age, start/updated times, polling and cycle settings, configured symbols/interval/lookback, PID and stop-requested flag, and the last recorded message/error.

    Parameters:
        state: Snapshot of the supervisor/service runtime state; pass `None` to indicate no recorded runtime state.
    """
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                MESSAGE_NO_RUNTIME_STATE,
                title=TITLE_SERVICE_STATUS,
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title=TITLE_SERVICE_STATUS)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_SERVICE, snapshot.service_name)
    table.add_row(LABEL_MODE, snapshot.runtime_mode)
    table.add_row(LABEL_RUNTIME, view.runtime_state)
    table.add_row(LABEL_LIVE_PROCESS, LABEL_YES if view.live_process else LABEL_NO)
    table.add_row(LABEL_LAST_RECORDED_STATE, view.last_recorded_state or "-")
    table.add_row(LABEL_UPDATED, snapshot.updated_at)
    table.add_row(LABEL_STARTED, snapshot.started_at or "-")
    table.add_row(LABEL_HEARTBEAT, snapshot.last_heartbeat_at or "-")
    table.add_row(
        LABEL_HEARTBEAT_AGE,
        f"{view.age_seconds}s" if view.age_seconds is not None else "-",
    )
    table.add_row(LABEL_CONTINUOUS, str(snapshot.continuous))
    table.add_row(
        LABEL_POLL_SECONDS,
        str(snapshot.poll_seconds) if snapshot.poll_seconds is not None else "-",
    )
    table.add_row(LABEL_CYCLE_COUNT, str(snapshot.cycle_count))
    table.add_row(LABEL_SYMBOLS, UI_LIST_SEPARATOR.join(snapshot.symbols) or "-")
    table.add_row(LABEL_INTERVAL, snapshot.interval or "-")
    table.add_row(LABEL_LOOKBACK, snapshot.lookback or "-")
    table.add_row(
        LABEL_MAX_CYCLES,
        str(snapshot.max_cycles) if snapshot.max_cycles is not None else "-",
    )
    table.add_row(LABEL_CURRENT_SYMBOL, snapshot.current_symbol or "-")
    table.add_row(LABEL_PID, str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row(LABEL_STOP_REQUESTED, str(snapshot.stop_requested))
    table.add_row(LABEL_STATUS_NOTE, view.status_message)
    table.add_row(LABEL_LAST_RECORDED_MESSAGE, snapshot.message or "-")
    table.add_row(LABEL_LAST_RECORDED_ERROR, snapshot.last_error or "-")
    console.print(table)


def _portfolio_payload(settings: Settings) -> dict[str, object]:
    return _finance_portfolio_payload(
        settings,
        open_db_provider=_open_db,
        broker_adapter_provider=get_broker_adapter,
    )


def _preferences_payload(settings: Settings) -> dict[str, object]:
    """
    Load persisted investment preferences and include availability and error metadata.

    Returns:
        payload (dict): JSON-serializable representation of the loaded InvestmentPreferences with two additional keys:
            - `available` (`True` if preferences were successfully loaded, `False` otherwise).
            - `error` (string error message when loading failed, or `None` when successful).
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        preferences = InvestmentPreferences()
        available = False
        error = str(exc)
    payload = preferences.model_dump(mode="json")
    payload["available"] = available
    payload["error"] = error
    return payload


def _journal_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    """
    Builds a payload containing the most recent trade journal entries.

    Parameters:
        limit (int): Maximum number of journal entries to include, ordered newest first.

    Returns:
        dict: Payload with keys:
            - `available` (bool): `True` if the database read succeeded, `False` on error.
            - `error` (str | None): Error message when `available` is `False`, otherwise `None`.
            - `entries` (list[dict]): Journal entries serialized as JSON-compatible dictionaries.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            entries = db.list_trade_journal(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except (
        Exception
    ) as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def _recent_runs_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    """
    Builds a JSON-serializable payload of recent run metadata for CLI/observer consumption.

    Parameters:
        settings (Settings): Application settings used to open the database.
        limit (int): Maximum number of recent runs to include.

    Returns:
        dict: A mapping with keys:
            - `available` (bool): `True` when runs were loaded successfully, `False` on error.
            - `error` (str | None): Error message when `available` is `False`, otherwise `None`.
            - `runs` (list[dict]): List of run summaries. Each entry contains:
                - `run_id` (str): Persisted run identifier.
                - `created_at` (str): Run creation timestamp.
                - `symbol` (str): Traded symbol for the run.
                - `interval` (str): Market interval used for the run.
                - `approved` (bool): Whether the run/execution was approved.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            runs = db.list_recent_runs(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except (
        Exception
    ) as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        runs = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "runs": [
            {
                "run_id": run_id,
                "created_at": created_at,
                "symbol": symbol,
                "interval": interval,
                "approved": approved,
            }
            for run_id, created_at, symbol, interval, approved in runs
        ],
    }


def _risk_report_payload(
    settings: Settings, *, report_date: str | None = None
) -> dict[str, object]:
    return _finance_risk_report_payload(
        settings,
        report_date=report_date,
        open_db_provider=_open_db,
        broker_adapter_provider=get_broker_adapter,
    )


def _run_record_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    """
    Builds a payload containing a persisted run record (or the latest run) and availability metadata.

    Parameters:
        run_id (str | None): Optional run identifier; when None the latest persisted run is loaded.

    Returns:
        dict[str, object]: Payload with keys:
            - "available": `True` if the database read succeeded, `False` on error.
            - "error": Error message string when unavailable, otherwise `None`.
            - "record": JSON-serializable dict of the run record when available, otherwise `None`.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = db.get_run(run_id) if run_id is not None else db.latest_run()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


def _trade_context_payload(
    settings: Settings, *, trade_id: str | None = None
) -> dict[str, object]:
    """
    Builds a payload containing a persisted trade context record for observer output or APIs.

    Parameters:
        settings (Settings): Application settings used to open the read-only database.
        trade_id (str | None): Optional trade identifier; when provided, returns the matching trade context, otherwise returns the latest trade context.

    Returns:
        dict: A JSON-serializable mapping with keys:
            - "available" (bool): `True` if the record was loaded successfully, `False` on error.
            - "error" (str | None): Error message when loading failed, otherwise `None`.
            - "record" (dict | None): The trade context serialized for JSON when available, otherwise `None`.
    """
    try:
        db = _open_db(settings, read_only=True)
        try:
            record = (
                db.get_trade_context(trade_id)
                if trade_id is not None
                else db.latest_trade_context()
            )
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


def _market_context_payload(settings: Settings) -> dict[str, object]:
    return _market_context_payload_impl(settings, open_db=_open_db)


def _canonical_analysis_payload(settings: Settings) -> dict[str, object]:
    return _canonical_analysis_payload_impl(settings, open_db=_open_db)


def _canonical_analysis_lines(
    canonical_snapshot: CanonicalAnalysisSnapshot | None,
) -> list[str]:
    return _canonical_analysis_lines_impl(canonical_snapshot)


def _service_supervisor_payload(settings: Settings) -> dict[str, object]:
    return _service_supervisor_payload_impl(settings, read_text_tail=_read_text_tail)


def _broker_payload(settings: Settings) -> dict[str, object]:
    return _finance_broker_payload(settings)


def _finance_ops_payload(settings: Settings) -> dict[str, object]:
    return _finance_ops_payload_impl(
        settings,
        open_db_provider=_open_db,
        broker_adapter_provider=get_broker_adapter,
    )


def _render_finance_ops(payload: dict[str, object]) -> None:
    _render_finance_ops_impl(payload)


def _render_position_plan_repair(payload: dict[str, object]) -> None:
    _render_position_plan_repair_impl(payload)


def _runtime_mode_transition_plan(
    settings: Settings, *, target_mode: RuntimeMode, check_provider: bool
) -> RuntimeModeTransitionPlan:
    return _runtime_mode_transition_plan_impl(
        settings,
        target_mode=target_mode,
        check_provider=check_provider,
    )


def _render_runtime_mode_transition_plan(plan: RuntimeModeTransitionPlan) -> None:
    """
    Render a runtime-mode transition checklist and summary for operator review.

    Prints a table of transition checks (name, pass status, blocking flag, and details) and a summary panel showing current mode, target mode, whether the transition is allowed, and the plan's human-readable summary.

    Parameters:
        plan (RuntimeModeTransitionPlan): Transition plan containing current and target modes, an ordered sequence of checks (each with name, passed, blocking, details), an overall `allowed` flag, and a short `summary` suitable for operator display.
    """
    table = Table(title=TITLE_RUNTIME_MODE_TRANSITION_CHECKLIST)
    table.add_column(LABEL_CHECK)
    table.add_column(LABEL_PASSED)
    table.add_column(LABEL_BLOCKING)
    table.add_column(LABEL_DETAILS)
    for check in plan.checks:
        table.add_row(
            check.name,
            LABEL_YES if check.passed else LABEL_NO,
            LABEL_YES if check.blocking else LABEL_NO,
            check.details,
        )
    console.print(
        Panel(
            (
                f"{LABEL_CURRENT}: {plan.current_mode}\n"
                f"{LABEL_TARGET}: {plan.target_mode}\n"
                f"{LABEL_ALLOWED}: {plan.allowed}\n\n{plan.summary}"
            ),
            title=TITLE_RUNTIME_MODE,
            border_style="green" if plan.allowed else "yellow",
        )
    )
    console.print(table)


def _runtime_status_payload(
    view: RuntimeStatusView, settings: Settings
) -> dict[str, object]:
    return _runtime_status_payload_impl(view, settings)


def _calendar_payload(
    settings: Settings, *, symbol: str | None = None
) -> dict[str, object]:
    return _calendar_payload_impl(settings, open_db=_open_db, symbol=symbol)


def _news_payload(
    settings: Settings, *, symbol: str | None = None
) -> dict[str, object]:
    return _news_payload_impl(settings, open_db=_open_db, symbol=symbol)


def _market_cache_payload(settings: Settings) -> dict[str, object]:
    return _market_cache_payload_impl(settings)


def _memory_explorer_payload(
    settings: Settings,
    *,
    symbol: str | None = None,
    interval: str | None = None,
    lookback: str = "180d",
    limit: int = 5,
    use_latest_run: bool = False,
) -> dict[str, object]:
    return _memory_explorer_payload_impl(
        settings,
        open_db=_open_db,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        limit=limit,
        use_latest_run=use_latest_run,
    )


def _retrieval_inspection_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    return _retrieval_inspection_payload_impl(
        settings,
        run_id=run_id,
        run_record_payload=_run_record_payload,
    )


def _chat_history_payload(settings: Settings, *, limit: int = 12) -> dict[str, object]:
    return _chat_history_payload_impl(settings, limit=limit)


def _run_replay_payload(
    settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    return _run_replay_payload_impl(
        settings,
        run_id=run_id,
        run_record_payload=_run_record_payload,
        manager_override_notes=_manager_override_notes,
        manager_resolution_notes=_manager_resolution_notes,
    )


def _run_backtest_comparison_provider(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: DataFrame | None = None,
) -> BacktestComparisonReport:
    return run_backtest_comparison(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        frame=frame,
    )


def _run_memory_ablation_backtest_provider(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: DataFrame | None = None,
) -> BacktestAblationReport:
    return run_memory_ablation_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        frame=frame,
    )


def _run_walk_forward_backtest_provider(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    memory_enabled: bool = True,
    frame: DataFrame | None = None,
) -> BacktestReport:
    return run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        memory_enabled=memory_enabled,
        frame=frame,
    )


register_status_commands(
    app,
    StatusCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        portfolio_payload=_portfolio_payload,
        runtime_status_payload=_runtime_status_payload,
        service_supervisor_payload=_service_supervisor_payload,
        broker_payload=_broker_payload,
        finance_ops_payload=_finance_ops_payload,
        render_finance_ops=_render_finance_ops,
        render_position_plan_repair=_render_position_plan_repair,
        provider_diagnostics_payload=provider_diagnostics_payload,
        v1_readiness_payload=v1_readiness_payload,
        read_service_state=read_service_state,
        build_runtime_status_view=build_runtime_status_view,
        render_service_state=_render_service_state,
        open_db=_open_db,
        repair_missing_position_plans=repair_missing_position_plans,
    ),
)

register_record_commands(
    app,
    RecordCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        preferences_payload=_preferences_payload,
        journal_payload=_journal_payload,
        risk_report_payload=_risk_report_payload,
        run_record_payload=_run_record_payload,
        trade_context_payload=_trade_context_payload,
        canonical_analysis_lines=_canonical_analysis_lines,
        run_replay_payload=_run_replay_payload,
        memory_explorer_payload=_memory_explorer_payload,
        retrieval_inspection_payload=_retrieval_inspection_payload,
        memory_write_policy_snapshot=memory_write_policy_snapshot,
        open_db=_open_db,
        ensure_ready=lambda settings: ensure_llm_ready(settings),
        run_comparison=_run_backtest_comparison_provider,
        run_ablation=_run_memory_ablation_backtest_provider,
        run_walk_forward=_run_walk_forward_backtest_provider,
    ),
)


@app.callback()
def app_entry(
    ctx: typer.Context,
    locale: str | None = typer.Option(
        None,
        "--locale",
        help=HELP_LOCALE_OVERRIDE,
    ),
) -> None:
    resolved_locale = parse_ui_locale(locale)
    if resolved_locale is not None:
        os.environ[UI_LOCALE_ENV] = resolved_locale
    if ctx.invoked_subcommand is None:
        _operator_launcher()


@app.command("locale")
def locale_command(
    set_locale: str | None = typer.Option(
        None,
        "--set",
        help=HELP_LOCALE_PERSIST,
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show or persist the terminal UI locale."""
    settings = get_settings()
    persisted = False
    selected_locale = parse_ui_locale(set_locale)
    if selected_locale is not None:
        upsert_env_local_value(UI_LOCALE_ENV, selected_locale)
        os.environ[UI_LOCALE_ENV] = selected_locale
        settings = Settings()
        persisted = True

    payload = {
        **ui_payload(settings.ui_locale),
        "persisted": persisted,
        "env_file": ".env.local",
    }
    if json_output:
        _emit_json(payload)
        return
    table = Table(title=TITLE_UI_LOCALE)
    table.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_LOCALE, str(payload["locale"]))
    table.add_row(LABEL_SUPPORTED, UI_LIST_SEPARATOR.join(SUPPORTED_UI_LOCALES))
    table.add_row(LABEL_ENVIRONMENT, UI_LOCALE_ENV)
    table.add_row(LABEL_PERSISTED, str(persisted))
    console.print(table)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help=HELP_JSON)) -> None:
    """Check local environment, LLM, and database readiness."""
    run_doctor_command(
        settings=get_settings(),
        json_output=json_output,
        open_db=_open_db,
        latest_order_formatter=_format_latest_order,
        health_check=lambda settings: LocalLLM(settings).health_check(),
    )


def _operator_launcher() -> None:
    """Interactive no-argument product launcher."""

    settings = get_settings()
    while True:
        payload = build_operator_launcher_status(settings).model_dump(mode="json")
        _render_operator_launcher_status(payload)
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION,
            choices=["1", "2", "3", "4", "8", "q"],
            default="2",
        )
        if choice == "1":
            try:
                status = start_operator_webgui(settings)
            except Exception as exc:
                console.print(
                    _render_health_panel(
                        TITLE_WEB_GUI_START_FAILED,
                        redact_sensitive_text(exc, max_length=240),
                        border_style="red",
                    )
                )
                raise typer.Exit(code=1) from exc
            _render_webgui_service_status(status.model_dump(mode="json"))
            return
        if choice == "2":
            run_main_menu()
            return
        if choice == "3":
            continue
        break
    console.print(
        _render_health_panel(
            TITLE_EXIT,
            MESSAGE_NO_ACTION_SELECTED,
            border_style="blue",
        )
    )


@app.command("runtime-mode-checklist")
def runtime_mode_checklist(
    target_mode: RuntimeMode = typer.Argument(..., help=HELP_RUNTIME_MODE_TARGET),
    check_provider: bool = typer.Option(
        True,
        "--provider-check/--skip-provider-check",
        help=HELP_RUNTIME_MODE_PROVIDER_CHECK,
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show the approved checklist for a Training/Operation mode transition."""
    settings = get_settings()
    plan = _runtime_mode_transition_plan(
        settings,
        target_mode=target_mode,
        check_provider=check_provider,
    )
    if json_output:
        _emit_json(plan.model_dump(mode="json"))
        return
    _render_runtime_mode_transition_plan(plan)


def build_dashboard_snapshot_payload(
    settings: Settings, *, log_limit: int = 14, check_provider: bool = False
) -> dict[str, object]:
    return _build_dashboard_snapshot_payload(
        settings,
        deps=_dashboard_command_deps(),
        log_limit=log_limit,
        check_provider=check_provider,
    )


def build_evidence_bundle(
    settings: Settings,
    *,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    return _build_dashboard_evidence_bundle(
        settings,
        deps=_dashboard_command_deps(),
        output_dir=output_dir,
        label=label,
        log_limit=log_limit,
        include_latest_smoke=include_latest_smoke,
        check_provider=check_provider,
    )


def build_observer_api_payload(
    settings: Settings, *, path: str, log_limit: int = 14
) -> tuple[int, dict[str, object]]:
    return _build_observer_api_payload(
        settings, deps=_dashboard_command_deps(), path=path, log_limit=log_limit
    )


def _dashboard_command_deps() -> DashboardCommandDeps:
    return DashboardCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        ui_payload=ui_payload,
        open_read_db=lambda settings: _open_db(settings, read_only=True),
        latest_order=_format_latest_order,
        runtime_status_payload=_runtime_status_payload,
        service_supervisor_payload=_service_supervisor_payload,
        broker_payload=_broker_payload,
        finance_ops_payload=_finance_ops_payload,
        portfolio_payload=_portfolio_payload,
        preferences_payload=_preferences_payload,
        recent_runs_payload=lambda settings, limit: _recent_runs_payload(
            settings, limit=limit
        ),
        proposal_candidates_payload=lambda settings, limit: proposal_candidates_payload(
            settings, limit=limit
        ),
        trade_proposals_payload=lambda settings, limit: trade_proposals_payload(
            settings, limit=limit
        ),
        journal_payload=lambda settings, limit: _journal_payload(settings, limit=limit),
        risk_report_payload=_risk_report_payload,
        run_record_payload=_run_record_payload,
        trade_context_payload=_trade_context_payload,
        market_context_payload=_market_context_payload,
        canonical_analysis_payload=_canonical_analysis_payload,
        run_replay_payload=_run_replay_payload,
        memory_explorer_payload=lambda settings, use_latest_run, limit: _memory_explorer_payload(
            settings, use_latest_run=use_latest_run, limit=limit
        ),
        retrieval_inspection_payload=_retrieval_inspection_payload,
        chat_history_payload=_chat_history_payload,
        calendar_payload=_calendar_payload,
        news_payload=_news_payload,
        market_cache_payload=_market_cache_payload,
        research_sidecar_payload=_research_sidecar_payload,
        provider_diagnostics_payload=provider_diagnostics_payload,
        v1_readiness_payload=lambda settings, check_provider: v1_readiness_payload(
            settings, check_provider=check_provider
        ),
        runtime_mode_operation=lambda settings: _runtime_mode_transition_plan(
            settings, target_mode="operation", check_provider=False
        ),
        operator_workflow=build_operator_workflow_payload,
        hardware_profile=build_hardware_profile_payload,
        read_service_events=read_service_events,
        read_service_state=read_service_state,
        build_runtime_status_view=build_runtime_status_view,
    )


register_dashboard_commands(app, _dashboard_command_deps())

register_market_commands(
    app,
    MarketCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        calendar_payload=_calendar_payload,
        news_payload=_news_payload,
        market_cache_payload=_market_cache_payload,
        fetch_ohlcv=fetch_ohlcv,
        news_research_plan=news_research_plan,
        classify_source_tier=classify_source_tier,
        research_cycle_plan_payload=research_cycle_plan_payload,
        run_research_cycle=run_research_cycle,
    ),
)


@app.command()
def chat(
    persona: ChatPersona = typer.Option("operator_liaison", help=HELP_CHAT_PERSONA),
    message: str | None = typer.Option(None, help=HELP_CHAT_MESSAGE),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Send a message to a chosen operator persona and display or emit the persona's reply.

    If `message` is omitted an interactive prompt is shown. The interaction is recorded
    in persistent chat history. Output is printed as a terminal panel unless
    `json_output` is true, in which case a JSON payload containing `persona`,
    `message`, and `response` is emitted.

    Parameters:
        persona (ChatPersona): Which agent persona should answer.
        message (str | None): Optional message text; when None an interactive prompt is used.
        json_output (bool): When true, emit a JSON payload instead of printing a panel.
    """
    settings = get_settings()
    ensure_llm_ready(settings)
    db = _open_db(settings, read_only=True)
    prompt = message or typer.prompt(LABEL_MESSAGE)
    response = chat_with_persona(
        llm=LocalLLM(settings),
        db=db,
        settings=settings,
        persona=persona,
        user_message=prompt,
    )
    db.close()
    append_chat_history(
        settings,
        ChatHistoryEntry(
            entry_id=f"chat-{uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc).isoformat(),
            persona=persona,
            user_message=prompt,
            response_text=response,
        ),
    )
    if json_output:
        _emit_json(
            {
                "persona": persona,
                "message": prompt,
                "response": response,
            }
        )
        return
    console.print(
        Panel(
            response,
            title=TITLE_CHAT.format(persona=persona),
            border_style="cyan",
        )
    )


@app.command()
def instruct(
    message: str = typer.Option(..., help=HELP_INSTRUCT_MESSAGE),
    apply: bool = typer.Option(False, help=HELP_INSTRUCT_APPLY),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """
    Interpret a natural-language operator instruction and optionally persist a resulting preference update.

    Interprets the provided operator instruction into an actionable instruction. If the interpreted instruction proposes a preference update and `apply` is True, the update is persisted. When `json_output` is True, emits a JSON object with keys `instruction` (the interpreted instruction), `applied` (`true` if a preference update was persisted, `false` otherwise), and `updated_preferences` (the new preferences or `null`); otherwise the instruction and any updated preferences are rendered to the console.

    Parameters:
        message (str): Natural-language operator instruction to interpret.
        apply (bool): If True, persist the parsed preference update when one is proposed.
        json_output (bool): If True, emit a JSON payload instead of rendering console output.
    """
    settings = get_settings()
    ensure_llm_ready(settings)
    db = TradingDatabase(settings)
    try:
        llm = LocalLLM(settings)
        instruction = interpret_operator_instruction(
            llm=llm,
            db=db,
            settings=settings,
            user_message=message,
            allow_fallback=True,
        )
        updated: InvestmentPreferences | None = None
        if apply and instruction.should_update_preferences:
            updated = apply_preference_update(db, instruction.preference_update)
        if json_output:
            _emit_json(
                {
                    "instruction": instruction.model_dump(mode="json"),
                    "applied": updated is not None,
                    "updated_preferences": (
                        updated.model_dump(mode="json") if updated is not None else None
                    ),
                }
            )
            return
        _render_instruction(instruction)
        if updated is not None:
            console.print(
                Panel(
                    updated.model_dump_json(indent=2),
                    title=TITLE_UPDATED_PREFERENCES,
                    border_style="green",
                )
            )
    finally:
        db.close()


@app.command()
def monitor(
    refresh_seconds: float = typer.Option(
        1.0, min=0.2, help=HELP_MONITOR_REFRESH_SECONDS
    ),
) -> None:
    """
    Open and attach to the live runtime monitor.

    Parameters:
        refresh_seconds (float): Dashboard refresh interval in seconds (minimum 0.2).
    """
    settings = get_settings()
    console.print(build_monitor_renderable(settings))
    run_live_monitor(settings, refresh_seconds=refresh_seconds)


@app.command("stop-service")
def stop_service(
    force: bool = typer.Option(False, help=HELP_STOP_SERVICE_FORCE),
) -> None:
    """Request a graceful stop for the background orchestrator."""
    run_stop_service_command(
        settings=get_settings(),
        force=force,
        read_state=read_service_state,
        process_alive=is_process_alive,
        request_service_stop=request_stop,
        database_factory=TradingDatabase,
        terminate_process=terminate_service_process,
    )


@app.command("restart-service")
def restart_service(
    grace_seconds: float = typer.Option(
        3.0, min=0.0, help=HELP_RESTART_SERVICE_GRACE_SECONDS
    ),
) -> None:
    """
    Restart the managed background orchestrator using its last recorded launch configuration.

    Parameters:
        grace_seconds (float): Seconds to wait for a graceful stop before forcing relaunch.
    """
    settings = get_settings()
    try:
        pid = restart_background_service(settings=settings, grace_seconds=grace_seconds)
    except Exception as exc:
        console.print(
            _render_health_panel(
                TITLE_RESTART_BLOCKED,
                str(exc),
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    console.print(
        _render_health_panel(
            TITLE_SERVICE_RESTARTED,
            MESSAGE_BACKGROUND_SERVICE_RESTARTED.format(pid=pid),
            border_style="green",
        )
    )


@app.command("service-run", hidden=True)
def service_run(
    symbols: str = typer.Option(...),
    interval: str = typer.Option("1d"),
    lookback: str = typer.Option("180d"),
    poll_seconds: int = typer.Option(300),
    max_cycles: int | None = typer.Option(None),
    continuous: bool = typer.Option(True),
) -> None:
    """Internal background worker entrypoint."""
    settings = get_settings()
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not symbol_list:
        raise typer.BadParameter(MESSAGE_LAUNCH_SYMBOL_REQUIRED)
    run_service(
        settings=settings,
        symbols=symbol_list,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )


@app.command()
def menu() -> None:
    """Open the interactive terminal control room."""
    run_main_menu()


@app.command("latest-order")
def latest_order() -> None:
    """Show the latest paper order."""
    settings = get_settings()
    db = TradingDatabase(settings)
    order = db.latest_order()
    if order is None:
        console.print(Text(MESSAGE_NO_ORDERS_RECORDED, style="yellow"))
        raise typer.Exit(code=0)

    columns: list[str] = [
        "order_id",
        "created_at",
        "symbol",
        "side",
        "approved",
        "entry_price",
        "stop_loss",
        "take_profit",
        "position_size_pct",
        "confidence",
    ]
    table = Table(title=LABEL_LATEST_ORDER)
    for column in columns:
        table.add_column(column)
    rendered_order = [str(value) for value in order]
    table.add_row(*rendered_order)
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
