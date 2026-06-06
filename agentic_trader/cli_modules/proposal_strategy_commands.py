"""Idea scanner and strategy catalog CLI commands."""

from __future__ import annotations

from typing import cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import (
    HELP_JSON,
    HELP_STRATEGY_CATALOG_PRESET_FILTER,
    HELP_STRATEGY_CATALOG_STATUS_FILTER,
    HELP_STRATEGY_PROFILE_NAME,
    LABEL_EVIDENCE,
    LABEL_FAMILY,
    LABEL_INTENT,
    LABEL_PRESET,
    LABEL_PROFILE,
    LABEL_RISK,
    LABEL_STATUS,
    LABEL_SUMMARY,
    LABEL_V1_PATH,
    LABEL_VALIDATION,
    MESSAGE_IDEA_PRESETS_EXECUTION_POLICY,
    MESSAGE_STRATEGY_PROFILE_EXECUTION_POLICY,
    TITLE_IDEA_SCANNER_PRESETS,
    TITLE_STRATEGY_PROFILE,
    TITLE_V1_STRATEGY_CATALOG,
)
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
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
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
        "execution_policy": MESSAGE_IDEA_PRESETS_EXECUTION_POLICY,
    }
    if json_output:
        emit_json(payload)
        return
    table = Table(title=TITLE_IDEA_SCANNER_PRESETS)
    table.add_column(LABEL_PRESET)
    table.add_column(LABEL_INTENT)
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
        help=HELP_STRATEGY_CATALOG_STATUS_FILTER,
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help=HELP_STRATEGY_CATALOG_PRESET_FILTER,
    ),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show repo-native strategy profiles and their V1 readiness gates."""

    parsed_status = parse_strategy_status(status)
    parsed_preset = parse_idea_preset(preset) if preset else None
    payload = strategy_catalog_payload(status=parsed_status, preset=parsed_preset)
    if json_output:
        emit_json(payload)
        return
    table = Table(title=TITLE_V1_STRATEGY_CATALOG)
    table.add_column(LABEL_PROFILE)
    table.add_column(LABEL_FAMILY)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_V1_PATH)
    table.add_column(LABEL_SUMMARY)
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
    name: str = typer.Argument(..., help=HELP_STRATEGY_PROFILE_NAME),
    json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
) -> None:
    """Show one strategy profile with evidence, risk, and validation gates."""

    try:
        profile = get_strategy_profile(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = {
        "profile": strategy_profile_payload(profile),
        "execution_policy": MESSAGE_STRATEGY_PROFILE_EXECUTION_POLICY,
    }
    if json_output:
        emit_json(payload)
        return
    profile_payload = payload["profile"]
    assert isinstance(profile_payload, dict)
    body = (
        f"{profile_payload['summary']}\n\n"
        f"{LABEL_EVIDENCE}: {', '.join(cast(list[str], profile_payload['evidence_requirements'])) or '-'}\n"
        f"{LABEL_RISK}: {', '.join(cast(list[str], profile_payload['risk_controls'])) or '-'}\n"
        f"{LABEL_VALIDATION}: {', '.join(cast(list[str], profile_payload['validation_checks'])) or '-'}"
    )
    console.print(
        Panel(
            body,
            title=TITLE_STRATEGY_PROFILE.format(name=profile.name),
            border_style="cyan",
        )
    )
