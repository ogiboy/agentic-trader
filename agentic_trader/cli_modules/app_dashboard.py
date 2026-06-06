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
    """
    Create a provider that supplies the namespace's current Settings.
    
    Parameters:
        namespace (Any): Object exposing a `get_settings()` method that returns a `Settings` instance.
    
    Returns:
        Callable[[], Settings]: A zero-argument callable which, when called, returns the namespace's `Settings`.
    """
    def get_settings() -> Settings:
        return namespace.get_settings()

    return get_settings


def _open_read_db_provider(namespace: Any) -> Callable[[Settings], TradingDatabase]:
    """
    Create a callable that opens the trading database in read-only mode using the provided namespace.
    
    Parameters:
        namespace (Any): Object exposing an `_open_db(settings, read_only=...)` method used to open the database.
    
    Returns:
        Callable[[Settings], TradingDatabase]: A function that accepts `settings` and returns a `TradingDatabase` opened with read-only access.
    """
    def open_read_db(settings: Settings) -> TradingDatabase:
        return namespace._open_db(settings, read_only=True)

    return open_read_db


def _service_supervisor_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    """
    Create a callable that produces the service supervisor payload for a given settings object.
    
    Parameters:
        settings (Settings): Application settings used to build the payload.
    
    Returns:
        dict[str, object]: A payload dictionary describing the service supervisor.
    """
    def service_supervisor(settings: Settings) -> dict[str, object]:
        return _service_supervisor_payload_impl(
            settings, read_text_tail=namespace._read_text_tail
        )

    return service_supervisor


def _finance_ops_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Constructs a finance-operations payload function bound to the provided namespace.
    
    Parameters:
        namespace (Any): An object exposing `_open_db(settings, ...)` and `get_broker_adapter()` used by the returned payload builder.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that, given `settings`, produces the finance operations payload dictionary.
    """
    def finance_ops(settings: Settings) -> dict[str, object]:
        return _finance_ops_payload_impl(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return finance_ops


def _portfolio_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a portfolio payload provider bound to the given namespace.
    
    Parameters:
        namespace (Any): Object providing `_open_db(settings, ...)` and `get_broker_adapter()` used to open the database and obtain a broker adapter when building the portfolio payload.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns a portfolio payload dictionary constructed using the namespace's DB opener and broker adapter.
    """
    def portfolio(settings: Settings) -> dict[str, object]:
        return _finance_portfolio_payload(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return portfolio


def _preferences_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Builds a preferences payload provider bound to the given namespace.
    
    Parameters:
        namespace (Any): Object that provides an `_open_db(settings, ...)` method used by the returned provider to open the database.
    
    Returns:
        provider (Callable[[Settings], dict[str, object]]): A function that accepts `settings` and returns the preferences payload dictionary.
    """
    def preferences(settings: Settings) -> dict[str, object]:
        return _preferences_payload_impl(settings, open_db=namespace._open_db)

    return preferences


def _recent_runs_provider(namespace: Any) -> Callable[[Settings, int], dict[str, object]]:
    """
    Create a `recent_runs(settings, limit)` payload builder bound to the provided namespace.
    
    Parameters:
        namespace (Any): Object that supplies an `_open_db` callable used to open the database for payload construction.
    
    Returns:
        Callable[[Settings, int], dict[str, object]]: A function that produces the recent runs payload for the given settings and `limit`.
    """
    def recent_runs(settings: Settings, limit: int) -> dict[str, object]:
        return _recent_runs_payload_impl(
            settings, open_db=namespace._open_db, limit=limit
        )

    return recent_runs


def _journal_provider(namespace: Any) -> Callable[[Settings, int], dict[str, object]]:
    """
    Create a journal payload builder bound to the provided namespace.
    
    The returned callable accepts (settings, limit) and produces a dictionary payload containing journal entries read from the namespace's database.
    
    Parameters:
        namespace (Any): Object providing a `_open_db(settings, read_only=...)` method used to open the database for reading.
    
    Returns:
        Callable[[Settings, int], dict[str, object]]: A function that takes `settings` and an integer `limit` and returns the journal payload.
    """
    def journal(settings: Settings, limit: int) -> dict[str, object]:
        return _journal_payload_impl(settings, open_db=namespace._open_db, limit=limit)

    return journal


def _risk_report_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a provider that returns a finance risk report payload using the namespace's database and broker adapter.
    
    Parameters:
        namespace (Any): Object that exposes database opening and broker adapter access used by the provider.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns a risk report payload dictionary.
    """
    def risk_report(settings: Settings) -> dict[str, object]:
        return _finance_risk_report_payload(
            settings,
            open_db_provider=namespace._open_db,
            broker_adapter_provider=namespace.get_broker_adapter,
        )

    return risk_report


def _run_record_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a run-record payload builder bound to the provided namespace.
    
    Parameters:
        namespace (Any): Object providing an `_open_db(settings, read_only=...)` method used to open the trading database.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns the run-record payload dictionary.
    """
    def run_record(settings: Settings) -> dict[str, object]:
        return _run_record_payload_impl(settings, open_db=namespace._open_db)

    return run_record


def _trade_context_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a trade-context payload builder bound to the given namespace.
    
    Parameters:
        namespace (Any): Object providing an `_open_db(settings, read_only=...)` callable used to open the trading database.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns the trade-context payload dictionary.
    """
    def trade_context(settings: Settings) -> dict[str, object]:
        return _trade_context_payload_impl(settings, open_db=namespace._open_db)

    return trade_context


def _market_context_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a market-context payload provider bound to the provided namespace.
    
    Parameters:
        namespace (Any): An object that exposes `_open_db(settings, ...)` used to open the trading database for payload construction.
    
    Returns:
        provider (Callable[[Settings], dict[str, object]]): A callable that accepts `settings` and returns the market context payload dictionary.
    """
    def market_context(settings: Settings) -> dict[str, object]:
        return _market_context_payload_impl(settings, open_db=namespace._open_db)

    return market_context


def _canonical_analysis_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    """
    Create a provider that builds the canonical analysis payload using the namespace's database opener.
    
    Parameters:
    	namespace (Any): An object providing application integrations; must expose `_open_db(settings, read_only=...)`.
    
    Returns:
    	Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns the canonical analysis payload dictionary.
    """
    def canonical_analysis(settings: Settings) -> dict[str, object]:
        return _canonical_analysis_payload_impl(settings, open_db=namespace._open_db)

    return canonical_analysis


def _run_replay_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Builds and returns a `run_replay` payload function bound to the given namespace.
    
    The returned callable produces the payload for replaying a run using the namespace's configured database and manager notes.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns a run-replay payload dictionary.
    """
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    def run_replay(settings: Settings) -> dict[str, object]:
        """
        Build a payload for replaying a previously recorded run.
        
        Parameters:
            settings (Settings): Application configuration used to construct the replay payload.
        
        Returns:
            dict[str, object]: Payload dictionary containing replay data and metadata for the given settings.
        """
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
    """
    Return a memory-explorer payload builder bound to the provided namespace.
    
    The returned callable accepts (settings, use_latest_run, limit) and produces a dictionary payload for the memory explorer.
    
    Returns:
        Callable[[Settings, bool, int], dict[str, object]]: Callable that takes `settings`, `use_latest_run`, and `limit` and returns a memory explorer payload dictionary.
    """
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
    """
    Create a retrieval-inspection payload provider bound to the given namespace.
    
    The returned callable accepts a `Settings` object and produces a dictionary payload containing retrieval inspection data for the dashboard.
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that builds and returns the retrieval inspection payload when invoked with `settings`.
    """
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    def retrieval_inspection(settings: Settings) -> dict[str, object]:
        """
        Builds the retrieval inspection payload for the dashboard.
        
        Parameters:
            settings (Settings): Application settings used to access configuration and data.
        
        Returns:
            dict[str, object]: Payload containing retrieval inspection data for the UI.
        """
        return _retrieval_inspection_payload_impl(
            settings,
            run_record_payload=run_record,
        )

    return retrieval_inspection


def _calendar_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a calendar payload provider bound to the given namespace.
    
    Parameters:
    	namespace (Any): Namespace object that provides the `_open_db` callable used to open the database for payload construction.
    
    Returns:
    	calendar_provider (Callable[[Settings], dict[str, object]]): A callable that accepts `settings` and returns a dictionary containing the calendar payload.
    """
    def calendar(settings: Settings) -> dict[str, object]:
        return _calendar_payload_impl(settings, open_db=namespace._open_db)

    return calendar


def _news_provider(namespace: Any) -> Callable[[Settings], dict[str, object]]:
    """
    Create a news payload builder bound to the provided namespace.
    
    Parameters:
        namespace (Any): Object that provides the database opener used to build the news payload (expects an `_open_db` attribute).
    
    Returns:
        Callable[[Settings], dict[str, object]]: A function that accepts `settings` and returns a dictionary containing the news payload, using the namespace's database opener.
    """
    def news(settings: Settings) -> dict[str, object]:
        return _news_payload_impl(settings, open_db=namespace._open_db)

    return news


def _provider_diagnostics_provider(
    namespace: Any,
) -> Callable[[Settings], dict[str, object]]:
    """
    Create a diagnostics payload provider bound to the given namespace.
    
    Returns:
        A callable that accepts a Settings object and returns the provider diagnostics payload as a dictionary.
    """
    def provider_diagnostics(settings: Settings) -> dict[str, object]:
        return namespace.provider_diagnostics_payload(settings)

    return provider_diagnostics


def _v1_readiness_provider(namespace: Any) -> Callable[[Settings, bool], dict[str, object]]:
    """
    Create a v1 readiness payload provider bound to the given namespace.
    
    Parameters:
        namespace (Any): Object that exposes a `v1_readiness_payload(settings, check_provider=bool)` callable.
    
    Returns:
        Callable[[Settings, bool], dict[str, object]]: A function `v1_readiness(settings, check_provider)` that returns the readiness payload dictionary produced by `namespace.v1_readiness_payload`.
    """
    def v1_readiness(settings: Settings, check_provider: bool) -> dict[str, object]:
        return namespace.v1_readiness_payload(
            settings, check_provider=check_provider
        )

    return v1_readiness


def _runtime_mode_provider(namespace: Any) -> Callable[[Settings], Any]:
    """
    Return a provider that produces a transition plan to switch the runtime mode to "operation".
    
    The returned callable accepts a Settings instance and yields a transition plan object describing the actions required to change the application's runtime mode to "operation".
    
    Returns:
        Callable[[Settings], Any]: A callable that takes `settings` and returns a transition plan object for moving to the "operation" mode.
    """
    def runtime_mode_operation(settings: Settings) -> Any:
        return _runtime_mode_transition_plan(
            settings, target_mode="operation", check_provider=False
        )

    return runtime_mode_operation


def dashboard_command_deps(namespace: Any) -> DashboardCommandDeps:
    """
    Builds a DashboardCommandDeps instance with provider callables wired to the given namespace.
    
    The returned DashboardCommandDeps contains core services (settings, JSON emission, UI payload, DB access, formatting), payload builders for dashboard and observer features (runtime status, finance/portfolio, runs/journal/risk, market/trade contexts, analysis, replay, memory and retrieval inspection, calendar, news, etc.), operator and hardware helpers, and IO/state hooks — each adapter is bound to the corresponding function or method from the provided namespace.
    
    Parameters:
        namespace (Any): The module-like object supplying application-specific implementations and helpers
            (e.g., settings access, DB opener, adapter factories, I/O hooks) that are bound into the
            returned dependency structure.
    
    Returns:
        DashboardCommandDeps: A dependency bundle of callables and helpers wired to `namespace` for use
        by dashboard, evidence, and observer payload builders.
    """
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
    """
    Builds a dashboard snapshot payload for the given namespace and settings.
    
    Parameters:
        namespace (Any): Namespace providing application integrations (settings access, DB/opening, adapters, and payload builders).
        settings (Any): Runtime settings used to construct the payload.
        log_limit (int): Maximum number of log entries to include in the snapshot.
        check_provider (bool): If True, include provider readiness checks in the snapshot.
    
    Returns:
        payload (dict[str, object]): A mapping containing the assembled dashboard snapshot payload.
    """
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
    """
    Builds an evidence bundle containing dashboard artifacts and metadata.
    
    Parameters:
        namespace (Any): CLI/module namespace that provides application wiring (settings, DB access, adapters and payload providers).
        settings (Any): Runtime settings used to build the evidence bundle.
        output_dir (Path | None): Optional directory where generated evidence files will be written.
        label (str | None): Optional human-readable label to attach to the evidence bundle.
        log_limit (int): Maximum number of log entries to include for each component.
        include_latest_smoke (bool): Whether to include the latest smoke-test artifacts in the bundle.
        check_provider (bool): Whether to perform provider readiness checks when gathering evidence.
    
    Returns:
        dict[str, object]: A mapping containing the assembled evidence artifacts and associated metadata.
    """
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
    """
    Build the observer API response payload for a given API path.
    
    Parameters:
        path (str): Observer API path to build the payload for (e.g., endpoint or resource identifier).
        log_limit (int): Maximum number of log entries to include in the payload.
    
    Returns:
        tuple[int, dict[str, object]]: A pair of HTTP status code and the observer API payload mapping.
    """
    return _build_observer_api_payload(
        settings,
        deps=dashboard_command_deps(namespace),
        path=path,
        log_limit=log_limit,
    )
