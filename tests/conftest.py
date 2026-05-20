from collections.abc import Iterator

import pytest

from agentic_trader.config import Settings


@pytest.fixture(autouse=True)
def _disable_settings_env_files(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """
    Prevent local .env files from being loaded during tests.
    
    Temporarily sets Settings.model_config["env_file"] to None so test configuration remains deterministic for the duration of each test.
    """

    monkeypatch.setitem(Settings.model_config, "env_file", None)
    yield
