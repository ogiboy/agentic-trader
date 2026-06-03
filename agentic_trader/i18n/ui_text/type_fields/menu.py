"""Menu UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuTextFields:
    """Typed menu copy fields for UITextCatalog."""

    menu_action_back: str
    menu_action_broker_status: str
    menu_action_configure_investment_preferences: str
    menu_action_doctor_system_checks: str
    menu_action_exit: str
    menu_action_inspect_latest_run_review: str
    menu_action_inspect_latest_run_trace: str
    menu_action_open_live_monitor: str
    menu_action_open_memory_explorer: str
    menu_action_open_operator_chat: str
    menu_action_operator_desk: str
    menu_action_parse_operator_instruction: str
    menu_action_portfolio_and_risk: str
    menu_action_provider_diagnostics: str
    menu_action_request_orchestrator_stop: str
    menu_action_research_and_memory: str
    menu_action_review_and_trace: str
    menu_action_runtime_control: str
    menu_action_show_daily_risk_report: str
    menu_action_show_paper_portfolio: str
    menu_action_show_recent_runs_and_events: str
    menu_action_show_trade_journal: str
    menu_action_start_one_strict_agent_cycle: str
    menu_action_start_orchestrator_service: str
    menu_action_v1_readiness_gates: str


__all__ = ("MenuTextFields",)
