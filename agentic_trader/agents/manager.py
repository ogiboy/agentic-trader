from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    ManagerConflict,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    StrategyPlan,
)


def _derive_manager_conflicts(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> list[ManagerConflict]:
    conflicts: list[ManagerConflict] = []
    if (
        coordinator.market_focus == "capital_preservation"
        and strategy.action != "hold"
        and manager.size_multiplier < 1.0
    ):
        conflicts.append(
            ManagerConflict(
                conflict_type="focus",
                severity="medium",
                summary="Capital-preservation focus reduced the specialist conviction.",
                specialist_view=(
                    f"Strategy wanted {strategy.action} with {strategy.confidence:.2f} confidence."
                ),
                manager_resolution=(
                    f"Manager kept the trade posture but reduced size to {manager.size_multiplier:.2f}."
                ),
            )
        )
    if manager.action_bias != strategy.action:
        conflicts.append(
            ManagerConflict(
                conflict_type="action",
                severity="high" if manager.action_bias == "hold" else "medium",
                summary="Manager changed the specialist action bias.",
                specialist_view=f"Strategy action: {strategy.action}",
                manager_resolution=f"Manager action bias: {manager.action_bias}",
            )
        )
    if manager.approved is False and strategy.action != "hold":
        conflicts.append(
            ManagerConflict(
                conflict_type="approval",
                severity="high",
                summary="Manager blocked a non-hold specialist plan.",
                specialist_view=(
                    f"Strategy proposed {strategy.action} at {strategy.confidence:.2f} confidence."
                ),
                manager_resolution="Manager withheld approval for execution.",
            )
        )
    if manager.confidence_cap < strategy.confidence:
        conflicts.append(
            ManagerConflict(
                conflict_type="confidence",
                severity="medium",
                summary="Manager tightened the specialist confidence level.",
                specialist_view=f"Strategy confidence: {strategy.confidence:.2f}",
                manager_resolution=f"Confidence capped at {manager.confidence_cap:.2f}",
            )
        )
    if manager.size_multiplier < 1.0:
        reason = "general risk reduction"
        if regime.regime == "high_volatility":
            reason = "high-volatility risk reduction"
        elif coordinator.market_focus == "capital_preservation":
            reason = "capital-preservation risk reduction"
        conflicts.append(
            ManagerConflict(
                conflict_type="size",
                severity="medium",
                summary="Manager reduced the planned position size.",
                specialist_view="Risk steward proposed the full base position size.",
                manager_resolution=(
                    f"Size multiplier set to {manager.size_multiplier:.2f} because of {reason}."
                ),
            )
        )
    return conflicts


def _derive_resolution_notes(
    strategy: StrategyPlan,
    manager: ManagerDecision,
    conflicts: list[ManagerConflict],
) -> list[str]:
    if manager.resolution_notes:
        return manager.resolution_notes

    notes: list[str] = []
    if not conflicts:
        notes.append("Manager accepted the specialist plan without additional overrides.")
    else:
        if manager.action_bias == strategy.action and manager.approved:
            notes.append("Manager kept the specialist action but added execution constraints.")
        if manager.action_bias == "hold":
            notes.append("Manager converted the specialist plan into a hold posture.")
        if manager.confidence_cap < strategy.confidence:
            notes.append("Manager tightened confidence before passing the plan onward.")
        if manager.size_multiplier < 1.0:
            notes.append("Manager reduced exposure before execution.")
    for flag in manager.escalation_flags:
        notes.append(f"Escalation flag: {flag}")
    return notes


def _finalize_manager_decision(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> ManagerDecision:
    conflicts = manager.conflicts or _derive_manager_conflicts(
        coordinator, regime, strategy, manager
    )
    resolution_notes = _derive_resolution_notes(strategy, manager, conflicts)
    override_applied = manager.override_applied or bool(conflicts)
    return manager.model_copy(
        update={
            "conflicts": conflicts,
            "resolution_notes": resolution_notes,
            "override_applied": override_applied,
        }
    )


def _fallback_manager(
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
) -> ManagerDecision:
    approved = (
        strategy.action != "hold"
        and strategy.confidence >= 0.6
        and risk.risk_reward_ratio >= 1.5
    )
    action_bias = strategy.action if approved else "hold"
    size_multiplier = 1.0
    flags: list[str] = []

    if (
        coordinator.market_focus == "capital_preservation"
        or regime.regime == "high_volatility"
    ):
        size_multiplier = 0.5
        flags.append("defensive_posture")
    if strategy.confidence < 0.65:
        size_multiplier = min(size_multiplier, 0.75)
        flags.append("moderate_conviction")
    if action_bias == "hold":
        flags.append("manager_no_trade")

    return ManagerDecision(
        approved=approved,
        action_bias=action_bias if action_bias in {"buy", "sell"} else "hold",
        confidence_cap=min(strategy.confidence, regime.confidence),
        size_multiplier=size_multiplier,
        rationale="Fallback manager combined specialist outputs into a guarded execution posture.",
        escalation_flags=flags,
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def manage_trade_decision(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> ManagerDecision:
    system_prompt = (
        "You are the manager agent for a systematic trading engine. "
        "Combine coordinator, regime, strategy, and risk outputs into a final execution posture. "
        "You may approve, force hold, cap confidence, or reduce size."
    )
    routed_llm = llm.for_role("manager")
    user_prompt = (
        render_agent_context(
            context,
            task="Combine coordinator, regime, strategy, and risk outputs into a final execution posture. You may approve, force hold, cap confidence, or reduce size.",
        )
        if context is not None
        else (
            f"Symbol: {snapshot.symbol}\n\nSnapshot:\n{snapshot.model_dump_json(indent=2)}\n\nCoordinator:\n{coordinator.model_dump_json(indent=2)}\n\nRegime:\n{regime.model_dump_json(indent=2)}\n\nStrategy:\n{strategy.model_dump_json(indent=2)}\n\nRisk:\n{risk.model_dump_json(indent=2)}"
        )
    )
    try:
        decision = routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ManagerDecision,
        )
        return _finalize_manager_decision(coordinator, regime, strategy, decision)
    except Exception:
        if not allow_fallback:
            raise
        decision = _fallback_manager(snapshot, coordinator, regime, strategy, risk)
        return _finalize_manager_decision(coordinator, regime, strategy, decision)
