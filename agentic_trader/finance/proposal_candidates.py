from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast
from uuid import uuid4

from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.finance.ideas import (
    IdeaCandidate,
    IdeaPresetName,
    score_candidate,
)
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    create_trade_proposal,
    utc_now_iso,
)
from agentic_trader.finance.strategy_catalog import score_strategy_context
from agentic_trader.schemas import ProposalCandidateRecord, TradeProposalRecord, TradeSide
from agentic_trader.storage.db import TradingDatabase

BLOCKING_CANDIDATE_WARNINGS = {"invalid_price", "low_volume", "wide_spread"}


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
    *, db: TradingDatabase, draft: ProposalCandidateDraft
) -> ProposalCandidateRecord:
    score = score_candidate(draft.idea, draft.preset)
    symbol = score.symbol.strip().upper()
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Proposal candidates require a simple V1 US equity symbol.")
    if draft.quantity is not None and draft.notional is not None:
        raise ValueError("Proposal candidates require exactly one of quantity or notional.")
    side = (
        cast(TradeSide, score.signal)
        if score.signal in {"buy", "sell"}
        else None
    )
    confidence = min(max(score.score / 100.0, 0.0), 1.0)
    context = score_strategy_context(score)
    now = utc_now_iso()
    candidate = ProposalCandidateRecord(
        candidate_id=f"candidate-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
        symbol=symbol,
        preset=score.preset,
        signal=score.signal,
        side=side,
        score=score.score,
        reference_price=draft.idea.price,
        confidence=confidence,
        quantity=draft.quantity,
        notional=draft.notional,
        thesis=_candidate_thesis(draft=draft, score_reasons=list(score.reasons)),
        stop_loss=draft.stop_loss,
        take_profit=draft.take_profit,
        invalidation_condition=draft.invalidation_condition,
        source=draft.source,
        materiality=draft.materiality or _default_materiality(score.score),
        freshness=draft.freshness,
        liquidity=draft.liquidity or _default_liquidity(draft.idea),
        spread_pct=draft.idea.spread_pct,
        risk_notes=draft.risk_notes or _default_risk_notes(score.warnings),
        evidence={
            "idea": asdict(draft.idea),
            "score": asdict(score),
            "strategy": context,
            "blocking_warnings": _blocking_warnings(score.warnings),
            **(draft.evidence or {}),
        },
    )
    db.insert_proposal_candidate(candidate)
    return candidate


def promote_proposal_candidate(
    *,
    db: TradingDatabase,
    candidate_id: str,
    review_notes: str = "",
) -> tuple[ProposalCandidateRecord, TradeProposalRecord]:
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
    proposal = create_trade_proposal(
        db=db,
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
    db.update_proposal_candidate(promoted)
    return promoted, proposal


def _candidate_thesis(
    *, draft: ProposalCandidateDraft, score_reasons: list[str]
) -> str:
    thesis = draft.thesis.strip()
    if thesis:
        return thesis
    reasons = ", ".join(score_reasons) or "scanner score passed"
    return f"{draft.preset} scanner candidate: {reasons}."


def _default_materiality(score: float) -> str:
    if score >= 70:
        return "high_score_candidate"
    if score >= 45:
        return "moderate_score_candidate"
    return "low_score_candidate"


def _default_liquidity(candidate: IdeaCandidate) -> str:
    return (
        f"volume={candidate.volume:.0f}; "
        f"relative_volume={candidate.relative_volume:.2f}; "
        f"spread_pct={candidate.spread_pct:.2f}"
    )


def _default_risk_notes(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return "no scanner warnings"
    return "scanner_warnings=" + ",".join(warnings)


def _blocking_warnings(warnings: tuple[str, ...]) -> list[str]:
    return sorted(warning for warning in warnings if warning in BLOCKING_CANDIDATE_WARNINGS)


def _validate_candidate_promotable(candidate: ProposalCandidateRecord) -> None:
    raw_blockers: Any = candidate.evidence.get("blocking_warnings")
    blockers = raw_blockers if isinstance(raw_blockers, list) else []
    if blockers:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has blocking scanner warnings: "
            + ", ".join(str(item) for item in blockers)
        )
    if candidate.side is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} is watch-only and cannot be promoted."
        )
    if candidate.quantity is None and candidate.notional is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has no quantity or notional."
        )
    if candidate.stop_loss is None or candidate.take_profit is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has no stop_loss/take_profit controls."
        )


def _promotion_review_notes(
    candidate: ProposalCandidateRecord, review_notes: str
) -> str:
    parts = [
        f"candidate_id={candidate.candidate_id}",
        f"preset={candidate.preset}",
        f"score={candidate.score:.2f}",
        f"materiality={candidate.materiality}",
        f"freshness={candidate.freshness}",
        f"liquidity={candidate.liquidity}",
        f"risk_notes={candidate.risk_notes}",
    ]
    cleaned = review_notes.strip()
    if cleaned:
        parts.append(f"operator_notes={cleaned}")
    return " | ".join(parts)
