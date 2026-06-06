from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from scripts.qa.smoke_qa_modules.common import (
    artifact_path,
    skip_result,
    write_artifact,
)
from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext


def _empty_issues() -> list[str]:
    return []


def _ink_navigation_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    env["CI"] = "false"
    return env


@dataclass
class InkNavigationCapture:
    overview_capture: str = ""
    settings_capture: str = ""
    issues: list[str] = field(default_factory=_empty_issues)


def ink_settings_capture_issues(output: str) -> list[str]:
    required_markers = {
        "page 7/7: Settings": "settings page header missing",
        "RECENT RUNS": "recent runs panel missing",
        "Risk / Style:": "risk/style preference line missing",
        "Behavior / Strictness:": "behavior/strictness line missing",
        "Mode: preview": "instruction composer mode missing",
    }
    return [issue for marker, issue in required_markers.items() if marker not in output]


def run_ink_settings_navigation(
    context: SmokeContext,
    command: str,
    *,
    repo_root: Path,
    subprocess_module: Any = subprocess,
    shutil_module: Any,
    timeout: int = 30,
) -> CheckResult:
    name = "ink_settings_navigation"
    artifact = artifact_path(context, name)
    tmux_path = shutil_module.which("tmux")
    if tmux_path is None:
        return skip_result(context, name, "tmux not found on PATH")

    session_name = f"agentic-trader-ink-{int(time.time() * 1000)}-{uuid.uuid4().hex}"
    launch_command = f"cd {shlex.quote(str(repo_root))} && {shlex.quote(command)} tui"
    capture = _run_tmux_navigation(
        tmux_path,
        session_name,
        launch_command,
        repo_root=repo_root,
        subprocess_module=subprocess_module,
        timeout=timeout,
    )
    _write_ink_navigation_artifact(
        artifact,
        command,
        repo_root=repo_root,
        capture=capture,
    )
    return _ink_navigation_result(name, artifact, capture.issues)


def _run_tmux_navigation(
    tmux_path: str,
    session_name: str,
    launch_command: str,
    *,
    repo_root: Path,
    subprocess_module: Any,
    timeout: int,
) -> InkNavigationCapture:
    capture = InkNavigationCapture()
    try:
        _start_tmux_session(
            tmux_path,
            session_name,
            launch_command,
            timeout,
            capture.issues,
            repo_root=repo_root,
            subprocess_module=subprocess_module,
        )
        capture.overview_capture = _wait_for_ink_overview(
            tmux_path,
            session_name,
            timeout,
            repo_root=repo_root,
            subprocess_module=subprocess_module,
        )
        _capture_settings_page_if_ready(
            capture,
            tmux_path,
            session_name,
            repo_root=repo_root,
            subprocess_module=subprocess_module,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if isinstance(exc.stderr, str) else str(exc.stderr)
        capture.issues.append(
            f"tmux new-session failed with code {exc.returncode}: {stderr or 'no stderr'}"
        )
    except Exception as exc:
        capture.issues.append(f"exception={exc}")
    finally:
        subprocess_module.run(
            [tmux_path, "kill-session", "-t", session_name],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
            env=_ink_navigation_env(),
        )
    return capture


def _capture_settings_page_if_ready(
    capture: InkNavigationCapture,
    tmux_path: str,
    session_name: str,
    *,
    repo_root: Path,
    subprocess_module: Any,
    timeout: int,
) -> None:
    if not _ink_overview_ready(capture.overview_capture):
        capture.issues.append("ink overview did not render in tmux")
        return
    if capture.issues:
        return
    capture.settings_capture = _open_and_capture_ink_settings(
        tmux_path,
        session_name,
        timeout,
        capture.issues,
        repo_root=repo_root,
        subprocess_module=subprocess_module,
    )
    _send_tmux_key(
        tmux_path,
        session_name,
        "q",
        repo_root=repo_root,
        subprocess_module=subprocess_module,
        timeout=timeout,
    )
    time.sleep(1.0)


def _write_ink_navigation_artifact(
    artifact: Path,
    command: str,
    *,
    repo_root: Path,
    capture: InkNavigationCapture,
) -> None:
    write_artifact(
        artifact,
        f"$ {command} tui (tmux compact navigation)\n"
        f"cwd: {repo_root}\n"
        f"issues: {json.dumps(capture.issues, indent=2)}\n\n"
        f"OVERVIEW_CAPTURE:\n{capture.overview_capture}\n\n"
        f"SETTINGS_CAPTURE:\n{capture.settings_capture}\n",
    )


def _ink_navigation_result(
    name: str, artifact: Path, issues: list[str]
) -> CheckResult:
    return CheckResult(
        name=name,
        passed=not issues,
        details="tmux_settings_navigation_ok" if not issues else "; ".join(issues),
        artifact=str(artifact),
    )


def _tmux_capture_pane(
    tmux_path: str,
    session_name: str,
    *,
    repo_root: Path,
    subprocess_module: Any,
    timeout: int,
) -> str:
    proc = cast(
        subprocess.CompletedProcess[str],
        subprocess_module.run(
            [tmux_path, "capture-pane", "-pt", f"{session_name}:0.0"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=_ink_navigation_env(),
        ),
    )
    return proc.stdout or ""


def _start_tmux_session(
    tmux_path: str,
    session_name: str,
    launch_command: str,
    timeout: int,
    issues: list[str],
    *,
    repo_root: Path,
    subprocess_module: Any,
) -> None:
    launch_proc = cast(
        subprocess.CompletedProcess[str],
        subprocess_module.run(
            [
                tmux_path,
                "new-session",
                "-d",
                "-s",
                session_name,
                "-x",
                "110",
                "-y",
                "30",
                launch_command,
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
            env=_ink_navigation_env(),
        ),
    )
    if launch_proc.stderr:
        issues.append(f"tmux new-session stderr: {launch_proc.stderr.strip()}")


def _wait_for_ink_overview(
    tmux_path: str,
    session_name: str,
    timeout: int,
    *,
    repo_root: Path,
    subprocess_module: Any,
) -> str:
    capture = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        capture = _tmux_capture_pane(
            tmux_path,
            session_name,
            repo_root=repo_root,
            subprocess_module=subprocess_module,
            timeout=timeout,
        )
        if _ink_overview_ready(capture):
            return capture
        time.sleep(0.5)
    return capture


def _ink_overview_ready(capture: str) -> bool:
    return (
        "AGENTIC TRADER // INK CONTROL ROOM" in capture
        and "page " in capture
        and "Last refresh:" in capture
    )


def _send_tmux_key(
    tmux_path: str,
    session_name: str,
    key: str,
    *,
    repo_root: Path,
    subprocess_module: Any,
    timeout: int,
) -> None:
    subprocess_module.run(
        [tmux_path, "send-keys", "-t", f"{session_name}:0.0", key],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=_ink_navigation_env(),
    )


def _open_and_capture_ink_settings(
    tmux_path: str,
    session_name: str,
    timeout: int,
    issues: list[str],
    *,
    repo_root: Path,
    subprocess_module: Any,
) -> str:
    _send_tmux_key(
        tmux_path,
        session_name,
        "7",
        repo_root=repo_root,
        subprocess_module=subprocess_module,
        timeout=timeout,
    )
    capture = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        capture = _tmux_capture_pane(
            tmux_path,
            session_name,
            repo_root=repo_root,
            subprocess_module=subprocess_module,
            timeout=timeout,
        )
        current_issues = ink_settings_capture_issues(capture)
        if not current_issues:
            return capture
        time.sleep(0.5)
    issues.extend(ink_settings_capture_issues(capture))
    return capture
