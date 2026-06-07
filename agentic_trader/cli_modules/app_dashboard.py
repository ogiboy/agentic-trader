from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentic_trader.config import Settings
from agentic_trader.cli_modules.dashboard_commands import (
    DashboardCommandDeps,
    build_dashboard_snapshot_payload as _build_dashboard_snapshot_payload,
)
from agentic_trader.cli_modules.dashboard_commands import (
    build_evidence_bundle as _build_dashboard_evidence_bundle,
)
from agentic_trader.cli_modules.dashboard_commands import (
    build_observer_api_payload as _build_observer_api_payload,
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
from agentic_trader.cli_modules.locale_commands import ui_payload
from agentic_trader.cli_modules.observer_payloads import (
    calendar_payload as _calendar_payload_impl,
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
    build_hardware_profile_payload,
    build_operator_workflow_payload,
)
from agentic_trader.cli_modules.proposal_desk import (
    proposal_candidates_payload,
    trade_proposals_payload,
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
    research_sidecar_payload as _research_sidecar_payload,
)
from agentic_trader.cli_modules.run_reports import (
    manager_override_notes as _manager_override_notes,
)
from agentic_trader.cli_modules.run_reports import (
    manager_resolution_notes as _manager_resolution_notes,
)
from agentic_trader.cli_modules.runtime_modes import (
    runtime_mode_transition_plan as _runtime_mode_transition_plan,
)
from agentic_trader.storage.db import TradingDatabase


def _settings_provider(namespace: Any) -> Callable[[], Settings]:
    def get_settings() -> Settings:
        return namespace.get_settings()

    return get_settings


def _open_read_db_provider(namespace: Any) -> Callable[[Settings], TradingDatabase]:
    def open_read_db(settings: Settings) -> TradingDatabase:
        return namespace._open_db(settings, read_only=True)

    return open_read_db


def _service_supervisor_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    def service_supervisor(settings: Settings) -> dict[str, object]:
        return _service_supervisor_payload_impl(
            settings, read_text_tail=namespace._read_text_tail
        )

    return service_supervisor


def _finance_ops_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def finance_ops(settings: Settings) -> dict[str, object]:
        return _finance_ops_payload_impl(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return finance_ops


def _portfolio_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def portfolio(settings: Settings) -> dict[str, object]:
        return _finance_portfolio_payload(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return portfolio


def _preferences_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def preferences(settings: Settings) -> dict[str, object]:
        return _preferences_payload_impl(settings, open_db=namespace._open_db)

    return preferences


def _recent_runs_provider(namespace: Any) -> Callable[[Settings, int], dict[str, object]]:
    def recent_runs(settings: Settings, limit: int) -> dict[str, object]:
        return _recent_runs_payload_impl(
            settings, open_db=namespace._open_db, limit=limit
        )

    return recent_runs


def _journal_provider(namespace: Any) -> Callable[[Settings, int], dict[str, object]]:
    def journal(settings: Settings, limit: int) -> dict[str, object]:
        return _journal_payload_impl(settings, open_db=namespace._open_db, limit=limit)

    return journal


def _risk_report_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def risk_report(settings: Settings) -> dict[str, object]:
        return _finance_risk_report_payload(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return risk_report


def _run_record_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def run_record(settings: Settings) -> dict[str, object]:
        return _run_record_payload_impl(settings, open_db=namespace._open_db)

    return run_record


def _trade_context_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def trade_context(settings: Settings) -> dict[str, object]:
        return _trade_context_payload_impl(settings, open_db=namespace._open_db)

    return trade_context


def _market_context_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def market_context(settings: Settings) -> dict[str, object]:
        return _market_context_payload_impl(settings, open_db=namespace._open_db)

    return market_context


def _canonical_analysis_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    def canonical_analysis(settings: Settings) -> dict[str, object]:
        return _canonical_analysis_payload_impl(settings, open_db=namespace._open_db)

    return canonical_analysis


def _run_replay_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    def run_replay(settings: Settings) -> dict[str, object]:
        return _run_replay_payload_impl(
            settings,
            run_record_payload=run_record,
            manager_override_notes=_manager_override_notes,
            manager_resolution_notes=_manager_resolution_notes,
        )

    return run_replay


def _memory_explorer_provider(
    namespace: Any,
) -> Callable[[Settings, bool, int], dict[str, object]]:
    def memory_explorer(
        settings: Settings, use_latest_run: bool, limit: int
    ) -> dict[str, object]:
        return _memory_explorer_payload_impl(
            settings,
            open_db=namespace._open_db,
            limit=limit,
            use_latest_run=use_latest_run,
        )

    return memory_explorer


def _retrieval_inspection_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    def retrieval_inspection(settings: Settings) -> dict[str, object]:
        return _retrieval_inspection_payload_impl(
            settings,
            run_record_payload=run_record,
        )

    return retrieval_inspection


def _calendar_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def calendar(settings: Settings) -> dict[str, object]:
        return _calendar_payload_impl(settings, open_db=namespace._open_db)

    return calendar


def _news_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    def news(settings: Settings) -> dict[str, object]:
        return _news_payload_impl(settings, open_db=namespace._open_db)

    return news


def _provider_diagnostics_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    def provider_diagnostics(settings: Settings) -> dict[str, object]:
        return namespace.provider_diagnostics_payload(settings)

    return provider_diagnostics


def _v1_readiness_provider(namespace: Any) -> Callable[[Settings, bool], dict[str, object]]:
    def v1_readiness(settings: Settings, check_provider: bool) -> dict[str, object]:
        return namespace.v1_readiness_payload(
            settings, check_provider=check_provider
        )

    return v1_readiness


def _runtime_mode_provider(namespace: Any) -> Callable[[Settings], Any]:
    def runtime_mode_operation(settings: Settings) -> Any:
        return _runtime_mode_transition_plan(
            settings, target_mode="operation", check_provider=False
        )

    return runtime_mode_operation


def dashboard_command_deps(namespace: Any) -> DashboardCommandDeps:
    return DashboardCommandDeps(
        get_settings=_settings_provider(namespace),
        emit_json=namespace._emit_json,
        ui_payload=ui_payload,
        open_read_db=_open_read_db_provider(namespace),
        latest_order=namespace._format_latest_order,
        runtime_status_payload=_runtime_status_payload_impl,
        service_supervisor_payload=_service_supervisor_provider(namespace),
        broker_payload=_finance_broker_payload,
        finance_ops_payload=_finance_ops_provider(namespace),
        portfolio_payload=_portfolio_provider(namespace),
        preferences_payload=_preferences_provider(namespace),
        recent_runs_payload=_recent_runs_provider(namespace),
        proposal_candidates_payload=lambda settings, limit: proposal_candidates_payload(
            settings, limit=limit
        ),
        trade_proposals_payload=lambda settings, limit: trade_proposals_payload(
            settings, limit=limit
        ),
        journal_payload=_journal_provider(namespace),
        risk_report_payload=_risk_report_provider(namespace),
        run_record_payload=_run_record_provider(namespace),
        trade_context_payload=_trade_context_provider(namespace),
        market_context_payload=_market_context_provider(namespace),
        canonical_analysis_payload=_canonical_analysis_provider(namespace),
        run_replay_payload=_run_replay_provider(namespace),
        memory_explorer_payload=_memory_explorer_provider(namespace),
        retrieval_inspection_payload=_retrieval_inspection_provider(namespace),
        chat_history_payload=_chat_history_payload_impl,
        calendar_payload=_calendar_provider(namespace),
        news_payload=_news_provider(namespace),
        market_cache_payload=_market_cache_payload_impl,
        research_sidecar_payload=_research_sidecar_payload,
        provider_diagnostics_payload=_provider_diagnostics_provider(namespace),
        v1_readiness_payload=_v1_readiness_provider(namespace),
        runtime_mode_operation=_runtime_mode_provider(namespace),
        operator_workflow=build_operator_workflow_payload,
        hardware_profile=build_hardware_profile_payload,
        read_service_events=namespace.read_service_events,
        read_service_state=namespace.read_service_state,
        build_runtime_status_view=namespace.build_runtime_status_view,
    )


def build_dashboard_snapshot_payload(
    namespace: Any, settings: Any, *, log_limit: int = 14, check_provider: bool = False
) -> dict[str, object]:
    return _build_dashboard_snapshot_payload(
        settings,
        deps=dashboard_command_deps(namespace),
        log_limit=log_limit,
        check_provider=check_provider,
    )


def build_evidence_bundle(
    namespace: Any,
    settings: Any,
    *,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    return _build_dashboard_evidence_bundle(
        settings,
        deps=dashboard_command_deps(namespace),
        output_dir=output_dir,
        label=label,
        log_limit=log_limit,
        include_latest_smoke=include_latest_smoke,
        check_provider=check_provider,
    )


def build_observer_api_payload(
    namespace: Any, settings: Any, *, path: str, log_limit: int = 14
) -> tuple[int, dict[str, object]]:
    return _build_observer_api_payload(
        settings,
        deps=dashboard_command_deps(namespace),
        path=path,
        log_limit=log_limit,
    )
