#!/usr/bin/env python3
"""Run a product-shaped V1 paper desk rehearsal and collect evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / ".ai" / "qa" / "artifacts"


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def _parse_json(stdout: str) -> Any:
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
    payload = {
        "name": name,
        "command": ["agentic-trader", *args],
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "expected_success": expect_success,
        "ok": completed.returncode == 0 if expect_success else completed.returncode != 0,
        "stdout_json": _parse_json(completed.stdout),
        "stdout": completed.stdout if not completed.stdout.strip().startswith("{") else None,
        "stderr": completed.stderr or None,
    }
    _write_json(artifact_dir / f"{name}.json", payload)
    return payload


def _env_for_run(args: argparse.Namespace, artifact_dir: Path) -> dict[str, str]:
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
    symbols = [item.strip().upper() for item in raw_symbols.split(",") if item.strip()]
    if not symbols:
        raise ValueError("at least one symbol is required")
    return symbols


def _proposal_risk_defaults(reference_price: float) -> tuple[float, float]:
    return (round(reference_price * 0.95, 2), round(reference_price * 1.1, 2))


def _build_markdown_report(summary: dict[str, object]) -> str:
    steps = summary["steps"]
    assert isinstance(steps, list)
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
    for step in steps:
        assert isinstance(step, dict)
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
    candidate = candidate_created.get("stdout_json")
    candidate_id = (
        candidate.get("candidate_id") if isinstance(candidate, dict) else None
    )
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
    promoted_payload = promoted.get("stdout_json")
    proposal = (
        promoted_payload.get("proposal")
        if isinstance(promoted_payload, dict)
        else None
    )
    proposal_id = proposal.get("proposal_id") if isinstance(proposal, dict) else None
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
    approved_payload = approved.get("stdout_json")
    approved_proposal = (
        approved_payload.get("proposal") if isinstance(approved_payload, dict) else {}
    )
    outcome = approved_payload.get("outcome") if isinstance(approved_payload, dict) else {}
    outcome_status = outcome.get("status") if isinstance(outcome, dict) else None
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

    readiness_payload = readiness.get("stdout_json")
    readiness_allowed = (
        readiness_payload.get("paper_operations", {}).get("allowed")
        if isinstance(readiness_payload, dict)
        else False
    )
    summary = {
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_dir": str(artifact_dir),
        "execution_backend": args.execution_backend,
        "symbols": ",".join(symbols),
        "candidate_id": candidate_id,
        "proposal_id": proposal_id,
        "approval_status": (
            approved_proposal.get("status") if isinstance(approved_proposal, dict) else None
        ),
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
