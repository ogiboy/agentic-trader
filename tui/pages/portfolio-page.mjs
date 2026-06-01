import { Box } from 'ink';
import React from 'react';
import { accountCurrency } from '../dashboard-defaults.mjs';
import {
  getJournalLines,
  renderLinesFallback,
} from '../line-formatters.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Portfolio page panels for the dashboard UI.
 *
 * Renders four panels—PORTFOLIO, RISK REPORT, TRADE JOURNAL, and PREFERENCES—arranged in two rows,
 * using available snapshot/report/journal/preference data or graceful fallback messages when unavailable.
 *
 * @param {object} props
 * @param {object} props.data - Dashboard data bag containing keys used to populate the page:
 *   `portfolio` (with `snapshot` and `positions`), `riskReport`, `journal`, and `preferences`.
 * @returns {import('react').ReactElement} The composed Ink/React element for the Portfolio page.
 */
function PortfolioPage({ data }) {
  const portfolio = data.portfolio;
  const riskReport = data.riskReport;
  const journal = data.journal;
  const preferences = data.preferences;
  const snapshot = portfolio.snapshot;
  const positions = portfolio.positions;
  const currency = accountCurrency(data);
  const accounting = data.financeOps?.accounting || portfolio.accounting || {};

  const portfolioLines = renderLinesFallback(
    'PORTFOLIO',
    portfolio.available,
    portfolio.error,
    'Portfolio view is temporarily unavailable.',
  ) || [
    `Cash (${currency}): ${snapshot.cash.toFixed(2)}`,
    `Market Value (${currency}): ${snapshot.market_value.toFixed(2)}`,
    `Equity (${currency}): ${snapshot.equity.toFixed(2)}`,
    `Realized PnL (${currency}): ${snapshot.realized_pnl.toFixed(2)}`,
    `Unrealized PnL (${currency}, paper mark): ${snapshot.unrealized_pnl.toFixed(2)}`,
    `Open Positions: ${positions.length}`,
    `Marked At: ${accounting.mark_created_at || 'mark time unavailable'}`,
    `Mark Source: ${accounting.mark_source || '-'}`,
    `Fees: ${accounting.cost_model?.fees || '-'}`,
    `Slippage: ${
      accounting.cost_model?.slippage_bps == null
        ? '-'
        : `${accounting.cost_model.slippage_bps} bps`
    }`,
    `Rejection Evidence: ${accounting.rejection_evidence || '-'}`,
  ];

  const riskLines =
    riskReport.available === false || !riskReport.report
      ? [
          'Risk report is temporarily unavailable.',
          riskReport.error || 'The runtime writer currently owns the database.',
        ]
      : [
          `Equity (${currency}): ${riskReport.report.equity.toFixed(2)}`,
          `Gross Exposure: ${(riskReport.report.gross_exposure_pct * 100).toFixed(2)}%`,
          `Largest Position: ${(riskReport.report.largest_position_pct * 100).toFixed(2)}%`,
          `Drawdown: ${(riskReport.report.drawdown_from_peak_pct * 100).toFixed(2)}%`,
          `Generated At: ${riskReport.report.generated_at || '-'}`,
          `Warnings: ${riskReport.report.warnings.length}`,
        ];

  const journalLines =
    journal.available === false
      ? renderLinesFallback(
          'TRADE JOURNAL',
          journal.available,
          journal.error,
          'Trade journal is temporarily unavailable.',
        ) || getJournalLines(journal)
      : getJournalLines(journal);

  const preferenceLines = renderLinesFallback(
    'PREFERENCES',
    preferences.available,
    preferences.error,
    'Preferences are temporarily unavailable.',
  ) || [
    `Regions: ${(preferences.regions || []).join(', ') || '-'}`,
    `Exchanges: ${(preferences.exchanges || []).join(', ') || '-'}`,
    `Currencies: ${(preferences.currencies || []).join(', ') || '-'}`,
    `Risk: ${preferences.risk_profile}`,
    `Style: ${preferences.trade_style}`,
    `Behavior: ${preferences.behavior_preset}`,
    `Agent Profile: ${preferences.agent_profile}`,
    `Agent Tone: ${preferences.agent_tone}`,
    `Strictness: ${preferences.strictness_preset}`,
    `Intervention: ${preferences.intervention_style}`,
  ];

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('PORTFOLIO', portfolioLines, 'yellow'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('RISK REPORT', riskLines, 'red'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('TRADE JOURNAL', journalLines.slice(0, 8), 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('PREFERENCES', preferenceLines, 'blue'),
      ),
    ),
  );
}

export { PortfolioPage };
