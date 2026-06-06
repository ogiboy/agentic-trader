#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

from scripts.qa.smoke_qa_modules import args as smoke_args, commands
from scripts.qa.smoke_qa_modules import environment as smoke_environment
from scripts.qa.smoke_qa_modules import ink_navigation, interactive, reporting
from scripts.qa.smoke_qa_modules.common import (
    artifact_path as _artifact_path,
    coverage_path as _coverage_path,
    write_artifact as _write_artifact,
)
from scripts.qa.smoke_qa_modules.environment import (
    DEFAULT_SONAR_TOKEN_KEYCHAIN_SERVICE,
)
from scripts.qa.smoke_qa_modules.market_context import (
    run_market_context_edge_case_check,
)
from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_ROOT = REPO_ROOT / ".ai" / "qa" / "artifacts"
DEFAULT_SONAR_SOURCES = (
    "agentic_trader,main.py,webgui/src,docs/app,docs/components,"
    "docs/content,docs/lib,tui"
)
DEFAULT_SONAR_TESTS = "tests"


def _current_git_branch() -> str | None:
    return smoke_environment.current_git_branch(
        REPO_ROOT, subprocess_module=subprocess
    )


def _current_git_commit() -> str | None:
    return smoke_environment.current_git_commit(
        REPO_ROOT, subprocess_module=subprocess
    )


def _git_worktree_dirty() -> bool | None:
    return smoke_environment.git_worktree_dirty(
        REPO_ROOT, subprocess_module=subprocess
    )


def _resolve_sonar_token() -> str | None:
    return smoke_environment.resolve_sonar_token(
        default_service=DEFAULT_SONAR_TOKEN_KEYCHAIN_SERVICE,
        env=os.environ,
        which=shutil.which,
        subprocess_module=subprocess,
    )


def _resolve_managed_conda_env_name() -> str | None:
    return smoke_environment.resolve_managed_conda_env_name(REPO_ROOT)


def _resolve_smoke_python() -> str:
    return smoke_environment.resolve_smoke_python(REPO_ROOT, env=os.environ)


SMOKE_PYTHON = _resolve_smoke_python()


def _resolve_agentic_trader_executable() -> str | None:
    return smoke_environment.resolve_agentic_trader_executable(
        SMOKE_PYTHON,
        env=os.environ,
        which=shutil.which,
    )


def run_command_capture(
    context: SmokeContext,
    name: str,
    command: list[str],
    *,
    timeout: int = 30,
    require_json_stdout: bool = False,
    display: str | None = None,
    env_overrides: dict[str, str] | None = None,
    sensitive_values: tuple[str, ...] = (),
) -> CheckResult:
    return commands.run_command_capture(
        context,
        name,
        command,
        repo_root=REPO_ROOT,
        subprocess_module=subprocess,
        timeout=timeout,
        require_json_stdout=require_json_stdout,
        display=display,
        env_overrides=env_overrides,
        sensitive_values=sensitive_values,
    )


def run_expected_failure_capture(
    context: SmokeContext,
    name: str,
    command: list[str],
    *,
    expected_text: str,
    timeout: int = 30,
    expected_exit_codes: tuple[int, ...] = (1, 2),
    display: str | None = None,
) -> CheckResult:
    return commands.run_expected_failure_capture(
        context,
        name,
        command,
        repo_root=REPO_ROOT,
        subprocess_module=subprocess,
        expected_text=expected_text,
        timeout=timeout,
        expected_exit_codes=expected_exit_codes,
        display=display,
    )


def run_cli_help_contract_check(
    context: SmokeContext, agentic_trader_executable: str
) -> CheckResult:
    return commands.run_cli_help_contract_check(
        context,
        agentic_trader_executable,
        repo_root=REPO_ROOT,
        subprocess_module=subprocess,
    )


def run_dashboard_contract_check(
    context: SmokeContext, command: list[str], *, timeout: int = 30
) -> CheckResult:
    return commands.run_dashboard_contract_check(
        context,
        command,
        repo_root=REPO_ROOT,
        subprocess_module=subprocess,
        timeout=timeout,
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
    return interactive.run_tui_open_and_quit(
        context,
        name,
        command,
        args,
        repo_root=REPO_ROOT,
        display=display,
        timeout=timeout,
    )


def ink_settings_capture_issues(output: str) -> list[str]:
    """Public test seam for Settings page capture validation."""

    return ink_navigation.ink_settings_capture_issues(output)


def run_ink_settings_navigation(
    context: SmokeContext,
    command: str,
    *,
    timeout: int = 30,
) -> CheckResult:
    return ink_navigation.run_ink_settings_navigation(
        context,
        command,
        repo_root=REPO_ROOT,
        subprocess_module=subprocess,
        shutil_module=shutil,
        timeout=timeout,
    )


def run_rich_menu_deep_navigation(
    context: SmokeContext,
    command: str,
    *,
    timeout: int = 20,
) -> CheckResult:
    return interactive.run_rich_menu_deep_navigation(
        context,
        command,
        repo_root=REPO_ROOT,
        timeout=timeout,
    )


def _require_executable(context: SmokeContext, name: str) -> CheckResult | None:
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
    return reporting.write_summary(
        context,
        results,
        repo_root=REPO_ROOT,
        smoke_python=SMOKE_PYTHON,
        resolve_agentic_trader_executable=_resolve_agentic_trader_executable,
    )


def _write_report(
    context: SmokeContext, results: list[CheckResult], summary_path: Path
) -> Path:
    return reporting.write_report(
        context,
        results,
        summary_path,
        repo_root=REPO_ROOT,
        smoke_python=SMOKE_PYTHON,
        resolve_agentic_trader_executable=_resolve_agentic_trader_executable,
        current_git_branch=_current_git_branch,
        current_git_commit=_current_git_commit,
        git_worktree_dirty=_git_worktree_dirty,
    )


def _claim_artifacts_dir(run_label: str) -> Path:
    return reporting.claim_artifacts_dir(ARTIFACTS_ROOT, run_label)


def claim_artifacts_dir(run_label: str) -> Path:
    """Public test seam for claiming a unique smoke artifact directory."""

    return _claim_artifacts_dir(run_label)


def resolve_smoke_python() -> str:
    """Public test seam for smoke Python resolution."""

    return _resolve_smoke_python()


def write_summary(context: SmokeContext, results: list[CheckResult]) -> Path:
    """Public test seam for writing a smoke summary artifact."""

    return _write_summary(context, results)


def write_report(
    context: SmokeContext, results: list[CheckResult], summary_path: Path
) -> Path:
    """Public test seam for writing the Markdown smoke report."""

    return _write_report(context, results, summary_path)


def _runtime_cycle_check(
    context: SmokeContext, args: Namespace, agentic_trader_executable: str
) -> CheckResult:
    runtime_dir = context.artifacts_dir / "runtime-cycle"
    database_path = runtime_dir / "agentic_trader.duckdb"
    return run_command_capture(
        context,
        "runtime_cycle",
        [
            agentic_trader_executable,
            "launch",
            "--symbols",
            str(args.runtime_symbol),
            "--interval",
            str(args.runtime_interval),
            "--lookback",
            str(args.runtime_lookback),
            "--poll-seconds",
            "0",
            "--continuous",
            "--max-cycles",
            "1",
        ],
        timeout=420,
        env_overrides={
            "AGENTIC_TRADER_RUNTIME_DIR": str(runtime_dir),
            "AGENTIC_TRADER_DATABASE_PATH": str(database_path),
            "AGENTIC_TRADER_MARKET_DATA_CACHE_DIR": str(
                runtime_dir / "market_snapshots"
            ),
            "AGENTIC_TRADER_MAX_OUTPUT_TOKENS": "2048",
            "AGENTIC_TRADER_MAX_RETRIES": "2",
            "AGENTIC_TRADER_REQUEST_TIMEOUT_SECONDS": "180",
        },
    )


def _surface_checks(context: SmokeContext, args: Namespace) -> list[CheckResult]:
    results: list[CheckResult] = []
    agentic_trader_executable = _resolve_agentic_trader_executable()
    missing_agentic_trader = _require_executable(context, "agentic-trader")
    if missing_agentic_trader is not None:
        results.append(missing_agentic_trader)
    else:
        assert agentic_trader_executable is not None
        results.extend(_agentic_trader_surface_checks(context, agentic_trader_executable))
        if args.include_runtime_cycle:
            results.append(
                _runtime_cycle_check(context, args, agentic_trader_executable)
            )

    results.append(
        run_tui_open_and_quit(
            context,
            "python_main_launcher",
            SMOKE_PYTHON,
            ["main.py"],
            display=f"python main.py (resolved: {SMOKE_PYTHON})",
        )
    )
    return results


def _agentic_trader_surface_checks(
    context: SmokeContext, agentic_trader_executable: str
) -> list[CheckResult]:
    return [
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
        run_cli_help_contract_check(context, agentic_trader_executable),
        run_market_context_edge_case_check(context),
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
        run_expected_failure_capture(
            context,
            "observer_api_empty_host_blocked",
            [
                agentic_trader_executable,
                "observer-api",
                "--host",
                "",
                "--port",
                "8765",
            ],
            expected_text="Observer API is local-only by default.",
        ),
        *_json_surface_checks(context, agentic_trader_executable),
        run_tui_open_and_quit(
            context,
            "main_entrypoint_launcher",
            agentic_trader_executable,
            [],
        ),
        run_tui_open_and_quit(
            context,
            "direct_tui_entrypoint",
            agentic_trader_executable,
            ["tui"],
        ),
        run_ink_settings_navigation(context, agentic_trader_executable),
        run_tui_open_and_quit(
            context,
            "rich_menu",
            agentic_trader_executable,
            ["menu"],
        ),
        run_rich_menu_deep_navigation(context, agentic_trader_executable),
    ]


def _json_surface_checks(
    context: SmokeContext, agentic_trader_executable: str
) -> list[CheckResult]:
    checks = (
        ("status_json", ["status", "--json"]),
        ("broker_status_json", ["broker-status", "--json"]),
        ("finance_ops_json", ["finance-ops", "--json"]),
        ("provider_diagnostics_json", ["provider-diagnostics", "--json"]),
        ("v1_readiness_json", ["v1-readiness", "--json"]),
        ("supervisor_status_json", ["supervisor-status", "--json"]),
        ("logs_json", ["logs", "--json", "--limit", "5"]),
        ("preferences_json", ["preferences", "--json"]),
        ("portfolio_json", ["portfolio", "--json"]),
        ("memory_policy_json", ["memory-policy", "--json"]),
    )
    return [
        run_command_capture(
            context,
            name,
            [agentic_trader_executable, *args],
            require_json_stdout=True,
        )
        for name, args in checks
    ]


def _pytest_command(context: SmokeContext, *, include_coverage: bool) -> list[str]:
    command = [SMOKE_PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if include_coverage:
        command.extend(
            [
                "--cov=agentic_trader",
                f"--cov-report=xml:{_coverage_path(context)}",
            ]
        )
    return command


def _quality_checks(
    context: SmokeContext, *, include_coverage: bool
) -> list[CheckResult]:
    results = [
        run_command_capture(
            context,
            "ruff_check",
            [SMOKE_PYTHON, "-m", "ruff", "check", "."],
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

    results.append(
        run_command_capture(
            context,
            "pyright",
            [
                SMOKE_PYTHON,
                "scripts/check_pyright_baseline.py",
                "--pythonpath",
                SMOKE_PYTHON,
                "agentic_trader",
                "tests",
                "scripts",
            ],
            timeout=120,
            display=(
                "python scripts/check_pyright_baseline.py "
                "--pythonpath <smoke-python> agentic_trader tests scripts"
            ),
        )
    )
    return results


def _sonar_check(context: SmokeContext, args: Namespace) -> CheckResult:
    token = _resolve_sonar_token()
    if not token:
        artifact = _artifact_path(context, "pysonar")
        _write_artifact(
            artifact,
            (
                "A Sonar token is required for --include-sonar. Set SONAR_TOKEN "
                "or store it in macOS Keychain service "
                f"{DEFAULT_SONAR_TOKEN_KEYCHAIN_SERVICE!r}. No token was written "
                "to artifacts.\n"
            ),
        )
        return CheckResult(
            name="pysonar",
            passed=False,
            details="Sonar token missing",
            artifact=str(artifact),
        )

    scanner_script = REPO_ROOT / "scripts" / "qa" / "run_sonar_scan.sh"
    command = [str(scanner_script), "pysonar"]
    env_overrides = {
        "SONAR_ARTIFACT_DIR": str(context.artifacts_dir),
        "SONAR_HOST_URL": args.sonar_host_url,
        "SONAR_PROJECT_KEY": args.sonar_project_key,
        "SONAR_TOKEN": token,
    }
    if args.sonar_branch_name:
        env_overrides["SONAR_BRANCH_NAME"] = args.sonar_branch_name
    if args.sonar_organization:
        env_overrides["SONAR_ORGANIZATION"] = args.sonar_organization

    display = (
        "SONAR_TOKEN=<redacted> "
        f"SONAR_ARTIFACT_DIR={context.artifacts_dir} "
        f"SONAR_HOST_URL={args.sonar_host_url} "
        f"SONAR_PROJECT_KEY={args.sonar_project_key} "
        "scripts/qa/run_sonar_scan.sh pysonar"
    )
    if args.sonar_branch_name:
        display += f" SONAR_BRANCH_NAME={args.sonar_branch_name}"
    if args.sonar_organization:
        display += f" SONAR_ORGANIZATION={args.sonar_organization}"
    return run_command_capture(
        context,
        "pysonar",
        command,
        timeout=360,
        display=display,
        env_overrides=env_overrides,
        sensitive_values=(token,),
    )


def main() -> int:
    args = smoke_args.parse_args(env=os.environ)
    context = SmokeContext(artifacts_dir=_claim_artifacts_dir(args.run_label))

    results = _surface_checks(context, args)
    if args.include_quality:
        results.extend(_quality_checks(context, include_coverage=args.include_sonar))
    if args.include_sonar:
        results.append(_sonar_check(context, args))

    summary_path = _write_summary(context, results)
    report_path = _write_report(context, results, summary_path)
    failed = [result for result in results if not result.passed]

    print("\nQA Smoke Summary")
    print("================")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} :: {result.details}")
        if result.artifact is not None:
            print(f"  artifact: {result.artifact}")
    print(f"\nSummary file: {summary_path}")
    print(f"Report file: {report_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
