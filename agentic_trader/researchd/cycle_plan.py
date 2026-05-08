"""Continuous research cycle plan for the local paper desk.

The plan is an operator/runtime contract, not an autonomous executor. It shows
how the existing safe commands compose into a PRE-FLIGHT -> MONITOR -> ANALYZE
-> PROPOSE -> DIGEST loop while keeping proposals manual and broker access out
of sidecar/news/scanner paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

CyclePhaseName = Literal["PRE-FLIGHT", "MONITOR", "ANALYZE", "PROPOSE", "DIGEST"]


@dataclass(frozen=True)
class ResearchCyclePhase:
    name: CyclePhaseName
    purpose: str
    read_commands: tuple[str, ...]
    produce: tuple[str, ...]
    fail_closed_on: tuple[str, ...]
    forbidden: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


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
        produce=("watchlist_monitor_summary", "source_health_delta", "proposal_queue_state"),
        fail_closed_on=(
            "dashboard_unavailable",
            "unredacted_provider_error",
            "news_plan_missing_source_policy",
        ),
        forbidden=("create_trade_without_operator_thesis", "ignore_pending_terminal_state"),
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
        produce=("idea_score_cards", "missing_evidence_list", "strategy_readiness_context"),
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
        forbidden=("proposal_approve", "broker_submit", "implicit_web_or_chat_approval"),
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


def research_cycle_plan_payload(
    *, symbols: list[str], cadence_seconds: int, max_proposals_per_cycle: int = 1
) -> dict[str, object]:
    clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    if not clean_symbols:
        raise ValueError("symbols must contain at least one non-empty symbol")
    return {
        "cycle": "PRE-FLIGHT -> MONITOR -> ANALYZE -> PROPOSE -> DIGEST",
        "cadence_seconds": max(60, cadence_seconds),
        "watchlist": clean_symbols,
        "scan_presets": list(DEFAULT_SCAN_PRESETS),
        "max_proposals_per_cycle": max(0, max_proposals_per_cycle),
        "phases": [phase.to_payload() for phase in RESEARCH_CYCLE_PHASES],
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
