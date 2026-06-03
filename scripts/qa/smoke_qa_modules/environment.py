from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

DEFAULT_SONAR_TOKEN_KEYCHAIN_SERVICE = "codex-sonarqube-token"


def current_git_branch(
    repo_root: Path, *, subprocess_module: Any = subprocess
) -> str | None:
    try:
        proc = subprocess_module.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    branch = proc.stdout.strip()
    if proc.returncode != 0 or not branch or branch == "HEAD":
        return None
    return branch


def current_git_commit(
    repo_root: Path, *, subprocess_module: Any = subprocess
) -> str | None:
    try:
        proc = subprocess_module.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    commit = proc.stdout.strip()
    if proc.returncode != 0 or not commit:
        return None
    return commit


def git_worktree_dirty(
    repo_root: Path, *, subprocess_module: Any = subprocess
) -> bool | None:
    try:
        proc = subprocess_module.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())


def resolve_sonar_token(
    *,
    default_service: str = DEFAULT_SONAR_TOKEN_KEYCHAIN_SERVICE,
    env: Mapping[str, str] = os.environ,
    platform: str = sys.platform,
    which: Callable[[str], str | None] = shutil.which,
    subprocess_module: Any = subprocess,
) -> str | None:
    token = env.get("SONAR_TOKEN")
    if token:
        return token
    if platform != "darwin" or which("security") is None:
        return None
    service = env.get("SONAR_TOKEN_KEYCHAIN_SERVICE", default_service)
    account = env.get("SONAR_TOKEN_KEYCHAIN_ACCOUNT", env.get("USER", ""))
    if not account:
        return None
    try:
        proc = subprocess_module.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                service,
                "-w",
            ],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def resolve_managed_conda_env_name(repo_root: Path) -> str | None:
    manifest_path = repo_root / ".codex" / "environments" / "environment.toml"
    if not manifest_path.exists():
        return None
    manifest = manifest_path.read_text(encoding="utf-8", errors="replace")
    marker = "conda activate "
    index = manifest.find(marker)
    if index == -1:
        return None
    remainder = manifest[index + len(marker) :].lstrip()
    lines = remainder.splitlines()
    if not lines:
        return None
    env_name = lines[0].strip().strip("'").strip('"')
    return env_name or None


def resolve_smoke_python(
    repo_root: Path,
    *,
    env: Mapping[str, str] = os.environ,
    executable: str = sys.executable,
) -> str:
    candidates: list[Path] = []

    explicit_python = env.get("AGENTIC_TRADER_PYTHON")
    if explicit_python:
        candidates.append(Path(explicit_python).expanduser())

    virtual_env = env.get("VIRTUAL_ENV")
    if virtual_env:
        candidates.append(Path(virtual_env) / "bin" / "python")

    candidates.append(repo_root / ".venv" / "bin" / "python")

    conda_prefix = env.get("CONDA_PREFIX")
    conda_default_env = env.get("CONDA_DEFAULT_ENV")
    if conda_prefix and conda_default_env and conda_default_env != "base":
        candidates.append(Path(conda_prefix) / "bin" / "python")

    managed_env_name = resolve_managed_conda_env_name(repo_root)
    if managed_env_name:
        conda_roots: list[Path] = []
        conda_exe = env.get("CONDA_EXE")
        if conda_exe:
            conda_roots.append(Path(conda_exe).resolve().parent.parent)
        home = Path.home()
        conda_roots.extend(
            [
                home / "miniconda3",
                home / "anaconda3",
                Path("/opt/anaconda3"),
                Path("/usr/local/anaconda3"),
            ]
        )
        for conda_root in conda_roots:
            candidates.append(conda_root / "envs" / managed_env_name / "bin" / "python")

    candidates.append(Path(executable))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return executable


def resolve_agentic_trader_executable(
    smoke_python: str,
    *,
    env: Mapping[str, str] = os.environ,
    which: Callable[[str], str | None] = shutil.which,
) -> str | None:
    candidates: list[Path] = [Path(smoke_python).with_name("agentic-trader")]
    conda_prefix = env.get("CONDA_PREFIX")
    if conda_prefix:
        candidates.append(Path(conda_prefix) / "bin" / "agentic-trader")
    which_path = which("agentic-trader")
    if which_path is not None:
        candidates.append(Path(which_path))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
