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
from agentic_trader.ui_text import (
    LABEL_BASE_URL,
    LABEL_DATABASE,
    LABEL_DB_STATUS,
    LABEL_KEY,
    LABEL_LATEST_ORDER,
    LABEL_LLM_PROVIDER,
    LABEL_MODEL,
    LABEL_MODEL_AVAILABLE,
    LABEL_MODEL_ROUTING,
    LABEL_OLLAMA_REACHABLE,
    LABEL_RUNTIME_DIR,
    LABEL_VALUE,
    MESSAGE_TRADING_RUNTIME_BLOCKED,
    MESSAGE_TRADING_RUNTIME_READY,
    TITLE_ENVIRONMENT_CHECK,
    TITLE_LLM_STATUS,
    TITLE_RUNTIME_MODE,
)

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
    table = Table(title=TITLE_ENVIRONMENT_CHECK)
    table.add_column(LABEL_KEY)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_LLM_PROVIDER, str(payload["provider"]))
    table.add_row(LABEL_MODEL, str(payload["model"]))
    table.add_row(TITLE_RUNTIME_MODE, str(payload["runtime_mode"]))
    table.add_row(LABEL_BASE_URL, str(payload["base_url"]))
    table.add_row(LABEL_RUNTIME_DIR, str(payload["runtime_dir"]))
    table.add_row(LABEL_DATABASE, str(payload["database"]))
    table.add_row(LABEL_DB_STATUS, str(payload["db_status"]))
    table.add_row(LABEL_MODEL_ROUTING, json.dumps(payload["model_routing"], indent=2))
    table.add_row(
        LABEL_OLLAMA_REACHABLE,
        "[green]yes[/green]" if payload["ollama_reachable"] else "[red]no[/red]",
    )
    table.add_row(
        LABEL_MODEL_AVAILABLE,
        "[green]yes[/green]" if payload["model_available"] else "[yellow]no[/yellow]",
    )
    table.add_row(TITLE_LLM_STATUS, str(payload["llm_status"]))
    table.add_row(LABEL_LATEST_ORDER, str(payload["latest_order"]))
    console.print(table)
    _render_runtime_readiness(payload)


def _render_runtime_readiness(payload: dict[str, object]) -> None:
    if payload["llm_reachable"] and payload["model_available"]:
        console.print(
            Panel(
                MESSAGE_TRADING_RUNTIME_READY,
                title="Ready",
                border_style="green",
            )
        )
        return
    console.print(
        Panel(
            MESSAGE_TRADING_RUNTIME_BLOCKED,
            title="Blocked",
            border_style="red",
        )
    )
