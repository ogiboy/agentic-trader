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
    help_lookback: str
    help_model_service_app: str
    help_run_id: str
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
    help_webgui_service_app: str
    label_agent: str
    label_allowed: str
    label_approved: str
    label_baseline: str
    label_base_url: str
    label_bias: str
    label_blocking: str
    label_category: str
    label_cash: str
    label_check: str
    label_closed_trades: str
    label_continuous: str
    label_confidence: str
    label_context: str
    label_created: str
    label_currency: str
    label_current: str
    label_current_symbol: str
    label_cycle: str
    label_cycle_count: str
    label_cycles: str
    label_database: str
    label_db_status: str
    label_daily_realized_pnl: str
    label_decision: str
    label_decision_path: str
    label_details: str
    label_delta: str
    label_drawdown_from_peak: str
    label_ending_equity: str
    label_entry: str
    label_entry_px: str
    label_equity: str
    label_exposure: str
    label_exit: str
    label_exit_px: str
    label_expectancy: str
    label_fallback: str
    label_fallback_cycles: str
    label_fees: str
    label_field: str
    label_fills_today: str
    label_final_rationale: str
    label_final_side: str
    label_generated: str
    label_gross_exposure: str
    label_heartbeat: str
    label_heartbeat_age: str
    label_id: str
    label_interval: str
    label_environment: str
    label_key: str
    label_last_recorded_error: str
    label_last_recorded_message: str
    label_last_recorded_state: str
    label_largest_position: str
    label_level: str
    label_latest_order: str
    label_llm_provider: str
    label_live_process: str
    label_llm: str
    label_locale: str
    label_lookback: str
    label_market_value: str
    label_mark_source: str
    label_mark_status: str
    label_marked_at: str
    label_marks_recorded: str
    label_max_drawdown: str
    label_max_cycles: str
    label_memories: str
    label_message: str
    label_metric: str
    label_mode: str
    label_model: str
    label_model_available: str
    label_model_routing: str
    label_multi_timeframe: str
    label_no: str
    label_notes: str
    label_observer_mode: str
    label_open_positions: str
    label_opened: str
    label_order_id: str
    label_ollama_reachable: str
    label_output: str
    label_output_preview: str
    label_pid: str
    label_passed: str
    label_persisted: str
    label_pnl: str
    label_poll_seconds: str
    label_preset: str
    label_preference_update: str
    label_proposal: str
    label_rationale: str
    label_realized_pnl: str
    label_ref: str
    label_rejection_evidence: str
    label_reason: str
    label_resolution_notes: str
    label_requires_confirmation: str
    label_return: str
    label_runtime: str
    label_runtime_dir: str
    label_role: str
    label_service: str
    label_side: str
    label_source: str
    label_specialist: str
    label_signal: str
    label_size: str
    label_score: str
    label_slippage: str
    label_stage: str
    label_started: str
    label_status: str
    label_status_note: str
    label_strategy: str
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
    label_tools: str
    label_total_return: str
    label_trades: str
    label_type: str
    label_purpose: str
    label_update_preferences: str
    label_updated: str
    label_unrealized_pnl: str
    label_value: str
    label_warmup_bars: str
    label_with_memory: str
    label_warnings: str
    label_win_rate: str
    label_without_memory: str
    label_v1_source: str
    label_yes: str
    list_separator: str
    message_all_agent_stages_llm_path: str
    message_fallback_used_in: str
    message_no_elevated_portfolio_risk_warnings: str
    message_no_runtime_state: str
    message_no_runtime_events: str
    message_no_trade_journal_entries: str
    message_no_historical_memories: str
    message_no_proposal_candidates: str
    message_no_trade_proposals: str
    message_finance_operations_unavailable: str
    message_gross_exposure_above_equity: str
    message_largest_position_above_equity: str
    message_mark_time_unavailable: str
    message_open_position_count_elevated: str
    message_portfolio_concentration_hhi: str
    message_position_plan_repair_unavailable: str
    message_runtime_mode_transition_allowed: str
    message_runtime_mode_transition_blocked: str
    message_trading_runtime_blocked: str
    message_trading_runtime_ready: str
    message_training_diagnostic_fallback: str
    prompt_continue: str
    prompt_select_action: str
    stage_coordinator: str
    stage_consensus: str
    stage_execution: str
    stage_fundamental: str
    stage_manager: str
    stage_regime: str
    stage_risk: str
    stage_strategy: str
    style_key_column: str
    title_execution_summary: str
    title_agent_decisions: str
    title_agent_trace: str
    title_backtest_comparison: str
    title_backtest_memory_ablation: str
    title_backtest_trades: str
    title_llm_status: str
    title_operator_instruction: str
    title_pipeline: str
    title_daily_risk_report: str
    title_desk_accounting_context: str
    title_environment_check: str
    title_finance_ledger_categories: str
    title_finance_operations: str
    title_finance_operations_checks: str
    title_manager_conflicts: str
    title_manager_conflict_replay: str
    title_manager_override_notes: str
    title_memory_aware_replay: str
    title_memory_explorer: str
    title_recent_runs: str
    title_risk_warnings: str
    title_review_note: str
    title_replay_stages: str
    title_run_artifacts: str
    title_run_review: str
    title_runtime_events: str
    title_runtime_mode: str
    title_runtime_mode_transition_checklist: str
    title_runtime_status: str
    title_service_status: str
    title_trade_journal: str
    title_trade_proposals: str
    title_proposal_candidates: str
    title_position_plan_repair: str
    title_trace: str
    title_training_diagnostic_mode: str
    title_ui_locale: str
    title_warning: str
    title_walk_forward_backtest: str


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
    help_lookback="Lookback window accepted by yfinance",
    help_model_service_app="Manage the optional app-owned local model service.",
    help_run_id="Run id to inspect. Defaults to the latest recorded run.",
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
    help_webgui_service_app="Manage the optional app-owned local Web GUI service.",
    label_agent="Agent",
    label_allowed="Allowed",
    label_approved="Approved",
    label_baseline="Baseline",
    label_base_url="Base URL",
    label_bias="Bias",
    label_blocking="Blocking",
    label_category="Category",
    label_cash="Cash",
    label_check="Check",
    label_closed_trades="Closed Trades",
    label_continuous="Continuous",
    label_confidence="Confidence",
    label_context="Context",
    label_created="Created",
    label_currency="Currency",
    label_current="Current",
    label_current_symbol="Current Symbol",
    label_cycle="Cycle",
    label_cycle_count="Cycle Count",
    label_cycles="Cycles",
    label_database="Database",
    label_db_status="DB Status",
    label_daily_realized_pnl="Daily Realized PnL",
    label_decision="Decision",
    label_decision_path="Decision Path",
    label_details="Details",
    label_delta="Delta",
    label_drawdown_from_peak="Drawdown From Peak",
    label_ending_equity="Ending Equity",
    label_entry="Entry",
    label_entry_px="Entry Px",
    label_equity="Equity",
    label_exposure="Exposure",
    label_exit="Exit",
    label_exit_px="Exit Px",
    label_expectancy="Expectancy",
    label_fallback="Fallback",
    label_fallback_cycles="Fallback Cycles",
    label_fees="Fees",
    label_field="Field",
    label_fills_today="Fills Today",
    label_final_rationale="Final Rationale",
    label_final_side="Final Side",
    label_generated="Generated",
    label_gross_exposure="Gross Exposure",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Age",
    label_id="ID",
    label_interval="Interval",
    label_environment="Environment",
    label_key="Key",
    label_last_recorded_error="Last Recorded Error",
    label_last_recorded_message="Last Recorded Message",
    label_last_recorded_state="Last Recorded State",
    label_largest_position="Largest Position",
    label_level="Level",
    label_latest_order="Latest Order",
    label_llm_provider="LLM Provider",
    label_live_process="Live Process",
    label_llm="LLM",
    label_locale="Locale",
    label_lookback="Lookback",
    label_market_value="Market Value",
    label_mark_source="Mark Source",
    label_mark_status="Mark Status",
    label_marked_at="Marked At",
    label_marks_recorded="Marks Recorded",
    label_max_drawdown="Max Drawdown",
    label_max_cycles="Max Cycles",
    label_memories="Memories",
    label_message="Message",
    label_metric="Metric",
    label_mode="Mode",
    label_model="Model",
    label_model_available="Model Available",
    label_model_routing="Model Routing",
    label_multi_timeframe="Multi-Timeframe",
    label_no="no",
    label_notes="Notes",
    label_observer_mode="Observer Mode",
    label_open_positions="Open Positions",
    label_opened="Opened",
    label_order_id="Order ID",
    label_ollama_reachable="Ollama Reachable",
    label_output="Output",
    label_output_preview="Output Preview",
    label_pid="PID",
    label_passed="Passed",
    label_persisted="Persisted",
    label_pnl="PnL",
    label_poll_seconds="Poll Seconds",
    label_preset="Preset",
    label_preference_update="Preference Update",
    label_proposal="Proposal",
    label_rationale="Rationale",
    label_realized_pnl="Realized PnL",
    label_ref="Ref",
    label_rejection_evidence="Rejection Evidence",
    label_reason="Reason",
    label_resolution_notes="Resolution Notes",
    label_requires_confirmation="Requires Confirmation",
    label_return="Return",
    label_runtime="Runtime",
    label_runtime_dir="Runtime Dir",
    label_role="Role",
    label_service="Service",
    label_side="Side",
    label_source="Source",
    label_specialist="Specialist",
    label_signal="Signal",
    label_size="Size",
    label_score="Score",
    label_slippage="Slippage",
    label_stage="Stage",
    label_started="Started",
    label_status="Status",
    label_status_note="Status Note",
    label_strategy="Strategy",
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
    label_tools="Tools",
    label_total_return="Total Return",
    label_trades="Trades",
    label_type="Type",
    label_purpose="Purpose",
    label_update_preferences="Update Preferences",
    label_updated="Updated",
    label_unrealized_pnl="Unrealized PnL",
    label_value="Value",
    label_warmup_bars="Warmup Bars",
    label_with_memory="With Memory",
    label_warnings="Warnings",
    label_win_rate="Win Rate",
    label_without_memory="Without Memory",
    label_v1_source="V1 Source",
    label_yes="yes",
    list_separator=", ",
    message_all_agent_stages_llm_path="All agent stages completed through the LLM path.",
    message_fallback_used_in="Fallback was used in",
    message_no_elevated_portfolio_risk_warnings=(
        "No elevated portfolio risk warnings for this report."
    ),
    message_no_runtime_state="No runtime state recorded yet.",
    message_no_runtime_events="No runtime events recorded yet.",
    message_no_trade_journal_entries="No trade journal entries recorded yet.",
    message_no_historical_memories="No historical memories are available yet.",
    message_no_proposal_candidates="No proposal candidates recorded yet.",
    message_no_trade_proposals="No trade proposals recorded yet.",
    message_finance_operations_unavailable="Finance operations status unavailable.",
    message_gross_exposure_above_equity="Gross exposure is above {limit} of equity.",
    message_largest_position_above_equity="Largest position is above {limit} of equity.",
    message_mark_time_unavailable="mark time unavailable",
    message_open_position_count_elevated="Open position count is elevated.",
    message_portfolio_concentration_hhi=(
        "Portfolio concentration HHI is elevated at {score:.3f}."
    ),
    message_position_plan_repair_unavailable="Position plan repair status unavailable.",
    message_runtime_mode_transition_allowed=(
        "Runtime mode transition {current_mode} -> {target_mode} is allowed."
    ),
    message_runtime_mode_transition_blocked=(
        "Runtime mode transition {current_mode} -> {target_mode} is blocked."
    ),
    message_trading_runtime_blocked=(
        "Trading runtime should not start until Ollama and the configured model are available."
    ),
    message_trading_runtime_ready="Trading runtime can start with full LLM access.",
    message_training_diagnostic_fallback=(
        "Training mode is continuing this evaluation with deterministic diagnostic "
        "fallbacks because the LLM gate failed:\n\n{error}"
    ),
    prompt_continue="Press Enter to continue",
    prompt_select_action="Select action",
    stage_coordinator="Coordinator",
    stage_consensus="Consensus",
    stage_execution="Execution",
    stage_fundamental="Fundamental",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column="bold cyan",
    title_agent_decisions="Agent Decisions",
    title_agent_trace="Agent Trace",
    title_backtest_comparison="Backtest Comparison",
    title_backtest_memory_ablation="Backtest Memory Ablation",
    title_backtest_trades="Backtest Trades",
    title_execution_summary="Execution Summary",
    title_llm_status="LLM Status",
    title_operator_instruction="Operator Instruction",
    title_pipeline="Pipeline",
    title_daily_risk_report="Daily Risk Report",
    title_desk_accounting_context="Desk Accounting Context",
    title_environment_check="Environment Check",
    title_finance_ledger_categories="Finance Ledger Categories",
    title_finance_operations="Finance Operations",
    title_finance_operations_checks="Finance Operations Checks",
    title_manager_conflicts="Manager Conflicts",
    title_manager_conflict_replay="Manager Conflict Replay",
    title_manager_override_notes="Manager Override Notes",
    title_memory_aware_replay="Memory-Aware Replay",
    title_memory_explorer="Memory Explorer",
    title_recent_runs="Recent Runs",
    title_risk_warnings="Risk Warnings",
    title_review_note="Review Note",
    title_replay_stages="Replay Stages",
    title_run_artifacts="Run Artifacts",
    title_run_review="Run Review",
    title_runtime_events="Runtime Events",
    title_runtime_mode="Runtime Mode",
    title_runtime_mode_transition_checklist="Runtime Mode Transition Checklist",
    title_runtime_status="Runtime Status",
    title_service_status="Service Status",
    title_trade_journal="Trade Journal",
    title_trade_proposals="Trade Proposals",
    title_proposal_candidates="Proposal Candidates",
    title_position_plan_repair="Position Plan Repair",
    title_trace="Trace",
    title_training_diagnostic_mode="Training Diagnostic Mode",
    title_ui_locale="UI Locale",
    title_warning="Warning",
    title_walk_forward_backtest="Walk-Forward Backtest",
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
    help_lookback="yfinance tarafindan kabul edilen geriye donuk pencere",
    help_model_service_app="Istege bagli app-owned yerel model servisini yonet.",
    help_run_id="Incelenecek run id. Varsayilan son kayitli run.",
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
    help_webgui_service_app="Istege bagli app-owned yerel Web GUI servisini yonet.",
    label_agent="Agent",
    label_allowed="Izinli",
    label_approved="Onaylandi",
    label_baseline="Baseline",
    label_base_url="Base URL",
    label_bias="Bias",
    label_blocking="Bloklayici",
    label_category="Kategori",
    label_cash="Nakit",
    label_check="Kontrol",
    label_closed_trades="Kapanan Trade'ler",
    label_continuous="Surekli",
    label_confidence="Guven",
    label_context="Baglam",
    label_created="Olusturuldu",
    label_currency="Para Birimi",
    label_current="Gecerli",
    label_current_symbol="Gecerli Sembol",
    label_cycle="Dongu",
    label_cycle_count="Dongu Sayisi",
    label_cycles="Donguler",
    label_database="Veritabani",
    label_db_status="DB Durumu",
    label_daily_realized_pnl="Gunluk Gerceklesen PnL",
    label_decision="Karar",
    label_decision_path="Karar Yolu",
    label_details="Detaylar",
    label_delta="Delta",
    label_drawdown_from_peak="Zirveden Drawdown",
    label_ending_equity="Final Equity",
    label_entry="Giris",
    label_entry_px="Giris Fiyati",
    label_equity="Equity",
    label_exposure="Exposure",
    label_exit="Cikis",
    label_exit_px="Cikis Fiyati",
    label_expectancy="Expectancy",
    label_fallback="Fallback",
    label_fallback_cycles="Fallback Donguleri",
    label_fees="Ucretler",
    label_field="Alan",
    label_fills_today="Bugunku Fill'ler",
    label_final_rationale="Final Gerekce",
    label_final_side="Final Yon",
    label_generated="Uretildi",
    label_gross_exposure="Brut Exposure",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Yasi",
    label_id="ID",
    label_interval="Aralik",
    label_environment="Ortam",
    label_key="Anahtar",
    label_last_recorded_error="Son Kayitli Hata",
    label_last_recorded_message="Son Kayitli Mesaj",
    label_last_recorded_state="Son Kayitli Durum",
    label_largest_position="En Buyuk Pozisyon",
    label_level="Seviye",
    label_latest_order="Son Order",
    label_llm_provider="LLM Provider",
    label_live_process="Canli Process",
    label_llm="LLM",
    label_locale="Locale",
    label_lookback="Geriye Donuk Pencere",
    label_market_value="Piyasa Degeri",
    label_mark_source="Mark Kaynagi",
    label_mark_status="Mark Durumu",
    label_marked_at="Mark Zamani",
    label_marks_recorded="Kayitli Mark'lar",
    label_max_drawdown="Maksimum Drawdown",
    label_max_cycles="Maksimum Dongu",
    label_memories="Hafizalar",
    label_message="Mesaj",
    label_metric="Metrik",
    label_mode="Mod",
    label_model="Model",
    label_model_available="Model Kullanilabilir",
    label_model_routing="Model Routing",
    label_multi_timeframe="Multi-Timeframe",
    label_no="hayir",
    label_notes="Notlar",
    label_observer_mode="Observer Modu",
    label_open_positions="Acik Pozisyonlar",
    label_opened="Acilis",
    label_order_id="Order ID",
    label_ollama_reachable="Ollama Erisilebilir",
    label_output="Cikti",
    label_output_preview="Cikti Onizleme",
    label_pid="PID",
    label_passed="Gecti",
    label_persisted="Kalici",
    label_pnl="PnL",
    label_poll_seconds="Poll Saniyesi",
    label_preset="Preset",
    label_preference_update="Preference Guncellemesi",
    label_proposal="Proposal",
    label_rationale="Gerekce",
    label_realized_pnl="Gerceklesen PnL",
    label_ref="Ref",
    label_rejection_evidence="Red Kaniti",
    label_reason="Neden",
    label_resolution_notes="Cozum Notlari",
    label_requires_confirmation="Onay Gerektirir",
    label_return="Return",
    label_runtime="Runtime",
    label_runtime_dir="Runtime Dir",
    label_role="Rol",
    label_service="Servis",
    label_side="Yon",
    label_source="Kaynak",
    label_specialist="Specialist",
    label_signal="Sinyal",
    label_size="Boyut",
    label_score="Skor",
    label_slippage="Slippage",
    label_stage="Asama",
    label_started="Basladi",
    label_status="Durum",
    label_status_note="Durum Notu",
    label_strategy="Strateji",
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
    label_tools="Araclar",
    label_total_return="Toplam Return",
    label_trades="Trade'ler",
    label_type="Tip",
    label_purpose="Amac",
    label_update_preferences="Tercihleri Guncelle",
    label_updated="Guncellendi",
    label_unrealized_pnl="Gerceklesmemis PnL",
    label_value="Deger",
    label_warmup_bars="Warmup Bar'lari",
    label_with_memory="Hafiza Ile",
    label_warnings="Uyarilar",
    label_win_rate="Kazanma Orani",
    label_without_memory="Hafiza Olmadan",
    label_v1_source="V1 Kaynagi",
    label_yes="evet",
    list_separator=", ",
    message_all_agent_stages_llm_path="Tum agent asamalari LLM yolu ile tamamlandi.",
    message_fallback_used_in="Fallback kullanilan asamalar",
    message_no_elevated_portfolio_risk_warnings=(
        "Bu rapor icin yuksek portfoy risk uyarisi yok."
    ),
    message_no_runtime_state="Henuz runtime durumu kaydedilmedi.",
    message_no_runtime_events="Henuz runtime olayi kaydedilmedi.",
    message_no_trade_journal_entries="Henuz trade journal kaydi yok.",
    message_no_historical_memories="Henuz historical memory yok.",
    message_no_proposal_candidates="Henuz proposal candidate kaydi yok.",
    message_no_trade_proposals="Henuz trade proposal kaydi yok.",
    message_finance_operations_unavailable="Finance operations durumu kullanilamiyor.",
    message_gross_exposure_above_equity="Gross exposure equity'nin {limit} uzerinde.",
    message_largest_position_above_equity="En buyuk pozisyon equity'nin {limit} uzerinde.",
    message_mark_time_unavailable="mark zamani yok",
    message_open_position_count_elevated="Acik pozisyon sayisi yuksek.",
    message_portfolio_concentration_hhi=(
        "Portfoy konsantrasyon HHI {score:.3f} ile yuksek."
    ),
    message_position_plan_repair_unavailable="Position plan repair durumu kullanilamiyor.",
    message_runtime_mode_transition_allowed=(
        "Runtime mode gecisi {current_mode} -> {target_mode} izinli."
    ),
    message_runtime_mode_transition_blocked=(
        "Runtime mode gecisi {current_mode} -> {target_mode} bloklandi."
    ),
    message_trading_runtime_blocked=(
        "Ollama ve configured model kullanilabilir olana kadar trading runtime baslamamali."
    ),
    message_trading_runtime_ready="Trading runtime tam LLM erisimiyle baslayabilir.",
    message_training_diagnostic_fallback=(
        "Training modu bu degerlendirmeye deterministic diagnostic fallback ile "
        "devam ediyor cunku LLM gate basarisiz oldu:\n\n{error}"
    ),
    prompt_continue="Devam etmek icin Enter'a basin",
    prompt_select_action="Aksiyon sec",
    stage_coordinator="Coordinator",
    stage_consensus="Consensus",
    stage_execution="Execution",
    stage_fundamental="Fundamental",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column=EN_TEXT.style_key_column,
    title_agent_decisions="Agent Kararlari",
    title_agent_trace="Agent Trace",
    title_backtest_comparison="Backtest Karsilastirma",
    title_backtest_memory_ablation="Backtest Memory Ablation",
    title_backtest_trades="Backtest Trade'leri",
    title_execution_summary="Execution Ozeti",
    title_llm_status="LLM Durumu",
    title_operator_instruction="Operator Talimati",
    title_pipeline="Pipeline",
    title_daily_risk_report="Gunluk Risk Raporu",
    title_desk_accounting_context="Desk Accounting Context",
    title_environment_check="Environment Check",
    title_finance_ledger_categories="Finance Ledger Kategorileri",
    title_finance_operations="Finance Operations",
    title_finance_operations_checks="Finance Operations Kontrolleri",
    title_manager_conflicts="Manager Catismalari",
    title_manager_conflict_replay="Manager Catisma Replay",
    title_manager_override_notes="Manager Override Notlari",
    title_memory_aware_replay="Memory-Aware Replay",
    title_memory_explorer="Memory Explorer",
    title_recent_runs="Son Run'lar",
    title_risk_warnings="Risk Uyarilari",
    title_review_note="Review Notu",
    title_replay_stages="Replay Asamalari",
    title_run_artifacts="Run Artifact'lari",
    title_run_review="Run Review",
    title_runtime_events="Runtime Olaylari",
    title_runtime_mode="Runtime Modu",
    title_runtime_mode_transition_checklist="Runtime Mode Gecis Kontrol Listesi",
    title_runtime_status="Runtime Durumu",
    title_service_status="Servis Durumu",
    title_trade_journal="Trade Journal",
    title_trade_proposals="Trade Proposal'lari",
    title_proposal_candidates="Proposal Candidate'leri",
    title_position_plan_repair="Position Plan Repair",
    title_trace="Trace",
    title_training_diagnostic_mode="Training Diagnostic Mode",
    title_ui_locale="UI Locale",
    title_warning="Uyari",
    title_walk_forward_backtest="Walk-Forward Backtest",
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
HELP_SYMBOL = EN_TEXT.help_symbol
HELP_INTERVAL = EN_TEXT.help_interval
HELP_LOOKBACK = EN_TEXT.help_lookback
HELP_RUN_ID = EN_TEXT.help_run_id
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

LABEL_AGENT = EN_TEXT.label_agent
LABEL_ALLOWED = EN_TEXT.label_allowed
LABEL_APPROVED = EN_TEXT.label_approved
LABEL_BASELINE = EN_TEXT.label_baseline
LABEL_BASE_URL = EN_TEXT.label_base_url
LABEL_BIAS = EN_TEXT.label_bias
LABEL_BLOCKING = EN_TEXT.label_blocking
LABEL_CATEGORY = EN_TEXT.label_category
LABEL_CASH = EN_TEXT.label_cash
LABEL_CHECK = EN_TEXT.label_check
LABEL_CLOSED_TRADES = EN_TEXT.label_closed_trades
LABEL_CONTINUOUS = EN_TEXT.label_continuous
LABEL_CONFIDENCE = EN_TEXT.label_confidence
LABEL_CONTEXT = EN_TEXT.label_context
LABEL_CREATED = EN_TEXT.label_created
LABEL_CURRENCY = EN_TEXT.label_currency
LABEL_CURRENT = EN_TEXT.label_current
LABEL_CURRENT_SYMBOL = EN_TEXT.label_current_symbol
LABEL_CYCLE = EN_TEXT.label_cycle
LABEL_CYCLE_COUNT = EN_TEXT.label_cycle_count
LABEL_CYCLES = EN_TEXT.label_cycles
LABEL_DATABASE = EN_TEXT.label_database
LABEL_DB_STATUS = EN_TEXT.label_db_status
LABEL_DAILY_REALIZED_PNL = EN_TEXT.label_daily_realized_pnl
LABEL_DECISION = EN_TEXT.label_decision
LABEL_DECISION_PATH = EN_TEXT.label_decision_path
LABEL_DETAILS = EN_TEXT.label_details
LABEL_DELTA = EN_TEXT.label_delta
LABEL_DRAWDOWN_FROM_PEAK = EN_TEXT.label_drawdown_from_peak
LABEL_ENDING_EQUITY = EN_TEXT.label_ending_equity
LABEL_ENTRY = EN_TEXT.label_entry
LABEL_ENTRY_PX = EN_TEXT.label_entry_px
LABEL_EQUITY = EN_TEXT.label_equity
LABEL_EXPOSURE = EN_TEXT.label_exposure
LABEL_EXIT = EN_TEXT.label_exit
LABEL_EXIT_PX = EN_TEXT.label_exit_px
LABEL_EXPECTANCY = EN_TEXT.label_expectancy
LABEL_FALLBACK = EN_TEXT.label_fallback
LABEL_FALLBACK_CYCLES = EN_TEXT.label_fallback_cycles
LABEL_FEES = EN_TEXT.label_fees
LABEL_FIELD = EN_TEXT.label_field
LABEL_FILLS_TODAY = EN_TEXT.label_fills_today
LABEL_FINAL_RATIONALE = EN_TEXT.label_final_rationale
LABEL_FINAL_SIDE = EN_TEXT.label_final_side
LABEL_GENERATED = EN_TEXT.label_generated
LABEL_GROSS_EXPOSURE = EN_TEXT.label_gross_exposure
LABEL_HEARTBEAT = EN_TEXT.label_heartbeat
LABEL_HEARTBEAT_AGE = EN_TEXT.label_heartbeat_age
LABEL_ID = EN_TEXT.label_id
LABEL_INTERVAL = EN_TEXT.label_interval
LABEL_ENVIRONMENT = EN_TEXT.label_environment
LABEL_KEY = EN_TEXT.label_key
LABEL_LAST_RECORDED_ERROR = EN_TEXT.label_last_recorded_error
LABEL_LAST_RECORDED_MESSAGE = EN_TEXT.label_last_recorded_message
LABEL_LAST_RECORDED_STATE = EN_TEXT.label_last_recorded_state
LABEL_LARGEST_POSITION = EN_TEXT.label_largest_position
LABEL_LEVEL = EN_TEXT.label_level
LABEL_LATEST_ORDER = EN_TEXT.label_latest_order
LABEL_LLM_PROVIDER = EN_TEXT.label_llm_provider
LABEL_LIVE_PROCESS = EN_TEXT.label_live_process
LABEL_LLM = EN_TEXT.label_llm
LABEL_LOCALE = EN_TEXT.label_locale
LABEL_LOOKBACK = EN_TEXT.label_lookback
LABEL_MARKET_VALUE = EN_TEXT.label_market_value
LABEL_MARK_SOURCE = EN_TEXT.label_mark_source
LABEL_MARK_STATUS = EN_TEXT.label_mark_status
LABEL_MARKED_AT = EN_TEXT.label_marked_at
LABEL_MARKS_RECORDED = EN_TEXT.label_marks_recorded
LABEL_MAX_DRAWDOWN = EN_TEXT.label_max_drawdown
LABEL_MAX_CYCLES = EN_TEXT.label_max_cycles
LABEL_MEMORIES = EN_TEXT.label_memories
LABEL_MESSAGE = EN_TEXT.label_message
LABEL_METRIC = EN_TEXT.label_metric
LABEL_MODE = EN_TEXT.label_mode
LABEL_MODEL = EN_TEXT.label_model
LABEL_MODEL_AVAILABLE = EN_TEXT.label_model_available
LABEL_MODEL_ROUTING = EN_TEXT.label_model_routing
LABEL_MULTI_TIMEFRAME = EN_TEXT.label_multi_timeframe
LABEL_NO = EN_TEXT.label_no
LABEL_NOTES = EN_TEXT.label_notes
LABEL_OBSERVER_MODE = EN_TEXT.label_observer_mode
LABEL_OPEN_POSITIONS = EN_TEXT.label_open_positions
LABEL_OPENED = EN_TEXT.label_opened
LABEL_ORDER_ID = EN_TEXT.label_order_id
LABEL_OLLAMA_REACHABLE = EN_TEXT.label_ollama_reachable
LABEL_OUTPUT = EN_TEXT.label_output
LABEL_OUTPUT_PREVIEW = EN_TEXT.label_output_preview
LABEL_PASSED = EN_TEXT.label_passed
LABEL_PERSISTED = EN_TEXT.label_persisted
LABEL_PID = EN_TEXT.label_pid
LABEL_PNL = EN_TEXT.label_pnl
LABEL_POLL_SECONDS = EN_TEXT.label_poll_seconds
LABEL_PRESET = EN_TEXT.label_preset
LABEL_PREFERENCE_UPDATE = EN_TEXT.label_preference_update
LABEL_PROPOSAL = EN_TEXT.label_proposal
LABEL_RATIONALE = EN_TEXT.label_rationale
LABEL_REALIZED_PNL = EN_TEXT.label_realized_pnl
LABEL_REF = EN_TEXT.label_ref
LABEL_REJECTION_EVIDENCE = EN_TEXT.label_rejection_evidence
LABEL_REASON = EN_TEXT.label_reason
LABEL_RESOLUTION_NOTES = EN_TEXT.label_resolution_notes
LABEL_REQUIRES_CONFIRMATION = EN_TEXT.label_requires_confirmation
LABEL_RETURN = EN_TEXT.label_return
LABEL_RUNTIME = EN_TEXT.label_runtime
LABEL_RUNTIME_DIR = EN_TEXT.label_runtime_dir
LABEL_ROLE = EN_TEXT.label_role
LABEL_SERVICE = EN_TEXT.label_service
LABEL_SIDE = EN_TEXT.label_side
LABEL_SOURCE = EN_TEXT.label_source
LABEL_SPECIALIST = EN_TEXT.label_specialist
LABEL_SIGNAL = EN_TEXT.label_signal
LABEL_SIZE = EN_TEXT.label_size
LABEL_SCORE = EN_TEXT.label_score
LABEL_SLIPPAGE = EN_TEXT.label_slippage
LABEL_STAGE = EN_TEXT.label_stage
LABEL_STARTED = EN_TEXT.label_started
LABEL_STATUS = EN_TEXT.label_status
LABEL_STATUS_NOTE = EN_TEXT.label_status_note
LABEL_STRATEGY = EN_TEXT.label_strategy
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
LABEL_TOOLS = EN_TEXT.label_tools
LABEL_TOTAL_RETURN = EN_TEXT.label_total_return
LABEL_TRADES = EN_TEXT.label_trades
LABEL_TYPE = EN_TEXT.label_type
LABEL_PURPOSE = EN_TEXT.label_purpose
LABEL_UPDATE_PREFERENCES = EN_TEXT.label_update_preferences
LABEL_UPDATED = EN_TEXT.label_updated
LABEL_UNREALIZED_PNL = EN_TEXT.label_unrealized_pnl
LABEL_VALUE = EN_TEXT.label_value
LABEL_WARMUP_BARS = EN_TEXT.label_warmup_bars
LABEL_WITH_MEMORY = EN_TEXT.label_with_memory
LABEL_WARNINGS = EN_TEXT.label_warnings
LABEL_WIN_RATE = EN_TEXT.label_win_rate
LABEL_WITHOUT_MEMORY = EN_TEXT.label_without_memory
LABEL_V1_SOURCE = EN_TEXT.label_v1_source
LABEL_YES = EN_TEXT.label_yes
UI_LIST_SEPARATOR = EN_TEXT.list_separator

MESSAGE_ALL_AGENT_STAGES_LLM_PATH = EN_TEXT.message_all_agent_stages_llm_path
MESSAGE_FALLBACK_USED_IN = EN_TEXT.message_fallback_used_in
MESSAGE_NO_ELEVATED_PORTFOLIO_RISK_WARNINGS = (
    EN_TEXT.message_no_elevated_portfolio_risk_warnings
)
MESSAGE_NO_RUNTIME_STATE = EN_TEXT.message_no_runtime_state
MESSAGE_NO_RUNTIME_EVENTS = EN_TEXT.message_no_runtime_events
MESSAGE_NO_TRADE_JOURNAL_ENTRIES = EN_TEXT.message_no_trade_journal_entries
MESSAGE_NO_HISTORICAL_MEMORIES = EN_TEXT.message_no_historical_memories
MESSAGE_NO_PROPOSAL_CANDIDATES = EN_TEXT.message_no_proposal_candidates
MESSAGE_NO_TRADE_PROPOSALS = EN_TEXT.message_no_trade_proposals
MESSAGE_FINANCE_OPERATIONS_UNAVAILABLE = EN_TEXT.message_finance_operations_unavailable
MESSAGE_GROSS_EXPOSURE_ABOVE_EQUITY = EN_TEXT.message_gross_exposure_above_equity
MESSAGE_LARGEST_POSITION_ABOVE_EQUITY = EN_TEXT.message_largest_position_above_equity
MESSAGE_MARK_TIME_UNAVAILABLE = EN_TEXT.message_mark_time_unavailable
MESSAGE_OPEN_POSITION_COUNT_ELEVATED = EN_TEXT.message_open_position_count_elevated
MESSAGE_PORTFOLIO_CONCENTRATION_HHI = EN_TEXT.message_portfolio_concentration_hhi
MESSAGE_POSITION_PLAN_REPAIR_UNAVAILABLE = (
    EN_TEXT.message_position_plan_repair_unavailable
)
MESSAGE_RUNTIME_MODE_TRANSITION_ALLOWED = (
    EN_TEXT.message_runtime_mode_transition_allowed
)
MESSAGE_RUNTIME_MODE_TRANSITION_BLOCKED = (
    EN_TEXT.message_runtime_mode_transition_blocked
)
MESSAGE_TRADING_RUNTIME_BLOCKED = EN_TEXT.message_trading_runtime_blocked
MESSAGE_TRADING_RUNTIME_READY = EN_TEXT.message_trading_runtime_ready
MESSAGE_TRAINING_DIAGNOSTIC_FALLBACK = EN_TEXT.message_training_diagnostic_fallback

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
TITLE_BACKTEST_COMPARISON = EN_TEXT.title_backtest_comparison
TITLE_BACKTEST_MEMORY_ABLATION = EN_TEXT.title_backtest_memory_ablation
TITLE_BACKTEST_TRADES = EN_TEXT.title_backtest_trades
TITLE_EXECUTION_SUMMARY = EN_TEXT.title_execution_summary
TITLE_LLM_STATUS = EN_TEXT.title_llm_status
TITLE_OPERATOR_INSTRUCTION = EN_TEXT.title_operator_instruction
TITLE_PIPELINE = EN_TEXT.title_pipeline
TITLE_DAILY_RISK_REPORT = EN_TEXT.title_daily_risk_report
TITLE_DESK_ACCOUNTING_CONTEXT = EN_TEXT.title_desk_accounting_context
TITLE_ENVIRONMENT_CHECK = EN_TEXT.title_environment_check
TITLE_FINANCE_LEDGER_CATEGORIES = EN_TEXT.title_finance_ledger_categories
TITLE_FINANCE_OPERATIONS = EN_TEXT.title_finance_operations
TITLE_FINANCE_OPERATIONS_CHECKS = EN_TEXT.title_finance_operations_checks
TITLE_MANAGER_CONFLICTS = EN_TEXT.title_manager_conflicts
TITLE_MANAGER_CONFLICT_REPLAY = EN_TEXT.title_manager_conflict_replay
TITLE_MANAGER_OVERRIDE_NOTES = EN_TEXT.title_manager_override_notes
TITLE_MEMORY_AWARE_REPLAY = EN_TEXT.title_memory_aware_replay
TITLE_MEMORY_EXPLORER = EN_TEXT.title_memory_explorer
TITLE_RECENT_RUNS = EN_TEXT.title_recent_runs
TITLE_RISK_WARNINGS = EN_TEXT.title_risk_warnings
TITLE_REVIEW_NOTE = EN_TEXT.title_review_note
TITLE_REPLAY_STAGES = EN_TEXT.title_replay_stages
TITLE_RUN_ARTIFACTS = EN_TEXT.title_run_artifacts
TITLE_RUN_REVIEW = EN_TEXT.title_run_review
TITLE_RUNTIME_EVENTS = EN_TEXT.title_runtime_events
TITLE_RUNTIME_MODE = EN_TEXT.title_runtime_mode
TITLE_RUNTIME_MODE_TRANSITION_CHECKLIST = (
    EN_TEXT.title_runtime_mode_transition_checklist
)
TITLE_RUNTIME_STATUS = EN_TEXT.title_runtime_status
TITLE_SERVICE_STATUS = EN_TEXT.title_service_status
TITLE_TRADE_JOURNAL = EN_TEXT.title_trade_journal
TITLE_TRADE_PROPOSALS = EN_TEXT.title_trade_proposals
TITLE_PROPOSAL_CANDIDATES = EN_TEXT.title_proposal_candidates
TITLE_POSITION_PLAN_REPAIR = EN_TEXT.title_position_plan_repair
TITLE_TRACE = EN_TEXT.title_trace
TITLE_TRAINING_DIAGNOSTIC_MODE = EN_TEXT.title_training_diagnostic_mode
TITLE_UI_LOCALE = EN_TEXT.title_ui_locale
TITLE_WARNING = EN_TEXT.title_warning
TITLE_WALK_FORWARD_BACKTEST = EN_TEXT.title_walk_forward_backtest

PROMPT_CONTINUE = EN_TEXT.prompt_continue
PROMPT_SELECT_ACTION = EN_TEXT.prompt_select_action

STYLE_KEY_COLUMN = EN_TEXT.style_key_column

DB_LOCKED_MSG = EN_TEXT.db_locked_msg
