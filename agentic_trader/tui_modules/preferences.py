from typing import cast

from rich.panel import Panel
from rich.prompt import Prompt

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    AgentProfile,
    AgentTone,
    BehaviorPreset,
    InterventionStyle,
    InvestmentPreferences,
    RiskProfile,
    StrictnessPreset,
    TradeStyle,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import console, open_db, split_csv
from agentic_trader.tui_modules.monitor_runtime import observer_mode_panel
from agentic_trader.tui_modules.monitor_tables import render_preferences
from agentic_trader.ui_text import t


def configure_preferences(db: TradingDatabase) -> None:
    current = db.load_preferences()
    console.print(render_preferences(current))
    regions = Prompt.ask(t("label.regions"), default=", ".join(current.regions))
    exchanges = Prompt.ask(t("label.exchanges"), default=", ".join(current.exchanges))
    currencies = Prompt.ask(t("label.currencies"), default=", ".join(current.currencies))
    sectors = Prompt.ask(
        t("label.sectors"),
        default=", ".join(current.sectors),
    )
    risk_profile = Prompt.ask(
        t("label.risk.profile"),
        choices=["conservative", "balanced", "aggressive"],
        default=current.risk_profile,
    )
    trade_style = Prompt.ask(
        t("label.trade.style"),
        choices=["swing", "position", "intraday"],
        default=current.trade_style,
    )
    behavior_preset = Prompt.ask(
        t("label.behavior.preset"),
        choices=["balanced_core", "trend_biased", "contrarian", "capital_preservation"],
        default=current.behavior_preset,
    )
    agent_profile = Prompt.ask(
        t("label.agent.profile"),
        choices=["neutral", "disciplined", "aggressive", "explanatory"],
        default=current.agent_profile,
    )
    agent_tone = Prompt.ask(
        t("label.agent.tone"),
        choices=["neutral", "supportive", "direct", "forensic"],
        default=current.agent_tone,
    )
    strictness_preset = Prompt.ask(
        t("label.strictness"),
        choices=["standard", "strict", "paranoid"],
        default=current.strictness_preset,
    )
    intervention_style = Prompt.ask(
        t("label.intervention"),
        choices=["hands_off", "balanced", "protective"],
        default=current.intervention_style,
    )
    notes = Prompt.ask(t("label.notes"), default=current.notes)
    updated = InvestmentPreferences(
        regions=split_csv(regions) or current.regions,
        exchanges=split_csv(exchanges) or current.exchanges,
        currencies=split_csv(currencies) or current.currencies,
        sectors=split_csv(sectors),
        risk_profile=cast(RiskProfile, risk_profile),
        trade_style=cast(TradeStyle, trade_style),
        behavior_preset=cast(BehaviorPreset, behavior_preset),
        agent_profile=cast(AgentProfile, agent_profile),
        agent_tone=cast(AgentTone, agent_tone),
        strictness_preset=cast(StrictnessPreset, strictness_preset),
        intervention_style=cast(InterventionStyle, intervention_style),
        notes=notes,
    )
    db.save_preferences(updated)
    console.print(
        Panel(t("message.preferences.saved"), title=t("title.saved"), border_style="green")
    )


def edit_preferences_action(settings: Settings) -> None:
    try:
        db = open_db(settings, read_only=False)
    except Exception as exc:
        console.print(observer_mode_panel(t("title.preference.editing"), str(exc)))
        Prompt.ask(t("prompt.continue"), default="")
        return
    try:
        configure_preferences(db)
    finally:
        db.close()
