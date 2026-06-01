import { getFundamentalAssessmentLines } from '../review-lines.mjs';
import { renderUnavailableMessage } from './context-lines.mjs';

function getReviewLines(reviewRecord) {
  if (!reviewRecord) {
    return ['No persisted runs are available yet.'];
  }
  return [
    `Run ID: ${reviewRecord.run_id}`,
    `Created: ${reviewRecord.created_at}`,
    `Symbol: ${reviewRecord.symbol}`,
    `Approved: ${reviewRecord.approved}`,
    `Coordinator Focus: ${reviewRecord.artifacts.coordinator.market_focus}`,
    ...getFundamentalAssessmentLines(reviewRecord.artifacts.fundamental),
    `Regime: ${reviewRecord.artifacts.regime.regime}`,
    `Strategy: ${reviewRecord.artifacts.strategy.strategy_family}`,
    `Manager Bias: ${reviewRecord.artifacts.manager.action_bias}`,
    `Consensus: ${reviewRecord.artifacts.consensus.alignment_level}`,
    `Review Summary: ${reviewRecord.artifacts.review.summary}`,
  ];
}

function getTraceLines(traceRecord) {
  if (!traceRecord?.artifacts?.agent_traces?.length) {
    return ['No persisted agent traces are available yet.'];
  }
  return traceRecord.artifacts.agent_traces.map(
    (stageTrace) =>
      `${stageTrace.role} | ${stageTrace.model_name} | fallback=${stageTrace.used_fallback} | ${stageTrace.output_json.replaceAll(/\s+/g, ' ').slice(0, 72)}`,
  );
}

function getReplayLines(replayState) {
  if (!replayState) {
    return ['No replayable run is available yet.'];
  }
  return [
    `Final Side: ${replayState.final_side}`,
    `Approved: ${replayState.approved}`,
    `Consensus: ${replayState.consensus.alignment_level}`,
    `MTF: ${replayState.snapshot.mtf_alignment} @ ${replayState.snapshot.higher_timeframe}`,
    `Manager: ${(replayState.manager_override_notes || []).join(' / ')}`,
    `Conflict Count: ${(replayState.manager_conflicts || []).length}`,
    ...(replayState.manager_conflicts || [])
      .slice(0, 3)
      .map(
        (conflict) =>
          `${conflict.conflict_type} [${conflict.severity}] | ${conflict.summary}`,
      ),
    `Final Rationale: ${replayState.final_rationale}`,
    ...replayState.stages
      .slice(0, 5)
      .map(
        (stage) =>
          `${stage.role} | memories=${stage.retrieved_memories.length} | bus=${(stage.shared_memory_bus || []).length} | tools=${stage.tool_outputs.length} | fallback=${stage.used_fallback}`,
      ),
  ];
}

function getExplorerLines(explorer) {
  if (!explorer?.matches?.length) {
    return ['No similar historical memories found yet.'];
  }
  return explorer.matches.map((match) => {
    const reason =
      match.explanation?.eligibility_reason || match.retrieval_source;
    return `${match.created_at} | ${match.symbol} | score=${match.similarity_score} | why=${reason} | ${match.regime} | ${match.strategy_family} | ${match.summary}`;
  });
}

function getInspectionLines(inspection) {
  if (!inspection?.stages?.length) {
    return ['No retrieval inspection data available yet.'];
  }
  return inspection.stages.flatMap((stage) => {
    const retrieved = stage.retrieved_memories?.length ?? 0;
    const notes = stage.memory_notes?.length ?? 0;
    const recentRuns = stage.recent_runs?.length ?? 0;
    const sharedBus = stage.shared_memory_bus?.length ?? 0;
    const why = stage.retrieval_explanations?.length ?? 0;
    const headline = `${stage.role} | retrieved=${retrieved} | why=${why} | trade-memory=${notes} | shared-bus=${sharedBus} | recent-runs=${recentRuns}`;
    const firstWhy = stage.retrieval_explanations?.[0]?.explanation;
    const whyLine = firstWhy
      ? `Why: ${firstWhy.eligibility_reason || '-'} | freshness=${firstWhy.freshness || '-'} | outcome=${firstWhy.outcome_tag || '-'}`
      : null;
    const sample =
      stage.retrieved_memories?.[0] ||
      stage.memory_notes?.[0] ||
      'No retrieval context attached.';
    return [headline, whyLine ? `  ${whyLine}` : `  ${sample}`, ''];
  });
}

function getJournalLines(journal) {
  if (!journal?.entries?.length) {
    return ['No trade journal entries yet.'];
  }
  return journal.entries.map(
    (entry) =>
      `${entry.opened_at} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`,
  );
}

function getRecentRunsLines(recentRuns) {
  if (recentRuns?.available === false) {
    return renderUnavailableMessage(recentRuns.error);
  }
  if (!recentRuns?.runs?.length) {
    return ['No recent runs recorded yet.'];
  }
  return recentRuns.runs.map(
    (run) =>
      `${run.created_at} | ${run.symbol} | ${run.interval} | approved=${run.approved} | ${run.run_id}`,
  );
}

function getInstructionResultLines(result) {
  if (!result) {
    return [
      'Type a safe operator instruction.',
      'Examples:',
      '  make the system conservative',
      '  switch to capital preservation',
    ];
  }
  const instruction = result.instruction || {};
  const update = instruction.preference_update || {};
  const updateLines = Object.entries(update)
    .filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    )
    .map(
      ([key, value]) =>
        `${key}=${Array.isArray(value) ? value.join(',') : value}`,
    );
  return [
    `Summary: ${instruction.summary ?? '-'}`,
    `Update Preferences: ${instruction.should_update_preferences ?? false}`,
    `Requires Confirmation: ${instruction.requires_confirmation ?? false}`,
    `Applied: ${result.applied ? 'yes' : 'no'}`,
    `Rationale: ${instruction.rationale ?? '-'}`,
    `Preference Update: ${updateLines.join(' | ') || '-'}`,
  ];
}

export {
  getReviewLines,
  getTraceLines,
  getReplayLines,
  getExplorerLines,
  getInspectionLines,
  getJournalLines,
  getRecentRunsLines,
  getInstructionResultLines,
};
