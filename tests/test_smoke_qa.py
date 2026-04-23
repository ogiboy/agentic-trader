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
