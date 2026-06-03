"""Trade context payload assembly helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.schemas import (
    AgentStageTrace,
    RunArtifacts,
    TradeContextRecord,
)


@dataclass
class TraceContextSummaries:
    routed_models: dict[str, str]
    retrieved_memory_summary: dict[str, list[str]]
    retrieval_explanation_summary: dict[str, list[dict[str, object]]]
    tool_outputs: dict[str, list[str]]
    shared_memory_summary: dict[str, list[str]]


@dataclass(frozen=True)
class ExecutionContextPayload:
    backend: str | None
    adapter: str | None
    intent: dict[str, object] | None
    outcome_status: str | None
    rejection_reason: str | None
    outcome: dict[str, object] | None
    simulated_metadata: dict[str, object]


def summarize_trace_contexts(
    traces: list[AgentStageTrace],
) -> TraceContextSummaries:
    summaries = _empty_trace_context_summaries()
    for trace in traces:
        summaries.routed_models[trace.role] = trace.model_name
        context = _trace_context(trace)
        if context is None:
            continue
        _collect_trace_context_summary(summaries, trace.role, context)
    return summaries


def execution_context_payload(
    *,
    execution_intent: ExecutionIntent | None = None,
    execution_outcome: ExecutionOutcome | None = None,
) -> ExecutionContextPayload:
    return ExecutionContextPayload(
        backend=(
            execution_intent.execution_backend if execution_intent is not None else None
        ),
        adapter=_execution_adapter_name(execution_intent, execution_outcome),
        intent=(
            cast(dict[str, object], execution_intent.model_dump(mode="json"))
            if execution_intent is not None
            else None
        ),
        outcome_status=(
            execution_outcome.status if execution_outcome is not None else None
        ),
        rejection_reason=(
            execution_outcome.rejection_reason
            if execution_outcome is not None
            else None
        ),
        outcome=(
            cast(dict[str, object], execution_outcome.model_dump(mode="json"))
            if execution_outcome is not None
            else None
        ),
        simulated_metadata=(
            execution_outcome.simulated_metadata
            if execution_outcome is not None
            else {}
        ),
    )


def trade_context_record(
    *,
    trade_id: str,
    run_id: str | None,
    artifacts: RunArtifacts,
    trace_summaries: TraceContextSummaries,
    execution_context: ExecutionContextPayload,
) -> TradeContextRecord:
    return TradeContextRecord(
        trade_id=trade_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        symbol=artifacts.snapshot.symbol,
        market_snapshot=artifacts.snapshot,
        market_context_pack=artifacts.snapshot.context_pack,
        canonical_snapshot=artifacts.canonical_snapshot,
        decision_features=artifacts.decision_features,
        routed_models=trace_summaries.routed_models,
        retrieved_memory_summary=trace_summaries.retrieved_memory_summary,
        retrieval_explanation_summary=trace_summaries.retrieval_explanation_summary,
        tool_outputs=trace_summaries.tool_outputs,
        shared_memory_summary=trace_summaries.shared_memory_summary,
        consensus=artifacts.consensus,
        fundamental_assessment=artifacts.fundamental,
        fundamental_summary=artifacts.fundamental.summary,
        macro_summary=artifacts.macro.summary,
        manager_rationale=artifacts.manager.rationale,
        manager_conflicts=artifacts.manager.conflicts,
        manager_resolution_notes=artifacts.manager.resolution_notes,
        execution_rationale=artifacts.execution.rationale,
        execution_backend=execution_context.backend,
        execution_adapter=execution_context.adapter,
        execution_intent=execution_context.intent,
        execution_outcome_status=execution_context.outcome_status,
        execution_rejection_reason=execution_context.rejection_reason,
        execution_outcome=execution_context.outcome,
        simulated_fill_metadata=execution_context.simulated_metadata,
        review_summary=artifacts.review.summary,
        review_warnings=artifacts.review.warnings,
    )


def _empty_trace_context_summaries() -> TraceContextSummaries:
    return TraceContextSummaries(
        routed_models={},
        retrieved_memory_summary={},
        retrieval_explanation_summary={},
        tool_outputs={},
        shared_memory_summary={},
    )


def _trace_context(trace: AgentStageTrace) -> dict[str, Any] | None:
    try:
        context = json.loads(trace.context_json)
    except json.JSONDecodeError:
        return None
    return cast(dict[str, Any], context) if isinstance(context, dict) else None


def _collect_trace_context_summary(
    summaries: TraceContextSummaries,
    role: str,
    context: dict[str, Any],
) -> None:
    retrieved_memories = context.get("retrieved_memories")
    if isinstance(retrieved_memories, list):
        summaries.retrieved_memory_summary[role] = [
            str(item) for item in cast(list[object], retrieved_memories)[:5]
        ]

    retrieval_explanations = context.get("retrieval_explanations")
    if isinstance(retrieval_explanations, list):
        summaries.retrieval_explanation_summary[role] = [
            cast(dict[str, Any], item)
            for item in cast(list[object], retrieval_explanations)[:5]
            if isinstance(item, dict)
        ]

    trace_tool_outputs = context.get("tool_outputs")
    if isinstance(trace_tool_outputs, list):
        summaries.tool_outputs[role] = [
            str(item) for item in cast(list[object], trace_tool_outputs)[:5]
        ]

    shared_memory_bus = context.get("shared_memory_bus")
    if isinstance(shared_memory_bus, list):
        summaries.shared_memory_summary[role] = [
            str(cast(dict[str, object], item).get("summary", ""))
            for item in cast(list[object], shared_memory_bus)[:5]
            if isinstance(item, dict)
        ]


def _execution_adapter_name(
    execution_intent: ExecutionIntent | None,
    execution_outcome: ExecutionOutcome | None,
) -> str | None:
    if execution_outcome is not None:
        return execution_outcome.adapter_name
    if execution_intent is not None:
        return execution_intent.adapter_name
    return None
