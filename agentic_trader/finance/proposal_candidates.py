from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.finance.ideas import (
    IdeaCandidate,
    IdeaPresetName,
    score_candidate,
)
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    prepare_trade_proposal,
    utc_now_iso,
)
from agentic_trader.finance.strategy_catalog import score_strategy_context
from agentic_trader.json_utils import (
    object_dict_or_none as _object_mapping,
    object_list as _object_list,
)
from agentic_trader.providers.aggregation import build_canonical_analysis_snapshot
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
    DataSourceAttribution,
    DisclosureEvent,
    FundamentalSnapshot,
    MacroSnapshot,
    MarketContextPack,
    MarketDataSnapshot,
    MarketSnapshot,
    NewsEvent,
    ProposalCandidateRecord,
    TradeProposalRecord,
    TradeSide,
)
from agentic_trader.security import redact_sensitive_text, safe_exception_note
from agentic_trader.storage.db import TradingDatabase

BLOCKING_CANDIDATE_WARNINGS = {"invalid_price", "low_volume", "wide_spread"}
RESERVED_CANDIDATE_EVIDENCE_KEYS = {
    "authority",
    "blocking_warnings",
    "canonical_analysis",
}
STALE_FRESHNESS_MARKERS = ("stale", "expired", "outdated", "unknown", "missing")
TRUNCATED_PAYLOAD_MARKER = "<truncated>"


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
    context = score_strategy_context(score)
    evidence = _candidate_evidence(
        draft=draft,
        strategy_context=context,
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


def _candidate_evidence(
    *,
    draft: ProposalCandidateDraft,
    strategy_context: dict[str, object],
    settings: Settings | None,
    enrich_provider_context: bool,
    fetch_provider_news: bool,
) -> dict[str, object]:
    """
    Assemble structured, redacted evidence for a proposal candidate, optionally enriched with a canonical provider analysis.

    Parameters:
        draft: The operator/scanner-provided ProposalCandidateDraft used to build evidence.
        strategy_context: Derived strategy metadata to include with the candidate (already compacted/redacted).
        settings: Optional Settings used to request provider canonical analysis; when None, provider context is marked unavailable.
        enrich_provider_context: If True, attempt to include canonical provider analysis (subject to `settings`); if False, canonical analysis is marked unavailable with a disabled policy.
        fetch_provider_news: If True and provider enrichment is requested, allow the provider analysis call to fetch news items; otherwise request a lighter network policy.

    Returns:
        dict containing redacted evidence for the candidate. Typical top-level keys:
          - "idea": redacted idea payload
          - "score": redacted scoring payload
          - "strategy": redacted strategy context
          - "blocking_warnings": list of blocking scanner warnings (may be empty)
          - "authority": policy flags for broker/proposal/manual review
          - optionally merged redacted `draft.evidence`
          - "canonical_analysis": either a compacted canonical analysis dict when available, or a dict with `"available": False` and a `policy` explaining why it is unavailable.
    """
    score = score_candidate(draft.idea, draft.preset)
    evidence: dict[str, object] = {
        "idea": _redacted_json_payload(asdict(draft.idea)),
        "score": _redacted_json_payload(asdict(score)),
        "strategy": _redacted_json_payload(strategy_context),
        "blocking_warnings": _blocking_warnings(score.warnings),
        "authority": {
            "broker_access": False,
            "proposal_approval": False,
            "manual_review_required": True,
        },
    }
    if draft.evidence:
        draft_evidence = cast(dict[str, object], _redacted_json_payload(draft.evidence))
        evidence.update(
            {
                key: value
                for key, value in draft_evidence.items()
                if key not in RESERVED_CANDIDATE_EVIDENCE_KEYS
            }
        )
    if settings is not None and enrich_provider_context:
        evidence["canonical_analysis"] = _candidate_provider_context(
            draft=draft,
            settings=settings,
            fetch_provider_news=fetch_provider_news,
        )
    elif not enrich_provider_context:
        evidence["canonical_analysis"] = {
            "available": False,
            "policy": {
                "enabled": False,
                "reason": "provider_context_disabled",
                "broker_access": False,
                "proposal_approval": False,
            },
        }
    elif settings is None:
        evidence["canonical_analysis"] = {
            "available": False,
            "policy": {
                "enabled": False,
                "reason": "settings_not_supplied",
                "broker_access": False,
            },
        }
    return evidence


def _candidate_provider_context(
    *,
    draft: ProposalCandidateDraft,
    settings: Settings,
    fetch_provider_news: bool,
) -> dict[str, object]:
    """
    Build a canonical provider analysis snapshot for the given candidate and return a compact, redacted representation suitable for storage.

    If provider snapshot construction succeeds, returns a compacted canonical analysis payload (as produced by the module's compaction helpers) optionally including news. If construction raises an exception, returns a dict with "available": False, an "error" note describing the failure, and a "policy" entry describing provider-context settings.

    Parameters:
        draft (ProposalCandidateDraft): Candidate inputs used to synthesize the market snapshot.
        settings (Settings): Provider settings and credentials used to build the canonical analysis.
        fetch_provider_news (bool): When True, allow the snapshot to include provider news items; when False, request the snapshot without news.

    Returns:
        dict[str, object]: Either a compacted canonical analysis payload, or an availability object of the form:
            {
                "available": False,
                "error": <string error note>,
                "policy": <policy dict>
            }
    """
    try:
        canonical = build_canonical_analysis_snapshot(
            _market_snapshot_from_idea(draft.idea),
            settings=settings,
            news_items=None if fetch_provider_news else [],
        )
    except Exception as exc:
        return {
            "available": False,
            "error": safe_exception_note("proposal_candidate_context", exc),
            "policy": _provider_context_policy(fetch_provider_news),
        }
    return _compact_canonical_analysis(
        canonical,
        fetch_provider_news=fetch_provider_news,
    )


def _provider_context_policy(fetch_provider_news: bool) -> dict[str, object]:
    """
    Builds a policy dictionary that controls how provider canonical analysis is requested.

    Parameters:
        fetch_provider_news (bool): If True, the policy enables fetching provider news; if False, it prefers a lighter network policy.

    Returns:
        dict[str, object]: Policy flags including:
            - "enabled": whether provider context is allowed.
            - "network_light_default": True when news fetching is not requested.
            - "fetch_provider_news": reflects the input parameter.
            - "broker_access": whether broker-level access is permitted (always False).
            - "proposal_approval": whether provider context can approve proposals (always False).
    """
    return {
        "enabled": True,
        "network_light_default": not fetch_provider_news,
        "fetch_provider_news": fetch_provider_news,
        "broker_access": False,
        "proposal_approval": False,
    }


def _market_snapshot_from_idea(candidate: IdeaCandidate) -> MarketSnapshot:
    """
    Synthesize a minimal MarketSnapshot suitable for provider-context building from scanner/operator idea inputs.

    Constructs a compact market snapshot for the given candidate where missing or potentially invalid inputs are safely defaulted:
    - Normalizes the symbol to upper-case without surrounding whitespace.
    - Ensures a sensible price floor (at least 0.01) and computes EMA and ATR values using available moving-average-like inputs with sensible fallbacks.
    - Sets RSI to the candidate value when provided, otherwise 50.0.
    - Derives volatility and short-term returns from the candidate's percent fields.
    - Marks higher-timeframe data as not available while providing aligned synthesized higher-timeframe metrics (last_close, ema_20, ema_50, rsi).
    - Includes a MarketContextPack indicating this is a single "scanner" candidate snapshot and that the data was synthesized.

    Parameters:
        candidate (IdeaCandidate): Operator/scanner-supplied idea used to synthesize the snapshot.

    Returns:
        MarketSnapshot: A compact, self-contained market snapshot with normalized symbol, derived price/indicator fields, synthesized higher-timeframe alignment, and an attached context pack describing the snapshot provenance.
    """
    symbol = candidate.symbol.strip().upper()
    price = max(candidate.price, 0.01)
    ema_20 = candidate.sma_20 or candidate.ema_9 or candidate.vwap or price
    ema_50 = candidate.sma_50 or ema_20
    range_floor_pct = max(candidate.range_pct, candidate.spread_pct, 0.1)
    atr_14 = max(price * range_floor_pct / 100.0, 0.01)
    context_pack = MarketContextPack(
        symbol=symbol,
        interval="scanner",
        lookback="scanner_input",
        interval_semantics="single_scanner_candidate",
        bars_required=1,
        bars_expected=1,
        bars_analyzed=1,
        coverage_ratio=1.0,
        higher_timeframe="not_available",
        higher_timeframe_used=False,
        data_quality_flags=["scanner_input_only", "not_provider_price_window"],
        summary=(
            "Proposal candidate context was synthesized from operator/scanner "
            "inputs and should be verified before approval."
        ),
    )
    return MarketSnapshot(
        symbol=symbol,
        interval="scanner",
        as_of=utc_now_iso(),
        last_close=price,
        ema_20=ema_20,
        ema_50=ema_50,
        atr_14=atr_14,
        rsi_14=candidate.rsi if candidate.rsi is not None else 50.0,
        volatility_20=max(range_floor_pct / 100.0, 0.0),
        return_5=candidate.change_pct / 100.0,
        return_20=(candidate.change_pct + candidate.gap_pct) / 100.0,
        volume_ratio_20=candidate.relative_volume,
        higher_timeframe="not_available",
        htf_last_close=price,
        htf_ema_20=ema_20,
        htf_ema_50=ema_50,
        htf_rsi_14=candidate.rsi if candidate.rsi is not None else 50.0,
        htf_return_5=candidate.change_pct / 100.0,
        mtf_alignment="mixed",
        mtf_confidence=0.0,
        bars_analyzed=1,
        context_pack=context_pack,
    )


def _compact_canonical_analysis(
    canonical: CanonicalAnalysisSnapshot, *, fetch_provider_news: bool
) -> dict[str, object]:
    """
    Create a compact, redacted representation of a canonical analysis snapshot suitable for storage as candidate evidence.

    Parameters:
        canonical (CanonicalAnalysisSnapshot): The full canonical analysis snapshot to compact.
        fetch_provider_news (bool): Whether provider-news fetching was requested; influences the included `policy` block.

    Returns:
        dict[str, object]: A redacted JSON-like payload containing:
            - `available`: availability flag
            - `policy`: provider context policy
            - `generated_at`, `summary`, `completeness_score`, `missing_sections`
            - `market`, `fundamental`, `macro`: compacted snapshot sections
            - `news_events`: up to 5 compacted news events
            - `disclosures`: up to 5 compacted disclosure events
            - `source_attributions`: up to 12 compacted attributions

    The returned payload is truncated and redacted to remove sensitive or overly large content.
    """
    payload = {
        "available": True,
        "policy": _provider_context_policy(fetch_provider_news),
        "generated_at": canonical.generated_at,
        "summary": canonical.summary,
        "completeness_score": canonical.completeness_score,
        "missing_sections": canonical.missing_sections,
        "market": _compact_market_snapshot(canonical.market),
        "fundamental": _compact_fundamental_snapshot(canonical.fundamental),
        "macro": _compact_macro_snapshot(canonical.macro),
        "news_events": [
            _compact_news_event(event) for event in canonical.news_events[:5]
        ],
        "disclosures": [
            _compact_disclosure_event(event) for event in canonical.disclosures[:5]
        ],
        "source_attributions": [
            _compact_attribution(attribution)
            for attribution in canonical.source_attributions[:12]
        ],
    }
    return cast(dict[str, object], _redacted_json_payload(payload))


def _compact_market_snapshot(snapshot: MarketDataSnapshot) -> dict[str, object]:
    """
    Create a compact dictionary representation of a MarketDataSnapshot suitable for storage or inclusion in a larger payload.

    Parameters:
        snapshot (MarketDataSnapshot): The market snapshot to compact; expected to provide `interval`, `lookback`, `rows`, `last_close`, `missing_fields`, `summary`, and `attribution` attributes.

    Returns:
        dict[str, object]: A reduced mapping containing `interval`, `lookback`, `rows`, `last_close`, `missing_fields`, `summary`, and a compacted `attribution`.
    """
    return {
        "interval": snapshot.interval,
        "lookback": snapshot.lookback,
        "rows": snapshot.rows,
        "last_close": snapshot.last_close,
        "missing_fields": snapshot.missing_fields,
        "summary": snapshot.summary,
        "attribution": _compact_attribution(snapshot.attribution),
    }


def _compact_fundamental_snapshot(
    snapshot: FundamentalSnapshot,
) -> dict[str, object]:
    """
    Produce a compact JSON-serializable representation of a FundamentalSnapshot.

    Parameters:
        snapshot (FundamentalSnapshot): The full fundamental snapshot to compact.

    Returns:
        dict[str, object]: A reduced mapping with keys:
            - "summary": brief textual summary of fundamentals,
            - "missing_fields": list of missing fundamental fields,
            - "attribution": compacted attribution metadata suitable for storage.
    """
    return {
        "summary": snapshot.summary,
        "missing_fields": snapshot.missing_fields,
        "attribution": _compact_attribution(snapshot.attribution),
    }


def _compact_macro_snapshot(snapshot: MacroSnapshot) -> dict[str, object]:
    """
    Produce a compact mapping of selected macroeconomic fields from a MacroSnapshot.

    Returns:
        dict[str, object]: A dictionary with keys `region`, `currency`, `rates_bias`, `inflation_bias`,
        `fx_risk`, `missing_fields`, `summary`, and `attribution` (the attribution is the result of
        `_compact_attribution`).
    """
    return {
        "region": snapshot.region,
        "currency": snapshot.currency,
        "rates_bias": snapshot.rates_bias,
        "inflation_bias": snapshot.inflation_bias,
        "fx_risk": snapshot.fx_risk,
        "missing_fields": snapshot.missing_fields,
        "summary": snapshot.summary,
        "attribution": _compact_attribution(snapshot.attribution),
    }


def _compact_news_event(event: NewsEvent) -> dict[str, object]:
    """
    Create a compact, serializable representation of a NewsEvent for storage or inclusion in proposal evidence.

    Parameters:
        event (NewsEvent): The source news event to compact.

    Returns:
        dict[str, object]: A reduced news-event dictionary containing `title`, `source`, `published_at`, `category`, `relevance_score`, `url`, `summary`, and a compacted `attribution`.
    """
    return {
        "title": event.title,
        "source": event.source,
        "published_at": event.published_at,
        "category": event.category,
        "relevance_score": event.relevance_score,
        "url": event.url,
        "summary": event.summary,
        "attribution": _compact_attribution(event.attribution),
    }


def _compact_disclosure_event(event: DisclosureEvent) -> dict[str, object]:
    """
    Create a compact dictionary containing key fields from a DisclosureEvent.

    Parameters:
        event (DisclosureEvent): The disclosure event to compact.

    Returns:
        dict[str, object]: A dictionary with the keys `title`, `published_at`, `disclosure_type`, `url`, `summary`, and `attribution` (the attribution value is a compacted attribution dict).
    """
    return {
        "title": event.title,
        "published_at": event.published_at,
        "disclosure_type": event.disclosure_type,
        "url": event.url,
        "summary": event.summary,
        "attribution": _compact_attribution(event.attribution),
    }


def _compact_attribution(attribution: DataSourceAttribution) -> dict[str, object]:
    """
    Create a compact, storage-friendly dict from a DataSourceAttribution.

    Parameters:
        attribution (DataSourceAttribution): Attribution record to compact.

    Returns:
        dict[str, object]: A reduced attribution dictionary containing:
            - `source_name`, `provider_type`, `source_role`: identity fields.
            - `fetched_at`, `freshness`: timing/freshness metadata.
            - `confidence`, `completeness`: numeric quality metrics.
            - `notes`: up to the first 8 note entries from the original attribution.
    """
    return {
        "source_name": attribution.source_name,
        "provider_type": attribution.provider_type,
        "source_role": attribution.source_role,
        "fetched_at": attribution.fetched_at,
        "freshness": attribution.freshness,
        "confidence": attribution.confidence,
        "completeness": attribution.completeness,
        "notes": attribution.notes[:8],
    }


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


def _blocking_warnings(warnings: tuple[str, ...]) -> list[str]:
    """
    Filter the provided warnings to those classified as blocking for candidate promotion and return them sorted.

    Parameters:
        warnings (tuple[str, ...]): Sequence of warning identifiers to evaluate.

    Returns:
        list[str]: Sorted list of warnings that are considered blocking for promotion.
    """
    return sorted(
        warning for warning in warnings if warning in BLOCKING_CANDIDATE_WARNINGS
    )


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


def _safe_note(value: object, *, max_length: int) -> str:
    """
    Produce a redacted, length-limited plain-text note suitable for storage or display.

    Parameters:
        value (object): Input value to redact and truncate; may be any JSON-like object or string.
        max_length (int): Maximum length of the returned string in characters.

    Returns:
        str: A trimmed string containing the redacted and truncated representation of `value`.
    """
    return redact_sensitive_text(value, max_length=max_length).strip()


def _redacted_json_payload(value: object, *, max_depth: int = 6) -> object:
    """
    Produce a redacted and size-limited JSON-serializable representation of `value` suitable for storage or logging.

    This function:
    - Returns the string TRUNCATED_PAYLOAD_MARKER when `max_depth <= 0`.
    - For dicts: includes up to 100 keys (remaining keys replaced by a truncation marker), redacts keys and recursively processes values with `max_depth - 1`.
    - For lists/tuples: includes up to 100 items, recursively processed with `max_depth - 1`; appends a truncation marker if more items exist.
    - For strings: returns a redacted/truncated string (max length ~1000).
    - For None, bool, int, float: returns the value unchanged.
    - For other object types: returns a redacted string representation (max length ~500).

    Parameters:
        value (object): The input object to redact and compact.
        max_depth (int): Maximum recursive depth to traverse; when 0 or below the payload is replaced by the truncation marker.

    Returns:
        object: A JSON-serializable, redacted, and truncated representation of `value`.
    """
    if max_depth <= 0:
        return TRUNCATED_PAYLOAD_MARKER
    if isinstance(value, dict):
        payload: dict[str, object] = {}
        for index, (key, item) in enumerate(cast(dict[object, object], value).items()):
            if index >= 100:
                payload[TRUNCATED_PAYLOAD_MARKER] = "additional keys omitted"
                break
            payload[_safe_note(key, max_length=120)] = _redacted_json_payload(
                item,
                max_depth=max_depth - 1,
            )
        return payload
    if isinstance(value, list | tuple):
        sequence = cast(list[object] | tuple[object, ...], value)
        items = [
            _redacted_json_payload(item, max_depth=max_depth - 1)
            for item in sequence[:100]
        ]
        if len(sequence) > 100:
            items.append(TRUNCATED_PAYLOAD_MARKER)
        return items
    if isinstance(value, str):
        return _safe_note(value, max_length=1000)
    if value is None or isinstance(value, bool | int | float):
        return value
    return _safe_note(value, max_length=500)
