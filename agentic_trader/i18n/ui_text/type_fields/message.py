"""Message UI catalog field declarations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MessageTextFields:
    """Typed message copy fields for UITextCatalog."""

    message_action_cancelled_returning: str
    message_all_agent_stages_llm_path: str
    message_background_service_not_active: str
    message_background_service_restarted: str
    message_control_room_closed: str
    message_fallback_used_in: str
    message_evidence_bundle_written: str
    message_no_elevated_portfolio_risk_warnings: str
    message_no_runtime_state: str
    message_no_runtime_events: str
    message_no_runs_recorded: str
    message_no_stderr_log_lines: str
    message_no_stdout_log_lines: str
    message_no_trade_journal_entries: str
    message_no_historical_memories: str
    message_no_orders_recorded: str
    message_no_agent_activity_recorded: str
    message_no_live_agent_stage_events: str
    message_memory_explorer_temporarily_unavailable: str
    message_no_action_selected: str
    message_no_retrieval_inspection_context: str
    message_no_retrieval_stage_context: str
    message_trade_journal_temporarily_unavailable: str
    message_risk_report_temporarily_unavailable: str
    message_run_review_temporarily_unavailable: str
    message_no_persisted_runs_review: str
    message_run_trace_temporarily_unavailable: str
    message_no_persisted_runs_trace: str
    message_trade_context_temporarily_unavailable: str
    message_no_trade_context: str
    message_run_replay_temporarily_unavailable: str
    message_no_persisted_runs_replay: str
    message_no_persisted_runs_export: str
    message_chat_exit_hint: str
    message_final_stage_update: str
    message_preferences_saved: str
    message_preparing_symbol: str
    message_run_report_written: str
    message_retrieval_inspection_temporarily_unavailable: str
    message_backtest_choose_one_comparison: str
    message_backtest_comparison_written: str
    message_backtest_memory_ablation_written: str
    message_backtest_summary_written: str
    message_operator_workflow_guidance: str
    message_installing_tui_dependencies: str
    message_node_missing: str
    message_calendar_status_unavailable: str
    message_cache_status: str
    message_market_snapshot_cached: str
    message_no_tool_news_headlines: str
    message_no_open_positions: str
    message_no_proposal_candidates: str
    message_no_trade_proposals: str
    message_finance_operations_unavailable: str
    message_gross_exposure_above_equity: str
    message_idea_presets_execution_policy: str
    message_idea_score_execution_policy: str
    message_idea_score_unavailable: str
    message_largest_position_above_equity: str
    message_background_requires_continuous: str
    message_launch_plan: str
    message_launch_symbol_required: str
    message_mark_time_unavailable: str
    message_monitor_return_shortcut: str
    message_open_position_count_elevated: str
    message_portfolio_concentration_hhi: str
    message_position_plan_repair_unavailable: str
    message_position_plan_repair_temporarily_unavailable: str
    message_proposal_candidates_temporarily_unavailable: str
    message_proposal_candidate_created: str
    message_proposal_candidate_promoted: str
    message_research_cycle_choose_one_action: str
    message_research_cycle_control_status: str
    message_research_cycle_reason_requires_action: str
    message_research_cycle_run_summary: str
    message_research_snapshot_recorded: str
    message_observer_api_listening: str
    message_observer_api_nonlocal_blocked: str
    message_observer_mode_temporarily_unavailable: str
    message_runtime_gate_open: str
    message_portfolio_temporarily_unavailable: str
    message_preferences_temporarily_unavailable: str
    message_trade_proposals_temporarily_unavailable: str
    message_trade_proposal_approved: str
    message_trade_proposal_created: str
    message_trade_proposal_reconciled: str
    message_trade_proposal_refreshed: str
    message_trade_proposal_rejected: str
    message_runtime_mode_transition_allowed: str
    message_runtime_mode_transition_blocked: str
    message_setup_bootstrap_guidance: str
    message_service_stale_runtime_recovered: str
    message_service_stale_runtime_recovered_event: str
    message_service_stop_requested: str
    message_service_spawned_background: str
    message_stage_update: str
    message_stale_runtime_pid: str
    message_strategy_profile_execution_policy: str
    message_trading_runtime_blocked: str
    message_trading_runtime_ready: str
    message_training_diagnostic_fallback: str
    message_tui_missing: str
    message_unique_artifact_dir_unavailable: str
    message_waiting_for_last_outcome: str
    message_v1_readiness_status_unavailable: str


__all__ = ("MessageTextFields",)
