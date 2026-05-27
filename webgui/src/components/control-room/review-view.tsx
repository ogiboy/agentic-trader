import type { DashboardData } from '../control-room.helpers';
import {
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
  const reviewLines =
    unavailableSectionLines(
      dashboard.review,
      copy.review.unavailable.latestReview,
    ) ||
    (dashboard.review?.record
      ? [
          `${copy.review.fields.runId}: ${dashboard.review.record.run_id}`,
          `${copy.review.fields.created}: ${formatTimestamp(dashboard.review.record.created_at)}`,
          `${copy.review.fields.symbol}: ${dashboard.review.record.symbol}`,
          `${copy.review.fields.approved}: ${dashboard.review.record.approved}`,
          `${copy.review.fields.coordinatorFocus}: ${dashboard.review.record.artifacts?.coordinator?.market_focus ?? '-'}`,
          `${copy.review.fields.consensus}: ${dashboard.review.record.artifacts?.consensus?.alignment_level ?? '-'}`,
          `${copy.review.fields.reviewSummary}: ${dashboard.review.record.artifacts?.review?.summary ?? '-'}`,
        ]
      : [copy.review.emptyPersistedRuns]);

  return (
    <div className='grid grid--2'>
      <Panel title={copy.review.panels.latestReview} accent='lime'>
        <TextList items={reviewLines} />
      </Panel>
      <Panel title={copy.review.panels.tradeContext} accent='cyan'>
        <TextList items={tradeContextLines(dashboard.tradeContext?.record)} />
      </Panel>
      <Panel title={copy.review.panels.canonicalAnalysis} accent='amber'>
        <TextList
          items={canonicalLines(dashboard.canonicalAnalysis?.snapshot)}
        />
      </Panel>
      <Panel title={copy.review.panels.marketContextPack} accent='rose'>
        <TextList
          items={marketContextLines(dashboard.marketContext?.contextPack)}
        />
      </Panel>
    </div>
  );
}
