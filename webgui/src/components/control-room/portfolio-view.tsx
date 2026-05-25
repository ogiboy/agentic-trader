import type { DashboardData } from '../control-room.helpers';
import {
  accountCurrency,
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
  const accounting =
    dashboard.financeOps?.accounting ?? dashboard.portfolio?.accounting ?? {};
  const portfolioUnavailable = unavailableSectionLines(
    dashboard.portfolio,
    copy.portfolio.unavailable.portfolio,
  );
  const riskUnavailable = unavailableSectionLines(
    dashboard.riskReport,
    copy.portfolio.unavailable.riskReport,
  );
  const journalLines =
    unavailableSectionLines(
      dashboard.journal,
      copy.portfolio.unavailable.tradeJournal,
    ) ||
    (dashboard.journal?.entries?.length
      ? dashboard.journal.entries.map(
          (entry: DashboardData) =>
            `${formatTimestamp(entry.opened_at)} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`,
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
                  formatNumber(dashboard.portfolio?.snapshot?.cash),
                ],
                [
                  `${copy.portfolio.fields.marketValue} (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.market_value),
                ],
                [
                  `${copy.portfolio.fields.equity} (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.equity),
                ],
                [
                  `${copy.portfolio.fields.realizedPnl} (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.realized_pnl),
                ],
                [
                  `${copy.portfolio.fields.unrealizedPnl} (${currency}, ${copy.portfolio.fields.paperMark})`,
                  formatNumber(dashboard.portfolio?.snapshot?.unrealized_pnl),
                ],
                [
                  copy.portfolio.fields.openPositions,
                  String(dashboard.portfolio?.snapshot?.open_positions ?? '-'),
                ],
                [
                  copy.portfolio.fields.markedAt,
                  formatTimestamp(accounting?.mark_created_at),
                ],
                [
                  copy.portfolio.fields.markSource,
                  accounting?.mark_source ?? '-',
                ],
              ]}
            />
            <JsonPreview value={dashboard.portfolio?.positions || []} />
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
                  formatNumber(dashboard.riskReport?.report?.equity),
                ],
                [
                  copy.portfolio.fields.grossExposure,
                  formatPercent(
                    dashboard.riskReport?.report?.gross_exposure_pct,
                  ),
                ],
                [
                  copy.portfolio.fields.largestPosition,
                  formatPercent(
                    dashboard.riskReport?.report?.largest_position_pct,
                  ),
                ],
                [
                  copy.portfolio.fields.drawdown,
                  formatPercent(
                    dashboard.riskReport?.report?.drawdown_from_peak_pct,
                  ),
                ],
                [
                  copy.portfolio.fields.warnings,
                  String((dashboard.riskReport?.report?.warnings || []).length),
                ],
                [
                  copy.portfolio.fields.generatedAt,
                  formatTimestamp(dashboard.riskReport?.report?.generated_at),
                ],
              ]}
            />
            <TextList
              items={
                dashboard.riskReport?.report?.warnings || [
                  copy.portfolio.noWarnings,
                ]
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
              formatList(dashboard.preferences?.regions),
            ],
            [
              copy.portfolio.fields.exchanges,
              formatList(dashboard.preferences?.exchanges),
            ],
            [
              copy.portfolio.fields.currencies,
              formatList(dashboard.preferences?.currencies),
            ],
            [
              copy.portfolio.fields.risk,
              dashboard.preferences?.risk_profile ?? '-',
            ],
            [
              copy.portfolio.fields.style,
              dashboard.preferences?.trade_style ?? '-',
            ],
            [
              copy.portfolio.fields.behavior,
              dashboard.preferences?.behavior_preset ?? '-',
            ],
            [
              copy.portfolio.fields.tone,
              dashboard.preferences?.agent_tone ?? '-',
            ],
            [
              copy.portfolio.fields.strictness,
              dashboard.preferences?.strictness_preset ?? '-',
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
              accounting.mark_status ?? 'mark_time_unavailable',
            ],
            [
              copy.portfolio.fields.deskFees,
              accounting.cost_model?.fees ?? '-',
            ],
            [
              copy.portfolio.fields.slippage,
              accounting.cost_model?.slippage_bps == null
                ? '-'
                : `${accounting.cost_model.slippage_bps} ${copy.portfolio.fields.basisPoints}`,
            ],
            [
              copy.portfolio.fields.rejectionEvidence,
              accounting.rejection_evidence ?? '-',
            ],
          ]}
        />
      </Panel>
    </div>
  );
}
