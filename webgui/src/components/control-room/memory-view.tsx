import type { DashboardData } from '../control-room.helpers';
import
  {
    asRecord,
    asRecordArray,
    formatTimestamp,
    unavailableSectionLines,
  } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { Panel, TextList } from './primitives';

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
  const memoryExplorer = asRecord(dashboard.memoryExplorer);
  const retrievalInspection = asRecord(dashboard.retrievalInspection);
  const memoryMatches = asRecordArray(memoryExplorer.matches);
  const retrievalStages = asRecordArray(retrievalInspection.stages);
  const memoryLines =
    unavailableSectionLines(
      memoryExplorer,
      copy.memory.labels.memoryExplorer,
    ) ||
    (memoryMatches.length
      ? memoryMatches.map((match) => {
          const explanation = asRecord(match.explanation);
          const reason =
            explanation.eligibility_reason || match.retrieval_source;
          return `${formatTimestamp(match.created_at)} | ${textValue(match.symbol)} | score=${textValue(match.similarity_score)} | why=${textValue(reason)} | ${textValue(match.summary)}`;
        })
      : [copy.memory.emptySimilar]);
  const retrievalLines =
    unavailableSectionLines(
      retrievalInspection,
      copy.memory.labels.retrievalInspection,
    ) ||
    (retrievalStages.length
      ? retrievalStages.flatMap((stage) => {
            const explanations = asRecordArray(stage.retrieval_explanations);
            const firstWhy = asRecord(asRecord(explanations[0]).explanation);
            const retrievedMemories = Array.isArray(stage.retrieved_memories)
              ? stage.retrieved_memories
              : [];
            const memoryNotes = Array.isArray(stage.memory_notes)
              ? stage.memory_notes
              : [];
            const sharedBus = Array.isArray(stage.shared_memory_bus)
              ? stage.shared_memory_bus
              : [];
            const recentRuns = Array.isArray(stage.recent_runs)
              ? stage.recent_runs
              : [];
            const sample = retrievedMemories[0] ?? memoryNotes[0];
            const sampleText =
              sample == null
                ? copy.memory.labels.noRetrievalContext
                : textValue(sample);
            const whyLine = Object.keys(firstWhy).length
              ? `${copy.memory.labels.why}: ${textValue(firstWhy.eligibility_reason)} | freshness=${textValue(firstWhy.freshness)} | outcome=${textValue(firstWhy.outcome_tag)}`
              : `${copy.memory.labels.sample}: ${sampleText}`;
            return [
              `${textValue(stage.role)} | retrieved=${retrievedMemories.length} | why=${explanations.length} | trade-memory=${memoryNotes.length} | shared-bus=${sharedBus.length} | recent-runs=${recentRuns.length}`,
              whyLine,
            ];
          })
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
