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
import type { ControlRoomCopy } from './labels';
import { JsonPreview, KeyValueList, Panel, TextList } from './primitives';

/**
 * Render the Portfolio tab panels showing portfolio metrics, risk report, trade journal, exit plan coverage, preferences, and desk accounting notes.
 *
 * @param dashboard - Dashboard payload used to populate portfolio, risk, journal, preferences, and accounting displays
 * @returns A React element containing the portfolio-related panels and their contents
 */
export function PortfolioView({
  copy,
  dashboard,
}: Readonly<{ copy: ControlRoomCopy; dashboard: DashboardData }>) {
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
    copy.portfolio.unavailable.portfolio,
  );
  const riskUnavailable = unavailableSectionLines(
    riskReport,
    copy.portfolio.unavailable.riskReport,
  );
  const journalLines =
    unavailableSectionLines(
      journal,
      copy.portfolio.unavailable.tradeJournal,
    ) ||
    (journalEntries.length
      ? journalEntries.map(
          (entry) =>
            `${formatTimestamp(entry.opened_at)} | ${asString(entry.symbol)} | ${asString(entry.journal_status)} | ${asString(entry.planned_side)} | ${asString(entry.realized_pnl)}`,
        )
      : [copy.portfolio.emptyTradeJournal]);

  return (
    <div className='grid grid--2'>
      <Panel title={copy.portfolio.panels.portfolio} accent='lime'>
        {portfolioUnavailable ? (
          <TextList items={portfolioUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `${copy.portfolio.fields.cash} (${currency})`,
                  formatNumber(snapshot.cash),
                ],
                [
                  `${copy.portfolio.fields.marketValue} (${currency})`,
                  formatNumber(snapshot.market_value),
                ],
                [
                  `${copy.portfolio.fields.equity} (${currency})`,
                  formatNumber(snapshot.equity),
                ],
                [
                  `${copy.portfolio.fields.realizedPnl} (${currency})`,
                  formatNumber(snapshot.realized_pnl),
                ],
                [
                  `${copy.portfolio.fields.unrealizedPnl} (${currency}, ${copy.portfolio.fields.paperMark})`,
                  formatNumber(snapshot.unrealized_pnl),
                ],
                [
                  copy.portfolio.fields.openPositions,
                  asString(snapshot.open_positions),
                ],
                [
                  copy.portfolio.fields.markedAt,
                  formatTimestamp(accounting?.mark_created_at),
                ],
                [
                  copy.portfolio.fields.markSource,
                  asString(accounting.mark_source),
                ],
              ]}
            />
            <JsonPreview value={portfolio.positions || []} />
          </>
        )}
      </Panel>
      <Panel title={copy.portfolio.panels.riskReport} accent='rose'>
        {riskUnavailable ? (
          <TextList items={riskUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `${copy.portfolio.fields.equity} (${currency})`,
                  formatNumber(riskReportRecord.equity),
                ],
                [
                  copy.portfolio.fields.grossExposure,
                  formatPercent(riskReportRecord.gross_exposure_pct),
                ],
                [
                  copy.portfolio.fields.largestPosition,
                  formatPercent(riskReportRecord.largest_position_pct),
                ],
                [
                  copy.portfolio.fields.drawdown,
                  formatPercent(riskReportRecord.drawdown_from_peak_pct),
                ],
                [
                  copy.portfolio.fields.warnings,
                  String(
                    Array.isArray(riskReportRecord.warnings)
                      ? riskReportRecord.warnings.length
                      : 0,
                  ),
                ],
                [
                  copy.portfolio.fields.generatedAt,
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
                  : [copy.portfolio.noWarnings]
              }
            />
          </>
        )}
      </Panel>
      <Panel title={copy.portfolio.panels.tradeJournal} accent='amber'>
        <TextList items={journalLines} />
      </Panel>
      <Panel title={copy.portfolio.panels.exitPlanCoverage} accent='rose'>
        <TextList items={positionPlanCoverageLines(dashboard)} />
      </Panel>
      <Panel title={copy.portfolio.panels.preferences} accent='cyan'>
        <KeyValueList
          items={[
            [
              copy.portfolio.fields.regions,
              formatList(preferences.regions),
            ],
            [
              copy.portfolio.fields.exchanges,
              formatList(preferences.exchanges),
            ],
            [
              copy.portfolio.fields.currencies,
              formatList(preferences.currencies),
            ],
            [
              copy.portfolio.fields.risk,
              asString(preferences.risk_profile),
            ],
            [
              copy.portfolio.fields.style,
              asString(preferences.trade_style),
            ],
            [
              copy.portfolio.fields.behavior,
              asString(preferences.behavior_preset),
            ],
            [
              copy.portfolio.fields.tone,
              asString(preferences.agent_tone),
            ],
            [
              copy.portfolio.fields.strictness,
              asString(preferences.strictness_preset),
            ],
          ]}
        />
      </Panel>
      <Panel title={copy.portfolio.panels.deskAccountingNotes} accent='amber'>
        <KeyValueList
          items={[
            [copy.portfolio.fields.currency, currency],
            [
              copy.portfolio.fields.markStatus,
              asString(accounting.mark_status, 'mark_time_unavailable'),
            ],
            [
              copy.portfolio.fields.deskFees,
              asString(costModel.fees),
            ],
            [
              copy.portfolio.fields.slippage,
              costModel.slippage_bps == null
                ? '-'
                : `${asString(costModel.slippage_bps)} ${copy.portfolio.fields.basisPoints}`,
            ],
            [
              copy.portfolio.fields.rejectionEvidence,
              asString(accounting.rejection_evidence),
            ],
          ]}
        />
      </Panel>
    </div>
  );
}
