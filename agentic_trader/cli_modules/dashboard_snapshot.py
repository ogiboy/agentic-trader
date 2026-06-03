from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.memory.policy import memory_write_policy_snapshot
from agentic_trader.runtime_feed import read_service_events, read_service_state
from agentic_trader.runtime_status import (
    AgentActivityView,
    AgentStageStatusView,
    RuntimeStatusView,
    build_agent_activity_view,
    build_runtime_status_view,
)
from agentic_trader.schema_models.preferences import LLMHealthStatus
from agentic_trader.storage.db import OrderRow, TradingDatabase
from agentic_trader.system.camofox_service import build_camofox_service_status
from agentic_trader.system.model_service import build_model_service_status
from agentic_trader.system.runtime_tools import apply_app_owned_service_settings
from agentic_trader.system.tool_ownership import (
    read_tool_ownership_payload,
)
from agentic_trader.system.webgui_service import build_webgui_service_status


@dataclass(frozen=True)
class DashboardSnapshotCollectors:
    ui_payload: Callable[[str], dict[str, object]]
    open_db: Callable[[Settings], TradingDatabase]
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


def build_dashboard_snapshot(
    settings: Settings,
    *,
    collectors: DashboardSnapshotCollectors,
    log_limit: int = 14,
    check_provider: bool = False,
) -> dict[str, object]:
    applied_tools = apply_app_owned_service_settings(settings, include_camofox=True)
    llm = LocalLLM(settings)
    health = llm.health_check()
    state = read_service_state(settings)
    view = build_runtime_status_view(state)

    latest = "unavailable"
    db_status = "ok"
    try:
        db = collectors.open_db(settings)
        try:
            latest = collectors.latest_order(db.latest_order())
        finally:
            db.close()
    except Exception as exc:
        db_status = f"Database unavailable: {exc}"

    events = read_service_events(settings, limit=log_limit)
    activity = build_agent_activity_view(view.state, events)

    return {
        "ui": collectors.ui_payload(settings.ui_locale),
        "doctor": _doctor_payload(settings, health, db_status, latest),
        "status": collectors.runtime_status_payload(view, settings),
        "supervisor": collectors.service_supervisor_payload(settings),
        "broker": collectors.broker_payload(settings),
        "modelService": (
            applied_tools.model_service or build_model_service_status(settings)
        ).model_dump(mode="json"),
        "camofoxService": (
            applied_tools.camofox_service or build_camofox_service_status(settings)
        ).model_dump(mode="json"),
        "webGui": build_webgui_service_status(settings).model_dump(mode="json"),
        "toolOwnership": read_tool_ownership_payload(settings).model_dump(mode="json"),
        "financeOps": collectors.finance_ops_payload(settings),
        "logs": [event.model_dump(mode="json") for event in events],
        "agentActivity": agent_activity_payload(activity),
        "portfolio": collectors.portfolio_payload(settings),
        "preferences": collectors.preferences_payload(settings),
        "recentRuns": collectors.recent_runs_payload(settings, 8),
        "proposalCandidates": collectors.proposal_candidates_payload(settings, 8),
        "tradeProposals": collectors.trade_proposals_payload(settings, 8),
        "journal": collectors.journal_payload(settings, 8),
        "riskReport": collectors.risk_report_payload(settings),
        "review": collectors.run_record_payload(settings),
        "trace": collectors.run_record_payload(settings),
        "tradeContext": collectors.trade_context_payload(settings),
        "marketContext": collectors.market_context_payload(settings),
        "canonicalAnalysis": collectors.canonical_analysis_payload(settings),
        "replay": collectors.run_replay_payload(settings),
        "memoryExplorer": collectors.memory_explorer_payload(settings, True, 5),
        "retrievalInspection": collectors.retrieval_inspection_payload(settings),
        "memoryPolicy": memory_write_policy_snapshot(),
        "chatHistory": collectors.chat_history_payload(settings),
        "calendar": collectors.calendar_payload(settings),
        "news": collectors.news_payload(settings),
        "marketCache": collectors.market_cache_payload(settings),
        "research": collectors.research_sidecar_payload(settings),
        "providerDiagnostics": collectors.provider_diagnostics_payload(settings),
        "v1Readiness": collectors.v1_readiness_payload(settings, check_provider),
    }


def _doctor_payload(
    settings: Settings,
    health: LLMHealthStatus,
    db_status: str,
    latest_order: str,
) -> dict[str, object]:
    return {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "runtime_mode": settings.runtime_mode,
        "base_url": settings.base_url,
        "runtime_dir": str(settings.runtime_dir),
        "database": str(settings.database_path),
        "db_status": db_status,
        "model_routing": settings.model_routing(),
        "llm_reachable": health.service_reachable,
        "ollama_reachable": health.service_reachable,
        "model_available": health.model_available,
        "llm_status": health.message,
        "latest_order": latest_order,
    }


def _stage_status_payload(stage: AgentStageStatusView) -> dict[str, object]:
    return {
        "stage": stage.stage,
        "status": stage.status,
        "message": stage.message,
        "created_at": stage.created_at,
        "cycle_count": stage.cycle_count,
        "symbol": stage.symbol,
    }


def agent_activity_payload(activity: AgentActivityView) -> dict[str, object]:
    return {
        "cycle_count": activity.cycle_count,
        "current_symbol": activity.current_symbol,
        "current_stage": activity.current_stage,
        "current_stage_status": activity.current_stage_status,
        "current_stage_message": activity.current_stage_message,
        "last_completed_stage": activity.last_completed_stage,
        "last_completed_message": activity.last_completed_message,
        "last_outcome_type": activity.last_outcome_type,
        "last_outcome_message": activity.last_outcome_message,
        "stage_statuses": [
            _stage_status_payload(stage) for stage in activity.stage_statuses
        ],
        "recent_stage_events": [
            _stage_status_payload(stage) for stage in activity.recent_stage_events
        ],
    }
