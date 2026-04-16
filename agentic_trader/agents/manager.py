from agentic_trader.agents.context import render_agent_context
from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    FundamentalAssessment,
    MacroAssessment,
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
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
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
        elif fundamental is not None and fundamental.overall_signal in {
            "cautious",
            "avoid",
        }:
            reason = "fundamental risk reduction"
        elif macro is not None and macro.macro_signal in {"cautious", "avoid"}:
            reason = "macro/news risk reduction"
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
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
) -> ManagerDecision:
    conflicts = manager.conflicts or _derive_manager_conflicts(
        coordinator, regime, strategy, manager, fundamental=fundamental, macro=macro
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


def _apply_confidence_calibration(
    strategy: StrategyPlan,
    manager: ManagerDecision,
    context: AgentContext | None,
) -> ManagerDecision:
    if context is None or context.calibration is None:
        return manager
    calibration = context.calibration
    if calibration.confidence_multiplier >= 1.0:
        return manager

    calibrated_cap = min(
        manager.confidence_cap,
        round(strategy.confidence * calibration.confidence_multiplier, 4),
    )
    calibrated_size = min(manager.size_multiplier, calibration.confidence_multiplier)
    conflicts = list(manager.conflicts)
    conflicts.append(
        ManagerConflict(
            conflict_type="confidence",
            severity="medium",
            summary="Historical trade outcomes triggered a defensive confidence calibration.",
            specialist_view=(
                f"Strategy confidence: {strategy.confidence:.2f} with manager cap {manager.confidence_cap:.2f}."
            ),
            manager_resolution=(
                f"Calibration multiplier {calibration.confidence_multiplier:.2f} tightened cap to {calibrated_cap:.2f} and size to {calibrated_size:.2f}."
            ),
        )
    )
    resolution_notes = list(manager.resolution_notes)
    resolution_notes.append(
        f"Historical calibration reduced confidence using {calibration.closed_trades} closed trades at {calibration.win_rate:.0%} win rate."
    )
    escalation_flags = list(manager.escalation_flags)
    if "historical_underperformance" not in escalation_flags:
        escalation_flags.append("historical_underperformance")
    return manager.model_copy(
        update={
            "confidence_cap": calibrated_cap,
            "size_multiplier": calibrated_size,
            "conflicts": conflicts,
            "resolution_notes": resolution_notes,
            "escalation_flags": escalation_flags,
            "override_applied": True,
        }
    )


def _fallback_manager(
    _snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
) -> ManagerDecision:
    """
    Constructs a conservative, rule-based fallback ManagerDecision used when the LLM is unavailable or returns an invalid structured response.
    
    The decision approves the specialist plan only if the specialist's action is not "hold", the specialist confidence is at least 0.6, and the risk reward ratio is at least 1.5. The returned decision normalizes action bias to "buy"/"sell"/"hold", sets confidence_cap to the minimum of strategy and regime confidences, adjusts size_multiplier downward for capital preservation focus or high-volatility regimes and when specialist confidence is low, and populates escalation_flags to reflect defensive posture or no-trade outcomes. The decision's source is "fallback" and fallback_reason is set to the LLM fallback constant.
    
    Returns:
        ManagerDecision: A guarded ManagerDecision with computed fields (approved, action_bias, confidence_cap, size_multiplier, rationale, escalation_flags, source="fallback", fallback_reason).
    """
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
    if fundamental is not None and fundamental.overall_signal in {"cautious", "avoid"}:
        size_multiplier = min(size_multiplier, 0.5)
        flags.append("fundamental_caution")
    if macro is not None and macro.macro_signal in {"cautious", "avoid"}:
        size_multiplier = min(size_multiplier, 0.5)
        flags.append("macro_caution")
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
        fallback_reason=LLM_FALLBACK_REASON,
    )


def manage_trade_decision(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    *,
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> ManagerDecision:
    """Route specialist outputs through the manager and apply deterministic safeguards."""
    system_prompt = (
        "You are the manager agent for a systematic trading engine. "
        "Combine coordinator, fundamental, macro, regime, strategy, and risk outputs into a final execution posture. "
        "You may approve, force hold, cap confidence, or reduce size."
    )
    routed_llm = llm.for_role("manager")
    user_prompt = (
        render_agent_context(
            context,
            task="Combine coordinator, fundamental, macro, regime, strategy, and risk outputs into a final execution posture. You may approve, force hold, cap confidence, or reduce size.",
        )
        if context is not None
        else (
            f"Symbol: {snapshot.symbol}\n\nSnapshot:\n{snapshot.model_dump_json(indent=2)}\n\nCoordinator:\n{coordinator.model_dump_json(indent=2)}\n\nFundamental:\n{fundamental.model_dump_json(indent=2) if fundamental else 'not provided'}\n\nMacro:\n{macro.model_dump_json(indent=2) if macro else 'not provided'}\n\nRegime:\n{regime.model_dump_json(indent=2)}\n\nStrategy:\n{strategy.model_dump_json(indent=2)}\n\nRisk:\n{risk.model_dump_json(indent=2)}"
        )
    )
    try:
        decision = routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ManagerDecision,
        )
        finalized = _finalize_manager_decision(
            coordinator,
            regime,
            strategy,
            decision,
            fundamental=fundamental,
            macro=macro,
        )
        return _apply_confidence_calibration(strategy, finalized, context)
    except Exception:
        if not allow_fallback:
            raise
        decision = _fallback_manager(
            snapshot,
            coordinator,
            regime,
            strategy,
            risk,
            fundamental=fundamental,
            macro=macro,
        )
        finalized = _finalize_manager_decision(
            coordinator,
            regime,
            strategy,
            decision,
            fundamental=fundamental,
            macro=macro,
        )
        return _apply_confidence_calibration(strategy, finalized, context)
