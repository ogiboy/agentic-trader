from __future__ import annotations

import os
import shutil
import sys as _sys
from collections.abc import Mapping
from pathlib import Path

import typer
from dotenv import set_key

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.backtest.walk_forward import (
    run_backtest_comparison,
    run_memory_ablation_backtest,
    run_walk_forward_backtest,
)
from agentic_trader.cli_modules.app_dashboard import (
    build_dashboard_snapshot_payload as _build_dashboard_snapshot_payload,
)
from agentic_trader.cli_modules.app_dashboard import (
    build_evidence_bundle as _build_evidence_bundle,
)
from agentic_trader.cli_modules.app_dashboard import (
    build_observer_api_payload as _build_observer_api_payload,
)
from agentic_trader.cli_modules.app_registration import (
    register_cli_app,
)
from agentic_trader.cli_modules.common import emit_json as _emit_json
from agentic_trader.cli_modules.common import open_db as _open_db
from agentic_trader.cli_modules.execution_rendering import render_execution_panels
from agentic_trader.cli_modules.locale_commands import parse_ui_locale, ui_payload
from agentic_trader.cli_modules.operator_readiness import (
    accelerator_payload as _operator_accelerator_payload,
)
from agentic_trader.cli_modules.operator_readiness import (
    total_memory_bytes as _operator_total_memory_bytes,
)
from agentic_trader.cli_modules.service_rendering import (
    format_latest_order as _format_latest_order,
)
from agentic_trader.cli_modules.service_rendering import (
    read_text_tail as _read_text_tail,
)
from agentic_trader.cli_modules.service_rendering import (
    render_health_panel as _render_health_panel,
)
from agentic_trader.cli_modules.service_rendering import (
    render_service_state as _render_service_state,
)
from agentic_trader.cli_modules.system_rendering import (
    render_operator_launcher_status as _render_operator_launcher_status,
)
from agentic_trader.cli_modules.system_rendering import (
    render_webgui_service_status as _render_webgui_service_status,
)
from agentic_trader.cli_modules.tui_node import (
    NodeCommandSet,
)
from agentic_trader.cli_modules.tui_node import (
    resolve_tui_node_commands as _resolve_tui_node_commands,
)
from agentic_trader.cli_modules.tui_node import (
    tui_dependencies_installed as tui_dependencies_installed,
)
from agentic_trader.config import Settings, get_settings
from agentic_trader.diagnostics import (
    provider_diagnostics_payload,
    v1_readiness_payload,
)
from agentic_trader.engine.broker import get_broker_adapter
from agentic_trader.finance.proposals import (
    refresh_trade_proposal_order,
    repair_missing_position_plans,
)
from agentic_trader.json_utils import object_list as _object_list
from agentic_trader.json_utils import object_mapping as _object_mapping
from agentic_trader.json_utils import object_mapping_list as _object_mapping_list
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.cycle_runner import run_research_cycle
from agentic_trader.researchd.news_intelligence import (
    classify_source_tier,
    news_research_plan,
)
from agentic_trader.runtime_feed import (
    append_chat_history,
    read_service_events,
    read_service_state,
    request_stop,
)
from agentic_trader.runtime_status import (
    build_runtime_status_view,
    is_process_alive,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.system.camofox_service import (
    build_camofox_service_status,
    start_camofox_service,
    stop_camofox_service,
)
from agentic_trader.system.model_service import (
    build_model_service_status,
    pull_model,
    start_model_service,
    stop_model_service,
)
from agentic_trader.system.operator_launcher import (
    build_operator_launcher_status,
    start_operator_webgui,
)
from agentic_trader.system.setup import build_setup_status
from agentic_trader.system.tool_ownership import (
    read_tool_ownership_payload,
    validate_ownership_mode,
    write_tool_ownership,
)
from agentic_trader.system.webgui_service import (
    build_webgui_service_status,
    stop_webgui_service,
)
from agentic_trader.tui import build_monitor_renderable, run_live_monitor, run_main_menu
from agentic_trader.ui_text import (
    HELP_CLI_APP,
    HELP_JSON,
    HELP_LOCALE_OVERRIDE,
    UI_LOCALE_ENV,
)
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import (
    ensure_llm_ready,
    restart_background_service,
    run_service,
    start_background_service,
    terminate_service_process,
)

__all__ = [
    "HELP_JSON",
    "HELP_LOCALE_OVERRIDE",
    "LocalLLM",
    "TradingDatabase",
    "UI_LOCALE_ENV",
    "_emit_json",
    "_format_latest_order",
    "_open_db",
    "_read_text_tail",
    "_render_health_panel",
    "_render_operator_launcher_status",
    "_render_service_state",
    "_render_webgui_service_status",
    "append_chat_history",
    "apply_preference_update",
    "build_monitor_renderable",
    "build_camofox_service_status",
    "build_operator_launcher_status",
    "build_runtime_status_view",
    "build_model_service_status",
    "build_setup_status",
    "build_webgui_service_status",
    "chat_with_persona",
    "classify_source_tier",
    "ensure_llm_ready",
    "fetch_ohlcv",
    "get_broker_adapter",
    "get_settings",
    "interpret_operator_instruction",
    "is_process_alive",
    "news_research_plan",
    "parse_ui_locale",
    "persist_run",
    "pull_model",
    "provider_diagnostics_payload",
    "read_service_events",
    "read_service_state",
    "read_tool_ownership_payload",
    "refresh_trade_proposal_order",
    "render_execution_panels",
    "repair_missing_position_plans",
    "request_stop",
    "research_cycle_plan_payload",
    "restart_background_service",
    "run_backtest_comparison",
    "run_live_monitor",
    "run_main_menu",
    "run_memory_ablation_backtest",
    "run_once",
    "run_research_cycle",
    "run_service",
    "run_walk_forward_backtest",
    "start_camofox_service",
    "start_background_service",
    "start_model_service",
    "start_operator_webgui",
    "stop_camofox_service",
    "stop_model_service",
    "stop_webgui_service",
    "terminate_service_process",
    "ui_payload",
    "validate_ownership_mode",
    "v1_readiness_payload",
    "write_tool_ownership",
]

app = typer.Typer(
    help=HELP_CLI_APP,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL_FILE = PROJECT_ROOT / ".env.local"


def object_mapping(value: object) -> Mapping[str, object]:
    """Return value as an object-keyed mapping when it already is one."""

    return _object_mapping(value)


def object_list(value: object) -> list[object]:
    """Return value as a list when it is a non-string sequence."""

    return _object_list(value)


def object_mapping_list(value: object) -> list[Mapping[str, object]]:
    """Return mapping rows from a non-string sequence."""

    return _object_mapping_list(value)


def upsert_env_local_value(key: str, value: str) -> None:
    set_key(ENV_LOCAL_FILE, key, value, quote_mode="never")
    os.environ[key] = value


def _accelerator_payload() -> dict[str, object]:
    return _operator_accelerator_payload()


def _total_memory_bytes() -> int | None:
    return _operator_total_memory_bytes()


def resolve_tui_node_commands(tui_dir: Path) -> NodeCommandSet | None:
    return _resolve_tui_node_commands(tui_dir, which=shutil.which)


def build_dashboard_snapshot_payload(
    settings: Settings, *, log_limit: int = 14, check_provider: bool = False
) -> dict[str, object]:
    return _build_dashboard_snapshot_payload(
        _sys.modules[__name__],
        settings,
        log_limit=log_limit,
        check_provider=check_provider,
    )


def build_evidence_bundle(
    settings: Settings,
    *,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    return _build_evidence_bundle(
        _sys.modules[__name__],
        settings,
        output_dir=output_dir,
        label=label,
        log_limit=log_limit,
        include_latest_smoke=include_latest_smoke,
        check_provider=check_provider,
    )


def build_observer_api_payload(
    settings: Settings, *, path: str, log_limit: int = 14
) -> tuple[int, dict[str, object]]:
    return _build_observer_api_payload(
        _sys.modules[__name__], settings, path=path, log_limit=log_limit
    )


register_cli_app(app=app, namespace=_sys.modules[__name__])


def main() -> None:
    app()


if __name__ == "__main__":
    main()
