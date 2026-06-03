import { useTranslations } from 'next-intl';

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
import { Panel, TextList } from './Primitives';

export function ReviewView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const t = useTranslations('controlRoom.review');
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
      t('unavailable.latestReview'),
    ) ||
    (Object.keys(reviewRecord).length
      ? [
          `${t('fields.runId')}: ${asString(reviewRecord.run_id)}`,
          `${t('fields.created')}: ${formatTimestamp(reviewRecord.created_at)}`,
          `${t('fields.symbol')}: ${asString(reviewRecord.symbol)}`,
          `${t('fields.approved')}: ${asString(reviewRecord.approved)}`,
          `${t('fields.coordinatorFocus')}: ${asString(coordinator.market_focus)}`,
          `${t('fields.consensus')}: ${asString(consensus.alignment_level)}`,
          `${t('fields.reviewSummary')}: ${asString(reviewArtifact.summary)}`,
        ]
      : [t('emptyPersistedRuns')]);

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.latestReview')} accent='lime'>
        <TextList items={reviewLines} />
      </Panel>
      <Panel title={t('panels.tradeContext')} accent='cyan'>
        <TextList items={tradeContextLines(tradeContext.record)} />
      </Panel>
      <Panel title={t('panels.canonicalAnalysis')} accent='amber'>
        <TextList items={canonicalLines(canonicalAnalysis.snapshot)} />
      </Panel>
      <Panel title={t('panels.marketContextPack')} accent='rose'>
        <TextList items={marketContextLines(marketContext.contextPack)} />
      </Panel>
    </div>
  );
}
