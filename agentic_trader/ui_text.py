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
    label_approved: str
    label_continuous: str
    label_confidence: str
    label_current_symbol: str
    label_cycle_count: str
    label_decision_path: str
    label_entry: str
    label_fallback: str
    label_field: str
    label_heartbeat: str
    label_heartbeat_age: str
    label_interval: str
    label_key: str
    label_last_recorded_error: str
    label_last_recorded_message: str
    label_last_recorded_state: str
    label_live_process: str
    label_llm: str
    label_lookback: str
    label_market_value: str
    label_max_cycles: str
    label_mode: str
    label_no: str
    label_notes: str
    label_observer_mode: str
    label_order_id: str
    label_pid: str
    label_poll_seconds: str
    label_preference_update: str
    label_rationale: str
    label_requires_confirmation: str
    label_runtime: str
    label_service: str
    label_side: str
    label_source: str
    label_stage: str
    label_started: str
    label_status_note: str
    label_stop_requested: str
    label_stop: str
    label_structured_llm: str
    label_summary: str
    label_symbols: str
    label_take_profit: str
    label_update_preferences: str
    label_updated: str
    label_unrealized_pnl: str
    label_value: str
    label_win_rate: str
    label_yes: str
    list_separator: str
    message_all_agent_stages_llm_path: str
    message_fallback_used_in: str
    message_no_runtime_state: str
    prompt_continue: str
    prompt_select_action: str
    stage_coordinator: str
    stage_manager: str
    stage_regime: str
    stage_risk: str
    stage_strategy: str
    style_key_column: str
    title_execution_summary: str
    title_llm_status: str
    title_operator_instruction: str
    title_pipeline: str
    title_recent_runs: str
    title_run_artifacts: str
    title_runtime_events: str
    title_runtime_status: str
    title_service_status: str
    title_warning: str


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
    label_approved="Approved",
    label_continuous="Continuous",
    label_confidence="Confidence",
    label_current_symbol="Current Symbol",
    label_cycle_count="Cycle Count",
    label_decision_path="Decision Path",
    label_entry="Entry",
    label_fallback="Fallback",
    label_field="Field",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Age",
    label_interval="Interval",
    label_key="Key",
    label_last_recorded_error="Last Recorded Error",
    label_last_recorded_message="Last Recorded Message",
    label_last_recorded_state="Last Recorded State",
    label_live_process="Live Process",
    label_llm="LLM",
    label_lookback="Lookback",
    label_market_value="Market Value",
    label_max_cycles="Max Cycles",
    label_mode="Mode",
    label_no="no",
    label_notes="Notes",
    label_observer_mode="Observer Mode",
    label_order_id="Order ID",
    label_pid="PID",
    label_poll_seconds="Poll Seconds",
    label_preference_update="Preference Update",
    label_rationale="Rationale",
    label_requires_confirmation="Requires Confirmation",
    label_runtime="Runtime",
    label_service="Service",
    label_side="Side",
    label_source="Source",
    label_stage="Stage",
    label_started="Started",
    label_status_note="Status Note",
    label_stop_requested="Stop Requested",
    label_stop="Stop",
    label_structured_llm="Structured LLM response",
    label_summary="Summary",
    label_symbols="Symbols",
    label_take_profit="Take Profit",
    label_update_preferences="Update Preferences",
    label_updated="Updated",
    label_unrealized_pnl="Unrealized PnL",
    label_value="Value",
    label_win_rate="Win Rate",
    label_yes="yes",
    list_separator=", ",
    message_all_agent_stages_llm_path="All agent stages completed through the LLM path.",
    message_fallback_used_in="Fallback was used in",
    message_no_runtime_state="No runtime state recorded yet.",
    prompt_continue="Press Enter to continue",
    prompt_select_action="Select action",
    stage_coordinator="Coordinator",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column="bold cyan",
    title_execution_summary="Execution Summary",
    title_llm_status="LLM Status",
    title_operator_instruction="Operator Instruction",
    title_pipeline="Pipeline",
    title_recent_runs="Recent Runs",
    title_run_artifacts="Run Artifacts",
    title_runtime_events="Runtime Events",
    title_runtime_status="Runtime Status",
    title_service_status="Service Status",
    title_warning="Warning",
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
    label_approved="Onaylandi",
    label_continuous="Surekli",
    label_confidence="Guven",
    label_current_symbol="Gecerli Sembol",
    label_cycle_count="Dongu Sayisi",
    label_decision_path="Karar Yolu",
    label_entry="Giris",
    label_fallback="Fallback",
    label_field="Alan",
    label_heartbeat="Heartbeat",
    label_heartbeat_age="Heartbeat Yasi",
    label_interval="Aralik",
    label_key="Anahtar",
    label_last_recorded_error="Son Kayitli Hata",
    label_last_recorded_message="Son Kayitli Mesaj",
    label_last_recorded_state="Son Kayitli Durum",
    label_live_process="Canli Process",
    label_llm="LLM",
    label_lookback="Geriye Donuk Pencere",
    label_market_value="Piyasa Degeri",
    label_max_cycles="Maksimum Dongu",
    label_mode="Mod",
    label_no="hayir",
    label_notes="Notlar",
    label_observer_mode="Observer Modu",
    label_order_id="Order ID",
    label_pid="PID",
    label_poll_seconds="Poll Saniyesi",
    label_preference_update="Preference Guncellemesi",
    label_rationale="Gerekce",
    label_requires_confirmation="Onay Gerektirir",
    label_runtime="Runtime",
    label_service="Servis",
    label_side="Yon",
    label_source="Kaynak",
    label_stage="Asama",
    label_started="Basladi",
    label_status_note="Durum Notu",
    label_stop_requested="Durdurma Istendi",
    label_stop="Stop",
    label_structured_llm="Yapilandirilmis LLM yaniti",
    label_summary="Ozet",
    label_symbols="Semboller",
    label_take_profit="Take Profit",
    label_update_preferences="Tercihleri Guncelle",
    label_updated="Guncellendi",
    label_unrealized_pnl="Gerceklesmemis PnL",
    label_value="Deger",
    label_win_rate="Kazanma Orani",
    label_yes="evet",
    list_separator=", ",
    message_all_agent_stages_llm_path="Tum agent asamalari LLM yolu ile tamamlandi.",
    message_fallback_used_in="Fallback kullanilan asamalar",
    message_no_runtime_state="Henuz runtime durumu kaydedilmedi.",
    prompt_continue="Devam etmek icin Enter'a basin",
    prompt_select_action="Aksiyon sec",
    stage_coordinator="Coordinator",
    stage_manager="Manager",
    stage_regime="Regime",
    stage_risk="Risk",
    stage_strategy="Strategy",
    style_key_column=EN_TEXT.style_key_column,
    title_execution_summary="Execution Ozeti",
    title_llm_status="LLM Durumu",
    title_operator_instruction="Operator Talimati",
    title_pipeline="Pipeline",
    title_recent_runs="Son Run'lar",
    title_run_artifacts="Run Artifact'lari",
    title_runtime_events="Runtime Olaylari",
    title_runtime_status="Runtime Durumu",
    title_service_status="Servis Durumu",
    title_warning="Uyari",
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

LABEL_APPROVED = EN_TEXT.label_approved
LABEL_CONTINUOUS = EN_TEXT.label_continuous
LABEL_CONFIDENCE = EN_TEXT.label_confidence
LABEL_CURRENT_SYMBOL = EN_TEXT.label_current_symbol
LABEL_CYCLE_COUNT = EN_TEXT.label_cycle_count
LABEL_DECISION_PATH = EN_TEXT.label_decision_path
LABEL_ENTRY = EN_TEXT.label_entry
LABEL_FALLBACK = EN_TEXT.label_fallback
LABEL_FIELD = EN_TEXT.label_field
LABEL_HEARTBEAT = EN_TEXT.label_heartbeat
LABEL_HEARTBEAT_AGE = EN_TEXT.label_heartbeat_age
LABEL_INTERVAL = EN_TEXT.label_interval
LABEL_KEY = EN_TEXT.label_key
LABEL_LAST_RECORDED_ERROR = EN_TEXT.label_last_recorded_error
LABEL_LAST_RECORDED_MESSAGE = EN_TEXT.label_last_recorded_message
LABEL_LAST_RECORDED_STATE = EN_TEXT.label_last_recorded_state
LABEL_LIVE_PROCESS = EN_TEXT.label_live_process
LABEL_LLM = EN_TEXT.label_llm
LABEL_LOOKBACK = EN_TEXT.label_lookback
LABEL_MARKET_VALUE = EN_TEXT.label_market_value
LABEL_MAX_CYCLES = EN_TEXT.label_max_cycles
LABEL_MODE = EN_TEXT.label_mode
LABEL_NO = EN_TEXT.label_no
LABEL_NOTES = EN_TEXT.label_notes
LABEL_OBSERVER_MODE = EN_TEXT.label_observer_mode
LABEL_ORDER_ID = EN_TEXT.label_order_id
LABEL_PID = EN_TEXT.label_pid
LABEL_POLL_SECONDS = EN_TEXT.label_poll_seconds
LABEL_PREFERENCE_UPDATE = EN_TEXT.label_preference_update
LABEL_RATIONALE = EN_TEXT.label_rationale
LABEL_REQUIRES_CONFIRMATION = EN_TEXT.label_requires_confirmation
LABEL_RUNTIME = EN_TEXT.label_runtime
LABEL_SERVICE = EN_TEXT.label_service
LABEL_SIDE = EN_TEXT.label_side
LABEL_SOURCE = EN_TEXT.label_source
LABEL_STAGE = EN_TEXT.label_stage
LABEL_STARTED = EN_TEXT.label_started
LABEL_STATUS_NOTE = EN_TEXT.label_status_note
LABEL_STOP_REQUESTED = EN_TEXT.label_stop_requested
LABEL_STOP = EN_TEXT.label_stop
LABEL_STRUCTURED_LLM = EN_TEXT.label_structured_llm
LABEL_SUMMARY = EN_TEXT.label_summary
LABEL_SYMBOLS = EN_TEXT.label_symbols
LABEL_TAKE_PROFIT = EN_TEXT.label_take_profit
LABEL_UPDATE_PREFERENCES = EN_TEXT.label_update_preferences
LABEL_UPDATED = EN_TEXT.label_updated
LABEL_UNREALIZED_PNL = EN_TEXT.label_unrealized_pnl
LABEL_VALUE = EN_TEXT.label_value
LABEL_WIN_RATE = EN_TEXT.label_win_rate
LABEL_YES = EN_TEXT.label_yes
UI_LIST_SEPARATOR = EN_TEXT.list_separator

MESSAGE_ALL_AGENT_STAGES_LLM_PATH = EN_TEXT.message_all_agent_stages_llm_path
MESSAGE_FALLBACK_USED_IN = EN_TEXT.message_fallback_used_in
MESSAGE_NO_RUNTIME_STATE = EN_TEXT.message_no_runtime_state

STAGE_COORDINATOR = EN_TEXT.stage_coordinator
STAGE_MANAGER = EN_TEXT.stage_manager
STAGE_REGIME = EN_TEXT.stage_regime
STAGE_RISK = EN_TEXT.stage_risk
STAGE_STRATEGY = EN_TEXT.stage_strategy

TITLE_EXECUTION_SUMMARY = EN_TEXT.title_execution_summary
TITLE_LLM_STATUS = EN_TEXT.title_llm_status
TITLE_OPERATOR_INSTRUCTION = EN_TEXT.title_operator_instruction
TITLE_PIPELINE = EN_TEXT.title_pipeline
TITLE_RECENT_RUNS = EN_TEXT.title_recent_runs
TITLE_RUN_ARTIFACTS = EN_TEXT.title_run_artifacts
TITLE_RUNTIME_EVENTS = EN_TEXT.title_runtime_events
TITLE_RUNTIME_STATUS = EN_TEXT.title_runtime_status
TITLE_SERVICE_STATUS = EN_TEXT.title_service_status
TITLE_WARNING = EN_TEXT.title_warning

PROMPT_CONTINUE = EN_TEXT.prompt_continue
PROMPT_SELECT_ACTION = EN_TEXT.prompt_select_action

STYLE_KEY_COLUMN = EN_TEXT.style_key_column

DB_LOCKED_MSG = EN_TEXT.db_locked_msg
