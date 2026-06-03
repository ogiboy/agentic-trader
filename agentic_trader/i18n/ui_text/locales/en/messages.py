"""EN terminal UI messages copy."""

from __future__ import annotations

EN_MESSAGES_COPY: dict[str, str] = {
    "db_locked_msg": "The runtime writer currently owns the database.",
    "message_action_cancelled_returning": "Action cancelled. Returning to the control room.",
    "message_all_agent_stages_llm_path": "All agent stages completed through the LLM path.",
    "message_background_service_not_active": "No managed service is currently active.",
    "message_background_service_restarted": "Background orchestrator restarted with PID {pid}.",
    "message_control_room_closed": "Control room closed cleanly.",
    "message_fallback_used_in": "Fallback was used in",
    "message_evidence_bundle_written": "Bundle written to {bundle_dir}",
    "message_no_elevated_portfolio_risk_warnings": "No elevated portfolio risk warnings for this report.",
    "message_no_runtime_state": "No runtime state recorded yet.",
    "message_no_runtime_events": "No runtime events recorded yet.",
    "message_no_runs_recorded": "No runs recorded yet.",
    "message_no_stderr_log_lines": "No stderr log lines yet.",
    "message_no_stdout_log_lines": "No stdout log lines yet.",
    "message_no_trade_journal_entries": "No trade journal entries recorded yet.",
    "message_no_historical_memories": "No historical memories are available yet.",
    "message_no_orders_recorded": "No orders recorded yet.",
    "message_no_agent_activity_recorded": "No agent activity recorded yet.",
    "message_no_live_agent_stage_events": "No live agent stage events yet.",
    "message_memory_explorer_temporarily_unavailable": "Memory explorer is temporarily unavailable.\n\n{error}",
    "message_no_action_selected": "No action selected.",
    "message_no_retrieval_inspection_context": "No agent trace contexts are available for retrieval inspection yet.",
    "message_no_retrieval_stage_context": "No retrieval or memory context was attached for this stage.",
    "message_trade_journal_temporarily_unavailable": "Trade journal is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_risk_report_temporarily_unavailable": "Risk report is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_run_review_temporarily_unavailable": "Run review is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_no_persisted_runs_review": "No persisted runs are available to review.",
    "message_run_trace_temporarily_unavailable": "Run trace is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_no_persisted_runs_trace": "No persisted runs are available to trace.",
    "message_trade_context_temporarily_unavailable": "Trade context is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_no_trade_context": "No persisted trade context is available yet.",
    "message_run_replay_temporarily_unavailable": "Run replay is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_no_persisted_runs_replay": "No persisted runs are available to replay.",
    "message_no_persisted_runs_export": "No persisted runs are available to export.",
    "message_chat_exit_hint": "Type /exit to leave chat.",
    "message_final_stage_update": "Final stage update: {latest_message}\n\n{artifacts_json}",
    "message_preferences_saved": "Preferences saved.",
    "message_preparing_symbol": "Preparing {symbol}.",
    "message_run_report_written": "Run report written to {output}.",
    "message_retrieval_inspection_temporarily_unavailable": "Retrieval inspection is temporarily unavailable.\n\n{error}",
    "message_backtest_choose_one_comparison": "Choose either --compare-baseline or --compare-memory for a single run.",
    "message_backtest_comparison_written": "Backtest comparison written to {output}.",
    "message_backtest_memory_ablation_written": "Backtest memory ablation written to {output}.",
    "message_backtest_summary_written": "Backtest summary written to {output}.",
    "message_operator_workflow_guidance": "Read-only workflow guide. Review readiness and evidence before long paper operation.",
    "message_installing_tui_dependencies": "First launch detected. Installing Ink dependencies with {package_manager}.",
    "message_node_missing": "A Node package manager is required to run the Ink control room. "
    "Falling back to the Rich control room.",
    "message_calendar_status_unavailable": "Calendar status is temporarily unavailable.\n\n{error}",
    "message_cache_status": "{mode_label}: {mode}\n"
    "{cache_dir_label}: {cache_dir}\n"
    "{snapshot_count_label}: {snapshot_count}",
    "message_market_snapshot_cached": "Cached {bar_count} bars for {symbol} {interval} {lookback}.\n\n"
    "{cache_dir_label}: {cache_dir}\n{snapshot_count_label}: {snapshot_count}",
    "message_no_tool_news_headlines": "No tool-driven news headlines are available for this symbol.",
    "message_no_open_positions": "No open positions.",
    "message_no_proposal_candidates": "No proposal candidates recorded yet.",
    "message_no_trade_proposals": "No trade proposals recorded yet.",
    "message_finance_operations_unavailable": "Finance operations status unavailable.",
    "message_gross_exposure_above_equity": "Gross exposure is above {limit} of equity.",
    "message_idea_presets_execution_policy": "scanner ideas must become proposals and require manual approval",
    "message_idea_score_execution_policy": "score output is research only; use proposal-create for manual review",
    "message_idea_score_unavailable": "No score could be produced for {symbol!r} with preset {preset!r}.",
    "message_largest_position_above_equity": "Largest position is above {limit} of equity.",
    "message_background_requires_continuous": "Background mode requires --continuous.",
    "message_launch_plan": "Symbols: {symbols}\nInterval: {interval}\nLookback: {lookback}\n"
    "Continuous: {continuous}\nPoll Seconds: {poll_seconds}\nBackground: {background}",
    "message_launch_symbol_required": "At least one symbol is required.",
    "message_mark_time_unavailable": "mark time unavailable",
    "message_monitor_return_shortcut": "Ctrl+C to return",
    "message_open_position_count_elevated": "Open position count is elevated.",
    "message_portfolio_concentration_hhi": "Portfolio concentration HHI is elevated at {score:.3f}.",
    "message_position_plan_repair_unavailable": "Position plan repair status unavailable.",
    "message_position_plan_repair_temporarily_unavailable": "Position plan repair is temporarily unavailable while the runtime writer "
    "owns the database.\n\n{error}",
    "message_proposal_candidates_temporarily_unavailable": "Proposal candidates are temporarily unavailable while the runtime writer "
    "owns the database.\n\n{error}",
    "message_proposal_candidate_created": "{candidate_id} recorded for review.\n\n"
    "{symbol} {signal} score={score:.2f}",
    "message_proposal_candidate_promoted": "{candidate_id} -> {proposal_id}\n"
    "Queued as pending proposal. No broker submission was attempted.",
    "message_research_cycle_choose_one_action": "Choose only one of --pause, --resume, or --trigger-now.",
    "message_research_cycle_control_status": "{label}: {status}\n{trigger_label}: {trigger_now}",
    "message_research_cycle_reason_requires_action": "--reason requires --pause, --resume, or --trigger-now.",
    "message_research_cycle_run_summary": "Executed {executed_cycles} evidence-only research cycle(s).\n"
    "Broker access, proposal approval, and raw web prompt injection stayed disabled.",
    "message_research_snapshot_recorded": "Snapshot {snapshot_id} recorded in the research feed.",
    "message_observer_api_listening": "Observer API listening on http://{host}:{port}\n\n"
    "Available endpoints:\n{endpoints}",
    "message_observer_api_nonlocal_blocked": "Observer API is local-only by default. Use a loopback host or set "
    "AGENTIC_TRADER_OBSERVER_API_TOKEN and pass --allow-nonlocal for an "
    "intentional nonlocal read-only bind.",
    "message_observer_mode_temporarily_unavailable": "{feature} is temporarily unavailable while the runtime writer owns "
    "the database.",
    "message_runtime_gate_open": "Ollama reachable at {base_url} and model {model_name} is available.",
    "message_runtime_mode_configured_backend": "Configured backend: {backend}",
    "message_runtime_mode_configured_model": "Configured model: {model_name}",
    "message_runtime_mode_kill_switch_clear_required": "Execution kill switch must be clear for production-like paper operation.",
    "message_runtime_mode_live_execution_disabled_required": "Live execution must remain disabled until a real adapter and approvals exist.",
    "message_runtime_mode_provider_check_skipped": "Provider check skipped; run doctor before Operation mode.",
    "message_runtime_mode_strict_llm_required": "Operation mode requires AGENTIC_TRADER_STRICT_LLM=true.",
    "message_runtime_mode_training_diagnostic_scope": "Training mode is limited to replay, walk-forward, ablation, and diagnostic evaluation flows.",
    "message_runtime_mode_training_no_hidden_trades": "`run`, `launch`, and service orchestration remain strict and do not silently trade with fallback outputs.",
    "message_runtime_mode_training_operator_confirmation_required": "Mode changes must be applied through explicit configuration, not chat side effects.",
    "message_portfolio_temporarily_unavailable": "Portfolio view is temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_preferences_temporarily_unavailable": "Preferences are temporarily unavailable while the runtime writer owns "
    "the database.\n\n{error}",
    "message_trade_proposals_temporarily_unavailable": "Trade proposals are temporarily unavailable while the runtime writer "
    "owns the database.\n\n{error}",
    "message_trade_proposal_approved": "{proposal_id} -> {status}\norder={order_id} status={outcome_status}",
    "message_trade_proposal_created": "{proposal_id} queued for manual review.\n\n"
    "{symbol} {side} @ {reference_price:.4f}",
    "message_trade_proposal_reconciled": "{proposal_id} -> {status}\n"
    "order={order_id} status={outcome_status}\n"
    "No broker resubmission was attempted.",
    "message_trade_proposal_refreshed": "{proposal_id} -> {status}\n"
    "order={order_id} status={outcome_status}\n"
    "No broker resubmission was attempted.",
    "message_trade_proposal_rejected": "{proposal_id} rejected.\n\nReason: {reason}",
    "message_runtime_mode_transition_allowed": "Runtime mode transition {current_mode} -> {target_mode} is allowed.",
    "message_runtime_mode_transition_blocked": "Runtime mode transition {current_mode} -> {target_mode} is blocked.",
    "message_setup_bootstrap_guidance": "Run `make bootstrap` for the interactive system-tool installer.",
    "message_service_stale_runtime_recovered": "Dead PID {pid} is no longer alive. Runtime state was marked stopped "
    "and the stale PID was cleared.",
    "message_service_stale_runtime_recovered_event": "Recovered stale runtime state from dead PID {pid}.",
    "message_service_stop_requested": "Service PID {pid} was asked to stop gracefully via the runtime control channel.",
    "message_service_spawned_background": "Service spawned in the background with PID {pid}.\n\n"
    "The control room stays responsive. Open the live monitor to watch progress "
    "or request a stop at any time.",
    "message_stage_update": "[{stage}] {message}",
    "message_stale_runtime_pid": "PID {pid} is no longer alive. The next start will recover the stale "
    "runtime state automatically.",
    "message_strategy_profile_execution_policy": "profile is read-only research metadata; it cannot execute trades",
    "message_trading_runtime_blocked": "Trading runtime should not start until Ollama and the configured model are available.",
    "message_trading_runtime_ready": "Trading runtime can start with full LLM access.",
    "message_training_diagnostic_fallback": "Training mode is continuing this evaluation with deterministic diagnostic "
    "fallbacks because the LLM gate failed:\n\n{error}",
    "message_tui_missing": "The Ink UI directory was not found. Falling back to the Rich control room.",
    "message_unique_artifact_dir_unavailable": "Unable to create a unique artifact directory for {label}",
    "message_waiting_for_last_outcome": "Waiting for a completed symbol, exit, or service result.",
    "message_v1_readiness_status_unavailable": "V1 readiness status unavailable.",
}
