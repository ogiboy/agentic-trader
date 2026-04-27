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
        """
        Indicates whether the plan targets the stable release channel.
        
        Returns:
            true if the plan's channel is "stable", false otherwise.
        """
        return self.channel == "stable"

    @property
    def is_next(self) -> bool:
        """
        Indicates whether the plan targets the "next" release channel.
        
        Returns:
            `true` if the plan's channel is "next", `false` otherwise.
        """
        return self.channel == "next"

    @property
    def is_beta(self) -> bool:
        """
        Indicates whether the plan's channel is beta.
        
        Returns:
            True if the channel is "beta", False otherwise.
        """
        return self.channel == "beta"


def _run_git(args: list[str]) -> str:
    """
    Run a git command in the repository root and return its trimmed standard output.
    
    Parameters:
        args (list[str]): Arguments passed to the `git` command (e.g., ["rev-parse", "HEAD"]).
    
    Returns:
        str: Trimmed stdout produced by the git command, or an empty string if the git command fails or git is not available.
    """
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
    """
    Read the project's version string from pyproject.toml.
    
    Returns:
        version (str): The value of `project.version` from pyproject.toml.
    """
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _normalize_semver(value: str | None, fallback: str) -> str:
    """
    Normalize a SemVer candidate string and return a validated semantic version or a fallback.
    
    Strips surrounding whitespace, accepts an optional leading "v" (which is removed), and validates the resulting candidate against the module's SemVer pattern. If the candidate is missing or does not match the SemVer pattern, the provided fallback is returned.
    
    Parameters:
        value (str | None): Candidate SemVer string (may start with "v" or be None).
        fallback (str): Value to return when `value` is missing or invalid.
    
    Returns:
        str: A normalized SemVer string without a leading "v", or `fallback` if the candidate is invalid.
    """
    candidate = (value or "").strip()
    match = SEMVER_RE.match(candidate)
    if not match:
        return fallback
    return candidate[1:] if candidate.startswith("v") else candidate


def _semver_core(value: str) -> str:
    """
    Extract the SemVer core (MAJOR.MINOR.PATCH) from a SemVer-compatible version string.
    
    Parameters:
        value (str): A version string expected to follow Semantic Versioning.
    
    Returns:
        core (str): The `MAJOR.MINOR.PATCH` portion of the version.
    
    Raises:
        ValueError: If `value` is not a SemVer-compatible version.
    """
    match = SEMVER_RE.match(value)
    if not match:
        raise ValueError(f"Not a SemVer-compatible version: {value}")
    return match.group("core")


def _sanitize_identifier(value: str) -> str:
    """
    Convert arbitrary text into a lowercase slug suitable for identifiers.
    
    Replaces runs of characters that are not ASCII letters, digits, or hyphens with a single hyphen, strips leading/trailing hyphens, and returns "detached" if the resulting slug is empty.
    
    Parameters:
        value (str): Input text to sanitize.
    
    Returns:
        str: A lowercase identifier composed of letters, digits, and hyphens, or `"detached"` when no valid characters remain.
    """
    slug = re.sub(r"[^0-9A-Za-z-]+", "-", value).strip("-").lower()
    return slug or "detached"


def _build_number(raw: str | None) -> int:
    """
    Selects a positive build number from a raw candidate or Git commit count.
    
    Parameters:
        raw (str | None): Optional candidate build number as a decimal string; used if it represents an integer greater than 0.
    
    Returns:
        int: An integer greater than or equal to 1 to use as the build number.
    """
    if raw and raw.isdecimal() and int(raw) > 0:
        return int(raw)
    commit_count = _run_git(["rev-list", "--count", "HEAD"])
    if commit_count.isdecimal() and int(commit_count) > 0:
        return int(commit_count)
    return 1


def _branch_from_env() -> str:
    """
    Select the active branch or ref name from the environment or git, falling back to "detached".
    
    Checks `GITHUB_HEAD_REF`, then `GITHUB_REF_NAME`, then the current branch from git, then a short commit id from git, and returns `"detached"` if none are available.
    
    Returns:
        str: The resolved branch or ref name, or `"detached"` when unavailable.
    """
    return (
        os.getenv("GITHUB_HEAD_REF")
        or os.getenv("GITHUB_REF_NAME")
        or _run_git(["branch", "--show-current"])
        or _run_git(["rev-parse", "--short", "HEAD"])
        or "detached"
    )


def _sha_from_env() -> str:
    """
    Selects the current commit SHA from CI environment or the local Git repository, falling back to forty zeros.
    
    Returns:
        str: A 40-character commit SHA string: the value of `GITHUB_SHA` if present, the repository HEAD SHA if obtainable, or `"0"*40` otherwise.
    """
    return os.getenv("GITHUB_SHA") or _run_git(["rev-parse", "HEAD"]) or "0" * 40


def _channel_for_ref(branch: str, explicit: str | None, release_ref: str) -> str:
    """
    Selects the release channel for a given branch/ref.
    
    Parameters:
        branch (str): Branch or ref name to evaluate.
        explicit (str | None): Optional override of the channel; expected values: "stable", "next", or "beta".
        release_ref (str): Release tag (if any); a non-empty string indicates a release ref.
    
    Returns:
        str: `"stable"` if the selection indicates the stable channel, `"next"` if the branch indicates a next (vN) branch, or `"beta"` otherwise.
    """
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
    """
    Builds a VersionPlan containing computed semantic, artifact, and file version fields derived from CLI arguments, environment variables, and git.
    
    Parameters:
        args (argparse.Namespace): Parsed CLI arguments. Expected attributes:
            - semantic_tag (str|None): optional semantic candidate to normalize.
            - release_ref (str|None): optional release tag (e.g., "v1.2.3"); when present marks a stable release.
            - ref_name (str|None): optional branch/ref name override.
            - run_number (str|int|None): optional CI run number used as build number.
            - sha (str|None): optional full commit SHA override.
            - channel (str|None): optional channel override; one of "stable", "next", or "beta".
    
    Returns:
        VersionPlan: Immutable plan populated with:
            - base_version, semantic_version, artifact_version, file_version
            - channel, branch, branch_slug, short_sha, build_number
            - release_ref and attach_to_release (True when release_ref is provided)
    """
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
    """
    Write version plan fields as GitHub Actions output key/value lines.
    
    Appends lines of the form `key=value` for every field in `plan` to the file specified by the `GITHUB_OUTPUT`
    environment variable; if `GITHUB_OUTPUT` is not set, writes the same lines to standard output.
    Adds lowercase boolean flags `is_stable`, `is_next`, `is_beta`, and `attach_to_release` to the emitted payload.
    
    Parameters:
        plan (VersionPlan): The computed version plan whose fields will be emitted.
    """
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
    """
    Write a human-readable "Version plan" summary to standard output.
    
    The summary includes the plan's base project version, semantic candidate, artifact version, Windows file version, channel, branch, and build number.
    
    Parameters:
        plan (VersionPlan): Computed version and build context to summarize.
    """
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
    """
    Parse command-line arguments for computing the release/version plan.
    
    Recognized options: --semantic-tag, --release-ref, --ref-name, --run-number, --sha, --channel, and --format.
    
    Parameters:
        argv (list[str]): Argument list to parse (typically sys.argv[1:]).
    
    Returns:
        argparse.Namespace: Parsed arguments with attributes `semantic_tag`, `release_ref`, `ref_name`, `run_number`, `sha`, `channel`, and `format`.
    """
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
    """
    Run the CLI: parse arguments, compute a VersionPlan, validate artifact normalization, and emit the chosen output.
    
    Parameters:
        argv (list[str] | None): Optional argument list to parse; if None, uses process arguments.
    
    Returns:
        int: Exit code (0 on success).
    
    Raises:
        RuntimeError: If the plan's channel is not "stable" and the artifact version contains uppercase characters (i.e., is not normalized to lowercase).
    """
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
