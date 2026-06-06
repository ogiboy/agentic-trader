from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import read_service_events, read_service_state
from agentic_trader.runtime_status import RuntimeStatusView, build_runtime_status_view
from agentic_trader.ui_text import t as ui_t

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QA_ARTIFACTS_ROOT = PROJECT_ROOT / ".ai" / "qa" / "artifacts"


class JsonDumpable(Protocol):
    def model_dump(self, *, mode: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class EvidenceBundleCollectors:
    dashboard_snapshot: Callable[[Settings, int, bool], object]
    status_payload: Callable[[RuntimeStatusView, Settings], object]
    broker_payload: Callable[[Settings], object]
    finance_ops_payload: Callable[[Settings], object]
    provider_diagnostics: Callable[[Settings], object]
    v1_readiness: Callable[[Settings, bool], object]
    supervisor_payload: Callable[[Settings], object]
    runtime_mode_operation: Callable[[Settings], JsonDumpable]
    operator_workflow: Callable[[Settings], object]
    research_payload: Callable[[Settings], object]
    hardware_profile: Callable[[Settings], object]


def _claim_timestamped_dir(root: Path, label: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 1000):
        suffix = "" if attempt == 1 else f"-{attempt}"
        candidate = root / f"{label}{suffix}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    msg = ui_t("message.unique_artifact_dir_unavailable").format(label=repr(label))
    raise RuntimeError(msg)


def _write_bundle_json(bundle_dir: Path, filename: str, payload: object) -> str:
    path = bundle_dir / filename
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def _latest_smoke_artifact_dir(artifacts_root: Path) -> Path | None:
    if not artifacts_root.exists():
        return None
    candidates = [
        path
        for path in artifacts_root.glob("smoke-*")
        if path.is_dir() and (path / "smoke-summary.json").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _resolved_artifacts_root(output_dir: Path | None) -> Path:
    artifacts_root = (
        output_dir.expanduser() if output_dir is not None else QA_ARTIFACTS_ROOT
    )
    return (
        artifacts_root
        if artifacts_root.is_absolute()
        else PROJECT_ROOT / artifacts_root
    )


def _write_core_artifacts(
    *,
    bundle_dir: Path,
    collectors: EvidenceBundleCollectors,
    settings: Settings,
    status_view: RuntimeStatusView,
    log_limit: int,
    check_provider: bool,
) -> dict[str, str]:
    events = read_service_events(settings, limit=log_limit)
    return {
        "dashboard": _write_bundle_json(
            bundle_dir,
            "dashboard-snapshot.json",
            collectors.dashboard_snapshot(settings, log_limit, check_provider),
        ),
        "status": _write_bundle_json(
            bundle_dir,
            "status.json",
            collectors.status_payload(status_view, settings),
        ),
        "broker": _write_bundle_json(
            bundle_dir,
            "broker-status.json",
            collectors.broker_payload(settings),
        ),
        "finance_ops": _write_bundle_json(
            bundle_dir,
            "finance-ops.json",
            collectors.finance_ops_payload(settings),
        ),
        "provider_diagnostics": _write_bundle_json(
            bundle_dir,
            "provider-diagnostics.json",
            collectors.provider_diagnostics(settings),
        ),
        "v1_readiness": _write_bundle_json(
            bundle_dir,
            "v1-readiness.json",
            collectors.v1_readiness(settings, check_provider),
        ),
        "supervisor": _write_bundle_json(
            bundle_dir,
            "supervisor-status.json",
            collectors.supervisor_payload(settings),
        ),
        "logs": _write_bundle_json(
            bundle_dir,
            "logs.json",
            {"logs": [event.model_dump(mode="json") for event in events]},
        ),
        "runtime_mode_operation": _write_bundle_json(
            bundle_dir,
            "runtime-mode-operation-checklist.json",
            collectors.runtime_mode_operation(settings).model_dump(mode="json"),
        ),
        "operator_workflow": _write_bundle_json(
            bundle_dir,
            "operator-workflow.json",
            collectors.operator_workflow(settings),
        ),
        "research": _write_bundle_json(
            bundle_dir,
            "research-status.json",
            collectors.research_payload(settings),
        ),
        "hardware_profile": _write_bundle_json(
            bundle_dir,
            "hardware-profile.json",
            collectors.hardware_profile(settings),
        ),
    }


def _copy_latest_smoke_artifacts(
    *,
    artifacts_root: Path,
    bundle_dir: Path,
    files: dict[str, str],
) -> Path | None:
    latest_smoke_dir = _latest_smoke_artifact_dir(artifacts_root)
    if latest_smoke_dir is None:
        return None
    for source_name, target_name, key in (
        ("smoke-summary.json", "latest-smoke-summary.json", "latest_smoke_summary"),
        ("qa-report.md", "latest-qa-report.md", "latest_qa_report"),
    ):
        source = latest_smoke_dir / source_name
        if source.exists():
            target = bundle_dir / target_name
            shutil.copyfile(source, target)
            files[key] = str(target)
    return latest_smoke_dir


def build_evidence_bundle(
    settings: Settings,
    *,
    collectors: EvidenceBundleCollectors,
    output_dir: Path | None = None,
    label: str | None = None,
    log_limit: int = 20,
    include_latest_smoke: bool = True,
    check_provider: bool = False,
) -> dict[str, object]:
    artifacts_root = _resolved_artifacts_root(output_dir)
    run_label = label or f"evidence-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    bundle_dir = _claim_timestamped_dir(artifacts_root, run_label)

    state = read_service_state(settings)
    status_view = build_runtime_status_view(state)
    files = _write_core_artifacts(
        bundle_dir=bundle_dir,
        collectors=collectors,
        settings=settings,
        status_view=status_view,
        log_limit=log_limit,
        check_provider=check_provider,
    )
    latest_smoke_dir = (
        _copy_latest_smoke_artifacts(
            artifacts_root=artifacts_root,
            bundle_dir=bundle_dir,
            files=files,
        )
        if include_latest_smoke
        else None
    )

    manifest: dict[str, object] = {
        "bundle_version": "qa-evidence.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(bundle_dir),
        "runtime_dir": str(settings.runtime_dir),
        "database_path": str(settings.database_path),
        "log_limit": log_limit,
        "latest_smoke_dir": str(latest_smoke_dir) if latest_smoke_dir else None,
        "files": files,
    }
    manifest_path = bundle_dir / "manifest.json"
    files["manifest"] = str(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    return manifest
