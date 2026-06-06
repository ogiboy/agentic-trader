from __future__ import annotations

import os
from typing import Any

import typer

from agentic_trader.cli_modules.app_callbacks import (
    apply_preference_update_callback,
    chat_with_persona_callback,
    interpret_operator_instruction_callback,
    memory_explorer_callback,
    refresh_trade_proposal_order_callback,
    retrieval_inspection_callback,
    run_ablation_callback,
    run_comparison_callback,
    run_replay_payload,
    run_service_callback,
    run_walk_forward_callback,
)
from agentic_trader.cli_modules.app_dashboard import dashboard_command_deps
from agentic_trader.cli_modules.dashboard_commands import (
    register_dashboard_commands,
)
from agentic_trader.cli_modules.doctor import run_doctor_command
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
    market_cache_payload as _market_cache_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    market_context_payload as _market_context_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    news_payload as _news_payload_impl,
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
    register_operator_readiness_commands,
)
from agentic_trader.cli_modules.proposal_desk import (
    register_proposal_desk_commands,
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
from agentic_trader.cli_modules.status_commands import (
    StatusCommandDeps,
    register_status_commands,
)
from agentic_trader.cli_modules.system_registration import register_cli_system_commands
from agentic_trader.cli_modules.tui_node import register_tui_command
from agentic_trader.memory.policy import memory_write_policy_snapshot
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
)


def _portfolio_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _finance_portfolio_payload(
        settings,
        open_db_provider=namespace._open_db,
        broker_adapter_provider=namespace.get_broker_adapter,
    )


def _preferences_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _preferences_payload_impl(settings, open_db=namespace._open_db)


def _journal_payload(namespace: Any, settings: Any, *, limit: int) -> dict[str, object]:
    return _journal_payload_impl(settings, open_db=namespace._open_db, limit=limit)


def _recent_runs_payload(
    namespace: Any, settings: Any, *, limit: int
) -> dict[str, object]:
    return _recent_runs_payload_impl(settings, open_db=namespace._open_db, limit=limit)


def _risk_report_payload(
    namespace: Any, settings: Any, *, report_date: str | None = None
) -> dict[str, object]:
    return _finance_risk_report_payload(
        settings,
        report_date=report_date,
        open_db_provider=namespace._open_db,
        broker_adapter_provider=namespace.get_broker_adapter,
    )


def _run_record_payload(
    namespace: Any, settings: Any, *, run_id: str | None = None
) -> dict[str, object]:
    return _run_record_payload_impl(settings, open_db=namespace._open_db, run_id=run_id)


def _trade_context_payload(
    namespace: Any, settings: Any, *, trade_id: str | None = None
) -> dict[str, object]:
    return _trade_context_payload_impl(
        settings, open_db=namespace._open_db, trade_id=trade_id
    )


def _market_context_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _market_context_payload_impl(settings, open_db=namespace._open_db)


def _canonical_analysis_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _canonical_analysis_payload_impl(settings, open_db=namespace._open_db)


def _canonical_analysis_lines(
    canonical_snapshot: CanonicalAnalysisSnapshot | None,
) -> list[str]:
    return _canonical_analysis_lines_impl(canonical_snapshot)


def _service_supervisor_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _service_supervisor_payload_impl(
        settings, read_text_tail=namespace._read_text_tail
    )


def _broker_payload(settings: Any) -> dict[str, object]:
    return _finance_broker_payload(settings)


def _finance_ops_payload(namespace: Any, settings: Any) -> dict[str, object]:
    return _finance_ops_payload_impl(
        settings,
        open_db_provider=namespace._open_db,
        broker_adapter_provider=namespace.get_broker_adapter,
    )


def _render_finance_ops(payload: dict[str, object]) -> None:
    _render_finance_ops_impl(payload)


def _render_position_plan_repair(payload: dict[str, object]) -> None:
    _render_position_plan_repair_impl(payload)


def _runtime_status_payload(view: Any, settings: Any) -> dict[str, object]:
    return _runtime_status_payload_impl(view, settings)


def _calendar_payload(
    namespace: Any, settings: Any, *, symbol: str | None = None
) -> dict[str, object]:
    return _calendar_payload_impl(settings, open_db=namespace._open_db, symbol=symbol)


def _news_payload(
    namespace: Any, settings: Any, *, symbol: str | None = None
) -> dict[str, object]:
    return _news_payload_impl(settings, open_db=namespace._open_db, symbol=symbol)


def _market_cache_payload(settings: Any) -> dict[str, object]:
    return _market_cache_payload_impl(settings)


def _operator_launcher(namespace: Any) -> None:
    run_operator_launcher(
        settings_provider=lambda: namespace.get_settings(),
        launcher_status_provider=lambda settings: (
            namespace.build_operator_launcher_status(settings)
        ),
        start_webgui=lambda settings: namespace.start_operator_webgui(settings),
        render_launcher_status=namespace._render_operator_launcher_status,
        render_webgui_status=namespace._render_webgui_service_status,
        render_health_panel=namespace._render_health_panel,
    )


def register_cli_app(app: typer.Typer, namespace: Any) -> None:
    register_cli_system_commands(
        app=app,
        settings_provider=lambda: namespace.get_settings(),
        emit_json=namespace._emit_json,
        service_namespace=namespace,
    )
    register_proposal_desk_commands(
        app,
        settings_provider=lambda: namespace.get_settings(),
        refresh_trade_proposal_order_provider=(
            refresh_trade_proposal_order_callback(namespace)
        ),
    )
    register_operator_readiness_commands(
        app,
        settings_provider=lambda: namespace.get_settings(),
        accelerator_provider=lambda: namespace._accelerator_payload(),
        cpu_count_provider=lambda: os.cpu_count(),
        total_memory_provider=lambda: namespace._total_memory_bytes(),
    )
    register_tui_command(app)
    register_research_commands(
        app,
        settings_provider=lambda: namespace.get_settings(),
        emit_json=namespace._emit_json,
    )
    register_launch_commands(
        app,
        settings_provider=lambda: namespace.get_settings(),
        ensure_ready=lambda settings: namespace.ensure_llm_ready(settings),
        run_once=namespace.run_once,
        persist_run=namespace.persist_run,
        run_service=namespace.run_service,
        start_background_service=namespace.start_background_service,
        render_execution=namespace.render_execution_panels,
    )
    register_locale_command(
        app,
        settings_provider=lambda: namespace.get_settings(),
        fresh_settings_provider=lambda: namespace.Settings(),
        persist_locale=lambda key, value: namespace.upsert_env_local_value(key, value),
        env_file_provider=lambda: namespace.ENV_LOCAL_FILE,
        emit_json=namespace._emit_json,
    )
    register_runtime_mode_commands(
        app,
        RuntimeModeCommandDeps(
            get_settings=lambda: namespace.get_settings(),
            emit_json=namespace._emit_json,
            transition_plan=_runtime_mode_transition_plan,
        ),
    )
    register_status_commands(app, _status_command_deps(namespace))
    register_record_commands(app, _record_command_deps(namespace))
    _register_app_entrypoints(app, namespace)
    register_dashboard_commands(app, dashboard_command_deps(namespace))
    register_market_commands(app, _market_command_deps(namespace))
    register_operator_chat_commands(app, _operator_chat_command_deps(namespace))
    register_service_commands(app, _service_command_deps(namespace))


def _register_app_entrypoints(app: typer.Typer, namespace: Any) -> None:
    @app.callback()
    def app_entry(
        ctx: typer.Context,
        locale: str | None = typer.Option(
            None,
            "--locale",
            help=namespace.HELP_LOCALE_OVERRIDE,
        ),
    ) -> None:
        resolved_locale = parse_ui_locale(locale)
        if resolved_locale is not None:
            previous_locale = os.environ.get(namespace.UI_LOCALE_ENV)

            def restore_locale() -> None:
                if previous_locale is None:
                    os.environ.pop(namespace.UI_LOCALE_ENV, None)
                    return
                os.environ[namespace.UI_LOCALE_ENV] = previous_locale

            ctx.call_on_close(restore_locale)
            os.environ[namespace.UI_LOCALE_ENV] = resolved_locale
        if ctx.invoked_subcommand is None:
            _operator_launcher(namespace)

    @app.command()
    def doctor(
        json_output: bool = typer.Option(False, "--json", help=namespace.HELP_JSON),
    ) -> None:
        """Check local environment, LLM, and database readiness."""
        run_doctor_command(
            settings=namespace.get_settings(),
            json_output=json_output,
            open_db=namespace._open_db,
            latest_order_formatter=namespace._format_latest_order,
            health_check=lambda settings: namespace.LocalLLM(settings).health_check(),
        )


def _status_command_deps(namespace: Any) -> StatusCommandDeps:
    return StatusCommandDeps(
        get_settings=lambda: namespace.get_settings(),
        emit_json=namespace._emit_json,
        portfolio_payload=lambda settings: _portfolio_payload(namespace, settings),
        runtime_status_payload=_runtime_status_payload,
        service_supervisor_payload=lambda settings: _service_supervisor_payload(
            namespace, settings
        ),
        broker_payload=_broker_payload,
        finance_ops_payload=lambda settings: _finance_ops_payload(namespace, settings),
        render_finance_ops=_render_finance_ops,
        render_position_plan_repair=_render_position_plan_repair,
        provider_diagnostics_payload=namespace.provider_diagnostics_payload,
        v1_readiness_payload=namespace.v1_readiness_payload,
        read_service_state=namespace.read_service_state,
        build_runtime_status_view=namespace.build_runtime_status_view,
        render_service_state=namespace._render_service_state,
        open_db=namespace._open_db,
        repair_missing_position_plans=namespace.repair_missing_position_plans,
    )


def _record_command_deps(namespace: Any) -> RecordCommandDeps:
    return RecordCommandDeps(
        get_settings=lambda: namespace.get_settings(),
        emit_json=namespace._emit_json,
        preferences_payload=lambda settings: _preferences_payload(namespace, settings),
        journal_payload=lambda settings, limit: _journal_payload(
            namespace, settings, limit=limit
        ),
        risk_report_payload=lambda settings, report_date=None: _risk_report_payload(
            namespace, settings, report_date=report_date
        ),
        run_record_payload=lambda settings, run_id=None: _run_record_payload(
            namespace, settings, run_id=run_id
        ),
        trade_context_payload=lambda settings, trade_id=None: _trade_context_payload(
            namespace, settings, trade_id=trade_id
        ),
        canonical_analysis_lines=_canonical_analysis_lines,
        run_replay_payload=lambda settings, run_id=None: run_replay_payload(
            namespace, settings, run_id=run_id
        ),
        memory_explorer_payload=memory_explorer_callback(namespace),
        retrieval_inspection_payload=retrieval_inspection_callback(namespace),
        memory_write_policy_snapshot=memory_write_policy_snapshot,
        open_db=namespace._open_db,
        ensure_ready=lambda settings: namespace.ensure_llm_ready(settings),
        run_comparison=run_comparison_callback(namespace),
        run_ablation=run_ablation_callback(namespace),
        run_walk_forward=run_walk_forward_callback(namespace),
    )


def _market_command_deps(namespace: Any) -> MarketCommandDeps:
    return MarketCommandDeps(
        get_settings=lambda: namespace.get_settings(),
        emit_json=namespace._emit_json,
        calendar_payload=lambda settings, symbol=None: _calendar_payload(
            namespace, settings, symbol=symbol
        ),
        news_payload=lambda settings, symbol=None: _news_payload(
            namespace, settings, symbol=symbol
        ),
        market_cache_payload=_market_cache_payload,
        fetch_ohlcv=namespace.fetch_ohlcv,
        news_research_plan=namespace.news_research_plan,
        classify_source_tier=namespace.classify_source_tier,
        research_cycle_plan_payload=namespace.research_cycle_plan_payload,
        run_research_cycle=namespace.run_research_cycle,
    )


def _operator_chat_command_deps(namespace: Any) -> OperatorChatCommandDeps:
    return OperatorChatCommandDeps(
        settings_provider=lambda: namespace.get_settings(),
        ensure_ready=lambda settings: namespace.ensure_llm_ready(settings),
        emit_json=namespace._emit_json,
        open_db=namespace._open_db,
        llm_factory=lambda settings: namespace.LocalLLM(settings),
        chat_with_persona=chat_with_persona_callback(namespace),
        append_chat_history=lambda settings, entry: namespace.append_chat_history(
            settings, entry
        ),
        database_factory=lambda settings: namespace.TradingDatabase(settings),
        interpret_instruction=interpret_operator_instruction_callback(namespace),
        apply_preference_update=apply_preference_update_callback(namespace),
    )


def _service_command_deps(namespace: Any) -> ServiceCommandDeps:
    return ServiceCommandDeps(
        get_settings=lambda: namespace.get_settings(),
        build_monitor_renderable=lambda settings: namespace.build_monitor_renderable(
            settings
        ),
        run_live_monitor=lambda settings, refresh_seconds: namespace.run_live_monitor(
            settings,
            refresh_seconds=refresh_seconds,
        ),
        read_service_state=namespace.read_service_state,
        is_process_alive=lambda pid: namespace.is_process_alive(pid),
        request_stop=lambda settings: namespace.request_stop(settings),
        database_factory=namespace.TradingDatabase,
        terminate_service_process=lambda pid: namespace.terminate_service_process(pid),
        restart_background_service=lambda settings, grace_seconds: (
            namespace.restart_background_service(
                settings=settings,
                grace_seconds=grace_seconds,
            )
        ),
        render_health_panel=namespace._render_health_panel,
        run_service=run_service_callback(namespace),
        run_main_menu=lambda: namespace.run_main_menu(),
    )
