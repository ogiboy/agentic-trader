from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


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


def _load_release_notes() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "release"
        / "release_notes.py"
    )
    spec = importlib.util.spec_from_file_location("release_notes", script_path)
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


def test_fill_stable_changelog_defaults_until_to_head_before_tag_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changelog = _load_fill_stable_changelog()

    def missing_ref(args: list[str]) -> str:
        if args[:3] == ["rev-parse", "--verify", "--quiet"]:
            raise subprocess.CalledProcessError(128, ["git", *args])
        raise AssertionError(f"unexpected git command: {args!r}")

    monkeypatch.setattr(changelog, "_run_git", missing_ref)

    assert changelog.default_until_ref("v0.13.0") == "HEAD"


def test_fill_stable_changelog_defaults_until_to_existing_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changelog = _load_fill_stable_changelog()

    def existing_ref(args: list[str]) -> str:
        if args == [
            "rev-parse",
            "--verify",
            "--quiet",
            "v0.13.0^{commit}",
        ]:
            return "abc1234"
        raise AssertionError(f"unexpected git command: {args!r}")

    monkeypatch.setattr(changelog, "_run_git", existing_ref)

    assert changelog.default_until_ref("0.13.0") == "v0.13.0"


def test_release_notes_includes_stable_changelog_body() -> None:
    release_notes = _load_release_notes()
    changelog_text = (
        "# Changelog\n\n"
        "## v0.14.4 (2026-06-05)\n\n"
        "### Bug Fixes\n\n"
        "- Harden agent skill catalog checks\n\n"
        "## v0.14.3 (2026-06-05)\n\n"
        "- Older.\n"
    )

    notes = release_notes.render_release_notes(
        version="0.14.4",
        changelog_text=changelog_text,
        repo_url="https://github.com/example/project",
        run_url="https://github.com/example/project/actions/runs/1",
        stable=True,
    )

    assert "Stable release build for `v0.14.4`." in notes
    assert "### Bug Fixes" in notes
    assert "- Harden agent skill catalog checks" in notes
    assert "blob/v0.14.4/CHANGELOG.md" in notes
    assert "actions/runs/1" in notes


def test_release_notes_renders_preview_build_metadata() -> None:
    release_notes = _load_release_notes()

    notes = release_notes.render_release_notes(
        version="v0.14.5-beta.1",
        changelog_text="# Changelog\n",
        repo_url="https://github.com/example/project",
        channel="beta",
        branch="feature/example",
        short_sha="abc1234",
    )

    assert "Automated beta preview build for `feature/example`." in notes
    assert "- Channel: `beta`" in notes
    assert "- Commit: `abc1234`" in notes
    assert "blob/abc1234/CHANGELOG.md" in notes
