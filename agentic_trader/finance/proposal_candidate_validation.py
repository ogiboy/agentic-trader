from __future__ import annotations

from agentic_trader.finance.proposal_candidate_context import safe_note
from agentic_trader.json_utils import object_dict_or_none as object_mapping
from agentic_trader.json_utils import object_list
from agentic_trader.schemas import ProposalCandidateRecord

STALE_FRESHNESS_MARKERS = ("stale", "expired", "outdated", "unknown", "missing")


def validate_candidate_promotable(candidate: ProposalCandidateRecord) -> None:
    validate_candidate_blockers(candidate)
    validate_candidate_sizing(candidate)
    validate_candidate_evidence(candidate)
    validate_candidate_risk_geometry(candidate)


def validate_candidate_blockers(candidate: ProposalCandidateRecord) -> None:
    blockers = object_list(candidate.evidence.get("blocking_warnings"))
    if blockers:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has blocking scanner warnings: "
            + ", ".join(str(item) for item in blockers)
        )
    if candidate.side is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} is watch-only and cannot be promoted."
        )


def validate_candidate_sizing(candidate: ProposalCandidateRecord) -> None:
    if candidate.quantity is None and candidate.notional is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has no quantity or notional."
        )
    if candidate.quantity is not None and candidate.quantity <= 0:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} requires quantity greater than zero."
        )
    if candidate.notional is not None and candidate.notional <= 0:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} requires notional greater than zero."
        )
    if candidate.stop_loss is None or candidate.take_profit is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has no stop_loss/take_profit controls."
        )


def validate_candidate_evidence(candidate: ProposalCandidateRecord) -> None:
    if not candidate_has_current_evidence(candidate):
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has stale or missing freshness evidence."
        )
    if candidate.reference_price <= 0:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} requires reference_price greater than zero."
        )


def validate_candidate_risk_geometry(candidate: ProposalCandidateRecord) -> None:
    stop_loss = candidate.stop_loss
    take_profit = candidate.take_profit
    if stop_loss is None or take_profit is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has no stop_loss/take_profit controls."
        )
    if candidate.side == "buy" and not (
        stop_loss < candidate.reference_price < take_profit
    ):
        raise ValueError(
            "Buy proposal candidate risk controls must satisfy "
            "stop_loss < reference_price < take_profit."
        )
    if candidate.side == "sell" and not (
        take_profit < candidate.reference_price < stop_loss
    ):
        raise ValueError(
            "Sell proposal candidate risk controls must satisfy "
            "take_profit < reference_price < stop_loss."
        )


def candidate_has_current_evidence(candidate: ProposalCandidateRecord) -> bool:
    freshness = candidate.freshness.strip().lower()
    if not freshness:
        return False
    return not any(marker in freshness for marker in STALE_FRESHNESS_MARKERS)


def promotion_review_notes(
    candidate: ProposalCandidateRecord,
    review_notes: str,
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
    canonical = candidate.evidence.get("canonical_analysis")
    canonical_payload = object_mapping(canonical)
    if canonical_payload is not None:
        completeness = canonical_payload.get("completeness_score")
        if isinstance(completeness, int | float):
            parts.append(f"canonical_completeness={completeness:.2f}")
        missing_sections = object_list(canonical_payload.get("missing_sections"))
        sections = ",".join(str(section) for section in missing_sections[:6])
        if sections:
            parts.append(f"missing_sections={sections}")
    cleaned = safe_note(review_notes, max_length=1000).strip()
    if cleaned:
        parts.append(f"operator_notes={cleaned}")
    return " | ".join(parts)


__all__ = (
    "candidate_has_current_evidence",
    "promotion_review_notes",
    "validate_candidate_promotable",
)
