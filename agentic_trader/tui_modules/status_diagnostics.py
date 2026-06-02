from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import provider_diagnostics_payload
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_list, object_mapping, object_mapping_list
from agentic_trader.ui_text import (
    LABEL_ALPACA_CREDENTIALS_CONFIGURED,
    LABEL_ALPACA_FEED,
    LABEL_ALPACA_PAPER_ENDPOINT,
    LABEL_API_KEY,
    LABEL_BASE_URL,
    LABEL_BLOCKING,
    LABEL_DEFAULT_MODEL,
    LABEL_ENABLED,
    LABEL_FIELD,
    LABEL_FRESHNESS,
    LABEL_HEALTHCHECK,
    LABEL_LLM_PROVIDER,
    LABEL_MARKET_PROVIDER,
    LABEL_MARKET_ROLE,
    LABEL_NEWS_MODE,
    LABEL_PROVIDER,
    LABEL_PROVIDER_WARNINGS,
    LABEL_REASONS,
    LABEL_ROLE,
    LABEL_TYPE,
    LABEL_VALUE,
    STYLE_KEY_COLUMN,
    TITLE_BROKER_STATUS,
    TITLE_PROVIDER_DIAGNOSTICS,
    TITLE_PROVIDER_SOURCE_LADDER,
    UI_LIST_SEPARATOR,
    get_ui_text,
)

console = Console()

BROKER_STATUS_KEYS: tuple[str, ...] = (
    "backend",
    "adapter_name",
    "state",
    "execution_mode",
    "external_paper",
    "live_execution_enabled",
    "kill_switch_active",
    "live_requested",
    "live_ready",
    "alpaca_paper_trading_enabled",
    "alpaca_paper_endpoint",
    "alpaca_data_feed",
    "alpaca_credentials_configured",
    "message",
)


def render_broker_status(settings: Settings) -> None:
    payload = broker_runtime_payload(settings)
    table = Table(title=TITLE_BROKER_STATUS)
    table.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_VALUE)
    for key in BROKER_STATUS_KEYS:
        rendered_key = key.replace("_", " ").title()
        table.add_row(rendered_key, str(payload.get(key, "-")))
    healthcheck = payload.get("healthcheck")
    healthcheck_mapping = object_mapping(healthcheck)
    if healthcheck_mapping:
        table.add_row(LABEL_HEALTHCHECK, str(healthcheck_mapping.get("message", "-")))
        blockers = object_list(healthcheck_mapping.get("blocking_reasons"))
        if blockers:
            table.add_row(
                LABEL_BLOCKING + " " + LABEL_REASONS,
                UI_LIST_SEPARATOR.join(str(item) for item in blockers) or "-",
            )
    console.print(table)


def render_provider_diagnostics(settings: Settings) -> None:
    text = get_ui_text()
    payload = object_mapping(provider_diagnostics_payload(settings))
    summary = Table(title=TITLE_PROVIDER_DIAGNOSTICS)
    summary.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    summary.add_column(LABEL_VALUE)
    llm = object_mapping(payload.get("llm"))
    market = object_mapping(payload.get("market_data"))
    news = object_mapping(payload.get("news"))
    alpaca = object_mapping(payload.get("alpaca"))
    if llm:
        summary.add_row(LABEL_LLM_PROVIDER, str(llm.get("provider", "-")))
        summary.add_row(LABEL_DEFAULT_MODEL, str(llm.get("default_model", "-")))
        summary.add_row(LABEL_BASE_URL, str(llm.get("base_url", "-")))
    if market:
        summary.add_row(LABEL_MARKET_PROVIDER, str(market.get("selected_provider", "-")))
        summary.add_row(LABEL_MARKET_ROLE, str(market.get("selected_role", "-")))
    if news:
        summary.add_row(LABEL_NEWS_MODE, str(news.get("mode", "-")))
    if alpaca:
        summary.add_row(
            LABEL_ALPACA_PAPER_ENDPOINT, str(alpaca.get("paper_endpoint", "-"))
        )
        summary.add_row(LABEL_ALPACA_FEED, str(alpaca.get("data_feed", "-")))
        summary.add_row(
            LABEL_ALPACA_CREDENTIALS_CONFIGURED,
            text.status_configured
            if alpaca.get("credentials_configured")
            else text.status_missing,
        )
    console.print(summary)

    warnings = object_list(payload.get("warnings"))
    if warnings:
        console.print(
            Panel(
                "\n".join(str(warning) for warning in warnings),
                title=LABEL_PROVIDER_WARNINGS,
                border_style="yellow",
            )
        )

    table = Table(title=TITLE_PROVIDER_SOURCE_LADDER)
    table.add_column(LABEL_PROVIDER, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_TYPE)
    table.add_column(LABEL_ROLE)
    table.add_column(LABEL_ENABLED)
    table.add_column(LABEL_API_KEY)
    table.add_column(LABEL_FRESHNESS)
    for row in object_mapping_list(payload.get("providers")):
        table.add_row(
            str(row.get("provider_id", "-")),
            str(row.get("provider_type", "-")),
            str(row.get("role", "-")),
            str(row.get("enabled", False)),
            str(row.get("api_key_ready", "-")),
            str(row.get("freshness", "-")),
        )
    console.print(table)


__all__ = (
    "render_broker_status",
    "render_provider_diagnostics",
)
