import subprocess
from pathlib import Path

from scripts.qa import smoke_qa


def test_claim_artifacts_dir_uses_unique_suffix_for_existing_label(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(smoke_qa, "ARTIFACTS_ROOT", tmp_path)

    first = smoke_qa._claim_artifacts_dir("smoke-fixed")
    second = smoke_qa._claim_artifacts_dir("smoke-fixed")

    assert first == tmp_path / "smoke-fixed"
    assert second == tmp_path / "smoke-fixed-2"
    assert first.is_dir()
    assert second.is_dir()


def test_ink_settings_capture_issues_accepts_compact_settings_view() -> None:
    output = "\n".join(
        [
            "AGENTIC TRADER // INK CONTROL ROOM",
            "page 7/7: Settings",
            "RECENT RUNS",
            "Risk / Style: conservative / swing",
            "Behavior / Strictness: capital_preservation / strict",
            "Mode: preview",
        ]
    )

    assert smoke_qa._ink_settings_capture_issues(output) == []


def test_ink_settings_capture_issues_reports_missing_markers() -> None:
    issues = smoke_qa._ink_settings_capture_issues("page 7/7: Settings\nMode: preview")

    assert "recent runs panel missing" in issues
    assert "risk/style preference line missing" in issues
    assert "behavior/strictness line missing" in issues


def test_run_ink_settings_navigation_reports_tmux_session_failures(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(smoke_qa.shutil, "which", lambda name: "/usr/bin/tmux")

    def _fake_run(*args, **kwargs):
        command = args[0]
        if command[1] == "new-session":
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command,
                stderr="permission denied",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(smoke_qa.subprocess, "run", _fake_run)

    result = smoke_qa.run_ink_settings_navigation(
        smoke_qa.SmokeContext(artifacts_dir=tmp_path),
        "agentic-trader",
    )

    assert not result.passed
    assert "tmux new-session failed" in result.details


def test_resolve_smoke_python_prefers_repo_uv_venv(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    python_path = repo_root / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)

    monkeypatch.setattr(smoke_qa, "REPO_ROOT", repo_root)
    monkeypatch.delenv("AGENTIC_TRADER_PYTHON", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("CONDA_DEFAULT_ENV", raising=False)
    monkeypatch.delenv("CONDA_EXE", raising=False)

    assert smoke_qa._resolve_smoke_python() == str(python_path)


def test_resolve_smoke_python_falls_back_to_legacy_repo_managed_conda_env(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    manifest_dir = repo_root / ".codex" / "environments"
    manifest_dir.mkdir(parents=True)
    manifest_dir.joinpath("environment.toml").write_text(
        "[setup]\nscript = '''\nconda activate trader\n'''\n",
        encoding="utf-8",
    )

    conda_root = tmp_path / "conda"
    python_path = conda_root / "envs" / "trader" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)

    conda_exe = conda_root / "bin" / "conda"
    conda_exe.parent.mkdir(parents=True)
    conda_exe.write_text("#!/bin/sh\n", encoding="utf-8")
    conda_exe.chmod(0o755)

    monkeypatch.setattr(smoke_qa, "REPO_ROOT", repo_root)
    monkeypatch.delenv("AGENTIC_TRADER_PYTHON", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", "/opt/anaconda3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")
    monkeypatch.setenv("CONDA_EXE", str(conda_exe))

    assert smoke_qa._resolve_smoke_python() == str(python_path)
