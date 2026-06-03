"""Research sidecar backend implementations."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.researchd.crewai_setup import default_crewai_flow_dir
from agentic_trader.researchd.orchestrator_contract import (
    contract_error_items as _contract_error_items,
)
from agentic_trader.researchd.orchestrator_contract import (
    contract_memory_update as _contract_memory_update,
)
from agentic_trader.researchd.orchestrator_contract import (
    contract_payload_items as _contract_payload_items,
)
from agentic_trader.researchd.orchestrator_contract import (
    sidecar_process_env as _sidecar_process_env,
)
from agentic_trader.researchd.orchestrator_types import (
    ContractRunner,
    ResearchPipelineResult,
    research_world_state_summary,
    summarize_provider_health,
)
from agentic_trader.researchd.orchestrator_noop_backend import NoopResearchBackend
from agentic_trader.researchd.providers import (
    ResearchProviderOutput,
    provider_health_from_output,
)
from agentic_trader.schemas import ResearchSidecarState, WorldStateSnapshot
from agentic_trader.security import redact_sensitive_text
from agentic_trader.time_utils import utc_now_iso

__all__ = ("CrewAiResearchBackend", "NoopResearchBackend")


class CrewAiResearchBackend:
    """Subprocess boundary for the tracked uv-managed CrewAI Flow sidecar."""

    name = "crewai"

    def __init__(
        self,
        *,
        flow_dir: Path | None = None,
        uv_path: str | None = None,
        timeout_seconds: float = 60.0,
        command_runner: ContractRunner | None = None,
    ) -> None:
        self.flow_dir = flow_dir
        self.uv_path = uv_path
        self.timeout_seconds = timeout_seconds
        self.command_runner = command_runner or self._run_contract_process

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        flow_dir = self.flow_dir or default_crewai_flow_dir(settings)
        uv_path = self.uv_path or shutil.which("uv")
        now = utc_now_iso()
        preflight_message = self._preflight_failure_message(flow_dir, uv_path)
        if preflight_message is not None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=preflight_message,
            )

        completed_or_result = self._run_contract_or_failure(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            flow_dir=flow_dir,
            uv_path=uv_path or "uv",
            now=now,
        )
        if isinstance(completed_or_result, ResearchPipelineResult):
            return completed_or_result

        contract_or_result = self._contract_result_or_failure(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            completed=completed_or_result,
            now=now,
        )
        if isinstance(contract_or_result, ResearchPipelineResult):
            return contract_or_result

        return self._result_from_contract_payload(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            payload=contract_or_result,
        )

    @staticmethod
    def _preflight_failure_message(flow_dir: Path, uv_path: str | None) -> str | None:
        if uv_path is None:
            return "uv is required before the CrewAI Flow sidecar can run."
        if not (flow_dir / "pyproject.toml").exists():
            return f"CrewAI Flow sidecar project is missing at {flow_dir}."
        if not (flow_dir / ".venv").exists():
            return (
                "CrewAI Flow sidecar environment is not installed. "
                "Run 'pnpm run setup:research-flow' first."
            )
        return None

    def _run_contract_or_failure(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        flow_dir: Path,
        uv_path: str,
        now: str,
    ) -> subprocess.CompletedProcess[str] | ResearchPipelineResult:
        try:
            return self.command_runner(
                self._contract_command(uv_path),
                json.dumps(
                    self._contract_request_payload(settings, symbols, provider_outputs)
                ),
                flow_dir,
                _sidecar_process_env(),
                self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            message = "CrewAI Flow sidecar contract timed out."
        except Exception as exc:
            message = (
                "CrewAI Flow sidecar contract failed to start: "
                f"{redact_sensitive_text(exc, max_length=240)}"
            )
        return self._failed_result(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            now=now,
            message=message,
        )

    def _contract_result_or_failure(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        completed: subprocess.CompletedProcess[str],
        now: str,
    ) -> dict[str, object] | ResearchPipelineResult:
        contract_payload = self._contract_payload_from_process(completed)
        if contract_payload is None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=self._non_json_contract_message(completed),
            )
        if completed.returncode == 0 and contract_payload.get("status") == "completed":
            return contract_payload
        return self._failed_result(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            now=now,
            message=self._failed_contract_message(contract_payload),
        )

    @staticmethod
    def _contract_command(uv_path: str) -> list[str]:
        return [
            uv_path,
            "run",
            "--locked",
            "--no-sync",
            "research-flow-contract",
        ]

    def _contract_request_payload(
        self,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> dict[str, object]:
        return {
            "mode": settings.research_mode,
            "symbols": symbols,
            "provider_outputs": [
                self._provider_output_payload(output) for output in provider_outputs
            ],
        }

    def _non_json_contract_message(
        self, completed: subprocess.CompletedProcess[str]
    ) -> str:
        return (
            "CrewAI Flow sidecar returned non-JSON output. "
            f"stdout={redact_sensitive_text(self._trim(completed.stdout), max_length=500)} "
            f"stderr={redact_sensitive_text(self._trim(completed.stderr), max_length=500)}"
        )

    @staticmethod
    def _failed_contract_message(payload: dict[str, object]) -> str:
        error_items = _contract_error_items(payload.get("errors"))
        if error_items:
            return "; ".join(str(item) for item in error_items)
        return "CrewAI Flow sidecar contract returned a failed status."

    @staticmethod
    def _run_contract_process(
        command: list[str],
        stdin_payload: str,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            input=stdin_payload,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

    @staticmethod
    def _provider_output_payload(output: ResearchProviderOutput) -> dict[str, object]:
        return {
            "metadata": output.metadata.model_dump(mode="json"),
            "raw_evidence": [
                item.model_dump(mode="json") for item in output.raw_evidence
            ],
            "macro_events": [
                item.model_dump(mode="json") for item in output.macro_events
            ],
            "social_signals": [
                item.model_dump(mode="json") for item in output.social_signals
            ],
            "missing_reasons": list(output.missing_reasons),
        }

    @staticmethod
    def _contract_payload_from_process(
        completed: subprocess.CompletedProcess[str],
    ) -> dict[str, object] | None:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return None
        return _object_mapping(payload)

    @staticmethod
    def _trim(value: str, *, limit: int = 500) -> str:
        return value.strip().replace("\n", " ")[:limit]

    def _failed_result(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        now: str,
        message: str,
    ) -> ResearchPipelineResult:
        health = [provider_health_from_output(output) for output in provider_outputs]
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="failed",
            updated_at=now,
            last_started_at=now,
            last_error=message,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            memory_update={
                "status": "not_written",
                "reason": "crewai_backend_failed",
                "error": message,
                "raw_web_text_injected": False,
                "broker_access": False,
            },
        )

    def _result_from_contract_payload(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        payload: dict[str, object],
    ) -> ResearchPipelineResult:
        health = [provider_health_from_output(output) for output in provider_outputs]
        items = _contract_payload_items(provider_outputs, payload)
        generated_at = str(payload.get("generated_at") or utc_now_iso())
        observed_at = str(payload.get("observed_at") or generated_at)
        world_state = WorldStateSnapshot(
            snapshot_id=f"world-{uuid4()}",
            mode=settings.research_mode,
            generated_at=generated_at,
            observed_at=observed_at,
            source_attributions=items.attributions,
            watched_symbols=symbols,
            entity_dossiers=items.dossiers,
            macro_events=items.macro_events,
            social_signals=items.social_signals,
            findings=items.findings,
            summary=str(
                payload.get("summary")
                or research_world_state_summary(
                    raw_evidence_count=len(items.raw_evidence),
                    macro_event_count=len(items.macro_events),
                    social_signal_count=len(items.social_signals),
                    finding_count=len(items.findings),
                )
            ),
        )
        memory_update = _contract_memory_update(payload)
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="completed",
            updated_at=generated_at,
            last_started_at=generated_at,
            last_successful_update_at=generated_at,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            world_state=world_state,
            raw_evidence=items.raw_evidence,
            macro_events=items.macro_events,
            social_signals=items.social_signals,
            findings=items.findings,
            dossiers=items.dossiers,
            memory_update=memory_update,
        )

