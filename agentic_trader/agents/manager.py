from agentic_trader.agents.context import render_agent_context
from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    ExecutionSide,
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


def _capital_preservation_conflict(
    coordinator: ResearchCoordinatorBrief,
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> ManagerConflict | None:
    if not (
        coordinator.market_focus == "capital_preservation"
        and strategy.action != "hold"
        and manager.size_multiplier < 1.0
    ):
        return None
    return ManagerConflict(
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


def _action_change_conflict(
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> ManagerConflict | None:
    if manager.action_bias == strategy.action:
        return None
    severity = "medium"
    if manager.action_bias == "hold":
        severity = "high"
    return ManagerConflict(
        conflict_type="action",
        severity=severity,
        summary="Manager changed the specialist action bias.",
        specialist_view=f"Strategy action: {strategy.action}",
        manager_resolution=f"Manager action bias: {manager.action_bias}",
    )


def _approval_conflict(
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> ManagerConflict | None:
    if manager.approved is not False or strategy.action == "hold":
        return None
    return ManagerConflict(
        conflict_type="approval",
        severity="high",
        summary="Manager blocked a non-hold specialist plan.",
        specialist_view=(
            f"Strategy proposed {strategy.action} at {strategy.confidence:.2f} confidence."
        ),
        manager_resolution="Manager withheld approval for execution.",
    )


def _confidence_conflict(
    strategy: StrategyPlan,
    manager: ManagerDecision,
) -> ManagerConflict | None:
    if manager.confidence_cap >= strategy.confidence:
        return None
    return ManagerConflict(
        conflict_type="confidence",
        severity="medium",
        summary="Manager tightened the specialist confidence level.",
        specialist_view=f"Strategy confidence: {strategy.confidence:.2f}",
        manager_resolution=f"Confidence capped at {manager.confidence_cap:.2f}",
    )


def _size_reduction_reason(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    fundamental: FundamentalAssessment | None,
    macro: MacroAssessment | None,
) -> str:
    if regime.regime == "high_volatility":
        return "high-volatility risk reduction"
    if coordinator.market_focus == "capital_preservation":
        return "capital-preservation risk reduction"
    if fundamental is not None and fundamental.overall_bias in {"cautious", "avoid"}:
        return "fundamental risk reduction"
    if macro is not None and macro.macro_signal in {"cautious", "avoid"}:
        return "macro/news risk reduction"
    return "general risk reduction"


def _size_reduction_conflict(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    manager: ManagerDecision,
    fundamental: FundamentalAssessment | None,
    macro: MacroAssessment | None,
) -> ManagerConflict | None:
    if manager.size_multiplier >= 1.0:
        return None
    reason = _size_reduction_reason(coordinator, regime, fundamental, macro)
    return ManagerConflict(
        conflict_type="size",
        severity="medium",
        summary="Manager reduced the planned position size.",
        specialist_view="Risk steward proposed the full base position size.",
        manager_resolution=(
            f"Size multiplier set to {manager.size_multiplier:.2f} because of {reason}."
        ),
    )


def _derive_manager_conflicts(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    manager: ManagerDecision,
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
) -> list[ManagerConflict]:
    """
    Derives a list of ManagerConflict entries describing mismatches or risk-control constraints between the coordinator, regime, strategy, and manager decisions.

    Parameters:
        coordinator (ResearchCoordinatorBrief): High-level research directives including market_focus.
        regime (RegimeAssessment): Current market regime assessment (e.g., high_volatility).
        strategy (StrategyPlan): Specialist plan including desired action and confidence.
        manager (ManagerDecision): Proposed manager decision used to detect overrides or tightenings.
        fundamental (FundamentalAssessment | None): Optional fundamental assessment; its `overall_bias` may trigger conservative sizing.
        macro (MacroAssessment | None): Optional macro/news assessment; its `macro_signal` may trigger conservative sizing.

    Returns:
        list[ManagerConflict]: A list of conflicts found (empty if manager decision aligns with guidance). Each conflict indicates type, severity, summary, specialist_view, and manager_resolution.
    """
    conflicts: list[ManagerConflict] = []
    possible_conflicts = (
        _capital_preservation_conflict(coordinator, strategy, manager),
        _action_change_conflict(strategy, manager),
        _approval_conflict(strategy, manager),
        _confidence_conflict(strategy, manager),
        _size_reduction_conflict(
            coordinator,
            regime,
            manager,
            fundamental,
            macro,
        ),
    )
    conflicts.extend(
        conflict for conflict in possible_conflicts if conflict is not None
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
        notes.append(
            "Manager accepted the specialist plan without additional overrides."
        )
    else:
        if manager.action_bias == strategy.action and manager.approved:
            notes.append(
                "Manager kept the specialist action but added execution constraints."
            )
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


def _fallback_approved(strategy: StrategyPlan, risk: RiskPlan) -> bool:
    return (
        strategy.action != "hold"
        and strategy.confidence >= 0.6
        and risk.risk_reward_ratio >= 1.5
    )


def _normalized_action_bias(action_bias: str) -> ExecutionSide:
    if action_bias == "buy":
        return "buy"
    if action_bias == "sell":
        return "sell"
    return "hold"


def _fallback_action_bias(strategy: StrategyPlan, approved: bool) -> ExecutionSide:
    if approved:
        return strategy.action
    return "hold"


def _fallback_size_and_flags(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    action_bias: ExecutionSide,
    fundamental: FundamentalAssessment | None,
    macro: MacroAssessment | None,
) -> tuple[float, list[str]]:
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
    if fundamental is not None and fundamental.overall_bias in {"cautious", "avoid"}:
        size_multiplier = min(size_multiplier, 0.5)
        flags.append("fundamental_caution")
    if macro is not None and macro.macro_signal in {"cautious", "avoid"}:
        size_multiplier = min(size_multiplier, 0.5)
        flags.append("macro_caution")
    if action_bias == "hold":
        flags.append("manager_no_trade")

    return size_multiplier, flags


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
    Produce a conservative, rule-based ManagerDecision when LLM output is unavailable or invalid.

    Approves the specialist plan only if the specialist's action is not "hold", the specialist confidence is >= 0.6, and the risk reward ratio is >= 1.5. Sets `confidence_cap` to the minimum of strategy and regime confidences. Reduces `size_multiplier` for capital-preservation focus, high-volatility regimes, low specialist confidence, or when fundamental.overall_bias or macro.macro_signal is "cautious" or "avoid". Populates `escalation_flags` to reflect defensive posture, reduced conviction, fundamental/macro caution, or a no-trade outcome. The decision's `source` is "fallback" and `fallback_reason` is set to the LLM fallback constant.

    Returns:
        ManagerDecision: A guarded decision with computed `approved`, normalized `action_bias` ("buy"/"sell"/"hold"), `confidence_cap`, `size_multiplier`, `rationale`, `escalation_flags`, `source="fallback"`, and `fallback_reason`.
    """
    approved = _fallback_approved(strategy, risk)
    action_bias = _fallback_action_bias(strategy, approved)
    size_multiplier, flags = _fallback_size_and_flags(
        coordinator,
        regime,
        strategy,
        action_bias,
        fundamental,
        macro,
    )

    return ManagerDecision(
        approved=approved,
        action_bias=_normalized_action_bias(action_bias),
        confidence_cap=min(strategy.confidence, regime.confidence),
        size_multiplier=size_multiplier,
        rationale="Fallback manager combined specialist outputs into a guarded execution posture.",
        escalation_flags=flags,
        source="fallback",
        fallback_reason=LLM_FALLBACK_REASON,
    )


def _render_optional_assessment(
    assessment: FundamentalAssessment | MacroAssessment | None,
) -> str:
    if assessment is None:
        return "not provided"
    return assessment.model_dump_json(indent=2)


def _build_manager_prompt(
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    fundamental: FundamentalAssessment | None,
    macro: MacroAssessment | None,
    context: AgentContext | None,
) -> str:
    task = (
        "Combine coordinator, fundamental, macro, regime, strategy, and risk outputs into a final execution posture. "
        "You may approve, force hold, cap confidence, or reduce size."
    )
    if context is not None:
        return render_agent_context(context, task=task)

    fundamental_payload = _render_optional_assessment(fundamental)
    macro_payload = _render_optional_assessment(macro)
    return (
        f"Symbol: {snapshot.symbol}\n\n"
        f"Snapshot:\n{snapshot.model_dump_json(indent=2)}\n\n"
        f"Coordinator:\n{coordinator.model_dump_json(indent=2)}\n\n"
        f"Fundamental:\n{fundamental_payload}\n\n"
        f"Macro:\n{macro_payload}\n\n"
        f"Regime:\n{regime.model_dump_json(indent=2)}\n\n"
        f"Strategy:\n{strategy.model_dump_json(indent=2)}\n\n"
        f"Risk:\n{risk.model_dump_json(indent=2)}"
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
    user_prompt = _build_manager_prompt(
        snapshot,
        coordinator,
        regime,
        strategy,
        risk,
        fundamental,
        macro,
        context,
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
