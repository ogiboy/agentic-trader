"""Repo-native strategy catalog and readiness helpers for V1 paper research."""

from __future__ import annotations

from agentic_trader.finance.ideas import IdeaPresetName, IdeaScore
from agentic_trader.finance.strategy_catalog_data import (
    LEDGER_CATEGORIES,
    STRATEGY_PROFILES,
)
from agentic_trader.finance.strategy_catalog_data import (
    FinanceLedgerCategory as FinanceLedgerCategory,
)
from agentic_trader.finance.strategy_catalog_data import (
    ReadinessState,
)
from agentic_trader.finance.strategy_catalog_data import (
    StrategyFamily as StrategyFamily,
)
from agentic_trader.finance.strategy_catalog_data import (
    StrategyProfile,
    StrategyStatus,
)
from agentic_trader.payloads import dataclass_payload


def list_strategy_profiles(
    *, status: StrategyStatus | None = None, preset: IdeaPresetName | None = None
) -> list[StrategyProfile]:
    profiles = list(STRATEGY_PROFILES)
    if status is not None:
        profiles = [profile for profile in profiles if profile.status == status]
    if preset is not None:
        profiles = [profile for profile in profiles if preset in profile.idea_presets]
    return profiles


def get_strategy_profile(name: str) -> StrategyProfile:
    normalized = name.strip().lower().replace("_", "-")
    for profile in STRATEGY_PROFILES:
        if profile.name == normalized:
            return profile
    known = ", ".join(profile.name for profile in STRATEGY_PROFILES)
    raise ValueError(f"Unknown strategy profile {name!r}. Known profiles: {known}")


def strategy_profile_for_preset(preset: IdeaPresetName) -> StrategyProfile:
    for profile in STRATEGY_PROFILES:
        if preset in profile.idea_presets:
            return profile
    raise ValueError(f"No strategy profile maps to preset {preset!r}")


def strategy_profile_payload(profile: StrategyProfile) -> dict[str, object]:
    return dataclass_payload(profile)


def finance_ledger_category_payload(
    category: FinanceLedgerCategory,
) -> dict[str, object]:
    return dataclass_payload(category)


def strategy_catalog_payload(
    *, status: StrategyStatus | None = None, preset: IdeaPresetName | None = None
) -> dict[str, object]:
    profiles = list_strategy_profiles(status=status, preset=preset)
    return {
        "profiles": [strategy_profile_payload(profile) for profile in profiles],
        "filters": {"status": status, "preset": preset},
        "execution_policy": (
            "strategy catalog entries are research/readiness metadata; all trade "
            "ideas still require proposal-create and explicit approval"
        ),
        "validation_policy": {
            "no_lookahead_required": True,
            "sweep_confidence_required_for_research_candidates": True,
            "raw_external_runtime_not_imported": True,
        },
    }


def score_strategy_context(score: IdeaScore) -> dict[str, object]:
    profile = strategy_profile_for_preset(score.preset)
    blocking_warnings = sorted(
        warning
        for warning in score.warnings
        if warning in {"low_volume", "wide_spread", "invalid_price"}
    )
    state: ReadinessState = (
        "watch_only" if score.signal == "watch" else "needs_evidence"
    )
    return {
        "strategy_profile": strategy_profile_payload(profile),
        "proposal_readiness": {
            "state": state,
            "proposal_candidate": False,
            "blocking_warnings": blocking_warnings,
            "missing_evidence": list(profile.evidence_requirements),
            "required_risk_controls": list(profile.risk_controls),
            "next_action": (
                "keep_on_watchlist"
                if state == "watch_only"
                else "enrich_with_news_provider_liquidity_and_fundamental_context"
            ),
            "manual_approval_required": True,
        },
    }


def finance_reconciliation_contract_payload() -> dict[str, object]:
    return {
        "ledger_categories": [
            finance_ledger_category_payload(category) for category in LEDGER_CATEGORIES
        ],
        "v1_policy": {
            "mode": "paper",
            "missing_evidence_policy": (
                "missing evidence must stay explicit and never be treated as zero"
            ),
            "known_missing_categories": [
                "dividends",
                "interest",
                "corporate_actions",
            ],
        },
        "audit_policy": {
            "preserve_source_ids": True,
            "distinguish_zero_from_missing": True,
            "reconcile_before_performance_claims": True,
        },
    }
