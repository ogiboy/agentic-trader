from pathlib import Path

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    interpret_operator_instruction,
)
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import OperatorInstruction, PreferenceUpdate
from agentic_trader.storage.db import TradingDatabase


def _force_fallback(**_kwargs: object) -> None:
    """
    Helper that always raises a RuntimeError to force the code path that handles structured-LLM fallback.

    Raises:
        RuntimeError: Always raised with the message "force fallback".
    """
    raise RuntimeError("force fallback")


def test_apply_preference_update_changes_only_supplied_fields(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    updated = apply_preference_update(
        db,
        PreferenceUpdate(
            risk_profile="conservative",
            behavior_preset="capital_preservation",
        ),
    )

    assert updated.risk_profile == "conservative"
    assert updated.behavior_preset == "capital_preservation"
    assert updated.trade_style == "swing"


def test_interpret_operator_instruction_uses_fallback_keywords(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    llm = LocalLLM(settings)
    monkeypatch.setattr(
        llm,
        "complete_structured",
        _force_fallback,
    )

    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message="Please make the system conservative, explanatory, forensic, strict, and protective.",
        allow_fallback=True,
    )

    assert instruction.should_update_preferences is True
    assert instruction.preference_update.risk_profile == "conservative"
    assert instruction.preference_update.agent_profile == "explanatory"
    assert instruction.preference_update.agent_tone == "forensic"
    assert instruction.preference_update.strictness_preset == "strict"
    assert instruction.preference_update.intervention_style == "protective"


def test_interpret_operator_instruction_can_use_structured_llm(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    llm = LocalLLM(settings)

    monkeypatch.setattr(
        llm,
        "complete_structured",
        lambda **kwargs: OperatorInstruction(
            summary="Parsed by LLM",
            should_update_preferences=True,
            preference_update=PreferenceUpdate(trade_style="intraday"),
            requires_confirmation=True,
            rationale="Test rationale",
        ),
    )

    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message="Use an intraday style.",
        allow_fallback=False,
    )

    assert instruction.summary == "Parsed by LLM"
    assert instruction.preference_update.trade_style == "intraday"
