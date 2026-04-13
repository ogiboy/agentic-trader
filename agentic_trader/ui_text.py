"""Shared operator-facing text constants.

This is intentionally a lightweight catalog, not a full localization layer yet.
Keeping recurring labels here gives future CLI, Rich, Ink, and WebUI surfaces a
single boundary to evolve into proper i18n without rewriting product flows.
"""

HELP_JSON = "Emit machine-readable JSON."
HELP_SYMBOL = "Ticker symbol, for example AAPL or BTC-USD"
HELP_INTERVAL = "yfinance interval, for example 1d or 1h"
HELP_LOOKBACK = "Lookback window accepted by yfinance"
HELP_RUN_ID = "Run id to inspect. Defaults to the latest recorded run."

LABEL_MARKET_VALUE = "Market Value"
LABEL_OBSERVER_MODE = "Observer Mode"
LABEL_STOP_REQUESTED = "Stop Requested"
LABEL_STRUCTURED_LLM = "Structured LLM response"
LABEL_UNREALIZED_PNL = "Unrealized PnL"
LABEL_WIN_RATE = "Win Rate"

TITLE_RECENT_RUNS = "Recent Runs"
TITLE_RUNTIME_EVENTS = "Runtime Events"
TITLE_RUNTIME_STATUS = "Runtime Status"
TITLE_SERVICE_STATUS = "Service Status"

PROMPT_CONTINUE = "Press Enter to continue"
PROMPT_SELECT_ACTION = "Select action"

STYLE_KEY_COLUMN = "bold cyan"

DB_LOCKED_MSG = "The runtime writer currently owns the database."
