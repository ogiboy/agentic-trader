from agentic_trader.schemas import (
    FundamentalAssessment,
    MacroAssessment,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    SpecialistConsensus,
    StrategyPlan,
)


def _fallback_evidence_note(role: str) -> str:
    return f"{role} evidence was fallback-generated and was not counted as support."


def assess_specialist_consensus(
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    *,
    fundamental: FundamentalAssessment | None = None,
    macro: MacroAssessment | None = None,
) -> SpecialistConsensus:
    """
    Synthesize specialist inputs into a consensus record that lists which roles support or dissent from the chosen strategy action.

    Evaluates regime, coordinator, and risk plans (and optional fundamental and macro assessments) to determine supporting and dissenting specialist roles, collects concise reasons for any disagreements, and produces an alignment summary. Treats a strategy action of "hold" as an immediate defensive consensus.

    Parameters:
        coordinator (ResearchCoordinatorBrief): Coordinator brief describing market focus and related metadata.
        regime (RegimeAssessment): Regime assessment containing direction bias used to compare against the strategy action.
        strategy (StrategyPlan): Chosen strategy plan; the `action` field is compared against specialist inputs.
        risk (RiskPlan): Risk plan whose risk/reward and position sizing influence consensus support.
        fundamental (FundamentalAssessment | None): Optional fundamental analyst assessment; if provided, `overall_bias` determines support vs dissent (a `source` value of `"fallback"` appends a fallback evidence note).
        macro (MacroAssessment | None): Optional macro/news assessment; if provided, `macro_signal` determines support vs dissent (a `source` value of `"fallback"` appends a fallback evidence note).

    Returns:
        SpecialistConsensus: A record containing:
            - `alignment_level`: one of `"aligned"`, `"mixed"`, or `"conflicted"`.
            - `summary`: short human-readable summary of the consensus.
            - `supporting_roles`: list of role names that support the action.
            - `dissenting_roles`: list of role names that dissent from the action.
            - `reasons`: list of concise reasons or notes explaining disagreements or fallback evidence.
    """
    supporting_roles: list[str] = []
    dissenting_roles: list[str] = []
    reasons: list[str] = []

    action = strategy.action
    if action == "hold":
        reasons.append(
            "Strategy selected hold, so specialist consensus is defensive by default."
        )
        return SpecialistConsensus(
            alignment_level="conflicted",
            summary="Specialists converged on a defensive no-trade posture.",
            supporting_roles=["strategy"],
            dissenting_roles=["coordinator", "regime"],
            reasons=reasons,
        )

    if (regime.direction_bias == "long" and action == "buy") or (
        regime.direction_bias == "short" and action == "sell"
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
        reasons.append(
            "Risk plan looked too constrained for full specialist agreement "
            f"(risk_reward_ratio={risk.risk_reward_ratio:.2f}, "
            f"position_size_pct={risk.position_size_pct:.2%})."
        )

    if fundamental is not None:
        if fundamental.source == "fallback":
            reasons.append(_fallback_evidence_note("Fundamental"))
        elif fundamental.overall_bias in {"supportive", "neutral"}:
            supporting_roles.append("fundamental")
        else:
            dissenting_roles.append("fundamental")
            reasons.append(
                f"Fundamental analyst returned {fundamental.overall_bias} evidence."
            )

    if macro is not None:
        if macro.source == "fallback":
            reasons.append(_fallback_evidence_note("Macro/news"))
        elif macro.macro_signal in {"supportive", "neutral"}:
            supporting_roles.append("macro")
        else:
            dissenting_roles.append("macro")
            reasons.append(f"Macro/news analyst returned {macro.macro_signal} context.")

    if not dissenting_roles:
        return SpecialistConsensus(
            alignment_level="aligned",
            summary="Available specialists were aligned before manager synthesis.",
            supporting_roles=supporting_roles,
            dissenting_roles=[],
            reasons=reasons or ["No specialist disagreements were detected."],
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
