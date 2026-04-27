#!/usr/bin/env python3
"""Compute SemVer-compatible release and branch build identity.

The stable project version remains `MAJOR.MINOR.PATCH`. Branch and CI build
identity is expressed as SemVer prerelease/build metadata so preview artifacts
can be versioned without inventing a fourth SemVer core segment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEMVER_RE = re.compile(
    r"^v?(?P<core>\d+\.\d+\.\d+)"
    r"(?P<prerelease>-[0-9A-Za-z.-]+)?"
    r"(?P<metadata>\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True)
class VersionPlan:
    base_version: str
    semantic_version: str
    artifact_version: str
    file_version: str
    channel: str
    branch: str
    branch_slug: str
    short_sha: str
    build_number: int
    release_ref: str
    attach_to_release: bool

    @property
    def is_stable(self) -> bool:
        return self.channel == "stable"

    @property
    def is_next(self) -> bool:
        return self.channel == "next"

    @property
    def is_beta(self) -> bool:
        return self.channel == "beta"


def _run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(  # noqa: S603
            ["git", *args],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _read_project_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _normalize_semver(value: str | None, fallback: str) -> str:
    candidate = (value or "").strip()
    match = SEMVER_RE.match(candidate)
    if not match:
        return fallback
    return candidate[1:] if candidate.startswith("v") else candidate


def _semver_core(value: str) -> str:
    match = SEMVER_RE.match(value)
    if not match:
        raise ValueError(f"Not a SemVer-compatible version: {value}")
    return match.group("core")


def _sanitize_identifier(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z-]+", "-", value).strip("-").lower()
    return slug or "detached"


def _build_number(raw: str | None) -> int:
    if raw and raw.isdecimal() and int(raw) > 0:
        return int(raw)
    commit_count = _run_git(["rev-list", "--count", "HEAD"])
    if commit_count.isdecimal() and int(commit_count) > 0:
        return int(commit_count)
    return 1


def _branch_from_env() -> str:
    return (
        os.getenv("GITHUB_HEAD_REF")
        or os.getenv("GITHUB_REF_NAME")
        or _run_git(["branch", "--show-current"])
        or _run_git(["rev-parse", "--short", "HEAD"])
        or "detached"
    )


def _sha_from_env() -> str:
    return os.getenv("GITHUB_SHA") or _run_git(["rev-parse", "HEAD"]) or "0" * 40


def _channel_for_ref(branch: str, explicit: str | None, release_ref: str) -> str:
    if explicit:
        return explicit
    if release_ref:
        return "stable"
    if branch == "main":
        return "stable"
    if re.fullmatch(r"[Vv]\d+", branch):
        return "next"
    return "beta"


def build_plan(args: argparse.Namespace) -> VersionPlan:
    base_version = _read_project_version()
    release_ref = (args.release_ref or "").strip()
    branch = args.ref_name or _branch_from_env()
    sha = args.sha or _sha_from_env()
    short_sha = sha[:7]
    build_number = _build_number(args.run_number or os.getenv("GITHUB_RUN_NUMBER"))
    semantic_version = _normalize_semver(args.semantic_tag or release_ref, base_version)
    core = _semver_core(semantic_version)
    channel = _channel_for_ref(branch, args.channel, release_ref)
    branch_slug = _sanitize_identifier(branch)

    if channel == "stable":
        artifact_version = f"v{semantic_version}"
    elif channel == "next":
        artifact_version = f"v{core}-next.{build_number}+g{short_sha}"
    else:
        artifact_version = f"v{core}-beta.{build_number}+g{short_sha}"

    major, minor, patch = core.split(".")
    file_version = f"{major}.{minor}.{patch}.{build_number}"

    return VersionPlan(
        base_version=base_version,
        semantic_version=semantic_version,
        artifact_version=artifact_version,
        file_version=file_version,
        channel=channel,
        branch=branch,
        branch_slug=branch_slug,
        short_sha=short_sha,
        build_number=build_number,
        release_ref=release_ref,
        attach_to_release=bool(release_ref),
    )


def _emit_github_outputs(plan: VersionPlan) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    lines = []
    payload = {
        **asdict(plan),
        "is_stable": str(plan.is_stable).lower(),
        "is_next": str(plan.is_next).lower(),
        "is_beta": str(plan.is_beta).lower(),
        "attach_to_release": str(plan.attach_to_release).lower(),
    }
    for key, value in payload.items():
        lines.append(f"{key}={value}")

    text = "\n".join(lines) + "\n"
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write(text)
    else:
        sys.stdout.write(text)


def _emit_summary(plan: VersionPlan) -> None:
    sys.stdout.write(
        "\n".join(
            [
                "### Version plan",
                "",
                f"- Base project version: `{plan.base_version}`",
                f"- Semantic candidate: `v{plan.semantic_version}`",
                f"- Artifact version: `{plan.artifact_version}`",
                f"- Windows file version: `{plan.file_version}`",
                f"- Channel: `{plan.channel}`",
                f"- Branch: `{plan.branch}`",
                f"- Build number: `{plan.build_number}`",
            ]
        )
        + "\n"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-tag", help="Next semantic-release tag preview")
    parser.add_argument("--release-ref", help="Release tag to package, for example v0.2.0")
    parser.add_argument("--ref-name", help="Branch or tag ref name")
    parser.add_argument("--run-number", help="CI run number for prerelease/build identity")
    parser.add_argument("--sha", help="Commit SHA for build metadata")
    parser.add_argument(
        "--channel",
        choices=["stable", "next", "beta"],
        help="Override channel detection",
    )
    parser.add_argument(
        "--format",
        choices=["github", "json", "summary"],
        default="json",
        help="Output format",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    plan = build_plan(args)
    if plan.channel != "stable" and plan.artifact_version != plan.artifact_version.lower():
        raise RuntimeError(f"Artifact version is not normalized: {plan.artifact_version}")

    if args.format == "github":
        _emit_github_outputs(plan)
    elif args.format == "summary":
        _emit_summary(plan)
    else:
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
