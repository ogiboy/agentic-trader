import os
import shutil
import sys as _sys
from collections.abc import Mapping
from pathlib import Path

import typer
from dotenv import set_key
from pandas import DataFrame

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
from agentic_trader.cli_modules.common import emit_json as _emit_json
from agentic_trader.cli_modules.common import open_db as _open_db
from agentic_trader.cli_modules.dashboard_commands import (
    DashboardCommandDeps,
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
from agentic_trader.cli_modules.dashboard_commands import (
    register_dashboard_commands,
)
from agentic_trader.cli_modules.doctor import run_doctor_command
from agentic_trader.cli_modules.execution_rendering import render_execution_panels
from agentic_trader.cli_modules.finance_rendering import (
    render_finance_ops as _render_finance_ops_impl,
)
from agentic_trader.cli_modules.finance_rendering import (
    render_position_plan_repair as _render_position_plan_repair_impl,
)
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
    risk_report_payload as _finance_risk_report_payload,
)
from agentic_trader.cli_modules.launch_commands import register_launch_commands
from agentic_trader.cli_modules.locale_commands import (
    parse_ui_locale,
    register_locale_command,
    ui_payload,
)
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
from agentic_trader.cli_modules.operator_chat_commands import (
    OperatorChatCommandDeps,
    register_operator_chat_commands,
)
from agentic_trader.cli_modules.operator_launcher_command import run_operator_launcher
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
from agentic_trader.cli_modules.record_payloads import (
    journal_payload as _journal_payload_impl,
)
from agentic_trader.cli_modules.record_payloads import (
    preferences_payload as _preferences_payload_impl,
)
from agentic_trader.cli_modules.record_payloads import (
    recent_runs_payload as _recent_runs_payload_impl,
)
from agentic_trader.cli_modules.record_payloads import (
    run_record_payload as _run_record_payload_impl,
)
from agentic_trader.cli_modules.record_payloads import (
    trade_context_payload as _trade_context_payload_impl,
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
from agentic_trader.cli_modules.runtime_mode_commands import (
    RuntimeModeCommandDeps,
    register_runtime_mode_commands,
)
from agentic_trader.cli_modules.runtime_modes import (
    runtime_mode_transition_plan as _runtime_mode_transition_plan,
)
from agentic_trader.cli_modules.service_commands import (
    ServiceCommandDeps,
    register_service_commands,
)
from agentic_trader.cli_modules.service_rendering import (
    format_latest_order as _format_latest_order,
)
from agentic_trader.cli_modules.service_rendering import (
    read_text_tail as _read_text_tail,
)
from agentic_trader.cli_modules.service_rendering import (
    render_health_panel as _render_health_panel,
)
from agentic_trader.cli_modules.service_rendering import (
    render_service_state as _render_service_state,
)
from agentic_trader.cli_modules.status_commands import (
    StatusCommandDeps,
    register_status_commands,
)
from agentic_trader.cli_modules.system_registration import register_cli_system_commands
from agentic_trader.cli_modules.system_rendering import (
    render_operator_launcher_status as _render_operator_launcher_status,
)
from agentic_trader.cli_modules.system_rendering import (
    render_webgui_service_status as _render_webgui_service_status,
)
from agentic_trader.cli_modules.tui_node import (
    NodeCommandSet,
    register_tui_command,
)
from agentic_trader.cli_modules.tui_node import (
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
    ChatPersona,
    InvestmentPreferences,
    OperatorInstruction,
    PreferenceUpdate,
    TradeProposalRecord,
)
from agentic_trader.storage.db import TradingDatabase
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
    HELP_CLI_APP,
    HELP_JSON,
    HELP_LOCALE_OVERRIDE,
    UI_LOCALE_ENV,
)
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import (
    ensure_llm_ready,
    restart_background_service,
    run_service,
    start_background_service,
    terminate_service_process,
)

__all__ = [
    "build_camofox_service_status",
    "build_model_service_status",
    "build_setup_status",
    "build_webgui_service_status",
    "pull_model",
    "read_tool_ownership_payload",
    "start_camofox_service",
    "start_model_service",
    "stop_camofox_service",
    "stop_model_service",
    "stop_webgui_service",
    "validate_ownership_mode",
    "write_tool_ownership",
]

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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL_FILE = PROJECT_ROOT / ".env.local"


def upsert_env_local_value(key: str, value: str) -> None:
    set_key(ENV_LOCAL_FILE, key, value, quote_mode="never")
    os.environ[key] = value


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


def _chat_with_persona_provider(
    *,
    llm: LocalLLM,
    db: TradingDatabase,
    settings: Settings,
    persona: ChatPersona,
    user_message: str,
) -> str:
    return chat_with_persona(
        llm=llm,
        db=db,
        settings=settings,
        persona=persona,
        user_message=user_message,
    )


def _interpret_operator_instruction_provider(
    *,
    llm: LocalLLM,
    db: TradingDatabase,
    settings: Settings,
    user_message: str,
    allow_fallback: bool,
) -> OperatorInstruction:
    return interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=user_message,
        allow_fallback=allow_fallback,
    )


def _apply_preference_update_provider(
    db: TradingDatabase, update: PreferenceUpdate
) -> InvestmentPreferences:
    return apply_preference_update(db, update)


def _run_service_provider(
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> object:
    return run_service(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )


register_cli_system_commands(
    app=app,
    settings_provider=lambda: get_settings(),
    emit_json=_emit_json,
    service_namespace=_sys.modules[__name__],
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
register_locale_command(
    app,
    settings_provider=lambda: get_settings(),
    fresh_settings_provider=lambda: Settings(),
    persist_locale=lambda key, value: upsert_env_local_value(key, value),
    env_file_provider=lambda: ENV_LOCAL_FILE,
    emit_json=_emit_json,
)
register_runtime_mode_commands(
    app,
    RuntimeModeCommandDeps(
        get_settings=lambda: get_settings(),
        emit_json=_emit_json,
        transition_plan=_runtime_mode_transition_plan,
    ),
)
QA_ARTIFACTS_ROOT = PROJECT_ROOT / ".ai" / "qa" / "artifacts"


def resolve_tui_node_commands(tui_dir: Path) -> NodeCommandSet | None:
    return _resolve_tui_node_commands(tui_dir, which=shutil.which)


def _portfolio_payload(settings: Settings) -> dict[str, object]:
    return _finance_portfolio_payload(
        settings,
        open_db_provider=_open_db,
        broker_adapter_provider=get_broker_adapter,
    )


def _preferences_payload(settings: Settings) -> dict[str, object]:
    return _preferences_payload_impl(settings, open_db=_open_db)


def _journal_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    return _journal_payload_impl(settings, open_db=_open_db, limit=limit)


def _recent_runs_payload(settings: Settings, *, limit: int) -> dict[str, object]:
    return _recent_runs_payload_impl(settings, open_db=_open_db, limit=limit)


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
    return _run_record_payload_impl(settings, open_db=_open_db, run_id=run_id)


def _trade_context_payload(
    settings: Settings, *, trade_id: str | None = None
) -> dict[str, object]:
    return _trade_context_payload_impl(settings, open_db=_open_db, trade_id=trade_id)


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
    run_operator_launcher(
        settings_provider=lambda: get_settings(),
        launcher_status_provider=lambda settings: build_operator_launcher_status(
            settings
        ),
        start_webgui=lambda settings: start_operator_webgui(settings),
        render_launcher_status=_render_operator_launcher_status,
        render_webgui_status=_render_webgui_service_status,
        render_health_panel=_render_health_panel,
    )


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
        memory_explorer_payload=lambda settings, use_latest_run, limit: (
            _memory_explorer_payload(
                settings, use_latest_run=use_latest_run, limit=limit
            )
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
register_operator_chat_commands(
    app,
    OperatorChatCommandDeps(
        settings_provider=lambda: get_settings(),
        ensure_ready=lambda settings: ensure_llm_ready(settings),
        emit_json=_emit_json,
        open_db=_open_db,
        llm_factory=lambda settings: LocalLLM(settings),
        chat_with_persona=_chat_with_persona_provider,
        append_chat_history=lambda settings, entry: append_chat_history(
            settings, entry
        ),
        database_factory=lambda settings: TradingDatabase(settings),
        interpret_instruction=_interpret_operator_instruction_provider,
        apply_preference_update=_apply_preference_update_provider,
    ),
)
register_service_commands(
    app,
    ServiceCommandDeps(
        get_settings=lambda: get_settings(),
        build_monitor_renderable=lambda settings: build_monitor_renderable(settings),
        run_live_monitor=lambda settings, refresh_seconds: run_live_monitor(
            settings,
            refresh_seconds=refresh_seconds,
        ),
        read_service_state=read_service_state,
        is_process_alive=lambda pid: is_process_alive(pid),
        request_stop=lambda settings: request_stop(settings),
        database_factory=TradingDatabase,
        terminate_service_process=lambda pid: terminate_service_process(pid),
        restart_background_service=lambda settings, grace_seconds: (
            restart_background_service(
                settings=settings,
                grace_seconds=grace_seconds,
            )
        ),
        render_health_panel=_render_health_panel,
        run_service=_run_service_provider,
        run_main_menu=lambda: run_main_menu(),
    ),
)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
