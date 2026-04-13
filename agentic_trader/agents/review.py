from agentic_trader.schemas import (
    ExecutionDecision,
    ManagerDecision,
    RegimeAssessment,
    ReviewNote,
    RiskPlan,
    StrategyPlan,
)


def build_review_note(
    regime: RegimeAssessment,
    _strategy: StrategyPlan,
    risk: RiskPlan,
    manager: ManagerDecision,
    execution: ExecutionDecision,
) -> ReviewNote:
    strengths: list[str] = []
    warnings: list[str] = []
    next_checks: list[str] = []

    if execution.approved:
        strengths.append("Execution guard approved the trade.")
    else:
        warnings.append("Execution guard did not approve the trade.")

    if regime.confidence >= 0.7:
        strengths.append("Regime confidence is relatively strong.")
    else:
        warnings.append("Regime confidence is modest.")

    if risk.risk_reward_ratio >= 2.0:
        strengths.append("Risk/reward profile is favorable.")
    else:
        warnings.append("Risk/reward profile is only marginal.")

    if manager.escalation_flags:
        warnings.extend([f"Manager flag: {flag}" for flag in manager.escalation_flags])

    next_checks.extend(
        [
            "Monitor whether price stays aligned with the chosen invalidation logic.",
            "Review portfolio exposure before allowing additional entries in the same direction.",
        ]
    )

    return ReviewNote(
        summary="Post-plan review synthesized coordinator, specialist, manager, and execution outputs.",
        strengths=strengths,
        warnings=warnings,
        next_checks=next_checks,
    )
