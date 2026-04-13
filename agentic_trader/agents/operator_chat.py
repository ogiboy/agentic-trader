from textwrap import dedent
from typing import Any

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    ChatPersona,
    AgentRole,
    InvestmentPreferences,
    OperatorInstruction,
    PreferenceUpdate,
)
from agentic_trader.storage.db import TradingDatabase


def _persona_to_role(persona: ChatPersona) -> AgentRole:
    mapping: dict[ChatPersona, AgentRole] = {
        "operator_liaison": "explainer",
        "regime_analyst": "regime",
        "strategy_selector": "strategy",
        "risk_steward": "risk",
        "portfolio_manager": "manager",
    }
    return mapping[persona]


def build_chat_context(db: TradingDatabase, settings: Settings) -> str:
    preferences = db.load_preferences()
    service_state = db.get_service_state()
    portfolio = db.get_account_snapshot()
    recent_runs = db.list_recent_runs(limit=5)

    lines = [
        f"Model: {settings.model_name}",
        f"Base URL: {settings.base_url}",
        "Preferences:",
        f"- Regions: {', '.join(preferences.regions) or '-'}",
        f"- Exchanges: {', '.join(preferences.exchanges) or '-'}",
        f"- Currencies: {', '.join(preferences.currencies) or '-'}",
        f"- Sectors: {', '.join(preferences.sectors) or '-'}",
        f"- Risk profile: {preferences.risk_profile}",
        f"- Trade style: {preferences.trade_style}",
        f"- Behavior preset: {preferences.behavior_preset}",
        f"- Agent profile: {preferences.agent_profile}",
        f"- Agent tone: {preferences.agent_tone}",
        f"- Strictness preset: {preferences.strictness_preset}",
        f"- Intervention style: {preferences.intervention_style}",
        "Portfolio:",
        f"- Cash: {portfolio.cash:.2f}",
        f"- Equity: {portfolio.equity:.2f}",
        f"- Open positions: {portfolio.open_positions}",
    ]

    if service_state is None:
        lines.append("Service: no runtime state recorded yet.")
    else:
        lines.extend(
            [
                "Service:",
                f"- State: {service_state.state}",
                f"- Cycle count: {service_state.cycle_count}",
                f"- Current symbol: {service_state.current_symbol or '-'}",
                f"- Message: {service_state.message}",
            ]
        )

    if recent_runs:
        lines.append("Recent runs:")
        for run_id, created_at, symbol, interval, approved in recent_runs:
            lines.append(
                f"- {created_at} | {symbol} {interval} | approved={approved} | {run_id}"
            )
    else:
        lines.append("Recent runs: none")

    return "\n".join(lines)


def build_persona_system_prompt(
    persona: ChatPersona, preferences: InvestmentPreferences
) -> str:
    shared = dedent(
        f"""
        You are part of Agentic Trader, a strict local-first multi-agent paper trading system.
        You are in a read-only operator chat surface.
        Do not claim to have executed trades, modified runtime state, or changed settings unless the user explicitly sees that in the provided context.
        Keep answers concise, practical, and grounded in the supplied runtime and portfolio context.
        Operator behavior preset: {preferences.behavior_preset}
        Operator preferred agent profile: {preferences.agent_profile}
        Operator preferred tone: {preferences.agent_tone}
        Operator strictness preset: {preferences.strictness_preset}
        Operator intervention style: {preferences.intervention_style}
        """
    ).strip()

    role_overrides: dict[ChatPersona, str] = {
        "operator_liaison": "Act as the operator liaison. Explain what the system is doing in plain language and suggest the next operator action when useful.",
        "regime_analyst": "Act as the regime analyst. Focus on market state, momentum, volatility, and whether current conditions fit the active posture.",
        "strategy_selector": "Act as the strategy selector. Focus on trade style fit, setup quality, and why a symbol does or does not deserve attention.",
        "risk_steward": "Act as the risk steward. Focus on sizing, downside, exposure, and why caution or aggression is justified.",
        "portfolio_manager": "Act as the portfolio manager. Focus on the total paper account, open positions, and how the system should prioritize capital.",
    }
    return f"{shared}\n\n{role_overrides[persona]}"


def chat_with_persona(
    *,
    llm: LocalLLM,
    db: TradingDatabase,
    settings: Settings,
    persona: ChatPersona,
    user_message: str,
) -> str:
    preferences = db.load_preferences()
    context = build_chat_context(db, settings)
    system_prompt = build_persona_system_prompt(persona, preferences)
    user_prompt = dedent(
        f"""
        Current system context:
        {context}

        Operator message:
        {user_message}
        """
    ).strip()
    return llm.for_role(_persona_to_role(persona)).complete_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def _apply_keyword_preference(
    lowered_message: str,
    update: PreferenceUpdate,
    field_name: str,
    options: tuple[tuple[tuple[str, ...], Any], ...],
) -> bool:
    for keywords, value in options:
        if any(keyword in lowered_message for keyword in keywords):
            setattr(update, field_name, value)
            return True
    return False


def _fallback_instruction(message: str) -> OperatorInstruction:
    lowered = message.lower()
    update = PreferenceUpdate()
    changed_fields = [
        _apply_keyword_preference(
            lowered,
            update,
            "risk_profile",
            (
                (("conservative",), "conservative"),
                (("balanced",), "balanced"),
                (("aggressive",), "aggressive"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "trade_style",
            (
                (("intraday",), "intraday"),
                (("position",), "position"),
                (("swing",), "swing"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "behavior_preset",
            (
                (("trend",), "trend_biased"),
                (("contrarian",), "contrarian"),
                (("preservation", "defensive"), "capital_preservation"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "agent_profile",
            (
                (("explain", "explanatory"), "explanatory"),
                (("disciplined",), "disciplined"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "agent_tone",
            (
                (("supportive",), "supportive"),
                (("forensic",), "forensic"),
                (("direct",), "direct"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "strictness_preset",
            (
                (("paranoid",), "paranoid"),
                (("strict",), "strict"),
                (("standard",), "standard"),
            ),
        ),
        _apply_keyword_preference(
            lowered,
            update,
            "intervention_style",
            (
                (("hands off", "hands-off"), "hands_off"),
                (("protective",), "protective"),
                (("balanced intervention", "balanced oversight"), "balanced"),
            ),
        ),
    ]

    return OperatorInstruction(
        summary="Fallback operator instruction parser evaluated the request.",
        should_update_preferences=any(changed_fields),
        preference_update=update,
        requires_confirmation=True,
        rationale="Fallback parser only maps explicit curated keywords to safe preference fields.",
    )


def interpret_operator_instruction(
    *,
    llm: LocalLLM,
    db: TradingDatabase,
    settings: Settings,
    user_message: str,
    allow_fallback: bool,
) -> OperatorInstruction:
    preferences = db.load_preferences()
    context = build_chat_context(db, settings)
    system_prompt = dedent(
        f"""
        You convert operator requests into a safe structured instruction for Agentic Trader.
        Only propose preference updates through the provided schema.
        Do not invent runtime actions or hidden side effects.
        Current behavior preset: {preferences.behavior_preset}
        Current agent profile: {preferences.agent_profile}
        Current tone: {preferences.agent_tone}
        Current strictness preset: {preferences.strictness_preset}
        Current intervention style: {preferences.intervention_style}
        """
    ).strip()
    user_prompt = dedent(
        f"""
        Current system context:
        {context}

        Operator request:
        {user_message}
        """
    ).strip()
    try:
        return llm.for_role("instruction").complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=OperatorInstruction,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_instruction(user_message)


def apply_preference_update(
    db: TradingDatabase, update: PreferenceUpdate
) -> InvestmentPreferences:
    current = db.load_preferences()
    merged = current.model_copy(
        update={
            "regions": (
                update.regions if update.regions is not None else current.regions
            ),
            "exchanges": (
                update.exchanges if update.exchanges is not None else current.exchanges
            ),
            "currencies": (
                update.currencies
                if update.currencies is not None
                else current.currencies
            ),
            "sectors": (
                update.sectors if update.sectors is not None else current.sectors
            ),
            "risk_profile": (
                update.risk_profile
                if update.risk_profile is not None
                else current.risk_profile
            ),
            "trade_style": (
                update.trade_style
                if update.trade_style is not None
                else current.trade_style
            ),
            "behavior_preset": (
                update.behavior_preset
                if update.behavior_preset is not None
                else current.behavior_preset
            ),
            "agent_profile": (
                update.agent_profile
                if update.agent_profile is not None
                else current.agent_profile
            ),
            "agent_tone": (
                update.agent_tone
                if update.agent_tone is not None
                else current.agent_tone
            ),
            "strictness_preset": (
                update.strictness_preset
                if update.strictness_preset is not None
                else current.strictness_preset
            ),
            "intervention_style": (
                update.intervention_style
                if update.intervention_style is not None
                else current.intervention_style
            ),
            "notes": update.notes if update.notes is not None else current.notes,
        }
    )
    db.save_preferences(merged)
    return merged
