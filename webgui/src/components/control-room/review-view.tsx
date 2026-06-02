import type { DashboardData } from '../control-room.helpers';
import
  {
    asRecord,
    asString,
    canonicalLines,
    formatTimestamp,
    marketContextLines,
    tradeContextLines,
    unavailableSectionLines,
  } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { Panel, TextList } from './primitives';

export function ReviewView({
  copy,
  dashboard,
}: Readonly<{ copy: ControlRoomCopy; dashboard: DashboardData }>) {
  const review = asRecord(dashboard.review);
  const reviewRecord = asRecord(review.record);
  const artifacts = asRecord(reviewRecord.artifacts);
  const coordinator = asRecord(artifacts.coordinator);
  const consensus = asRecord(artifacts.consensus);
  const reviewArtifact = asRecord(artifacts.review);
  const tradeContext = asRecord(dashboard.tradeContext);
  const canonicalAnalysis = asRecord(dashboard.canonicalAnalysis);
  const marketContext = asRecord(dashboard.marketContext);
  const reviewLines =
    unavailableSectionLines(
      review,
      copy.review.unavailable.latestReview,
    ) ||
    (Object.keys(reviewRecord).length
      ? [
          `${copy.review.fields.runId}: ${asString(reviewRecord.run_id)}`,
          `${copy.review.fields.created}: ${formatTimestamp(reviewRecord.created_at)}`,
          `${copy.review.fields.symbol}: ${asString(reviewRecord.symbol)}`,
          `${copy.review.fields.approved}: ${asString(reviewRecord.approved)}`,
          `${copy.review.fields.coordinatorFocus}: ${asString(coordinator.market_focus)}`,
          `${copy.review.fields.consensus}: ${asString(consensus.alignment_level)}`,
          `${copy.review.fields.reviewSummary}: ${asString(reviewArtifact.summary)}`,
        ]
      : [copy.review.emptyPersistedRuns]);

  return (
    <div className='grid grid--2'>
      <Panel title={copy.review.panels.latestReview} accent='lime'>
        <TextList items={reviewLines} />
      </Panel>
      <Panel title={copy.review.panels.tradeContext} accent='cyan'>
        <TextList items={tradeContextLines(tradeContext.record)} />
      </Panel>
      <Panel title={copy.review.panels.canonicalAnalysis} accent='amber'>
        <TextList items={canonicalLines(canonicalAnalysis.snapshot)} />
      </Panel>
      <Panel title={copy.review.panels.marketContextPack} accent='rose'>
        <TextList items={marketContextLines(marketContext.contextPack)} />
      </Panel>
    </div>
  );
}
