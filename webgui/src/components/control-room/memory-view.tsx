/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
import {
  formatTimestamp,
  unavailableSectionLines,
} from '../control-room.helpers';
import type { DashboardData } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { Panel, TextList } from './primitives';

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
      ? dashboard.memoryExplorer.matches.map((match: Record<string, any>) => {
          const reason =
            match.explanation?.eligibility_reason || match.retrieval_source;
          return `${formatTimestamp(match.created_at)} | ${match.symbol} | score=${match.similarity_score} | why=${reason} | ${match.summary}`;
        })
      : [copy.memory.emptySimilar]);
  const retrievalLines =
    unavailableSectionLines(
      dashboard.retrievalInspection,
      copy.memory.labels.retrievalInspection,
    ) ||
    (dashboard.retrievalInspection?.stages?.length
      ? dashboard.retrievalInspection.stages.flatMap(
          (stage: Record<string, any>) => {
            const firstWhy = stage.retrieval_explanations?.[0]?.explanation;
            const whyLine = firstWhy
              ? `${copy.memory.labels.why}: ${firstWhy.eligibility_reason || '-'} | freshness=${firstWhy.freshness || '-'} | outcome=${firstWhy.outcome_tag || '-'}`
              : `${copy.memory.labels.sample}: ${
                  stage.retrieved_memories?.[0] ||
                  stage.memory_notes?.[0] ||
                  copy.memory.labels.noRetrievalContext
                }`;
            return [
              `${stage.role} | retrieved=${stage.retrieved_memories?.length ?? 0} | why=${stage.retrieval_explanations?.length ?? 0} | trade-memory=${stage.memory_notes?.length ?? 0} | shared-bus=${stage.shared_memory_bus?.length ?? 0} | recent-runs=${stage.recent_runs?.length ?? 0}`,
              whyLine,
            ];
          },
        )
      : [copy.memory.emptyRetrieval]);

  return (
    <div className="grid grid--2">
      <Panel title={copy.memory.panels.similarPastRuns} accent="lime">
        <TextList items={memoryLines} />
      </Panel>
      <Panel title={copy.memory.panels.whyContextWasUsed} accent="cyan">
        <TextList items={retrievalLines} />
      </Panel>
    </div>
  );
}
