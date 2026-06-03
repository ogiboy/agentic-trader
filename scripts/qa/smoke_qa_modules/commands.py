from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast

from scripts.qa.smoke_qa_modules.common import (
    artifact_path,
    command_display,
    json_stdout_error,
    operator_noise_marker,
    output_has_traceback,
    redact_sensitive_text,
    write_artifact,
)
from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext

HELP_COMMANDS = (
    ("top_help", ["--help"]),
    ("top_short_help", ["-h"]),
    ("run_help", ["run", "--help"]),
    ("launch_help", ["launch", "--help"]),
    ("broker_status_help", ["broker-status", "--help"]),
    ("trade_context_help", ["trade-context", "--help"]),
    ("tui_help", ["tui", "--help"]),
    ("menu_help", ["menu", "--help"]),
    ("webgui_service_help", ["webgui-service", "--help"]),
    ("observer_api_help", ["observer-api", "--help"]),
)
HELP_INTERNAL_MARKERS = ("Parameters:", "Raises:", "Returns:")


def run_command_capture(
    context: SmokeContext,
    name: str,
    command: list[str],
    *,
    repo_root: Path,
    subprocess_module: Any = subprocess,
    timeout: int = 30,
    require_json_stdout: bool = False,
    display: str | None = None,
    env_overrides: dict[str, str] | None = None,
    sensitive_values: tuple[str, ...] = (),
) -> CheckResult:
    artifact = artifact_path(context, name)
    display_command = display or command_display(command)
    proc_or_result = _run_capture_process(
        command,
        artifact=artifact,
        display_command=display_command,
        repo_root=repo_root,
        subprocess_module=subprocess_module,
        timeout=timeout,
        env_overrides=env_overrides,
        sensitive_values=sensitive_values,
        name=name,
    )
    if isinstance(proc_or_result, CheckResult):
        return proc_or_result

    return _capture_process_result(
        proc_or_result,
        name=name,
        artifact=artifact,
        display_command=display_command,
        repo_root=repo_root,
        require_json_stdout=require_json_stdout,
        sensitive_values=sensitive_values,
    )


def _run_capture_process(
    command: list[str],
    *,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    subprocess_module: Any,
    timeout: int,
    env_overrides: dict[str, str] | None,
    sensitive_values: tuple[str, ...],
    name: str,
) -> subprocess.CompletedProcess[str] | CheckResult:
    try:
        return cast(
            subprocess.CompletedProcess[str],
            subprocess_module.run(
                command,
                cwd=repo_root,
                env={**os.environ, **env_overrides}
                if env_overrides is not None
                else None,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            ),
        )
    except subprocess.TimeoutExpired as exc:
        return timeout_capture_result(
            exc,
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            timeout=timeout,
            sensitive_values=sensitive_values,
        )
    except Exception as exc:
        exception_text = redact_sensitive_text(str(exc), sensitive_values)
        write_artifact(
            artifact, f"$ {display_command}\n\nEXCEPTION:\n{exception_text}\n"
        )
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exception_text}",
            artifact=str(artifact),
        )


def timeout_capture_result(
    exc: subprocess.TimeoutExpired,
    *,
    name: str,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    timeout: int,
    sensitive_values: tuple[str, ...],
) -> CheckResult:
    stdout = _decode_timeout_stream(exc.stdout)
    stderr = _decode_timeout_stream(exc.stderr)
    stdout = redact_sensitive_text(stdout, sensitive_values)
    stderr = redact_sensitive_text(stderr, sensitive_values)
    exception_text = redact_sensitive_text(str(exc), sensitive_values)
    write_artifact(
        artifact,
        f"$ {display_command}\n"
        f"cwd: {repo_root}\n"
        f"timeout: {timeout}\n\n"
        f"STDOUT:\n{stdout}\n\n"
        f"STDERR:\n{stderr}\n\n"
        f"EXCEPTION:\n{exception_text}\n",
    )
    return CheckResult(
        name=name,
        passed=False,
        details=f"timeout_after={timeout}s",
        artifact=str(artifact),
    )


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _capture_process_result(
    proc: subprocess.CompletedProcess[str],
    *,
    name: str,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    require_json_stdout: bool,
    sensitive_values: tuple[str, ...],
) -> CheckResult:
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    json_error = json_stdout_error(stdout) if require_json_stdout else None
    artifact_stdout = redact_sensitive_text(stdout, sensitive_values)
    artifact_stderr = redact_sensitive_text(stderr, sensitive_values)

    artifact_body = (
        f"$ {display_command}\n"
        f"cwd: {repo_root}\n"
        f"exit_code: {proc.returncode}\n\n"
        f"STDOUT:\n{artifact_stdout}\n\n"
        f"STDERR:\n{artifact_stderr}"
    )
    if json_error is not None:
        artifact_body += f"\n\nJSON_ERROR:\n{json_error}\n"
    write_artifact(artifact, artifact_body)

    combined_output = stdout + stderr
    noise_marker = operator_noise_marker(combined_output)
    passed = (
        proc.returncode == 0
        and not output_has_traceback(combined_output)
        and noise_marker is None
    )
    if require_json_stdout:
        passed = passed and json_error is None

    details = f"exit_code={proc.returncode}"
    if json_error is not None:
        details += f"; invalid_json={json_error}"
    if noise_marker is not None:
        details += f"; raw_operator_noise={noise_marker}"
    return CheckResult(
        name=name,
        passed=passed,
        details=details,
        artifact=str(artifact),
    )


def run_expected_failure_capture(
    context: SmokeContext,
    name: str,
    command: list[str],
    *,
    repo_root: Path,
    subprocess_module: Any = subprocess,
    expected_text: str,
    timeout: int = 30,
    expected_exit_codes: tuple[int, ...] = (1, 2),
    display: str | None = None,
) -> CheckResult:
    artifact = artifact_path(context, name)
    display_command = display or command_display(command)
    try:
        proc = cast(
            subprocess.CompletedProcess[str],
            subprocess_module.run(
                command,
                cwd=repo_root,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            ),
        )
    except subprocess.TimeoutExpired as exc:
        return timeout_capture_result(
            exc,
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            timeout=timeout,
            sensitive_values=(),
        )
    except Exception as exc:
        write_artifact(artifact, f"$ {display_command}\n\nEXCEPTION:\n{exc}\n")
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exc}",
            artifact=str(artifact),
        )

    combined_output = f"{proc.stdout}\n{proc.stderr}"
    passed = (
        proc.returncode in expected_exit_codes
        and expected_text in combined_output
        and not output_has_traceback(combined_output)
    )
    write_artifact(
        artifact,
        (
            f"$ {display_command}\n"
            f"cwd: {repo_root}\n"
            f"expected_exit_codes: {expected_exit_codes}\n"
            f"expected_text: {expected_text}\n"
            f"exit_code: {proc.returncode}\n\n"
            f"STDOUT:\n{proc.stdout}\n\n"
            f"STDERR:\n{proc.stderr}"
        ),
    )
    details = f"exit_code={proc.returncode}"
    if expected_text not in combined_output:
        details += "; expected_text_missing"
    if proc.returncode not in expected_exit_codes:
        details += "; unexpected_exit_code"
    return CheckResult(
        name=name,
        passed=passed,
        details=details,
        artifact=str(artifact),
    )


def run_cli_help_contract_check(
    context: SmokeContext,
    agentic_trader_executable: str,
    *,
    repo_root: Path,
    subprocess_module: Any = subprocess,
) -> CheckResult:
    name = "cli_help_contract"
    artifact = artifact_path(context, name)
    issues: list[str] = []
    output_sections: list[str] = []

    for check_name, args in HELP_COMMANDS:
        command = [agentic_trader_executable, *args]
        display_command = command_display(command)
        try:
            proc = cast(
                subprocess.CompletedProcess[str],
                subprocess_module.run(
                    command,
                    cwd=repo_root,
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                ),
            )
        except Exception as exc:
            issues.append(f"{check_name}: exception={exc}")
            output_sections.append(f"$ {display_command}\nEXCEPTION:\n{exc}")
            continue

        combined_output = f"{proc.stdout}\n{proc.stderr}"
        output_sections.append(
            f"$ {display_command}\nexit_code: {proc.returncode}\n\n{combined_output}"
        )
        if proc.returncode != 0:
            issues.append(f"{check_name}: exit_code={proc.returncode}")
        if "Usage:" not in combined_output:
            issues.append(f"{check_name}: missing Usage")
        for marker in HELP_INTERNAL_MARKERS:
            if marker in combined_output:
                issues.append(f"{check_name}: internal marker {marker}")
        if output_has_traceback(combined_output):
            issues.append(f"{check_name}: traceback")

    write_artifact(
        artifact,
        f"issues: {json.dumps(issues, indent=2)}\n\n"
        + "\n\n---\n\n".join(output_sections),
    )
    return CheckResult(
        name=name,
        passed=not issues,
        details="help_contract_ok" if not issues else "; ".join(issues),
        artifact=str(artifact),
    )


def run_dashboard_contract_check(
    context: SmokeContext,
    command: list[str],
    *,
    repo_root: Path,
    subprocess_module: Any = subprocess,
    timeout: int = 30,
) -> CheckResult:
    name = "dashboard_contract"
    artifact = artifact_path(context, name)
    display_command = command_display(command)
    issues: list[str] = []
    try:
        proc = cast(
            subprocess.CompletedProcess[str],
            subprocess_module.run(
                command,
                cwd=repo_root,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            ),
        )
        payload = json.loads(proc.stdout or "{}")
    except Exception as exc:
        write_artifact(artifact, f"$ {display_command}\n\nEXCEPTION:\n{exc}\n")
        return CheckResult(
            name=name,
            passed=False,
            details=f"exception={exc}",
            artifact=str(artifact),
        )

    issues.extend(_dashboard_contract_issues(payload, proc.returncode))

    write_artifact(
        artifact,
        (
            f"$ {display_command}\n"
            f"cwd: {repo_root}\n"
            f"issues: {json.dumps(issues, indent=2)}\n\n"
            f"STDOUT:\n{proc.stdout}\n\n"
            f"STDERR:\n{proc.stderr}"
        ),
    )
    return CheckResult(
        name=name,
        passed=not issues and not output_has_traceback(proc.stdout + proc.stderr),
        details="contract_ok" if not issues else "; ".join(issues),
        artifact=str(artifact),
    )


def _dashboard_contract_issues(
    payload: dict[str, object], returncode: int
) -> list[str]:
    issues: list[str] = []
    if returncode != 0:
        issues.append(f"exit_code={returncode}")
    _require_dict_field(payload, "doctor", issues, required_keys=("runtime_mode",))
    _require_dict_field(payload, "status", issues, required_keys=("runtime_mode",))
    _validate_market_context_section(payload, issues)
    _require_dict_field(payload, "recentRuns", issues, required_keys=("runs",))
    _validate_provider_diagnostics_section(payload, issues)
    _validate_v1_readiness_section(payload, issues)
    _validate_finance_ops_section(payload, issues)
    _validate_broker_section(payload, issues)
    return issues


def _require_dict_field(
    payload: dict[str, object],
    key: str,
    issues: list[str],
    *,
    required_keys: tuple[str, ...] = (),
) -> dict[str, object] | None:
    value = payload.get(key)
    if not isinstance(value, dict):
        issues.append(f"{key} section missing")
        return None
    for required_key in required_keys:
        if required_key not in value:
            issues.append(f"{key}.{required_key} missing")
    return cast(dict[str, object], value)


def _validate_market_context_section(
    payload: dict[str, object], issues: list[str]
) -> None:
    market_context = _require_dict_field(payload, "marketContext", issues)
    if market_context is None:
        return
    if "contextPack" not in market_context:
        issues.append("marketContext.contextPack missing")
        return
    context_pack = market_context["contextPack"]
    if context_pack is None:
        return
    if not isinstance(context_pack, dict):
        issues.append("marketContext.contextPack has unexpected type")
        return
    for field in ("summary", "bars_analyzed", "horizons"):
        if field not in context_pack:
            issues.append(f"marketContext.contextPack.{field} missing")


def _validate_provider_diagnostics_section(
    payload: dict[str, object], issues: list[str]
) -> None:
    provider_diagnostics = _require_dict_field(payload, "providerDiagnostics", issues)
    if provider_diagnostics is None:
        return
    if not isinstance(provider_diagnostics.get("warnings"), list):
        issues.append("providerDiagnostics.warnings missing")
    if not isinstance(provider_diagnostics.get("providers"), list):
        issues.append("providerDiagnostics.providers missing")


def _validate_v1_readiness_section(
    payload: dict[str, object], issues: list[str]
) -> None:
    v1_readiness = _require_dict_field(payload, "v1Readiness", issues)
    if v1_readiness is None:
        return
    if not isinstance(v1_readiness.get("paper_operations"), dict):
        issues.append("v1Readiness.paper_operations missing")
    paper_evidence = v1_readiness.get("paper_evidence")
    if not isinstance(paper_evidence, dict):
        issues.append("v1Readiness.paper_evidence missing")
    else:
        paper_evidence_payload = cast(dict[str, object], paper_evidence)
        review_artifacts = paper_evidence_payload.get("review_artifacts", [])
        if not isinstance(review_artifacts, list) or (
            "evidence_bundle" not in review_artifacts
        ):
            issues.append("v1Readiness.paper_evidence.review_artifacts incomplete")
    if not isinstance(v1_readiness.get("alpaca_paper"), dict):
        issues.append("v1Readiness.alpaca_paper missing")


def _validate_broker_section(payload: dict[str, object], issues: list[str]) -> None:
    broker = _require_dict_field(payload, "broker", issues)
    if broker is None:
        return
    if "external_paper" not in broker:
        issues.append("broker.external_paper missing")
    if not isinstance(broker.get("healthcheck"), dict):
        issues.append("broker.healthcheck missing")


def _validate_finance_ops_section(
    payload: dict[str, object], issues: list[str]
) -> None:
    finance_ops = _require_dict_field(payload, "financeOps", issues)
    if finance_ops is None:
        return
    if not isinstance(finance_ops.get("checks"), list):
        issues.append("financeOps.checks missing")
    if not isinstance(finance_ops.get("broker"), dict):
        issues.append("financeOps.broker missing")
    if not isinstance(finance_ops.get("portfolio"), dict):
        issues.append("financeOps.portfolio missing")
    if not isinstance(finance_ops.get("paperEvidence"), dict):
        issues.append("financeOps.paperEvidence missing")
