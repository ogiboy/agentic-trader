/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard context payloads are schema-loose JSON today */
import type { DashboardData } from '../control-room.helpers';
import { formatList, formatNumber, formatPercent } from './formatting';

export function accountCurrency(dashboard: DashboardData): string {
  return (
    dashboard.financeOps?.accounting?.currency ||
    dashboard.portfolio?.accounting?.currency ||
    dashboard.preferences?.currencies?.[0] ||
    'USD'
  );
}

export function tradeContextLines(
  record: Record<string, any> | null | undefined,
): string[] {
  if (!record) {
    return ['No persisted trade context is available yet.'];
  }
  const routedModels = Object.entries(record.routed_models || {})
    .map(([role, model]) => `${role}:${model}`)
    .join(' | ');
  return [
    `Trade ID: ${record.trade_id ?? '-'}`,
    `Run ID: ${record.run_id ?? '-'}`,
    `Consensus: ${record.consensus?.alignment_level ?? '-'}`,
    `Manager Rationale: ${record.manager_rationale ?? '-'}`,
    `Execution Rationale: ${record.execution_rationale ?? '-'}`,
    `Execution Backend: ${record.execution_backend ?? '-'}`,
    `Execution Adapter: ${record.execution_adapter ?? '-'}`,
    `Execution Outcome: ${record.execution_outcome_status ?? '-'}`,
    `Rejection Reason: ${record.execution_rejection_reason ?? '-'}`,
    `Review Summary: ${record.review_summary ?? '-'}`,
    `Routed Models: ${routedModels || '-'}`,
  ];
}

function proposalSizeLabel(proposal: Record<string, any>): string {
  if (typeof proposal.quantity === 'number') {
    return `qty ${formatNumber(proposal.quantity, 4)}`;
  }
  if (typeof proposal.notional === 'number') {
    return `$${formatNumber(proposal.notional, 2)}`;
  }
  return '-';
}

export function proposalHeadline(proposal: Record<string, any>): string {
  return `${proposal.symbol ?? '-'} ${String(proposal.side ?? '-').toUpperCase()} | ${proposal.status ?? '-'} | ${proposalSizeLabel(proposal)}`;
}

export function proposalLines(dashboard: DashboardData): string[] {
  const payload = dashboard.tradeProposals;
  if (payload?.available === false) {
    return [`Proposal desk unavailable: ${payload.error || 'Unknown error.'}`];
  }
  const proposals = Array.isArray(payload?.proposals) ? payload.proposals : [];
  if (!proposals.length) {
    return ['No manual-review proposals are queued yet.'];
  }
  return proposals.map(
    (proposal: Record<string, any>) =>
      `${proposal.proposal_id ?? '-'} | ${proposalHeadline(proposal)} | confidence=${formatNumber(proposal.confidence, 2)} | source=${proposal.source ?? '-'}`,
  );
}

export function positionPlanCoverageLines(dashboard: DashboardData): string[] {
  const coverage =
    dashboard.financeOps?.positionPlanCoverage ||
    dashboard.positionPlanCoverage;
  if (!coverage) {
    return ['No position plan coverage snapshot is available yet.'];
  }
  if (coverage.available === false) {
    return [
      `Position plan coverage unavailable: ${coverage.error || 'Unknown error.'}`,
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
  const broker = dashboard.broker || {};
  if (broker.kill_switch_active) {
    return 'Execution kill switch is active.';
  }
  if (broker.live_requested || broker.live) {
    return 'Live backend is not proposal-approval ready in V1.';
  }
  if (broker.state === 'blocked') {
    return broker.message || 'Broker state is blocked.';
  }
  return '';
}

export function canonicalLines(
  snapshot: Record<string, any> | null | undefined,
): string[] {
  if (!snapshot) {
    return ['No canonical analysis snapshot is available yet.'];
  }
  const sources = (snapshot.source_attributions || [])
    .slice(0, 6)
    .map(
      (source: Record<string, any>) =>
        `${source.provider_type}:${source.source_name} (${source.source_role}, ${source.freshness})`,
    );
  return [
    `Summary: ${snapshot.summary || '-'}`,
    `Completeness: ${snapshot.completeness_score ?? '-'}`,
    `Missing Sections: ${formatList(snapshot.missing_sections)}`,
    `Market Source: ${snapshot.market?.attribution?.source_name ?? '-'}`,
    `Fundamental Source: ${snapshot.fundamental?.attribution?.source_name ?? '-'}`,
    `Macro Source: ${snapshot.macro?.attribution?.source_name ?? '-'}`,
    `News Events: ${(snapshot.news_events || []).length}`,
    `Disclosures: ${(snapshot.disclosures || []).length}`,
    ...sources.map((source: string) => `Source: ${source}`),
  ];
}

export function marketContextLines(
  pack: Record<string, any> | null | undefined,
): string[] {
  if (!pack) {
    return ['No persisted market context pack is available yet.'];
  }
  const horizons = (pack.horizons || [])
    .slice(0, 4)
    .map(
      (item: Record<string, any>) =>
        `${item.horizon_bars} bars | ${item.trend_vote} | return=${item.return_pct ?? '-'} | drawdown=${item.max_drawdown_pct ?? '-'}`,
    );
  return [
    `Summary: ${pack.summary || '-'}`,
    `Lookback: ${pack.lookback ?? '-'} | Interval: ${pack.interval ?? '-'}`,
    `Window: ${pack.window_start ?? '-'} -> ${pack.window_end ?? '-'}`,
    `Coverage: ${pack.bars_analyzed ?? '-'} / ${pack.bars_expected ?? '-'} (${pack.coverage_ratio ?? '-'})`,
    `Quality: ${formatList(pack.data_quality_flags)}`,
    `Anomalies: ${formatList(pack.anomaly_flags)}`,
    ...horizons,
  ];
}

export function unavailableSectionLines(
  section: Record<string, any> | null | undefined,
  label: string,
): null | string[] {
  if (section?.available === false) {
    return [`${label} unavailable: ${section.error || 'Unknown error.'}`];
  }
  return null;
}
