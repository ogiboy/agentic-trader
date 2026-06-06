from __future__ import annotations

from typing import NoReturn, cast

import typer
from rich.panel import Panel

from agentic_trader.ui_text import (
    MESSAGE_PROPOSAL_CANDIDATE_CREATED,
    TITLE_CANDIDATE_REJECTED,
    TITLE_PROPOSAL_CANDIDATE_CREATED,
)
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
    if json_output:
        emit_json_error(exc)
        raise typer.Exit(code=2) from exc
    console.print(
        Panel(str(exc), title=TITLE_CANDIDATE_REJECTED, border_style="red")
    )
    raise typer.Exit(code=2) from exc


def emit_candidate_created(
    candidate: ProposalCandidateRecord,
    *,
    json_output: bool,
) -> None:
    if json_output:
        emit_json(candidate.model_dump(mode="json"))
        return
    console.print(
        Panel(
            MESSAGE_PROPOSAL_CANDIDATE_CREATED.format(
                candidate_id=candidate.candidate_id,
                symbol=candidate.symbol,
                signal=candidate.signal.upper(),
                score=candidate.score,
            ),
            title=TITLE_PROPOSAL_CANDIDATE_CREATED,
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
