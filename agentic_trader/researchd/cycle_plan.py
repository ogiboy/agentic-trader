"""Continuous research cycle plan for the local paper desk.

The plan is an operator/runtime contract, not an autonomous trading executor. It shows
how the existing safe commands compose into a PRE-FLIGHT -> MONITOR -> ANALYZE
-> PROPOSE -> DIGEST loop while keeping proposals manual and broker access out
of sidecar/news/scanner paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentic_trader.payloads import dataclass_payload

CyclePhaseName = Literal["PRE-FLIGHT", "MONITOR", "ANALYZE", "PROPOSE", "DIGEST"]


@dataclass(frozen=True)
class ResearchCyclePhase:
    name: CyclePhaseName
    purpose: str
    read_commands: tuple[str, ...]
    produce: tuple[str, ...]
    fail_closed_on: tuple[str, ...]
    forbidden: tuple[str, ...]


DEFAULT_SCAN_PRESETS = (
    "momentum",
    "mean-reversion",
    "breakout",
    "volatile",
    "gap-up",
    "gap-down",
)

RESEARCH_CYCLE_PHASES: tuple[ResearchCyclePhase, ...] = (
    ResearchCyclePhase(
        name="PRE-FLIGHT",
        purpose="Verify paper-operation, provider/source, broker, and sidecar health before spending research budget.",
        read_commands=(
            "agentic-trader v1-readiness --json",
            "agentic-trader provider-diagnostics --json",
            "agentic-trader finance-ops --json",
            "agentic-trader broker-status --json",
            "agentic-trader research-status --json",
        ),
        produce=("cycle_preflight_state", "blocking_gate_list"),
        fail_closed_on=(
            "live_execution_enabled",
            "broker_health_missing",
            "non_paper_backend_without_explicit_external_paper_readiness",
            "provider_or_sidecar_error_hidden",
        ),
        forbidden=("broker_submit", "policy_mutation", "raw_web_prompt_injection"),
    ),
    ResearchCyclePhase(
        name="MONITOR",
        purpose="Observe portfolio, proposal queue, source health, and watchlist changes without asking the model to reason deeply yet.",
        read_commands=(
            "agentic-trader dashboard-snapshot",
            "agentic-trader trade-proposals --json",
            "agentic-trader risk-report --json",
            "agentic-trader news-intelligence --symbol <SYMBOL> --json",
        ),
        produce=(
            "watchlist_monitor_summary",
            "source_health_delta",
            "proposal_queue_state",
        ),
        fail_closed_on=(
            "dashboard_unavailable",
            "unredacted_provider_error",
            "news_plan_missing_source_policy",
        ),
        forbidden=(
            "create_trade_without_operator_thesis",
            "ignore_pending_terminal_state",
        ),
    ),
    ResearchCyclePhase(
        name="ANALYZE",
        purpose="Score ideas, attach strategy readiness, and decide what still needs evidence before a proposal can exist.",
        read_commands=(
            "agentic-trader idea-presets --json",
            "agentic-trader strategy-catalog --json",
            "agentic-trader idea-score --symbol <SYMBOL> --preset <PRESET> ... --json",
            "agentic-trader research-refresh --json",
        ),
        produce=(
            "idea_score_cards",
            "missing_evidence_list",
            "strategy_readiness_context",
        ),
        fail_closed_on=(
            "scanner_warning_unreviewed",
            "freshness_unknown_for_event_trade",
            "single_source_material_claim",
        ),
        forbidden=("treat_score_as_order", "bypass_proposal_queue"),
    ),
    ResearchCyclePhase(
        name="PROPOSE",
        purpose="Let an operator convert enriched ideas into pending proposals; the cycle itself never approves.",
        read_commands=(
            "agentic-trader proposal-create ... --json",
            "agentic-trader trade-proposals --status pending --json",
        ),
        produce=("pending_trade_proposal", "operator_review_packet"),
        fail_closed_on=(
            "missing_quantity_or_notional",
            "missing_manual_thesis",
            "wide_spread_or_low_volume_unaccepted",
        ),
        forbidden=(
            "proposal_approve",
            "broker_submit",
            "implicit_web_or_chat_approval",
        ),
    ),
    ResearchCyclePhase(
        name="DIGEST",
        purpose="Persist a compact review trail and next-watch list without mutating trading memory silently.",
        read_commands=(
            "agentic-trader evidence-bundle --json",
            "agentic-trader research-status --json",
            "agentic-trader trade-proposals --json",
        ),
        produce=("cycle_digest", "watch_next", "qa_or_evidence_bundle_reference"),
        fail_closed_on=("evidence_bundle_error", "secret_leak_in_artifact"),
        forbidden=("silent_memory_write", "hide_missing_sources"),
    ),
)


def research_cycle_phase_payload(phase: ResearchCyclePhase) -> dict[str, object]:
    """
    Convert a ResearchCyclePhase into a payload dictionary suitable for inclusion in the cycle plan.
    
    Parameters:
        phase (ResearchCyclePhase): The immutable phase definition to convert.
    
    Returns:
        dict[str, object]: A dictionary mapping the phase's fields (e.g., name, purpose, read_commands, produce, fail_closed_on, forbidden) to their serializable values.
    """
    return dataclass_payload(phase)


def research_cycle_plan_payload(
    *, symbols: list[str], cadence_seconds: int, max_proposals_per_cycle: int = 1
) -> dict[str, object]:
    """
    Builds a research cycle plan payload for the given watchlist and cadence.
    
    Cleans and normalizes inputs, then returns a dict describing the fixed PRE-FLIGHT → MONITOR → ANALYZE → PROPOSE → DIGEST cycle, its phases, safety policy, and operator controls.
    
    Parameters:
        symbols (list[str]): Watchlist symbols; each symbol is stripped of surrounding whitespace and uppercased. Empty or whitespace-only symbols are removed.
        cadence_seconds (int): Desired cycle cadence in seconds; values below 60 are normalized to 60.
        max_proposals_per_cycle (int): Maximum number of proposals allowed per cycle; negative values are normalized to 0.
    
    Returns:
        dict[str, object]: Payload including keys "cycle", "cadence_seconds", "watchlist", "scan_presets",
        "max_proposals_per_cycle", "phases", "safety_policy", and "operator_controls".
    
    Raises:
        ValueError: If `symbols` contains no non-empty entries after cleaning.
    """
    clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    if not clean_symbols:
        raise ValueError("symbols must contain at least one non-empty symbol")
    return {
        "cycle": "PRE-FLIGHT -> MONITOR -> ANALYZE -> PROPOSE -> DIGEST",
        "cadence_seconds": max(60, cadence_seconds),
        "watchlist": clean_symbols,
        "scan_presets": list(DEFAULT_SCAN_PRESETS),
        "max_proposals_per_cycle": max(0, max_proposals_per_cycle),
        "phases": [
            research_cycle_phase_payload(phase) for phase in RESEARCH_CYCLE_PHASES
        ],
        "safety_policy": {
            "manual_approval_required": True,
            "sidecar_broker_access": False,
            "scanner_direct_execution": False,
            "raw_web_text_in_core_prompt": False,
            "terminal_proposal_states_immutable": True,
        },
        "operator_controls": {
            "pause": "stop or skip future cycle execution in the future daemon",
            "trigger_now": "run PRE-FLIGHT and MONITOR immediately before any analysis",
            "resume": "only after PRE-FLIGHT gates pass again",
            "status": "research-status plus trade-proposals plus dashboard-snapshot",
        },
    }
