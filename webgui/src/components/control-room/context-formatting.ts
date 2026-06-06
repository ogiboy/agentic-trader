import { EN_CONTROL_ROOM_COPY } from './copy/en';
import type { ControlRoomCopy } from './copy/types';
import { formatList, formatNumber, formatPercent } from './formatting';
import { asRecord, asRecordArray, asString, isRecord } from './payload';
import type { DashboardData, DashboardRecord } from './types';

type PortfolioContextCopy = ControlRoomCopy['portfolio']['context'];
type ProposalContextCopy = ControlRoomCopy['proposals']['context'];
type ReviewContextCopy = ControlRoomCopy['review']['context'];
type UnavailableContextCopy = Pick<ReviewContextCopy, 'unavailable' | 'unknownError'>;

const DEFAULT_PORTFOLIO_CONTEXT_COPY = EN_CONTROL_ROOM_COPY.portfolio.context;
const DEFAULT_PROPOSAL_CONTEXT_COPY = EN_CONTROL_ROOM_COPY.proposals.context;
const DEFAULT_REVIEW_CONTEXT_COPY = EN_CONTROL_ROOM_COPY.review.context;

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
  copy: ReviewContextCopy = DEFAULT_REVIEW_CONTEXT_COPY,
): string[] {
  const tradeRecord = asRecord(record);
  if (!Object.keys(tradeRecord).length) {
    return [copy.tradeEmpty];
  }
  const consensus = asRecord(tradeRecord.consensus);
  const routedModels = Object.entries(asRecord(tradeRecord.routed_models))
    .map(([role, model]) => `${role}:${model}`)
    .join(' | ');
  return [
    `${copy.tradeId}: ${asString(tradeRecord.trade_id)}`,
    `${copy.tradeRunId}: ${asString(tradeRecord.run_id)}`,
    `${copy.tradeConsensus}: ${asString(consensus.alignment_level)}`,
    `${copy.tradeManagerRationale}: ${asString(tradeRecord.manager_rationale)}`,
    `${copy.tradeExecutionRationale}: ${asString(tradeRecord.execution_rationale)}`,
    `${copy.tradeExecutionBackend}: ${asString(tradeRecord.execution_backend)}`,
    `${copy.tradeExecutionAdapter}: ${asString(tradeRecord.execution_adapter)}`,
    `${copy.tradeExecutionOutcome}: ${asString(tradeRecord.execution_outcome_status)}`,
    `${copy.tradeRejectionReason}: ${asString(tradeRecord.execution_rejection_reason)}`,
    `${copy.tradeReviewSummary}: ${asString(tradeRecord.review_summary)}`,
    `${copy.tradeRoutedModels}: ${routedModels || '-'}`,
  ];
}

function proposalSizeLabel(
  proposal: DashboardRecord,
  copy: ProposalContextCopy,
): string {
  if (typeof proposal.quantity === 'number') {
    return `${copy.quantity} ${formatNumber(proposal.quantity, 4)}`;
  }
  if (typeof proposal.notional === 'number') {
    return `$${formatNumber(proposal.notional, 2)}`;
  }
  return '-';
}

export function proposalHeadline(proposal: unknown): string {
  return proposalHeadlineWithCopy(proposal, DEFAULT_PROPOSAL_CONTEXT_COPY);
}

export function proposalHeadlineWithCopy(
  proposal: unknown,
  copy: ProposalContextCopy,
): string {
  const proposalRecord = asRecord(proposal);
  return `${asString(proposalRecord.symbol)} ${asString(proposalRecord.side).toUpperCase()} | ${asString(proposalRecord.status)} | ${proposalSizeLabel(proposalRecord, copy)}`;
}

export function proposalLines(
  dashboard: DashboardData,
  copy: ProposalContextCopy = DEFAULT_PROPOSAL_CONTEXT_COPY,
): string[] {
  const payload = asRecord(dashboard.tradeProposals);
  if (payload?.available === false) {
    return [`${copy.unavailable}: ${asString(payload.error, copy.unknownError)}`];
  }
  const proposals = asRecordArray(payload.proposals);
  if (!proposals.length) {
    return [copy.empty];
  }
  return proposals.map(
    (proposal) =>
      `${asString(proposal.proposal_id)} | ${proposalHeadlineWithCopy(proposal, copy)} | ${copy.confidence}=${formatNumber(proposal.confidence, 2)} | ${copy.source}=${asString(proposal.source)}`,
  );
}

export function positionPlanCoverageLines(
  dashboard: DashboardData,
  copy: PortfolioContextCopy = DEFAULT_PORTFOLIO_CONTEXT_COPY,
): string[] {
  const financeOps = asRecord(dashboard.financeOps);
  const coverageSource = isRecord(financeOps.positionPlanCoverage)
    ? financeOps.positionPlanCoverage
    : dashboard.positionPlanCoverage;
  if (!isRecord(coverageSource)) {
    return [copy.positionPlanEmpty];
  }
  const coverage = coverageSource;
  if (coverage.available === false) {
    return [
      `${copy.positionPlanUnavailable}: ${asString(coverage.error, copy.unknownError)}`,
    ];
  }
  return [
    `${copy.positionPlanOpenPositions}: ${formatList(coverage.open_symbols)}`,
    `${copy.positionPlanExitPlans}: ${formatList(coverage.planned_symbols)}`,
    `${copy.positionPlanMissingPlans}: ${formatList(coverage.missing_symbols)}`,
    `${copy.positionPlanCoverage}: ${formatPercent(coverage.coverage_ratio)}`,
  ];
}

export function proposalApprovalBlockedReason(
  dashboard: DashboardData,
  copy: ProposalContextCopy = DEFAULT_PROPOSAL_CONTEXT_COPY,
): string {
  const broker = asRecord(dashboard.broker);
  if (broker.kill_switch_active) {
    return copy.killSwitchActive;
  }
  if (broker.live_requested || broker.live) {
    return copy.liveBackendBlocked;
  }
  if (broker.state === 'blocked') {
    return asString(
      broker.message,
      copy.brokerStateBlocked,
    );
  }
  return '';
}

export function canonicalLines(
  snapshot: unknown,
  copy: ReviewContextCopy = DEFAULT_REVIEW_CONTEXT_COPY,
): string[] {
  const snapshotRecord = asRecord(snapshot);
  if (!Object.keys(snapshotRecord).length) {
    return [copy.canonicalEmpty];
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
    `${copy.canonicalSummary}: ${asString(snapshotRecord.summary)}`,
    `${copy.canonicalCompleteness}: ${asString(snapshotRecord.completeness_score)}`,
    `${copy.canonicalMissingSections}: ${formatList(snapshotRecord.missing_sections)}`,
    `${copy.canonicalMarketSource}: ${asString(marketAttribution.source_name)}`,
    `${copy.canonicalFundamentalSource}: ${asString(fundamentalAttribution.source_name)}`,
    `${copy.canonicalMacroSource}: ${asString(macroAttribution.source_name)}`,
    `${copy.canonicalNewsEvents}: ${Array.isArray(snapshotRecord.news_events) ? snapshotRecord.news_events.length : 0}`,
    `${copy.canonicalDisclosures}: ${Array.isArray(snapshotRecord.disclosures) ? snapshotRecord.disclosures.length : 0}`,
    ...sources.map((source) => `${copy.canonicalSource}: ${source}`),
  ];
}

export function marketContextLines(
  pack: unknown,
  copy: ReviewContextCopy = DEFAULT_REVIEW_CONTEXT_COPY,
): string[] {
  const contextPack = asRecord(pack);
  if (!Object.keys(contextPack).length) {
    return [copy.marketEmpty];
  }
  const horizons = asRecordArray(contextPack.horizons)
    .slice(0, 4)
    .map(
      (item) =>
        `${asString(item.horizon_bars)} ${copy.marketHorizon} | ${asString(item.trend_vote)} | ${copy.marketReturn}=${asString(item.return_pct)} | ${copy.marketDrawdown}=${asString(item.max_drawdown_pct)}`,
    );
  return [
    `${copy.marketSummary}: ${asString(contextPack.summary)}`,
    `${copy.marketLookbackInterval}: ${asString(contextPack.lookback)} | ${copy.marketInterval}: ${asString(contextPack.interval)}`,
    `${copy.marketWindow}: ${asString(contextPack.window_start)} -> ${asString(contextPack.window_end)}`,
    `${copy.marketCoverage}: ${asString(contextPack.bars_analyzed)} / ${asString(contextPack.bars_expected)} (${asString(contextPack.coverage_ratio)})`,
    `${copy.marketQuality}: ${formatList(contextPack.data_quality_flags)}`,
    `${copy.marketAnomalies}: ${formatList(contextPack.anomaly_flags)}`,
    ...horizons,
  ];
}

export function unavailableSectionLines(
  section: unknown,
  label: string,
  copy: UnavailableContextCopy = DEFAULT_REVIEW_CONTEXT_COPY,
): null | string[] {
  const sectionRecord = asRecord(section);
  if (sectionRecord.available === false) {
    return [
      `${label} ${copy.unavailable}: ${asString(
        sectionRecord.error,
        copy.unknownError,
      )}`,
    ];
  }
  return null;
}
