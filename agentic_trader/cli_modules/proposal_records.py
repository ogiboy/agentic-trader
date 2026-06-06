from __future__ import annotations

from typing import NoReturn, cast

import typer
from rich.panel import Panel

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import (
    console,
    emit_json,
    emit_json_error,
    open_db,
)
from agentic_trader.cli_modules.proposal_support import (
    parse_idea_preset,
    parse_order_type,
    parse_trade_side,
)
from agentic_trader.config import Settings
from agentic_trader.finance.ideas import IdeaCandidate
from agentic_trader.finance.proposal_candidates import (
    ProposalCandidateDraft,
    create_proposal_candidate,
)
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    create_trade_proposal,
)
from agentic_trader.schemas import ProposalCandidateRecord, TradeProposalRecord


def candidate_draft_from_options(options: dict[str, object]) -> ProposalCandidateDraft:
    return ProposalCandidateDraft(
        idea=IdeaCandidate(
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
        preset=parse_idea_preset(str(options["preset"])),
        quantity=cast(float | None, options["quantity"]),
        notional=cast(float | None, options["notional"]),
        stop_loss=cast(float | None, options["stop_loss"]),
        take_profit=cast(float | None, options["take_profit"]),
        invalidation_condition=cast(str | None, options["invalidation_condition"]),
        thesis=str(options["thesis"]),
        materiality=str(options["materiality"]),
        freshness=str(options["freshness"]),
        liquidity=str(options["liquidity"]),
        risk_notes=str(options["risk_notes"]),
        source=str(options["source"]),
    )


def create_candidate_record(
    *,
    settings: Settings,
    draft: ProposalCandidateDraft,
    enrich_provider_context: bool,
    fetch_provider_news: bool,
) -> ProposalCandidateRecord:
    db = open_db(settings)
    try:
        return create_proposal_candidate(
            db=db,
            draft=draft,
            settings=settings,
            enrich_provider_context=enrich_provider_context,
            fetch_provider_news=fetch_provider_news,
        )
    finally:
        db.close()


def raise_candidate_create_error(exc: ValueError, *, json_output: bool) -> NoReturn:
    """
    Handle a candidate creation failure by reporting the error and terminating the CLI.
    
    If `json_output` is True, emit a machine-readable JSON error and exit with code 2.
    Otherwise, print a red panel with the localized "candidate rejected" title and exit with code 2.
    
    Parameters:
        exc (ValueError): The exception describing the rejection reason.
        json_output (bool): If True, emit the error as JSON instead of printing a console panel.
    
    Raises:
        typer.Exit: Always raised to terminate the command with exit code 2; the original exception is chained.
    """
    if json_output:
        emit_json_error(exc)
        raise typer.Exit(code=2) from exc
    console.print(
        Panel(str(exc), title=ui_t("title.candidate_rejected"), border_style="red")
    )
    raise typer.Exit(code=2) from exc


def emit_candidate_created(
    candidate: ProposalCandidateRecord,
    *,
    json_output: bool,
) -> None:
    """
    Emit a success message announcing a created proposal candidate.
    
    If `json_output` is True, output the candidate as JSON; otherwise print a green, titled success panel containing the candidate ID, symbol, uppercased signal, and score.
    
    Parameters:
        candidate (ProposalCandidateRecord): The created proposal candidate to report.
        json_output (bool): When True emit JSON output; when False render a console panel.
    """
    if json_output:
        emit_json(candidate.model_dump(mode="json"))
        return
    console.print(
        Panel(
            ui_t("message.proposal_candidate_created").format(
                candidate_id=candidate.candidate_id,
                symbol=candidate.symbol,
                signal=candidate.signal.upper(),
                score=candidate.score,
            ),
            title=ui_t("title.proposal_candidate_created"),
            border_style="green",
        )
    )


def trade_proposal_draft_from_options(
    options: dict[str, object],
) -> TradeProposalDraft:
    return TradeProposalDraft(
        symbol=str(options["symbol"]),
        side=parse_trade_side(str(options["side"])),
        order_type=parse_order_type(str(options["order_type"])),
        quantity=cast(float | None, options["quantity"]),
        notional=cast(float | None, options["notional"]),
        limit_price=cast(float | None, options["limit_price"]),
        reference_price=cast(float, options["reference_price"]),
        confidence=cast(float, options["confidence"]),
        thesis=str(options["thesis"]),
        stop_loss=cast(float | None, options["stop_loss"]),
        take_profit=cast(float | None, options["take_profit"]),
        invalidation_condition=cast(str | None, options["invalidation_condition"]),
        source=str(options["source"]),
        review_notes=str(options["review_notes"]),
    )


def create_trade_proposal_record(
    *,
    settings: Settings,
    draft: TradeProposalDraft,
) -> TradeProposalRecord:
    db = open_db(settings)
    try:
        return create_trade_proposal(db=db, draft=draft)
    finally:
        db.close()
