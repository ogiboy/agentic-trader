import type { DashboardData } from '../control-room.helpers';
import {
  formatTimestamp,
  unavailableSectionLines,
} from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { Panel, TextList } from './primitives';

type RetrievalExplanation = {
  explanation?: {
    eligibility_reason?: unknown;
    freshness?: unknown;
    outcome_tag?: unknown;
  };
};

type MemoryMatch = {
  created_at?: unknown;
  explanation?: {
    eligibility_reason?: unknown;
  };
  retrieval_source?: unknown;
  similarity_score?: unknown;
  summary?: unknown;
  symbol?: unknown;
};

type RetrievalStage = {
  memory_notes?: unknown[];
  recent_runs?: unknown[];
  retrieved_memories?: unknown[];
  retrieval_explanations?: RetrievalExplanation[];
  role?: unknown;
  shared_memory_bus?: unknown[];
};

function textValue(value: unknown): string {
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }
  return '-';
}

export function MemoryView({
  copy,
  dashboard,
}: Readonly<{ copy: ControlRoomCopy; dashboard: DashboardData }>) {
  const memoryLines =
    unavailableSectionLines(
      dashboard.memoryExplorer,
      copy.memory.labels.memoryExplorer,
    ) ||
    (dashboard.memoryExplorer?.matches?.length
      ? (dashboard.memoryExplorer.matches as MemoryMatch[]).map((match) => {
          const reason =
            match.explanation?.eligibility_reason || match.retrieval_source;
          return `${formatTimestamp(match.created_at)} | ${textValue(match.symbol)} | score=${textValue(match.similarity_score)} | why=${textValue(reason)} | ${textValue(match.summary)}`;
        })
      : [copy.memory.emptySimilar]);
  const retrievalLines =
    unavailableSectionLines(
      dashboard.retrievalInspection,
      copy.memory.labels.retrievalInspection,
    ) ||
    (dashboard.retrievalInspection?.stages?.length
      ? (dashboard.retrievalInspection.stages as RetrievalStage[]).flatMap(
          (stage) => {
            const firstWhy = stage.retrieval_explanations?.[0]?.explanation;
            const sample =
              stage.retrieved_memories?.[0] ?? stage.memory_notes?.[0];
            const sampleText =
              sample == null
                ? copy.memory.labels.noRetrievalContext
                : textValue(sample);
            const whyLine = firstWhy
              ? `${copy.memory.labels.why}: ${textValue(firstWhy.eligibility_reason)} | freshness=${textValue(firstWhy.freshness)} | outcome=${textValue(firstWhy.outcome_tag)}`
              : `${copy.memory.labels.sample}: ${sampleText}`;
            return [
              `${textValue(stage.role)} | retrieved=${stage.retrieved_memories?.length ?? 0} | why=${stage.retrieval_explanations?.length ?? 0} | trade-memory=${stage.memory_notes?.length ?? 0} | shared-bus=${stage.shared_memory_bus?.length ?? 0} | recent-runs=${stage.recent_runs?.length ?? 0}`,
              whyLine,
            ];
          },
        )
      : [copy.memory.emptyRetrieval]);

  return (
    <div className='grid grid--2'>
      <Panel title={copy.memory.panels.similarPastRuns} accent='lime'>
        <TextList items={memoryLines} />
      </Panel>
      <Panel title={copy.memory.panels.whyContextWasUsed} accent='cyan'>
        <TextList items={retrievalLines} />
      </Panel>
    </div>
  );
}
