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


def test_llm_provider_defaults_to_ollama(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_LLM_PROVIDER", raising=False)

    assert Settings().llm_provider == "ollama"


def test_llm_provider_accepts_openai_compatible(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_TRADER_LLM_PROVIDER", "openai-compatible")

    assert Settings().llm_provider == "openai-compatible"


def test_openai_compatible_api_key_reads_primary_env(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENTIC_TRADER_OPENAI_COMPATIBLE_API_KEY", "primary-key")

    assert Settings().openai_compatible_api_key == "primary-key"


def test_openai_compatible_api_key_reads_openai_api_key_fallback(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-fallback-key")

    assert Settings().openai_compatible_api_key == "openai-fallback-key"


def test_openai_compatible_api_key_is_none_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENTIC_TRADER_OPENAI_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert Settings().openai_compatible_api_key is None


def test_openai_compatible_api_key_can_be_passed_directly() -> None:
    settings = Settings(openai_compatible_api_key="direct-key")

    assert settings.openai_compatible_api_key == "direct-key"
