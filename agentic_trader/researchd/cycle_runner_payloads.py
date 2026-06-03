from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.payloads import dataclass_payload
from agentic_trader.researchd.cycle_runner_types import (
    ResearchCycleExecution,
    ResolvedResearchCycleRequest,
)
from agentic_trader.researchd.orchestrator import utc_now_iso
from agentic_trader.schemas import (
    ResearchCycleOperatorControl,
    ResearchDigestReplayRecord,
)


def research_cycle_execution_payload(
    execution: ResearchCycleExecution,
) -> dict[str, object]:
    return dataclass_payload(execution)


def research_digest_replay(
    *,
    settings: Settings,
    resolved: ResolvedResearchCycleRequest,
    executions: list[ResearchCycleExecution],
    latest_digest: dict[str, object],
    execution_policy: dict[str, bool],
    operator_control: ResearchCycleOperatorControl,
) -> ResearchDigestReplayRecord:
    return ResearchDigestReplayRecord(
        artifact_id=f"research-digest-{uuid4()}",
        generated_at=utc_now_iso(),
        snapshot_id=digest_snapshot_id(latest_digest),
        mode=settings.research_mode,
        backend=(
            executions[-1].backend if executions else settings.research_sidecar_backend
        ),
        watched_symbols=list(resolved.symbols),
        digest=dict(latest_digest),
        executions=[
            research_cycle_execution_payload(execution) for execution in executions
        ],
        execution_policy=execution_policy,
        operator_control=operator_control,
        replay_notes=[
            "artifact_replays_operator_digest_only",
            "raw_web_text_is_not_included",
            "broker_or_proposal_authority_is_disabled",
        ],
    )


def digest_snapshot_id(latest_digest: dict[str, object]) -> str | None:
    value = latest_digest.get("snapshot_id")
    return str(value) if value is not None else None


def research_cycle_run_payload(
    *,
    plan: dict[str, object],
    resolved: ResolvedResearchCycleRequest,
    executions: list[ResearchCycleExecution],
    execution_policy: dict[str, bool],
    operator_control: ResearchCycleOperatorControl,
    digest_replay: ResearchDigestReplayRecord,
    latest_digest: dict[str, object],
) -> dict[str, object]:
    return {
        "cycle": "research-cycle-run",
        "plan": plan,
        "requested_cycles": resolved.requested_cycles,
        "executed_cycles": len(executions),
        "cadence_seconds": resolved.safe_cadence,
        "persisted": resolved.persist,
        "sleep_between_cycles": resolved.sleep_between_cycles,
        "execution_policy": execution_policy,
        "operator_control": operator_control.model_dump(mode="json"),
        "digest_replay": digest_replay.model_dump(mode="json"),
        "latest_digest": latest_digest,
        "executions": [
            research_cycle_execution_payload(execution) for execution in executions
        ],
    }


def execution_policy_payload() -> dict[str, bool]:
    return {
        "broker_access": False,
        "proposal_approval": False,
        "proposal_creation": False,
        "raw_web_text_in_core_prompt": False,
        "manual_review_required": True,
    }
