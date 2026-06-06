"""Idea scanner and strategy catalog CLI commands."""

from __future__ import annotations

from typing import cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console, emit_json
from agentic_trader.cli_modules.proposal_support import (
    parse_idea_preset,
    parse_strategy_status,
    render_idea_score,
)
from agentic_trader.finance.ideas import PRESET_DESCRIPTIONS, IdeaCandidate
from agentic_trader.finance.strategy_catalog import (
    get_strategy_profile,
    strategy_catalog_payload,
    strategy_profile_for_preset,
    strategy_profile_payload,
)


def idea_presets(
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """Show V1 idea-scanner presets and their operator intent."""

    payload = {
        "presets": [
            {
                "name": name,
                "description": description,
                "strategy_profile": strategy_profile_payload(
                    strategy_profile_for_preset(name)
                ),
            }
            for name, description in PRESET_DESCRIPTIONS.items()
        ],
        "execution_policy": ui_t("message.idea_presets_execution_policy"),
    }
    if json_output:
        emit_json(payload)
        return
    table = Table(title=ui_t("title.idea_scanner_presets"))
    table.add_column(ui_t("label.preset"))
    table.add_column(ui_t("label.intent"))
    for item in cast(list[dict[str, str]], payload["presets"]):
        table.add_row(item["name"], item["description"])
    console.print(table)


def idea_score(**options: str) -> None:
    """Score a single scanner candidate without creating or executing a proposal."""

    render_idea_score(
        candidate=IdeaCandidate(
            symbol=str(options["symbol"]),
            price=cast(float, options["price"]),
            volume=cast(float, options["volume"]),
            change_pct=cast(float, options["change_pct"]),
            relative_volume=cast(float, options["relative_volume"]),
            gap_pct=cast(float, options["gap_pct"]),
            range_pct=cast(float, options["range_pct"]),
            rsi=cast(float | None, options["rsi"]),
            ema_9=cast(float | None, options["ema_9"]),
            sma_20=cast(float | None, options["sma_20"]),
            sma_50=cast(float | None, options["sma_50"]),
            vwap=cast(float | None, options["vwap"]),
            spread_pct=cast(float, options["spread_pct"]),
        ),
        preset=str(options["preset"]),
        json_output=bool(options["json_output"]),
    )


def strategy_catalog(
    status: str | None = typer.Option(
        None,
        "--status",
        help=ui_t("help.strategy_catalog_status_filter"),
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help=ui_t("help.strategy_catalog_preset_filter"),
    ),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """
    Show repository-native strategy profiles and their V1 readiness gates.
    
    Parameters:
        status (str | None): Optional status filter to restrict listed profiles.
        preset (str | None): Optional preset filter to restrict listed profiles.
        json_output (bool): If True, emit the catalog payload as JSON instead of rendering a table.
    """

    parsed_status = parse_strategy_status(status)
    parsed_preset = parse_idea_preset(preset) if preset else None
    payload = strategy_catalog_payload(status=parsed_status, preset=parsed_preset)
    if json_output:
        emit_json(payload)
        return
    table = Table(title=ui_t("title.v1_strategy_catalog"))
    table.add_column(ui_t("label.profile"))
    table.add_column(ui_t("label.family"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.v1_path"))
    table.add_column(ui_t("label.summary"))
    for item in cast(list[dict[str, object]], payload["profiles"]):
        table.add_row(
            str(item.get("name", "-")),
            str(item.get("family", "-")),
            str(item.get("status", "-")),
            str(item.get("v1_path", "-")),
            str(item.get("summary", "-")),
        )
    console.print(table)


def strategy_profile(
    name: str = typer.Argument(..., help=ui_t("help.strategy_profile_name")),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """
    Display a strategy profile including its summary, evidence requirements, risk controls, and validation checks.
    
    When `json_output` is true, emit a JSON payload containing the profile and execution policy instead of rendering a panel.
    
    Parameters:
        json_output (bool): If true, output the profile as JSON.
    
    Raises:
        typer.BadParameter: If the named strategy profile cannot be loaded.
    """

    try:
        profile = get_strategy_profile(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = {
        "profile": strategy_profile_payload(profile),
        "execution_policy": ui_t("message.strategy_profile_execution_policy"),
    }
    if json_output:
        emit_json(payload)
        return
    profile_payload = payload["profile"]
    assert isinstance(profile_payload, dict)
    body = (
        f"{profile_payload['summary']}\n\n"
        f"{ui_t('label.evidence')}: {', '.join(cast(list[str], profile_payload['evidence_requirements'])) or '-'}\n"
        f"{ui_t('label.risk')}: {', '.join(cast(list[str], profile_payload['risk_controls'])) or '-'}\n"
        f"{ui_t('label.validation')}: {', '.join(cast(list[str], profile_payload['validation_checks'])) or '-'}"
    )
    console.print(
        Panel(
            body,
            title=ui_t("title.strategy_profile").format(name=profile.name),
            border_style="cyan",
        )
    )
