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
    help_interval: str
    help_json: str
    help_lookback: str
    help_model_service_app: str
    help_run_id: str
    help_symbol: str
    help_tool_ownership_app: str
    help_trade_notional: str
    help_trade_quantity: str
    help_trade_side: str
    help_webgui_service_app: str
    label_market_value: str
    label_observer_mode: str
    label_stop_requested: str
    label_structured_llm: str
    label_unrealized_pnl: str
    label_win_rate: str
    prompt_continue: str
    prompt_select_action: str
    style_key_column: str
    title_recent_runs: str
    title_runtime_events: str
    title_runtime_status: str
    title_service_status: str


EN_TEXT = UITextCatalog(
    cli_app_help="Agentic Trader CLI",
    db_locked_msg="The runtime writer currently owns the database.",
    help_camofox_service_app="Manage the optional app-owned local Camofox browser helper.",
    help_interval="yfinance interval, for example 1d or 1h",
    help_json="Emit machine-readable JSON.",
    help_lookback="Lookback window accepted by yfinance",
    help_model_service_app="Manage the optional app-owned local model service.",
    help_run_id="Run id to inspect. Defaults to the latest recorded run.",
    help_symbol="Ticker symbol, for example AAPL or BTC-USD",
    help_tool_ownership_app="Inspect or record optional helper ownership decisions.",
    help_trade_notional="Dollar notional. Either quantity or notional is required.",
    help_trade_quantity="Share quantity. Either quantity or notional is required.",
    help_trade_side="Trade side: buy or sell.",
    help_webgui_service_app="Manage the optional app-owned local Web GUI service.",
    label_market_value="Market Value",
    label_observer_mode="Observer Mode",
    label_stop_requested="Stop Requested",
    label_structured_llm="Structured LLM response",
    label_unrealized_pnl="Unrealized PnL",
    label_win_rate="Win Rate",
    prompt_continue="Press Enter to continue",
    prompt_select_action="Select action",
    style_key_column="bold cyan",
    title_recent_runs="Recent Runs",
    title_runtime_events="Runtime Events",
    title_runtime_status="Runtime Status",
    title_service_status="Service Status",
)

# Terminal-facing Turkish copy intentionally remains ASCII-safe until CLI/TUI
# locale rendering is audited across non-UTF-8 shells. Web surfaces keep full
# Turkish orthography in their own copy catalogs.
TR_TEXT = UITextCatalog(
    cli_app_help="Agentic Trader CLI",
    db_locked_msg="Runtime writer veritabaninin sahibi; biraz sonra tekrar deneyin.",
    help_camofox_service_app="Istege bagli app-owned yerel Camofox browser yardimcisini yonet.",
    help_interval="yfinance araligi, ornegin 1d veya 1h",
    help_json="Makine tarafindan okunabilir JSON uret.",
    help_lookback="yfinance tarafindan kabul edilen geriye donuk pencere",
    help_model_service_app="Istege bagli app-owned yerel model servisini yonet.",
    help_run_id="Incelenecek run id. Varsayilan son kayitli run.",
    help_symbol="Ticker sembolu, ornegin AAPL veya BTC-USD",
    help_tool_ownership_app="Istege bagli yardimci arac sahipligi kararlarini incele veya kaydet.",
    help_trade_notional="Dolar notional. Quantity veya notional degerlerinden biri gereklidir.",
    help_trade_quantity="Hisse adedi. Quantity veya notional degerlerinden biri gereklidir.",
    help_trade_side="Trade yonu: buy veya sell.",
    help_webgui_service_app="Istege bagli app-owned yerel Web GUI servisini yonet.",
    label_market_value="Piyasa Degeri",
    label_observer_mode="Observer Modu",
    label_stop_requested="Durdurma Istendi",
    label_structured_llm="Yapilandirilmis LLM yaniti",
    label_unrealized_pnl="Gerceklesmemis PnL",
    label_win_rate="Kazanma Orani",
    prompt_continue="Devam etmek icin Enter'a basin",
    prompt_select_action="Aksiyon sec",
    style_key_column=EN_TEXT.style_key_column,
    title_recent_runs="Son Run'lar",
    title_runtime_events="Runtime Olaylari",
    title_runtime_status="Runtime Durumu",
    title_service_status="Servis Durumu",
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
HELP_TRADE_SIDE = EN_TEXT.help_trade_side
HELP_TRADE_QUANTITY = EN_TEXT.help_trade_quantity
HELP_TRADE_NOTIONAL = EN_TEXT.help_trade_notional

LABEL_MARKET_VALUE = EN_TEXT.label_market_value
LABEL_OBSERVER_MODE = EN_TEXT.label_observer_mode
LABEL_STOP_REQUESTED = EN_TEXT.label_stop_requested
LABEL_STRUCTURED_LLM = EN_TEXT.label_structured_llm
LABEL_UNREALIZED_PNL = EN_TEXT.label_unrealized_pnl
LABEL_WIN_RATE = EN_TEXT.label_win_rate

TITLE_RECENT_RUNS = EN_TEXT.title_recent_runs
TITLE_RUNTIME_EVENTS = EN_TEXT.title_runtime_events
TITLE_RUNTIME_STATUS = EN_TEXT.title_runtime_status
TITLE_SERVICE_STATUS = EN_TEXT.title_service_status

PROMPT_CONTINUE = EN_TEXT.prompt_continue
PROMPT_SELECT_ACTION = EN_TEXT.prompt_select_action

STYLE_KEY_COLUMN = EN_TEXT.style_key_column

DB_LOCKED_MSG = EN_TEXT.db_locked_msg
