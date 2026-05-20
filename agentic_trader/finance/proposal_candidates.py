from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast
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
from agentic_trader.providers.aggregation import build_canonical_analysis_snapshot
from agentic_trader.security import redact_sensitive_text, safe_exception_note
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
from agentic_trader.storage.db import TradingDatabase

BLOCKING_CANDIDATE_WARNINGS = {"invalid_price", "low_volume", "wide_spread"}
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
    score = score_candidate(draft.idea, draft.preset)
    symbol = score.symbol.strip().upper()
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Proposal candidates require a simple V1 US equity symbol.")
    if draft.quantity is not None and draft.notional is not None:
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
        evidence.update(cast(dict[str, object], _redacted_json_payload(draft.evidence)))
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
    return {
        "enabled": True,
        "network_light_default": not fetch_provider_news,
        "fetch_provider_news": fetch_provider_news,
        "broker_access": False,
        "proposal_approval": False,
    }


def _market_snapshot_from_idea(candidate: IdeaCandidate) -> MarketSnapshot:
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
    return {
        "summary": snapshot.summary,
        "missing_fields": snapshot.missing_fields,
        "attribution": _compact_attribution(snapshot.attribution),
    }


def _compact_macro_snapshot(snapshot: MacroSnapshot) -> dict[str, object]:
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
    return {
        "title": event.title,
        "published_at": event.published_at,
        "disclosure_type": event.disclosure_type,
        "url": event.url,
        "summary": event.summary,
        "attribution": _compact_attribution(event.attribution),
    }


def _compact_attribution(attribution: DataSourceAttribution) -> dict[str, object]:
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
    return sorted(
        warning for warning in warnings if warning in BLOCKING_CANDIDATE_WARNINGS
    )


def _validate_candidate_promotable(candidate: ProposalCandidateRecord) -> None:
    _validate_candidate_blockers(candidate)
    _validate_candidate_sizing(candidate)
    _validate_candidate_evidence(candidate)
    _validate_candidate_risk_geometry(candidate)


def _validate_candidate_blockers(candidate: ProposalCandidateRecord) -> None:
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


def _validate_candidate_sizing(candidate: ProposalCandidateRecord) -> None:
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
    if not _candidate_has_current_evidence(candidate):
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} has stale or missing freshness evidence."
        )
    if candidate.reference_price <= 0:
        raise ValueError(
            f"Proposal candidate {candidate.candidate_id} requires reference_price greater than zero."
        )


def _validate_candidate_risk_geometry(candidate: ProposalCandidateRecord) -> None:
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
    freshness = candidate.freshness.strip().lower()
    if not freshness:
        return False
    return not any(marker in freshness for marker in STALE_FRESHNESS_MARKERS)


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
    canonical = candidate.evidence.get("canonical_analysis")
    if isinstance(canonical, dict):
        completeness = canonical.get("completeness_score")
        if isinstance(completeness, int | float):
            parts.append(f"canonical_completeness={completeness:.2f}")
        missing_sections = canonical.get("missing_sections")
        if isinstance(missing_sections, list):
            sections = ",".join(str(section) for section in missing_sections[:6])
            if sections:
                parts.append(f"missing_sections={sections}")
    cleaned = _safe_note(review_notes, max_length=1000).strip()
    if cleaned:
        parts.append(f"operator_notes={cleaned}")
    return " | ".join(parts)


def _safe_note(value: object, *, max_length: int) -> str:
    return redact_sensitive_text(value, max_length=max_length).strip()


def _redacted_json_payload(value: object, *, max_depth: int = 6) -> object:
    if max_depth <= 0:
        return TRUNCATED_PAYLOAD_MARKER
    if isinstance(value, dict):
        payload: dict[str, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 100:
                payload[TRUNCATED_PAYLOAD_MARKER] = "additional keys omitted"
                break
            payload[_safe_note(key, max_length=120)] = _redacted_json_payload(
                item,
                max_depth=max_depth - 1,
            )
        return payload
    if isinstance(value, list | tuple):
        items = [
            _redacted_json_payload(item, max_depth=max_depth - 1)
            for item in value[:100]
        ]
        if len(value) > 100:
            items.append(TRUNCATED_PAYLOAD_MARKER)
        return items
    if isinstance(value, str):
        return _safe_note(value, max_length=1000)
    if value is None or isinstance(value, bool | int | float):
        return value
    return _safe_note(value, max_length=500)
