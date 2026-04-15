#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pexpect


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = REPO_ROOT / ".ai" / "qa" / "artifacts"
TRACEBACK_MARKERS = ("Traceback (most recent call last):", "KeyboardInterrupt")
RENDER_SECONDS = 3.0
EXIT_WAIT_SECONDS = 2.0
TUI_READY_PATTERNS = (
    r"Agentic Trader",
    r"AGENTIC TRADER",
    r"CONTROL ROOM",
    r"Main Menu",
    r"Select action",
    r"Overview",
)
DEFAULT_SONAR_HOST_URL = "http://localhost:9000"
DEFAULT_SONAR_PROJECT_KEY = "agentic-trader-dev"


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str
    artifact: str | None = None


@dataclass(frozen=True)
class SmokeContext:
    artifacts_dir: Path


def _artifact_path(context: SmokeContext, name: str) -> Path:
    """
    Return the Path to a log artifact for a named check, creating the artifacts directory if necessary.
    
    Parameters:
        context (SmokeContext): Context containing the artifacts_dir where logs are stored.
        name (str): Base name for the artifact file (no extension).
    
    Returns:
        Path: Path to the artifact file at `<artifacts_dir>/<name>.log`.
    """
    context.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return context.artifacts_dir / f"{name}.log"


def _coverage_path(context: SmokeContext) -> Path:
    """
    Return the file path for the coverage XML artifact inside the provided context's artifacts directory.
    
    Parameters:
        context (SmokeContext): Context containing the artifacts_dir.
    
    Returns:
        Path: Path to coverage.xml within the artifacts directory.
    """
    return context.artifacts_dir / "coverage.xml"


def _command_display(command: list[str]) -> str:
    """
    Format a command and its arguments as a single space-separated string for display.
    
    Returns:
        The command elements joined into a single space-separated string.
    """
    return " ".join(command)


def _resolve_agentic_trader_executable() -> str | None:
    """
    Locate the `agentic-trader` executable, preferring a copy next to the running Python interpreter, then in the active conda environment's bin directory, and finally on the system PATH.
    
    Returns:
        The filesystem path to an executable `agentic-trader` as a string if one is found and executable, or `None` if no suitable executable is found.
    """
    candidates: list[Path] = [Path(sys.executable).with_name("agentic-trader")]
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidates.append(Path(conda_prefix) / "bin" / "agentic-trader")
    which_path = shutil.which("agentic-trader")
    if which_path is not None:
        candidates.append(Path(which_path))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _write_artifact(path: Path, content: str) -> None:
    """
    Write text content to a file, creating or overwriting it.
    
    The file is written using UTF-8 encoding; encoding errors are handled by replacing invalid characters.
    
    Parameters:
        path (Path): Destination file path to write the artifact to.
        content (str): Text content to write.
    """
    path.write_text(content, encoding="utf-8", errors="replace")


def _output_has_traceback(output: str) -> bool:
    """
    Check whether the given captured output contains any known traceback or interrupt markers.
    
    Parameters:
        output (str): Combined stdout and stderr text to scan for error markers.
    
    Returns:
        True if any marker from TRACEBACK_MARKERS appears in `output`, False otherwise.
    """
    return any(marker in output for marker in TRACEBACK_MARKERS)


def run_command_capture(
    context: SmokeContext,
    name: str,
    command: list[str],
    *,
    timeout: int = 30,
    require_json_stdout: bool = False,
    display: str | None = None,
) -> CheckResult:
    """
    Run a command, record its stdout/stderr and metadata to a per-check artifact, and return a CheckResult describing success or failure.
    
    Parameters:
        context (SmokeContext): Context whose artifacts_dir is used to write the per-check log.
        name (str): Short identifier used to name the artifact and the resulting CheckResult.
        command (list[str]): Command and arguments to execute.
        timeout (int): Seconds to wait before terminating the command.
        require_json_stdout (bool): If True, the check also requires that stdout parses as JSON.
        display (str | None): Human-friendly command string to record in the artifact; if None the command list is joined.
    
    Returns:
        CheckResult: Contains the check name, whether it passed, human-readable details, and the artifact path.
            `passed` is True only if the process exit code is 0, the combined stdout/stderr contains no traceback markers, and (when requested) stdout is valid JSON.
            `details` includes `exit_code=<n>` and, when JSON parsing fails, `invalid_json=<error>`.
    
    Notes:
        On exception while running the subprocess, an artifact is written containing the exception and a failing CheckResult is returned.
    """
    artifact = _artifact_path(context, name)
    display_command = display or _command_display(command)
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        _write_artifact(artifact, f"$ {display_command}\n\nEXCEPTION:\n{exc}\n")
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exc}",
            artifact=str(artifact),
        )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    json_error: str | None = None
    if require_json_stdout:
        try:
            json.loads(stdout)
        except json.JSONDecodeError as exc:
            json_error = str(exc)

    artifact_body = (
        f"$ {display_command}\n"
        f"cwd: {REPO_ROOT}\n"
        f"exit_code: {proc.returncode}\n\n"
        f"STDOUT:\n{stdout}\n\n"
        f"STDERR:\n{stderr}"
    )
    if json_error is not None:
        artifact_body += f"\n\nJSON_ERROR:\n{json_error}\n"
    _write_artifact(artifact, artifact_body)

    passed = proc.returncode == 0 and not _output_has_traceback(stdout + stderr)
    if require_json_stdout:
        passed = passed and json_error is None

    details = f"exit_code={proc.returncode}"
    if json_error is not None:
        details += f"; invalid_json={json_error}"
    return CheckResult(
        name=name,
        passed=passed,
        details=details,
        artifact=str(artifact),
    )


def run_dashboard_contract_check(
    context: SmokeContext, command: list[str], *, timeout: int = 30
) -> CheckResult:
    """
    Validate dashboard JSON fields that operator surfaces rely on.

    This lightweight contract check intentionally tolerates an empty runtime
    database, but it fails if the dashboard payload drops the runtime-mode or
    market-context sections that newer CLI, Ink, and observer surfaces consume.
    """
    name = "dashboard_contract"
    artifact = _artifact_path(context, name)
    display_command = _command_display(command)
    issues: list[str] = []
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        payload = json.loads(proc.stdout or "{}")
    except Exception as exc:
        _write_artifact(artifact, f"$ {display_command}\n\nEXCEPTION:\n{exc}\n")
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exc}",
            artifact=str(artifact),
        )

    if proc.returncode != 0:
        issues.append(f"exit_code={proc.returncode}")
    if not isinstance(payload.get("doctor"), dict):
        issues.append("missing doctor object")
    elif "runtime_mode" not in payload["doctor"]:
        issues.append("doctor.runtime_mode missing")
    if not isinstance(payload.get("status"), dict):
        issues.append("missing status object")
    elif "runtime_mode" not in payload["status"]:
        issues.append("status.runtime_mode missing")
    if not isinstance(payload.get("marketContext"), dict):
        issues.append("marketContext section missing")
    else:
        market_context = payload["marketContext"]
        if "contextPack" not in market_context:
            issues.append("marketContext.contextPack missing")
        else:
            context_pack = market_context["contextPack"]
            if context_pack is not None and not isinstance(context_pack, dict):
                issues.append("marketContext.contextPack has wrong type (expected dict or null)")
            elif isinstance(context_pack, dict):
                for field in ("summary", "bars_analyzed", "horizons"):
                    if field not in context_pack:
                        issues.append(f"marketContext.contextPack.{field} missing")

    _write_artifact(
        artifact,
        (
            f"$ {display_command}\n"
            f"cwd: {REPO_ROOT}\n"
            f"issues: {json.dumps(issues, indent=2)}\n\n"
            f"STDOUT:\n{proc.stdout}\n\n"
            f"STDERR:\n{proc.stderr}"
        ),
    )
    return CheckResult(
        name=name,
        passed=not issues and not _output_has_traceback(proc.stdout + proc.stderr),
        details="contract_ok" if not issues else "; ".join(issues),
        artifact=str(artifact),
    )


def _spawn_env() -> dict[str, str]:
    """
    Provide an environment dictionary for spawning interactive child processes, ensuring a default terminal type.
    
    Returns:
        env (dict[str, str]): A copy of the current process environment with `TERM` set to `"xterm-256color"` when it was not already defined.
    """
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    return env


def _drain_child(child: pexpect.spawn, seconds: float) -> None:
    """
    Consume and discard any pending output from a spawned pexpect child for up to the given number of seconds.
    
    This repeatedly performs short, non-blocking expect calls to read available data while the child process is alive, stopping when the deadline is reached or if an OSError occurs.
    
    Parameters:
        child (pexpect.spawn): The spawned child process whose output should be drained.
        seconds (float): Maximum time in seconds to attempt draining output.
    """
    deadline = time.monotonic() + seconds
    while child.isalive() and time.monotonic() < deadline:
        try:
            child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=0.25)
        except OSError:
            break


def _close_interactive_child(child: pexpect.spawn) -> str:
    """
    Attempt to close a spawned pexpect child process by sending a quit key, then Ctrl-C, and finally force-terminating if necessary.
    
    Parameters:
        child (pexpect.spawn): The spawned child process to close.
    
    Returns:
        A string describing how the child exited:
        - "exited_after_render": child was already not alive on entry.
        - "exited_before_q": child exited while attempting to send "q".
        - "sent_q": successfully sent "q" and the child exited (or is the method used if it later exited).
        - "exited_before_ctrl_c": child exited while attempting to send Ctrl-C.
        - "sent_ctrl_c": successfully sent Ctrl-C and the child exited (or is the method used if it later exited).
        - "force_terminated": child remained alive after both signals and was forcibly terminated.
    """
    if not child.isalive():
        return "exited_after_render"
    try:
        child.send("q")
        exit_method = "sent_q"
    except OSError:
        return "exited_before_q"
    _drain_child(child, EXIT_WAIT_SECONDS)

    if not child.isalive():
        return exit_method
    try:
        child.sendcontrol("c")
        exit_method = "sent_ctrl_c"
    except OSError:
        return "exited_before_ctrl_c"
    _drain_child(child, EXIT_WAIT_SECONDS)

    if child.isalive():
        child.terminate(force=True)
        time.sleep(0.2)
        return "force_terminated"
    return exit_method


def _write_interactive_artifact(
    artifact: Path,
    display_command: str,
    exit_method: str,
    child: pexpect.spawn,
    output: str,
) -> None:
    """
    Write an artifact file summarizing a spawned interactive TUI session.
    
    Parameters:
        artifact (Path): Path to the artifact file to create (UTF-8 text).
        display_command (str): Human-readable command string shown at the top of the artifact.
        exit_method (str): How the session was terminated (e.g., "exited_after_render", "sent_ctrl_c", "force_terminated").
        child (pexpect.spawn): The spawned process object whose exitstatus and signalstatus will be recorded.
        output (str): Captured terminal output to include under the "CAPTURE" section.
    """
    _write_artifact(
        artifact,
        f"$ {display_command}\n"
        f"cwd: {REPO_ROOT}\n"
        f"exit_method: {exit_method}\n"
        f"exitstatus: {child.exitstatus}\n"
        f"signalstatus: {child.signalstatus}\n\n"
        f"CAPTURE:\n{output}\n",
    )


def _interactive_check_result(
    name: str, artifact: Path, exit_method: str, child: pexpect.spawn, output: str
) -> CheckResult:
    """
    Evaluate the captured interactive session and produce a CheckResult that indicates whether the TUI run passed smoke checks.
    
    Parameters:
        name (str): Logical name of the check.
        artifact (Path): Path to the artifact file containing the saved session.
        exit_method (str): How the session was terminated (e.g., "exited_after_render", "sent_ctrl_c", "force_terminated").
        child (pexpect.spawn): Spawned process object; its exitstatus is used to determine failures.
        output (str): Captured terminal output from the session.
    
    Returns:
        CheckResult: Contains `passed` set to `false` when any of the following are observed: the output is empty or whitespace, a traceback is detected in output, the process exited with a nonzero code (except the special-case of Ctrl-C exit with status 130), or the session was force-terminated; otherwise `passed` is `true`. The `details` field describes the exit method and failure reason, and `artifact` is the artifact path as a string.
    """
    if not output.strip():
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; no_visible_output",
            artifact=str(artifact),
        )
    if _output_has_traceback(output):
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; traceback_detected",
            artifact=str(artifact),
        )
    ctrl_c_exit = exit_method == "sent_ctrl_c" and child.exitstatus == 130
    if child.exitstatus not in (None, 0) and not ctrl_c_exit:
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; exit_code={child.exitstatus}",
            artifact=str(artifact),
        )
    if exit_method == "force_terminated":
        return CheckResult(
            name=name,
            passed=False,
            details=exit_method,
            artifact=str(artifact),
        )
    return CheckResult(
        name=name,
        passed=True,
        details=exit_method,
        artifact=str(artifact),
    )


def _wait_for_tui_ready(child: pexpect.spawn, *, timeout: int) -> str:
    """
    Wait for a concrete rendering marker that indicates the spawned TUI is actually alive.

    A visible byte stream alone is not enough for smoke QA because startup errors can
    print output before the operator surface renders. These patterns are deliberately
    broad across the Ink and Rich surfaces while still requiring an Agentic Trader
    UI marker rather than arbitrary child output.
    """
    matched_index = child.expect(list(TUI_READY_PATTERNS), timeout=timeout)
    return TUI_READY_PATTERNS[matched_index]


def run_tui_open_and_quit(
    context: SmokeContext,
    name: str,
    command: str,
    args: list[str],
    *,
    display: str | None = None,
    timeout: int = 20,
) -> CheckResult:
    """
    Launches a TUI command, attempts to render and quit it, captures the terminal session to an artifact, and returns a pass/fail check result.
    
    The spawned process runs in the repository root with a fixed terminal size; its captured output, exit method, and exit codes are persisted to an artifact file named for this check. The CheckResult indicates success when the TUI produced visible output, contains no traceback markers, and exited cleanly (with a special-case allowance for Ctrl-C). On error or exception the artifact contains the exception and any captured output.
    
    Parameters:
        display (str | None): Optional human-readable command string to record in the artifact; when omitted a display string is derived from `command` and `args`.
        timeout (int): Seconds to use as the spawn/read timeout for the interactive session.
    
    Returns:
        CheckResult: Result for the named smoke check; `passed` is `true` when the interactive run met the success criteria, `false` otherwise. The `artifact` field points to the written log file and `details` explains failures when present.
    """
    artifact = _artifact_path(context, name)
    display_command = display or _command_display([command, *args])
    log = io.StringIO()
    child: pexpect.spawn | None = None

    try:
        child = pexpect.spawn(
            command,
            args=args,
            cwd=str(REPO_ROOT),
            env=cast(Any, _spawn_env()),
            encoding="utf-8",
            timeout=timeout,
            dimensions=(36, 120),
        )
        child.logfile_read = log
        ready_signal = _wait_for_tui_ready(child, timeout=timeout)
        _drain_child(child, RENDER_SECONDS)
        exit_method = _close_interactive_child(child)
        child.close(force=False)

        output = log.getvalue()
        _write_interactive_artifact(artifact, display_command, exit_method, child, output)
        result = _interactive_check_result(name, artifact, exit_method, child, output)
        if not result.passed:
            return result
        return CheckResult(
            name=result.name,
            passed=True,
            details=f"{result.details}; ready={ready_signal}",
            artifact=result.artifact,
        )
    except pexpect.TIMEOUT as exc:
        output = log.getvalue()
        if child is not None and child.isalive():
            child.terminate(force=True)
        _write_artifact(
            artifact,
            f"$ {display_command}\n"
            f"cwd: {REPO_ROOT}\n"
            f"failure: tui_ready_timeout\n"
            f"timeout: {timeout}\n"
            f"exception: {exc}\n\n"
            f"CAPTURE:\n{output}\n",
        )
        return CheckResult(
            name=name,
            passed=False,
            details="tui_ready_timeout",
            artifact=str(artifact),
        )
    except pexpect.EOF as exc:
        output = log.getvalue()
        _write_artifact(
            artifact,
            f"$ {display_command}\n"
            f"cwd: {REPO_ROOT}\n"
            f"failure: tui_ready_eof\n"
            f"exception: {exc}\n\n"
            f"CAPTURE:\n{output}\n",
        )
        return CheckResult(
            name=name,
            passed=False,
            details="tui_ready_eof",
            artifact=str(artifact),
        )
    except Exception as exc:
        output = log.getvalue()
        if child is not None and child.isalive():
            child.terminate(force=True)
        _write_artifact(
            artifact,
            f"$ {display_command}\n"
            f"cwd: {REPO_ROOT}\n"
            f"exception: {exc}\n\n"
            f"CAPTURE:\n{output}\n",
        )
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exc}",
            artifact=str(artifact),
        )


def _skip_result(context: SmokeContext, name: str, details: str) -> CheckResult:
    """
    Create and record a skipped check result.
    
    Parameters:
        context (SmokeContext): Artifact directory/context used to store the skip log.
        name (str): Identifier for the check; used to name the artifact file and the result.
        details (str): Human-readable reason for skipping the check.
    
    Returns:
        CheckResult: A result with `passed=True`, `details` starting with "skipped; " followed by `details`,
        and `artifact` set to the path of the written skip log.
    """
    artifact = _artifact_path(context, name)
    _write_artifact(artifact, f"SKIPPED: {details}\n")
    return CheckResult(
        name=name,
        passed=True,
        details=f"skipped; {details}",
        artifact=str(artifact),
    )


def _fail_result(context: SmokeContext, name: str, details: str) -> CheckResult:
    """
    Create and record a hard-failing check result for required QA prerequisites.
    """
    artifact = _artifact_path(context, name)
    _write_artifact(artifact, f"FAILED: {details}\n")
    return CheckResult(
        name=name,
        passed=False,
        details=details,
        artifact=str(artifact),
    )


def _require_executable(context: SmokeContext, name: str) -> CheckResult | None:
    """
    Verify that a required executable is available and record a failing artifact if it is not.
    
    Checks availability of `name`; for `"agentic-trader"` it uses the resolver that checks next to the Python interpreter, the active conda prefix, and PATH, otherwise it uses `shutil.which`. If the executable is missing, writes `<name>_missing.log` into the artifacts directory and returns a failing CheckResult describing the missing executable.
    
    Parameters:
        context (SmokeContext): Context containing the artifacts directory for written diagnostics.
        name (str): The executable name to verify.
    
    Returns:
        None if the executable was found; a failing CheckResult with `details` and `artifact` when it is not.
    """
    if name == "agentic-trader":
        if _resolve_agentic_trader_executable() is not None:
            return None
    elif shutil.which(name) is not None:
        return None
    artifact = _artifact_path(context, f"{name}_missing")
    _write_artifact(artifact, f"Executable not found on PATH: {name}\n")
    return CheckResult(
        name=f"{name}_available",
        passed=False,
        details=f"{name} not found on PATH",
        artifact=str(artifact),
    )


def _write_summary(context: SmokeContext, results: list[CheckResult]) -> Path:
    """
    Write a JSON summary of the smoke run to the artifacts directory.
    
    The file is named "smoke-summary.json" and contains the repository root, the artifacts directory path, the Python interpreter path, the resolved `agentic-trader` executable path (or null if not found), and the provided list of check results serialized as dictionaries.
    
    Parameters:
        context (SmokeContext): Context containing the artifacts_dir where the summary will be written.
        results (list[CheckResult]): Ordered list of check results to include in the summary.
    
    Returns:
        Path: Path to the written "smoke-summary.json" file.
    """
    summary_path = context.artifacts_dir / "smoke-summary.json"
    payload: dict[str, Any] = {
        "repo_root": str(REPO_ROOT),
        "artifacts_dir": str(context.artifacts_dir),
        "python": sys.executable,
        "agentic_trader_path": _resolve_agentic_trader_executable(),
        "results": [asdict(result) for result in results],
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def _run_id() -> str:
    """
    Produce a timestamp string used as a unique run identifier.
    
    Returns:
        str: Timestamp in the format YYYYMMDD-HHMMSS (e.g., 20260413-142530).
    """
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _parse_args() -> Namespace:
    """
    Parse command-line arguments for the smoke QA script.
    
    Supports flags to include code-quality checks and SonarQube analysis, and to configure Sonar host/project and the artifact run label.
    
    Returns:
        argparse.Namespace: Parsed arguments with attributes:
            include_quality (bool): If true, run ruff, pytest, and pyright when available.
            include_sonar (bool): If true, run pysonar (requires SONAR_TOKEN in the environment).
            sonar_host_url (str): SonarQube host URL to use when running pysonar.
            sonar_project_key (str): SonarQube project key to use when running pysonar.
            run_label (str): Subdirectory name under .ai/qa/artifacts/ where artifacts will be written.
    """
    parser = ArgumentParser(
        description="Run terminal smoke QA checks for Agentic Trader."
    )
    parser.add_argument(
        "--include-quality",
        action="store_true",
        help="Also run code-quality checks: ruff, pytest, and pyright when available.",
    )
    parser.add_argument(
        "--include-sonar",
        action="store_true",
        help="Also run pysonar. Requires SONAR_TOKEN in the environment.",
    )
    parser.add_argument(
        "--sonar-host-url",
        default=os.environ.get("SONAR_HOST_URL", DEFAULT_SONAR_HOST_URL),
        help="SonarQube host URL for --include-sonar.",
    )
    parser.add_argument(
        "--sonar-project-key",
        default=os.environ.get("SONAR_PROJECT_KEY", DEFAULT_SONAR_PROJECT_KEY),
        help="SonarQube project key for --include-sonar.",
    )
    parser.add_argument(
        "--run-label",
        default=f"smoke-{_run_id()}",
        help="Artifact subdirectory name under .ai/qa/artifacts/.",
    )
    return parser.parse_args()


def _surface_checks(context: SmokeContext) -> list[CheckResult]:
    """
    Run the predefined set of CLI and TUI smoke checks for `agentic-trader` and a Python TUI, collecting their CheckResult entries.
    
    If the `agentic-trader` executable is not found on PATH, a single failing availability CheckResult is returned. Otherwise this function runs multiple command-capture checks (including several JSON-output checks) and interactive TUI open-and-quit checks for the `agentic-trader` CLI, then always runs a Python TUI check against `main.py`. Artifacts for each check are written into context.artifacts_dir.
    
    Parameters:
        context (SmokeContext): Execution context containing the artifacts directory where per-check logs are written.
    
    Returns:
        list[CheckResult]: Ordered list of results for each performed check (availability, CLI checks, TUI checks, and the Python TUI).
    """
    results: list[CheckResult] = []
    agentic_trader_executable = _resolve_agentic_trader_executable()
    missing_agentic_trader = _require_executable(context, "agentic-trader")
    if missing_agentic_trader is not None:
        results.append(missing_agentic_trader)
    else:
        assert agentic_trader_executable is not None
        results.extend(
            [
                run_command_capture(
                    context,
                    "doctor",
                    [agentic_trader_executable, "doctor"],
                ),
                run_command_capture(
                    context,
                    "dashboard_snapshot",
                    [agentic_trader_executable, "dashboard-snapshot"],
                    require_json_stdout=True,
                ),
                run_dashboard_contract_check(
                    context,
                    [agentic_trader_executable, "dashboard-snapshot"],
                ),
                run_command_capture(
                    context,
                    "runtime_mode_checklist_json",
                    [
                        agentic_trader_executable,
                        "runtime-mode-checklist",
                        "operation",
                        "--json",
                        "--skip-provider-check",
                    ],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "status_json",
                    [agentic_trader_executable, "status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "broker_status_json",
                    [agentic_trader_executable, "broker-status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "supervisor_status_json",
                    [agentic_trader_executable, "supervisor-status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "logs_json",
                    [agentic_trader_executable, "logs", "--json", "--limit", "5"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "preferences_json",
                    [agentic_trader_executable, "preferences", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "portfolio_json",
                    [agentic_trader_executable, "portfolio", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "memory_policy_json",
                    [agentic_trader_executable, "memory-policy", "--json"],
                    require_json_stdout=True,
                ),
                run_tui_open_and_quit(
                    context,
                    "main_entrypoint_tui",
                    agentic_trader_executable,
                    [],
                ),
                run_tui_open_and_quit(
                    context,
                    "rich_menu",
                    agentic_trader_executable,
                    ["menu"],
                ),
            ]
        )

    results.append(
        run_tui_open_and_quit(
            context,
            "python_main_tui",
            sys.executable,
            ["main.py"],
            display=f"python main.py (resolved: {sys.executable})",
        )
    )
    return results


def _pytest_command(context: SmokeContext, *, include_coverage: bool) -> list[str]:
    """
    Builds the pytest command-line invocation used for running the test suite.
    
    When `include_coverage` is True, adds coverage measurement for the `agentic_trader`
    package and writes an XML report to the run artifacts coverage path resolved from
    the provided `context`.
    
    Parameters:
        context (SmokeContext): Context used to resolve artifact paths (coverage.xml).
        include_coverage (bool): If True, include coverage flags and an XML report path.
    
    Returns:
        list[str]: The full pytest command as an argument list suitable for subprocess execution.
    """
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if include_coverage:
        command.extend(
            [
                "--cov=agentic_trader",
                f"--cov-report=xml:{_coverage_path(context)}",
            ]
        )
    return command


def _quality_checks(context: SmokeContext, *, include_coverage: bool) -> list[CheckResult]:
    """
    Run code-quality checks (ruff, pytest, and pyright) and collect their results.
    
    When `include_coverage` is true, pytest is invoked to produce a coverage XML report (coverage.xml)
    alongside test execution. If `pyright` is not available on PATH, a skipped CheckResult is returned for it.
    
    Parameters:
        context (SmokeContext): Artifact/output directory and execution context.
        include_coverage (bool): If true, enable coverage reporting for the pytest run.
    
    Returns:
        list[CheckResult]: A list of results for `ruff_check`, `pytest`, and `pyright` (or a skipped result
        if pyright is absent).
    """
    results = [
        run_command_capture(
            context,
            "ruff_check",
            [sys.executable, "-m", "ruff", "check", "."],
            timeout=90,
            display="python -m ruff check .",
        ),
        run_command_capture(
            context,
            "pytest",
            _pytest_command(context, include_coverage=include_coverage),
            timeout=180,
            display=(
                "python -m pytest -q -p no:cacheprovider"
                + (
                    " --cov=agentic_trader --cov-report=xml:coverage.xml"
                    if include_coverage
                    else ""
                )
            ),
        ),
    ]

    pyright = shutil.which("pyright")
    if pyright is None:
        results.append(_fail_result(context, "pyright", "pyright not found on PATH"))
    else:
        results.append(
            run_command_capture(
                context,
                "pyright",
                [pyright],
                timeout=120,
                display="pyright",
            )
        )
    return results


def _sonar_check(context: SmokeContext, args: Namespace) -> CheckResult:
    """
    Run SonarQube analysis using the `pysonar` CLI and record the invocation/result in the artifacts directory.
    
    Checks that `pysonar` is available on PATH and that the `SONAR_TOKEN` environment variable is set; if either is missing, writes a diagnostic artifact and returns a failing CheckResult. If a coverage.xml artifact exists, it is passed to pysonar. Invokes `pysonar` (with a 240s timeout) via the common command-capture helper so stdout/stderr and exit status are persisted.
    
    Parameters:
        context (SmokeContext): Execution context containing the artifacts directory.
        args (Namespace): Parsed CLI arguments; must provide `sonar_host_url` and `sonar_project_key`.
    
    Returns:
        CheckResult: Result of the pysonar invocation; `passed` reflects the command exit status and output validation, and `artifact` points to the written log.
    """
    pysonar = shutil.which("pysonar")
    if pysonar is None:
        artifact = _artifact_path(context, "pysonar")
        _write_artifact(artifact, "pysonar executable not found on PATH.\n")
        return CheckResult(
            name="pysonar",
            passed=False,
            details="pysonar not found on PATH",
            artifact=str(artifact),
        )

    token = os.environ.get("SONAR_TOKEN")
    if not token:
        artifact = _artifact_path(context, "pysonar")
        _write_artifact(
            artifact,
            "SONAR_TOKEN is required for --include-sonar. No token was written to artifacts.\n",
        )
        return CheckResult(
            name="pysonar",
            passed=False,
            details="SONAR_TOKEN missing",
            artifact=str(artifact),
        )

    command = [
        pysonar,
        "--sonar-host-url",
        args.sonar_host_url,
        "--sonar-token",
        token,
        "--sonar-project-key",
        args.sonar_project_key,
    ]
    coverage_path = _coverage_path(context)
    if coverage_path.exists():
        command.extend(["--sonar-python-coverage-report-paths", str(coverage_path)])
    display = (
        "pysonar "
        f"--sonar-host-url={args.sonar_host_url} "
        "--sonar-token=<redacted> "
        f"--sonar-project-key={args.sonar_project_key}"
    )
    if coverage_path.exists():
        display += " --sonar-python-coverage-report-paths=coverage.xml"
    return run_command_capture(
        context,
        "pysonar",
        command,
        timeout=240,
        display=display,
    )


def main() -> int:
    """
    Run the smoke QA suite (CLI and TUI checks), optional code-quality checks, and optional Sonar analysis; write artifacts and a JSON summary, print a human-readable summary, and return an exit code.
    
    The function:
    - Creates the artifacts directory for this run.
    - Executes surface smoke checks and, if requested, quality and Sonar checks.
    - Persists per-check log artifacts and a top-level `smoke-summary.json`.
    - Prints a pass/fail table with details and artifact locations to stdout.
    
    Returns:
        int: 0 if all checks passed, 1 if any check failed.
    """
    args = _parse_args()
    context = SmokeContext(artifacts_dir=ARTIFACTS_ROOT / args.run_label)
    context.artifacts_dir.mkdir(parents=True, exist_ok=True)

    results = _surface_checks(context)
    if args.include_quality:
        results.extend(_quality_checks(context, include_coverage=args.include_sonar))
    if args.include_sonar:
        results.append(_sonar_check(context, args))

    summary_path = _write_summary(context, results)
    failed = [result for result in results if not result.passed]

    print("\nQA Smoke Summary")
    print("================")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} :: {result.details}")
        if result.artifact is not None:
            print(f"  artifact: {result.artifact}")
    print(f"\nSummary file: {summary_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())