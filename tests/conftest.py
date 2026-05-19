from collections.abc import Iterator

import pytest

from agentic_trader.config import Settings


@pytest.fixture(autouse=True)
def _disable_settings_env_files(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep local .env files from changing deterministic unit-test defaults."""

    monkeypatch.setitem(Settings.model_config, "env_file", None)
    yield
