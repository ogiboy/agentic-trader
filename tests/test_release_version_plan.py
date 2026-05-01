from __future__ import annotations

from argparse import Namespace
import importlib.util
from pathlib import Path
import sys
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

    plan = version_plan.build_plan(
        _args(semantic_tag=None, release_ref="v0.9.0", ref_name="v0.9.0")
    )

    assert plan.channel == "stable"
    assert plan.release_ref == "v0.9.0"
    assert plan.artifact_version == "v0.9.0"
    assert plan.attach_to_release is True
