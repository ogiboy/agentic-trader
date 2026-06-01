from collections.abc import Mapping

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import (
    provider_diagnostics_payload,
    v1_readiness_payload,
)
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_list as _object_list
from agentic_trader.json_utils import object_mapping as _object_mapping
from agentic_trader.json_utils import object_mapping_list as _object_mapping_list
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import read_service_events, read_service_state
from agentic_trader.runtime_status import build_runtime_status_view
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_monitor_sections import (
    _current_activity_panel,
    _observer_mode_panel,
    _render_preferences,
    _render_recent_runs,
    _render_runtime_events,
    _render_runtime_state,
)
from agentic_trader.ui_text import (
    LABEL_ALPACA_CREDENTIALS_CONFIGURED,
    LABEL_ALPACA_FEED,
    LABEL_ALPACA_PAPER_ENDPOINT,
    LABEL_ALPACA_PAPER_READY,
    LABEL_API_KEY,
    LABEL_BASE_URL,
    LABEL_BLOCKING,
    LABEL_BROKER,
    LABEL_CHECK,
    LABEL_DATABASE,
    LABEL_DB_VIEWS,
    LABEL_DEFAULT_MODEL,
    LABEL_DETAILS,
    LABEL_ENABLED,
    LABEL_FIELD,
    LABEL_FRESHNESS,
    LABEL_HEALTHCHECK,
    LABEL_KEY,
    LABEL_KILL_SWITCH,
    LABEL_LLM_PROVIDER,
    LABEL_LLM_READY,
    LABEL_MARKET_PROVIDER,
    LABEL_MARKET_ROLE,
    LABEL_MODEL,
    LABEL_MODEL_AVAILABLE,
    LABEL_NEWS_MODE,
    LABEL_NO,
    LABEL_OBSERVER_MODE,
    LABEL_OLLAMA_REACHABLE,
    LABEL_PROVIDER,
    LABEL_PROVIDER_WARNINGS,
    LABEL_REASONS,
    LABEL_ROLE,
    LABEL_RUNTIME,
    LABEL_RUNTIME_DIR,
    LABEL_STATE,
    LABEL_STRICT_LLM,
    LABEL_TYPE,
    LABEL_V1_PAPER_READY,
    LABEL_VALUE,
    LABEL_YES,
    MESSAGE_V1_READINESS_STATUS_UNAVAILABLE,
    STYLE_KEY_COLUMN,
    TITLE_ALPACA_PAPER_CHECKS,
    TITLE_BROKER_STATUS,
    TITLE_INVESTMENT_PREFERENCES,
    TITLE_PAPER_OPERATION_CHECKS,
    TITLE_PORTFOLIO,
    TITLE_PROVIDER_DIAGNOSTICS,
    TITLE_PROVIDER_SOURCE_LADDER,
    TITLE_RUNTIME_MODE,
    TITLE_SYSTEM_SNAPSHOT,
    TITLE_SYSTEM_STATUS,
    TITLE_V1_READINESS,
    UI_LIST_SEPARATOR,
)

console = Console()

def _render_status(settings: Settings, db: TradingDatabase | None) -> None:
    """
    Render the system and runtime overview panels to the console, including status, current activity, preferences or observer-mode placeholders, and recent runtime events.

    Parameters:
        settings (Settings): Application settings used to populate system status and to read runtime/service state.
        db (TradingDatabase | None): If provided, DB-backed panels (preferences and recent runs) are rendered; if `None`, observer-mode placeholders are shown.
    """
    health = LocalLLM(settings).health_check()
    runtime_state = read_service_state(settings)
    status = Table(title=TITLE_SYSTEM_STATUS)
    status.add_column(LABEL_KEY)
    status.add_column(LABEL_VALUE)
    status.add_row(LABEL_RUNTIME_DIR, str(settings.runtime_dir))
    status.add_row(LABEL_DATABASE, str(settings.database_path))
    status.add_row(
        TITLE_RUNTIME_MODE,
        (
            runtime_state.runtime_mode
            if runtime_state is not None
            else settings.runtime_mode
        ),
    )
    status.add_row(LABEL_MODEL, settings.model_name)
    status.add_row(LABEL_BASE_URL, settings.base_url)
    status.add_row(
        LABEL_OLLAMA_REACHABLE, LABEL_YES if health.service_reachable else LABEL_NO
    )
    status.add_row(
        LABEL_MODEL_AVAILABLE, LABEL_YES if health.model_available else LABEL_NO
    )
    status.add_row(LABEL_STRICT_LLM, str(settings.strict_llm))
    console.print(status)
    _render_runtime_state(runtime_state)
    console.print(
        _current_activity_panel(
            settings, runtime_state, read_service_events(settings, limit=12)
        )
    )
    if db is None:
        console.print(
            _observer_mode_panel(
                TITLE_INVESTMENT_PREFERENCES + " / " + TITLE_PORTFOLIO
            )
        )
    else:
        console.print(_render_preferences(db.load_preferences()))
        _render_recent_runs(db)
    _render_runtime_events(read_service_events(settings, limit=6))


def _render_compact_status(settings: Settings, db: TradingDatabase | None) -> None:
    """
    Render a compact system snapshot table showing runtime state, model, LLM readiness, broker status, kill-switch state, and whether database views are readable.

    Parameters:
        settings (Settings): Application settings used to read runtime and broker state and to evaluate LLM health.
        db (TradingDatabase | None): Open read-capable database instance; when None the UI marks DB views as observer-only.
    """
    health = LocalLLM(settings).health_check()
    runtime_state = read_service_state(settings)
    runtime_view = build_runtime_status_view(runtime_state)
    broker = broker_runtime_payload(settings)
    provider = _object_mapping(provider_diagnostics_payload(settings))
    readiness = _object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper = _object_mapping(readiness.get("paper_operations"))
    alpaca = _object_mapping(readiness.get("alpaca_paper"))
    table = Table(title=TITLE_SYSTEM_SNAPSHOT, expand=True)
    table.add_column(LABEL_KEY, style="cyan")
    table.add_column(LABEL_VALUE)
    table.add_row(
        LABEL_RUNTIME,
        f"{runtime_view.runtime_state} / {runtime_state.runtime_mode if runtime_state is not None else settings.runtime_mode}",
    )
    table.add_row(LABEL_MODEL, settings.model_name)
    table.add_row(
        LABEL_LLM_READY,
        LABEL_YES if health.service_reachable and health.model_available else LABEL_NO,
    )
    table.add_row(
        LABEL_BROKER,
        f"{broker['backend']} / {broker['state']}",
    )
    table.add_row(
        LABEL_V1_PAPER_READY,
        LABEL_YES if paper.get("allowed") else LABEL_NO,
    )
    table.add_row(
        LABEL_ALPACA_PAPER_READY,
        LABEL_YES if alpaca.get("ready") else LABEL_NO,
    )
    warnings = _object_list(provider.get("warnings"))
    table.add_row(
        LABEL_PROVIDER_WARNINGS,
        str(len(warnings)),
    )
    table.add_row(
        LABEL_KILL_SWITCH,
        LABEL_YES if broker["kill_switch_active"] else LABEL_NO,
    )
    table.add_row(
        LABEL_DB_VIEWS,
        "readable" if db is not None else LABEL_OBSERVER_MODE,
    )
    console.print(table)


def _render_broker_status(settings: Settings) -> None:
    """
    Render the broker backend runtime status as a Rich table to the console.

    Fetches the broker runtime payload from the current settings and prints it.

    Parameters:
        settings (Settings): Application settings used to obtain the broker runtime payload.
    """
    payload = broker_runtime_payload(settings)
    table = Table(title=TITLE_BROKER_STATUS)
    table.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_VALUE)
    for key in (
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
    ):
        rendered_key = key.replace("_", " ").title()
        table.add_row(rendered_key, str(payload.get(key, "-")))
    healthcheck = payload.get("healthcheck")
    healthcheck_mapping = _object_mapping(healthcheck)
    if healthcheck_mapping:
        table.add_row(LABEL_HEALTHCHECK, str(healthcheck_mapping.get("message", "-")))
        blockers = _object_list(healthcheck_mapping.get("blocking_reasons"))
        if blockers:
            table.add_row(
                LABEL_BLOCKING + " " + LABEL_REASONS,
                UI_LIST_SEPARATOR.join(str(item) for item in blockers) or "-",
            )
    console.print(table)


def _render_provider_diagnostics(settings: Settings) -> None:
    """
    Render provider diagnostics and provider source ladder panels to the console.
    
    Parameters:
        settings (Settings): Application settings used to collect provider diagnostics payloads.
    """
    payload = _object_mapping(provider_diagnostics_payload(settings))
    summary = Table(title=TITLE_PROVIDER_DIAGNOSTICS)
    summary.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    summary.add_column(LABEL_VALUE)
    llm = _object_mapping(payload.get("llm"))
    market = _object_mapping(payload.get("market_data"))
    news = _object_mapping(payload.get("news"))
    alpaca = _object_mapping(payload.get("alpaca"))
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
        summary.add_row(LABEL_ALPACA_PAPER_ENDPOINT, str(alpaca.get("paper_endpoint", "-")))
        summary.add_row(LABEL_ALPACA_FEED, str(alpaca.get("data_feed", "-")))
        summary.add_row(
            LABEL_ALPACA_CREDENTIALS_CONFIGURED,
            "configured" if alpaca.get("credentials_configured") else "missing",
        )
    console.print(summary)

    warnings = _object_list(payload.get("warnings"))
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
    for row in _object_mapping_list(payload.get("providers")):
        table.add_row(
            str(row.get("provider_id", "-")),
            str(row.get("provider_type", "-")),
            str(row.get("role", "-")),
            str(row.get("enabled", False)),
            str(row.get("api_key_ready", "-")),
            str(row.get("freshness", "-")),
        )
    console.print(table)


def _render_readiness_table(title: str, payload: Mapping[str, object]) -> None:
    """
    Render a readiness checks table showing each check's name, pass/fail state, blocking flag, and details.
    
    Parameters:
        title (str): Title displayed for the table.
        payload (Mapping[str, object]): Mapping expected to contain a "checks" entry iterable. Each check should be a mapping with optional keys:
            - "name" (str): Human-readable check name.
            - "passed" (bool): Whether the check passed.
            - "blocking" (bool): Whether the check blocks readiness.
            - "details" (str): Additional information about the check.
    """
    table = Table(title=title)
    table.add_column(LABEL_CHECK, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_STATE)
    table.add_column(LABEL_BLOCKING)
    table.add_column(LABEL_DETAILS)
    for item in _object_mapping_list(payload.get("checks")):
        table.add_row(
            str(item.get("name", "-")),
            "[green]pass[/green]" if item.get("passed") else "[red]fail[/red]",
            str(item.get("blocking", True)),
            str(item.get("details", "")),
        )
    console.print(table)


def _render_v1_readiness(settings: Settings) -> None:
    """
    Render the v1 readiness summary and any available readiness check tables to the console.
    
    Prints a summary panel describing overall v1 readiness (including whether paper operations are allowed) and, when present, renders detailed readiness check tables for paper operations and Alpaca paper.
    
    Parameters:
        settings (Settings): Application settings used to compute the v1 readiness payload.
    """
    payload = _object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper = _object_mapping(payload.get("paper_operations"))
    alpaca = _object_mapping(payload.get("alpaca_paper"))
    paper_allowed = bool(paper.get("allowed"))
    console.print(
        Panel(
            str(payload.get("summary", MESSAGE_V1_READINESS_STATUS_UNAVAILABLE)),
            title=TITLE_V1_READINESS,
            border_style="green" if paper_allowed else "yellow",
        )
    )
    if paper:
        _render_readiness_table(TITLE_PAPER_OPERATION_CHECKS, paper)
    if alpaca:
        _render_readiness_table(TITLE_ALPACA_PAPER_CHECKS, alpaca)
