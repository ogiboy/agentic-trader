/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
'use client';

import Image from 'next/image';
import {
  CheckCircle2,
  Power,
  RefreshCw,
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
import {
  accountCurrency,
  canonicalLines,
  cx,
  formatList,
  formatNumber,
  formatPercent,
  formatTimestamp,
  localToolLines,
  marketContextLines,
  marketLensImage,
  normalizeChatHistory,
  positionPlanCoverageLines,
  proposalApprovalBlockedReason,
  proposalHeadline,
  proposalLines,
  providerWarningLines,
  readinessLines,
  systemStatusItems,
  tabs,
  tradeContextLines,
  unavailableSectionLines,
} from './control-room.helpers';
import type {
  DashboardData,
  InstructionMode,
  KeyValueItems,
  MessageTone,
  PanelAccent,
  ProposalActionKind,
  TabId,
  ToolActionKind,
} from './control-room.helpers';

export {
  canonicalLines,
  failedCheckNames,
  formatList,
  formatNumber,
  formatPercent,
  formatSourceHealthCount,
  formatTimestamp,
  localToolLines,
  marketContextLines,
  normalizeChatHistory,
  positionPlanCoverageLines,
  proposalHeadline,
  proposalLines,
  providerWarningLines,
  readinessLines,
  sourceHealthSummaryLine,
  systemStatusItems,
  tradeContextLines,
  unavailableSectionLines,
} from './control-room.helpers';
export type {
  DashboardData,
  InstructionMode,
  KeyValueItems,
  MessageTone,
  PanelAccent,
  ProposalActionKind,
  TabId,
  ToolActionKind,
} from './control-room.helpers';

export class WebguiHttpError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'WebguiHttpError';
    this.status = status;
  }
}

type DashboardRequestContext = {
  controller: AbortController;
  seq: number;
};

/**
 * Checks whether a dashboard request corresponds to the current active request.
 *
 * @param request - The in-flight dashboard request context containing an AbortController and sequence number
 * @param latestSeq - The most recent request sequence number to compare against
 * @returns `true` if the request's abort signal is not aborted and its sequence equals `latestSeq`, `false` otherwise
 */
function isDashboardRequestCurrent(
  request: DashboardRequestContext,
  latestSeq: number,
): boolean {
  return !request.controller.signal.aborted && request.seq === latestSeq;
}

/**
 * Convert an unknown error value into a human-readable message.
 *
 * @param error - The error value to format; may be an `Error` or any other value.
 * @returns The `message` property when `error` is an `Error`, otherwise `String(error)`.
 */
function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
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
              disabled={
                busy !== null ||
                dashboard.camofoxService?.access_key_configured === false
              }
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

/**
 * Render the Portfolio tab panels showing portfolio metrics, risk report, trade journal, exit plan coverage, preferences, and desk accounting notes.
 *
 * @param dashboard - Dashboard payload used to populate portfolio, risk, journal, preferences, and accounting displays
 * @returns A React element containing the portfolio-related panels and their contents
 */
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
      <Panel title="Exit Plan Coverage" accent="rose">
        <TextList items={positionPlanCoverageLines(dashboard)} />
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

/**
 * Render the Proposal Desk panel with proposal cards, a review-note composer, and safety metadata.
 *
 * The panel lists up to six proposals and exposes action buttons for approve, reject, reconcile, and refresh.
 * Action buttons are enabled only when the proposal's status and required metadata allow it and a non-empty
 * review note is present where the UI requires one.
 *
 * @param dashboard - Full dashboard payload used to derive proposals, availability flags, and broker safety fields
 * @param busy - Current busy token that disables interactive buttons when non-null
 * @param proposalNote - Current text of the review note composer; trimmed emptiness gates certain actions
 * @param onProposalNoteChange - Called with the updated proposal note when the composer textarea changes
 * @param onProposalAction - Invoked to perform a proposal action; receives the action kind and the target proposal ID
 * @returns The Proposal Desk React element
 */
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
  const hasProposalNote = Boolean(proposalNote.trim());

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
                  const canApprove =
                    isPending && !approvalBlockedReason && hasProposalNote;
                  const canReconcile =
                    proposal.status === 'approved' &&
                    Boolean(proposal.execution_intent_id) &&
                    hasProposalNote;
                  const canRefresh =
                    (proposal.status === 'approved' ||
                      proposal.status === 'executed') &&
                    proposal.execution_outcome_status === 'accepted' &&
                    Boolean(proposal.execution_order_id) &&
                    hasProposalNote;
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
                            !isPending || Boolean(busy) || !hasProposalNote
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
                        <button
                          className="button"
                          disabled={!canRefresh || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('refresh', proposalId)
                          }
                          title="Refresh accepted broker order without resubmitting"
                          type="button"
                        >
                          <RefreshCw aria-hidden size={16} />
                          Refresh
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : null}
            <div className="composer">
              <textarea
                onChange={(event) => onProposalNoteChange(event.target.value)}
                placeholder="Review note required for approve, reject, reconcile, or refresh."
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
            ['External Paper', dashboard.broker?.external_paper ? 'yes' : 'no'],
            ['Live Requested', dashboard.broker?.live_requested ? 'yes' : 'no'],
            [
              'Kill Switch',
              dashboard.broker?.kill_switch_active ? 'on' : 'off',
            ],
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
 * Operator control room UI component for viewing dashboard data and controlling runtime, local tools, chat, and operator instructions.
 *
 * Handles polling the dashboard, same-origin WebGUI token unlocking, and exposes tabbed views (overview, runtime, portfolio, proposals, review, memory, chat, settings) with actions that invoke backend endpoints.
 *
 * @returns A React element containing the tabbed operator dashboard UI and its runtime/tool/chat/instruction controls
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
  const busyRef = useRef<string | null>(null);
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

  const selectTab = useCallback((nextTab: TabId) => {
    setTab(nextTab);
    setError(null);
    setMessage(null);
  }, []);

  const setBusyState = useCallback((nextBusy: string | null) => {
    busyRef.current = nextBusy;
    setBusy(nextBusy);
  }, []);

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

  const beginDashboardRequest = useCallback(
    (force: boolean): DashboardRequestContext | null => {
      if (!force && busyRef.current) {
        return null;
      }
      const activeRequest = dashboardAbortRef.current;
      if (activeRequest && !activeRequest.signal.aborted) {
        if (!force) {
          return null;
        }
        activeRequest.abort();
      }
      const seq = lastRequestSeqRef.current + 1;
      lastRequestSeqRef.current = seq;
      const controller = new AbortController();
      dashboardAbortRef.current = controller;
      return { controller, seq };
    },
    [],
  );

  const completeDashboardRequest = useCallback(
    ({ controller, seq }: DashboardRequestContext) => {
      if (dashboardAbortRef.current === controller) {
        dashboardAbortRef.current = null;
      }
      if (seq === lastRequestSeqRef.current) {
        setLoading(false);
      }
    },
    [],
  );

  const loadDashboard = useCallback(
    async ({ force = false }: { force?: boolean } = {}) => {
      const request = beginDashboardRequest(force);
      if (!request) {
        return;
      }
      try {
        const payload = await readJson<DashboardData>('/api/dashboard', {
          signal: request.controller.signal,
        });
        if (!isDashboardRequestCurrent(request, lastRequestSeqRef.current)) {
          return;
        }
        applyDashboardPayload(payload);
      } catch (nextError) {
        if (!isDashboardRequestCurrent(request, lastRequestSeqRef.current)) {
          return;
        }
        if (nextError instanceof WebguiHttpError && nextError.status === 401) {
          setAuthRequired(true);
          setAuthError(null);
          setDashboard(null);
          return;
        }
        setError(errorMessage(nextError));
      } finally {
        completeDashboardRequest(request);
      }
    },
    [applyDashboardPayload, beginDashboardRequest, completeDashboardRequest],
  );
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
        await loadDashboard({ force: true });
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
        setBusyState('refresh');
        await loadDashboard({ force: true });
        setMessage({ text: 'Dashboard refreshed.', tone: 'neutral' });
        setBusyState(null);
        return;
      }
      setBusyState(kind);
      dashboardAbortRef.current?.abort();
      dashboardAbortRef.current = null;
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
        setBusyState(null);
      }
    },
    [applyLatestDashboard, loadDashboard, setBusyState],
  );

  const runToolAction = useCallback(
    async (kind: ToolActionKind) => {
      setBusyState(kind);
      dashboardAbortRef.current?.abort();
      dashboardAbortRef.current = null;
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
        setBusyState(null);
      }
    },
    [applyLatestDashboard, setBusyState],
  );

  const runProposalAction = useCallback(
    async (kind: ProposalActionKind, proposalId: string) => {
      const reviewNotes = proposalNote.trim();
      setBusyState(`proposal-${kind}`);
      dashboardAbortRef.current?.abort();
      dashboardAbortRef.current = null;
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
        setBusyState(null);
      }
    },
    [applyLatestDashboard, proposalNote, setBusyState],
  );

  const sendChat = useCallback(async () => {
    const messageText = chatDraft.trim();
    if (!messageText) {
      return;
    }
    setBusyState('chat');
    dashboardAbortRef.current?.abort();
    dashboardAbortRef.current = null;
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
      await loadDashboard({ force: true });
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
      setBusyState(null);
    }
  }, [chatDraft, chatPersona, loadDashboard, setBusyState]);

  const sendInstruction = useCallback(async () => {
    const messageText = instructionDraft.trim();
    if (!messageText) {
      return;
    }
    setBusyState('instruction');
    dashboardAbortRef.current?.abort();
    dashboardAbortRef.current = null;
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
      setBusyState(null);
    }
  }, [applyLatestDashboard, instructionDraft, instructionMode, setBusyState]);

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
              onClick={() => selectTab(item.id)}
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
