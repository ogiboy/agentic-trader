"""Proposal candidate create/promote CLI commands."""

import typer
from rich.panel import Panel

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.common import console, emit_json, emit_json_error
from agentic_trader.cli_modules.proposal_actions import promote_candidate_payload
from agentic_trader.cli_modules.proposal_desk_state import settings as _settings
from agentic_trader.cli_modules.proposal_records import (
    candidate_draft_from_options,
    create_candidate_record,
    emit_candidate_created,
    raise_candidate_create_error,
)
from agentic_trader.schemas import ProposalCandidateRecord, TradeProposalRecord


def proposal_candidate_create(  # NOSONAR - Typer maps each CLI option into the command signature.
    symbol: str = typer.Option(..., "--symbol", help=text.HELP_SYMBOL),  # NOSONAR
    preset: str = typer.Option("momentum", "--preset", help=text.HELP_IDEA_PRESET),
    price: float = typer.Option(
        ..., "--price", min=0.01, help=text.HELP_TRADE_REFERENCE_PRICE
    ),
    volume: float = typer.Option(..., "--volume", min=0.0, help=text.HELP_IDEA_VOLUME),
    change_pct: float = typer.Option(
        ..., "--change-pct", help=text.HELP_IDEA_CHANGE_PCT
    ),
    relative_volume: float = typer.Option(0.0, "--relative-volume", min=0.0),
    gap_pct: float = typer.Option(0.0, "--gap-pct", help=text.HELP_IDEA_GAP_PCT),
    range_pct: float = typer.Option(0.0, "--range-pct", min=0.0),
    rsi: float | None = typer.Option(None, "--rsi", min=0.0, max=100.0),
    ema_9: float | None = typer.Option(None, "--ema-9", min=0.0),
    sma_20: float | None = typer.Option(None, "--sma-20", min=0.0),
    sma_50: float | None = typer.Option(None, "--sma-50", min=0.0),
    vwap: float | None = typer.Option(None, "--vwap", min=0.0),
    spread_pct: float = typer.Option(0.0, "--spread-pct", min=0.0),
    quantity: float | None = typer.Option(None, "--quantity", min=0.0),
    notional: float | None = typer.Option(None, "--notional", min=0.0),
    stop_loss: float | None = typer.Option(None, "--stop-loss", min=0.01),
    take_profit: float | None = typer.Option(None, "--take-profit", min=0.01),
    invalidation_condition: str | None = typer.Option(
        None,
        "--invalidation-condition",
        help=text.HELP_TRADE_INVALIDATION,
    ),
    thesis: str = typer.Option("", "--thesis", help=text.HELP_TRADE_THESIS),
    materiality: str = typer.Option(
        "", "--materiality", help=text.HELP_CANDIDATE_MATERIALITY
    ),
    freshness: str = typer.Option(
        "operator_supplied_current",
        "--freshness",
        help=text.HELP_CANDIDATE_FRESHNESS,
    ),
    liquidity: str = typer.Option(
        "", "--liquidity", help=text.HELP_CANDIDATE_LIQUIDITY
    ),
    risk_notes: str = typer.Option(
        "", "--risk-notes", help=text.HELP_CANDIDATE_RISK_NOTES
    ),
    source: str = typer.Option(
        "idea-scanner", "--source", help=text.HELP_CANDIDATE_SOURCE
    ),
    enrich_provider_context: bool = typer.Option(
        True,
        "--enrich-provider-context/--no-enrich-provider-context",
        help=text.HELP_ENRICH_PROVIDER_CONTEXT,
    ),
    fetch_provider_news: bool = typer.Option(
        False,
        "--fetch-provider-news/--no-fetch-provider-news",
        help=text.HELP_FETCH_PROVIDER_NEWS,
    ),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Persist a scanner/research candidate without approving or submitting it."""
    settings = _settings()
    draft = candidate_draft_from_options(locals())
    try:
        candidate = create_candidate_record(
            settings=settings,
            draft=draft,
            enrich_provider_context=enrich_provider_context,
            fetch_provider_news=fetch_provider_news,
        )
    except ValueError as exc:
        raise_candidate_create_error(exc, json_output=json_output)
    emit_candidate_created(candidate, json_output=json_output)


def proposal_candidate_promote(
    candidate_id: str = typer.Argument(..., help=text.HELP_PROPOSAL_CANDIDATE_ID),
    review_notes: str = typer.Option("", help=text.HELP_PROMOTION_NOTES),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Promote a proposal candidate into a pending manual-review trade proposal."""
    settings = _settings()
    try:
        payload = promote_candidate_payload(
            settings=settings,
            candidate_id=candidate_id,
            review_notes=review_notes,
        )
    except ValueError as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=text.TITLE_PROMOTION_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    candidate = ProposalCandidateRecord.model_validate(payload["candidate"])
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    console.print(
        Panel(
            text.MESSAGE_PROPOSAL_CANDIDATE_PROMOTED.format(
                candidate_id=candidate.candidate_id,
                proposal_id=proposal.proposal_id,
            ),
            title=text.TITLE_PROPOSAL_CANDIDATE_PROMOTED,
            border_style="green",
        )
    )
