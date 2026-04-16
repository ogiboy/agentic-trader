from agentic_trader.agents.context import render_agent_context
from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    MarketSnapshot,
    RegimeAssessment,
    RiskPlan,
    StrategyPlan,
)


def _fallback_risk(snapshot: MarketSnapshot, strategy: StrategyPlan) -> RiskPlan:
    """
    Return a conservative fallback RiskPlan derived from the market snapshot and strategy when an LLM-produced plan is unavailable.
    
    Parameters:
        snapshot (MarketSnapshot): Current market metrics; used to compute a volatility baseline (ATR) and reference prices.
        strategy (StrategyPlan): The proposed strategy whose `action` and `confidence` influence sizing and directional plan.
    
    Behavior:
        - For a buy action: produces a long-risk plan with a stop-loss set below the last close by ~1.5×ATR and a take-profit above by ~3.0×ATR. Position size is strategy.confidence × 0.08 clamped to [0.02, 0.08].
        - For a sell action: produces a short-risk plan with mirrored stop/take levels (stop above, take below) and the same sizing rules as buy.
        - For any other action: returns a conservative no-trade plan with a small fixed position (1%) and stop/take spaced by ~1×ATR.
    
    Returns:
        RiskPlan: A fully populated fallback risk plan with numeric stop_loss and take_profit (rounded), a risk_reward_ratio, max_holding_bars, `source` set to "fallback", and `fallback_reason` set to the shared LLM fallback constant.
    """
    atr = max(snapshot.atr_14, snapshot.last_close * 0.01)

    if strategy.action == "buy":
        stop = snapshot.last_close - (1.5 * atr)
        take_profit = snapshot.last_close + (3.0 * atr)
        return RiskPlan(
            position_size_pct=min(0.08, max(0.02, strategy.confidence * 0.08)),
            stop_loss=round(stop, 4),
            take_profit=round(take_profit, 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Fallback risk model for long setup.",
            source="fallback",
            fallback_reason=LLM_FALLBACK_REASON,
        )

    if strategy.action == "sell":
        stop = snapshot.last_close + (1.5 * atr)
        take_profit = snapshot.last_close - (3.0 * atr)
        return RiskPlan(
            position_size_pct=min(0.08, max(0.02, strategy.confidence * 0.08)),
            stop_loss=round(stop, 4),
            take_profit=round(take_profit, 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Fallback risk model for short setup.",
            source="fallback",
            fallback_reason=LLM_FALLBACK_REASON,
        )

    return RiskPlan(
        position_size_pct=0.01,
        stop_loss=round(snapshot.last_close - atr, 4),
        take_profit=round(snapshot.last_close + atr, 4),
        risk_reward_ratio=1.0,
        max_holding_bars=5,
        notes="Fallback no-trade risk plan.",
        source="fallback",
        fallback_reason=LLM_FALLBACK_REASON,
    )


def _finalize_risk_plan(
    snapshot: MarketSnapshot, strategy: StrategyPlan, risk: RiskPlan
) -> RiskPlan:
    """Keep LLM risk output operator-safe without changing the selected action."""
    if strategy.action != "hold" and strategy.strategy_family != "no_trade":
        return risk

    atr = max(snapshot.atr_14, snapshot.last_close * 0.01)
    stop_loss = round(max(snapshot.last_close - atr, 1e-6), 4)
    take_profit = round(snapshot.last_close + atr, 4)
    notes = risk.notes
    if risk.stop_loss <= 1e-4 or risk.take_profit <= 1e-4:
        notes = (
            f"{risk.notes} Normalized no-trade reference levels around last close "
            "for operator readability."
        )
    return risk.model_copy(
        update={
            "position_size_pct": min(risk.position_size_pct, 0.01),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": max(risk.risk_reward_ratio, 1.0),
            "max_holding_bars": min(risk.max_holding_bars, 5),
            "notes": notes,
        }
    )


def build_risk_plan(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> RiskPlan:
    """Ask the routed risk model for size, stop, take-profit, and holding horizon."""
    system_prompt = (
        "You are a risk agent for a paper trading system. "
        "Use smaller sizing when volatility or uncertainty is elevated. "
        "The stop loss and take profit must be concrete numeric price levels."
    )
    routed_llm = llm.for_role("risk")
    user_prompt = (
        render_agent_context(
            context,
            task="Set position sizing, stop loss, take profit, and holding horizon with smaller sizing when volatility or uncertainty is elevated.",
        )
        if context is not None
        else (
            f"Symbol: {snapshot.symbol}\n\nSnapshot:\n{snapshot.model_dump_json(indent=2)}\n\nRegime:\n{regime.model_dump_json(indent=2)}\n\nStrategy:\n{strategy.model_dump_json(indent=2)}"
        )
    )
    try:
        risk = routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=RiskPlan,
        )
        return _finalize_risk_plan(snapshot, strategy, risk)
    except Exception:
        if not allow_fallback:
            raise
        return _finalize_risk_plan(snapshot, strategy, _fallback_risk(snapshot, strategy))
