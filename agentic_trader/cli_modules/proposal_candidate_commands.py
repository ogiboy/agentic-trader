"""Proposal candidate create/promote CLI commands."""

import typer
from rich.panel import Panel

from agentic_trader.ui_text import t as ui_t
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
    symbol: str = typer.Option(..., "--symbol", help=ui_t("help.symbol")),  # NOSONAR
    preset: str = typer.Option("momentum", "--preset", help=ui_t("help.idea_preset")),
    price: float = typer.Option(
        ..., "--price", min=0.01, help=ui_t("help.trade_reference_price")
    ),
    volume: float = typer.Option(
        ..., "--volume", min=0.0, help=ui_t("help.idea_volume")
    ),
    change_pct: float = typer.Option(
        ..., "--change-pct", help=ui_t("help.idea_change_pct")
    ),
    relative_volume: float = typer.Option(0.0, "--relative-volume", min=0.0),
    gap_pct: float = typer.Option(0.0, "--gap-pct", help=ui_t("help.idea_gap_pct")),
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
        help=ui_t("help.trade_invalidation"),
    ),
    thesis: str = typer.Option("", "--thesis", help=ui_t("help.trade_thesis")),
    materiality: str = typer.Option(
        "", "--materiality", help=ui_t("help.candidate_materiality")
    ),
    freshness: str = typer.Option(
        "operator_supplied_current",
        "--freshness",
        help=ui_t("help.candidate_freshness"),
    ),
    liquidity: str = typer.Option(
        "", "--liquidity", help=ui_t("help.candidate_liquidity")
    ),
    risk_notes: str = typer.Option(
        "", "--risk-notes", help=ui_t("help.candidate_risk_notes")
    ),
    source: str = typer.Option(
        "idea-scanner", "--source", help=ui_t("help.candidate_source")
    ),
    enrich_provider_context: bool = typer.Option(
        True,
        "--enrich-provider-context/--no-enrich-provider-context",
        help=ui_t("help.enrich_provider_context"),
    ),
    fetch_provider_news: bool = typer.Option(
        False,
        "--fetch-provider-news/--no-fetch-provider-news",
        help=ui_t("help.fetch_provider_news"),
    ),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
    candidate_id: str = typer.Argument(..., help=ui_t("help.proposal_candidate_id")),
    review_notes: str = typer.Option("", help=ui_t("help.promotion_notes")),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
            Panel(str(exc), title=ui_t("title.promotion_blocked"), border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    candidate = ProposalCandidateRecord.model_validate(payload["candidate"])
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    console.print(
        Panel(
            ui_t("message.proposal_candidate_promoted").format(
                candidate_id=candidate.candidate_id,
                proposal_id=proposal.proposal_id,
            ),
            title=ui_t("title.proposal_candidate_promoted"),
            border_style="green",
        )
    )
