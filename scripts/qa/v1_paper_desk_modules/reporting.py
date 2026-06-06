from __future__ import annotations

import json
from pathlib import Path
from typing import cast


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def parse_json(stdout: str) -> object | None:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


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


def build_markdown_report(summary: dict[str, object]) -> str:
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


def write_rehearsal_outputs(context: object, summary: dict[str, object]) -> None:
    artifact_dir = getattr(context, "artifact_dir")
    write_json(artifact_dir / "rehearsal-summary.json", summary)
    (artifact_dir / "rehearsal-report.md").write_text(
        build_markdown_report(summary), encoding="utf-8"
    )
