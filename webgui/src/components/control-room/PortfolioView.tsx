import { useTranslations } from 'next-intl';

import type { DashboardData } from '../control-room.helpers';
import
  {
    accountCurrency,
    asRecord,
    asRecordArray,
    asString,
    formatList,
    formatNumber,
    formatPercent,
    formatTimestamp,
    positionPlanCoverageLines,
    unavailableSectionLines,
  } from '../control-room.helpers';
import { usePortfolioContextCopy } from './intl-copy';
import { JsonPreview, KeyValueList, Panel, TextList } from './Primitives';

/**
 * Render the Portfolio tab panels showing portfolio metrics, risk report, trade journal, exit plan coverage, preferences, and desk accounting notes.
 *
 * @param dashboard - Dashboard payload used to populate portfolio, risk, journal, preferences, and accounting displays
 * @returns A React element containing the portfolio-related panels and their contents
 */
export function PortfolioView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const t = useTranslations('controlRoom.portfolio');
  const contextCopy = usePortfolioContextCopy();
  const currency = accountCurrency(dashboard);
  const financeOps = asRecord(dashboard.financeOps);
  const portfolio = asRecord(dashboard.portfolio);
  const accounting = asRecord(financeOps.accounting || portfolio.accounting);
  const snapshot = asRecord(portfolio.snapshot);
  const riskReport = asRecord(dashboard.riskReport);
  const riskReportRecord = asRecord(riskReport.report);
  const journal = asRecord(dashboard.journal);
  const journalEntries = asRecordArray(journal.entries);
  const preferences = asRecord(dashboard.preferences);
  const costModel = asRecord(accounting.cost_model);
  const portfolioUnavailable = unavailableSectionLines(
    portfolio,
    t('unavailable.portfolio'),
    contextCopy,
  );
  const riskUnavailable = unavailableSectionLines(
    riskReport,
    t('unavailable.riskReport'),
    contextCopy,
  );
  const journalLines =
    unavailableSectionLines(
      journal,
      t('unavailable.tradeJournal'),
      contextCopy,
    ) ||
    (journalEntries.length
      ? journalEntries.map(
          (entry) =>
            `${formatTimestamp(entry.opened_at)} | ${asString(entry.symbol)} | ${asString(entry.journal_status)} | ${asString(entry.planned_side)} | ${asString(entry.realized_pnl)}`,
        )
      : [t('emptyTradeJournal')]);

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.portfolio')} accent='lime'>
        {portfolioUnavailable ? (
          <TextList items={portfolioUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `${t('fields.cash')} (${currency})`,
                  formatNumber(snapshot.cash),
                ],
                [
                  `${t('fields.marketValue')} (${currency})`,
                  formatNumber(snapshot.market_value),
                ],
                [
                  `${t('fields.equity')} (${currency})`,
                  formatNumber(snapshot.equity),
                ],
                [
                  `${t('fields.realizedPnl')} (${currency})`,
                  formatNumber(snapshot.realized_pnl),
                ],
                [
                  `${t('fields.unrealizedPnl')} (${currency}, ${t('fields.paperMark')})`,
                  formatNumber(snapshot.unrealized_pnl),
                ],
                [
                  t('fields.openPositions'),
                  asString(snapshot.open_positions),
                ],
                [
                  t('fields.markedAt'),
                  formatTimestamp(accounting?.mark_created_at),
                ],
                [
                  t('fields.markSource'),
                  asString(accounting.mark_source),
                ],
              ]}
            />
            <JsonPreview value={portfolio.positions || []} />
          </>
        )}
      </Panel>
      <Panel title={t('panels.riskReport')} accent='rose'>
        {riskUnavailable ? (
          <TextList items={riskUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `${t('fields.equity')} (${currency})`,
                  formatNumber(riskReportRecord.equity),
                ],
                [
                  t('fields.grossExposure'),
                  formatPercent(riskReportRecord.gross_exposure_pct),
                ],
                [
                  t('fields.largestPosition'),
                  formatPercent(riskReportRecord.largest_position_pct),
                ],
                [
                  t('fields.drawdown'),
                  formatPercent(riskReportRecord.drawdown_from_peak_pct),
                ],
                [
                  t('fields.warnings'),
                  String(
                    Array.isArray(riskReportRecord.warnings)
                      ? riskReportRecord.warnings.length
                      : 0,
                  ),
                ],
                [
                  t('fields.generatedAt'),
                  formatTimestamp(riskReportRecord.generated_at),
                ],
              ]}
            />
            <TextList
              items={
                Array.isArray(riskReportRecord.warnings)
                  ? riskReportRecord.warnings.map((warning) =>
                      asString(warning),
                    )
                  : [t('noWarnings')]
              }
            />
          </>
        )}
      </Panel>
      <Panel title={t('panels.tradeJournal')} accent='amber'>
        <TextList items={journalLines} />
      </Panel>
      <Panel title={t('panels.exitPlanCoverage')} accent='rose'>
        <TextList items={positionPlanCoverageLines(dashboard, contextCopy)} />
      </Panel>
      <Panel title={t('panels.preferences')} accent='cyan'>
        <KeyValueList
          items={[
            [
              t('fields.regions'),
              formatList(preferences.regions),
            ],
            [
              t('fields.exchanges'),
              formatList(preferences.exchanges),
            ],
            [
              t('fields.currencies'),
              formatList(preferences.currencies),
            ],
            [
              t('fields.risk'),
              asString(preferences.risk_profile),
            ],
            [
              t('fields.style'),
              asString(preferences.trade_style),
            ],
            [
              t('fields.behavior'),
              asString(preferences.behavior_preset),
            ],
            [
              t('fields.tone'),
              asString(preferences.agent_tone),
            ],
            [
              t('fields.strictness'),
              asString(preferences.strictness_preset),
            ],
          ]}
        />
      </Panel>
      <Panel title={t('panels.deskAccountingNotes')} accent='amber'>
        <KeyValueList
          items={[
            [t('fields.currency'), currency],
            [
              t('fields.markStatus'),
              asString(accounting.mark_status, 'mark_time_unavailable'),
            ],
            [
              t('fields.deskFees'),
              asString(costModel.fees),
            ],
            [
              t('fields.slippage'),
              costModel.slippage_bps == null
                ? '-'
                : `${asString(costModel.slippage_bps)} ${t('fields.basisPoints')}`,
            ],
            [
              t('fields.rejectionEvidence'),
              asString(accounting.rejection_evidence),
            ],
          ]}
        />
      </Panel>
    </div>
  );
}
