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

/**
 * Joins truthy string fragments with a single space, omitting falsy values.
 *
 * @param values - String fragments or falsy placeholders (false, null, undefined) to be filtered out
 * @returns The remaining fragments joined by a single space; an empty string if no fragments remain
 */
export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

/**
 * Formats a numeric value using US locale with a fixed number of fraction digits.
 *
 * @param value - The value to format; non-number or `NaN` values produce `'-'`.
 * @param digits - Number of fraction digits to include (defaults to 2).
 * @returns The formatted number string with exactly `digits` fraction digits, or `'-'` for invalid numbers.
 */
export function formatNumber(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

/**
 * Determines the account currency for the given dashboard.
 *
 * @param dashboard - Dashboard payload to read currency configuration from
 * @returns The first configured currency found (financeOps.accounting.currency, then portfolio.accounting.currency, then preferences.currencies[0]) or `USD` if none are set
 */
export function accountCurrency(dashboard: DashboardData): string {
  return (
    dashboard.financeOps?.accounting?.currency ||
    dashboard.portfolio?.accounting?.currency ||
    dashboard.preferences?.currencies?.[0] ||
    'USD'
  );
}

/**
 * Format a numeric fraction as a percentage string.
 *
 * @param value - The numeric fraction to format (e.g., `0.123` for 12.3%); if not a valid number, `'-'` is returned.
 * @param digits - Number of digits after the decimal point to include
 * @returns The formatted percentage with a `%` suffix (for example, `12.30%`), or `'-'` for invalid input
 */
export function formatPercent(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

/**
 * Formats an array as a comma-separated string or returns a placeholder when no items are present.
 *
 * @param value - The value to format; when it's an array its elements are joined with `', '`. If `value` is not an array or is empty, a placeholder is used.
 * @returns `'-'` if `value` is not an array or has no elements, otherwise the array elements joined by `', '`.
 */
export function formatList(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) {
    return '-';
  }
  return value.join(', ');
}

/**
 * Produce a concise summary line of source health counts for fresh, missing, and unknown.
 *
 * @param summary - Object containing `fresh`, `missing`, and `unknown` counts (may be numbers, strings, booleans, or undefined); if `summary` is falsy the function yields a placeholder.
 * @returns A string in the form `fresh X / missing Y / unknown Z`, or `-` when `summary` is not provided.
 */
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

/**
 * Format a source-health count value as a display string.
 *
 * @param value - A value representing a source health count; string, number, or boolean inputs are converted to their string form. Null, undefined, or non-primitive values are treated as zero.
 * @returns `'0'` for null/undefined or non-primitive values; otherwise the stringified input.
 */
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

/**
 * Convert a date/time string into a localized human-readable representation, with fallbacks.
 *
 * @param value - The input expected to be a non-empty date/time string.
 * @returns `'-'` if `value` is not a non-empty string; the original `value` string if it cannot be parsed as a valid Date; otherwise a localized date/time string produced by `Date.prototype.toLocaleString()`.
 */
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

/**
 * Build a list of human-readable context lines summarizing a persisted trade record.
 *
 * @param record - The persisted trade context object (may contain fields like `trade_id`, `run_id`, `consensus`, `manager_rationale`, `execution_*`, `review_summary`, and `routed_models`)
 * @returns An array of labeled strings for display; if `record` is missing returns a single-item array with `"No persisted trade context is available yet."`
 */
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

/**
 * Produce a compact size label for a proposal.
 *
 * @param proposal - Object containing optional numeric `quantity` or `notional` fields
 * @returns `qty {quantity}` with quantity formatted to 4 decimals if `proposal.quantity` is a number; `$ {notional}` with notional formatted to 2 decimals if `proposal.notional` is a number; otherwise `'-'`.
 */
function proposalSizeLabel(proposal: Record<string, any>): string {
  if (typeof proposal.quantity === 'number') {
    return `qty ${formatNumber(proposal.quantity, 4)}`;
  }
  if (typeof proposal.notional === 'number') {
    return `$${formatNumber(proposal.notional, 2)}`;
  }
  return '-';
}

/**
 * Builds a compact headline string for a trade proposal.
 *
 * @param proposal - Proposal object expected to include `symbol`, `side`, `status`, and optionally `quantity` or `notional` to describe size
 * @returns A string in the form `{symbol} {SIDE} | {status} | {sizeLabel}` where missing fields are `'-'`, `SIDE` is uppercased, and `sizeLabel` is `qty {quantity (4 decimals)}` if `quantity` is a number, `$ {notional (2 decimals)}` if `notional` is a number, or `'-'` otherwise
 */
export function proposalHeadline(proposal: Record<string, any>): string {
  return `${proposal.symbol ?? '-'} ${String(proposal.side ?? '-').toUpperCase()} | ${proposal.status ?? '-'} | ${proposalSizeLabel(proposal)}`;
}

/**
 * Builds an array of display lines summarizing manual-review trade proposals from the dashboard payload.
 *
 * @param dashboard - Dashboard payload that may contain a `tradeProposals` section
 * @returns An array of lines. If the proposal desk is unavailable a single line describing the error is returned. If there are no proposals a single informational line is returned. Otherwise each proposal is rendered as `"{proposal_id} | {headline} | confidence={formatted} | source={source or '-'"}`
 */
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

/**
 * Builds human-readable lines summarizing position plan coverage from a dashboard payload.
 *
 * Extracts the position plan coverage snapshot from the provided dashboard and returns
 * labeled lines for open positions, exit plans, missing plans, and overall coverage.
 * If no snapshot is present or the snapshot is explicitly unavailable, returns a single
 * explanatory message.
 *
 * @param dashboard - Dashboard payload to read position plan coverage from
 * @returns An array of labeled strings describing open positions, exit plans, missing plans, and coverage percentage; or a single-item array with an explanatory unavailable message
 */
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

/**
 * Determine the broker-related reason that blocks proposal approval.
 *
 * @param dashboard - Dashboard payload containing broker status and metadata
 * @returns A human-readable blocking reason when proposal approval is prevented, or an empty string if there is no broker-related block
 */
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

/**
 * Builds a list of human-readable, labeled lines summarizing a canonical analysis snapshot.
 *
 * @param snapshot - Snapshot object that may contain `summary`, `completeness_score`, `missing_sections`,
 *   `market | fundamental | macro` attribution objects (each with `source_name`), `news_events` and `disclosures` arrays,
 *   and `source_attributions` (array of source objects with `provider_type`, `source_name`, `source_role`, `freshness`).
 * @returns An array of labeled strings representing the snapshot fields. If `snapshot` is falsy, returns
 *   `['No canonical analysis snapshot is available yet.']`.
 */
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

/**
 * Builds an array of human-readable lines summarizing a persisted market context pack for UI display.
 *
 * @param pack - Persisted market context pack containing fields like `summary`, `lookback`, `interval`, `window_start`, `window_end`, `bars_analyzed`, `bars_expected`, `coverage_ratio`, `data_quality_flags`, `anomaly_flags`, and an array of `horizons`
 * @returns An array of formatted lines suitable for rendering; if `pack` is missing returns a single-element array with an unavailable message
 */
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

/**
 * Produce a single-line message when a section is unavailable, otherwise return `null`.
 *
 * @param section - Object that may contain `available: boolean` and optional `error: string`; treated as unavailable when `available === false`
 * @param label - Human-readable label used at the start of the message
 * @returns `null` if the section is not marked unavailable; otherwise an array with one message string like `{label} unavailable: {error || 'Unknown error.'}`
 */
export function unavailableSectionLines(
  section: Record<string, any> | null | undefined,
  label: string,
): null | string[] {
  if (section?.available === false) {
    return [`${label} unavailable: ${section.error || 'Unknown error.'}`];
  }
  return null;
}

/**
 * Convert dashboard chat history into a simple list of chat records.
 *
 * @param data - Dashboard payload that may contain `chatHistory.entries`; `null` or missing entries result in an empty list.
 * @returns An array of objects each with `user`, `persona`, and `response` properties, produced by reversing the original `entries` order.
 */
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

/**
 * Builds a short comma-separated list of up to three failing, blocking check names from a section.
 *
 * @param section - Object that may contain a `checks` array of diagnostic check objects
 * @returns `"-"` if no blocking failed checks are found, otherwise a comma-separated list of up to three check `name` values
 */
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

/**
 * Builds labeled status lines describing readiness and broker health from a dashboard payload.
 *
 * The returned lines cover local paper cycle permission and block reasons, Alpaca paper readiness and block reasons,
 * broker backend, external paper mode, kill switch state, and a broker health message.
 *
 * @param dashboard - Dashboard payload containing `v1Readiness` and `broker` sections
 * @returns An array of human-readable status strings for readiness and broker diagnostics
 */
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

/**
 * Summarizes provider diagnostics from the dashboard into display lines.
 *
 * @param dashboard - Dashboard payload containing `providerDiagnostics`
 * @returns An array of human-readable lines: market provider, market role, news mode, Finnhub/FMP/Alpaca key status (`configured` or `missing`), followed by up to three diagnostic warnings or `No provider warnings.`
 */
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

/**
 * Retrieves the ownership decision mode for a specific tool from the dashboard.
 *
 * @param dashboard - Dashboard payload containing ownership decisions
 * @param tool - Tool identifier to look up
 * @returns The ownership mode for the specified tool, or `'undecided'` if no decision is available.
 */
function ownershipMode(dashboard: DashboardData, tool: string): string {
  return (
    dashboard.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? 'undecided'
  );
}

/**
 * Normalize a base API URL to ensure it ends with the `/v1` path segment.
 *
 * If `baseUrl` is not a non-empty string, returns `'-'`. Otherwise trims a
 * trailing slash and returns the input with `/v1` appended unless it already
 * ends with `/v1`.
 *
 * @param baseUrl - Candidate base URL to normalize
 * @returns A base URL guaranteed to end with `/v1`, or `'-'` when `baseUrl` is not a valid non-empty string
 */
function withOpenAiSuffix(baseUrl: unknown): string {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    return '-';
  }
  const trimmed = baseUrl.replace(/\/$/, '');
  return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
}

/**
 * Resolve the effective model service base URL from the dashboard payload.
 *
 * @param dashboard - The dashboard payload to inspect for `modelService.base_url` and `doctor.base_url`
 * @returns The normalized base URL (ensuring an OpenAI-style `/v1` suffix when available), or `'-'` if no base URL is configured
 */
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

/**
 * Choose between two candidate values and indicate the chosen value's truthiness as `'yes'` or `'no'`.
 *
 * @param appOwnedValue - Primary value to evaluate; used unless it is `null` or `undefined`
 * @param fallbackValue - Secondary value used when `appOwnedValue` is `null` or `undefined`
 * @returns `'yes'` if the selected value is truthy, `'no'` otherwise
 */
function effectiveBoolean(
  appOwnedValue: unknown,
  fallbackValue: unknown,
): string {
  return (appOwnedValue ?? fallbackValue) ? 'yes' : 'no';
}

/**
 * Builds an ordered list of key/value status pairs representing system and service health for the control-room UI.
 *
 * @param dashboard - The control-room dashboard payload to read status fields from; may be `null`. Missing or undefined fields are rendered with fallback values.
 * @returns An array of `[label, value]` pairs (KeyValueItems) such as provider, model, base URL, reachability/availability, service messages, research state, broker backend/state, and market session; values use `'-'` when unavailable. 
 */
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

/**
 * Builds human-readable status lines for local tools and related services from the dashboard payload.
 *
 * @param dashboard - Dashboard payload used to derive ownership, runtime, reachability, and service information
 * @returns An array of status strings covering model adapter/runtime, model service details, firecrawl and camofox ownership/runtime/reachability, web GUI status, research status, and research source health summary
 */
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
