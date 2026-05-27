"""Shared operator-facing text catalog.

The module keeps the legacy constant exports used by CLI and TUI code while
adding a typed catalog boundary for future i18n. New UI surfaces should prefer
``get_ui_text(locale)`` over adding more top-level constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

UILocale = Literal["en", "tr"]
SUPPORTED_UI_LOCALES: tuple[UILocale, ...] = ("en", "tr")


@dataclass(frozen=True)
class UITextCatalog:
    """Operator-facing copy shared by terminal and Python UI surfaces."""

    cli_app_help: str
    db_locked_msg: str
    help_camofox_service_app: str
    help_idea_change_pct: str
    help_idea_ema_9: str
    help_idea_gap_pct: str
    help_idea_preset: str
    help_idea_price: str
    help_idea_range_pct: str
    help_idea_relative_volume: str
    help_idea_rsi: str
    help_idea_sma_20: str
    help_idea_sma_50: str
    help_idea_spread_pct: str
    help_idea_volume: str
    help_idea_vwap: str
    help_interval: str
    help_json: str
    help_locale_override: str
    help_locale_persist: str
    help_launch_background: str
    help_launch_continuous: str
    help_launch_max_cycles: str
    help_launch_poll_seconds: str
    help_launch_symbols: str
    help_lookback: str
    help_candidate_freshness: str
    help_candidate_liquidity: str
    help_candidate_materiality: str
    help_candidate_risk_notes: str
    help_candidate_source: str
    help_enrich_provider_context: str
    help_fetch_provider_news: str
    help_model_name_to_pull: str
    help_model_service_app: str
    help_model_service_host: str
    help_model_service_port: str
    help_ollama_owner: str
    help_position_plan_repair_apply: str
    help_position_plan_repair_max_holding_bars: str
    help_proposal_candidate_id: str
    help_proposal_candidates_limit: str
    help_proposal_candidates_status_filter: str
    help_promotion_notes: str
    help_research_cycle_pause: str
    help_research_cycle_reason: str
    help_research_cycle_resume: str
    help_research_cycle_trigger_now: str
    help_research_probe: str
    help_research_refresh_persist: str
    help_firecrawl_owner: str
    help_camofox_owner: str
    help_camofox_service_host: str
    help_camofox_service_port: str
    help_run_id: str
    help_runtime_mode_provider_check: str
    help_runtime_mode_target: str
    help_setup_dry_run: str
    help_symbol: str
    help_tool_ownership_app: str
    help_trade_confidence: str
    help_trade_invalidation: str
    help_trade_limit_price: str
    help_trade_notional: str
    help_trade_order_type: str
    help_trade_quantity: str
    help_trade_reference_price: str
    help_trade_review_notes: str
    help_trade_source: str
    help_trade_stop_loss: str
    help_trade_take_profit: str
    help_trade_thesis: str
    help_trade_side: str
    help_trade_proposals_limit: str
    help_trade_proposals_status_filter: str
    help_trade_proposal_approval_notes: str
    help_trade_proposal_id_approve: str
    help_trade_proposal_id_reject: str
    help_trade_proposal_reconcile_id: str
    help_trade_proposal_reconciliation_notes: str
    help_trade_proposal_refresh_id: str
    help_trade_proposal_refresh_notes: str
    help_trade_proposal_rejection_reason: str
    help_v1_provider_check: str
    help_webgui_open_browser: str
    help_webgui_service_app: str
    label_agent: str
    label_allowed: str
    label_adapter: str
    label_alpaca_credentials_configured: str
    label_alpaca_feed: str
    label_alpaca_paper_endpoint: str
    label_approved: str
    label_api_key: str
    label_average_price: str
    label_baseline: str
    label_base_url: str
    label_backend: str
    label_background_mode: str
    label_bias: str
    label_blocking: str
    label_camofox: str
    label_category: str
    label_cash: str
    label_check: str
    label_closed_trades: str
    label_continuous: str
    label_confidence: str
    label_context: str
    label_core_dependency: str
    label_core_ready: str
    label_created: str
    label_currency: str
    label_current: str
    label_current_symbol: str
    label_cycle: str
    label_cycle_control: str
    label_cycle_count: str
    label_cycles: str
    label_database: str
    label_db_status: str
    label_daily_realized_pnl: str
    label_decision: str
    label_decision_path: str
    label_default_model: str
    label_details: str
    label_delta: str
    label_digest_replay: str
    label_drawdown_from_peak: str
    label_ending_equity: str
    label_entry: str
    label_entry_px: str
    label_equity: str
    label_enabled: str
    label_environment_exists: str
    label_exposure: str
    label_exit: str
    label_exit_code: str
    label_exit_px: str
    label_expectancy: str
    label_fallback: str
    label_fallback_cycles: str
    label_fees: str
    label_field: str
    label_fills_today: str
    label_final_rationale: str
    label_final_side: str
    label_freshness: str
    label_flow_dir: str
    label_generated: str
    label_gross_exposure: str
    label_heartbeat: str
    label_heartbeat_age: str
    label_healthcheck: str
    label_id: str
    label_interval: str
    label_environment: str
    label_key: str
    label_last_recorded_error: str
    label_last_recorded_message: str
    label_last_recorded_state: str
    label_largest_position: str
    label_level: str
    label_kill_switch_active: str
    label_lockfile_exists: str
    label_launch_count: str
    label_latest_order: str
    label_last_error: str
    label_last_successful_update: str
    label_last_terminal_at: str
    label_last_terminal_state: str
    label_llm_provider: str
    label_live_execution_enabled: str
    label_live_process: str
    label_live_ready: str
    label_live_requested: str
    label_llm: str
    label_locale: str
    label_lookback: str
    label_market_value: str
    label_market_price: str
    label_market_provider: str
    label_market_role: str
    label_mark_source: str
    label_mark_status: str
    label_marked_at: str
    label_marks_recorded: str
    label_max_drawdown: str
    label_max_cycles: str
    label_memories: str
    label_meaning: str
    label_message: str
    label_metric: str
    label_mode: str
    label_model: str
    label_model_available: str
    label_model_routing: str
    label_multi_timeframe: str
    label_no: str
    label_notes: str
    label_next: str
    label_news_mode: str
    label_observer_mode: str
    label_open_positions: str
    label_opened: str
    label_order_id: str
    label_ownership: str
    label_ollama_reachable: str
    label_output: str
    label_output_preview: str
    label_optional_runtime_ready: str
    label_pid: str
    label_passed: str
    label_persisted: str
    label_platform: str
    label_pnl: str
    label_path: str
    label_poll_seconds: str
    label_preset: str
    label_preference_update: str
    label_provider: str
    label_python_version: str
    label_quantity: str
    label_proposal: str
    label_rationale: str
    label_realized_pnl: str
    label_ref: str
    label_rejection_evidence: str
    label_reason: str
    label_resolution_notes: str
    label_requires_confirmation: str
    label_research_cycle_control: str
    label_restart_count: str
    label_return: str
    label_runtime: str
    label_runtime_daemon: str
    label_runtime_dir: str
    label_role: str
    label_service: str
    label_side: str
    label_source: str
    label_specialist: str
    label_setup: str
    label_scaffold_exists: str
    label_signal: str
    label_simulated: str
    label_sidecar_available: str
    label_size: str
    label_score: str
    label_slippage: str
    label_stage: str
    label_started: str
    label_state: str
    label_status: str
    label_status_note: str
    label_stderr: str
    label_stderr_log: str
    label_stdout: str
    label_stdout_log: str
    label_strategy: str
    label_surface: str
    label_stop_requested: str
    label_stop: str
    label_structured_llm: str
    label_summary: str
    label_symbol: str
    label_symbols: str
    label_supported: str
    label_target: str
    label_take: str
    label_take_profit: str
    label_tool: str
    label_tools: str
    label_total_return: str
    label_trades: str
    label_trigger_now: str
    label_trigger_now_requested: str
    label_type: str
    label_purpose: str
    label_update_preferences: str
    label_updated: str
    label_updated_at: str
    label_unrealized_pnl: str
    label_uv_available: str
    label_value: str
    label_version: str
    label_version_source: str
    label_warmup_bars: str
    label_with_memory: str
    label_warnings: str
    label_win_rate: str
    label_without_memory: str
    label_v1_source: str
    label_web_gui: str
    label_watched_symbols: str
    label_workspace: str
    label_yes: str
    list_separator: str
    message_all_agent_stages_llm_path: str
    message_fallback_used_in: str
    message_no_elevated_portfolio_risk_warnings: str
    message_no_runtime_state: str
    message_no_runtime_events: str
    message_no_stderr_log_lines: str
    message_no_stdout_log_lines: str
    message_no_trade_journal_entries: str
    message_no_historical_memories: str
    message_no_action_selected: str
    message_no_open_positions: str
    message_no_proposal_candidates: str
    message_no_trade_proposals: str
    message_finance_operations_unavailable: str
    message_gross_exposure_above_equity: str
    message_largest_position_above_equity: str
    message_background_requires_continuous: str
    message_launch_plan: str
    message_launch_symbol_required: str
    message_mark_time_unavailable: str
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
    message_research_snapshot_recorded: str
    message_runtime_gate_open: str
    message_portfolio_temporarily_unavailable: str
    message_trade_proposals_temporarily_unavailable: str
    message_trade_proposal_approved: str
    message_trade_proposal_created: str
    message_trade_proposal_reconciled: str
    message_trade_proposal_refreshed: str
    message_trade_proposal_rejected: str
    message_runtime_mode_transition_allowed: str
    message_runtime_mode_transition_blocked: str
    message_setup_bootstrap_guidance: str
    message_trading_runtime_blocked: str
    message_trading_runtime_ready: str
    message_training_diagnostic_fallback: str
    message_v1_readiness_status_unavailable: str
    prompt_continue: str
    prompt_select_action: str
    launcher_option_open_web_gui: str
    launcher_option_continue_tui: str
    launcher_option_refresh: str
    launcher_option_exit: str
    stage_coordinator: str
    stage_consensus: str
    stage_execution: str
    stage_fundamental: str
    stage_manager: str
    stage_regime: str
    stage_risk: str
    stage_strategy: str
    style_key_column: str
    status_active: str
    status_app_owned: str
    status_available: str
    status_external: str
    status_fail: str
    status_needs_attention: str
    status_pass: str
    status_ready: str
    title_execution_summary: str
    title_agent_decisions: str
    title_agent_trace: str
    title_approval_blocked: str
    title_available_models: str
    title_backtest_comparison: str
    title_backtest_memory_ablation: str
    title_backtest_trades: str
    title_broker_status: str
    title_alpaca_paper_checks: str
    title_candidate_rejected: str
    title_camofox_browser_helper: str
    title_camofox_stderr_tail: str
    title_camofox_start_failed: str
    title_choose_surface: str
    title_llm_status: str
    title_operator_instruction: str
    title_operator_launcher: str
    title_pipeline: str
    title_paper_operation_checks: str
    title_provider_diagnostics: str
    title_provider_source_ladder: str
    title_daily_risk_report: str
    title_desk_accounting_context: str
    title_environment_check: str
    title_exit: str
    title_finance_ledger_categories: str
    title_finance_operations: str
    title_finance_operations_checks: str
    title_manager_conflicts: str
    title_manager_conflict_replay: str
    title_manager_override_notes: str
    title_memory_aware_replay: str
    title_memory_explorer: str
    title_model_pull: str
    title_model_service_stderr_tail: str
    title_model_service_start_failed: str
    title_recent_runs: str
    title_risk_warnings: str
    title_review_note: str
    title_replay_stages: str
    title_run_artifacts: str
    title_run_review: str
    title_run_blocked: str
    title_reconciliation_blocked: str
    title_refresh_blocked: str
    title_rejection_blocked: str
    title_runtime_events: str
    title_runtime_gate_open: str
    title_launch_plan: str
    title_runtime_mode: str
    title_runtime_mode_transition_checklist: str
    title_runtime_status: str
    title_service_status: str
    title_service_stderr_tail: str
    title_service_stdout_tail: str
    title_service_supervisor: str
    title_trade_journal: str
    title_trade_proposals: str
    title_proposal_candidates: str
    title_position_plan_repair: str
    title_portfolio: str
    title_positions: str
    title_proposal_rejected: str
    title_promotion_blocked: str
    title_proposal_candidate_created: str
    title_proposal_candidate_promoted: str
    title_recommended_next_commands: str
    title_recommended_commands: str
    title_research_crewai_flow_setup: str
    title_research_cycle_control: str
    title_research_sidecar_status: str
    title_research_source_health: str
    title_research_snapshot_persisted: str
    title_setup_status: str
    title_setup_guidance: str
    title_trace: str
    title_trade_proposal_approved: str
    title_trade_proposal_created: str
    title_trade_proposal_reconciled: str
    title_trade_proposal_refreshed: str
    title_trade_proposal_rejected: str
    title_tool_ownership: str
    title_tool_readiness: str
    title_training_diagnostic_mode: str
    title_ui_locale: str
    title_v1_readiness: str
    title_warning: str
    title_walk_forward_backtest: str
    title_web_gui_service: str
    title_web_gui_start_failed: str
    title_web_gui_stderr_tail: str


EN_TEXT = UITextCatalog(
    cli_app_help="Agentic Trader CLI",
    db_locked_msg="The runtime writer currently owns the database.",
    help_camofox_service_app="Manage the optional app-owned local Camofox browser helper.",
    help_idea_change_pct="Percent change over the scan window.",
    help_idea_ema_9="9 EMA value.",
    help_idea_gap_pct="Opening gap percent.",
    help_idea_preset="Idea preset to apply.",
    help_idea_price="Last or reference price.",
    help_idea_range_pct="Intraday range percent.",
    help_idea_relative_volume="Relative volume.",
    help_idea_rsi="RSI value.",
    help_idea_sma_20="20 SMA value.",
    help_idea_sma_50="50 SMA value.",
    help_idea_spread_pct="Bid/ask spread percent.",
    help_idea_volume="Latest volume.",
    help_idea_vwap="VWAP value.",
    help_interval="yfinance interval, for example 1d or 1h",
    help_json="Emit machine-readable JSON.",
    help_locale_override="Override terminal UI locale for this command: en or tr.",
    help_locale_persist="Persist terminal UI locale to .env.local: en or tr.",
    help_launch_background="Spawn the orchestrator as a background service.",
    help_launch_continuous="Keep the orchestrator running.",
    help_launch_max_cycles="Optional cap for continuous mode.",
    help_launch_poll_seconds="Sleep between cycles in continuous mode.",
    help_launch_symbols="Comma-separated symbols, for example AAPL,MSFT,BTC-USD",
    help_lookback="Lookback window accepted by yfinance",
    help_candidate_freshness="Freshness note for the scanner inputs.",
    help_candidate_liquidity="Liquidity note.",
    help_candidate_materiality="Materiality note.",
    help_candidate_risk_notes="Risk note.",
    help_candidate_source="Candidate source.",
    help_enrich_provider_context=(
        "Attach a compact, broker-free canonical provider context. Defaults to "
        "network-light evidence."
    ),
    help_fetch_provider_news=(
        "Allow configured news providers to refresh headlines for this candidate."
    ),
    help_model_name_to_pull="Ollama model name to pull.",
    help_model_service_app="Manage the optional app-owned local model service.",
    help_model_service_host="Loopback bind host for app-managed Ollama.",
    help_model_service_port="Preferred app-managed Ollama port.",
    help_ollama_owner="Ownership mode for Ollama: host-owned, app-owned, api-key-only, or skipped.",
    help_position_plan_repair_apply="Write repairable missing position plans. Defaults to dry-run.",
    help_position_plan_repair_max_holding_bars="Maximum holding bars for repaired position plans.",
    help_proposal_candidate_id="Proposal candidate id to promote.",
    help_proposal_candidates_limit="Maximum number of proposal candidates to show.",
    help_proposal_candidates_status_filter="Filter by candidate state: candidate, promoted, rejected, expired.",
    help_promotion_notes="Optional promotion notes.",
    help_research_cycle_pause="Pause future automated research-cycle runs.",
    help_research_cycle_reason="Optional operator note persisted with the control state.",
    help_research_cycle_resume="Resume future automated research-cycle runs.",
    help_research_cycle_trigger_now="Request one immediate research-cycle run for the next runner.",
    help_research_probe="Run one isolated sidecar provider probe before reporting status.",
    help_research_refresh_persist="Persist the sidecar snapshot to the runtime research JSON feed.",
    help_firecrawl_owner="Ownership mode for Firecrawl: host-owned, app-owned, api-key-only, or skipped.",
    help_camofox_owner="Ownership mode for Camofox: host-owned, app-owned, api-key-only, or skipped.",
    help_camofox_service_host="Loopback bind host for app-managed Camofox.",
    help_camofox_service_port="Preferred app-managed Camofox port.",
    help_run_id="Run id to inspect. Defaults to the latest recorded run.",
    help_runtime_mode_provider_check="Check local provider/model readiness for Operation mode.",
    help_runtime_mode_target="Target runtime mode: training or operation.",
    help_setup_dry_run="Report setup status. Use make bootstrap for interactive installs.",
    help_symbol="Ticker symbol, for example AAPL or BTC-USD",
    help_tool_ownership_app="Inspect or record optional helper ownership decisions.",
    help_trade_confidence="Proposal confidence from 0.0 to 1.0.",
    help_trade_invalidation="Optional condition that invalidates the trade idea.",
    help_trade_limit_price="Limit price. Required with --order-type limit.",
    help_trade_notional="Dollar notional. Either quantity or notional is required.",
    help_trade_order_type="Proposal order type. V1 supports market or limit.",
    help_trade_quantity="Share quantity. Either quantity or notional is required.",
    help_trade_reference_price="Reference price used for the proposal.",
    help_trade_review_notes="Optional review notes.",
    help_trade_source="Source label such as manual, scanner, or research-sidecar.",
    help_trade_stop_loss="Optional stop loss.",
    help_trade_take_profit="Optional take profit.",
    help_trade_thesis="Short operator-readable proposal thesis.",
    help_trade_side="Trade side: buy or sell.",
    help_trade_proposals_limit="Maximum number of trade proposals to show.",
    help_trade_proposals_status_filter="Filter by proposal state: pending, approved, rejected, executed, failed, expired.",
    help_trade_proposal_approval_notes="Required approval audit notes.",
    help_trade_proposal_id_approve="Trade proposal id to approve.",
    help_trade_proposal_id_reject="Trade proposal id to reject.",
    help_trade_proposal_reconcile_id="In-flight approved proposal id to reconcile.",
    help_trade_proposal_reconciliation_notes="Required reconciliation audit notes.",
    help_trade_proposal_refresh_id="Executed proposal id with an accepted broker order to refresh.",
    help_trade_proposal_refresh_notes="Required refresh audit notes.",
    help_trade_proposal_rejection_reason="Human-readable rejection reason.",
    help_v1_provider_check="Check local model/provider readiness; may call the configured LLM service.",
    help_webgui_open_browser="Ask the OS to open the Web GUI URL after starting.",
    help_webgui_service_app="Manage the optional app-owned local Web GUI service.",
    label_agent="Agent",
    label_allowed="Allowed",
    label_adapter="Adapter",
    label_alpaca_credentials_configured="Alpaca Credentials Configured",
    label_alpaca_feed="Alpaca Feed",
    label_alpaca_paper_endpoint="Alpaca Paper Endpoint",
    label_approved="Approved",
    label_api_key="API Key",
    label_average_price="Average Price",
    label_baseline="Baseline",
    label_base_url="Base URL",
    label_backend="Backend",
    label_background_mode="Background Mode",
    label_bias="Bias",
    label_blocking="Blocking",
    label_camofox="Camofox",
    label_category="Category",
    label_cash="Cash",
    label_check="Check",
    label_closed_trades="Closed Trades",
    label_continuous="Continuous",
    label_confidence="Confidence",
    label_context="Context",
    label_core_dependency="Core Dependency",
    label_core_ready="Core Ready",
    label_created="Created",
    label_currency="Currency",
    label_current="Current",
    label_current_symbol="Current Symbol",
    label_cycle="Cycle",
    label_cycle_control="Cycle Control",
    label_cycle_count="Cycle Count",
    label_cycles="Cycles",
    label_database="Database",
    label_db_status="DB Status",
    label_daily_realized_pnl="Daily Realized PnL",
    label_decision="Decision",
    label_decision_path="Decision Path",
    label_default_model="Default Model",
    label_details="Details",
    label_delta="Delta",
    label_digest_replay="Digest Replay",
    label_drawdown_from_peak="Drawdown From Peak",
    label_ending_equity="Ending Equity",
    label_entry="Entry",
    label_entry_px="Entry Px",
    label_equity="Equity",
    label_enabled="Enabled",
    label_environment_exists="Environment Exists",
    label_exposure="Exposure",
    label_exit="Exit",
    label_exit_code="Exit Code",
    label_exit_px="Exit Px",
    label_expectancy="Expectancy",
    label_fallback="Fallback",
    label_fallback_cycles="Fallback Cycles",
    label_fees="Fees",
    label_field="Field",
    label_fills_today="Fills Today",
    label_final_rationale="Final Rationale",
    label_final_side="Final Side",
    label_freshness="Freshness",
    label_flow_dir="Flow Dir",
    label_generated="Generated",
    label_gross_exposure="Gross Exposure",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Age",
    label_healthcheck="Healthcheck",
    label_id="ID",
    label_interval="Interval",
    label_environment="Environment",
    label_key="Key",
    label_last_recorded_error="Last Recorded Error",
    label_last_recorded_message="Last Recorded Message",
    label_last_recorded_state="Last Recorded State",
    label_largest_position="Largest Position",
    label_kill_switch_active="Kill Switch Active",
    label_last_error="Last Error",
    label_last_successful_update="Last Successful Update",
    label_last_terminal_at="Last Terminal At",
    label_last_terminal_state="Last Terminal State",
    label_level="Level",
    label_lockfile_exists="Lockfile Exists",
    label_launch_count="Launch Count",
    label_latest_order="Latest Order",
    label_llm_provider="LLM Provider",
    label_live_execution_enabled="Live Execution Enabled",
    label_live_process="Live Process",
    label_live_ready="Live Ready",
    label_live_requested="Live Requested",
    label_llm="LLM",
    label_locale="Locale",
    label_lookback="Lookback",
    label_market_value="Market Value",
    label_market_price="Market Price",
    label_market_provider="Market Provider",
    label_market_role="Market Role",
    label_mark_source="Mark Source",
    label_mark_status="Mark Status",
    label_marked_at="Marked At",
    label_marks_recorded="Marks Recorded",
    label_max_drawdown="Max Drawdown",
    label_max_cycles="Max Cycles",
    label_memories="Memories",
    label_meaning="Meaning",
    label_message="Message",
    label_metric="Metric",
    label_mode="Mode",
    label_model="Model",
    label_model_available="Model Available",
    label_model_routing="Model Routing",
    label_multi_timeframe="Multi-Timeframe",
    label_no="no",
    label_notes="Notes",
    label_next="Next",
    label_news_mode="News Mode",
    label_observer_mode="Observer Mode",
    label_open_positions="Open Positions",
    label_opened="Opened",
    label_order_id="Order ID",
    label_ownership="Ownership",
    label_ollama_reachable="Ollama Reachable",
    label_output="Output",
    label_output_preview="Output Preview",
    label_optional_runtime_ready="Optional Runtime Ready",
    label_pid="PID",
    label_passed="Passed",
    label_persisted="Persisted",
    label_platform="Platform",
    label_pnl="PnL",
    label_path="Path",
    label_poll_seconds="Poll Seconds",
    label_preset="Preset",
    label_preference_update="Preference Update",
    label_provider="Provider",
    label_python_version="Python Version",
    label_quantity="Quantity",
    label_proposal="Proposal",
    label_rationale="Rationale",
    label_realized_pnl="Realized PnL",
    label_ref="Ref",
    label_rejection_evidence="Rejection Evidence",
    label_reason="Reason",
    label_resolution_notes="Resolution Notes",
    label_requires_confirmation="Requires Confirmation",
    label_research_cycle_control="Research cycle control",
    label_restart_count="Restart Count",
    label_return="Return",
    label_runtime="Runtime",
    label_runtime_daemon="Runtime Daemon",
    label_runtime_dir="Runtime Dir",
    label_role="Role",
    label_service="Service",
    label_side="Side",
    label_source="Source",
    label_specialist="Specialist",
    label_setup="Setup",
    label_scaffold_exists="Scaffold Exists",
    label_signal="Signal",
    label_simulated="Simulated",
    label_sidecar_available="Sidecar Available",
    label_size="Size",
    label_score="Score",
    label_slippage="Slippage",
    label_stage="Stage",
    label_started="Started",
    label_state="State",
    label_status="Status",
    label_status_note="Status Note",
    label_stderr="Stderr",
    label_stderr_log="Stderr Log",
    label_stdout="Stdout",
    label_stdout_log="Stdout Log",
    label_strategy="Strategy",
    label_surface="Surface",
    label_stop_requested="Stop Requested",
    label_stop="Stop",
    label_structured_llm="Structured LLM response",
    label_summary="Summary",
    label_symbol="Symbol",
    label_symbols="Symbols",
    label_supported="Supported",
    label_target="Target",
    label_take="Take",
    label_take_profit="Take Profit",
    label_tool="Tool",
    label_tools="Tools",
    label_total_return="Total Return",
    label_trades="Trades",
    label_trigger_now="Trigger Now",
    label_trigger_now_requested="Trigger now requested",
    label_type="Type",
    label_purpose="Purpose",
    label_update_preferences="Update Preferences",
    label_updated="Updated",
    label_updated_at="Updated At",
    label_unrealized_pnl="Unrealized PnL",
    label_uv_available="uv Available",
    label_value="Value",
    label_version="Version",
    label_version_source="Version Source",
    label_warmup_bars="Warmup Bars",
    label_watched_symbols="Watched Symbols",
    label_with_memory="With Memory",
    label_warnings="Warnings",
    label_win_rate="Win Rate",
    label_without_memory="Without Memory",
    label_v1_source="V1 Source",
    label_web_gui="Web GUI",
    label_workspace="Workspace",
    label_yes="yes",
    list_separator=", ",
    message_all_agent_stages_llm_path="All agent stages completed through the LLM path.",
    message_fallback_used_in="Fallback was used in",
    message_no_elevated_portfolio_risk_warnings=(
        "No elevated portfolio risk warnings for this report."
    ),
    message_no_runtime_state="No runtime state recorded yet.",
    message_no_runtime_events="No runtime events recorded yet.",
    message_no_stderr_log_lines="No stderr log lines yet.",
    message_no_stdout_log_lines="No stdout log lines yet.",
    message_no_trade_journal_entries="No trade journal entries recorded yet.",
    message_no_historical_memories="No historical memories are available yet.",
    message_no_action_selected="No action selected.",
    message_no_open_positions="No open positions.",
    message_no_proposal_candidates="No proposal candidates recorded yet.",
    message_no_trade_proposals="No trade proposals recorded yet.",
    message_finance_operations_unavailable="Finance operations status unavailable.",
    message_gross_exposure_above_equity="Gross exposure is above {limit} of equity.",
    message_largest_position_above_equity="Largest position is above {limit} of equity.",
    message_background_requires_continuous="Background mode requires --continuous.",
    message_launch_plan=(
        "Symbols: {symbols}\nInterval: {interval}\nLookback: {lookback}\n"
        "Continuous: {continuous}\nPoll Seconds: {poll_seconds}\nBackground: {background}"
    ),
    message_launch_symbol_required="At least one symbol is required.",
    message_mark_time_unavailable="mark time unavailable",
    message_open_position_count_elevated="Open position count is elevated.",
    message_portfolio_concentration_hhi=(
        "Portfolio concentration HHI is elevated at {score:.3f}."
    ),
    message_position_plan_repair_unavailable="Position plan repair status unavailable.",
    message_position_plan_repair_temporarily_unavailable=(
        "Position plan repair is temporarily unavailable while the runtime writer "
        "owns the database.\n\n{error}"
    ),
    message_proposal_candidates_temporarily_unavailable=(
        "Proposal candidates are temporarily unavailable while the runtime writer "
        "owns the database.\n\n{error}"
    ),
    message_proposal_candidate_created=(
        "{candidate_id} recorded for review.\n\n"
        "{symbol} {signal} score={score:.2f}"
    ),
    message_proposal_candidate_promoted=(
        "{candidate_id} -> {proposal_id}\n"
        "Queued as pending proposal. No broker submission was attempted."
    ),
    message_research_cycle_choose_one_action="Choose only one of --pause, --resume, or --trigger-now.",
    message_research_cycle_control_status="{label}: {status}\n{trigger_label}: {trigger_now}",
    message_research_cycle_reason_requires_action="--reason requires --pause, --resume, or --trigger-now.",
    message_research_snapshot_recorded="Snapshot {snapshot_id} recorded in the research feed.",
    message_runtime_gate_open="Ollama reachable at {base_url} and model {model_name} is available.",
    message_portfolio_temporarily_unavailable=(
        "Portfolio view is temporarily unavailable while the runtime writer owns "
        "the database.\n\n{error}"
    ),
    message_trade_proposals_temporarily_unavailable=(
        "Trade proposals are temporarily unavailable while the runtime writer "
        "owns the database.\n\n{error}"
    ),
    message_trade_proposal_approved=(
        "{proposal_id} -> {status}\norder={order_id} status={outcome_status}"
    ),
    message_trade_proposal_created=(
        "{proposal_id} queued for manual review.\n\n"
        "{symbol} {side} @ {reference_price:.4f}"
    ),
    message_trade_proposal_reconciled=(
        "{proposal_id} -> {status}\n"
        "order={order_id} status={outcome_status}\n"
        "No broker resubmission was attempted."
    ),
    message_trade_proposal_refreshed=(
        "{proposal_id} -> {status}\n"
        "order={order_id} status={outcome_status}\n"
        "No broker resubmission was attempted."
    ),
    message_trade_proposal_rejected=(
        "{proposal_id} rejected.\n\nReason: {reason}"
    ),
    message_runtime_mode_transition_allowed=(
        "Runtime mode transition {current_mode} -> {target_mode} is allowed."
    ),
    message_runtime_mode_transition_blocked=(
        "Runtime mode transition {current_mode} -> {target_mode} is blocked."
    ),
    message_setup_bootstrap_guidance="Run `make bootstrap` for the interactive system-tool installer.",
    message_trading_runtime_blocked=(
        "Trading runtime should not start until Ollama and the configured model are available."
    ),
    message_trading_runtime_ready="Trading runtime can start with full LLM access.",
    message_training_diagnostic_fallback=(
        "Training mode is continuing this evaluation with deterministic diagnostic "
        "fallbacks because the LLM gate failed:\n\n{error}"
    ),
    message_v1_readiness_status_unavailable="V1 readiness status unavailable.",
    prompt_continue="Press Enter to continue",
    prompt_select_action="Select action",
    launcher_option_open_web_gui="1  Open/start the local Web GUI command center",
    launcher_option_continue_tui="2  Continue in the Rich terminal control room",
    launcher_option_refresh="3  Stay here and refresh this launcher",
    launcher_option_exit="4  Exit",
    stage_coordinator="Coordinator",
    stage_consensus="Consensus",
    stage_execution="Execution",
    stage_fundamental="Fundamental",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column="bold cyan",
    status_active="active",
    status_app_owned="app-owned",
    status_available="available",
    status_external="external",
    status_fail="fail",
    status_needs_attention="needs attention",
    status_pass="pass",
    status_ready="ready",
    title_agent_decisions="Agent Decisions",
    title_agent_trace="Agent Trace",
    title_approval_blocked="Approval Blocked",
    title_available_models="Available Models",
    title_backtest_comparison="Backtest Comparison",
    title_backtest_memory_ablation="Backtest Memory Ablation",
    title_backtest_trades="Backtest Trades",
    title_broker_status="Broker Status",
    title_alpaca_paper_checks="Alpaca Paper Checks",
    title_candidate_rejected="Candidate Rejected",
    title_camofox_browser_helper="Camofox Browser Helper",
    title_camofox_stderr_tail="Camofox Stderr Tail",
    title_camofox_start_failed="Camofox Start Failed",
    title_choose_surface="Choose A Surface",
    title_execution_summary="Execution Summary",
    title_llm_status="LLM Status",
    title_operator_instruction="Operator Instruction",
    title_operator_launcher="Agentic Trader Operator Launcher",
    title_pipeline="Pipeline",
    title_paper_operation_checks="Paper Operation Checks",
    title_provider_diagnostics="Provider Diagnostics",
    title_provider_source_ladder="Provider Source Ladder",
    title_daily_risk_report="Daily Risk Report",
    title_desk_accounting_context="Desk Accounting Context",
    title_environment_check="Environment Check",
    title_exit="Exit",
    title_finance_ledger_categories="Finance Ledger Categories",
    title_finance_operations="Finance Operations",
    title_finance_operations_checks="Finance Operations Checks",
    title_manager_conflicts="Manager Conflicts",
    title_manager_conflict_replay="Manager Conflict Replay",
    title_manager_override_notes="Manager Override Notes",
    title_memory_aware_replay="Memory-Aware Replay",
    title_memory_explorer="Memory Explorer",
    title_model_pull="Model Pull",
    title_model_service_stderr_tail="Model Service Stderr Tail",
    title_model_service_start_failed="Model Service Start Failed",
    title_recent_runs="Recent Runs",
    title_risk_warnings="Risk Warnings",
    title_review_note="Review Note",
    title_replay_stages="Replay Stages",
    title_run_artifacts="Run Artifacts",
    title_run_review="Run Review",
    title_run_blocked="Run Blocked",
    title_reconciliation_blocked="Reconciliation Blocked",
    title_refresh_blocked="Refresh Blocked",
    title_rejection_blocked="Rejection Blocked",
    title_runtime_events="Runtime Events",
    title_runtime_gate_open="Runtime Gate Open",
    title_launch_plan="Launch Plan",
    title_runtime_mode="Runtime Mode",
    title_runtime_mode_transition_checklist="Runtime Mode Transition Checklist",
    title_runtime_status="Runtime Status",
    title_service_status="Service Status",
    title_service_stderr_tail="Service Stderr Tail",
    title_service_stdout_tail="Service Stdout Tail",
    title_service_supervisor="Service Supervisor",
    title_trade_journal="Trade Journal",
    title_trade_proposals="Trade Proposals",
    title_proposal_candidates="Proposal Candidates",
    title_position_plan_repair="Position Plan Repair",
    title_portfolio="Portfolio",
    title_positions="Positions",
    title_proposal_rejected="Proposal Rejected",
    title_promotion_blocked="Promotion Blocked",
    title_proposal_candidate_created="Proposal Candidate Created",
    title_proposal_candidate_promoted="Proposal Candidate Promoted",
    title_recommended_next_commands="Recommended Next Commands",
    title_recommended_commands="Recommended Commands",
    title_research_crewai_flow_setup="Research CrewAI Flow Setup",
    title_research_cycle_control="Research Cycle Control",
    title_research_sidecar_status="Research Sidecar Status",
    title_research_source_health="Research Source Health",
    title_research_snapshot_persisted="Research Snapshot Persisted",
    title_setup_status="Setup Status",
    title_setup_guidance="Setup Guidance",
    title_trace="Trace",
    title_trade_proposal_approved="Trade Proposal Approved",
    title_trade_proposal_created="Trade Proposal Created",
    title_trade_proposal_reconciled="Trade Proposal Reconciled",
    title_trade_proposal_refreshed="Trade Proposal Refreshed",
    title_trade_proposal_rejected="Trade Proposal Rejected",
    title_tool_ownership="Tool Ownership",
    title_tool_readiness="Tool Readiness",
    title_training_diagnostic_mode="Training Diagnostic Mode",
    title_ui_locale="UI Locale",
    title_v1_readiness="V1 Readiness",
    title_warning="Warning",
    title_walk_forward_backtest="Walk-Forward Backtest",
    title_web_gui_service="Web GUI Service",
    title_web_gui_start_failed="Web GUI Start Failed",
    title_web_gui_stderr_tail="Web GUI Stderr Tail",
)

# Terminal-facing Turkish copy intentionally remains ASCII-safe until CLI/TUI
# locale rendering is audited across non-UTF-8 shells. Web surfaces keep full
# Turkish orthography in their own copy catalogs.
TR_TEXT = UITextCatalog(
    cli_app_help="Agentic Trader CLI",
    db_locked_msg="Runtime writer veritabaninin sahibi; biraz sonra tekrar deneyin.",
    help_camofox_service_app="Istege bagli app-owned yerel Camofox browser yardimcisini yonet.",
    help_idea_change_pct="Tarama penceresindeki yuzde degisim.",
    help_idea_ema_9="9 EMA degeri.",
    help_idea_gap_pct="Acilis gap yuzdesi.",
    help_idea_preset="Uygulanacak idea preset.",
    help_idea_price="Son veya referans fiyat.",
    help_idea_range_pct="Gun ici range yuzdesi.",
    help_idea_relative_volume="Relative volume.",
    help_idea_rsi="RSI degeri.",
    help_idea_sma_20="20 SMA degeri.",
    help_idea_sma_50="50 SMA degeri.",
    help_idea_spread_pct="Bid/ask spread yuzdesi.",
    help_idea_volume="Son volume.",
    help_idea_vwap="VWAP degeri.",
    help_interval="yfinance araligi, ornegin 1d veya 1h",
    help_json="Makine tarafindan okunabilir JSON uret.",
    help_locale_override="Bu komut icin terminal UI locale override et: en veya tr.",
    help_locale_persist="Terminal UI locale degerini .env.local icine yaz: en veya tr.",
    help_launch_background="Orchestrator'i background service olarak baslat.",
    help_launch_continuous="Orchestrator'i calisir durumda tut.",
    help_launch_max_cycles="Continuous mod icin istege bagli limit.",
    help_launch_poll_seconds="Continuous modda donguler arasi bekleme suresi.",
    help_launch_symbols="Virgulle ayrilmis semboller, ornegin AAPL,MSFT,BTC-USD",
    help_lookback="yfinance tarafindan kabul edilen geriye donuk pencere",
    help_candidate_freshness="Scanner input'lari icin freshness notu.",
    help_candidate_liquidity="Liquidity notu.",
    help_candidate_materiality="Materiality notu.",
    help_candidate_risk_notes="Risk notu.",
    help_candidate_source="Candidate kaynagi.",
    help_enrich_provider_context=(
        "Kompakt, broker-free canonical provider context ekle. Varsayilan "
        "network-light evidence."
    ),
    help_fetch_provider_news=(
        "Bu candidate icin configured news provider'larin headline yenilemesine izin ver."
    ),
    help_model_name_to_pull="Cekilecek Ollama model adi.",
    help_model_service_app="Istege bagli app-owned yerel model servisini yonet.",
    help_model_service_host="App-managed Ollama icin loopback bind host.",
    help_model_service_port="Tercih edilen app-managed Ollama portu.",
    help_ollama_owner="Ollama sahiplik modu: host-owned, app-owned, api-key-only veya skipped.",
    help_position_plan_repair_apply="Repair edilebilir eksik position plan'lari yaz. Varsayilan dry-run.",
    help_position_plan_repair_max_holding_bars="Repair edilen position plan'lari icin maksimum holding bar.",
    help_proposal_candidate_id="Promote edilecek proposal candidate id.",
    help_proposal_candidates_limit="Gosterilecek maksimum proposal candidate sayisi.",
    help_proposal_candidates_status_filter="Candidate state filtresi: candidate, promoted, rejected, expired.",
    help_promotion_notes="Istege bagli promotion notlari.",
    help_research_cycle_pause="Gelecekteki otomatik research-cycle run'larini duraklat.",
    help_research_cycle_reason="Control state ile kaydedilecek istege bagli operator notu.",
    help_research_cycle_resume="Gelecekteki otomatik research-cycle run'larini surdur.",
    help_research_cycle_trigger_now="Sonraki runner icin bir anlik research-cycle run iste.",
    help_research_probe="Durumu raporlamadan once izole bir sidecar provider probe calistir.",
    help_research_refresh_persist="Sidecar snapshot'i runtime research JSON feed icine kaydet.",
    help_firecrawl_owner="Firecrawl sahiplik modu: host-owned, app-owned, api-key-only veya skipped.",
    help_camofox_owner="Camofox sahiplik modu: host-owned, app-owned, api-key-only veya skipped.",
    help_camofox_service_host="App-managed Camofox icin loopback bind host.",
    help_camofox_service_port="Tercih edilen app-managed Camofox portu.",
    help_run_id="Incelenecek run id. Varsayilan son kayitli run.",
    help_runtime_mode_provider_check="Operation modu icin yerel provider/model hazirligini kontrol et.",
    help_runtime_mode_target="Hedef runtime modu: training veya operation.",
    help_setup_dry_run="Setup durumunu raporla. Interaktif kurulumlar icin make bootstrap kullan.",
    help_symbol="Ticker sembolu, ornegin AAPL veya BTC-USD",
    help_tool_ownership_app="Istege bagli yardimci arac sahipligi kararlarini incele veya kaydet.",
    help_trade_confidence="Proposal guveni: 0.0 ile 1.0 arasi.",
    help_trade_invalidation="Trade fikrini gecersiz kilan istege bagli kosul.",
    help_trade_limit_price="Limit fiyat. --order-type limit ile gereklidir.",
    help_trade_notional="Dolar notional. Quantity veya notional degerlerinden biri gereklidir.",
    help_trade_order_type="Proposal emir tipi. V1 market veya limit destekler.",
    help_trade_quantity="Hisse adedi. Quantity veya notional degerlerinden biri gereklidir.",
    help_trade_reference_price="Proposal icin kullanilan referans fiyat.",
    help_trade_review_notes="Istege bagli review notlari.",
    help_trade_source="manual, scanner veya research-sidecar gibi kaynak etiketi.",
    help_trade_stop_loss="Istege bagli stop loss.",
    help_trade_take_profit="Istege bagli take profit.",
    help_trade_thesis="Operator tarafindan okunabilir kisa proposal tezi.",
    help_trade_side="Trade yonu: buy veya sell.",
    help_trade_proposals_limit="Gosterilecek maksimum trade proposal sayisi.",
    help_trade_proposals_status_filter="Proposal state filtresi: pending, approved, rejected, executed, failed, expired.",
    help_trade_proposal_approval_notes="Zorunlu approval audit notlari.",
    help_trade_proposal_id_approve="Approve edilecek trade proposal id.",
    help_trade_proposal_id_reject="Reject edilecek trade proposal id.",
    help_trade_proposal_reconcile_id="Reconcile edilecek in-flight approved proposal id.",
    help_trade_proposal_reconciliation_notes="Zorunlu reconciliation audit notlari.",
    help_trade_proposal_refresh_id="Accepted broker order iceren executed proposal id.",
    help_trade_proposal_refresh_notes="Zorunlu refresh audit notlari.",
    help_trade_proposal_rejection_reason="Insan tarafindan okunabilir rejection nedeni.",
    help_v1_provider_check="Yerel model/provider hazirligini kontrol et; configured LLM servisine cagri yapabilir.",
    help_webgui_open_browser="Baslatmadan sonra Web GUI URL'sini OS ile ac.",
    help_webgui_service_app="Istege bagli app-owned yerel Web GUI servisini yonet.",
    label_agent="Agent",
    label_allowed="Izinli",
    label_adapter="Adapter",
    label_alpaca_credentials_configured="Alpaca Credential'lari Ayarli",
    label_alpaca_feed="Alpaca Feed",
    label_alpaca_paper_endpoint="Alpaca Paper Endpoint",
    label_approved="Onaylandi",
    label_api_key="API Key",
    label_average_price="Ortalama Fiyat",
    label_baseline="Baseline",
    label_base_url="Base URL",
    label_backend="Backend",
    label_background_mode="Background Modu",
    label_bias="Bias",
    label_blocking="Bloklayici",
    label_camofox="Camofox",
    label_category="Kategori",
    label_cash="Nakit",
    label_check="Kontrol",
    label_closed_trades="Kapanan Trade'ler",
    label_continuous="Surekli",
    label_confidence="Guven",
    label_context="Baglam",
    label_core_dependency="Core Dependency",
    label_core_ready="Core Hazir",
    label_created="Olusturuldu",
    label_currency="Para Birimi",
    label_current="Gecerli",
    label_current_symbol="Gecerli Sembol",
    label_cycle="Dongu",
    label_cycle_control="Cycle Control",
    label_cycle_count="Dongu Sayisi",
    label_cycles="Donguler",
    label_database="Veritabani",
    label_db_status="DB Durumu",
    label_daily_realized_pnl="Gunluk Gerceklesen PnL",
    label_decision="Karar",
    label_decision_path="Karar Yolu",
    label_default_model="Varsayilan Model",
    label_details="Detaylar",
    label_delta="Delta",
    label_digest_replay="Digest Replay",
    label_drawdown_from_peak="Zirveden Drawdown",
    label_ending_equity="Final Equity",
    label_entry="Giris",
    label_entry_px="Giris Fiyati",
    label_equity="Equity",
    label_enabled="Etkin",
    label_environment_exists="Environment Var",
    label_exposure="Exposure",
    label_exit="Cikis",
    label_exit_code="Exit Code",
    label_exit_px="Cikis Fiyati",
    label_expectancy="Expectancy",
    label_fallback="Fallback",
    label_fallback_cycles="Fallback Donguleri",
    label_fees="Ucretler",
    label_field="Alan",
    label_fills_today="Bugunku Fill'ler",
    label_final_rationale="Final Gerekce",
    label_final_side="Final Yon",
    label_freshness="Freshness",
    label_flow_dir="Flow Dir",
    label_generated="Uretildi",
    label_gross_exposure="Brut Exposure",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Yasi",
    label_healthcheck="Healthcheck",
    label_id="ID",
    label_interval="Aralik",
    label_environment="Ortam",
    label_key="Anahtar",
    label_last_recorded_error="Son Kayitli Hata",
    label_last_recorded_message="Son Kayitli Mesaj",
    label_last_recorded_state="Son Kayitli Durum",
    label_largest_position="En Buyuk Pozisyon",
    label_kill_switch_active="Kill Switch Aktif",
    label_last_error="Son Hata",
    label_last_successful_update="Son Basarili Guncelleme",
    label_last_terminal_at="Son Terminal Zamani",
    label_last_terminal_state="Son Terminal Durumu",
    label_level="Seviye",
    label_lockfile_exists="Lockfile Var",
    label_launch_count="Launch Sayisi",
    label_latest_order="Son Order",
    label_llm_provider="LLM Provider",
    label_live_execution_enabled="Live Execution Etkin",
    label_live_process="Canli Process",
    label_live_ready="Live Hazir",
    label_live_requested="Live Istendi",
    label_llm="LLM",
    label_locale="Locale",
    label_lookback="Geriye Donuk Pencere",
    label_market_value="Piyasa Degeri",
    label_market_price="Piyasa Fiyati",
    label_market_provider="Market Provider",
    label_market_role="Market Rolu",
    label_mark_source="Mark Kaynagi",
    label_mark_status="Mark Durumu",
    label_marked_at="Mark Zamani",
    label_marks_recorded="Kayitli Mark'lar",
    label_max_drawdown="Maksimum Drawdown",
    label_max_cycles="Maksimum Dongu",
    label_memories="Hafizalar",
    label_meaning="Anlam",
    label_message="Mesaj",
    label_metric="Metrik",
    label_mode="Mod",
    label_model="Model",
    label_model_available="Model Kullanilabilir",
    label_model_routing="Model Routing",
    label_multi_timeframe="Multi-Timeframe",
    label_no="hayir",
    label_notes="Notlar",
    label_next="Sonraki",
    label_news_mode="News Modu",
    label_observer_mode="Observer Modu",
    label_open_positions="Acik Pozisyonlar",
    label_opened="Acilis",
    label_order_id="Order ID",
    label_ownership="Sahiplik",
    label_ollama_reachable="Ollama Erisilebilir",
    label_output="Cikti",
    label_output_preview="Cikti Onizleme",
    label_optional_runtime_ready="Optional Runtime Hazir",
    label_pid="PID",
    label_passed="Gecti",
    label_persisted="Kalici",
    label_platform="Platform",
    label_pnl="PnL",
    label_path="Path",
    label_poll_seconds="Poll Saniyesi",
    label_preset="Preset",
    label_preference_update="Preference Guncellemesi",
    label_provider="Provider",
    label_python_version="Python Version",
    label_quantity="Miktar",
    label_proposal="Proposal",
    label_rationale="Gerekce",
    label_realized_pnl="Gerceklesen PnL",
    label_ref="Ref",
    label_rejection_evidence="Red Kaniti",
    label_reason="Neden",
    label_resolution_notes="Cozum Notlari",
    label_requires_confirmation="Onay Gerektirir",
    label_research_cycle_control="Research cycle control",
    label_restart_count="Restart Sayisi",
    label_return="Return",
    label_runtime="Runtime",
    label_runtime_daemon="Runtime Daemon",
    label_runtime_dir="Runtime Dir",
    label_role="Rol",
    label_service="Servis",
    label_side="Yon",
    label_source="Kaynak",
    label_specialist="Specialist",
    label_setup="Setup",
    label_scaffold_exists="Scaffold Var",
    label_signal="Sinyal",
    label_simulated="Simule",
    label_sidecar_available="Sidecar Kullanilabilir",
    label_size="Boyut",
    label_score="Skor",
    label_slippage="Slippage",
    label_stage="Asama",
    label_started="Basladi",
    label_state="State",
    label_status="Durum",
    label_status_note="Durum Notu",
    label_stderr="Stderr",
    label_stderr_log="Stderr Log",
    label_stdout="Stdout",
    label_stdout_log="Stdout Log",
    label_strategy="Strateji",
    label_surface="Yuzey",
    label_stop_requested="Durdurma Istendi",
    label_stop="Stop",
    label_structured_llm="Yapilandirilmis LLM yaniti",
    label_summary="Ozet",
    label_symbol="Sembol",
    label_symbols="Semboller",
    label_supported="Desteklenen",
    label_target="Hedef",
    label_take="Take",
    label_take_profit="Take Profit",
    label_tool="Tool",
    label_tools="Araclar",
    label_total_return="Toplam Return",
    label_trades="Trade'ler",
    label_trigger_now="Simdi Tetikle",
    label_trigger_now_requested="Simdi tetikleme istendi",
    label_type="Tip",
    label_purpose="Amac",
    label_update_preferences="Tercihleri Guncelle",
    label_updated="Guncellendi",
    label_updated_at="Guncelleme Zamani",
    label_unrealized_pnl="Gerceklesmemis PnL",
    label_uv_available="uv Kullanilabilir",
    label_value="Deger",
    label_version="Versiyon",
    label_version_source="Versiyon Kaynagi",
    label_warmup_bars="Warmup Bar'lari",
    label_watched_symbols="Izlenen Semboller",
    label_with_memory="Hafiza Ile",
    label_warnings="Uyarilar",
    label_win_rate="Kazanma Orani",
    label_without_memory="Hafiza Olmadan",
    label_v1_source="V1 Kaynagi",
    label_web_gui="Web GUI",
    label_workspace="Workspace",
    label_yes="evet",
    list_separator=", ",
    message_all_agent_stages_llm_path="Tum agent asamalari LLM yolu ile tamamlandi.",
    message_fallback_used_in="Fallback kullanilan asamalar",
    message_no_elevated_portfolio_risk_warnings=(
        "Bu rapor icin yuksek portfoy risk uyarisi yok."
    ),
    message_no_runtime_state="Henuz runtime durumu kaydedilmedi.",
    message_no_runtime_events="Henuz runtime olayi kaydedilmedi.",
    message_no_stderr_log_lines="Henuz stderr log satiri yok.",
    message_no_stdout_log_lines="Henuz stdout log satiri yok.",
    message_no_trade_journal_entries="Henuz trade journal kaydi yok.",
    message_no_historical_memories="Henuz historical memory yok.",
    message_no_action_selected="Aksiyon secilmedi.",
    message_no_open_positions="Acik pozisyon yok.",
    message_no_proposal_candidates="Henuz proposal candidate kaydi yok.",
    message_no_trade_proposals="Henuz trade proposal kaydi yok.",
    message_finance_operations_unavailable="Finance operations durumu kullanilamiyor.",
    message_gross_exposure_above_equity="Gross exposure equity'nin {limit} uzerinde.",
    message_largest_position_above_equity="En buyuk pozisyon equity'nin {limit} uzerinde.",
    message_background_requires_continuous="Background modu --continuous gerektirir.",
    message_launch_plan=(
        "Semboller: {symbols}\nAralik: {interval}\nLookback: {lookback}\n"
        "Surekli: {continuous}\nPoll Saniyesi: {poll_seconds}\nBackground: {background}"
    ),
    message_launch_symbol_required="En az bir sembol gereklidir.",
    message_mark_time_unavailable="mark zamani yok",
    message_open_position_count_elevated="Acik pozisyon sayisi yuksek.",
    message_portfolio_concentration_hhi=(
        "Portfoy konsantrasyon HHI {score:.3f} ile yuksek."
    ),
    message_position_plan_repair_unavailable="Position plan repair durumu kullanilamiyor.",
    message_position_plan_repair_temporarily_unavailable=(
        "Runtime writer veritabaninin sahibiyken position plan repair gecici "
        "olarak kullanilamiyor.\n\n{error}"
    ),
    message_proposal_candidates_temporarily_unavailable=(
        "Runtime writer veritabaninin sahibiyken proposal candidate'leri gecici "
        "olarak kullanilamiyor.\n\n{error}"
    ),
    message_proposal_candidate_created=(
        "{candidate_id} review icin kaydedildi.\n\n"
        "{symbol} {signal} score={score:.2f}"
    ),
    message_proposal_candidate_promoted=(
        "{candidate_id} -> {proposal_id}\n"
        "Pending proposal olarak kuyruga alindi. Broker submission denenmedi."
    ),
    message_research_cycle_choose_one_action="--pause, --resume veya --trigger-now icinden yalnizca birini secin.",
    message_research_cycle_control_status="{label}: {status}\n{trigger_label}: {trigger_now}",
    message_research_cycle_reason_requires_action="--reason icin --pause, --resume veya --trigger-now gerekir.",
    message_research_snapshot_recorded="Snapshot {snapshot_id} research feed icine kaydedildi.",
    message_runtime_gate_open="Ollama {base_url} adresinde erisilebilir ve {model_name} modeli kullanilabilir.",
    message_portfolio_temporarily_unavailable=(
        "Runtime writer veritabaninin sahibiyken portfolio view gecici olarak "
        "kullanilamiyor.\n\n{error}"
    ),
    message_trade_proposals_temporarily_unavailable=(
        "Runtime writer veritabaninin sahibiyken trade proposal'lari gecici "
        "olarak kullanilamiyor.\n\n{error}"
    ),
    message_trade_proposal_approved=(
        "{proposal_id} -> {status}\norder={order_id} status={outcome_status}"
    ),
    message_trade_proposal_created=(
        "{proposal_id} manual review icin kuyruga alindi.\n\n"
        "{symbol} {side} @ {reference_price:.4f}"
    ),
    message_trade_proposal_reconciled=(
        "{proposal_id} -> {status}\n"
        "order={order_id} status={outcome_status}\n"
        "Broker resubmission denenmedi."
    ),
    message_trade_proposal_refreshed=(
        "{proposal_id} -> {status}\n"
        "order={order_id} status={outcome_status}\n"
        "Broker resubmission denenmedi."
    ),
    message_trade_proposal_rejected=(
        "{proposal_id} reddedildi.\n\nNeden: {reason}"
    ),
    message_runtime_mode_transition_allowed=(
        "Runtime mode gecisi {current_mode} -> {target_mode} izinli."
    ),
    message_runtime_mode_transition_blocked=(
        "Runtime mode gecisi {current_mode} -> {target_mode} bloklandi."
    ),
    message_setup_bootstrap_guidance="Interaktif system-tool installer icin `make bootstrap` calistirin.",
    message_trading_runtime_blocked=(
        "Ollama ve configured model kullanilabilir olana kadar trading runtime baslamamali."
    ),
    message_trading_runtime_ready="Trading runtime tam LLM erisimiyle baslayabilir.",
    message_training_diagnostic_fallback=(
        "Training modu bu degerlendirmeye deterministic diagnostic fallback ile "
        "devam ediyor cunku LLM gate basarisiz oldu:\n\n{error}"
    ),
    message_v1_readiness_status_unavailable="V1 readiness durumu kullanilamiyor.",
    prompt_continue="Devam etmek icin Enter'a basin",
    prompt_select_action="Aksiyon sec",
    launcher_option_open_web_gui="1  Yerel Web GUI command center'i ac/baslat",
    launcher_option_continue_tui="2  Rich terminal control room ile devam et",
    launcher_option_refresh="3  Burada kal ve launcher'i yenile",
    launcher_option_exit="4  Cikis",
    stage_coordinator="Coordinator",
    stage_consensus="Consensus",
    stage_execution="Execution",
    stage_fundamental="Fundamental",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column=EN_TEXT.style_key_column,
    status_active="aktif",
    status_app_owned="app-owned",
    status_available="kullanilabilir",
    status_external="harici",
    status_fail="fail",
    status_needs_attention="dikkat gerekiyor",
    status_pass="pass",
    status_ready="hazir",
    title_agent_decisions="Agent Kararlari",
    title_agent_trace="Agent Trace",
    title_approval_blocked="Approval Bloklandi",
    title_available_models="Kullanilabilir Modeller",
    title_backtest_comparison="Backtest Karsilastirma",
    title_backtest_memory_ablation="Backtest Memory Ablation",
    title_backtest_trades="Backtest Trade'leri",
    title_broker_status="Broker Durumu",
    title_alpaca_paper_checks="Alpaca Paper Kontrolleri",
    title_candidate_rejected="Candidate Reddedildi",
    title_camofox_browser_helper="Camofox Browser Yardimcisi",
    title_camofox_stderr_tail="Camofox Stderr Kuyrugu",
    title_camofox_start_failed="Camofox Baslatma Basarisiz",
    title_choose_surface="Yuzey Sec",
    title_execution_summary="Execution Ozeti",
    title_llm_status="LLM Durumu",
    title_operator_instruction="Operator Talimati",
    title_operator_launcher="Agentic Trader Operator Launcher",
    title_pipeline="Pipeline",
    title_paper_operation_checks="Paper Operation Kontrolleri",
    title_provider_diagnostics="Provider Diagnostics",
    title_provider_source_ladder="Provider Source Ladder",
    title_daily_risk_report="Gunluk Risk Raporu",
    title_desk_accounting_context="Desk Accounting Context",
    title_environment_check="Environment Check",
    title_exit="Cikis",
    title_finance_ledger_categories="Finance Ledger Kategorileri",
    title_finance_operations="Finance Operations",
    title_finance_operations_checks="Finance Operations Kontrolleri",
    title_manager_conflicts="Manager Catismalari",
    title_manager_conflict_replay="Manager Catisma Replay",
    title_manager_override_notes="Manager Override Notlari",
    title_memory_aware_replay="Memory-Aware Replay",
    title_memory_explorer="Memory Explorer",
    title_model_pull="Model Cekme",
    title_model_service_stderr_tail="Model Service Stderr Kuyrugu",
    title_model_service_start_failed="Model Service Baslatma Basarisiz",
    title_recent_runs="Son Run'lar",
    title_risk_warnings="Risk Uyarilari",
    title_review_note="Review Notu",
    title_replay_stages="Replay Asamalari",
    title_run_artifacts="Run Artifact'lari",
    title_run_review="Run Review",
    title_run_blocked="Run Bloklandi",
    title_reconciliation_blocked="Reconciliation Bloklandi",
    title_refresh_blocked="Refresh Bloklandi",
    title_rejection_blocked="Rejection Bloklandi",
    title_runtime_events="Runtime Olaylari",
    title_runtime_gate_open="Runtime Gate Acik",
    title_launch_plan="Baslatma Plani",
    title_runtime_mode="Runtime Modu",
    title_runtime_mode_transition_checklist="Runtime Mode Gecis Kontrol Listesi",
    title_runtime_status="Runtime Durumu",
    title_service_status="Servis Durumu",
    title_service_stderr_tail="Service Stderr Kuyrugu",
    title_service_stdout_tail="Service Stdout Kuyrugu",
    title_service_supervisor="Service Supervisor",
    title_trade_journal="Trade Journal",
    title_trade_proposals="Trade Proposal'lari",
    title_proposal_candidates="Proposal Candidate'leri",
    title_position_plan_repair="Position Plan Repair",
    title_portfolio="Portfolio",
    title_positions="Pozisyonlar",
    title_proposal_rejected="Proposal Reddedildi",
    title_promotion_blocked="Promotion Bloklandi",
    title_proposal_candidate_created="Proposal Candidate Olusturuldu",
    title_proposal_candidate_promoted="Proposal Candidate Promote Edildi",
    title_recommended_next_commands="Onerilen Sonraki Komutlar",
    title_recommended_commands="Onerilen Komutlar",
    title_research_crewai_flow_setup="Research CrewAI Flow Setup",
    title_research_cycle_control="Research Cycle Control",
    title_research_sidecar_status="Research Sidecar Durumu",
    title_research_source_health="Research Kaynak Sagligi",
    title_research_snapshot_persisted="Research Snapshot Kaydedildi",
    title_setup_status="Setup Durumu",
    title_setup_guidance="Setup Rehberi",
    title_trace="Trace",
    title_trade_proposal_approved="Trade Proposal Onaylandi",
    title_trade_proposal_created="Trade Proposal Olusturuldu",
    title_trade_proposal_reconciled="Trade Proposal Reconcile Edildi",
    title_trade_proposal_refreshed="Trade Proposal Yenilendi",
    title_trade_proposal_rejected="Trade Proposal Reddedildi",
    title_tool_ownership="Tool Ownership",
    title_tool_readiness="Tool Readiness",
    title_training_diagnostic_mode="Training Diagnostic Mode",
    title_ui_locale="UI Locale",
    title_v1_readiness="V1 Readiness",
    title_warning="Uyari",
    title_walk_forward_backtest="Walk-Forward Backtest",
    title_web_gui_service="Web GUI Servisi",
    title_web_gui_start_failed="Web GUI Baslatma Basarisiz",
    title_web_gui_stderr_tail="Web GUI Stderr Kuyrugu",
)

UI_TEXT: dict[UILocale, UITextCatalog] = {
    "en": EN_TEXT,
    "tr": TR_TEXT,
}


def normalize_locale(locale: str | None) -> UILocale:
    """Normalize a locale-ish value to one of the supported UI locales."""

    if not locale:
        return "en"
    normalized = locale.lower()
    if normalized == "tr" or normalized.startswith("tr-"):
        return "tr"
    return "en"


def get_ui_text(locale: str | None = None) -> UITextCatalog:
    """Return the shared UI copy catalog for the requested locale."""

    return UI_TEXT[normalize_locale(locale)]


# Legacy constant exports. Keep these in place until CLI and TUI call sites move
# to explicit locale-aware catalog injection.
HELP_JSON = EN_TEXT.help_json
HELP_LOCALE_OVERRIDE = EN_TEXT.help_locale_override
HELP_LOCALE_PERSIST = EN_TEXT.help_locale_persist
HELP_LAUNCH_BACKGROUND = EN_TEXT.help_launch_background
HELP_LAUNCH_CONTINUOUS = EN_TEXT.help_launch_continuous
HELP_LAUNCH_MAX_CYCLES = EN_TEXT.help_launch_max_cycles
HELP_LAUNCH_POLL_SECONDS = EN_TEXT.help_launch_poll_seconds
HELP_LAUNCH_SYMBOLS = EN_TEXT.help_launch_symbols
HELP_SYMBOL = EN_TEXT.help_symbol
HELP_INTERVAL = EN_TEXT.help_interval
HELP_LOOKBACK = EN_TEXT.help_lookback
HELP_CANDIDATE_FRESHNESS = EN_TEXT.help_candidate_freshness
HELP_CANDIDATE_LIQUIDITY = EN_TEXT.help_candidate_liquidity
HELP_CANDIDATE_MATERIALITY = EN_TEXT.help_candidate_materiality
HELP_CANDIDATE_RISK_NOTES = EN_TEXT.help_candidate_risk_notes
HELP_CANDIDATE_SOURCE = EN_TEXT.help_candidate_source
HELP_ENRICH_PROVIDER_CONTEXT = EN_TEXT.help_enrich_provider_context
HELP_FETCH_PROVIDER_NEWS = EN_TEXT.help_fetch_provider_news
HELP_RUN_ID = EN_TEXT.help_run_id
HELP_MODEL_NAME_TO_PULL = EN_TEXT.help_model_name_to_pull
HELP_MODEL_SERVICE_HOST = EN_TEXT.help_model_service_host
HELP_MODEL_SERVICE_PORT = EN_TEXT.help_model_service_port
HELP_OLLAMA_OWNER = EN_TEXT.help_ollama_owner
HELP_POSITION_PLAN_REPAIR_APPLY = EN_TEXT.help_position_plan_repair_apply
HELP_POSITION_PLAN_REPAIR_MAX_HOLDING_BARS = (
    EN_TEXT.help_position_plan_repair_max_holding_bars
)
HELP_PROPOSAL_CANDIDATE_ID = EN_TEXT.help_proposal_candidate_id
HELP_PROPOSAL_CANDIDATES_LIMIT = EN_TEXT.help_proposal_candidates_limit
HELP_PROPOSAL_CANDIDATES_STATUS_FILTER = (
    EN_TEXT.help_proposal_candidates_status_filter
)
HELP_PROMOTION_NOTES = EN_TEXT.help_promotion_notes
HELP_RESEARCH_CYCLE_PAUSE = EN_TEXT.help_research_cycle_pause
HELP_RESEARCH_CYCLE_REASON = EN_TEXT.help_research_cycle_reason
HELP_RESEARCH_CYCLE_RESUME = EN_TEXT.help_research_cycle_resume
HELP_RESEARCH_CYCLE_TRIGGER_NOW = EN_TEXT.help_research_cycle_trigger_now
HELP_RESEARCH_PROBE = EN_TEXT.help_research_probe
HELP_RESEARCH_REFRESH_PERSIST = EN_TEXT.help_research_refresh_persist
HELP_FIRECRAWL_OWNER = EN_TEXT.help_firecrawl_owner
HELP_CAMOFOX_OWNER = EN_TEXT.help_camofox_owner
HELP_CAMOFOX_SERVICE_HOST = EN_TEXT.help_camofox_service_host
HELP_CAMOFOX_SERVICE_PORT = EN_TEXT.help_camofox_service_port
HELP_RUNTIME_MODE_PROVIDER_CHECK = EN_TEXT.help_runtime_mode_provider_check
HELP_RUNTIME_MODE_TARGET = EN_TEXT.help_runtime_mode_target
HELP_SETUP_DRY_RUN = EN_TEXT.help_setup_dry_run
HELP_CLI_APP = EN_TEXT.cli_app_help
HELP_MODEL_SERVICE_APP = EN_TEXT.help_model_service_app
HELP_WEBGUI_SERVICE_APP = EN_TEXT.help_webgui_service_app
HELP_CAMOFOX_SERVICE_APP = EN_TEXT.help_camofox_service_app
HELP_TOOL_OWNERSHIP_APP = EN_TEXT.help_tool_ownership_app
HELP_IDEA_CHANGE_PCT = EN_TEXT.help_idea_change_pct
HELP_IDEA_EMA_9 = EN_TEXT.help_idea_ema_9
HELP_IDEA_GAP_PCT = EN_TEXT.help_idea_gap_pct
HELP_IDEA_PRESET = EN_TEXT.help_idea_preset
HELP_IDEA_PRICE = EN_TEXT.help_idea_price
HELP_IDEA_RANGE_PCT = EN_TEXT.help_idea_range_pct
HELP_IDEA_RELATIVE_VOLUME = EN_TEXT.help_idea_relative_volume
HELP_IDEA_RSI = EN_TEXT.help_idea_rsi
HELP_IDEA_SMA_20 = EN_TEXT.help_idea_sma_20
HELP_IDEA_SMA_50 = EN_TEXT.help_idea_sma_50
HELP_IDEA_SPREAD_PCT = EN_TEXT.help_idea_spread_pct
HELP_IDEA_VOLUME = EN_TEXT.help_idea_volume
HELP_IDEA_VWAP = EN_TEXT.help_idea_vwap
HELP_TRADE_CONFIDENCE = EN_TEXT.help_trade_confidence
HELP_TRADE_INVALIDATION = EN_TEXT.help_trade_invalidation
HELP_TRADE_LIMIT_PRICE = EN_TEXT.help_trade_limit_price
HELP_TRADE_SIDE = EN_TEXT.help_trade_side
HELP_TRADE_QUANTITY = EN_TEXT.help_trade_quantity
HELP_TRADE_NOTIONAL = EN_TEXT.help_trade_notional
HELP_TRADE_ORDER_TYPE = EN_TEXT.help_trade_order_type
HELP_TRADE_REFERENCE_PRICE = EN_TEXT.help_trade_reference_price
HELP_TRADE_REVIEW_NOTES = EN_TEXT.help_trade_review_notes
HELP_TRADE_SOURCE = EN_TEXT.help_trade_source
HELP_TRADE_STOP_LOSS = EN_TEXT.help_trade_stop_loss
HELP_TRADE_TAKE_PROFIT = EN_TEXT.help_trade_take_profit
HELP_TRADE_THESIS = EN_TEXT.help_trade_thesis
HELP_TRADE_PROPOSALS_LIMIT = EN_TEXT.help_trade_proposals_limit
HELP_TRADE_PROPOSALS_STATUS_FILTER = EN_TEXT.help_trade_proposals_status_filter
HELP_TRADE_PROPOSAL_APPROVAL_NOTES = EN_TEXT.help_trade_proposal_approval_notes
HELP_TRADE_PROPOSAL_ID_APPROVE = EN_TEXT.help_trade_proposal_id_approve
HELP_TRADE_PROPOSAL_ID_REJECT = EN_TEXT.help_trade_proposal_id_reject
HELP_TRADE_PROPOSAL_RECONCILE_ID = EN_TEXT.help_trade_proposal_reconcile_id
HELP_TRADE_PROPOSAL_RECONCILIATION_NOTES = (
    EN_TEXT.help_trade_proposal_reconciliation_notes
)
HELP_TRADE_PROPOSAL_REFRESH_ID = EN_TEXT.help_trade_proposal_refresh_id
HELP_TRADE_PROPOSAL_REFRESH_NOTES = EN_TEXT.help_trade_proposal_refresh_notes
HELP_TRADE_PROPOSAL_REJECTION_REASON = (
    EN_TEXT.help_trade_proposal_rejection_reason
)
HELP_V1_PROVIDER_CHECK = EN_TEXT.help_v1_provider_check
HELP_WEBGUI_OPEN_BROWSER = EN_TEXT.help_webgui_open_browser

LABEL_AGENT = EN_TEXT.label_agent
LABEL_ALLOWED = EN_TEXT.label_allowed
LABEL_ADAPTER = EN_TEXT.label_adapter
LABEL_ALPACA_CREDENTIALS_CONFIGURED = EN_TEXT.label_alpaca_credentials_configured
LABEL_ALPACA_FEED = EN_TEXT.label_alpaca_feed
LABEL_ALPACA_PAPER_ENDPOINT = EN_TEXT.label_alpaca_paper_endpoint
LABEL_APPROVED = EN_TEXT.label_approved
LABEL_API_KEY = EN_TEXT.label_api_key
LABEL_AVERAGE_PRICE = EN_TEXT.label_average_price
LABEL_BASELINE = EN_TEXT.label_baseline
LABEL_BASE_URL = EN_TEXT.label_base_url
LABEL_BACKEND = EN_TEXT.label_backend
LABEL_BACKGROUND_MODE = EN_TEXT.label_background_mode
LABEL_BIAS = EN_TEXT.label_bias
LABEL_BLOCKING = EN_TEXT.label_blocking
LABEL_CAMOFOX = EN_TEXT.label_camofox
LABEL_CATEGORY = EN_TEXT.label_category
LABEL_CASH = EN_TEXT.label_cash
LABEL_CHECK = EN_TEXT.label_check
LABEL_CLOSED_TRADES = EN_TEXT.label_closed_trades
LABEL_CONTINUOUS = EN_TEXT.label_continuous
LABEL_CONFIDENCE = EN_TEXT.label_confidence
LABEL_CONTEXT = EN_TEXT.label_context
LABEL_CORE_DEPENDENCY = EN_TEXT.label_core_dependency
LABEL_CORE_READY = EN_TEXT.label_core_ready
LABEL_CREATED = EN_TEXT.label_created
LABEL_CURRENCY = EN_TEXT.label_currency
LABEL_CURRENT = EN_TEXT.label_current
LABEL_CURRENT_SYMBOL = EN_TEXT.label_current_symbol
LABEL_CYCLE = EN_TEXT.label_cycle
LABEL_CYCLE_CONTROL = EN_TEXT.label_cycle_control
LABEL_CYCLE_COUNT = EN_TEXT.label_cycle_count
LABEL_CYCLES = EN_TEXT.label_cycles
LABEL_DATABASE = EN_TEXT.label_database
LABEL_DB_STATUS = EN_TEXT.label_db_status
LABEL_DAILY_REALIZED_PNL = EN_TEXT.label_daily_realized_pnl
LABEL_DECISION = EN_TEXT.label_decision
LABEL_DECISION_PATH = EN_TEXT.label_decision_path
LABEL_DEFAULT_MODEL = EN_TEXT.label_default_model
LABEL_DETAILS = EN_TEXT.label_details
LABEL_DELTA = EN_TEXT.label_delta
LABEL_DIGEST_REPLAY = EN_TEXT.label_digest_replay
LABEL_DRAWDOWN_FROM_PEAK = EN_TEXT.label_drawdown_from_peak
LABEL_ENDING_EQUITY = EN_TEXT.label_ending_equity
LABEL_ENTRY = EN_TEXT.label_entry
LABEL_ENTRY_PX = EN_TEXT.label_entry_px
LABEL_EQUITY = EN_TEXT.label_equity
LABEL_ENABLED = EN_TEXT.label_enabled
LABEL_ENVIRONMENT_EXISTS = EN_TEXT.label_environment_exists
LABEL_EXPOSURE = EN_TEXT.label_exposure
LABEL_EXIT = EN_TEXT.label_exit
LABEL_EXIT_CODE = EN_TEXT.label_exit_code
LABEL_EXIT_PX = EN_TEXT.label_exit_px
LABEL_EXPECTANCY = EN_TEXT.label_expectancy
LABEL_FALLBACK = EN_TEXT.label_fallback
LABEL_FALLBACK_CYCLES = EN_TEXT.label_fallback_cycles
LABEL_FEES = EN_TEXT.label_fees
LABEL_FIELD = EN_TEXT.label_field
LABEL_FILLS_TODAY = EN_TEXT.label_fills_today
LABEL_FINAL_RATIONALE = EN_TEXT.label_final_rationale
LABEL_FINAL_SIDE = EN_TEXT.label_final_side
LABEL_FRESHNESS = EN_TEXT.label_freshness
LABEL_FLOW_DIR = EN_TEXT.label_flow_dir
LABEL_GENERATED = EN_TEXT.label_generated
LABEL_GROSS_EXPOSURE = EN_TEXT.label_gross_exposure
LABEL_HEARTBEAT = EN_TEXT.label_heartbeat
LABEL_HEARTBEAT_AGE = EN_TEXT.label_heartbeat_age
LABEL_HEALTHCHECK = EN_TEXT.label_healthcheck
LABEL_ID = EN_TEXT.label_id
LABEL_INTERVAL = EN_TEXT.label_interval
LABEL_ENVIRONMENT = EN_TEXT.label_environment
LABEL_KEY = EN_TEXT.label_key
LABEL_LAST_RECORDED_ERROR = EN_TEXT.label_last_recorded_error
LABEL_LAST_RECORDED_MESSAGE = EN_TEXT.label_last_recorded_message
LABEL_LAST_RECORDED_STATE = EN_TEXT.label_last_recorded_state
LABEL_KILL_SWITCH_ACTIVE = EN_TEXT.label_kill_switch_active
LABEL_LARGEST_POSITION = EN_TEXT.label_largest_position
LABEL_LAST_ERROR = EN_TEXT.label_last_error
LABEL_LAST_SUCCESSFUL_UPDATE = EN_TEXT.label_last_successful_update
LABEL_LAST_TERMINAL_AT = EN_TEXT.label_last_terminal_at
LABEL_LAST_TERMINAL_STATE = EN_TEXT.label_last_terminal_state
LABEL_LEVEL = EN_TEXT.label_level
LABEL_LOCKFILE_EXISTS = EN_TEXT.label_lockfile_exists
LABEL_LAUNCH_COUNT = EN_TEXT.label_launch_count
LABEL_LATEST_ORDER = EN_TEXT.label_latest_order
LABEL_LLM_PROVIDER = EN_TEXT.label_llm_provider
LABEL_LIVE_EXECUTION_ENABLED = EN_TEXT.label_live_execution_enabled
LABEL_LIVE_PROCESS = EN_TEXT.label_live_process
LABEL_LIVE_READY = EN_TEXT.label_live_ready
LABEL_LIVE_REQUESTED = EN_TEXT.label_live_requested
LABEL_LLM = EN_TEXT.label_llm
LABEL_LOCALE = EN_TEXT.label_locale
LABEL_LOOKBACK = EN_TEXT.label_lookback
LABEL_MARKET_VALUE = EN_TEXT.label_market_value
LABEL_MARKET_PRICE = EN_TEXT.label_market_price
LABEL_MARKET_PROVIDER = EN_TEXT.label_market_provider
LABEL_MARKET_ROLE = EN_TEXT.label_market_role
LABEL_MARK_SOURCE = EN_TEXT.label_mark_source
LABEL_MARK_STATUS = EN_TEXT.label_mark_status
LABEL_MARKED_AT = EN_TEXT.label_marked_at
LABEL_MARKS_RECORDED = EN_TEXT.label_marks_recorded
LABEL_MAX_DRAWDOWN = EN_TEXT.label_max_drawdown
LABEL_MAX_CYCLES = EN_TEXT.label_max_cycles
LABEL_MEMORIES = EN_TEXT.label_memories
LABEL_MEANING = EN_TEXT.label_meaning
LABEL_MESSAGE = EN_TEXT.label_message
LABEL_METRIC = EN_TEXT.label_metric
LABEL_MODE = EN_TEXT.label_mode
LABEL_MODEL = EN_TEXT.label_model
LABEL_MODEL_AVAILABLE = EN_TEXT.label_model_available
LABEL_MODEL_ROUTING = EN_TEXT.label_model_routing
LABEL_MULTI_TIMEFRAME = EN_TEXT.label_multi_timeframe
LABEL_NO = EN_TEXT.label_no
LABEL_NOTES = EN_TEXT.label_notes
LABEL_NEXT = EN_TEXT.label_next
LABEL_NEWS_MODE = EN_TEXT.label_news_mode
LABEL_OBSERVER_MODE = EN_TEXT.label_observer_mode
LABEL_OPEN_POSITIONS = EN_TEXT.label_open_positions
LABEL_OPENED = EN_TEXT.label_opened
LABEL_ORDER_ID = EN_TEXT.label_order_id
LABEL_OWNERSHIP = EN_TEXT.label_ownership
LABEL_OLLAMA_REACHABLE = EN_TEXT.label_ollama_reachable
LABEL_OUTPUT = EN_TEXT.label_output
LABEL_OUTPUT_PREVIEW = EN_TEXT.label_output_preview
LABEL_OPTIONAL_RUNTIME_READY = EN_TEXT.label_optional_runtime_ready
LABEL_PASSED = EN_TEXT.label_passed
LABEL_PERSISTED = EN_TEXT.label_persisted
LABEL_PLATFORM = EN_TEXT.label_platform
LABEL_PID = EN_TEXT.label_pid
LABEL_PNL = EN_TEXT.label_pnl
LABEL_PATH = EN_TEXT.label_path
LABEL_POLL_SECONDS = EN_TEXT.label_poll_seconds
LABEL_PRESET = EN_TEXT.label_preset
LABEL_PREFERENCE_UPDATE = EN_TEXT.label_preference_update
LABEL_PROVIDER = EN_TEXT.label_provider
LABEL_PYTHON_VERSION = EN_TEXT.label_python_version
LABEL_QUANTITY = EN_TEXT.label_quantity
LABEL_PROPOSAL = EN_TEXT.label_proposal
LABEL_RATIONALE = EN_TEXT.label_rationale
LABEL_REALIZED_PNL = EN_TEXT.label_realized_pnl
LABEL_REF = EN_TEXT.label_ref
LABEL_REJECTION_EVIDENCE = EN_TEXT.label_rejection_evidence
LABEL_REASON = EN_TEXT.label_reason
LABEL_RESOLUTION_NOTES = EN_TEXT.label_resolution_notes
LABEL_REQUIRES_CONFIRMATION = EN_TEXT.label_requires_confirmation
LABEL_RESEARCH_CYCLE_CONTROL = EN_TEXT.label_research_cycle_control
LABEL_RESTART_COUNT = EN_TEXT.label_restart_count
LABEL_RETURN = EN_TEXT.label_return
LABEL_RUNTIME = EN_TEXT.label_runtime
LABEL_RUNTIME_DAEMON = EN_TEXT.label_runtime_daemon
LABEL_RUNTIME_DIR = EN_TEXT.label_runtime_dir
LABEL_ROLE = EN_TEXT.label_role
LABEL_SERVICE = EN_TEXT.label_service
LABEL_SIDE = EN_TEXT.label_side
LABEL_SOURCE = EN_TEXT.label_source
LABEL_SPECIALIST = EN_TEXT.label_specialist
LABEL_SETUP = EN_TEXT.label_setup
LABEL_SCAFFOLD_EXISTS = EN_TEXT.label_scaffold_exists
LABEL_SIGNAL = EN_TEXT.label_signal
LABEL_SIMULATED = EN_TEXT.label_simulated
LABEL_SIDECAR_AVAILABLE = EN_TEXT.label_sidecar_available
LABEL_SIZE = EN_TEXT.label_size
LABEL_SCORE = EN_TEXT.label_score
LABEL_SLIPPAGE = EN_TEXT.label_slippage
LABEL_STAGE = EN_TEXT.label_stage
LABEL_STARTED = EN_TEXT.label_started
LABEL_STATE = EN_TEXT.label_state
LABEL_STATUS = EN_TEXT.label_status
LABEL_STATUS_NOTE = EN_TEXT.label_status_note
LABEL_STDERR = EN_TEXT.label_stderr
LABEL_STDERR_LOG = EN_TEXT.label_stderr_log
LABEL_STDOUT = EN_TEXT.label_stdout
LABEL_STDOUT_LOG = EN_TEXT.label_stdout_log
LABEL_STRATEGY = EN_TEXT.label_strategy
LABEL_SURFACE = EN_TEXT.label_surface
LABEL_STOP_REQUESTED = EN_TEXT.label_stop_requested
LABEL_STOP = EN_TEXT.label_stop
LABEL_STRUCTURED_LLM = EN_TEXT.label_structured_llm
LABEL_SUMMARY = EN_TEXT.label_summary
LABEL_SYMBOL = EN_TEXT.label_symbol
LABEL_SYMBOLS = EN_TEXT.label_symbols
LABEL_SUPPORTED = EN_TEXT.label_supported
LABEL_TARGET = EN_TEXT.label_target
LABEL_TAKE = EN_TEXT.label_take
LABEL_TAKE_PROFIT = EN_TEXT.label_take_profit
LABEL_TOOL = EN_TEXT.label_tool
LABEL_TOOLS = EN_TEXT.label_tools
LABEL_TOTAL_RETURN = EN_TEXT.label_total_return
LABEL_TRADES = EN_TEXT.label_trades
LABEL_TRIGGER_NOW = EN_TEXT.label_trigger_now
LABEL_TRIGGER_NOW_REQUESTED = EN_TEXT.label_trigger_now_requested
LABEL_TYPE = EN_TEXT.label_type
LABEL_PURPOSE = EN_TEXT.label_purpose
LABEL_UPDATE_PREFERENCES = EN_TEXT.label_update_preferences
LABEL_UPDATED = EN_TEXT.label_updated
LABEL_UPDATED_AT = EN_TEXT.label_updated_at
LABEL_UNREALIZED_PNL = EN_TEXT.label_unrealized_pnl
LABEL_UV_AVAILABLE = EN_TEXT.label_uv_available
LABEL_VALUE = EN_TEXT.label_value
LABEL_VERSION = EN_TEXT.label_version
LABEL_VERSION_SOURCE = EN_TEXT.label_version_source
LABEL_WARMUP_BARS = EN_TEXT.label_warmup_bars
LABEL_WATCHED_SYMBOLS = EN_TEXT.label_watched_symbols
LABEL_WITH_MEMORY = EN_TEXT.label_with_memory
LABEL_WARNINGS = EN_TEXT.label_warnings
LABEL_WIN_RATE = EN_TEXT.label_win_rate
LABEL_WITHOUT_MEMORY = EN_TEXT.label_without_memory
LABEL_V1_SOURCE = EN_TEXT.label_v1_source
LABEL_WEB_GUI = EN_TEXT.label_web_gui
LABEL_WORKSPACE = EN_TEXT.label_workspace
LABEL_YES = EN_TEXT.label_yes
UI_LIST_SEPARATOR = EN_TEXT.list_separator

MESSAGE_ALL_AGENT_STAGES_LLM_PATH = EN_TEXT.message_all_agent_stages_llm_path
MESSAGE_FALLBACK_USED_IN = EN_TEXT.message_fallback_used_in
MESSAGE_NO_ELEVATED_PORTFOLIO_RISK_WARNINGS = (
    EN_TEXT.message_no_elevated_portfolio_risk_warnings
)
MESSAGE_NO_RUNTIME_STATE = EN_TEXT.message_no_runtime_state
MESSAGE_NO_RUNTIME_EVENTS = EN_TEXT.message_no_runtime_events
MESSAGE_NO_STDERR_LOG_LINES = EN_TEXT.message_no_stderr_log_lines
MESSAGE_NO_STDOUT_LOG_LINES = EN_TEXT.message_no_stdout_log_lines
MESSAGE_NO_TRADE_JOURNAL_ENTRIES = EN_TEXT.message_no_trade_journal_entries
MESSAGE_NO_HISTORICAL_MEMORIES = EN_TEXT.message_no_historical_memories
MESSAGE_NO_ACTION_SELECTED = EN_TEXT.message_no_action_selected
MESSAGE_NO_OPEN_POSITIONS = EN_TEXT.message_no_open_positions
MESSAGE_NO_PROPOSAL_CANDIDATES = EN_TEXT.message_no_proposal_candidates
MESSAGE_NO_TRADE_PROPOSALS = EN_TEXT.message_no_trade_proposals
MESSAGE_FINANCE_OPERATIONS_UNAVAILABLE = EN_TEXT.message_finance_operations_unavailable
MESSAGE_GROSS_EXPOSURE_ABOVE_EQUITY = EN_TEXT.message_gross_exposure_above_equity
MESSAGE_LARGEST_POSITION_ABOVE_EQUITY = EN_TEXT.message_largest_position_above_equity
MESSAGE_BACKGROUND_REQUIRES_CONTINUOUS = (
    EN_TEXT.message_background_requires_continuous
)
MESSAGE_LAUNCH_PLAN = EN_TEXT.message_launch_plan
MESSAGE_LAUNCH_SYMBOL_REQUIRED = EN_TEXT.message_launch_symbol_required
MESSAGE_MARK_TIME_UNAVAILABLE = EN_TEXT.message_mark_time_unavailable
MESSAGE_OPEN_POSITION_COUNT_ELEVATED = EN_TEXT.message_open_position_count_elevated
MESSAGE_PORTFOLIO_CONCENTRATION_HHI = EN_TEXT.message_portfolio_concentration_hhi
MESSAGE_PORTFOLIO_TEMPORARILY_UNAVAILABLE = (
    EN_TEXT.message_portfolio_temporarily_unavailable
)
MESSAGE_POSITION_PLAN_REPAIR_UNAVAILABLE = (
    EN_TEXT.message_position_plan_repair_unavailable
)
MESSAGE_POSITION_PLAN_REPAIR_TEMPORARILY_UNAVAILABLE = (
    EN_TEXT.message_position_plan_repair_temporarily_unavailable
)
MESSAGE_PROPOSAL_CANDIDATES_TEMPORARILY_UNAVAILABLE = (
    EN_TEXT.message_proposal_candidates_temporarily_unavailable
)
MESSAGE_PROPOSAL_CANDIDATE_CREATED = EN_TEXT.message_proposal_candidate_created
MESSAGE_PROPOSAL_CANDIDATE_PROMOTED = EN_TEXT.message_proposal_candidate_promoted
MESSAGE_RESEARCH_CYCLE_CHOOSE_ONE_ACTION = (
    EN_TEXT.message_research_cycle_choose_one_action
)
MESSAGE_RESEARCH_CYCLE_CONTROL_STATUS = (
    EN_TEXT.message_research_cycle_control_status
)
MESSAGE_RESEARCH_CYCLE_REASON_REQUIRES_ACTION = (
    EN_TEXT.message_research_cycle_reason_requires_action
)
MESSAGE_RESEARCH_SNAPSHOT_RECORDED = EN_TEXT.message_research_snapshot_recorded
MESSAGE_RUNTIME_GATE_OPEN = EN_TEXT.message_runtime_gate_open
MESSAGE_RUNTIME_MODE_TRANSITION_ALLOWED = (
    EN_TEXT.message_runtime_mode_transition_allowed
)
MESSAGE_RUNTIME_MODE_TRANSITION_BLOCKED = (
    EN_TEXT.message_runtime_mode_transition_blocked
)
MESSAGE_SETUP_BOOTSTRAP_GUIDANCE = EN_TEXT.message_setup_bootstrap_guidance
MESSAGE_TRADE_PROPOSALS_TEMPORARILY_UNAVAILABLE = (
    EN_TEXT.message_trade_proposals_temporarily_unavailable
)
MESSAGE_TRADE_PROPOSAL_APPROVED = EN_TEXT.message_trade_proposal_approved
MESSAGE_TRADE_PROPOSAL_CREATED = EN_TEXT.message_trade_proposal_created
MESSAGE_TRADE_PROPOSAL_RECONCILED = EN_TEXT.message_trade_proposal_reconciled
MESSAGE_TRADE_PROPOSAL_REFRESHED = EN_TEXT.message_trade_proposal_refreshed
MESSAGE_TRADE_PROPOSAL_REJECTED = EN_TEXT.message_trade_proposal_rejected
MESSAGE_TRADING_RUNTIME_BLOCKED = EN_TEXT.message_trading_runtime_blocked
MESSAGE_TRADING_RUNTIME_READY = EN_TEXT.message_trading_runtime_ready
MESSAGE_TRAINING_DIAGNOSTIC_FALLBACK = EN_TEXT.message_training_diagnostic_fallback
MESSAGE_V1_READINESS_STATUS_UNAVAILABLE = (
    EN_TEXT.message_v1_readiness_status_unavailable
)

STAGE_COORDINATOR = EN_TEXT.stage_coordinator
STAGE_CONSENSUS = EN_TEXT.stage_consensus
STAGE_EXECUTION = EN_TEXT.stage_execution
STAGE_FUNDAMENTAL = EN_TEXT.stage_fundamental
STAGE_MANAGER = EN_TEXT.stage_manager
STAGE_REGIME = EN_TEXT.stage_regime
STAGE_RISK = EN_TEXT.stage_risk
STAGE_STRATEGY = EN_TEXT.stage_strategy

TITLE_AGENT_DECISIONS = EN_TEXT.title_agent_decisions
TITLE_AGENT_TRACE = EN_TEXT.title_agent_trace
TITLE_APPROVAL_BLOCKED = EN_TEXT.title_approval_blocked
TITLE_AVAILABLE_MODELS = EN_TEXT.title_available_models
TITLE_BACKTEST_COMPARISON = EN_TEXT.title_backtest_comparison
TITLE_BACKTEST_MEMORY_ABLATION = EN_TEXT.title_backtest_memory_ablation
TITLE_BACKTEST_TRADES = EN_TEXT.title_backtest_trades
TITLE_BROKER_STATUS = EN_TEXT.title_broker_status
TITLE_ALPACA_PAPER_CHECKS = EN_TEXT.title_alpaca_paper_checks
TITLE_CANDIDATE_REJECTED = EN_TEXT.title_candidate_rejected
TITLE_CAMOFOX_BROWSER_HELPER = EN_TEXT.title_camofox_browser_helper
TITLE_CAMOFOX_STDERR_TAIL = EN_TEXT.title_camofox_stderr_tail
TITLE_CAMOFOX_START_FAILED = EN_TEXT.title_camofox_start_failed
TITLE_CHOOSE_SURFACE = EN_TEXT.title_choose_surface
TITLE_EXECUTION_SUMMARY = EN_TEXT.title_execution_summary
TITLE_LLM_STATUS = EN_TEXT.title_llm_status
TITLE_OPERATOR_INSTRUCTION = EN_TEXT.title_operator_instruction
TITLE_OPERATOR_LAUNCHER = EN_TEXT.title_operator_launcher
TITLE_PIPELINE = EN_TEXT.title_pipeline
TITLE_PAPER_OPERATION_CHECKS = EN_TEXT.title_paper_operation_checks
TITLE_PROVIDER_DIAGNOSTICS = EN_TEXT.title_provider_diagnostics
TITLE_PROVIDER_SOURCE_LADDER = EN_TEXT.title_provider_source_ladder
TITLE_DAILY_RISK_REPORT = EN_TEXT.title_daily_risk_report
TITLE_DESK_ACCOUNTING_CONTEXT = EN_TEXT.title_desk_accounting_context
TITLE_ENVIRONMENT_CHECK = EN_TEXT.title_environment_check
TITLE_EXIT = EN_TEXT.title_exit
TITLE_FINANCE_LEDGER_CATEGORIES = EN_TEXT.title_finance_ledger_categories
TITLE_FINANCE_OPERATIONS = EN_TEXT.title_finance_operations
TITLE_FINANCE_OPERATIONS_CHECKS = EN_TEXT.title_finance_operations_checks
TITLE_MANAGER_CONFLICTS = EN_TEXT.title_manager_conflicts
TITLE_MANAGER_CONFLICT_REPLAY = EN_TEXT.title_manager_conflict_replay
TITLE_MANAGER_OVERRIDE_NOTES = EN_TEXT.title_manager_override_notes
TITLE_MEMORY_AWARE_REPLAY = EN_TEXT.title_memory_aware_replay
TITLE_MEMORY_EXPLORER = EN_TEXT.title_memory_explorer
TITLE_MODEL_PULL = EN_TEXT.title_model_pull
TITLE_MODEL_SERVICE_STDERR_TAIL = EN_TEXT.title_model_service_stderr_tail
TITLE_MODEL_SERVICE_START_FAILED = EN_TEXT.title_model_service_start_failed
TITLE_RECENT_RUNS = EN_TEXT.title_recent_runs
TITLE_RISK_WARNINGS = EN_TEXT.title_risk_warnings
TITLE_REVIEW_NOTE = EN_TEXT.title_review_note
TITLE_REPLAY_STAGES = EN_TEXT.title_replay_stages
TITLE_RUN_ARTIFACTS = EN_TEXT.title_run_artifacts
TITLE_RUN_REVIEW = EN_TEXT.title_run_review
TITLE_RUN_BLOCKED = EN_TEXT.title_run_blocked
TITLE_RECONCILIATION_BLOCKED = EN_TEXT.title_reconciliation_blocked
TITLE_REFRESH_BLOCKED = EN_TEXT.title_refresh_blocked
TITLE_REJECTION_BLOCKED = EN_TEXT.title_rejection_blocked
TITLE_RUNTIME_EVENTS = EN_TEXT.title_runtime_events
TITLE_RUNTIME_GATE_OPEN = EN_TEXT.title_runtime_gate_open
TITLE_LAUNCH_PLAN = EN_TEXT.title_launch_plan
TITLE_RUNTIME_MODE = EN_TEXT.title_runtime_mode
TITLE_RUNTIME_MODE_TRANSITION_CHECKLIST = (
    EN_TEXT.title_runtime_mode_transition_checklist
)
TITLE_RUNTIME_STATUS = EN_TEXT.title_runtime_status
TITLE_SERVICE_STATUS = EN_TEXT.title_service_status
TITLE_SERVICE_STDERR_TAIL = EN_TEXT.title_service_stderr_tail
TITLE_SERVICE_STDOUT_TAIL = EN_TEXT.title_service_stdout_tail
TITLE_SERVICE_SUPERVISOR = EN_TEXT.title_service_supervisor
TITLE_TRADE_JOURNAL = EN_TEXT.title_trade_journal
TITLE_TRADE_PROPOSALS = EN_TEXT.title_trade_proposals
TITLE_PROPOSAL_CANDIDATES = EN_TEXT.title_proposal_candidates
TITLE_POSITION_PLAN_REPAIR = EN_TEXT.title_position_plan_repair
TITLE_PORTFOLIO = EN_TEXT.title_portfolio
TITLE_POSITIONS = EN_TEXT.title_positions
TITLE_PROPOSAL_REJECTED = EN_TEXT.title_proposal_rejected
TITLE_PROMOTION_BLOCKED = EN_TEXT.title_promotion_blocked
TITLE_PROPOSAL_CANDIDATE_CREATED = EN_TEXT.title_proposal_candidate_created
TITLE_PROPOSAL_CANDIDATE_PROMOTED = EN_TEXT.title_proposal_candidate_promoted
TITLE_RECOMMENDED_NEXT_COMMANDS = EN_TEXT.title_recommended_next_commands
TITLE_RECOMMENDED_COMMANDS = EN_TEXT.title_recommended_commands
TITLE_RESEARCH_CREWAI_FLOW_SETUP = EN_TEXT.title_research_crewai_flow_setup
TITLE_RESEARCH_CYCLE_CONTROL = EN_TEXT.title_research_cycle_control
TITLE_RESEARCH_SIDECAR_STATUS = EN_TEXT.title_research_sidecar_status
TITLE_RESEARCH_SOURCE_HEALTH = EN_TEXT.title_research_source_health
TITLE_RESEARCH_SNAPSHOT_PERSISTED = EN_TEXT.title_research_snapshot_persisted
TITLE_SETUP_GUIDANCE = EN_TEXT.title_setup_guidance
TITLE_SETUP_STATUS = EN_TEXT.title_setup_status
TITLE_TRACE = EN_TEXT.title_trace
TITLE_TOOL_OWNERSHIP = EN_TEXT.title_tool_ownership
TITLE_TRADE_PROPOSAL_APPROVED = EN_TEXT.title_trade_proposal_approved
TITLE_TRADE_PROPOSAL_CREATED = EN_TEXT.title_trade_proposal_created
TITLE_TRADE_PROPOSAL_RECONCILED = EN_TEXT.title_trade_proposal_reconciled
TITLE_TRADE_PROPOSAL_REFRESHED = EN_TEXT.title_trade_proposal_refreshed
TITLE_TRADE_PROPOSAL_REJECTED = EN_TEXT.title_trade_proposal_rejected
TITLE_TOOL_READINESS = EN_TEXT.title_tool_readiness
TITLE_TRAINING_DIAGNOSTIC_MODE = EN_TEXT.title_training_diagnostic_mode
TITLE_UI_LOCALE = EN_TEXT.title_ui_locale
TITLE_V1_READINESS = EN_TEXT.title_v1_readiness
TITLE_WARNING = EN_TEXT.title_warning
TITLE_WALK_FORWARD_BACKTEST = EN_TEXT.title_walk_forward_backtest
TITLE_WEB_GUI_SERVICE = EN_TEXT.title_web_gui_service
TITLE_WEB_GUI_START_FAILED = EN_TEXT.title_web_gui_start_failed
TITLE_WEB_GUI_STDERR_TAIL = EN_TEXT.title_web_gui_stderr_tail

PROMPT_CONTINUE = EN_TEXT.prompt_continue
PROMPT_SELECT_ACTION = EN_TEXT.prompt_select_action

STYLE_KEY_COLUMN = EN_TEXT.style_key_column
STATUS_ACTIVE = EN_TEXT.status_active
STATUS_APP_OWNED = EN_TEXT.status_app_owned
STATUS_AVAILABLE = EN_TEXT.status_available
STATUS_EXTERNAL = EN_TEXT.status_external
STATUS_FAIL = EN_TEXT.status_fail
STATUS_NEEDS_ATTENTION = EN_TEXT.status_needs_attention
STATUS_PASS = EN_TEXT.status_pass
STATUS_READY = EN_TEXT.status_ready

DB_LOCKED_MSG = EN_TEXT.db_locked_msg

LAUNCHER_OPTION_OPEN_WEB_GUI = EN_TEXT.launcher_option_open_web_gui
LAUNCHER_OPTION_CONTINUE_TUI = EN_TEXT.launcher_option_continue_tui
LAUNCHER_OPTION_REFRESH = EN_TEXT.launcher_option_refresh
LAUNCHER_OPTION_EXIT = EN_TEXT.launcher_option_exit
