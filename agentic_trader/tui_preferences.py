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
from agentic_trader.tui_common import console, open_db, split_csv
from agentic_trader.tui_monitor_sections import observer_mode_panel, render_preferences
from agentic_trader.ui_text import (
    MESSAGE_PREFERENCES_SAVED,
    PROMPT_CONTINUE,
    TITLE_PREFERENCE_EDITING,
    TITLE_SAVED,
)


def configure_preferences(db: TradingDatabase) -> None:
    current = db.load_preferences()
    console.print(render_preferences(current))
    regions = Prompt.ask(
        "Regions (comma-separated)", default=", ".join(current.regions)
    )
    exchanges = Prompt.ask(
        "Exchanges (comma-separated)", default=", ".join(current.exchanges)
    )
    currencies = Prompt.ask(
        "Currencies (comma-separated)", default=", ".join(current.currencies)
    )
    sectors = Prompt.ask(
        "Sectors (comma-separated, optional)",
        default=", ".join(current.sectors),
    )
    risk_profile = Prompt.ask(
        "Risk profile",
        choices=["conservative", "balanced", "aggressive"],
        default=current.risk_profile,
    )
    trade_style = Prompt.ask(
        "Trade style",
        choices=["swing", "position", "intraday"],
        default=current.trade_style,
    )
    behavior_preset = Prompt.ask(
        "Behavior preset",
        choices=["balanced_core", "trend_biased", "contrarian", "capital_preservation"],
        default=current.behavior_preset,
    )
    agent_profile = Prompt.ask(
        "Agent profile",
        choices=["neutral", "disciplined", "aggressive", "explanatory"],
        default=current.agent_profile,
    )
    agent_tone = Prompt.ask(
        "Agent tone",
        choices=["neutral", "supportive", "direct", "forensic"],
        default=current.agent_tone,
    )
    strictness_preset = Prompt.ask(
        "Strictness preset",
        choices=["standard", "strict", "paranoid"],
        default=current.strictness_preset,
    )
    intervention_style = Prompt.ask(
        "Intervention style",
        choices=["hands_off", "balanced", "protective"],
        default=current.intervention_style,
    )
    notes = Prompt.ask("Notes", default=current.notes)
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
        Panel(MESSAGE_PREFERENCES_SAVED, title=TITLE_SAVED, border_style="green")
    )


def edit_preferences_action(settings: Settings) -> None:
    try:
        db = open_db(settings, read_only=False)
    except Exception as exc:
        console.print(observer_mode_panel(TITLE_PREFERENCE_EDITING, str(exc)))
        Prompt.ask(PROMPT_CONTINUE, default="")
        return
    try:
        configure_preferences(db)
    finally:
        db.close()
