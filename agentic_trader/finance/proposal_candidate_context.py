from __future__ import annotations

from dataclasses import asdict
from typing import Protocol, cast

from agentic_trader.config import Settings
from agentic_trader.finance.ideas import IdeaCandidate, IdeaPresetName, score_candidate
from agentic_trader.finance.strategy_catalog import score_strategy_context
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
)
from agentic_trader.security import redact_sensitive_text, safe_exception_note
from agentic_trader.time_utils import utc_now_iso

BLOCKING_CANDIDATE_WARNINGS = {"invalid_price", "low_volume", "wide_spread"}
RESERVED_CANDIDATE_EVIDENCE_KEYS = {
    "authority",
    "blocking_warnings",
    "canonical_analysis",
}
TRUNCATED_PAYLOAD_MARKER = "<truncated>"


class CandidateEvidenceDraft(Protocol):
    @property
    def idea(self) -> IdeaCandidate: ...

    @property
    def preset(self) -> IdeaPresetName: ...

    @property
    def evidence(self) -> dict[str, object] | None: ...


def candidate_evidence(
    *,
    draft: CandidateEvidenceDraft,
    settings: Settings | None,
    enrich_provider_context: bool,
    fetch_provider_news: bool,
) -> dict[str, object]:
    score = score_candidate(draft.idea, draft.preset)
    strategy_context = score_strategy_context(score)
    evidence: dict[str, object] = {
        "idea": redacted_json_payload(asdict(draft.idea)),
        "score": redacted_json_payload(asdict(score)),
        "strategy": redacted_json_payload(strategy_context),
        "blocking_warnings": blocking_warnings(score.warnings),
        "authority": {
            "broker_access": False,
            "proposal_approval": False,
            "manual_review_required": True,
        },
    }
    if draft.evidence:
        draft_evidence = cast(dict[str, object], redacted_json_payload(draft.evidence))
        evidence.update(
            {
                key: value
                for key, value in draft_evidence.items()
                if key not in RESERVED_CANDIDATE_EVIDENCE_KEYS
            }
        )
    if settings is not None and enrich_provider_context:
        evidence["canonical_analysis"] = candidate_provider_context(
            draft=draft,
            settings=settings,
            fetch_provider_news=fetch_provider_news,
        )
    elif not enrich_provider_context:
        evidence["canonical_analysis"] = unavailable_provider_context(
            reason="provider_context_disabled",
            include_proposal_approval=True,
        )
    elif settings is None:
        evidence["canonical_analysis"] = unavailable_provider_context(
            reason="settings_not_supplied",
            include_proposal_approval=False,
        )
    return evidence


def unavailable_provider_context(
    *, reason: str, include_proposal_approval: bool
) -> dict[str, object]:
    policy: dict[str, object] = {
        "enabled": False,
        "reason": reason,
        "broker_access": False,
    }
    if include_proposal_approval:
        policy["proposal_approval"] = False
    return {"available": False, "policy": policy}


def candidate_provider_context(
    *,
    draft: CandidateEvidenceDraft,
    settings: Settings,
    fetch_provider_news: bool,
) -> dict[str, object]:
    try:
        canonical = build_canonical_analysis_snapshot(
            market_snapshot_from_idea(draft.idea),
            settings=settings,
            news_items=None if fetch_provider_news else [],
        )
    except Exception as exc:
        return {
            "available": False,
            "error": safe_exception_note("proposal_candidate_context", exc),
            "policy": provider_context_policy(fetch_provider_news),
        }
    return compact_canonical_analysis(
        canonical,
        fetch_provider_news=fetch_provider_news,
    )


def provider_context_policy(fetch_provider_news: bool) -> dict[str, object]:
    return {
        "enabled": True,
        "network_light_default": not fetch_provider_news,
        "fetch_provider_news": fetch_provider_news,
        "broker_access": False,
        "proposal_approval": False,
    }


def market_snapshot_from_idea(candidate: IdeaCandidate) -> MarketSnapshot:
    symbol = candidate.symbol.strip().upper()
    price = max(candidate.price, 0.01)
    ema_20 = candidate.sma_20 or candidate.ema_9 or candidate.vwap or price
    ema_50 = candidate.sma_50 or ema_20
    range_floor_pct = max(candidate.range_pct, candidate.spread_pct, 0.1)
    atr_14 = max(price * range_floor_pct / 100.0, 0.01)
    rsi = candidate.rsi if candidate.rsi is not None else 50.0
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
        rsi_14=rsi,
        volatility_20=max(range_floor_pct / 100.0, 0.0),
        return_5=candidate.change_pct / 100.0,
        return_20=(candidate.change_pct + candidate.gap_pct) / 100.0,
        volume_ratio_20=candidate.relative_volume,
        higher_timeframe="not_available",
        htf_last_close=price,
        htf_ema_20=ema_20,
        htf_ema_50=ema_50,
        htf_rsi_14=rsi,
        htf_return_5=candidate.change_pct / 100.0,
        mtf_alignment="mixed",
        mtf_confidence=0.0,
        bars_analyzed=1,
        context_pack=context_pack,
    )


def compact_canonical_analysis(
    canonical: CanonicalAnalysisSnapshot, *, fetch_provider_news: bool
) -> dict[str, object]:
    payload = {
        "available": True,
        "policy": provider_context_policy(fetch_provider_news),
        "generated_at": canonical.generated_at,
        "summary": canonical.summary,
        "completeness_score": canonical.completeness_score,
        "missing_sections": canonical.missing_sections,
        "market": compact_market_snapshot(canonical.market),
        "fundamental": compact_fundamental_snapshot(canonical.fundamental),
        "macro": compact_macro_snapshot(canonical.macro),
        "news_events": [
            compact_news_event(event) for event in canonical.news_events[:5]
        ],
        "disclosures": [
            compact_disclosure_event(event) for event in canonical.disclosures[:5]
        ],
        "source_attributions": [
            compact_attribution(attribution)
            for attribution in canonical.source_attributions[:12]
        ],
    }
    return cast(dict[str, object], redacted_json_payload(payload))


def compact_market_snapshot(snapshot: MarketDataSnapshot) -> dict[str, object]:
    return {
        "interval": snapshot.interval,
        "lookback": snapshot.lookback,
        "rows": snapshot.rows,
        "last_close": snapshot.last_close,
        "missing_fields": snapshot.missing_fields,
        "summary": snapshot.summary,
        "attribution": compact_attribution(snapshot.attribution),
    }


def compact_fundamental_snapshot(snapshot: FundamentalSnapshot) -> dict[str, object]:
    return {
        "summary": snapshot.summary,
        "missing_fields": snapshot.missing_fields,
        "attribution": compact_attribution(snapshot.attribution),
    }


def compact_macro_snapshot(snapshot: MacroSnapshot) -> dict[str, object]:
    return {
        "region": snapshot.region,
        "currency": snapshot.currency,
        "rates_bias": snapshot.rates_bias,
        "inflation_bias": snapshot.inflation_bias,
        "fx_risk": snapshot.fx_risk,
        "missing_fields": snapshot.missing_fields,
        "summary": snapshot.summary,
        "attribution": compact_attribution(snapshot.attribution),
    }


def compact_news_event(event: NewsEvent) -> dict[str, object]:
    return {
        "title": event.title,
        "source": event.source,
        "published_at": event.published_at,
        "category": event.category,
        "relevance_score": event.relevance_score,
        "url": event.url,
        "summary": event.summary,
        "attribution": compact_attribution(event.attribution),
    }


def compact_disclosure_event(event: DisclosureEvent) -> dict[str, object]:
    return {
        "title": event.title,
        "published_at": event.published_at,
        "disclosure_type": event.disclosure_type,
        "url": event.url,
        "summary": event.summary,
        "attribution": compact_attribution(event.attribution),
    }


def compact_attribution(attribution: DataSourceAttribution) -> dict[str, object]:
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


def blocking_warnings(warnings: tuple[str, ...]) -> list[str]:
    return sorted(
        warning for warning in warnings if warning in BLOCKING_CANDIDATE_WARNINGS
    )


def safe_note(value: object, *, max_length: int) -> str:
    return redact_sensitive_text(value, max_length=max_length).strip()


def redacted_json_payload(value: object, *, max_depth: int = 6) -> object:
    if max_depth <= 0:
        return TRUNCATED_PAYLOAD_MARKER
    if isinstance(value, dict):
        payload: dict[str, object] = {}
        for index, (key, item) in enumerate(cast(dict[object, object], value).items()):
            if index >= 100:
                payload[TRUNCATED_PAYLOAD_MARKER] = "additional keys omitted"
                break
            payload[safe_note(key, max_length=120)] = redacted_json_payload(
                item,
                max_depth=max_depth - 1,
            )
        return payload
    if isinstance(value, list | tuple):
        sequence = cast(list[object] | tuple[object, ...], value)
        items = [
            redacted_json_payload(item, max_depth=max_depth - 1)
            for item in sequence[:100]
        ]
        if len(sequence) > 100:
            items.append(TRUNCATED_PAYLOAD_MARKER)
        return items
    if isinstance(value, str):
        return safe_note(value, max_length=1000)
    if value is None or isinstance(value, bool | int | float):
        return value
    return safe_note(value, max_length=500)
