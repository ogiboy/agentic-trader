from rich.console import Console
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import (
    provider_diagnostics_payload,
    v1_readiness_payload,
)
from agentic_trader.engine.broker import broker_runtime_payload
from agentic_trader.json_utils import object_list, object_mapping
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import read_service_events, read_service_state
from agentic_trader.runtime_status import build_runtime_status_view
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.monitor_runtime import (
    current_activity_panel,
    observer_mode_panel,
    render_runtime_events,
    render_runtime_state,
)
from agentic_trader.tui_modules.monitor_tables import (
    render_preferences,
    render_recent_runs,
)
from agentic_trader.ui_text import (
    LABEL_ALPACA_PAPER_READY,
    LABEL_BASE_URL,
    LABEL_BROKER,
    LABEL_DATABASE,
    LABEL_DB_VIEWS,
    LABEL_KEY,
    LABEL_KILL_SWITCH,
    LABEL_LLM_READY,
    LABEL_MODEL,
    LABEL_MODEL_AVAILABLE,
    LABEL_NO,
    LABEL_OBSERVER_MODE,
    LABEL_OLLAMA_REACHABLE,
    LABEL_PROVIDER_WARNINGS,
    LABEL_RUNTIME,
    LABEL_RUNTIME_DIR,
    LABEL_STRICT_LLM,
    LABEL_V1_PAPER_READY,
    LABEL_VALUE,
    LABEL_YES,
    TITLE_INVESTMENT_PREFERENCES,
    TITLE_PORTFOLIO,
    TITLE_RUNTIME_MODE,
    TITLE_SYSTEM_SNAPSHOT,
    TITLE_SYSTEM_STATUS,
    get_ui_text,
)

console = Console()


def render_status(settings: Settings, db: TradingDatabase | None) -> None:
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
    render_runtime_state(runtime_state)
    console.print(
        current_activity_panel(
            settings, runtime_state, read_service_events(settings, limit=12)
        )
    )
    if db is None:
        console.print(
            observer_mode_panel(TITLE_INVESTMENT_PREFERENCES + " / " + TITLE_PORTFOLIO)
        )
    else:
        console.print(render_preferences(db.load_preferences()))
        render_recent_runs(db)
    render_runtime_events(read_service_events(settings, limit=6))


def render_compact_status(settings: Settings, db: TradingDatabase | None) -> None:
    text = get_ui_text()
    health = LocalLLM(settings).health_check()
    runtime_state = read_service_state(settings)
    runtime_view = build_runtime_status_view(runtime_state)
    broker = broker_runtime_payload(settings)
    provider = object_mapping(provider_diagnostics_payload(settings))
    readiness = object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper = object_mapping(readiness.get("paper_operations"))
    alpaca = object_mapping(readiness.get("alpaca_paper"))
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
    warnings = object_list(provider.get("warnings"))
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
        text.status_readable if db is not None else LABEL_OBSERVER_MODE,
    )
    console.print(table)


__all__ = (
    "render_compact_status",
    "render_status",
)
