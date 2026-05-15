from __future__ import annotations

from argparse import Namespace
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib
from types import ModuleType


def _load_version_plan() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "release"
        / "version_plan.py"
    )
    spec = importlib.util.spec_from_file_location("version_plan", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _args(
    *,
    semantic_tag: str | None,
    release_ref: str | None = None,
    ref_name: str = "main",
) -> Namespace:
    return Namespace(
        semantic_tag=semantic_tag,
        release_ref=release_ref,
        ref_name=ref_name,
        run_number="123",
        sha="abcdef1234567890",
        channel=None,
    )


def test_version_plan_floors_below_baseline_stable_candidate() -> None:
    version_plan = _load_version_plan()

    plan = version_plan.build_plan(_args(semantic_tag="v0.1.0"))

    assert plan.raw_semantic_version == "0.1.0"
    assert plan.semantic_floor_applied is True
    assert plan.semantic_version == plan.base_version
    assert plan.artifact_version == f"v{plan.base_version}"
    assert plan.channel == "stable"
    assert plan.attach_to_release is False


def test_version_plan_marks_explicit_release_ref_for_attachment() -> None:
    version_plan = _load_version_plan()
    release_ref = f"v{version_plan._read_project_version()}"

    plan = version_plan.build_plan(
        _args(semantic_tag=None, release_ref=release_ref, ref_name=release_ref)
    )

    assert plan.channel == "stable"
    assert plan.release_ref == release_ref
    assert plan.artifact_version == release_ref
    assert plan.attach_to_release is True


def test_tracked_product_versions_match_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(pyproject["project"]["version"])

    assert json.loads((root / "package.json").read_text(encoding="utf-8"))[
        "version"
    ] == version
    for package_path in (
        root / "webgui" / "package.json",
        root / "docs" / "package.json",
        root / "tui" / "package.json",
    ):
        assert json.loads(package_path.read_text(encoding="utf-8"))["version"] == version

    sidecar = tomllib.loads(
        (root / "sidecars" / "research_flow" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    assert str(sidecar["project"]["version"]) == version

    init_text = (root / "agentic_trader" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    assert match is not None
    assert match.group(1) == version

    release_config = pyproject["tool"]["semantic_release"]
    assert "agentic_trader/__init__.py:__version__" in release_config[
        "version_variables"
    ]
