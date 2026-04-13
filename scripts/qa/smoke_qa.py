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
    context.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return context.artifacts_dir / f"{name}.log"


def _coverage_path(context: SmokeContext) -> Path:
    return context.artifacts_dir / "coverage.xml"


def _command_display(command: list[str]) -> str:
    return " ".join(command)


def _write_artifact(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", errors="replace")


def _output_has_traceback(output: str) -> bool:
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


def _spawn_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    return env


def _drain_child(child: pexpect.spawn, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while child.isalive() and time.monotonic() < deadline:
        try:
            child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=0.25)
        except OSError:
            break


def _close_interactive_child(child: pexpect.spawn) -> str:
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


def run_tui_open_and_quit(
    context: SmokeContext,
    name: str,
    command: str,
    args: list[str],
    *,
    display: str | None = None,
    timeout: int = 20,
) -> CheckResult:
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
        _drain_child(child, RENDER_SECONDS)
        exit_method = _close_interactive_child(child)
        child.close(force=False)

        output = log.getvalue()
        _write_interactive_artifact(artifact, display_command, exit_method, child, output)
        return _interactive_check_result(name, artifact, exit_method, child, output)
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
    artifact = _artifact_path(context, name)
    _write_artifact(artifact, f"SKIPPED: {details}\n")
    return CheckResult(
        name=name,
        passed=True,
        details=f"skipped; {details}",
        artifact=str(artifact),
    )


def _require_executable(context: SmokeContext, name: str) -> CheckResult | None:
    if shutil.which(name) is not None:
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
    summary_path = context.artifacts_dir / "smoke-summary.json"
    payload: dict[str, Any] = {
        "repo_root": str(REPO_ROOT),
        "artifacts_dir": str(context.artifacts_dir),
        "python": sys.executable,
        "agentic_trader_path": shutil.which("agentic-trader"),
        "results": [asdict(result) for result in results],
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def _run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _parse_args() -> Namespace:
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
    results: list[CheckResult] = []
    missing_agentic_trader = _require_executable(context, "agentic-trader")
    if missing_agentic_trader is not None:
        results.append(missing_agentic_trader)
    else:
        results.extend(
            [
                run_command_capture(
                    context,
                    "doctor",
                    ["agentic-trader", "doctor"],
                ),
                run_command_capture(
                    context,
                    "dashboard_snapshot",
                    ["agentic-trader", "dashboard-snapshot"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "status_json",
                    ["agentic-trader", "status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "broker_status_json",
                    ["agentic-trader", "broker-status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "supervisor_status_json",
                    ["agentic-trader", "supervisor-status", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "logs_json",
                    ["agentic-trader", "logs", "--json", "--limit", "5"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "preferences_json",
                    ["agentic-trader", "preferences", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "portfolio_json",
                    ["agentic-trader", "portfolio", "--json"],
                    require_json_stdout=True,
                ),
                run_command_capture(
                    context,
                    "memory_policy_json",
                    ["agentic-trader", "memory-policy", "--json"],
                    require_json_stdout=True,
                ),
                run_tui_open_and_quit(
                    context,
                    "main_entrypoint_tui",
                    "agentic-trader",
                    [],
                ),
                run_tui_open_and_quit(
                    context,
                    "rich_menu",
                    "agentic-trader",
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
        results.append(_skip_result(context, "pyright", "pyright not found on PATH"))
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
