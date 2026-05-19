/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */

export type DashboardData = Record<string, any>;
export type TabId =
  | 'overview'
  | 'runtime'
  | 'portfolio'
  | 'proposals'
  | 'review'
  | 'memory'
  | 'chat'
  | 'settings';
export type MessageTone = 'neutral' | 'good' | 'warn' | 'bad';
export type InstructionMode = 'preview' | 'apply';
export type PanelAccent = 'lime' | 'amber' | 'cyan' | 'rose';
export type KeyValueItems = Array<[string, string]>;
export type ToolActionKind =
  | 'enable-local-tools'
  | 'enable-host-fallbacks'
  | 'start-model-service'
  | 'start-camofox-service';
export type ProposalActionKind = 'approve' | 'reject' | 'reconcile' | 'refresh';

export const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'runtime', label: 'Runtime' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'proposals', label: 'Proposals' },
  { id: 'review', label: 'Review' },
  { id: 'memory', label: 'Decision Evidence' },
  { id: 'chat', label: 'Chat' },
  { id: 'settings', label: 'Settings' },
];

export const marketLensImage =
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80';

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

export function formatNumber(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function accountCurrency(dashboard: DashboardData): string {
  return (
    dashboard.financeOps?.accounting?.currency ||
    dashboard.portfolio?.accounting?.currency ||
    dashboard.preferences?.currencies?.[0] ||
    'USD'
  );
}

export function formatPercent(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatList(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) {
    return '-';
  }
  return value.join(', ');
}

export function sourceHealthSummaryLine(
  summary: Record<string, unknown> | undefined,
): string {
  if (!summary) {
    return '-';
  }
  const fresh = formatSourceHealthCount(summary.fresh);
  const missing = formatSourceHealthCount(summary.missing);
  const unknown = formatSourceHealthCount(summary.unknown);
  return `fresh ${fresh} / missing ${missing} / unknown ${unknown}`;
}

export function formatSourceHealthCount(value: unknown): string {
  if (value === null || value === undefined) {
    return '0';
  }
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }
  return '0';
}

export function formatTimestamp(value: unknown): string {
  if (typeof value !== 'string' || !value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
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
    return [
      `Proposal desk unavailable: ${payload.error || 'Unknown error.'}`,
    ];
  }
  const proposals = Array.isArray(payload?.proposals)
    ? payload.proposals
    : [];
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

export function normalizeChatHistory(
  data: DashboardData | null,
): Array<Record<string, string>> {
  const entries = data?.chatHistory?.entries || [];
  return [...entries].reverse().map((entry: Record<string, any>) => ({
    user: entry.user_message,
    persona: entry.persona,
    response: entry.response_text,
  }));
}

export function failedCheckNames(
  section: Record<string, any> | undefined,
): string {
  const failed = (section?.checks || [])
    .filter(
      (item: Record<string, any>) => item.blocking !== false && !item.passed,
    )
    .map((item: Record<string, any>) => item.name)
    .slice(0, 3);
  return failed.length ? failed.join(', ') : '-';
}

export function readinessLines(dashboard: DashboardData): string[] {
  const readiness = dashboard.v1Readiness || {};
  const broker = dashboard.broker || {};
  const paper = readiness.paper_operations || {};
  const alpaca = readiness.alpaca_paper || {};
  return [
    `Can run local paper cycle: ${paper.allowed ? 'yes' : 'no'}`,
    `Why paper cycle is blocked: ${failedCheckNames(paper)}`,
    `Can use Alpaca paper: ${alpaca.ready ? 'yes' : 'no'}`,
    `Why Alpaca paper is blocked: ${failedCheckNames(alpaca)}`,
    `Backend: ${broker.backend ?? '-'}`,
    `External paper mode active: ${broker.external_paper ? 'yes' : 'no'}`,
    `Kill Switch: ${broker.kill_switch_active ? 'active' : 'inactive'}`,
    `Broker Health: ${broker.healthcheck?.message ?? broker.message ?? '-'}`,
  ];
}

export function providerWarningLines(dashboard: DashboardData): string[] {
  const diagnostics = dashboard.providerDiagnostics || {};
  const market = diagnostics.market_data || {};
  const keys = diagnostics.configured_keys || {};
  const warnings = Array.isArray(diagnostics.warnings)
    ? diagnostics.warnings
    : [];
  return [
    `Market Provider: ${market.selected_provider ?? '-'}`,
    `Market Role: ${market.selected_role ?? '-'}`,
    `News Mode: ${diagnostics.news?.mode ?? '-'}`,
    `Finnhub Key: ${keys.finnhub ? 'configured' : 'missing'}`,
    `FMP Key: ${keys.fmp ? 'configured' : 'missing'}`,
    `Alpaca Key: ${keys.alpaca ? 'configured' : 'missing'}`,
    ...(warnings.length ? warnings.slice(0, 3) : ['No provider warnings.']),
  ];
}

function ownershipMode(dashboard: DashboardData, tool: string): string {
  return dashboard.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? 'undecided';
}

function withOpenAiSuffix(baseUrl: unknown): string {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    return '-';
  }
  const trimmed = baseUrl.replace(/\/$/, '');
  return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
}

function effectiveModelBaseUrl(dashboard: DashboardData | null): string {
  const modelService = dashboard?.modelService || {};
  if (modelService.app_owned && modelService.base_url) {
    return withOpenAiSuffix(modelService.base_url);
  }
  if (dashboard?.doctor?.base_url) {
    return withOpenAiSuffix(dashboard.doctor.base_url);
  }
  return '-';
}

function effectiveBoolean(
  appOwnedValue: unknown,
  fallbackValue: unknown,
): string {
  return (appOwnedValue ?? fallbackValue) ? 'yes' : 'no';
}

export function systemStatusItems(
  dashboard: DashboardData | null,
): KeyValueItems {
  const modelService = dashboard?.modelService || {};
  const provider = dashboard?.doctor?.provider ?? 'ollama';
  const reachabilityLabel =
    provider === 'ollama' ? 'Ollama Reachable' : 'LLM Reachable';
  return [
    ['Provider', provider],
    ['Model', dashboard?.doctor?.model ?? modelService.configured_model ?? '-'],
    ['Base URL', effectiveModelBaseUrl(dashboard)],
    [
      reachabilityLabel,
      effectiveBoolean(
        modelService.app_owned ? modelService.service_reachable : undefined,
        dashboard?.doctor?.llm_reachable ?? dashboard?.doctor?.ollama_reachable,
      ),
    ],
    [
      'Model Available',
      effectiveBoolean(
        modelService.app_owned ? modelService.model_available : undefined,
        dashboard?.doctor?.model_available,
      ),
    ],
    ['Model Service', modelService.message ?? '-'],
    ['Camofox Service', dashboard?.camofoxService?.message ?? '-'],
    ['Web GUI Service', dashboard?.webGui?.message ?? '-'],
    ['Research', dashboard?.research?.status ?? '-'],
    ['Research Control', dashboard?.research?.cycleControl?.status ?? '-'],
    [
      'Research Trigger',
      dashboard?.research?.cycleControl?.trigger_now_requested
        ? 'requested'
        : 'clear',
    ],
    [
      'Research Digest Replay',
      dashboard?.research?.latestDigestReplay?.available ? 'available' : '-',
    ],
    [
      'Research Sources',
      sourceHealthSummaryLine(dashboard?.research?.source_health_summary),
    ],
    ['Broker Backend', dashboard?.broker?.backend ?? '-'],
    ['Broker State', dashboard?.broker?.state ?? '-'],
    ['Execution Mode', dashboard?.broker?.execution_mode ?? '-'],
    ['Market Session', dashboard?.calendar?.session?.session_state ?? '-'],
  ];
}

export function localToolLines(dashboard: DashboardData): string[] {
  const modelService = dashboard.modelService || {};
  const camofox = dashboard.camofoxService || {};
  const provider = dashboard.doctor?.provider ?? 'ollama';
  const firecrawlMode = ownershipMode(dashboard, 'firecrawl');
  let camofoxBlocker = 'Camofox Access Key: -';
  if (camofox.access_key_configured === false) {
    camofoxBlocker =
      'Camofox Blocker: set CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY in ignored local env before start';
  } else if (camofox.access_key_configured) {
    camofoxBlocker = 'Camofox Access Key: configured';
  }
  return [
    `Model Adapter: ${provider}`,
    `LLM Runtime: internal-first${modelService.app_owned ? ' app-owned' : ''}`,
    `Model Service: ${modelService.message ?? '-'}`,
    `Ollama Ownership: ${ownershipMode(dashboard, 'ollama')}`,
    `Model Service Owned: ${modelService.app_owned ? 'yes' : 'no'}`,
    `Model Service Reachable: ${modelService.service_reachable ? 'yes' : 'no'}`,
    `Model Available: ${modelService.model_available ? 'yes' : 'no'}`,
    `Model Service URL: ${withOpenAiSuffix(modelService.base_url ?? modelService.configured_base_url)}`,
    `Firecrawl Ownership: ${firecrawlMode}`,
    `Firecrawl Runtime: internal SDK first; host CLI fallback ${firecrawlMode === 'host-owned' ? 'enabled' : 'disabled by ownership'}`,
    `Camofox: ${camofox.message ?? '-'}`,
    `Camofox Ownership: ${ownershipMode(dashboard, 'camofox')}`,
    `Camofox Owned: ${camofox.app_owned ? 'yes' : 'no'}`,
    `Camofox Reachable: ${camofox.service_reachable ? 'yes' : 'no'}`,
    camofoxBlocker,
    `Camofox URL: ${camofox.base_url ?? '-'}`,
    `Web GUI: ${dashboard.webGui?.message ?? '-'}`,
    `Web GUI Owned: ${dashboard.webGui?.app_owned ? 'yes' : 'no'}`,
    `Web GUI URL: ${dashboard.webGui?.url ?? '-'}`,
    `Research: ${dashboard.research?.status ?? '-'} (${dashboard.research?.backend ?? '-'})`,
    `Research Sources: ${sourceHealthSummaryLine(dashboard.research?.source_health_summary)}`,
  ];
}
