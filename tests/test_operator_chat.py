from pathlib import Path

from agentic_trader.agents.operator_chat import build_chat_context, build_persona_system_prompt, chat_with_persona
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase


def test_build_chat_context_includes_preferences_and_portfolio(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    db.save_preferences(
        InvestmentPreferences(
            regions=["US"],
            exchanges=["NASDAQ"],
            currencies=["USD"],
            sectors=["TECH"],
            risk_profile="balanced",
            trade_style="swing",
            behavior_preset="balanced_core",
            agent_profile="explanatory",
            notes="Context test",
        )
    )

    context = build_chat_context(db, settings)

    assert "Behavior preset: balanced_core" in context
    assert "Agent profile: explanatory" in context
    assert "Portfolio:" in context


def test_build_persona_system_prompt_reflects_profile() -> None:
    prompt = build_persona_system_prompt(
        "risk_steward",
        InvestmentPreferences(
            behavior_preset="capital_preservation",
            agent_profile="disciplined",
        ),
    )

    assert "capital_preservation" in prompt
    assert "disciplined" in prompt
    assert "risk steward" in prompt.lower()


def test_chat_with_persona_uses_llm_response(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm,
        "complete_text",
        lambda **kwargs: "Operator-facing response",
    )

    response = chat_with_persona(
        llm=llm,
        db=db,
        settings=settings,
        persona="operator_liaison",
        user_message="What is happening?",
    )

    assert response == "Operator-facing response"
