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


def test_sec_edgar_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED", raising=False)
    monkeypatch.delenv("AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT", raising=False)

    settings = Settings()

    assert settings.research_sec_edgar_enabled is False
    assert settings.research_sec_edgar_user_agent is None


def test_sec_edgar_fields_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED", "true")
    monkeypatch.setenv(
        "AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT",
        "Agentic Trader test contact@example.com",
    )

    settings = Settings()

    assert settings.research_sec_edgar_enabled is True
    assert settings.research_sec_edgar_user_agent == "Agentic Trader test contact@example.com"
