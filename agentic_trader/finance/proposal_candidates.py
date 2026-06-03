from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.finance.ideas import (
    IdeaCandidate,
    IdeaPresetName,
    IdeaScore,
    score_candidate,
)
from agentic_trader.finance.proposal_candidate_context import (
    candidate_evidence,
)
from agentic_trader.finance.proposal_candidate_context import safe_note as _safe_note
from agentic_trader.finance.proposal_candidate_validation import (
    promotion_review_notes as _promotion_review_notes,
)
from agentic_trader.finance.proposal_candidate_validation import (
    validate_candidate_promotable as _validate_candidate_promotable,
)
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    prepare_trade_proposal,
    utc_now_iso,
)
from agentic_trader.schemas import (
    ProposalCandidateRecord,
    TradeProposalRecord,
    TradeSide,
)
from agentic_trader.storage.db import TradingDatabase


@dataclass(frozen=True, slots=True)
class ProposalCandidateDraft:
    idea: IdeaCandidate
    preset: IdeaPresetName
    quantity: float | None = None
    notional: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    invalidation_condition: str | None = None
    thesis: str = ""
    materiality: str = ""
    freshness: str = "operator_supplied_current"
    liquidity: str = ""
    risk_notes: str = ""
    source: str = "idea-scanner"
    evidence: dict[str, object] | None = None


def create_proposal_candidate(
    *,
    db: TradingDatabase,
    draft: ProposalCandidateDraft,
    settings: Settings | None = None,
    enrich_provider_context: bool = True,
    fetch_provider_news: bool = False,
) -> ProposalCandidateRecord:
    """Create and persist a validated, scored proposal candidate."""
    score = score_candidate(draft.idea, draft.preset)
    symbol = score.symbol.strip().upper()
    _validate_candidate_inputs(symbol=symbol, draft=draft)
    evidence = candidate_evidence(
        draft=draft,
        settings=settings,
        enrich_provider_context=enrich_provider_context,
        fetch_provider_news=fetch_provider_news,
    )
    candidate = _candidate_record(
        draft=draft,
        score=score,
        symbol=symbol,
        evidence=evidence,
    )
    db.insert_proposal_candidate(candidate)
    return candidate


def _validate_candidate_inputs(*, symbol: str, draft: ProposalCandidateDraft) -> None:
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Proposal candidates require a simple V1 US equity symbol.")
    if (draft.quantity is None) == (draft.notional is None):
        raise ValueError(
            "Proposal candidates require exactly one of quantity or notional."
        )
    if draft.quantity is not None and draft.quantity <= 0:
        raise ValueError("Proposal candidates require quantity greater than zero.")
    if draft.notional is not None and draft.notional <= 0:
        raise ValueError("Proposal candidates require notional greater than zero.")


def _candidate_side(score: IdeaScore) -> TradeSide | None:
    return cast(TradeSide, score.signal) if score.signal in {"buy", "sell"} else None


def _candidate_record(
    *,
    draft: ProposalCandidateDraft,
    score: IdeaScore,
    symbol: str,
    evidence: dict[str, object],
) -> ProposalCandidateRecord:
    now = utc_now_iso()
    return ProposalCandidateRecord(
        candidate_id=f"candidate-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
        symbol=symbol,
        preset=score.preset,
        signal=score.signal,
        side=_candidate_side(score),
        score=score.score,
        reference_price=draft.idea.price,
        confidence=min(max(score.score / 100.0, 0.0), 1.0),
        quantity=draft.quantity,
        notional=draft.notional,
        thesis=_safe_note(
            _candidate_thesis(draft=draft, score_reasons=list(score.reasons)),
            max_length=1000,
        ),
        stop_loss=draft.stop_loss,
        take_profit=draft.take_profit,
        invalidation_condition=draft.invalidation_condition,
        source=_safe_note(draft.source, max_length=120),
        materiality=_safe_note(
            draft.materiality or _default_materiality(score.score),
            max_length=300,
        ),
        freshness=_safe_note(draft.freshness, max_length=160),
        liquidity=_safe_note(
            draft.liquidity or _default_liquidity(draft.idea),
            max_length=300,
        ),
        spread_pct=draft.idea.spread_pct,
        risk_notes=_safe_note(
            draft.risk_notes or _default_risk_notes(score.warnings),
            max_length=500,
        ),
        evidence=evidence,
    )


def promote_proposal_candidate(
    *,
    db: TradingDatabase,
    candidate_id: str,
    review_notes: str = "",
) -> tuple[ProposalCandidateRecord, TradeProposalRecord]:
    """
    Promote a stored proposal candidate into an active trade proposal and return the updated candidate and its created proposal.

    Parameters:
        db (TradingDatabase): Database interface used to load, update, and persist records.
        candidate_id (str): Identifier of the candidate to promote.
        review_notes (str): Operator review notes appended to the proposal review payload.

    Returns:
        tuple[ProposalCandidateRecord, TradeProposalRecord]: The candidate record updated to `promoted` and the created trade proposal.

    Raises:
        ValueError: If the candidate is not found, is not in `candidate` status, is watch-only (no trade side), fails promotability validation, or if the candidate changes before promotion completes (promotion race).
    """
    candidate = db.get_proposal_candidate(candidate_id)
    if candidate is None:
        raise ValueError(f"Proposal candidate not found: {candidate_id}")
    if candidate.status != "candidate":
        raise ValueError(
            f"Proposal candidate {candidate_id} is already {candidate.status}."
        )
    _validate_candidate_promotable(candidate)
    side = candidate.side
    if side is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} is watch-only and cannot be promoted."
        )
    note = _promotion_review_notes(candidate, review_notes)
    proposal = prepare_trade_proposal(
        draft=TradeProposalDraft(
            symbol=candidate.symbol,
            side=side,
            quantity=candidate.quantity,
            notional=candidate.notional,
            reference_price=candidate.reference_price,
            confidence=candidate.confidence,
            thesis=candidate.thesis,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            invalidation_condition=candidate.invalidation_condition,
            source="proposal-candidate",
            review_notes=note,
        ),
    )
    promoted = candidate.model_copy(
        update={
            "status": "promoted",
            "updated_at": utc_now_iso(),
            "proposal_id": proposal.proposal_id,
            "evidence": {
                **candidate.evidence,
                "promoted_proposal_id": proposal.proposal_id,
            },
        }
    )
    if not db.promote_proposal_candidate_with_proposal(
        candidate=promoted,
        proposal=proposal,
    ):
        current = db.get_proposal_candidate(candidate_id)
        if current is not None and current.status == "promoted" and current.proposal_id:
            existing = db.get_trade_proposal(current.proposal_id)
            if existing is not None:
                return current, existing
        raise ValueError(
            f"Proposal candidate {candidate_id} changed before promotion completed."
        )
    return promoted, proposal


def _candidate_thesis(
    *, draft: ProposalCandidateDraft, score_reasons: list[str]
) -> str:
    """
    Compose the operator-facing thesis for a proposal candidate.

    If the draft includes a non-empty thesis (after trimming), that thesis is returned; otherwise a default thesis is built from the draft's preset and the provided score reasons (or the phrase "scanner score passed" when no reasons are given).

    Parameters:
        draft (ProposalCandidateDraft): The candidate draft containing an optional operator thesis and the preset name.
        score_reasons (list[str]): Explanatory reasons produced by scoring to include when building a default thesis.

    Returns:
        str: A thesis string suitable for operator display or storage.
    """
    thesis = draft.thesis.strip()
    if thesis:
        return thesis
    reasons = ", ".join(score_reasons) or "scanner score passed"
    return f"{draft.preset} scanner candidate: {reasons}."


def _default_materiality(score: float) -> str:
    """
    Map a numeric candidate score to a materiality label indicating priority.

    Parameters:
        score (float): Candidate score on a 0–100 scale.

    Returns:
        str: `'high_score_candidate'` if score >= 70, `'moderate_score_candidate'` if score >= 45, `'low_score_candidate'` otherwise.
    """
    if score >= 70:
        return "high_score_candidate"
    if score >= 45:
        return "moderate_score_candidate"
    return "low_score_candidate"


def _default_liquidity(candidate: IdeaCandidate) -> str:
    """
    Format a short liquidity summary string from an idea candidate's market metrics.

    Parameters:
        candidate (IdeaCandidate): Idea candidate containing `volume`, `relative_volume`, and `spread_pct`.

    Returns:
        str: A single-line summary like "volume=12345; relative_volume=1.23; spread_pct=0.45" with volume rounded to integer and the other values formatted to two decimal places.
    """
    return (
        f"volume={candidate.volume:.0f}; "
        f"relative_volume={candidate.relative_volume:.2f}; "
        f"spread_pct={candidate.spread_pct:.2f}"
    )


def _default_risk_notes(warnings: tuple[str, ...]) -> str:
    """
    Build a compact risk-notes string from scanner warnings.

    Parameters:
        warnings (tuple[str, ...]): Scanner warning identifiers or messages.

    Returns:
        A string equal to "no scanner warnings" when `warnings` is empty, otherwise
        "scanner_warnings=" followed by the warnings joined with commas.
    """
    if not warnings:
        return "no scanner warnings"
    return "scanner_warnings=" + ",".join(warnings)
