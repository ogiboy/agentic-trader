from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console, emit_json
from agentic_trader.config import Settings
from agentic_trader.schemas import LLMHealthStatus
from agentic_trader.storage.db import OrderRow, TradingDatabase
from agentic_trader.system.runtime_tools import apply_app_owned_service_settings
from agentic_trader.ui_text import t as ui_t

LatestOrderFormatter = Callable[[OrderRow | None], str]
HealthCheck = Callable[[Settings], LLMHealthStatus]


class OpenDatabase(Protocol):
    def __call__(
        self, settings: Settings, *, read_only: bool = False
    ) -> TradingDatabase: ...


def run_doctor_command(
    *,
    settings: Settings,
    json_output: bool,
    open_db: OpenDatabase,
    latest_order_formatter: LatestOrderFormatter,
    health_check: HealthCheck,
) -> None:
    apply_app_owned_service_settings(settings, include_camofox=True)
    payload = doctor_payload(
        settings,
        open_db=open_db,
        latest_order_formatter=latest_order_formatter,
        health_check=health_check,
    )
    if json_output:
        emit_json(payload)
        return
    render_doctor_payload(payload)


def doctor_payload(
    settings: Settings,
    *,
    open_db: OpenDatabase,
    latest_order_formatter: LatestOrderFormatter,
    health_check: HealthCheck,
) -> dict[str, object]:
    latest, db_status = _latest_order_status(
        settings,
        open_db=open_db,
        latest_order_formatter=latest_order_formatter,
    )
    health = health_check(settings)
    return {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "base_url": settings.base_url,
        "runtime_dir": str(settings.runtime_dir),
        "runtime_mode": settings.runtime_mode,
        "database": str(settings.database_path),
        "db_status": db_status,
        "model_routing": settings.model_routing(),
        "llm_reachable": health.service_reachable,
        "ollama_reachable": health.service_reachable,
        "model_available": health.model_available,
        "llm_status": health.message,
        "latest_order": latest,
    }


def _latest_order_status(
    settings: Settings,
    *,
    open_db: OpenDatabase,
    latest_order_formatter: LatestOrderFormatter,
) -> tuple[str, str]:
    try:
        db = open_db(settings, read_only=True)
        try:
            return latest_order_formatter(db.latest_order()), "ok"
        finally:
            db.close()
    except Exception as exc:
        return "unavailable", f"Database unavailable: {exc}"


def render_doctor_payload(payload: dict[str, object]) -> None:
    table = Table(title=ui_t("title.environment_check"))
    table.add_column(ui_t("label.key"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.llm_provider"), str(payload["provider"]))
    table.add_row(ui_t("label.model"), str(payload["model"]))
    table.add_row(ui_t("title.runtime_mode"), str(payload["runtime_mode"]))
    table.add_row(ui_t("label.base_url"), str(payload["base_url"]))
    table.add_row(ui_t("label.runtime_dir"), str(payload["runtime_dir"]))
    table.add_row(ui_t("label.database"), str(payload["database"]))
    table.add_row(ui_t("label.db_status"), str(payload["db_status"]))
    table.add_row(
        ui_t("label.model_routing"), json.dumps(payload["model_routing"], indent=2)
    )
    table.add_row(
        ui_t("label.ollama_reachable"),
        "[green]yes[/green]" if payload["ollama_reachable"] else "[red]no[/red]",
    )
    table.add_row(
        ui_t("label.model_available"),
        "[green]yes[/green]" if payload["model_available"] else "[yellow]no[/yellow]",
    )
    table.add_row(ui_t("title.llm_status"), str(payload["llm_status"]))
    table.add_row(ui_t("label.latest_order"), str(payload["latest_order"]))
    console.print(table)
    _render_runtime_readiness(payload)


def _render_runtime_readiness(payload: dict[str, object]) -> None:
    if payload["llm_reachable"] and payload["model_available"]:
        console.print(
            Panel(
                ui_t("message.trading_runtime_ready"),
                title="Ready",
                border_style="green",
            )
        )
        return
    console.print(
        Panel(
            ui_t("message.trading_runtime_blocked"),
            title="Blocked",
            border_style="red",
        )
    )
