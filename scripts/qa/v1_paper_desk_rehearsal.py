#!/usr/bin/env python3
"""Run a product-shaped V1 paper desk rehearsal and collect evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / ".ai" / "qa" / "artifacts"


def _json_default(value: object) -> str:
    """
    Convert a value to a JSON-serializable string representation.

    Specifically converts pathlib.Path objects to their string path; all other values are converted using `str()`.

    Parameters:
        value (object): The value to convert for JSON serialization.

    Returns:
        str: A string suitable for JSON encoding representing `value`.
    """
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: object) -> None:
    """
    Write a JSON-serializable payload to the given file path using stable formatting.

    The file is written with 2-space indentation, keys sorted, non-standard types converted via _json_default, and UTF-8 encoding.

    Parameters:
        path (Path): Destination file path to write.
        payload (object): JSON-serializable object to persist.
    """
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def _object_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def _object_mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in cast(list[object], value):
        row = _object_mapping(item)
        if row is not None:
            rows.append(row)
    return rows


def _parse_json(stdout: str) -> object | None:
    """
    Attempt to parse a stdout string as JSON and return the resulting value.

    Parameters:
        stdout (str): The stdout text to parse as JSON.

    Returns:
        The Python object resulting from JSON decoding of `stdout`, or `None` if `stdout` is not valid JSON.
    """
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _run_step(
    *,
    name: str,
    args: list[str],
    env: dict[str, str],
    artifact_dir: Path,
    expect_success: bool = True,
    timeout: int = 120,
) -> dict[str, object]:
    """
    Run a single agentic_trader CLI step, record its outputs and duration, and persist a per-step JSON artifact.

    Parameters:
        name (str): Identifier used for the step and artifact filename (written as <name>.json).
        args (list[str]): CLI arguments passed to the agentic_trader module (excluding the Python interpreter).
        env (dict[str, str]): Environment variables to use for the subprocess execution.
        artifact_dir (Path): Directory where the per-step JSON payload will be written.
        expect_success (bool): If True, `ok` is True when the process exit code is 0; if False, `ok` is True when the exit code is non-zero.
        timeout (int): Subprocess execution timeout in seconds.

    Returns:
        dict: A payload dictionary persisted to `{artifact_dir}/{name}.json` containing:
            - name (str): step name
            - command (list[str]): human-friendly command representation (["agentic-trader", *args])
            - exit_code (int): subprocess exit code
            - duration_ms (int): elapsed runtime in milliseconds
            - expected_success (bool): the provided expectation flag
            - ok (bool): pass/fail based on `expect_success` and the exit code
            - stdout_json (Any): result of best-effort JSON parse of stdout, or None on parse failure
            - stdout (str|None): raw stdout when it does not begin with "{" after stripping, otherwise None
            - stderr (str|None): raw stderr or None if empty
    """
    started = time.monotonic()
    command = [sys.executable, "-m", "agentic_trader.cli", *args]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    duration_ms = round((time.monotonic() - started) * 1000)
    payload: dict[str, object] = {
        "name": name,
        "command": ["agentic-trader", *args],
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "expected_success": expect_success,
        "ok": (
            completed.returncode == 0 if expect_success else completed.returncode != 0
        ),
        "stdout_json": _parse_json(completed.stdout),
        "stdout": (
            completed.stdout if not completed.stdout.strip().startswith("{") else None
        ),
        "stderr": completed.stderr or None,
    }
    _write_json(artifact_dir / f"{name}.json", payload)
    return payload


def _env_for_run(args: argparse.Namespace, artifact_dir: Path) -> dict[str, str]:
    """
    Create an environment mapping configured for an isolated rehearsal runtime and return it.

    This will ensure a runtime directory exists under `artifact_dir` and populate environment variables
    that point to that runtime, configure the execution backend, and disable live execution and the
    execution kill switch. If `args.execution_backend` equals `"alpaca_paper"`, the Alpaca paper trading
    flag is enabled.

    Parameters:
        args (argparse.Namespace): Parsed CLI arguments; uses `args.execution_backend`.
        artifact_dir (Path): Directory under which a `runtime` subdirectory will be created and used
            for runtime artifacts (database path, etc.).

    Returns:
        dict[str, str]: A copy of the current environment updated with rehearsal-specific variables.
    """
    runtime_dir = artifact_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "AGENTIC_TRADER_RUNTIME_DIR": str(runtime_dir),
            "AGENTIC_TRADER_DATABASE_PATH": str(runtime_dir / "agentic_trader.duckdb"),
            "AGENTIC_TRADER_EXECUTION_BACKEND": args.execution_backend,
            "AGENTIC_TRADER_LIVE_EXECUTION_ENABLED": "false",
            "AGENTIC_TRADER_EXECUTION_KILL_SWITCH_ACTIVE": "false",
        }
    )
    if args.execution_backend == "alpaca_paper":
        env["AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED"] = "true"
    return env


def _symbol_list(raw_symbols: str) -> list[str]:
    """
    Parse a comma-separated string of symbols into a list of uppercase symbol strings.

    Empty items and surrounding whitespace are removed. Leading/trailing whitespace on each symbol is stripped and each symbol is converted to uppercase.

    Parameters:
        raw_symbols (str): Comma-separated symbols, e.g. "AAPL, msft, GOOG".

    Returns:
        list[str]: A list of uppercase symbol tokens.

    Raises:
        ValueError: If no valid symbols are found.
    """
    symbols = [item.strip().upper() for item in raw_symbols.split(",") if item.strip()]
    if not symbols:
        raise ValueError("at least one symbol is required")
    return symbols


def _proposal_risk_defaults(reference_price: float) -> tuple[float, float]:
    """
    Compute default stop-loss and take-profit bounds from a reference price.

    Parameters:
        reference_price (float): Price used as the baseline for risk calculations.

    Returns:
        tuple[float, float]: (stop_loss, take_profit) where stop_loss is the reference price multiplied by 0.95 and rounded to two decimal places, and take_profit is the reference price multiplied by 1.1 and rounded to two decimal places.
    """
    return (round(reference_price * 0.95, 2), round(reference_price * 1.1, 2))


def _build_markdown_report(summary: dict[str, object]) -> str:
    """
    Build a human-readable Markdown report summarizing a rehearsal run.

    Parameters:
        summary (dict[str, object]): Summary mapping produced by run_rehearsal. Expected keys:
            - "created_at": ISO timestamp string.
            - "execution_backend": backend identifier.
            - "symbols": list or representation of symbols.
            - "artifact_dir": artifact directory path or string.
            - "passed": boolean overall pass status.
            - "steps": list of step dicts; each step should include at least "name", "exit_code", "duration_ms", and "ok".
            - Optional proposal-related keys: "candidate_id", "proposal_id", "approval_status", "outcome_status", "refresh_check".

    Returns:
        str: A Markdown-formatted string with rehearshal metadata, a per-step PASS/FAIL listing, proposal fields, and notes.
    """
    lines = [
        "# V1 Paper Desk Rehearsal",
        "",
        f"- Created: {summary['created_at']}",
        f"- Execution backend: `{summary['execution_backend']}`",
        f"- Symbols: `{summary['symbols']}`",
        f"- Artifact directory: `{summary['artifact_dir']}`",
        f"- Passed: `{summary['passed']}`",
        "",
        "## Steps",
        "",
    ]
    for step in _object_mapping_list(summary.get("steps")):
        status = "PASS" if step.get("ok") else "FAIL"
        lines.append(
            f"- {status}: `{step.get('name')}` exit={step.get('exit_code')} duration_ms={step.get('duration_ms')}"
        )
    lines.extend(
        [
            "",
            "## Proposal",
            "",
            f"- Candidate ID: `{summary.get('candidate_id') or '-'}`",
            f"- Proposal ID: `{summary.get('proposal_id') or '-'}`",
            f"- Approval status: `{summary.get('approval_status') or '-'}`",
            f"- Outcome status: `{summary.get('outcome_status') or '-'}`",
            f"- Refresh check: `{summary.get('refresh_check') or '-'}`",
            "",
            "## Notes",
            "",
            "- This rehearsal uses an isolated runtime/database under the artifact directory.",
            "- The default `paper` backend does not contact an external broker.",
            "- `alpaca_paper` remains paper-only and keeps live execution disabled.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_rehearsal(args: argparse.Namespace) -> dict[str, object]:
    """
    Orchestrates a V1 paper desk rehearsal by running a sequence of agentic_trader CLI steps, recording per-step evidence and producing summary artifacts in an isolated artifact directory.

    Runs provider diagnostics, readiness checks, finance/research/memory steps, creates/promotes/approves a proposal candidate, conditionally attempts a refresh, collects post-action artifacts and an evidence bundle, and writes both a JSON summary and a Markdown report to the artifact directory.

    Parameters:
        args (argparse.Namespace): Configuration for the rehearsal run (as returned by parse_args).
            Relevant fields used include: symbols, proposal_symbol, reference_price, side,
            quantity, cycles, interval, lookback, thesis, invalidation_condition,
            execution_backend, artifact_root, and label.

    Returns:
        summary (dict[str, object]): A dictionary summarizing the rehearsal with keys:
            - created_at (str): ISO 8601 UTC timestamp when the summary was built.
            - artifact_dir (str): Path to the artifact directory containing written files.
            - execution_backend (str): The execution backend used for the run.
            - symbols (str): Comma-joined symbol list used for the run.
            - candidate_id (object): Created candidate identifier, or None if missing.
            - proposal_id (object): Created proposal identifier, or None if missing.
            - approval_status (object): Proposal approval status, or None.
            - outcome_status (object): Outcome status from the approval step, or None.
            - refresh_check (str): Indicator of which refresh branch was executed.
            - refresh_ok (object): `ok` value from the refresh step payload.
            - evidence_bundle (object): Parsed JSON stdout from the evidence-bundle step, if present.
            - readiness_allowed (bool): Whether readiness allowed paper operations.
            - steps (list[dict]): List of per-step payloads recorded for each executed CLI step.
            - passed (bool): True when readiness_allowed is true and all recorded steps have truthy `ok`.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    label = args.label or f"v1-paper-desk-{timestamp}"
    artifact_dir = (args.artifact_root / label).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    symbols = _symbol_list(args.symbols)
    proposal_symbol = (args.proposal_symbol or symbols[0]).upper()
    stop_loss, take_profit = _proposal_risk_defaults(args.reference_price)
    env = _env_for_run(args, artifact_dir)

    steps: list[dict[str, object]] = []

    def step(
        name: str,
        command_args: list[str],
        *,
        expect_success: bool = True,
        timeout: int = 120,
    ) -> dict[str, object]:
        """
        Run a single agentic_trader CLI step, persist its per-step payload to the rehearsal steps list, and return that payload.

        Parameters:
            name (str): Human-readable label for the step; used as the per-step artifact filename (name.json).
            command_args (list[str]): CLI arguments passed to the agentic_trader command (excluding the python -m prefix).
            expect_success (bool): Whether an exit code of 0 is considered a successful outcome for this step.
            timeout (int): Maximum seconds to wait for the CLI command to complete.

        Returns:
            dict[str, object]: The per-step payload recorded for this step (also appended to the enclosing `steps` list and persisted to disk). The payload includes keys such as `name`, `command`, `exit_code`, `duration_ms`, `expected_success`, `ok`, `stdout_json`, `stdout`, and `stderr`.
        """
        result = _run_step(
            name=name,
            args=command_args,
            env=env,
            artifact_dir=artifact_dir,
            expect_success=expect_success,
            timeout=timeout,
        )
        steps.append(result)
        return result

    step("provider-diagnostics", ["provider-diagnostics", "--json"])
    readiness = step(
        "v1-readiness",
        ["v1-readiness", "--provider-check", "--json"],
        timeout=180,
    )
    step("finance-ops-before", ["finance-ops", "--json"])
    step(
        "research-cycle-run",
        [
            "research-cycle-run",
            "--symbols",
            ",".join(symbols),
            "--cycles",
            str(args.cycles),
            "--no-sleep",
            "--json",
        ],
        timeout=180,
    )
    step(
        "memory-explorer",
        [
            "memory-explorer",
            "--symbol",
            proposal_symbol,
            "--interval",
            args.interval,
            "--lookback",
            args.lookback,
            "--json",
        ],
        timeout=120,
    )
    candidate_created = step(
        "proposal-candidate-create",
        [
            "proposal-candidate-create",
            "--symbol",
            proposal_symbol,
            "--preset",
            "momentum" if args.side == "buy" else "gap-down",
            "--price",
            str(args.reference_price),
            "--volume",
            "5000000",
            "--change-pct",
            "6.2" if args.side == "buy" else "-6.2",
            "--relative-volume",
            "3.4",
            "--rsi",
            "63" if args.side == "buy" else "32",
            "--ema-9",
            str(round(args.reference_price * 0.97, 2)),
            "--gap-pct",
            "0" if args.side == "buy" else "-5.8",
            "--spread-pct",
            "0.05",
            "--quantity",
            str(args.quantity),
            "--thesis",
            args.thesis,
            "--stop-loss",
            str(stop_loss),
            "--take-profit",
            str(take_profit),
            "--invalidation-condition",
            args.invalidation_condition,
            "--source",
            "v1-paper-desk-rehearsal",
            "--materiality",
            "qa_rehearsal_scanner_candidate",
            "--freshness",
            "same_session_rehearsal_input",
            "--liquidity",
            "synthetic_liquid_us_equity_rehearsal",
            "--risk-notes",
            "stop_loss_take_profit_supplied_before_promotion",
            "--json",
        ],
    )
    candidate = _object_mapping(candidate_created.get("stdout_json"))
    candidate_id = candidate.get("candidate_id") if candidate is not None else None
    if not candidate_id:
        raise RuntimeError("proposal-candidate-create did not return a candidate_id")
    promoted = step(
        "proposal-candidate-promote",
        [
            "proposal-candidate-promote",
            str(candidate_id),
            "--review-notes",
            "promoted by V1 paper desk rehearsal",
            "--json",
        ],
    )
    promoted_payload = _object_mapping(promoted.get("stdout_json"))
    proposal = _object_mapping(
        promoted_payload.get("proposal") if promoted_payload is not None else None
    )
    proposal_id = proposal.get("proposal_id") if proposal is not None else None
    if not proposal_id:
        raise RuntimeError("proposal-candidate-promote did not return a proposal_id")
    approved = step(
        "proposal-approve",
        [
            "proposal-approve",
            str(proposal_id),
            "--review-notes",
            "approved by V1 paper desk rehearsal",
            "--json",
        ],
        timeout=180,
    )
    approved_payload = _object_mapping(approved.get("stdout_json"))
    approved_proposal = _object_mapping(
        approved_payload.get("proposal") if approved_payload is not None else None
    )
    outcome = _object_mapping(
        approved_payload.get("outcome") if approved_payload is not None else None
    )
    outcome_status_value = outcome.get("status") if outcome is not None else None
    outcome_status = (
        outcome_status_value if isinstance(outcome_status_value, str) else None
    )
    if outcome_status == "accepted":
        refresh = step(
            "proposal-refresh",
            [
                "proposal-refresh",
                str(proposal_id),
                "--review-notes",
                "refresh accepted broker order from V1 paper desk rehearsal",
                "--json",
            ],
            timeout=180,
        )
        refresh_check = "accepted-order-refresh"
    else:
        refresh = step(
            "proposal-refresh-terminal-guard",
            [
                "proposal-refresh",
                str(proposal_id),
                "--review-notes",
                "verify terminal paper fill is not refreshed",
                "--json",
            ],
            expect_success=False,
        )
        refresh_check = "terminal-refresh-guard"
    step("trade-proposals-after", ["trade-proposals", "--json"])
    step("journal-after", ["journal", "--limit", "10", "--json"])
    step("finance-ops-after", ["finance-ops", "--json"])
    bundle = step(
        "evidence-bundle",
        [
            "evidence-bundle",
            "--output-dir",
            str(artifact_dir),
            "--label",
            "evidence",
            "--provider-check",
            "--json",
        ],
        timeout=180,
    )

    readiness_payload = _object_mapping(readiness.get("stdout_json"))
    paper_operations = _object_mapping(
        readiness_payload.get("paper_operations")
        if readiness_payload is not None
        else None
    )
    readiness_allowed = (
        paper_operations.get("allowed") is True
        if paper_operations is not None
        else False
    )
    approval_status = (
        approved_proposal.get("status") if approved_proposal is not None else None
    )
    summary: dict[str, object] = {
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_dir": str(artifact_dir),
        "execution_backend": args.execution_backend,
        "symbols": ",".join(symbols),
        "candidate_id": candidate_id,
        "proposal_id": proposal_id,
        "approval_status": approval_status,
        "outcome_status": outcome_status,
        "refresh_check": refresh_check,
        "refresh_ok": refresh.get("ok"),
        "evidence_bundle": bundle.get("stdout_json"),
        "readiness_allowed": readiness_allowed,
        "steps": steps,
    }
    summary["passed"] = bool(readiness_allowed) and all(
        bool(step_payload.get("ok")) for step_payload in steps
    )
    _write_json(artifact_dir / "rehearsal-summary.json", summary)
    (artifact_dir / "rehearsal-report.md").write_text(
        _build_markdown_report(summary), encoding="utf-8"
    )
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Create and parse command-line arguments for the V1 paper desk rehearsal CLI.

    Parameters:
        argv (list[str]): List of command-line arguments (typically sys.argv[1:]).

    Arguments parsed:
        --symbols: Comma-separated list of ticker symbols (default "AAPL,MSFT").
        --cycles: Number of research cycles to run (default 2).
        --interval: Data interval for exploration (e.g., "1d") (default "1d").
        --lookback: Lookback window for data (e.g., "180d") (default "180d").
        --proposal-symbol: Symbol to use when creating the proposal (optional).
        --side: Trade side, "buy" or "sell" (default "buy").
        --quantity: Order quantity as a floating-point value (default 1.0).
        --reference-price: Reference price used to derive risk bounds (default 190.0).
        --confidence: Confidence value for proposal generation (default 0.72).
        --thesis: Proposal thesis text (default provided).
        --invalidation-condition: Text describing when to invalidate the proposal (default provided).
        --execution-backend: Execution backend to configure ("paper" or "alpaca_paper", default "paper").
        --artifact-root: Path to the artifact root directory (default DEFAULT_ARTIFACT_ROOT).
        --label: Optional label to namespace the artifact output directory.

    Returns:
        argparse.Namespace: Parsed arguments with attributes corresponding to the options above.
    """
    parser = argparse.ArgumentParser(
        description="Run the V1 paper desk rehearsal and collect QA evidence."
    )
    parser.add_argument("--symbols", default="AAPL,MSFT")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--lookback", default="180d")
    parser.add_argument("--proposal-symbol")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--quantity", type=float, default=1.0)
    parser.add_argument("--reference-price", type=float, default=190.0)
    parser.add_argument("--confidence", type=float, default=0.72)
    parser.add_argument(
        "--thesis",
        default="V1 paper desk rehearsal proposal with explicit risk controls.",
    )
    parser.add_argument(
        "--invalidation-condition",
        default="Close if risk controls trigger or thesis invalidates.",
    )
    parser.add_argument(
        "--execution-backend",
        choices=["paper", "alpaca_paper"],
        default="paper",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
    )
    parser.add_argument("--label")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Run the rehearsal CLI flow and print a compact JSON result to stdout.

    Parameters:
        argv (list[str] | None): Command-line arguments to parse; when `None` uses `sys.argv[1:]`.
            If the first argument is `"--"`, that sentinel is removed before parsing.

    Returns:
        int: 0 when the rehearsal passed, 1 otherwise. On exceptions the function prints an error JSON
        (`{"passed": False, "error": ...}`) and returns 1.
    """
    next_argv = list(argv or sys.argv[1:])
    if next_argv[:1] == ["--"]:
        next_argv = next_argv[1:]
    try:
        summary = run_rehearsal(parse_args(next_argv))
    except Exception as error:
        print(json.dumps({"passed": False, "error": str(error)}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "passed": summary["passed"],
                "artifact_dir": summary["artifact_dir"],
                "proposal_id": summary["proposal_id"],
                "outcome_status": summary["outcome_status"],
                "refresh_check": summary["refresh_check"],
            },
            indent=2,
        )
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
