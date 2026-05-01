from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def _load_bootstrap_changelog() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "release"
        / "bootstrap_changelog.py"
    )
    spec = importlib.util.spec_from_file_location("bootstrap_changelog", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bootstrap_changelog_renders_categorized_baseline_section() -> None:
    changelog = _load_bootstrap_changelog()

    section = changelog.render_section(
        version="v0.9.0",
        date="2026-05-01",
        entries={
            "Features": ["- feat: add provider diagnostics (abc1234)"],
            "Fixes": ["- fix: repair release publish path (def5678)"],
        },
    )

    assert "## v0.9.0 - 2026-05-01" in section
    assert "### Features" in section
    assert "- feat: add provider diagnostics (abc1234)" in section
    assert "### Fixes" in section


def test_bootstrap_changelog_does_not_duplicate_existing_version() -> None:
    changelog = _load_bootstrap_changelog()
    original = "# Changelog\n\n## v0.9.0 - 2026-05-01\n\n### Features\n"

    updated = changelog.insert_section(
        original,
        "## v0.9.0 - 2026-05-01\n\n### Maintenance\n\n- Baseline.",
        version="v0.9.0",
    )

    assert updated == original


def test_bootstrap_changelog_inserts_before_older_sections() -> None:
    changelog = _load_bootstrap_changelog()
    original = "# Changelog\n\nIntro.\n\n## v0.8.0 - 2026-04-01\n"

    updated = changelog.insert_section(
        original,
        "## v0.9.0 - 2026-05-01\n\n### Maintenance\n\n- Baseline.",
        version="v0.9.0",
    )

    assert updated.index("## v0.9.0") < updated.index("## v0.8.0")
