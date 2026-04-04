from agentic_trader.schemas import (
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    SpecialistConsensus,
    StrategyPlan,
)


def assess_specialist_consensus(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
) -> SpecialistConsensus:
    supporting_roles: list[str] = []
    dissenting_roles: list[str] = []
    reasons: list[str] = []

    action = strategy.action
    if action == "hold":
        reasons.append("Strategy selected hold, so specialist consensus is defensive by default.")
        return SpecialistConsensus(
            alignment_level="conflicted",
            summary="Specialists converged on a defensive no-trade posture.",
            supporting_roles=["strategy"],
            dissenting_roles=["coordinator", "regime"],
            reasons=reasons,
        )

    if (
        (regime.direction_bias == "long" and action == "buy")
        or (regime.direction_bias == "short" and action == "sell")
    ):
        supporting_roles.append("regime")
    else:
        dissenting_roles.append("regime")
        reasons.append("Regime bias did not line up cleanly with the selected action.")

    if coordinator.market_focus in {"trend_following", "breakout", "mean_reversion"}:
        supporting_roles.append("coordinator")
    else:
        dissenting_roles.append("coordinator")
        reasons.append(
            f"Coordinator focus {coordinator.market_focus} leaned defensive versus the chosen action."
        )

    if risk.risk_reward_ratio >= 1.5 and risk.position_size_pct >= 0.02:
        supporting_roles.append("risk")
    else:
        dissenting_roles.append("risk")
        reasons.append("Risk plan looked too constrained for full specialist agreement.")

    if not dissenting_roles:
        return SpecialistConsensus(
            alignment_level="aligned",
            summary="Coordinator, regime, strategy, and risk were aligned.",
            supporting_roles=supporting_roles,
            dissenting_roles=[],
            reasons=["No specialist disagreements were detected."],
        )
    if len(dissenting_roles) == 1:
        return SpecialistConsensus(
            alignment_level="mixed",
            summary="Most specialists aligned, with one material caution signal.",
            supporting_roles=supporting_roles,
            dissenting_roles=dissenting_roles,
            reasons=reasons,
        )
    return SpecialistConsensus(
        alignment_level="conflicted",
        summary="Multiple specialist signals conflicted before execution.",
        supporting_roles=supporting_roles,
        dissenting_roles=dissenting_roles,
        reasons=reasons,
    )
