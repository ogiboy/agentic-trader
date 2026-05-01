"""Tests for agentic_trader/researchd/crewai_setup.py changes.

Covers:
- default_crewai_flow_dir now points to sidecars/research_flow
- crewai_setup_status new fields: uv_available, environment_exists,
  python_version, lockfile_exists
"""

from pathlib import Path

import pytest

from agentic_trader.config import Settings
from agentic_trader.researchd.crewai_setup import (
    crewai_setup_status,
    default_crewai_flow_dir,
)


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
    )
    settings.ensure_directories()
    return settings


def test_default_crewai_flow_dir_points_to_tracked_sidecar(tmp_path: Path) -> None:
    """default_crewai_flow_dir now returns sidecars/research_flow, not a runtime path."""
    settings = _settings(tmp_path)

    flow_dir = default_crewai_flow_dir(settings)

    # Must end in sidecars/research_flow regardless of runtime_dir
    assert flow_dir.parts[-1] == "research_flow"
    assert flow_dir.parts[-2] == "sidecars"


def test_default_crewai_flow_dir_ignores_settings_runtime_dir(tmp_path: Path) -> None:
    """The sidecar path is independent of the runtime_dir setting."""
    settings_a = _settings(tmp_path / "runtime_a")
    settings_b = _settings(tmp_path / "runtime_b")

    dir_a = default_crewai_flow_dir(settings_a)
    dir_b = default_crewai_flow_dir(settings_b)

    # Both point to the same tracked location, not inside runtime_dir
    assert dir_a == dir_b
    assert str(tmp_path) not in str(dir_a)


def test_crewai_setup_status_includes_uv_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """crewai_setup_status now reports whether uv is on PATH."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: "/usr/bin/uv" if name == "uv" else None,
    )

    result = crewai_setup_status(settings)

    assert result["uv_available"] is True
    assert result["uv_path"] == "/usr/bin/uv"


def test_crewai_setup_status_uv_not_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """crewai_setup_status reports uv_available=False when uv is not on PATH."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["uv_available"] is False
    assert result["uv_path"] is None
    assert result["available"] is False


def test_crewai_setup_status_environment_exists_false_when_no_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """environment_exists is False when .venv directory is absent."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()
    (fake_flow / "pyproject.toml").write_text("[project]\nname='fake'\n")
    # No .venv directory created

    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    def fake_flow_dir(_settings: Settings) -> Path:
        return fake_flow

    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.Path.__new__",
        Path.__new__,
    )
    # Patch default_crewai_flow_dir indirectly via monkeypatching the module-level call
    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(setup_module, "default_crewai_flow_dir", fake_flow_dir)

    result = crewai_setup_status(settings)

    assert result["flow_scaffold_exists"] is True
    assert result["environment_exists"] is False


def test_crewai_setup_status_environment_exists_true_when_venv_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """environment_exists is True when .venv directory is present."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()
    (fake_flow / "pyproject.toml").write_text("[project]\nname='fake'\n")
    (fake_flow / ".venv").mkdir()

    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(
        setup_module, "default_crewai_flow_dir", lambda _: fake_flow
    )
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["environment_exists"] is True


def test_crewai_setup_status_python_version_read_from_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """python_version is read from .python-version file when it exists."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()
    (fake_flow / ".python-version").write_text("3.13\n", encoding="utf-8")

    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(
        setup_module, "default_crewai_flow_dir", lambda _: fake_flow
    )
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["python_version"] == "3.13"


def test_crewai_setup_status_python_version_none_when_file_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """python_version is None when .python-version file does not exist."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()
    # No .python-version file

    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(
        setup_module, "default_crewai_flow_dir", lambda _: fake_flow
    )
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["python_version"] is None


def test_crewai_setup_status_lockfile_exists_true_when_uv_lock_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lockfile_exists is True when uv.lock file is present."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()
    (fake_flow / "uv.lock").write_text("# lockfile\n", encoding="utf-8")

    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(
        setup_module, "default_crewai_flow_dir", lambda _: fake_flow
    )
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["lockfile_exists"] is True


def test_crewai_setup_status_lockfile_exists_false_when_uv_lock_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lockfile_exists is False when uv.lock file is absent."""
    settings = _settings(tmp_path)
    fake_flow = tmp_path / "fake_flow"
    fake_flow.mkdir()

    import agentic_trader.researchd.crewai_setup as setup_module

    monkeypatch.setattr(
        setup_module, "default_crewai_flow_dir", lambda _: fake_flow
    )
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["lockfile_exists"] is False


def test_crewai_setup_status_recommended_commands_use_pnpm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """recommended_commands now list pnpm-based setup/check/run commands."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    commands = result["recommended_commands"]
    assert isinstance(commands, list)
    assert any("pnpm" in str(cmd) for cmd in commands)
    assert any("setup:research-flow" in str(cmd) for cmd in commands)
    assert any("check:research-flow" in str(cmd) for cmd in commands)


def test_crewai_setup_status_core_dependency_always_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """core_dependency must always be False; CrewAI must never be a core dep."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    assert result["core_dependency"] is False


def test_crewai_setup_status_notes_mention_subprocess_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Notes should mention the subprocess JSON contract isolation."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "agentic_trader.researchd.crewai_setup.shutil.which",
        lambda name: None,
    )

    result = crewai_setup_status(settings)

    notes = [str(n).lower() for n in result["notes"]]
    assert any("subprocess" in note or "contract" in note for note in notes)
    assert any("import" in note for note in notes)