from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_bootstrap_changelog() -> ModuleType:
    """
    Load the repository's scripts/release/bootstrap_changelog.py as a module.
    
    Locates scripts/release/bootstrap_changelog.py relative to this file, imports and executes it, registers it in sys.modules under the module name, and returns the loaded module object.
    
    Returns:
        module (ModuleType): The imported module object for bootstrap_changelog.
    """
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


def _load_fill_stable_changelog() -> ModuleType:
    """
    Load and return the `fill_stable_changelog` module from the repository's scripts/release directory.
    
    Returns:
        ModuleType: The imported module object for `fill_stable_changelog`.
    """
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "release"
        / "fill_stable_changelog.py"
    )
    spec = importlib.util.spec_from_file_location("fill_stable_changelog", script_path)
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


def test_fill_stable_changelog_replaces_empty_stable_section() -> None:
    changelog = _load_fill_stable_changelog()
    original = (
        "# Changelog\n\n"
        "<!-- version list -->\n\n"
        "## v0.12.5 (2026-05-26)\n\n\n"
        "## v0.12.4 (2026-05-25)\n\n"
        "### Bug Fixes\n\n"
        "- Existing fix.\n"
    )

    updated = changelog.fill_empty_section(
        original,
        version="v0.12.5",
        entries={
            "Bug Fixes": [
                "- Pin qs security override\n"
                "  ([`a7a3765`](https://github.com/ogiboy/agentic-trader/commit/a7a376552fca45c7ce8a9fd132faa46bdee4ac12))"
            ],
            "Tests": ["- Stabilize setup status typing\n  ([`305287a`](url))"],
        },
    )

    assert "## v0.12.5 (2026-05-26)" in updated
    assert "### Bug Fixes" in updated
    assert "Pin qs security override" in updated
    assert updated.index("## v0.12.5") < updated.index("## v0.12.4")


def test_fill_stable_changelog_leaves_non_empty_section_unchanged() -> None:
    changelog = _load_fill_stable_changelog()
    original = (
        "# Changelog\n\n"
        "## v0.12.5 (2026-05-26)\n\n"
        "### Bug Fixes\n\n"
        "- Existing fix.\n\n"
        "## v0.12.4 (2026-05-25)\n"
    )

    updated = changelog.fill_empty_section(
        original,
        version="v0.12.5",
        entries={"Tests": ["- New test."]},
    )

    assert updated == original


def test_fill_stable_changelog_ignores_prerelease_tags_for_previous_stable() -> None:
    changelog = _load_fill_stable_changelog()

    assert changelog._stable_version_tuple("v0.12.5-beta.184+g854a22e") is None
    assert changelog._stable_version_tuple("v0.12.4") == (0, 12, 4)
