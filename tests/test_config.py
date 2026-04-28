from agentic_trader.config import Settings


def test_model_name_reads_canonical_env(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_MODEL", raising=False)
    monkeypatch.setenv("AGENTIC_TRADER_MODEL_NAME", "canonical-model")

    assert Settings().model_name == "canonical-model"


def test_model_name_keeps_legacy_env_alias(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_MODEL_NAME", raising=False)
    monkeypatch.setenv("AGENTIC_TRADER_MODEL", "legacy-model")

    assert Settings().model_name == "legacy-model"


def test_model_name_can_still_be_passed_directly(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_MODEL", raising=False)
    monkeypatch.delenv("AGENTIC_TRADER_MODEL_NAME", raising=False)

    assert Settings(model_name="direct-model").model_name == "direct-model"
