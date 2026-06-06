from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import (
    HELP_EVIDENCE_BUNDLE_INCLUDE_LATEST_SMOKE,
    HELP_EVIDENCE_BUNDLE_LABEL,
    HELP_EVIDENCE_BUNDLE_OUTPUT_DIR,
    HELP_JSON,
    HELP_OBSERVER_API_ALLOW_NONLOCAL,
    HELP_OBSERVER_API_HOST,
    HELP_OBSERVER_API_PORT,
    HELP_PROVIDER_CHECK,
    HELP_RUNTIME_EVENT_LIMIT,
    LABEL_ARTIFACT,
    LABEL_CREATED,
    LABEL_CYCLE,
    LABEL_LEVEL,
    LABEL_MESSAGE,
    LABEL_PATH,
    LABEL_SYMBOL,
    LABEL_TYPE,
    MESSAGE_EVIDENCE_BUNDLE_WRITTEN,
    MESSAGE_OBSERVER_API_LISTENING,
    MESSAGE_OBSERVER_API_NONLOCAL_BLOCKED,
    TITLE_EVIDENCE_BUNDLE,
    TITLE_OBSERVER_API,
    TITLE_OBSERVER_API_BLOCKED,
    TITLE_QA_EVIDENCE_BUNDLE,
    TITLE_RUNTIME_EVENTS,
)
from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.dashboard_snapshot import (
    DashboardSnapshotCollectors,
    build_dashboard_snapshot,
)
from agentic_trader.cli_modules.evidence_bundle import (
    EvidenceBundleCollectors,
)
from agentic_trader.cli_modules.evidence_bundle import (
    build_evidence_bundle as _build_evidence_bundle,
)
from agentic_trader.config import Settings
from agentic_trader.observer_api import serve_observer_api
from agentic_trader.runtime_status import RuntimeStatusView
from agentic_trader.security import is_loopback_host
from agentic_trader.storage.db import OrderRow, TradingDatabase


@dataclass(frozen=True)
class DashboardCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    ui_payload: Callable[[str], dict[str, object]]
    open_read_db: Callable[[Settings], TradingDatabase]
    latest_order: Callable[[OrderRow | None], str]
    runtime_status_payload: Callable[[RuntimeStatusView, Settings], dict[str, object]]
    service_supervisor_payload: Callable[[Settings], dict[str, object]]
    broker_payload: Callable[[Settings], dict[str, object]]
    finance_ops_payload: Callable[[Settings], dict[str, object]]
    portfolio_payload: Callable[[Settings], dict[str, object]]
    preferences_payload: Callable[[Settings], dict[str, object]]
    recent_runs_payload: Callable[[Settings, int], dict[str, object]]
    proposal_candidates_payload: Callable[[Settings, int], dict[str, object]]
    trade_proposals_payload: Callable[[Settings, int], dict[str, object]]
    journal_payload: Callable[[Settings, int], dict[str, object]]
    risk_report_payload: Callable[[Settings], dict[str, object]]
    run_record_payload: Callable[[Settings], dict[str, object]]
    trade_context_payload: Callable[[Settings], dict[str, object]]
    market_context_payload: Callable[[Settings], dict[str, object]]
    canonical_analysis_payload: Callable[[Settings], dict[str, object]]
    run_replay_payload: Callable[[Settings], dict[str, object]]
    memory_explorer_payload: Callable[[Settings, bool, int], dict[str, object]]
    retrieval_inspection_payload: Callable[[Settings], dict[str, object]]
    chat_history_payload: Callable[[Settings], dict[str, object]]
    calendar_payload: Callable[[Settings], dict[str, object]]
    news_payload: Callable[[Settings], dict[str, object]]
    market_cache_payload: Callable[[Settings], dict[str, object]]
    research_sidecar_payload: Callable[[Settings], dict[str, object]]
    provider_diagnostics_payload: Callable[[Settings], dict[str, object]]
    v1_readiness_payload: Callable[[Settings, bool], dict[str, object]]
    runtime_mode_operation: Callable[[Settings], Any]
    operator_workflow: Callable[[Settings], object]
    hardware_profile: Callable[[Settings], object]
    read_service_events: Any
    read_service_state: Any
    build_runtime_status_view: Any


def register_dashboard_commands(app: typer.Typer, deps: DashboardCommandDeps) -> None:
    _register_logs_command(app, deps)
    _register_dashboard_snapshot_command(app, deps)
    _register_evidence_bundle_command(app, deps)
    _register_observer_api_command(app, deps)


def build_dashboard_snapshot_payload(
    settings: Settings,
    *,
    deps: DashboardCommandDeps,
    log_limit: int = 14,
    check_provider: bool = False,
) -> dict[str, object]:
    return build_dashboard_snapshot(
        settings,
        collectors=DashboardSnapshotCollectors(
            ui_payload=deps.ui_payload,
            open_db=deps.open_read_db,
            latest_order=deps.latest_order,
            runtime_status_payload=deps.runtime_status_payload,
            service_supervisor_payload=deps.service_supervisor_payload,
            broker_payload=deps.broker_payload,
            finance_ops_payload=deps.finance_ops_payload,
            portfolio_payload=deps.portfolio_payload,
            preferences_payload=deps.preferences_payload,
            recent_runs_payload=deps.recent_runs_payload,
            proposal_candidates_payload=deps.proposal_candidates_payload,
            trade_proposals_payload=deps.trade_proposals_payload,
            journal_payload=deps.journal_payload,
            risk_report_payload=deps.risk_report_payload,
            run_record_payload=deps.run_record_payload,
            trade_context_payload=deps.trade_context_payload,
            market_context_payload=deps.market_context_payload,
            canonical_analysis_payload=deps.canonical_analysis_payload,
            run_replay_payload=deps.run_replay_payload,
            memory_explorer_payload=deps.memory_explorer_payload,
            retrieval_inspection_payload=deps.retrieval_inspection_payload,
            chat_history_payload=deps.chat_history_payload,
            calendar_payload=deps.calendar_payload,
            news_payload=deps.news_payload,
            market_cache_payload=deps.market_cache_payload,
            research_sidecar_payload=deps.research_sidecar_payload,
            provider_diagnostics_payload=deps.provider_diagnostics_payload,
            v1_readiness_payload=deps.v1_readiness_payload,
        ),
        log_limit=log_limit,
        check_provider=check_provider,
    )


def build_evidence_bundle(
    settings: Settings,
    *,
    deps: DashboardCommandDeps,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    return _build_evidence_bundle(
        settings,
        collectors=EvidenceBundleCollectors(
            dashboard_snapshot=lambda settings, log_limit, check_provider: build_dashboard_snapshot_payload(
                settings,
                deps=deps,
                log_limit=log_limit,
                check_provider=check_provider,
            ),
            status_payload=deps.runtime_status_payload,
            broker_payload=deps.broker_payload,
            finance_ops_payload=deps.finance_ops_payload,
            provider_diagnostics=deps.provider_diagnostics_payload,
            v1_readiness=deps.v1_readiness_payload,
            supervisor_payload=deps.service_supervisor_payload,
            runtime_mode_operation=deps.runtime_mode_operation,
            operator_workflow=deps.operator_workflow,
            research_payload=deps.research_sidecar_payload,
            hardware_profile=deps.hardware_profile,
        ),
        output_dir=output_dir,
        label=label,
        log_limit=log_limit,
        include_latest_smoke=include_latest_smoke,
        check_provider=check_provider,
    )


def build_observer_api_payload(
    settings: Settings,
    *,
    deps: DashboardCommandDeps,
    path: str,
    log_limit: int = 14,
) -> tuple[int, dict[str, object]]:
    if path in {"/", "/dashboard"}:
        return 200, build_dashboard_snapshot_payload(
            settings, deps=deps, log_limit=log_limit
        )
    if path == "/health":
        return 200, {
            "service": "agentic-trader-observer-api",
            "ok": True,
            "runtime": deps.build_runtime_status_view(
                deps.read_service_state(settings)
            ).runtime_state,
        }
    if path == "/status":
        state = deps.read_service_state(settings)
        view = deps.build_runtime_status_view(state)
        return 200, deps.runtime_status_payload(view, settings)
    if path == "/logs":
        return 200, {
            "logs": [
                event.model_dump(mode="json")
                for event in deps.read_service_events(settings, limit=log_limit)
            ]
        }
    if path == "/supervisor":
        return 200, deps.service_supervisor_payload(settings)
    if path == "/broker":
        return 200, deps.broker_payload(settings)
    if path == "/finance-ops":
        return 200, deps.finance_ops_payload(settings)
    if path == "/provider-diagnostics":
        return 200, deps.provider_diagnostics_payload(settings)
    if path == "/v1-readiness":
        return 200, deps.v1_readiness_payload(settings, False)
    if path == "/research":
        return 200, deps.research_sidecar_payload(settings)
    if path == "/proposal-candidates":
        return 200, deps.proposal_candidates_payload(settings, 50)
    if path == "/trade-proposals":
        return 200, deps.trade_proposals_payload(settings, 50)
    return 404, {"error": "not_found", "path": path}


def _register_logs_command(app: typer.Typer, deps: DashboardCommandDeps) -> None:
    @app.command()
    def logs(
        limit: int = typer.Option(
            20, min=1, max=200, help=HELP_RUNTIME_EVENT_LIMIT
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        events = deps.read_service_events(settings, limit=limit)
        if json_output:
            deps.emit_json([event.model_dump(mode="json") for event in events])
            return
        _render_service_events(events)


def _register_dashboard_snapshot_command(
    app: typer.Typer, deps: DashboardCommandDeps
) -> None:
    @app.command("dashboard-snapshot")
    def dashboard_snapshot(
        log_limit: int = typer.Option(
            14, min=1, max=100, help=HELP_RUNTIME_EVENT_LIMIT
        ),
        provider_check: bool = typer.Option(
            False,
            "--provider-check/--no-provider-check",
            help=HELP_PROVIDER_CHECK,
        ),
    ) -> None:
        settings = deps.get_settings()
        deps.emit_json(
            build_dashboard_snapshot_payload(
                settings,
                deps=deps,
                log_limit=log_limit,
                check_provider=provider_check,
            )
        )


def _register_evidence_bundle_command(
    app: typer.Typer, deps: DashboardCommandDeps
) -> None:
    @app.command("evidence-bundle")
    def evidence_bundle_command(
        output_dir: Path | None = typer.Option(
            None,
            "--output-dir",
            help=HELP_EVIDENCE_BUNDLE_OUTPUT_DIR,
        ),
        label: str | None = typer.Option(
            None,
            "--label",
            help=HELP_EVIDENCE_BUNDLE_LABEL,
        ),
        log_limit: int = typer.Option(
            20, min=1, max=200, help=HELP_RUNTIME_EVENT_LIMIT
        ),
        include_latest_smoke: bool = typer.Option(
            True,
            "--include-latest-smoke/--no-latest-smoke",
            help=HELP_EVIDENCE_BUNDLE_INCLUDE_LATEST_SMOKE,
        ),
        provider_check: bool = typer.Option(
            False,
            "--provider-check/--no-provider-check",
            help=HELP_PROVIDER_CHECK,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        manifest = build_evidence_bundle(
            settings,
            deps=deps,
            output_dir=output_dir,
            label=label,
            log_limit=log_limit,
            include_latest_smoke=include_latest_smoke,
            check_provider=provider_check,
        )
        if json_output:
            deps.emit_json(manifest)
            return
        _render_evidence_bundle_manifest(manifest)


def _render_evidence_bundle_manifest(manifest: dict[str, object]) -> None:
    files = cast(dict[str, str], manifest["files"])
    table = Table(title=TITLE_QA_EVIDENCE_BUNDLE)
    table.add_column(LABEL_ARTIFACT, style="cyan")
    table.add_column(LABEL_PATH)
    for key, path in files.items():
        table.add_row(key, path)
    console.print(
        Panel(
            MESSAGE_EVIDENCE_BUNDLE_WRITTEN.format(
                bundle_dir=manifest["bundle_dir"]
            ),
            title=TITLE_EVIDENCE_BUNDLE,
            border_style="green",
        )
    )
    console.print(table)


OBSERVER_API_ENDPOINTS: tuple[str, ...] = (
    "/health",
    "/dashboard",
    "/status",
    "/logs",
    "/broker",
    "/finance-ops",
    "/provider-diagnostics",
    "/v1-readiness",
    "/research",
    "/proposal-candidates",
    "/trade-proposals",
)


def _register_observer_api_command(
    app: typer.Typer, deps: DashboardCommandDeps
) -> None:
    @app.command("observer-api")
    def observer_api_command(
        host: str = typer.Option("127.0.0.1", help=HELP_OBSERVER_API_HOST),
        port: int = typer.Option(
            8765, min=1, max=65535, help=HELP_OBSERVER_API_PORT
        ),
        log_limit: int = typer.Option(
            14, min=1, max=100, help=HELP_RUNTIME_EVENT_LIMIT
        ),
        allow_nonlocal: bool = typer.Option(
            False,
            "--allow-nonlocal",
            help=HELP_OBSERVER_API_ALLOW_NONLOCAL,
        ),
    ) -> None:
        settings = deps.get_settings()
        nonlocal_bind = not is_loopback_host(host)
        if nonlocal_bind and (not allow_nonlocal or not settings.observer_api_token):
            console.print(
                Panel(
                    MESSAGE_OBSERVER_API_NONLOCAL_BLOCKED,
                    title=TITLE_OBSERVER_API_BLOCKED,
                    border_style="red",
                )
            )
            raise typer.Exit(code=2)
        _render_observer_api_listening(host=host, port=port)
        try:
            serve_observer_api(
                host=host,
                port=port,
                resolver=lambda path: build_observer_api_payload(
                    settings, deps=deps, path=path, log_limit=log_limit
                ),
                allow_nonlocal=allow_nonlocal,
                token=settings.observer_api_token,
            )
        except ValueError as exc:
            console.print(
                Panel(
                    str(exc),
                    title=TITLE_OBSERVER_API_BLOCKED,
                    border_style="red",
                )
            )
            raise typer.Exit(code=2) from exc


def _render_observer_api_listening(*, host: str, port: int) -> None:
    endpoints = "\n".join(f"- {endpoint}" for endpoint in OBSERVER_API_ENDPOINTS)
    console.print(
        Panel(
            MESSAGE_OBSERVER_API_LISTENING.format(
                endpoints=endpoints,
                host=host,
                port=port,
            ),
            title=TITLE_OBSERVER_API,
            border_style="cyan",
        )
    )


def _render_service_events(events: list[object]) -> None:
    table = Table(title=TITLE_RUNTIME_EVENTS)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_LEVEL)
    table.add_column(LABEL_TYPE)
    table.add_column(LABEL_CYCLE)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_MESSAGE)
    for event in events:
        table.add_row(
            str(getattr(event, "created_at", "-")),
            str(getattr(event, "level", "-")),
            str(getattr(event, "event_type", "-")),
            str(getattr(event, "cycle_count", "-") or "-"),
            str(getattr(event, "symbol", "-") or "-"),
            str(getattr(event, "message", "-")),
        )
    console.print(table)
