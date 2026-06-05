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
from agentic_trader.ui_text import t

console = Console()


def _yes_no(value: object) -> str:
    return t("label.yes") if value else t("label.no")


def render_status(settings: Settings, db: TradingDatabase | None) -> None:
    health = LocalLLM(settings).health_check()
    runtime_state = read_service_state(settings)
    status = Table(title=t("title.system.status"))
    status.add_column(t("label.key"))
    status.add_column(t("label.value"))
    status.add_row(t("label.runtime.dir"), str(settings.runtime_dir))
    status.add_row(t("label.database"), str(settings.database_path))
    status.add_row(
        t("title.runtime.mode"),
        (
            runtime_state.runtime_mode
            if runtime_state is not None
            else settings.runtime_mode
        ),
    )
    status.add_row(t("label.model"), settings.model_name)
    status.add_row(t("label.base.url"), settings.base_url)
    status.add_row(
        t("label.ollama.reachable"),
        _yes_no(health.service_reachable),
    )
    status.add_row(
        t("label.model.available"),
        _yes_no(health.model_available),
    )
    status.add_row(t("label.strict.llm"), str(settings.strict_llm))
    console.print(status)
    render_runtime_state(runtime_state)
    console.print(
        current_activity_panel(
            settings, runtime_state, read_service_events(settings, limit=12)
        )
    )
    if db is None:
        console.print(
            observer_mode_panel(
                f"{t('title.investment.preferences')} / {t('title.portfolio')}"
            )
        )
    else:
        console.print(render_preferences(db.load_preferences()))
        render_recent_runs(db)
    render_runtime_events(read_service_events(settings, limit=6))


def render_compact_status(settings: Settings, db: TradingDatabase | None) -> None:
    health = LocalLLM(settings).health_check()
    runtime_state = read_service_state(settings)
    runtime_view = build_runtime_status_view(runtime_state)
    broker = broker_runtime_payload(settings)
    provider = object_mapping(provider_diagnostics_payload(settings))
    readiness = object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper = object_mapping(readiness.get("paper_operations"))
    alpaca = object_mapping(readiness.get("alpaca_paper"))
    table = Table(title=t("title.system.snapshot"), expand=True)
    table.add_column(t("label.key"), style="cyan")
    table.add_column(t("label.value"))
    table.add_row(
        t("label.runtime"),
        f"{runtime_view.runtime_state} / {runtime_state.runtime_mode if runtime_state is not None else settings.runtime_mode}",
    )
    table.add_row(t("label.model"), settings.model_name)
    table.add_row(
        t("label.llm.ready"),
        _yes_no(health.service_reachable and health.model_available),
    )
    table.add_row(
        t("label.broker"),
        f"{broker['backend']} / {broker['state']}",
    )
    table.add_row(
        t("label.v1.paper.ready"),
        _yes_no(paper.get("allowed")),
    )
    table.add_row(
        t("label.alpaca.paper.ready"),
        _yes_no(alpaca.get("ready")),
    )
    warnings = object_list(provider.get("warnings"))
    table.add_row(
        t("label.provider.warnings"),
        str(len(warnings)),
    )
    table.add_row(
        t("label.kill.switch"),
        _yes_no(broker["kill_switch_active"]),
    )
    table.add_row(
        t("label.db.views"),
        t("status.readable") if db is not None else t("label.observer.mode"),
    )
    console.print(table)


__all__ = (
    "render_compact_status",
    "render_status",
)
