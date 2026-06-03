"""Proposal-desk list commands."""

from typing import cast

import typer
from rich.panel import Panel

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.common import console, emit_json
from agentic_trader.cli_modules.proposal_desk_state import settings as _settings
from agentic_trader.cli_modules.proposal_support import (
    parse_candidate_status,
    parse_proposal_status,
    proposal_candidates_payload,
    render_proposal_candidates,
    render_trade_proposals,
    trade_proposals_payload,
)
from agentic_trader.schemas import ProposalCandidateRecord, TradeProposalRecord


def trade_proposals(
    status: str | None = typer.Option(
        None,
        "--status",
        help=text.HELP_TRADE_PROPOSALS_STATUS_FILTER,
    ),
    limit: int = typer.Option(50, min=1, max=200, help=text.HELP_TRADE_PROPOSALS_LIMIT),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Display the manual-review trade proposal queue."""
    settings = _settings()
    parsed_status = parse_proposal_status(status)
    payload = trade_proposals_payload(settings, status=parsed_status, limit=limit)
    if json_output:
        emit_json(payload)
        return
    proposals = [
        TradeProposalRecord.model_validate(item)
        for item in cast(list[dict[str, object]], payload["proposals"])
    ]
    if not payload["available"]:
        console.print(
            Panel(
                text.MESSAGE_TRADE_PROPOSALS_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    render_trade_proposals(proposals)


def proposal_candidates(
    status: str | None = typer.Option(
        None,
        "--status",
        help=text.HELP_PROPOSAL_CANDIDATES_STATUS_FILTER,
    ),
    limit: int = typer.Option(
        50, min=1, max=200, help=text.HELP_PROPOSAL_CANDIDATES_LIMIT
    ),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Show scanner/research candidates that may be promoted into proposals."""
    settings = _settings()
    parsed_status = parse_candidate_status(status)
    payload = proposal_candidates_payload(
        settings,
        status=parsed_status,
        limit=limit,
    )
    if json_output:
        emit_json(payload)
        return
    candidates = [
        ProposalCandidateRecord.model_validate(item)
        for item in cast(list[dict[str, object]], payload["candidates"])
    ]
    if not payload["available"]:
        console.print(
            Panel(
                text.MESSAGE_PROPOSAL_CANDIDATES_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    render_proposal_candidates(candidates)
