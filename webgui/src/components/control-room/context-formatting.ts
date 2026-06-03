import { CONTROL_ROOM_CONTEXT_COPY } from './copy/context';
import { formatList, formatNumber, formatPercent } from './formatting';
import { asRecord, asRecordArray, asString, isRecord } from './payload';
import type { DashboardData, DashboardRecord } from './types';

export function accountCurrency(dashboard: DashboardData): string {
  const financeOps = asRecord(dashboard.financeOps);
  const financeAccounting = asRecord(financeOps.accounting);
  const portfolio = asRecord(dashboard.portfolio);
  const portfolioAccounting = asRecord(portfolio.accounting);
  const preferences = asRecord(dashboard.preferences);
  const currencies = Array.isArray(preferences.currencies)
    ? preferences.currencies
    : [];
  return (
    asString(financeAccounting.currency, '') ||
    asString(portfolioAccounting.currency, '') ||
    asString(currencies[0], '') ||
    'USD'
  );
}

export function tradeContextLines(
  record: unknown,
): string[] {
  const tradeRecord = asRecord(record);
  if (!Object.keys(tradeRecord).length) {
    return ['No persisted trade context is available yet.'];
  }
  const consensus = asRecord(tradeRecord.consensus);
  const routedModels = Object.entries(asRecord(tradeRecord.routed_models))
    .map(([role, model]) => `${role}:${model}`)
    .join(' | ');
  return [
    `Trade ID: ${asString(tradeRecord.trade_id)}`,
    `Run ID: ${asString(tradeRecord.run_id)}`,
    `Consensus: ${asString(consensus.alignment_level)}`,
    `Manager Rationale: ${asString(tradeRecord.manager_rationale)}`,
    `Execution Rationale: ${asString(tradeRecord.execution_rationale)}`,
    `Execution Backend: ${asString(tradeRecord.execution_backend)}`,
    `Execution Adapter: ${asString(tradeRecord.execution_adapter)}`,
    `Execution Outcome: ${asString(tradeRecord.execution_outcome_status)}`,
    `Rejection Reason: ${asString(tradeRecord.execution_rejection_reason)}`,
    `Review Summary: ${asString(tradeRecord.review_summary)}`,
    `Routed Models: ${routedModels || '-'}`,
  ];
}

function proposalSizeLabel(proposal: DashboardRecord): string {
  if (typeof proposal.quantity === 'number') {
    return `qty ${formatNumber(proposal.quantity, 4)}`;
  }
  if (typeof proposal.notional === 'number') {
    return `$${formatNumber(proposal.notional, 2)}`;
  }
  return '-';
}

export function proposalHeadline(proposal: unknown): string {
  const proposalRecord = asRecord(proposal);
  return `${asString(proposalRecord.symbol)} ${asString(proposalRecord.side).toUpperCase()} | ${asString(proposalRecord.status)} | ${proposalSizeLabel(proposalRecord)}`;
}

export function proposalLines(dashboard: DashboardData): string[] {
  const payload = asRecord(dashboard.tradeProposals);
  if (payload?.available === false) {
    return [`Proposal desk unavailable: ${asString(payload.error, 'Unknown error.')}`];
  }
  const proposals = asRecordArray(payload.proposals);
  if (!proposals.length) {
    return ['No manual-review proposals are queued yet.'];
  }
  return proposals.map(
    (proposal) =>
      `${asString(proposal.proposal_id)} | ${proposalHeadline(proposal)} | confidence=${formatNumber(proposal.confidence, 2)} | source=${asString(proposal.source)}`,
  );
}

export function positionPlanCoverageLines(dashboard: DashboardData): string[] {
  const financeOps = asRecord(dashboard.financeOps);
  const coverageSource = isRecord(financeOps.positionPlanCoverage)
    ? financeOps.positionPlanCoverage
    : dashboard.positionPlanCoverage;
  if (!isRecord(coverageSource)) {
    return ['No position plan coverage snapshot is available yet.'];
  }
  const coverage = coverageSource;
  if (coverage.available === false) {
    return [
      `Position plan coverage unavailable: ${asString(coverage.error, 'Unknown error.')}`,
    ];
  }
  return [
    `Open Positions: ${formatList(coverage.open_symbols)}`,
    `Exit Plans: ${formatList(coverage.planned_symbols)}`,
    `Missing Plans: ${formatList(coverage.missing_symbols)}`,
    `Coverage: ${formatPercent(coverage.coverage_ratio)}`,
  ];
}

export function proposalApprovalBlockedReason(
  dashboard: DashboardData,
): string {
  const broker = asRecord(dashboard.broker);
  if (broker.kill_switch_active) {
    return 'Execution kill switch is active.';
  }
  if (broker.live_requested || broker.live) {
    return 'Live backend is not proposal-approval ready in V1.';
  }
  if (broker.state === 'blocked') {
    return asString(
      broker.message,
      CONTROL_ROOM_CONTEXT_COPY.brokerStateBlocked,
    );
  }
  return '';
}

export function canonicalLines(
  snapshot: unknown,
): string[] {
  const snapshotRecord = asRecord(snapshot);
  if (!Object.keys(snapshotRecord).length) {
    return ['No canonical analysis snapshot is available yet.'];
  }
  const market = asRecord(snapshotRecord.market);
  const fundamental = asRecord(snapshotRecord.fundamental);
  const macro = asRecord(snapshotRecord.macro);
  const marketAttribution = asRecord(market.attribution);
  const fundamentalAttribution = asRecord(fundamental.attribution);
  const macroAttribution = asRecord(macro.attribution);
  const sources = asRecordArray(snapshotRecord.source_attributions)
    .slice(0, 6)
    .map(
      (source) =>
        `${asString(source.provider_type)}:${asString(source.source_name)} (${asString(source.source_role)}, ${asString(source.freshness)})`,
    );
  return [
    `Summary: ${asString(snapshotRecord.summary)}`,
    `Completeness: ${asString(snapshotRecord.completeness_score)}`,
    `Missing Sections: ${formatList(snapshotRecord.missing_sections)}`,
    `Market Source: ${asString(marketAttribution.source_name)}`,
    `Fundamental Source: ${asString(fundamentalAttribution.source_name)}`,
    `Macro Source: ${asString(macroAttribution.source_name)}`,
    `News Events: ${Array.isArray(snapshotRecord.news_events) ? snapshotRecord.news_events.length : 0}`,
    `Disclosures: ${Array.isArray(snapshotRecord.disclosures) ? snapshotRecord.disclosures.length : 0}`,
    ...sources.map((source) => `Source: ${source}`),
  ];
}

export function marketContextLines(
  pack: unknown,
): string[] {
  const contextPack = asRecord(pack);
  if (!Object.keys(contextPack).length) {
    return ['No persisted market context pack is available yet.'];
  }
  const horizons = asRecordArray(contextPack.horizons)
    .slice(0, 4)
    .map(
      (item) =>
        `${asString(item.horizon_bars)} bars | ${asString(item.trend_vote)} | return=${asString(item.return_pct)} | drawdown=${asString(item.max_drawdown_pct)}`,
    );
  return [
    `Summary: ${asString(contextPack.summary)}`,
    `Lookback: ${asString(contextPack.lookback)} | Interval: ${asString(contextPack.interval)}`,
    `Window: ${asString(contextPack.window_start)} -> ${asString(contextPack.window_end)}`,
    `Coverage: ${asString(contextPack.bars_analyzed)} / ${asString(contextPack.bars_expected)} (${asString(contextPack.coverage_ratio)})`,
    `Quality: ${formatList(contextPack.data_quality_flags)}`,
    `Anomalies: ${formatList(contextPack.anomaly_flags)}`,
    ...horizons,
  ];
}

export function unavailableSectionLines(
  section: unknown,
  label: string,
): null | string[] {
  const sectionRecord = asRecord(section);
  if (sectionRecord.available === false) {
    return [
      `${label} unavailable: ${asString(
        sectionRecord.error,
        CONTROL_ROOM_CONTEXT_COPY.unknownError,
      )}`,
    ];
  }
  return null;
}
