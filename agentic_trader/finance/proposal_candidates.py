from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.finance.ideas import (
    IdeaCandidate,
    IdeaPresetName,
    score_candidate,
)
from agentic_trader.finance.proposal_candidate_context import (
    candidate_evidence,
)
from agentic_trader.finance.proposal_candidate_context import safe_note as _safe_note
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    prepare_trade_proposal,
    utc_now_iso,
)
from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.json_utils import object_list as _object_list
from agentic_trader.schemas import (
    ProposalCandidateRecord,
    TradeProposalRecord,
    TradeSide,
)
from agentic_trader.storage.db import TradingDatabase

STALE_FRESHNESS_MARKERS = ("stale", "expired", "outdated", "unknown", "missing")


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
    """
    Create and persist a validated, scored proposal candidate enriched with optional provider context.

    Parameters:
        draft (ProposalCandidateDraft): Operator-provided inputs for the candidate (idea, sizing, risk controls, text fields, and optional evidence).
        settings (Settings | None): Optional provider settings used when enriching canonical provider context; if omitted, provider context will be marked unavailable.
        enrich_provider_context (bool): If True, attempt to include canonical provider analysis in the candidate's evidence; otherwise mark provider context as disabled.
        fetch_provider_news (bool): If True (and provider enrichment is enabled), request provider news items when building the canonical analysis snapshot.

    Returns:
        ProposalCandidateRecord: The inserted proposal candidate record, including computed score/confidence, normalized symbol, redacted text fields, assembled evidence, timestamps, and a generated candidate_id.

    """
    score = score_candidate(draft.idea, draft.preset)
    symbol = score.symbol.strip().upper()
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
    side = cast(TradeSide, score.signal) if score.signal in {"buy", "sell"} else None
    confidence = min(max(score.score / 100.0, 0.0), 1.0)
    evidence = candidate_evidence(
        draft=draft,
        settings=settings,
        enrich_provider_context=enrich_provider_context,
        fetch_provider_news=fetch_provider_news,
    )
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
    db.insert_proposal_candidate(candidate)
    return candidate


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


def _validate_candidate_promotable(candidate: ProposalCandidateRecord) -> None:
    """
    Run the full suite of promotability validations against a proposal candidate.

    This invokes blocker, sizing, evidence, and risk-geometry checks in order and raises a ValueError if any validation fails.
    """
    _validate_candidate_blockers(candidate)
    _validate_candidate_sizing(candidate)
    _validate_candidate_evidence(candidate)
    _validate_candidate_risk_geometry(candidate)


def _validate_candidate_blockers(candidate: ProposalCandidateRecord) -> None:
    """
    Ensure the candidate has no blocking scanner warnings and is not watch-only.

    Raises:
        ValueError: If `candidate.evidence["blocking_warnings"]` is a list with any entries (the error lists them), or if `candidate.side` is `None` indicating a watch-only candidate.
    """
    blockers = _object_list(candidate.evidence.get("blocking_warnings"))
    if blockers:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has blocking scanner warnings: "
            + ", ".join(str(item) for item in blockers)
        )
    if candidate.side is None:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} is watch-only and cannot be promoted."
        )


def _validate_candidate_sizing(candidate: ProposalCandidateRecord) -> None:
    """
    Validate that the candidate contains required sizing and risk-control values for promotion.

    Parameters:
        candidate (ProposalCandidateRecord): The proposal candidate to validate.

    Raises:
        ValueError: If both `quantity` and `notional` are missing; if `quantity` is present but <= 0; if `notional` is present but <= 0; or if either `stop_loss` or `take_profit` is missing.
    """
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


def _validate_candidate_evidence(candidate: ProposalCandidateRecord) -> None:
    """
    Ensure the candidate contains current freshness evidence and a positive reference price.

    Parameters:
        candidate (ProposalCandidateRecord): The proposal candidate to validate.

    Raises:
        ValueError: If the candidate's freshness evidence is missing or stale.
        ValueError: If the candidate's reference_price is less than or equal to zero.
    """
    if not _candidate_has_current_evidence(candidate):
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has stale or missing freshness evidence."
        )
    if candidate.reference_price <= 0:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} requires reference_price greater than zero."
        )


def _validate_candidate_risk_geometry(candidate: ProposalCandidateRecord) -> None:
    """
    Validate that the candidate's stop-loss and take-profit define a correct risk geometry for its trade side.

    Checks that both `stop_loss` and `take_profit` are present and, for a buy side, that stop_loss < reference_price < take_profit, or for a sell side, that take_profit < reference_price < stop_loss.

    Parameters:
        candidate (ProposalCandidateRecord): Candidate record whose risk controls and reference price will be validated.

    Raises:
        ValueError: If either stop-loss or take-profit is missing, or if the numeric relationship between stop-loss, reference price, and take-profit does not match the candidate's side.
    """
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


def _candidate_has_current_evidence(candidate: ProposalCandidateRecord) -> bool:
    """
    Determine whether a candidate's freshness field indicates current (non-stale) evidence.

    Parameters:
        candidate (ProposalCandidateRecord): The proposal candidate whose freshness metadata will be evaluated.

    Returns:
        bool: `True` if the candidate's `freshness` is non-empty and does not contain any substring listed in `STALE_FRESHNESS_MARKERS`, `False` otherwise.
    """
    freshness = candidate.freshness.strip().lower()
    if not freshness:
        return False
    return not any(marker in freshness for marker in STALE_FRESHNESS_MARKERS)


def _promotion_review_notes(
    candidate: ProposalCandidateRecord, review_notes: str
) -> str:
    """
    Constructs a single-line promotion review string summarizing key candidate metadata and optional operator notes.

    Parameters:
        candidate (ProposalCandidateRecord): The candidate whose identifying fields, score, materiality, freshness, liquidity, risk notes, and canonical-analysis metadata (if present) will be included.
        review_notes (str): Operator-provided freeform review notes; cleaned and truncated to 1000 chars before inclusion.

    Returns:
        str: A single string of parts joined with " | " containing candidate_id, preset, score, materiality, freshness, liquidity, risk_notes, optional `canonical_completeness` and `missing_sections`, and optional `operator_notes`.
    """
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
    canonical_payload = _object_mapping(canonical)
    if canonical_payload is not None:
        completeness = canonical_payload.get("completeness_score")
        if isinstance(completeness, int | float):
            parts.append(f"canonical_completeness={completeness:.2f}")
        missing_sections = _object_list(canonical_payload.get("missing_sections"))
        sections = ",".join(str(section) for section in missing_sections[:6])
        if sections:
            parts.append(f"missing_sections={sections}")
    cleaned = _safe_note(review_notes, max_length=1000).strip()
    if cleaned:
        parts.append(f"operator_notes={cleaned}")
    return " | ".join(parts)
