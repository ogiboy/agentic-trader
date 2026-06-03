from __future__ import annotations

import json

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.schemas import ManagerDecision, RunArtifacts, RunRecord, RunReplay
from agentic_trader.ui_text import (
    LABEL_APPROVED,
    LABEL_CONTEXT,
    LABEL_CREATED,
    LABEL_DECISION,
    LABEL_FALLBACK,
    LABEL_FIELD,
    LABEL_FINAL_RATIONALE,
    LABEL_FINAL_SIDE,
    LABEL_INTERVAL,
    LABEL_MEMORIES,
    LABEL_MODEL,
    LABEL_MULTI_TIMEFRAME,
    LABEL_NOTES,
    LABEL_OUTPUT,
    LABEL_OUTPUT_PREVIEW,
    LABEL_RESOLUTION_NOTES,
    LABEL_ROLE,
    LABEL_SPECIALIST,
    LABEL_STAGE,
    LABEL_SYMBOL,
    LABEL_TOOLS,
    LABEL_VALUE,
    LABEL_WARNINGS,
    STAGE_CONSENSUS,
    STAGE_COORDINATOR,
    STAGE_EXECUTION,
    STAGE_FUNDAMENTAL,
    STAGE_MANAGER,
    STAGE_REGIME,
    STAGE_RISK,
    STAGE_STRATEGY,
    TITLE_AGENT_DECISIONS,
    TITLE_AGENT_TRACE,
    TITLE_MANAGER_CONFLICT_REPLAY,
    TITLE_MANAGER_CONFLICTS,
    TITLE_MANAGER_OVERRIDE_NOTES,
    TITLE_MEMORY_AWARE_REPLAY,
    TITLE_REPLAY_STAGES,
    TITLE_REVIEW_NOTE,
    TITLE_RUN_REVIEW,
    TITLE_TRACE,
    UI_LIST_SEPARATOR,
)


def render_run_markdown(record: RunRecord) -> str:
    artifacts = record.artifacts
    lines = _run_header_lines(record)
    lines.extend(_fundamental_lines(artifacts))
    lines.extend(_decision_lines(artifacts))
    lines.extend(_manager_lines(artifacts))
    lines.extend(_execution_review_lines(artifacts))
    return "\n".join(lines)


def render_run_review(record: RunRecord) -> None:
    metadata = _run_review_metadata(record)
    analysis = _run_review_analysis(record)
    console.print(Columns([metadata, analysis]))
    console.print(
        Panel(
            "\n".join(f"- {note}" for note in manager_override_notes(record.artifacts)),
            title=TITLE_MANAGER_OVERRIDE_NOTES,
            border_style="yellow",
        )
    )
    console.print(manager_conflicts_panel(record.artifacts.manager))
    console.print(
        Panel(
            record.artifacts.review.model_dump_json(indent=2),
            title=TITLE_REVIEW_NOTE,
            border_style="cyan",
        )
    )


def _run_review_metadata(record: RunRecord) -> Table:
    metadata = Table(title=TITLE_RUN_REVIEW + " / " + record.run_id)
    metadata.add_column(LABEL_FIELD)
    metadata.add_column(LABEL_VALUE)
    metadata.add_row(LABEL_CREATED, record.created_at)
    metadata.add_row(LABEL_SYMBOL, record.symbol)
    metadata.add_row(LABEL_INTERVAL, record.interval)
    metadata.add_row(LABEL_APPROVED, str(record.approved))
    return metadata


def _run_review_analysis(record: RunRecord) -> Table:
    artifacts = record.artifacts
    analysis = Table(title=TITLE_AGENT_DECISIONS)
    analysis.add_column(LABEL_STAGE)
    analysis.add_column(LABEL_DECISION)
    analysis.add_column(LABEL_NOTES)
    analysis.add_row(
        STAGE_COORDINATOR,
        artifacts.coordinator.market_focus,
        artifacts.coordinator.summary,
    )
    analysis.add_row(
        STAGE_FUNDAMENTAL,
        artifacts.fundamental.overall_bias,
        (
            f"{artifacts.fundamental.summary} | "
            f"red_flags={UI_LIST_SEPARATOR.join(artifacts.fundamental.red_flags) or '-'}"
        ),
    )
    analysis.add_row(STAGE_REGIME, artifacts.regime.regime, artifacts.regime.reasoning)
    analysis.add_row(
        STAGE_STRATEGY,
        artifacts.strategy.strategy_family,
        artifacts.strategy.entry_logic,
    )
    analysis.add_row(
        STAGE_RISK,
        f"size={artifacts.risk.position_size_pct:.2%}",
        artifacts.risk.notes,
    )
    analysis.add_row(
        STAGE_CONSENSUS,
        artifacts.consensus.alignment_level,
        artifacts.consensus.summary or "-",
    )
    analysis.add_row(
        STAGE_MANAGER, artifacts.manager.action_bias, artifacts.manager.rationale
    )
    analysis.add_row(
        STAGE_EXECUTION,
        artifacts.execution.side,
        artifacts.execution.rationale,
    )
    return analysis


def manager_conflicts_panel(manager: ManagerDecision) -> Panel:
    if not manager.conflicts:
        body = "\n".join(f"- {note}" for note in manager.resolution_notes) or (
            "- Manager accepted the specialist plan without additional overrides."
        )
        return Panel(body, title=TITLE_MANAGER_CONFLICTS, border_style="green")

    lines: list[str] = []
    for conflict in manager.conflicts:
        lines.append(
            f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
        )
        lines.append(f"  Specialist: {conflict.specialist_view}")
        lines.append(f"  Manager: {conflict.manager_resolution}")
    if manager.resolution_notes:
        lines.append("")
        lines.append(LABEL_RESOLUTION_NOTES + ":")
        lines.extend(f"- {note}" for note in manager.resolution_notes)
    return Panel("\n".join(lines), title=TITLE_MANAGER_CONFLICTS, border_style="yellow")


def render_run_trace(record: RunRecord) -> None:
    table = Table(title=TITLE_AGENT_TRACE + " / " + record.run_id)
    table.add_column(LABEL_ROLE)
    table.add_column(LABEL_MODEL)
    table.add_column(LABEL_FALLBACK)
    table.add_column(LABEL_OUTPUT_PREVIEW)
    for trace in record.artifacts.agent_traces:
        preview = trace.output_json.replace("\n", " ")[:120]
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback), preview)
    console.print(table)
    for trace in record.artifacts.agent_traces:
        trace_body = "\n".join(
            (
                f"[bold]{LABEL_CONTEXT}[/bold]",
                trace.context_json,
                "",
                f"[bold]{LABEL_OUTPUT}[/bold]",
                trace.output_json,
            )
        )
        console.print(
            Panel(
                trace_body,
                title=TITLE_TRACE + " / " + trace.role,
                border_style="cyan" if not trace.used_fallback else "yellow",
            )
        )


def render_run_replay(replay: RunReplay) -> None:
    summary = _run_replay_summary(replay)
    console.print(summary)
    console.print(
        Panel(
            "\n".join(f"- {note}" for note in replay.manager_override_notes),
            title=TITLE_MANAGER_OVERRIDE_NOTES,
            border_style="yellow",
        )
    )
    _render_replay_conflicts(replay)
    _render_replay_stages(replay)


def _run_replay_summary(replay: RunReplay) -> Table:
    summary = Table(title=TITLE_MEMORY_AWARE_REPLAY + " / " + replay.run_id)
    summary.add_column(LABEL_FIELD)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_CREATED, replay.created_at)
    summary.add_row(LABEL_SYMBOL, replay.symbol)
    summary.add_row(LABEL_INTERVAL, replay.interval)
    summary.add_row(LABEL_APPROVED, str(replay.approved))
    summary.add_row(LABEL_FINAL_SIDE, replay.final_side)
    summary.add_row(LABEL_FINAL_RATIONALE, replay.final_rationale)
    summary.add_row(STAGE_CONSENSUS, replay.consensus.alignment_level)
    summary.add_row(
        LABEL_MULTI_TIMEFRAME,
        f"{replay.snapshot.mtf_alignment} @ {replay.snapshot.higher_timeframe} ({replay.snapshot.mtf_confidence:.2f})",
    )
    return summary


def _render_replay_conflicts(replay: RunReplay) -> None:
    if not replay.manager_conflicts:
        return
    lines: list[str] = []
    for conflict in replay.manager_conflicts:
        lines.append(
            f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
        )
        lines.append(f"  {LABEL_SPECIALIST}: {conflict.specialist_view}")
        lines.append(f"  {STAGE_MANAGER}: {conflict.manager_resolution}")
    if replay.manager_resolution_notes:
        lines.append("")
        lines.append(LABEL_RESOLUTION_NOTES + ":")
        lines.extend(f"- {note}" for note in replay.manager_resolution_notes)
    console.print(
        Panel(
            "\n".join(lines),
            title=TITLE_MANAGER_CONFLICT_REPLAY,
            border_style="yellow",
        )
    )


def _render_replay_stages(replay: RunReplay) -> None:
    stage_table = Table(title=TITLE_REPLAY_STAGES)
    stage_table.add_column(LABEL_ROLE)
    stage_table.add_column(LABEL_MODEL)
    stage_table.add_column(LABEL_FALLBACK)
    stage_table.add_column(LABEL_MEMORIES)
    stage_table.add_column(LABEL_TOOLS)
    stage_table.add_column(LABEL_OUTPUT_PREVIEW)
    for stage in replay.stages:
        output_preview = (
            json.dumps(stage.output, indent=2)
            if isinstance(stage.output, dict)
            else stage.output
        ).replace("\n", " ")[:120]
        stage_table.add_row(
            stage.role,
            stage.model_name,
            str(stage.used_fallback),
            str(len(stage.retrieved_memories)),
            str(len(stage.tool_outputs)),
            output_preview,
        )
    console.print(stage_table)


def _run_header_lines(record: RunRecord) -> list[str]:
    artifacts = record.artifacts
    return [
        "# " + TITLE_RUN_REVIEW + ": " + record.run_id,
        "",
        "## Metadata",
        f"- Created: {record.created_at}",
        f"- Symbol: {record.symbol}",
        f"- Interval: {record.interval}",
        f"- Approved: {record.approved}",
        "",
        "## Coordinator",
        f"- Focus: {artifacts.coordinator.market_focus}",
        f"- Summary: {artifacts.coordinator.summary}",
        "",
    ]


def _fundamental_lines(artifacts: RunArtifacts) -> list[str]:
    fundamental_evidence = artifacts.fundamental.evidence_vs_inference
    return [
        "## Fundamental",
        f"- Overall Bias: {artifacts.fundamental.overall_bias}",
        f"- Growth Quality: {artifacts.fundamental.growth_quality}",
        f"- Profitability Quality: {artifacts.fundamental.profitability_quality}",
        f"- Cash Flow Quality: {artifacts.fundamental.cash_flow_quality}",
        f"- Balance Sheet Quality: {artifacts.fundamental.balance_sheet_quality}",
        f"- FX Risk: {artifacts.fundamental.fx_risk}",
        f"- Business Quality: {artifacts.fundamental.business_quality}",
        f"- Macro Fit: {artifacts.fundamental.macro_fit}",
        f"- Forward Outlook: {artifacts.fundamental.forward_outlook}",
        f"- Red Flags: {join_or_dash(artifacts.fundamental.red_flags)}",
        f"- Strengths: {join_or_dash(artifacts.fundamental.strengths)}",
        f"- Evidence: {join_or_dash(fundamental_evidence.evidence)}",
        f"- Inference: {join_or_dash(fundamental_evidence.inference)}",
        f"- Uncertainty: {join_or_dash(fundamental_evidence.uncertainty)}",
        f"- Summary: {artifacts.fundamental.summary}",
        "",
    ]


def _decision_lines(artifacts: RunArtifacts) -> list[str]:
    return [
        "## Regime",
        f"- Regime: {artifacts.regime.regime}",
        f"- Direction Bias: {artifacts.regime.direction_bias}",
        f"- Reasoning: {artifacts.regime.reasoning}",
        "",
        "## Strategy",
        f"- Family: {artifacts.strategy.strategy_family}",
        f"- Action: {artifacts.strategy.action}",
        f"- Entry Logic: {artifacts.strategy.entry_logic}",
        f"- Invalidation Logic: {artifacts.strategy.invalidation_logic}",
        "",
        "## Risk",
        f"- Position Size: {artifacts.risk.position_size_pct:.2%}",
        f"- Stop Loss: {artifacts.risk.stop_loss:.4f}",
        f"- Take Profit: {artifacts.risk.take_profit:.4f}",
        f"- Notes: {artifacts.risk.notes}",
        "",
        "## Consensus",
        f"- Alignment: {artifacts.consensus.alignment_level}",
        f"- Summary: {value_or_dash(artifacts.consensus.summary)}",
        f"- Supporting Roles: {join_or_dash(artifacts.consensus.supporting_roles)}",
        f"- Dissenting Roles: {join_or_dash(artifacts.consensus.dissenting_roles)}",
        f"- Reasons: {join_or_dash(artifacts.consensus.reasons)}",
        "",
    ]


def _manager_lines(artifacts: RunArtifacts) -> list[str]:
    lines = [
        "## Manager",
        f"- Action Bias: {artifacts.manager.action_bias}",
        f"- Confidence Cap: {artifacts.manager.confidence_cap:.2f}",
        f"- Size Multiplier: {artifacts.manager.size_multiplier:.2f}",
        f"- Rationale: {artifacts.manager.rationale}",
        f"- Override Applied: {artifacts.manager.override_applied}",
        "",
        "## Manager Conflicts",
    ]
    lines.extend(_manager_conflict_lines(artifacts))
    lines.extend(
        [
            "",
            "## Manager Resolution Notes",
            *_markdown_bullets(
                manager_resolution_notes(artifacts),
                fallback="No additional manager resolution notes.",
            ),
            "",
        ]
    )
    return lines


def _execution_review_lines(artifacts: RunArtifacts) -> list[str]:
    return [
        "## Execution",
        f"- Approved: {artifacts.execution.approved}",
        f"- Side: {artifacts.execution.side}",
        f"- Entry Price: {artifacts.execution.entry_price:.4f}",
        f"- Rationale: {artifacts.execution.rationale}",
        "",
        "## Review",
        f"- Summary: {artifacts.review.summary}",
        f"- Strengths: {join_or_dash(artifacts.review.strengths)}",
        "- " + LABEL_WARNINGS + ": " + join_or_dash(artifacts.review.warnings),
        f"- Next Checks: {join_or_dash(artifacts.review.next_checks)}",
        "",
    ]


def manager_override_notes(artifacts: RunArtifacts) -> list[str]:
    notes: list[str] = []
    if artifacts.manager.action_bias != artifacts.strategy.action:
        notes.append(
            f"Manager bias {artifacts.manager.action_bias} diverged from strategy action {artifacts.strategy.action}."
        )
    if artifacts.manager.confidence_cap < artifacts.strategy.confidence:
        notes.append(
            f"Manager confidence cap {artifacts.manager.confidence_cap:.2f} tightened strategy confidence {artifacts.strategy.confidence:.2f}."
        )
    if artifacts.manager.size_multiplier < 1.0:
        notes.append(
            f"Manager size multiplier {artifacts.manager.size_multiplier:.2f} reduced the planned position size."
        )
    if artifacts.execution.approved != artifacts.manager.approved:
        notes.append(
            f"Execution approval {artifacts.execution.approved} differed from manager approval {artifacts.manager.approved}."
        )
    if not notes:
        notes.append(
            "Manager accepted the specialist plan without additional overrides."
        )
    return notes


def manager_resolution_notes(artifacts: RunArtifacts) -> list[str]:
    return artifacts.manager.resolution_notes or manager_override_notes(artifacts)


def _manager_conflict_lines(artifacts: RunArtifacts) -> list[str]:
    if not artifacts.manager.conflicts:
        return ["- None detected."]

    lines: list[str] = []
    for conflict in artifacts.manager.conflicts:
        lines.append(
            f"- [{conflict.severity}] {conflict.conflict_type}: {conflict.summary}"
        )
        lines.append(f"  - Specialist: {conflict.specialist_view}")
        lines.append(f"  - Manager: {conflict.manager_resolution}")
    return lines


def value_or_dash(value: object) -> str:
    return str(value) if value else "-"


def join_or_dash(values: list[str] | tuple[str, ...]) -> str:
    return UI_LIST_SEPARATOR.join(values) if values else "-"


def _markdown_bullets(values: list[str], *, fallback: str) -> list[str]:
    if not values:
        return [f"- {fallback}"]
    return [f"- {value}" for value in values]
