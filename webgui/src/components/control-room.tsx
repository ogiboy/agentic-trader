/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
'use client';

import Image from 'next/image';
import {
  CheckCircle2,
  Power,
  RotateCcw,
  SlidersHorizontal,
  Wrench,
  XCircle,
} from 'lucide-react';
import {
  type SyntheticEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  CHAT_PERSONAS,
  formatChatPersona,
  type ChatPersona,
} from '@/lib/chat-personas';

type DashboardData = Record<string, any>;
type TabId =
  | 'overview'
  | 'runtime'
  | 'portfolio'
  | 'proposals'
  | 'review'
  | 'memory'
  | 'chat'
  | 'settings';
type MessageTone = 'neutral' | 'good' | 'warn' | 'bad';
type InstructionMode = 'preview' | 'apply';
type PanelAccent = 'lime' | 'amber' | 'cyan' | 'rose';
type KeyValueItems = Array<[string, string]>;
type ToolActionKind =
  | 'enable-local-tools'
  | 'enable-host-fallbacks'
  | 'start-model-service'
  | 'start-camofox-service';
type ProposalActionKind = 'approve' | 'reject' | 'reconcile';

const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'runtime', label: 'Runtime' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'proposals', label: 'Proposals' },
  { id: 'review', label: 'Review' },
  { id: 'memory', label: 'Decision Evidence' },
  { id: 'chat', label: 'Chat' },
  { id: 'settings', label: 'Settings' },
];

const marketLensImage =
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80';

/**
 * Builds a space-separated className string from the provided fragments, ignoring falsy entries.
 *
 * @param values - Class name fragments; falsy values (false, null, undefined, or empty string) are omitted
 * @returns The concatenated className or an empty string if no fragments remain
 */
function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

/**
 * Formats a numeric input using en-US locale with a fixed number of fraction digits.
 *
 * @param value - The value to format; non-number or `NaN` yields `"-"`.
 * @param digits - Number of fraction digits to display (default: `2`).
 * @returns `"-"` for non-number or `NaN`, otherwise the number formatted with exactly `digits` fraction digits.
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

function accountCurrency(dashboard: DashboardData): string {
  return (
    dashboard.financeOps?.accounting?.currency ||
    dashboard.portfolio?.accounting?.currency ||
    dashboard.preferences?.currencies?.[0] ||
    'USD'
  );
}

/**
 * Format a numeric ratio as a percent string.
 *
 * @param value - The numeric ratio to format (e.g., `0.12` for 12%). Non-number or `NaN` values produce `"-"`.
 * @param digits - Number of digits after the decimal point in the formatted percent (default: `2`).
 * @returns `"-"` for non-number or `NaN`, otherwise the percentage string with a trailing `%` (e.g., `"12.00%"`).
 */
export function formatPercent(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

/**
 * Produce a comma-separated display string from an array or a placeholder when missing.
 *
 * @param value - The value expected to be an array of items; elements are joined with ", ". If `value` is not an array or is empty, the placeholder `"-"` is returned.
 * @returns The joined string of `value` elements separated by ", " when `value` is a non-empty array, otherwise `"-"`.
 */
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

/**
 * Format a timestamp string into the current locale's readable date and time.
 *
 * @param value - The input timestamp to format. If `value` is falsy or not a string, the function returns `"-"`. If `value` is a string that cannot be parsed as a valid Date, the original string is returned.
 * @returns A localized date/time string when `value` is a parseable date string; the original `value` string if it cannot be parsed; `"-"` when `value` is falsy or not a string.
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
 * Builds an array of human-readable lines summarizing a persisted trade context record for UI display.
 *
 * @param record - The trade context object (may be `null`/`undefined`). Expected fields include `trade_id`, `run_id`, `consensus.alignment_level`, `manager_rationale`, `execution_rationale`, `execution_backend`, `execution_adapter`, `execution_outcome_status`, `execution_rejection_reason`, `review_summary`, and `routed_models`.
 * @returns An array of labeled strings for trade/run IDs, consensus, rationales, execution details, review summary, and routed models; if `record` is missing returns a single line stating no persisted trade context is available.
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

function proposalSizeLabel(proposal: Record<string, any>): string {
  if (typeof proposal.quantity === 'number') {
    return `qty ${formatNumber(proposal.quantity, 4)}`;
  }
  if (typeof proposal.notional === 'number') {
    return `$${formatNumber(proposal.notional, 2)}`;
  }
  return '-';
}

function proposalHeadline(proposal: Record<string, any>): string {
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

function proposalApprovalBlockedReason(dashboard: DashboardData): string {
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
 * Builds display lines summarizing a canonical analysis snapshot.
 *
 * @param snapshot - Snapshot object containing analysis fields; if `null` or `undefined` a placeholder line is returned
 * @returns An array of human-readable lines: summary, completeness score, missing sections, market/fundamental/macro source names, counts for news events and disclosures, and up to six source attribution lines
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
 * Builds an array of human-readable lines summarizing a market context pack for display.
 *
 * @param pack - Market context pack object (or `null`/`undefined`). Expected fields used:
 *   `summary`, `lookback`, `interval`, `window_start`, `window_end`,
 *   `bars_analyzed`, `bars_expected`, `coverage_ratio`,
 *   `data_quality_flags`, `anomaly_flags`, and `horizons` (each horizon may include
 *   `horizon_bars`, `trend_vote`, `return_pct`, `max_drawdown_pct`).
 * @returns An array of formatted strings representing the pack summary, window, coverage,
 * quality/anomaly flags, and up to four horizon lines. If `pack` is `null`/`undefined`,
 * returns a single line stating that no persisted market context pack is available yet.
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
 * Returns a single explicit operator-facing error line when a dashboard section is unavailable.
 *
 * @param section - Dashboard section object that may expose `available` and `error`
 * @param label - Human-readable section label used in the message
 * @returns A one-line array when the section is explicitly unavailable; otherwise `null`
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
 * Convert dashboard chat history into a simplified, normalized list of message objects.
 *
 * @param data - The dashboard payload (or `null`) containing optional `chatHistory.entries`.
 * @returns An array of objects each with `user` (the user's message), `persona`, and `response` (the agent's reply); the order is the source entries reversed.
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

export class WebguiHttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'WebguiHttpError';
    this.status = status;
  }
}

/**
 * Fetches JSON from the given URL and returns the parsed payload.
 *
 * The request includes a `Content-Type: application/json` header (merged with any headers in `init`)
 * and uses `cache: "no-store"`.
 *
 * @param url - The endpoint URL to fetch.
 * @param init - Optional fetch init options; headers provided here are merged with the default JSON header.
 * @returns The parsed JSON payload cast to `T`.
 * @throws Error when the response has a non-OK status; the error message is `payload.error` if present or `"Request failed."`.
 */
export async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const requestInit: RequestInit = {};
  if (init) {
    Object.assign(requestInit, init);
    delete requestInit.headers;
  }

  const response = await fetch(url, {
    ...requestInit,
    headers,
    cache: 'no-store',
    credentials: 'same-origin',
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new WebguiHttpError(
      payload.error || 'Request failed.',
      response.status,
    );
  }
  return payload as T;
}

async function authenticateWebguiSession(token: string): Promise<void> {
  await readJson<{ authenticated: boolean; tokenRequired: boolean }>(
    '/api/session',
    {
      method: 'POST',
      body: JSON.stringify({ token }),
    },
  );
}

/**
 * Render a titled panel section with optional accent styling.
 *
 * @param accent - Optional accent color; one of `"lime"`, `"amber"`, `"cyan"`, or `"rose"`. When provided, applies the `panel--{accent}` modifier class.
 * @returns The section element containing the panel title and body.
 */
function Panel({
  title,
  accent,
  children,
}: Readonly<{
  title: string;
  accent?: PanelAccent;
  children: React.ReactNode;
}>) {
  return (
    <section className={cx('panel', accent ? `panel--${accent}` : undefined)}>
      <div className="panel__title">{title}</div>
      <div className="panel__body">{children}</div>
    </section>
  );
}

function WebguiTokenPrompt({
  busy,
  error,
  token,
  onSubmit,
  onTokenChange,
}: Readonly<{
  busy: boolean;
  error: string | null;
  token: string;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onTokenChange: (value: string) => void;
}>) {
  return (
    <section className="auth-panel" aria-labelledby="webgui-token-title">
      <div className="auth-panel__header">
        <div className="sidebar__eyebrow">Protected local command center</div>
        <h1 id="webgui-token-title">Agentic Trader</h1>
        <p>
          Enter the Web GUI token from your ignored local environment. The token
          is exchanged for a same-origin HttpOnly session cookie and is not
          rendered into the page.
        </p>
      </div>
      <form className="auth-panel__form" onSubmit={onSubmit}>
        <label className="field-label">
          <span>Web GUI token</span>
          <input
            autoComplete="off"
            autoFocus
            onChange={(event) => onTokenChange(event.target.value)}
            type="password"
            value={token}
          />
        </label>
        {error ? <div className="banner banner--bad">{error}</div> : null}
        <button
          className="button button--solid"
          disabled={busy || !token.trim()}
          type="submit"
        >
          {busy ? 'Unlocking...' : 'Unlock'}
        </button>
      </form>
    </section>
  );
}

/**
 * Renders a description list (`dl`) of label/value pairs as a key/value list.
 *
 * @param items - An array of `[label, value]` string tuples to render as `dt`/`dd` rows
 * @returns A `<dl>` element containing one row per tuple, each with a `dt` for the label and a `dd` for the value
 */
function KeyValueList({ items }: Readonly<{ items: KeyValueItems }>) {
  return (
    <dl className="kv-list">
      {items.map(([label, value]) => (
        <div className="kv-list__row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Render an unordered list from an array of strings.
 *
 * @param items - Array of text entries to display as list items
 * @returns A `<ul>` element whose children are `<li>` elements for each string in `items`
 */
function TextList({ items }: Readonly<{ items: string[] }>) {
  return (
    <ul className="text-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * Renders a pretty-printed JSON representation of `value` inside a <pre> element.
 *
 * @param value - The value to serialize as formatted JSON for display
 * @returns A React element containing the formatted JSON
 */
function JsonPreview({ value }: Readonly<{ value: unknown }>) {
  return <pre className="json-preview">{JSON.stringify(value, null, 2)}</pre>;
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

/**
 * Builds human-readable lines summarizing provider configuration and warnings from the dashboard.
 *
 * Reads provider diagnostics from the `dashboard` payload and returns lines for selected market provider,
 * provider role, news mode, whether Finnhub/FMP/Alpaca API keys are configured, and up to three provider warnings.
 *
 * @param dashboard - Dashboard payload containing `providerDiagnostics` used to derive provider and key status
 * @returns An array of status lines describing provider selection, news mode, key configuration, and up to three warnings (or `"No provider warnings."` when none)
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
 * Get the ownership decision mode for a specified tool.
 *
 * @param dashboard - The dashboard payload containing tool ownership decisions
 * @param tool - The tool key to look up in `dashboard.toolOwnership.decisions_by_tool`
 * @returns The `mode` value for the given tool, or `'undecided'` if no mode is recorded
 */
function ownershipMode(dashboard: DashboardData, tool: string): string {
  return dashboard.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? 'undecided';
}

/**
 * Normalize a model service base URL so it consistently ends with `/v1`, or return `-` for invalid input.
 *
 * @param baseUrl - The value to normalize into a base URL; may be any type.
 * @returns The input URL with a trailing slash removed and `/v1` appended when missing, or `-` if `baseUrl` is not a non-empty string.
 */
function withOpenAiSuffix(baseUrl: unknown): string {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    return '-';
  }
  const trimmed = baseUrl.replace(/\/$/, '');
  return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
}

/**
 * Determines the effective base URL to use for model service requests.
 *
 * @param dashboard - The dashboard payload containing modelService and doctor configuration
 * @returns The model service base URL with an OpenAI `/v1` suffix when the app-owned model service is configured, otherwise the doctor's base URL, or `'-'` if neither is available
 */
function effectiveModelBaseUrl(dashboard: DashboardData | null): string {
  const modelService = dashboard?.modelService || {};
  if (modelService.app_owned && modelService.base_url) {
    return withOpenAiSuffix(modelService.base_url);
  }
  return dashboard?.doctor?.base_url ?? '-';
}

/**
 * Selects the primary value when defined, otherwise the fallback, and yields `"yes"` if that chosen value is truthy, `"no"` otherwise.
 *
 * @param appOwnedValue - Primary value to consider first (used when not `null` or `undefined`)
 * @param fallbackValue - Secondary value used when `appOwnedValue` is `null` or `undefined`
 * @returns `"yes"` if the selected value is truthy, `"no"` otherwise
 */
function effectiveBoolean(
  appOwnedValue: unknown,
  fallbackValue: unknown,
): string {
  return (appOwnedValue ?? fallbackValue) ? 'yes' : 'no';
}

/**
 * Build a list of labeled system status key/value pairs derived from the dashboard payload.
 *
 * Uses model service, doctor, research, broker, calendar, and auxiliary service fields to produce
 * human-readable status entries (provider, model, base URL, reachability, availability, service
 * messages, research and broker states, and market session).
 *
 * @param dashboard - The dashboard payload (may be null) from which status values are extracted
 * @returns A KeyValueItems array where each tuple is [label, value] describing a system status item
 */
export function systemStatusItems(dashboard: DashboardData | null): KeyValueItems {
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
 * Builds human-readable status lines describing local tool, model service, and related ownership/reachability state from the dashboard payload.
 *
 * @param dashboard - The dashboard payload containing runtime, service, and ownership metadata
 * @returns An array of labeled status strings suitable for display in the "Local Tools" panel (e.g., model adapter, service reachability, ownership, URLs, and research source summary)
 */
export function localToolLines(dashboard: DashboardData): string[] {
  const modelService = dashboard.modelService || {};
  const camofox = dashboard.camofoxService || {};
  const provider = dashboard.doctor?.provider ?? 'ollama';
  const firecrawlMode = ownershipMode(dashboard, 'firecrawl');
  const camofoxBlocker =
    camofox.access_key_configured === false
      ? 'Camofox Blocker: set CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY in ignored local env before start'
      : `Camofox Access Key: ${camofox.access_key_configured ? 'configured' : '-'}`;
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

/**
 * Render the Overview tab, including market ribbon, current cycle, system status, readiness gates, local tool controls, provider warnings, and recent decision workflow events.
 *
 * @param dashboard - Dashboard payload used to populate view sections and derive display data.
 * @param currentCycle - Key/value pairs describing the current runtime cycle displayed in the "Current Cycle" panel.
 * @param system - Key/value pairs describing system and provider status displayed in the "System" panel.
 * @param busy - Current global busy/action identifier; when non-null, tool action buttons are disabled.
 * @param onToolAction - Handler invoked with a ToolActionKind when a local tool action button is clicked.
 * @returns The rendered Overview view as JSX.
 */
export function OverviewView({
  dashboard,
  currentCycle,
  system,
  busy,
  onToolAction,
}: Readonly<{
  dashboard: DashboardData;
  currentCycle: KeyValueItems;
  system: KeyValueItems;
  busy: string | null;
  onToolAction: (kind: ToolActionKind) => void;
}>) {
  const recentStageEvents = dashboard.agentActivity?.recent_stage_events?.length
    ? dashboard.agentActivity.recent_stage_events.map(
        (event: Record<string, any>) =>
          `${formatTimestamp(event.created_at)} | ${event.stage} | ${event.status} | ${event.message}`,
      )
    : ['No live agent stage events yet.'];

  return (
    <div className="stack">
      <section className="market-ribbon">
        <Image
          className="market-ribbon__image"
          src={marketLensImage}
          alt="Trading screens showing market data."
          fill
          priority
          sizes="(max-width: 960px) 100vw, 50vw"
        />
        <div className="market-ribbon__overlay">
          <div>
            <p className="eyebrow">Operator Truth</p>
            <h1>Agentic Trader Web GUI</h1>
            <p className="market-ribbon__copy">
              Local-first runtime, paper-first execution, and the same dashboard
              contract that powers CLI, Rich, and Ink.
            </p>
          </div>
          <div className="pill-row">
            <span className="pill">
              {dashboard.status?.runtime_mode ?? '-'}
            </span>
            <span className="pill">{dashboard.broker?.backend ?? '-'}</span>
            <span className="pill">
              {dashboard.calendar?.session?.venue ?? 'session unknown'}
            </span>
            <span className="pill">{dashboard.doctor?.model ?? '-'}</span>
          </div>
        </div>
      </section>

      <div className="grid grid--2">
        <Panel title="Current Cycle" accent="lime">
          <KeyValueList items={currentCycle} />
        </Panel>
        <Panel title="System" accent="cyan">
          <KeyValueList items={system} />
        </Panel>
      </div>

      <div className="grid grid--2">
        <Panel title="Readiness Gates" accent="rose">
          <TextList items={readinessLines(dashboard)} />
        </Panel>
        <Panel title="Local Tools" accent="cyan">
          <div className="tool-actions">
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('enable-local-tools')}
              type="button"
            >
              <SlidersHorizontal aria-hidden="true" size={16} />
              App Tools
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('enable-host-fallbacks')}
              type="button"
            >
              <SlidersHorizontal aria-hidden="true" size={16} />
              Host Fallback
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => onToolAction('start-model-service')}
              type="button"
            >
              <Power aria-hidden="true" size={16} />
              Ollama
            </button>
            <button
              className="button"
              disabled={busy !== null || dashboard.camofoxService?.access_key_configured === false}
              onClick={() => onToolAction('start-camofox-service')}
              type="button"
            >
              <Wrench aria-hidden="true" size={16} />
              Camofox
            </button>
          </div>
          <TextList items={localToolLines(dashboard)} />
        </Panel>
      </div>

      <Panel title="Provider Warnings" accent="amber">
        <TextList items={providerWarningLines(dashboard)} />
      </Panel>

      <Panel title="Decision Workflow" accent="amber">
        <TextList items={recentStageEvents} />
      </Panel>
    </div>
  );
}

export function RuntimeView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const runtimeEvents = dashboard.logs?.length
    ? dashboard.logs.map(
        (event: Record<string, any>) =>
          `${formatTimestamp(event.created_at)} | ${event.level} | ${event.event_type} | ${event.symbol ?? '-'} | ${event.message}`,
      )
    : ['No runtime events recorded yet.'];
  const supervisorTails = [
    ...(dashboard.supervisor?.stderr_tail?.length
      ? dashboard.supervisor.stderr_tail
      : ['No stderr tail.']),
    ...(dashboard.supervisor?.stdout_tail?.length
      ? dashboard.supervisor.stdout_tail
      : ['No stdout tail.']),
  ];

  return (
    <div className="grid grid--2">
      <Panel title="Runtime State" accent="lime">
        <KeyValueList
          items={[
            ['Runtime', dashboard.status?.runtime_state ?? '-'],
            ['Live Process', dashboard.status?.live_process ? 'yes' : 'no'],
            ['PID', String(dashboard.status?.state?.pid ?? '-')],
            ['Current Symbol', dashboard.status?.state?.current_symbol ?? '-'],
            [
              'Cycle Count',
              String(dashboard.status?.state?.cycle_count ?? '-'),
            ],
            ['Updated', formatTimestamp(dashboard.status?.state?.updated_at)],
            [
              'Stop Requested',
              String(dashboard.status?.state?.stop_requested ?? false),
            ],
            ['Status', dashboard.status?.status_message ?? '-'],
          ]}
        />
      </Panel>
      <Panel title="Stage Flow" accent="cyan">
        <TextList
          items={(dashboard.agentActivity?.stage_statuses || []).map(
            (stage: Record<string, any>) =>
              `${stage.stage} | ${stage.status} | ${stage.message}`,
          )}
        />
      </Panel>
      <Panel title="Runtime Events" accent="amber">
        <TextList items={runtimeEvents} />
      </Panel>
      <Panel title="Supervisor Tails" accent="rose">
        <TextList items={supervisorTails} />
      </Panel>
    </div>
  );
}

export function PortfolioView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const currency = accountCurrency(dashboard);
  const accounting =
    dashboard.financeOps?.accounting ?? dashboard.portfolio?.accounting ?? {};
  const portfolioUnavailable = unavailableSectionLines(
    dashboard.portfolio,
    'Portfolio',
  );
  const riskUnavailable = unavailableSectionLines(
    dashboard.riskReport,
    'Risk report',
  );
  const journalLines =
    unavailableSectionLines(dashboard.journal, 'Trade journal') ||
    (dashboard.journal?.entries?.length
      ? dashboard.journal.entries.map(
          (entry: Record<string, any>) =>
            `${formatTimestamp(entry.opened_at)} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`,
        )
      : ['No trade journal entries yet.']);

  return (
    <div className="grid grid--2">
      <Panel title="Portfolio" accent="lime">
        {portfolioUnavailable ? (
          <TextList items={portfolioUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `Cash (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.cash),
                ],
                [
                  `Market Value (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.market_value),
                ],
                [
                  `Equity (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.equity),
                ],
                [
                  `Realized PnL (${currency})`,
                  formatNumber(dashboard.portfolio?.snapshot?.realized_pnl),
                ],
                [
                  `Unrealized PnL (${currency}, paper mark)`,
                  formatNumber(dashboard.portfolio?.snapshot?.unrealized_pnl),
                ],
                [
                  'Open Positions',
                  String(dashboard.portfolio?.snapshot?.open_positions ?? '-'),
                ],
                ['Marked At', formatTimestamp(accounting?.mark_created_at)],
                ['Mark Source', accounting?.mark_source ?? '-'],
              ]}
            />
            <JsonPreview value={dashboard.portfolio?.positions || []} />
          </>
        )}
      </Panel>
      <Panel title="Risk Report" accent="rose">
        {riskUnavailable ? (
          <TextList items={riskUnavailable} />
        ) : (
          <>
            <KeyValueList
              items={[
                [
                  `Equity (${currency})`,
                  formatNumber(dashboard.riskReport?.report?.equity),
                ],
                [
                  'Gross Exposure',
                  formatPercent(
                    dashboard.riskReport?.report?.gross_exposure_pct,
                  ),
                ],
                [
                  'Largest Position',
                  formatPercent(
                    dashboard.riskReport?.report?.largest_position_pct,
                  ),
                ],
                [
                  'Drawdown',
                  formatPercent(
                    dashboard.riskReport?.report?.drawdown_from_peak_pct,
                  ),
                ],
                [
                  'Warnings',
                  String((dashboard.riskReport?.report?.warnings || []).length),
                ],
                [
                  'Generated At',
                  formatTimestamp(dashboard.riskReport?.report?.generated_at),
                ],
              ]}
            />
            <TextList
              items={dashboard.riskReport?.report?.warnings || ['No warnings.']}
            />
          </>
        )}
      </Panel>
      <Panel title="Trade Journal" accent="amber">
        <TextList items={journalLines} />
      </Panel>
      <Panel title="Preferences" accent="cyan">
        <KeyValueList
          items={[
            ['Regions', formatList(dashboard.preferences?.regions)],
            ['Exchanges', formatList(dashboard.preferences?.exchanges)],
            ['Currencies', formatList(dashboard.preferences?.currencies)],
            ['Risk', dashboard.preferences?.risk_profile ?? '-'],
            ['Style', dashboard.preferences?.trade_style ?? '-'],
            ['Behavior', dashboard.preferences?.behavior_preset ?? '-'],
            ['Tone', dashboard.preferences?.agent_tone ?? '-'],
            ['Strictness', dashboard.preferences?.strictness_preset ?? '-'],
          ]}
        />
      </Panel>
      <Panel title="Desk Accounting Notes" accent="amber">
        <KeyValueList
          items={[
            ['Currency', currency],
            ['Mark Status', accounting.mark_status ?? 'mark_time_unavailable'],
            ['Fees', accounting.cost_model?.fees ?? '-'],
            [
              'Slippage',
              accounting.cost_model?.slippage_bps == null
                ? '-'
                : `${accounting.cost_model.slippage_bps} bps`,
            ],
            ['Rejection Evidence', accounting.rejection_evidence ?? '-'],
          ]}
        />
      </Panel>
    </div>
  );
}

export function ProposalDeskView({
  dashboard,
  busy,
  proposalNote,
  onProposalNoteChange,
  onProposalAction,
}: Readonly<{
  dashboard: DashboardData;
  busy: string | null;
  proposalNote: string;
  onProposalNoteChange: (value: string) => void;
  onProposalAction: (
    kind: ProposalActionKind,
    proposalId: string,
  ) => Promise<void>;
}>) {
  const proposals = Array.isArray(dashboard.tradeProposals?.proposals)
    ? dashboard.tradeProposals.proposals
    : [];
  const proposalUnavailable = dashboard.tradeProposals?.available === false;
  const approvalBlockedReason = proposalApprovalBlockedReason(dashboard);

  return (
    <div className="grid grid--2">
      <Panel title="Proposal Desk" accent="amber">
        <TextList items={proposalLines(dashboard)} />
        {approvalBlockedReason ? (
          <div className="banner banner--warn">{approvalBlockedReason}</div>
        ) : null}
        {proposalUnavailable ? null : (
          <>
            {proposals.length ? (
              <div className="proposal-list">
                {proposals.slice(0, 6).map((proposal: Record<string, any>) => {
                  const proposalId = String(proposal.proposal_id ?? '');
                  const isPending = proposal.status === 'pending';
                  const canApprove = isPending && !approvalBlockedReason;
                  const canReconcile =
                    proposal.status === 'approved' &&
                    Boolean(proposal.execution_intent_id);
                  return (
                    <article className="proposal-card" key={proposalId}>
                      <div className="proposal-card__head">
                        <strong>{proposalHeadline(proposal)}</strong>
                        <span className="chip">
                          {formatNumber(proposal.confidence, 2)}
                        </span>
                      </div>
                      <p>{proposal.thesis || '-'}</p>
                      <div className="proposal-card__meta">
                        <span>{proposalId}</span>
                        <span>{proposal.source || '-'}</span>
                        <span>
                          stop {formatNumber(proposal.stop_loss, 2)} / take{' '}
                          {formatNumber(proposal.take_profit, 2)}
                        </span>
                      </div>
                      <div className="tool-actions">
                        <button
                          className="button button--solid"
                          disabled={!canApprove || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('approve', proposalId)
                          }
                          title="Approve pending paper proposal"
                          type="button"
                        >
                          <CheckCircle2 aria-hidden size={16} />
                          Approve
                        </button>
                        <button
                          className="button"
                          disabled={
                            !isPending || Boolean(busy) || !proposalNote.trim()
                          }
                          onClick={() =>
                            void onProposalAction('reject', proposalId)
                          }
                          title="Reject pending proposal"
                          type="button"
                        >
                          <XCircle aria-hidden size={16} />
                          Reject
                        </button>
                        <button
                          className="button"
                          disabled={!canReconcile || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('reconcile', proposalId)
                          }
                          title="Reconcile approved in-flight proposal"
                          type="button"
                        >
                          <RotateCcw aria-hidden size={16} />
                          Reconcile
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : null}
            <div className="composer">
              <textarea
                onChange={(event) =>
                  onProposalNoteChange(event.target.value)
                }
                placeholder="Approval note or rejection reason."
                value={proposalNote}
              />
            </div>
          </>
        )}
      </Panel>
      <Panel title="Desk Safety" accent="cyan">
        <KeyValueList
          items={[
            ['Backend', dashboard.broker?.backend ?? '-'],
            ['State', dashboard.broker?.state ?? '-'],
            [
              'External Paper',
              dashboard.broker?.external_paper ? 'yes' : 'no',
            ],
            ['Live Requested', dashboard.broker?.live_requested ? 'yes' : 'no'],
            ['Kill Switch', dashboard.broker?.kill_switch_active ? 'on' : 'off'],
            ['Message', dashboard.broker?.message ?? '-'],
          ]}
        />
      </Panel>
    </div>
  );
}

export function ReviewView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const reviewLines =
    unavailableSectionLines(dashboard.review, 'Latest review') ||
    (dashboard.review?.record
      ? [
          `Run ID: ${dashboard.review.record.run_id}`,
          `Created: ${formatTimestamp(dashboard.review.record.created_at)}`,
          `Symbol: ${dashboard.review.record.symbol}`,
          `Approved: ${dashboard.review.record.approved}`,
          `Coordinator Focus: ${dashboard.review.record.artifacts?.coordinator?.market_focus ?? '-'}`,
          `Consensus: ${dashboard.review.record.artifacts?.consensus?.alignment_level ?? '-'}`,
          `Review Summary: ${dashboard.review.record.artifacts?.review?.summary ?? '-'}`,
        ]
      : ['No persisted runs are available yet.']);

  return (
    <div className="grid grid--2">
      <Panel title="Latest Review" accent="lime">
        <TextList items={reviewLines} />
      </Panel>
      <Panel title="Trade Context" accent="cyan">
        <TextList items={tradeContextLines(dashboard.tradeContext?.record)} />
      </Panel>
      <Panel title="Canonical Analysis" accent="amber">
        <TextList
          items={canonicalLines(dashboard.canonicalAnalysis?.snapshot)}
        />
      </Panel>
      <Panel title="Market Context Pack" accent="rose">
        <TextList
          items={marketContextLines(dashboard.marketContext?.contextPack)}
        />
      </Panel>
    </div>
  );
}

export function MemoryView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const memoryLines =
    unavailableSectionLines(dashboard.memoryExplorer, 'Memory explorer') ||
    (dashboard.memoryExplorer?.matches?.length
      ? dashboard.memoryExplorer.matches.map((match: Record<string, any>) => {
          const reason =
            match.explanation?.eligibility_reason || match.retrieval_source;
          return `${formatTimestamp(match.created_at)} | ${match.symbol} | score=${match.similarity_score} | why=${reason} | ${match.summary}`;
        })
      : ['No similar historical memories found yet.']);
  const retrievalLines =
    unavailableSectionLines(
      dashboard.retrievalInspection,
      'Retrieval inspection',
    ) ||
    (dashboard.retrievalInspection?.stages?.length
      ? dashboard.retrievalInspection.stages.flatMap(
          (stage: Record<string, any>) => {
            const firstWhy = stage.retrieval_explanations?.[0]?.explanation;
            const whyLine = firstWhy
              ? `Why: ${firstWhy.eligibility_reason || '-'} | freshness=${firstWhy.freshness || '-'} | outcome=${firstWhy.outcome_tag || '-'}`
              : `Sample: ${
                  stage.retrieved_memories?.[0] ||
                  stage.memory_notes?.[0] ||
                  'No retrieval context attached.'
                }`;
            return [
              `${stage.role} | retrieved=${stage.retrieved_memories?.length ?? 0} | why=${stage.retrieval_explanations?.length ?? 0} | trade-memory=${stage.memory_notes?.length ?? 0} | shared-bus=${stage.shared_memory_bus?.length ?? 0} | recent-runs=${stage.recent_runs?.length ?? 0}`,
              whyLine,
            ];
          },
        )
      : ['No retrieval inspection data available yet.']);

  return (
    <div className="grid grid--2">
      <Panel title="Similar Past Runs" accent="lime">
        <TextList items={memoryLines} />
      </Panel>
      <Panel title="Why This Context Was Used" accent="cyan">
        <TextList items={retrievalLines} />
      </Panel>
    </div>
  );
}

export function ChatView({
  dashboard,
  chatPersona,
  chatHistory,
  chatDraft,
  busy,
  onChatPersonaChange,
  onChatDraftChange,
  onSendChat,
}: Readonly<{
  dashboard: DashboardData;
  chatPersona: ChatPersona;
  chatHistory: Array<Record<string, string>>;
  chatDraft: string;
  busy: string | null;
  onChatPersonaChange: (value: ChatPersona) => void;
  onChatDraftChange: (value: string) => void;
  onSendChat: () => Promise<void>;
}>) {
  return (
    <div className="grid grid--2">
      <Panel title="Operator Chat" accent="lime">
        <div className="form-row">
          <label className="field-label">
            <span>Role</span>
            <select
              value={chatPersona}
              onChange={(event) =>
                onChatPersonaChange(event.target.value as ChatPersona)
              }
            >
              {CHAT_PERSONAS.map((persona) => (
                <option key={persona} value={persona}>
                  {formatChatPersona(persona)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="chat-log">
          {chatHistory.length ? (
            chatHistory.map((entry, index) => (
              <article className="chat-bubble" key={`${entry.user}-${index}`}>
                <div className="chat-bubble__meta">you</div>
                <p>{entry.user}</p>
                <div className="chat-bubble__meta">
                  {formatChatPersona(entry.persona)}
                </div>
                <p>{entry.response}</p>
              </article>
            ))
          ) : (
            <p className="empty-copy">No chat messages yet.</p>
          )}
        </div>
        <div className="composer">
          <textarea
            value={chatDraft}
            onChange={(event) => onChatDraftChange(event.target.value)}
            placeholder="Ask for a review, status, or explanation."
          />
          <button
            className="button button--solid"
            disabled={busy === 'chat'}
            onClick={() => void onSendChat()}
            type="button"
          >
            {busy === 'chat' ? 'Working...' : 'Send'}
          </button>
        </div>
      </Panel>
      <Panel title="Decision Workflow Context" accent="cyan">
        <TextList
          items={[
            `Current Stage: ${dashboard.agentActivity?.current_stage ?? '-'}`,
            `Stage Status: ${dashboard.agentActivity?.current_stage_status ?? '-'}`,
            `Stage Detail: ${dashboard.agentActivity?.current_stage_message ?? '-'}`,
            `Last Completed: ${dashboard.agentActivity?.last_completed_stage ?? '-'}`,
            `Completed Detail: ${dashboard.agentActivity?.last_completed_message ?? '-'}`,
            `Tool Roles: ${Object.keys(dashboard.tradeContext?.record?.tool_outputs || {}).join(', ') || '-'}`,
            `Memory Roles: ${Object.keys(dashboard.tradeContext?.record?.retrieved_memory_summary || {}).join(', ') || '-'}`,
          ]}
        />
      </Panel>
    </div>
  );
}

function instructionButtonLabel(
  busy: string | null,
  instructionMode: InstructionMode,
) {
  if (busy === 'instruction') {
    return 'Working...';
  }
  return instructionMode === 'apply' ? 'Apply' : 'Preview';
}

export function SettingsView({
  dashboard,
  instructionDraft,
  instructionMode,
  instructionResult,
  busy,
  onInstructionDraftChange,
  onInstructionModeChange,
  onSendInstruction,
}: Readonly<{
  dashboard: DashboardData;
  instructionDraft: string;
  instructionMode: InstructionMode;
  instructionResult: Record<string, any> | null;
  busy: string | null;
  onInstructionDraftChange: (value: string) => void;
  onInstructionModeChange: (value: InstructionMode) => void;
  onSendInstruction: () => Promise<void>;
}>) {
  const recentRunLines = dashboard.recentRuns?.runs?.length
    ? dashboard.recentRuns.runs.map(
        (run: Record<string, any>) =>
          `${formatTimestamp(run.created_at)} | ${run.symbol} | ${run.interval} | approved=${run.approved}`,
      )
    : ['No recent runs recorded yet.'];
  const instructionLines = instructionResult
    ? [
        `Summary: ${instructionResult.instruction?.summary ?? '-'}`,
        `Update Preferences: ${instructionResult.instruction?.should_update_preferences ?? false}`,
        `Requires Confirmation: ${instructionResult.instruction?.requires_confirmation ?? false}`,
        `Applied: ${instructionResult.applied ? 'yes' : 'no'}`,
        `Rationale: ${instructionResult.instruction?.rationale ?? '-'}`,
      ]
    : [
        'Type a safe operator instruction.',
        'Examples:',
        'make the system conservative',
        'switch to capital preservation',
      ];

  return (
    <div className="grid grid--2">
      <Panel title="Preferences" accent="lime">
        <KeyValueList
          items={[
            ['Regions', formatList(dashboard.preferences?.regions)],
            ['Exchanges', formatList(dashboard.preferences?.exchanges)],
            ['Currencies', formatList(dashboard.preferences?.currencies)],
            ['Sectors', formatList(dashboard.preferences?.sectors)],
            ['Risk', dashboard.preferences?.risk_profile ?? '-'],
            ['Style', dashboard.preferences?.trade_style ?? '-'],
            ['Behavior', dashboard.preferences?.behavior_preset ?? '-'],
            ['Profile', dashboard.preferences?.agent_profile ?? '-'],
            ['Tone', dashboard.preferences?.agent_tone ?? '-'],
            ['Strictness', dashboard.preferences?.strictness_preset ?? '-'],
          ]}
        />
      </Panel>
      <Panel title="Recent Runs" accent="amber">
        <TextList items={recentRunLines} />
      </Panel>
      <Panel title="Operator Instruction" accent="cyan">
        <TextList items={instructionLines} />
      </Panel>
      <Panel title="Composer" accent="rose">
        <div className="form-row">
          <label className="field-label">
            <span>Mode</span>
            <select
              value={instructionMode}
              onChange={(event) =>
                onInstructionModeChange(event.target.value as InstructionMode)
              }
            >
              <option value="preview">preview</option>
              <option value="apply">apply</option>
            </select>
          </label>
        </div>
        <div className="composer">
          <textarea
            value={instructionDraft}
            onChange={(event) => onInstructionDraftChange(event.target.value)}
            placeholder="Make the system more conservative and protective."
          />
          <button
            className="button button--solid"
            disabled={busy === 'instruction'}
            onClick={() => void onSendInstruction()}
            type="button"
          >
            {instructionButtonLabel(busy, instructionMode)}
          </button>
        </div>
      </Panel>
    </div>
  );
}

type ActiveViewProps = Readonly<{
  tab: TabId;
  dashboard: DashboardData;
  currentCycle: KeyValueItems;
  system: KeyValueItems;
  chatPersona: ChatPersona;
  chatHistory: Array<Record<string, string>>;
  chatDraft: string;
  instructionDraft: string;
  instructionMode: InstructionMode;
  instructionResult: Record<string, any> | null;
  proposalNote: string;
  busy: string | null;
  onChatPersonaChange: (value: ChatPersona) => void;
  onChatDraftChange: (value: string) => void;
  onSendChat: () => Promise<void>;
  onInstructionDraftChange: (value: string) => void;
  onInstructionModeChange: (value: InstructionMode) => void;
  onSendInstruction: () => Promise<void>;
  onToolAction: (kind: ToolActionKind) => void;
  onProposalNoteChange: (value: string) => void;
  onProposalAction: (
    kind: ProposalActionKind,
    proposalId: string,
  ) => Promise<void>;
}>;

/**
 * Renders the dashboard tab specified by `props.tab` and forwards the relevant
 * slice of state and handlers to the corresponding view component.
 *
 * @param props - Component props containing `tab`, the `dashboard` payload, UI state such as `busy`,
 *                and any view-specific handlers and data (chat, instruction, tool actions, etc.).
 * @returns The JSX element for the active tab view.
 */
export function ActiveView(props: ActiveViewProps) {
  switch (props.tab) {
    case 'overview':
      return (
        <OverviewView
          dashboard={props.dashboard}
          currentCycle={props.currentCycle}
          system={props.system}
          busy={props.busy}
          onToolAction={props.onToolAction}
        />
      );
    case 'runtime':
      return <RuntimeView dashboard={props.dashboard} />;
    case 'portfolio':
      return <PortfolioView dashboard={props.dashboard} />;
    case 'proposals':
      return (
        <ProposalDeskView
          dashboard={props.dashboard}
          busy={props.busy}
          proposalNote={props.proposalNote}
          onProposalAction={props.onProposalAction}
          onProposalNoteChange={props.onProposalNoteChange}
        />
      );
    case 'review':
      return <ReviewView dashboard={props.dashboard} />;
    case 'memory':
      return <MemoryView dashboard={props.dashboard} />;
    case 'chat':
      return (
        <ChatView
          dashboard={props.dashboard}
          chatPersona={props.chatPersona}
          chatHistory={props.chatHistory}
          chatDraft={props.chatDraft}
          busy={props.busy}
          onChatPersonaChange={props.onChatPersonaChange}
          onChatDraftChange={props.onChatDraftChange}
          onSendChat={props.onSendChat}
        />
      );
    case 'settings':
      return (
        <SettingsView
          dashboard={props.dashboard}
          instructionDraft={props.instructionDraft}
          instructionMode={props.instructionMode}
          instructionResult={props.instructionResult}
          busy={props.busy}
          onInstructionDraftChange={props.onInstructionDraftChange}
          onInstructionModeChange={props.onInstructionModeChange}
          onSendInstruction={props.onSendInstruction}
        />
      );
  }
}

/**
 * Render the operator control room UI for viewing dashboard data and interacting with runtime controls, local tools, chat, and operator instructions.
 *
 * This component manages dashboard polling and session unlocking, presents tabbed views (overview, runtime, portfolio, review, memory, chat, settings), and exposes UI-driven actions that call backend endpoints to control runtime, tools, chat, and instruction workflows.
 *
 * @returns A React element containing the tabbed operator dashboard UI with runtime/tool action controls, chat composer, instruction composer, and status/metadata panels.
 */
export function ControlRoom() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [tab, setTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    text: string;
    tone: MessageTone;
  } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [chatDraft, setChatDraft] = useState('');
  const [chatPersona, setChatPersona] =
    useState<ChatPersona>('operator_liaison');
  const [chatHistory, setChatHistory] = useState<Array<Record<string, string>>>(
    [],
  );
  const [instructionDraft, setInstructionDraft] = useState('');
  const [instructionMode, setInstructionMode] =
    useState<InstructionMode>('preview');
  const [instructionResult, setInstructionResult] = useState<Record<
    string,
    any
  > | null>(null);
  const [proposalNote, setProposalNote] = useState('');
  const [lastLoadedAt, setLastLoadedAt] = useState<string>('-');
  const [webguiToken, setWebguiToken] = useState('');
  const [authRequired, setAuthRequired] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const lastRequestSeqRef = useRef(0);
  const dashboardAbortRef = useRef<AbortController | null>(null);

  const applyDashboardPayload = useCallback((payload: DashboardData) => {
    setDashboard(payload);
    setChatHistory(normalizeChatHistory(payload));
    setLastLoadedAt(new Date().toLocaleTimeString());
    setAuthRequired(false);
    setAuthError(null);
    setError(null);
  }, []);

  const applyLatestDashboard = useCallback(
    (payload: DashboardData) => {
      lastRequestSeqRef.current += 1;
      dashboardAbortRef.current?.abort();
      dashboardAbortRef.current = null;
      applyDashboardPayload(payload);
      setLoading(false);
    },
    [applyDashboardPayload],
  );

  const loadDashboard = useCallback(async () => {
    const seq = lastRequestSeqRef.current + 1;
    lastRequestSeqRef.current = seq;
    dashboardAbortRef.current?.abort();
    const controller = new AbortController();
    dashboardAbortRef.current = controller;
    try {
      const payload = await readJson<DashboardData>('/api/dashboard', {
        signal: controller.signal,
      });
      if (controller.signal.aborted || seq !== lastRequestSeqRef.current) {
        return;
      }
      applyDashboardPayload(payload);
    } catch (nextError) {
      if (controller.signal.aborted || seq !== lastRequestSeqRef.current) {
        return;
      }
      if (nextError instanceof WebguiHttpError && nextError.status === 401) {
        setAuthRequired(true);
        setAuthError(null);
        setDashboard(null);
        return;
      }
      setError(
        nextError instanceof Error ? nextError.message : String(nextError),
      );
    } finally {
      if (dashboardAbortRef.current === controller) {
        dashboardAbortRef.current = null;
      }
      if (seq === lastRequestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [applyDashboardPayload]);
  useEffect(() => {
    const initialRefresh = setTimeout(() => {
      void loadDashboard();
    }, 0);
    const timer = setInterval(() => {
      void loadDashboard();
    }, 2500);
    return () => {
      clearTimeout(initialRefresh);
      clearInterval(timer);
      dashboardAbortRef.current?.abort();
      dashboardAbortRef.current = null;
    };
  }, [loadDashboard]);

  const unlockWebgui = useCallback(
    async (event: SyntheticEvent<HTMLFormElement>) => {
      event.preventDefault();
      const token = webguiToken.trim();
      if (!token) {
        return;
      }
      setAuthBusy(true);
      setAuthError(null);
      try {
        await authenticateWebguiSession(token);
        setWebguiToken('');
        setAuthRequired(false);
        await loadDashboard();
      } catch (nextError) {
        setAuthRequired(true);
        setAuthError(
          nextError instanceof Error ? nextError.message : String(nextError),
        );
      } finally {
        setAuthBusy(false);
      }
    },
    [loadDashboard, webguiToken],
  );

  const runAction = useCallback(
    async (kind: 'refresh' | 'start' | 'stop' | 'restart' | 'one-shot') => {
      if (kind === 'refresh') {
        setBusy('refresh');
        await loadDashboard();
        setMessage({ text: 'Dashboard refreshed.', tone: 'neutral' });
        setBusy(null);
        return;
      }
      setBusy(kind);
      try {
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/runtime', {
          method: 'POST',
          body: JSON.stringify({ kind }),
        });
        applyLatestDashboard(result.dashboard);
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        if (nextError instanceof WebguiHttpError && nextError.status === 401) {
          setAuthRequired(true);
        }
        setMessage({
          text:
            nextError instanceof Error ? nextError.message : String(nextError),
          tone: 'bad',
        });
      } finally {
        setBusy(null);
      }
    },
    [applyLatestDashboard, loadDashboard],
  );

  const runToolAction = useCallback(
    async (kind: ToolActionKind) => {
      setBusy(kind);
      try {
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/tools', {
          method: 'POST',
          body: JSON.stringify({ kind }),
        });
        applyLatestDashboard(result.dashboard);
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        if (nextError instanceof WebguiHttpError && nextError.status === 401) {
          setAuthRequired(true);
        }
        setMessage({
          text:
            nextError instanceof Error ? nextError.message : String(nextError),
          tone: 'bad',
        });
      } finally {
        setBusy(null);
      }
    },
    [applyLatestDashboard],
  );

  const runProposalAction = useCallback(
    async (kind: ProposalActionKind, proposalId: string) => {
      const reviewNotes = proposalNote.trim();
      setBusy(`proposal-${kind}`);
      try {
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/proposals', {
          method: 'POST',
          body: JSON.stringify({ kind, proposalId, reviewNotes }),
        });
        applyLatestDashboard(result.dashboard);
        setProposalNote('');
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        if (nextError instanceof WebguiHttpError && nextError.status === 401) {
          setAuthRequired(true);
        }
        setMessage({
          text:
            nextError instanceof Error ? nextError.message : String(nextError),
          tone: 'bad',
        });
      } finally {
        setBusy(null);
      }
    },
    [applyLatestDashboard, proposalNote],
  );

  const sendChat = useCallback(async () => {
    const messageText = chatDraft.trim();
    if (!messageText) {
      return;
    }
    setBusy('chat');
    try {
      await readJson<Record<string, string>>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          persona: chatPersona,
          message: messageText,
        }),
      });
      setChatDraft('');
      setMessage({ text: 'Operator reply received.', tone: 'good' });
      await loadDashboard();
    } catch (nextError) {
      if (nextError instanceof WebguiHttpError && nextError.status === 401) {
        setAuthRequired(true);
      }
      setMessage({
        text:
          nextError instanceof Error ? nextError.message : String(nextError),
        tone: 'bad',
      });
    } finally {
      setBusy(null);
    }
  }, [chatDraft, chatPersona, loadDashboard]);

  const sendInstruction = useCallback(async () => {
    const messageText = instructionDraft.trim();
    if (!messageText) {
      return;
    }
    setBusy('instruction');
    try {
      const result = await readJson<{
        result: Record<string, any>;
        dashboard: DashboardData;
      }>('/api/instruct', {
        method: 'POST',
        body: JSON.stringify({
          message: messageText,
          apply: instructionMode === 'apply',
        }),
      });
      setInstructionResult(result.result);
      applyLatestDashboard(result.dashboard);
      setInstructionDraft('');
      setMessage({
        text:
          instructionMode === 'apply'
            ? 'Preferences updated from operator instruction.'
            : 'Instruction preview ready.',
        tone: 'good',
      });
    } catch (nextError) {
      if (nextError instanceof WebguiHttpError && nextError.status === 401) {
        setAuthRequired(true);
      }
      setMessage({
        text:
          nextError instanceof Error ? nextError.message : String(nextError),
        tone: 'bad',
      });
    } finally {
      setBusy(null);
    }
  }, [applyLatestDashboard, instructionDraft, instructionMode]);

  const currentCycle = useMemo<KeyValueItems>(
    () => [
      ['Runtime', dashboard?.status?.runtime_state ?? '-'],
      [
        'Mode',
        dashboard?.status?.runtime_mode ??
          dashboard?.doctor?.runtime_mode ??
          '-',
      ],
      ['Current Symbol', dashboard?.status?.state?.current_symbol ?? '-'],
      ['Cycle Count', String(dashboard?.status?.state?.cycle_count ?? '-')],
      ['Status', dashboard?.status?.status_message ?? '-'],
      ['Current Stage', dashboard?.agentActivity?.current_stage ?? '-'],
      ['Stage Status', dashboard?.agentActivity?.current_stage_status ?? '-'],
      [
        'Last Outcome',
        dashboard?.agentActivity?.last_outcome_message ??
          'Waiting for a completed symbol or service result.',
      ],
    ],
    [dashboard],
  );

  const system = useMemo<KeyValueItems>(
    () => systemStatusItems(dashboard),
    [dashboard],
  );

  const activeView = dashboard ? (
    <ActiveView
      tab={tab}
      dashboard={dashboard}
      currentCycle={currentCycle}
      system={system}
      chatPersona={chatPersona}
      chatHistory={chatHistory}
      chatDraft={chatDraft}
      instructionDraft={instructionDraft}
      instructionMode={instructionMode}
      instructionResult={instructionResult}
      proposalNote={proposalNote}
      busy={busy}
      onChatPersonaChange={setChatPersona}
      onChatDraftChange={setChatDraft}
      onSendChat={sendChat}
      onInstructionDraftChange={setInstructionDraft}
      onInstructionModeChange={setInstructionMode}
      onSendInstruction={sendInstruction}
      onToolAction={(kind) => void runToolAction(kind)}
      onProposalNoteChange={setProposalNote}
      onProposalAction={runProposalAction}
    />
  ) : null;
  const content = (() => {
    if (loading) {
      return <div className="loading">Loading dashboard...</div>;
    }
    if (dashboard) {
      return activeView;
    }
    return <div className="loading">Dashboard unavailable.</div>;
  })();

  if (authRequired) {
    return (
      <div className="auth-shell">
        <WebguiTokenPrompt
          busy={authBusy}
          error={authError}
          onSubmit={unlockWebgui}
          onTokenChange={setWebguiToken}
          token={webguiToken}
        />
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__eyebrow">Local-first control room</div>
          <div className="sidebar__title">Agentic Trader</div>
          <div className="sidebar__subtitle">
            Paper-first. Strict. Inspectable.
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="Sections">
          {tabs.map((item) => (
            <button
              className={cx(
                'nav-button',
                item.id === tab && 'nav-button--active',
              )}
              key={item.id}
              onClick={() => setTab(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar__meta">
          <div>Runtime: {dashboard?.status?.runtime_state ?? '-'}</div>
          <div>
            Mode:{' '}
            {dashboard?.status?.runtime_mode ??
              dashboard?.doctor?.runtime_mode ??
              '-'}
          </div>
          <div>Backend: {dashboard?.broker?.backend ?? '-'}</div>
          <div>Last refresh: {lastLoadedAt}</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar__status">
            <span className="topbar__headline">
              {tabs.find((item) => item.id === tab)?.label}
            </span>
            <span className="chip">
              {dashboard?.status?.runtime_mode ??
                dashboard?.doctor?.runtime_mode ??
                '-'}
            </span>
            <span className="chip">
              {dashboard?.broker?.execution_mode ?? '-'}
            </span>
            <span className="chip">
              {dashboard?.broker?.message ?? 'runtime unavailable'}
            </span>
          </div>
          <div className="topbar__actions">
            <button
              className="button"
              onClick={() => void runAction('refresh')}
              type="button"
            >
              Refresh
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => void runAction('one-shot')}
              type="button"
            >
              One Shot
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => void runAction('start')}
              type="button"
            >
              Start
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => void runAction('stop')}
              type="button"
            >
              Stop
            </button>
            <button
              className="button"
              disabled={busy !== null}
              onClick={() => void runAction('restart')}
              type="button"
            >
              Restart
            </button>
          </div>
        </header>

        {message ? (
          <div className={cx('banner', `banner--${message.tone}`)}>
            {message.text}
          </div>
        ) : null}
        {error ? <div className="banner banner--bad">{error}</div> : null}

        {content}
      </main>
    </div>
  );
}
