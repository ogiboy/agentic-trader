from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import provider_diagnostics_payload
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_list, object_mapping, object_mapping_list
from agentic_trader.ui_text import t

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
    table = Table(title=t("title.broker.status"))
    table.add_column(t("label.field"), style=t("style.key.column"))
    table.add_column(t("label.value"))
    for key in BROKER_STATUS_KEYS:
        rendered_key = key.replace("_", " ").title()
        table.add_row(rendered_key, str(payload.get(key, "-")))
    healthcheck = payload.get("healthcheck")
    healthcheck_mapping = object_mapping(healthcheck)
    if healthcheck_mapping:
        table.add_row(
            t("label.healthcheck"), str(healthcheck_mapping.get("message", "-"))
        )
        blockers = object_list(healthcheck_mapping.get("blocking_reasons"))
        if blockers:
            table.add_row(
                f"{t('label.blocking')} {t('label.reasons')}",
                t("ui.list.separator").join(str(item) for item in blockers) or "-",
            )
    console.print(table)


def render_provider_diagnostics(settings: Settings) -> None:
    payload = object_mapping(provider_diagnostics_payload(settings))
    summary = Table(title=t("title.provider.diagnostics"))
    summary.add_column(t("label.field"), style=t("style.key.column"))
    summary.add_column(t("label.value"))
    llm = object_mapping(payload.get("llm"))
    market = object_mapping(payload.get("market_data"))
    news = object_mapping(payload.get("news"))
    alpaca = object_mapping(payload.get("alpaca"))
    if llm:
        summary.add_row(t("label.llm.provider"), str(llm.get("provider", "-")))
        summary.add_row(t("label.default.model"), str(llm.get("default_model", "-")))
        summary.add_row(t("label.base.url"), str(llm.get("base_url", "-")))
    if market:
        summary.add_row(
            t("label.market.provider"),
            str(market.get("selected_provider", "-")),
        )
        summary.add_row(t("label.market.role"), str(market.get("selected_role", "-")))
    if news:
        summary.add_row(t("label.news.mode"), str(news.get("mode", "-")))
    if alpaca:
        summary.add_row(
            t("label.alpaca.paper.endpoint"),
            str(alpaca.get("paper_endpoint", "-")),
        )
        summary.add_row(t("label.alpaca.feed"), str(alpaca.get("data_feed", "-")))
        summary.add_row(
            t("label.alpaca.credentials.configured"),
            (
                t("status.configured")
                if alpaca.get("credentials_configured")
                else t("status.missing")
            ),
        )
    console.print(summary)

    warnings = object_list(payload.get("warnings"))
    if warnings:
        console.print(
            Panel(
                "\n".join(str(warning) for warning in warnings),
                title=t("label.provider.warnings"),
                border_style="yellow",
            )
        )

    table = Table(title=t("title.provider.source.ladder"))
    table.add_column(t("label.provider"), style=t("style.key.column"))
    table.add_column(t("label.type"))
    table.add_column(t("label.role"))
    table.add_column(t("label.enabled"))
    table.add_column(t("label.api.key"))
    table.add_column(t("label.freshness"))
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
