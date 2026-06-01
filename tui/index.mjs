import { Box, Text, useApp, useInput } from 'ink';
import { execFile } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  dashboardPages as pages,
  dashboardStatusLine,
  dashboardTitle,
  formatPersona,
  rotateInstructionMode,
  rotatePersona,
} from './copy.mjs';
import {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  getSupervisorLogLines,
} from './dashboard-defaults.mjs';
import {
  handleChatInput,
  handleDashboardInput,
  handleGlobalInput,
  handleSettingsInput,
} from './input.mjs';
import {
  failedCheckNames,
  formatMarketSession,
  formatMarketSessionWithTradable,
  formatMTFSnapshot,
  getAgentEventLines,
  getCurrentCycleLines,
  getExplorerLines,
  getInspectionLines,
  getInstructionResultLines,
  getJournalLines,
  getMarketContextLines,
  getRecentRunsLines,
  getReplayLines,
  getReviewLines,
  getStatusBorderColor,
  getSystemLines,
  getTraceLines,
  getTradeContextLines,
  overviewRuntimeMode,
  providerLines,
  readinessLines,
  renderLinesFallback,
  renderUnavailableMessage,
  sourceHealthSummaryLine,
} from './line-formatters.mjs';
import { getCanonicalAnalysisLines } from './review-lines.mjs';

const execFileAsync = promisify(execFile);
const e = React.createElement;
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;
const once = process.argv.includes('--once');
const projectRoot = fileURLToPath(new URL('..', import.meta.url));

/**
 * Execute the Agentic Trader CLI using one of the configured executables, retrying across candidates.
 *
 * Attempts to run either the configured Python module invocation or the standalone CLI binary (whichever are available), returning parsed JSON when requested or the raw stdout/stderr pair otherwise.
 *
 * @param {string[]} args - Command-line arguments to pass to the CLI.
 * @param {{ expectJson?: boolean }} [options] - Execution options.
 * @param {boolean} [options.expectJson=false] - If true, parse and return stdout as JSON.
 * @returns {any|{stdout: string, stderr: string}} Parsed JSON when `expectJson` is true; otherwise an object containing `stdout` and `stderr`.
 * @throws Will re-throw a non-ENOENT child-process error immediately, or throw the last captured error (or a generic error) if no candidate executable could be run.
 */
async function execCli(args, { expectJson = false } = {}) {
  const attempts = [];
  if (pythonExecutable) {
    attempts.push([pythonExecutable, ['-m', 'agentic_trader.cli', ...args]]);
  }
  if (cliExecutable) {
    attempts.push([cliExecutable, args]);
  }

  let lastError;
  for (const [command, commandArgs] of attempts) {
    try {
      const { stdout, stderr } = await execFileAsync(command, commandArgs, {
        cwd: projectRoot,
        env: process.env,
        maxBuffer: 1024 * 1024 * 8,
      });
      return expectJson ? JSON.parse(stdout) : { stdout, stderr };
    } catch (error) {
      lastError = error;
      if (error && typeof error === 'object' && error.code !== 'ENOENT') {
        throw error;
      }
    }
  }

  throw lastError || new Error('No CLI command could be executed.');
}

async function runJsonCommand(args) {
  return execCli(args, { expectJson: true });
}

async function runTextCommand(args) {
  return execCli(args, { expectJson: false });
}

/**
 * Perform a runtime control action based on the provided dashboard snapshot and return a user-facing message about the outcome.
 *
 * @param {string} kind - Action to perform: "start", "stop", "one-shot", or other (treated as a restart when a saved launch configuration exists).
 * @param {Object} data - Dashboard snapshot containing runtime `status` and `preferences` used to determine behavior.
 * @returns {{kind: string, text: string}} An action message: `kind` is a message level (e.g., `'info'`), and `text` explains the outcome or reason no action was taken.
 */
async function performRuntimeAction(kind, data) {
  if (kind === 'start') {
    if (data.status.live_process) {
      return {
        kind: 'info',
        text: `Runtime already active with PID ${data.status.state?.pid ?? '-'}.`,
      };
    }
    const symbols = defaultSymbolsFromPreferences(data.preferences);
    await runTextCommand([
      'launch',
      '--symbols',
      symbols,
      '--interval',
      '1d',
      '--lookback',
      '180d',
      '--continuous',
      '--background',
      '--poll-seconds',
      '300',
    ]);
    return {
      kind: 'info',
      text: `Background runtime launch requested for ${symbols}.`,
    };
  }

  if (kind === 'stop') {
    if (!data.status.state?.pid) {
      return { kind: 'info', text: 'No managed runtime is currently active.' };
    }
    await runTextCommand(['stop-service']);
    return {
      kind: 'info',
      text: `Stop requested for PID ${data.status.state.pid}.`,
    };
  }

  if (kind === 'one-shot') {
    if (data.status.live_process) {
      return {
        kind: 'info',
        text: `Runtime already active with PID ${data.status.state?.pid ?? '-'}. Stop it before running a one-shot cycle.`,
      };
    }
    const symbol = defaultSingleSymbol(data);
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await runTextCommand([
      'run',
      '--symbol',
      symbol,
      '--interval',
      interval,
      '--lookback',
      lookback,
    ]);
    return {
      kind: 'info',
      text: `Strict one-shot cycle completed for ${symbol} (${interval}, ${lookback}).`,
    };
  }

  if ((data.status.state?.symbols || []).length) {
    await runTextCommand(['restart-service']);
    return { kind: 'info', text: 'Background runtime restart requested.' };
  }
  return {
    kind: 'info',
    text: 'No saved runtime launch config is available yet.',
  };
}

/**
 * Fetches the dashboard snapshot and records the retrieval time.
 *
 * @returns {object} The dashboard snapshot augmented with a `loadedAt` ISO 8601 timestamp string.
 */
async function loadDashboard() {
  const payload = await runJsonCommand([
    'dashboard-snapshot',
    '--log-limit',
    '14',
  ]);
  return {
    ...payload,
    loadedAt: new Date().toISOString(),
  };
}

/**
 * Return the UI component element for the given dashboard page key.
 *
 * @param {Object} options - View selection and page state.
 * @param {string} options.page - Page key: 'overview', 'runtime', 'portfolio', 'review', 'memory', 'settings', or other (defaults to chat).
 * @param {Object} options.data - Dashboard snapshot and related data passed into the page component.
 * @param {{persona: string, history: Array<Object>, draft: string, busy: boolean}} options.chat - Chat page state.
 * @param {{draft: string, busy: boolean, mode: string, result: Object|null}} options.instruction - Settings page state.
 * @param {boolean} options.compact - Whether to render pages in compact mode (affects applicable pages).
 * @returns {import('react').ReactElement} The page element corresponding to `page`; unknown keys render the Chat page.
 */
function getPageView({ page, data, chat, instruction, compact }) {
  switch (page) {
    case 'overview':
      return e(OverviewPage, { data, compact });
    case 'runtime':
      return e(RuntimePage, { data });
    case 'portfolio':
      return e(PortfolioPage, { data });
    case 'review':
      return e(ReviewPage, { data });
    case 'memory':
      return e(MemoryPage, { data });
    case 'settings':
      return e(SettingsPage, {
        data,
        draft: instruction.draft,
        instructionBusy: instruction.busy,
        instructionMode: instruction.mode,
        instructionResult: instruction.result,
        compact,
      });
    default:
      return e(ChatPage, {
        data,
        persona: chat.persona,
        history: chat.history,
        draft: chat.draft,
        chatBusy: chat.busy,
      });
  }
}

/**
 * Render a bordered panel with a bold colored title and a list of text lines.
 *
 * @param {string} title - The panel title shown in bold at the top.
 * @param {Array<any>} lines - Lines to display inside the panel; each item will be converted to a string.
 * @param {string} [borderColor='cyan'] - Color used for the panel border and title text.
 * @returns {import('react').ReactElement} The Ink Box element containing the titled panel and its lines.
 */
function panel(title, lines, borderColor = 'cyan') {
  return e(
    Box,
    {
      flexDirection: 'column',
      borderStyle: 'round',
      borderColor,
      paddingX: 1,
      paddingY: 0,
      width: '100%',
    },
    e(Text, { color: borderColor, bold: true }, title),
    ...lines.map((line, index) =>
      e(Text, { key: `${title}-${index}`, wrap: 'truncate-end' }, String(line)),
    ),
  );
}

/**
 * Render the Overview dashboard page showing runtime status, system information, and recent agent activity.
 * @param {object} props
 * @param {object} props.data - Dashboard snapshot used to populate panels; expected to include keys such as `doctor`, `status`, `preferences`, `calendar`, `broker`, `marketCache`, `marketContext`, `review`, and `agentActivity`.
 * @returns {import('react').ReactElement} The Ink/React element tree for the Overview page.
 */
function OverviewPage({ data, compact = false }) {
  const doctor = data.doctor;
  const runtime = data.status;
  const agentActivity = data.agentActivity;
  const agentEvents = agentActivity?.recent_stage_events || [];
  const currentCycleLines = getCurrentCycleLines(data, compact);
  const systemLines = getSystemLines(data, compact);

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel(
          'CURRENT CYCLE',
          currentCycleLines,
          getStatusBorderColor(runtime.runtime_state),
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'SYSTEM',
          systemLines,
          doctor.ollama_reachable && doctor.model_available ? 'green' : 'red',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('READINESS GATES', readinessLines(data), 'red'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('PROVIDER WARNINGS', providerLines(data), 'yellow'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('AGENT ACTIVITY', getAgentEventLines(agentEvents), 'magenta'),
      ),
    ),
  );
}

/**
 * Render the Runtime page with runtime status, supervisor/stage flow, and recent events.
 *
 * @param {Object} data - Dashboard snapshot containing runtime and related information.
 *   Expected properties: `status`, `supervisor`, `broker`, `logs`, `agentActivity`,
 *   `review`, `calendar`, and `marketCache`.
 * @returns {import('react').ReactElement} The Ink component tree for the Runtime page.
 */
function RuntimePage({ data }) {
  const runtime = data.status;
  const supervisor = data.supervisor;
  const broker = data.broker;
  const events = data.logs;
  const agentActivity = data.agentActivity;
  const reviewRecord = data.review.record;
  const calendar = data.calendar;
  const marketCache = data.marketCache;
  const latestSnapshot = reviewRecord?.artifacts?.snapshot;
  const recentSummary =
    reviewRecord?.artifacts?.review?.summary ||
    'No persisted review summary yet.';

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel(
          'RUNTIME STATE',
          [
            `Runtime: ${runtime.runtime_state}`,
            `Mode: ${runtime.runtime_mode ?? runtime.state?.runtime_mode ?? data.doctor?.runtime_mode ?? '-'}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `State: ${runtime.state?.state ?? '-'}`,
            `Symbols: ${(runtime.state?.symbols || []).join(', ') || '-'}`,
            `Interval: ${runtime.state?.interval ?? '-'}`,
            `Lookback: ${runtime.state?.lookback ?? '-'}`,
            `Max Cycles: ${runtime.state?.max_cycles ?? '-'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `PID: ${runtime.state?.pid ?? '-'}`,
            `Updated: ${runtime.state?.updated_at ?? '-'}`,
            `Heartbeat Age: ${runtime.age_seconds ?? '-'}s`,
            `Stop Requested: ${runtime.state?.stop_requested ?? false}`,
            `Background Mode: ${runtime.state?.background_mode ?? false}`,
            `Launch Count: ${runtime.state?.launch_count ?? 0}`,
            `Restart Count: ${runtime.state?.restart_count ?? 0}`,
            `Last Terminal State: ${runtime.state?.last_terminal_state ?? '-'}`,
            `Last Terminal At: ${runtime.state?.last_terminal_at ?? '-'}`,
            `Message: ${runtime.state?.message ?? '-'}`,
            `Current Stage: ${agentActivity?.current_stage ?? '-'}`,
            `Stage Status: ${agentActivity?.current_stage_status ?? '-'}`,
            `Stage Detail: ${agentActivity?.current_stage_message ?? '-'}`,
            `Last Completed Stage: ${agentActivity?.last_completed_stage ?? '-'}`,
            `Last Completed Detail: ${agentActivity?.last_completed_message ?? '-'}`,
            `Broker Backend: ${broker?.backend ?? '-'}`,
            `Broker State: ${broker?.state ?? '-'}`,
            `External Paper: ${broker?.external_paper ?? false}`,
            `Kill Switch: ${broker?.kill_switch_active ?? false}`,
            `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
            `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
            `MTF Alignment: ${latestSnapshot?.mtf_alignment ?? '-'}`,
            `Higher Timeframe: ${latestSnapshot?.higher_timeframe ?? '-'}`,
            `Market Session: ${formatMarketSessionWithTradable(calendar.session)}`,
            `Snapshot Cache Mode: ${marketCache.mode}`,
            `Cached Snapshots: ${marketCache.count}`,
          ],
          'cyan',
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'SUPERVISOR / STAGE FLOW',
          [
            `Stdout Tail Lines: ${supervisor?.stdout_tail?.length ?? 0}`,
            `Stderr Tail Lines: ${supervisor?.stderr_tail?.length ?? 0}`,
            `Stdout Log: ${runtime.state?.stdout_log_path ?? '-'}`,
            `Stderr Log: ${runtime.state?.stderr_log_path ?? '-'}`,
            '',
            ...(agentActivity?.stage_statuses?.length
              ? agentActivity.stage_statuses.map(
                  (stage) =>
                    `${stage.stage}: ${stage.status} | ${stage.message}`,
                )
              : ['No stage flow recorded yet.']),
            '',
            `Latest Review Available: ${data.review.available !== false && reviewRecord ? 'yes' : 'no'}`,
            `Latest Review Summary: ${recentSummary}`,
            '',
            ...readinessLines(data),
            '',
            ...getSupervisorLogLines(supervisor),
          ],
          'green',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel(
          'RUNTIME EVENTS',
          events.length
            ? events.map(
                (event) =>
                  `${event.created_at} | ${event.level} | ${event.event_type} | ${event.symbol ?? '-'} | ${event.message}`,
              )
            : ['No runtime events recorded yet.'],
          'yellow',
        ),
      ),
    ),
  );
}

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

/**
 * Render the Review page with panels for run review, agent trace, memory-aware replay, trade context, and market context.
 *
 * @param {{ data: { review: Object, trace: Object, replay: Object, tradeContext: Object, marketContext: Object, canonicalAnalysis: Object } }} props
 * @param {Object} props.data - Dashboard snapshot subsets used to populate panels.
 *   Expected keys:
 *     - review: { available?: boolean, record?: Object, error?: string }
 *     - trace: { available?: boolean, record?: Object, error?: string }
 *     - replay: { available?: boolean, replay?: Object, error?: string }
 *     - tradeContext: Object
 *     - marketContext: Object
 *     - canonicalAnalysis: Object
 * @returns {import('react').ReactElement} An Ink layout containing review, trace, replay, trade-context, and market-context panels.
 */
function ReviewPage({ data }) {
  const review = data.review;
  const trace = data.trace;
  const replay = data.replay;
  const tradeContext = data.tradeContext;
  const marketContext = data.marketContext;
  const canonicalAnalysis = data.canonicalAnalysis;
  const reviewRecord = review.record;
  const traceRecord = trace.record;
  const replayState = replay.replay;

  const reviewLines =
    review.available === false
      ? renderUnavailableMessage(review.error)
      : getReviewLines(reviewRecord);

  const traceLines =
    trace.available === false
      ? renderUnavailableMessage(trace.error)
      : getTraceLines(traceRecord);

  const replayLines =
    replay.available === false
      ? renderUnavailableMessage(replay.error)
      : getReplayLines(replayState);

  const tradeContextLines = getTradeContextLines(tradeContext);
  const marketContextLines = getMarketContextLines(marketContext);
  const canonicalAnalysisLines = getCanonicalAnalysisLines(canonicalAnalysis);

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('LATEST RUN REVIEW', reviewLines, 'green'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('AGENT TRACE', traceLines.slice(0, 8), 'magenta'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('MEMORY-AWARE REPLAY', replayLines, 'yellow'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('TRADE CONTEXT', tradeContextLines, 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('MARKET CONTEXT PACK', marketContextLines, 'blue'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('CANONICAL ANALYSIS', canonicalAnalysisLines, 'blue'),
      ),
    ),
  );
}

/**
 * Render the Memory page containing a "Similar Memories" panel and a "Retrieval Inspection" panel.
 *
 * @param {Object} data - Dashboard snapshot payload for this page.
 * @param {Object} data.memoryExplorer - Explorer results used to populate the "Similar Memories" panel; may include `available` and `error`.
 * @param {Object} data.retrievalInspection - Inspection results used to populate the "Retrieval Inspection" panel; may include `available` and `error`.
 * @returns {import('react').ReactElement} An Ink layout Box containing two side-by-side panels with memory matches and retrieval inspection lines.
 */
function MemoryPage({ data }) {
  const explorer = data.memoryExplorer;
  const inspection = data.retrievalInspection;

  const matchLines =
    explorer.available === false
      ? renderUnavailableMessage(explorer.error)
      : getExplorerLines(explorer);

  const retrievalLines =
    inspection.available === false
      ? renderUnavailableMessage(inspection.error)
      : getInspectionLines(inspection);

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('SIMILAR PAST RUNS', matchLines.slice(0, 10), 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'WHY THIS CONTEXT WAS USED',
          retrievalLines.slice(0, 12),
          'yellow',
        ),
      ),
    ),
  );
}

/**
 * Render the Settings page composed of Preferences, Recent Runs, Operator Instruction, and Composer panels.
 *
 * @param {Object} params - Component props.
 * @param {Object} params.data - Dashboard snapshot containing preferences and recentRuns used to populate panels.
 * @param {string} params.draft - Current instruction draft text shown in the composer.
 * @param {boolean} params.instructionBusy - Whether an instruction submit is in progress; displays a working indicator when true.
 * @param {'preview'|'apply'} params.instructionMode - Current instruction mode; shown in the composer header.
 * @param {Object|null} params.instructionResult - Result object from the last instruction invocation used to render the Operator Instruction panel.
 * @param {boolean} [params.compact=false] - When true, render condensed preference/recent-run summaries for tighter layouts.
 * @returns {React.Element} The Settings page React element tree.
 */
function SettingsPage({
  data,
  draft,
  instructionBusy,
  instructionMode,
  instructionResult,
  compact = false,
}) {
  const preferences = data.preferences;
  const recentRuns = data.recentRuns;
  const rawPreferenceLines = renderLinesFallback(
    'PREFERENCES',
    preferences.available,
    preferences.error,
    'Preferences are temporarily unavailable.',
  ) || [
    `Regions: ${(preferences.regions || []).join(', ') || '-'}`,
    `Exchanges: ${(preferences.exchanges || []).join(', ') || '-'}`,
    `Currencies: ${(preferences.currencies || []).join(', ') || '-'}`,
    `Sectors: ${(preferences.sectors || []).join(', ') || '-'}`,
    `Risk: ${preferences.risk_profile}`,
    `Style: ${preferences.trade_style}`,
    `Behavior: ${preferences.behavior_preset}`,
    `Agent Profile: ${preferences.agent_profile}`,
    `Agent Tone: ${preferences.agent_tone}`,
    `Strictness: ${preferences.strictness_preset}`,
    `Intervention: ${preferences.intervention_style}`,
    `Notes: ${preferences.notes || '-'}`,
  ];
  const preferenceLines =
    compact && preferences.available !== false
      ? [
          `Regions / Exchanges: ${(preferences.regions || []).join(', ') || '-'} / ${(preferences.exchanges || []).join(', ') || '-'}`,
          `Currencies / Sectors: ${(preferences.currencies || []).join(', ') || '-'} / ${(preferences.sectors || []).join(', ') || '-'}`,
          `Risk / Style: ${preferences.risk_profile} / ${preferences.trade_style}`,
          `Behavior / Strictness: ${preferences.behavior_preset} / ${preferences.strictness_preset}`,
          `Profile / Tone: ${preferences.agent_profile} / ${preferences.agent_tone}`,
          `Intervention: ${preferences.intervention_style}`,
          `Notes: ${preferences.notes || '-'}`,
        ]
      : rawPreferenceLines;
  const recentRunLines = getRecentRunsLines(recentRuns);
  const instructionLines = getInstructionResultLines(instructionResult);
  const composerLines = [
    `Mode: ${instructionMode}`,
    instructionBusy ? 'Working...' : 'Enter submit  |  [ ] switch mode',
    draft || '(type a safe operator instruction here)',
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
        panel(
          'PREFERENCES',
          preferenceLines.slice(0, compact ? 7 : 12),
          'blue',
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'RECENT RUNS',
          recentRunLines.slice(0, compact ? 5 : 8),
          'yellow',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('OPERATOR INSTRUCTION', instructionLines, 'green'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(Box, { width: '100%' }, panel('COMPOSER', composerLines, 'magenta')),
    ),
  );
}

/**
 * Render the chat page of the dashboard showing operator chat, live agent activity, reasoning/tools, and the composer.
 *
 * Renders panels for operator chat (persona, input instructions, status, and recent history), live agent activity (stage/status details), a reasoning/tools summary derived from trade context and review, and the composer draft.
 * @param {object} props
 * @param {object} props.data - Dashboard snapshot containing agentActivity, tradeContext, and review used to build display lines.
 * @param {string} props.persona - Currently selected chat persona.
 * @param {Array<object>} props.history - Chat history entries in UI order; each entry should include `user`, `persona`, and `response`.
 * @param {string} props.draft - Current composer draft text.
 * @param {boolean} props.chatBusy - Whether a chat send is in progress; affects the operator chat status line.
 * @returns {import('react').ReactElement} The Ink component tree for the chat page.
 */
function ChatPage({ data, persona, history, draft, chatBusy }) {
  const agentActivity = data?.agentActivity || {};
  const tradeContext = data?.tradeContext || {};
  const review = data?.review || {};

  const activityLines = [
    `Current Stage: ${agentActivity.current_stage ?? '-'}`,
    `Stage Status: ${agentActivity.current_stage_status ?? '-'}`,
    `Stage Detail: ${agentActivity.current_stage_message ?? '-'}`,
    `Last Completed: ${agentActivity.last_completed_stage ?? '-'}`,
    `Completed Detail: ${agentActivity.last_completed_message ?? '-'}`,
    `Outcome Type: ${agentActivity.last_outcome_type ?? '-'}`,
    `Outcome: ${agentActivity.last_outcome_message ?? 'Waiting for a completed symbol or service result.'}`,
  ];

  const tradeRecord =
    tradeContext.available === false ? null : tradeContext.record;
  const reviewRecord = review.available === false ? null : review.record;
  const toolRoles = tradeRecord
    ? Object.keys(tradeRecord.tool_outputs || {})
    : [];
  const memoryRoles = tradeRecord
    ? Object.keys(tradeRecord.retrieved_memory_summary || {})
    : [];
  const reviewWarnings = reviewRecord?.artifacts?.review?.warnings || [];

  const reasoningLines = [
    `Tool Roles: ${toolRoles.join(', ') || '-'}`,
    `Memory Roles: ${memoryRoles.join(', ') || '-'}`,
    `Review Warnings: ${reviewWarnings.join(' | ') || '-'}`,
    ...(agentActivity.stage_statuses?.length
      ? agentActivity.stage_statuses
          .slice(0, 6)
          .map((stage) => `${stage.stage} | ${stage.status} | ${stage.message}`)
      : ['No stage timeline recorded yet.']),
  ];

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '58%', paddingRight: 1 },
        panel(
          'OPERATOR CHAT',
          [
            `Role: ${formatPersona(persona)}`,
            'Type directly to write. Enter sends. Backspace deletes. [ and ] switch persona.',
            chatBusy ? 'Sending message to the operator surface...' : 'Ready.',
            '',
            ...(history.length
              ? history
                  .slice(-8)
                  .flatMap((entry) => [
                    `you: ${entry.user}`,
                    `${formatPersona(entry.persona)}: ${entry.response}`,
                    '',
                  ])
              : ['No chat messages yet.']),
          ],
          'green',
        ),
      ),
      e(
        Box,
        { width: '42%', paddingLeft: 1, flexDirection: 'column' },
        e(
          Box,
          { width: '100%' },
          panel('DECISION WORKFLOW', activityLines, 'cyan'),
        ),
        e(
          Box,
          { width: '100%', marginTop: 1 },
          panel('REASONING / TOOLS', reasoningLines.slice(0, 10), 'magenta'),
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(Box, { width: '100%' }, panel('COMPOSER', [draft || ''], 'yellow')),
    ),
  );
}

function normalizeChatHistory(data) {
  const entries = data?.chatHistory?.entries || [];
  return [...entries].reverse().map((entry) => ({
    user: entry.user_message,
    persona: entry.persona,
    response: entry.response_text,
  }));
}

/**
 * Render the Ink dashboard UI for the control room using the provided view state and props.
 *
 * Renders an error view when `error` is present, a loading view when `data` is absent, and the selected page with header/footer and optional action message when `data` is available.
 *
 * @param {Object} props - Component props.
 * @param {?Object} props.data - Dashboard snapshot payload; expected to include `loadedAt` (ISO string) used for the footer timestamp.
 * @param {?string} props.error - Error message to display in the header area; when present the full dashboard is replaced by the error view.
 * @param {string} props.loadingText - Text displayed while the dashboard snapshot is loading.
 * @param {string} props.page - Current page key; one of 'overview','runtime','portfolio','review','memory','chat','settings'.
 * @param {?{kind:string,text:string}} props.actionMessage - Optional transient action message; `kind === 'error'` renders in red, other kinds render in yellow.
 * @param {boolean} props.busy - When true, shows a working indicator in the header.
 * @param {string} props.chatPersona - Selected chat persona key for the chat composer.
 * @param {Array<Object>} props.chatHistory - Normalized chat history entries shown in the chat page.
 * @param {string} props.chatDraft - Current chat composer draft text.
 * @param {boolean} props.chatBusy - When true, indicates an in-flight chat send and disables composer actions.
 * @param {string} props.instructionDraft - Current settings/instruction composer draft text.
 * @param {boolean} props.instructionBusy - When true, indicates an in-flight instruction preview/apply request.
 * @param {string} props.instructionMode - Settings page submit mode; either 'preview' or 'apply'.
 * @param {?object} props.instructionResult - Latest parsed/applied instruction payload returned by the CLI (used to render preview/result on the settings page).
 * @returns {import('react').ReactElement} The Ink element tree representing the dashboard view.
 */
function DashboardView({
  data,
  error,
  loadingText,
  page,
  actionMessage,
  busy,
  chatPersona,
  chatHistory,
  chatDraft,
  chatBusy,
  instructionDraft,
  instructionBusy,
  instructionMode,
  instructionResult,
}) {
  if (error) {
    return e(
      Box,
      { flexDirection: 'column' },
      e(
        Text,
        { color: 'red', bold: true },
        dashboardTitle,
      ),
      e(Text, { color: 'red' }, `Error: ${error}`),
      e(Text, { color: 'gray' }, `CLI executable: ${cliExecutable}`),
    );
  }

  if (!data) {
    return e(
      Box,
      { flexDirection: 'column' },
      e(
        Text,
        { color: 'green', bold: true },
        dashboardTitle,
      ),
      e(Text, { color: 'gray' }, loadingText),
    );
  }

  const terminalRows = process.stdout.rows || 36;
  const terminalColumns = process.stdout.columns || 100;
  const navRows = terminalColumns < 140 ? 2 : 1;
  const headerRows = 1 + navRows + (actionMessage ? 1 : 0);
  const footerRows = 1;
  const bodyHeight = Math.max(1, terminalRows - headerRows - footerRows);
  const compact = terminalRows <= 30 || terminalColumns <= 110;

  const view = getPageView({
    page,
    data,
    chat: {
      persona: chatPersona,
      history: chatHistory,
      draft: chatDraft,
      busy: chatBusy,
    },
    instruction: {
      draft: instructionDraft,
      busy: instructionBusy,
      mode: instructionMode,
      result: instructionResult,
    },
    compact,
  });

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Text,
      { color: 'green', bold: true },
      dashboardTitle,
    ),
    e(Text, { color: 'gray' }, dashboardStatusLine({ busy, page })),
    actionMessage
      ? e(
          Text,
          { color: actionMessage.kind === 'error' ? 'red' : 'yellow' },
          actionMessage.text,
        )
      : null,
    e(
      Box,
      {
        flexDirection: 'column',
        width: '100%',
        height: bodyHeight,
        overflowY: 'hidden',
      },
      view,
    ),
    e(Text, { color: 'gray' }, `Last refresh: ${data.loadedAt}`),
  );
}

/**
 * Manage dashboard state, periodic refresh, runtime actions, and chat UI state for the dashboard UI.
 *
 * Initializes and exposes dashboard data, error/loading indicators, page navigation, runtime action handling,
 * and chat-related state (persona, history, draft, busy). When `interactive` is true, the hook also starts a
 * 2s interval to refresh the dashboard automatically.
 *
 * @param {{ interactive: boolean }} params - Configuration options.
 * @param {boolean} params.interactive - If true, enable periodic automatic refresh and input-interactive behavior.
 * @returns {{
 *   data: any,
 *   error: string|null,
 *   loadingText: string,
 *   refreshNow: () => void,
 *   exit: () => void,
 *   page: string,
 *   setPage: (p: string) => void,
 *   nextPage: () => void,
 *   prevPage: () => void,
 *   runAction: (kind: string) => Promise<void>,
 *   busy: boolean,
 *   actionMessage: { kind: string, text: string }|null,
 *   chatPersona: string,
 *   setChatPersona: (p: string) => void,
 *   chatHistory: Array<any>,
 *   setChatHistory: (h: Array<any>) => void,
 *   chatDraft: string,
 *   setChatDraft: (d: string) => void,
 *   chatBusy: boolean,
 *   setChatBusy: (b: boolean) => void,
 *   instructionDraft: string,
 *   setInstructionDraft: (d: string) => void,
 *   instructionBusy: boolean,
 *   setInstructionBusy: (b: boolean) => void,
 *   instructionMode: string,
 *   setInstructionMode: (m: string) => void,
 *   instructionResult: object|null,
 *   setInstructionResult: (r: object|null) => void,
 *   sendInstruction: () => Promise<void>
 * }}
 */
function useDashboardState({ interactive }) {
  const { exit } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [page, setPage] = useState('overview');
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [chatPersona, setChatPersona] = useState('operator_liaison');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatDraft, setChatDraft] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [instructionDraft, setInstructionDraft] = useState('');
  const [instructionBusy, setInstructionBusy] = useState(false);
  const [instructionMode, setInstructionMode] = useState('preview');
  const [instructionResult, setInstructionResult] = useState(null);
  const loadingText = useMemo(() => `Connecting to ${cliExecutable}...`, []);

  const refresh = useCallback(async () => {
    try {
      const next = await loadDashboard();
      setData(next);
      setError(null);
      if (once) {
        setTimeout(() => exit(), 50);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      if (once) {
        setTimeout(() => exit(), 50);
      }
    }
  }, [exit]);

  useEffect(() => {
    refresh();
  }, [refresh, refreshCount]);

  useEffect(() => {
    if (!data) {
      return;
    }
    setChatHistory(normalizeChatHistory(data));
  }, [data]);

  useEffect(() => {
    if (!interactive) {
      return undefined;
    }
    const timer = setInterval(() => {
      setRefreshCount((current) => current + 1);
    }, 2000);
    return () => clearInterval(timer);
  }, [interactive]);

  const refreshNow = useCallback(() => {
    setRefreshCount((current) => current + 1);
  }, []);

  const runAction = useCallback(
    async (kind) => {
      if (!data || busy) {
        return;
      }
      setBusy(true);
      try {
        setActionMessage(await performRuntimeAction(kind, data));
        const next = await loadDashboard();
        setData(next);
        setError(null);
      } catch (err) {
        setActionMessage({
          kind: 'error',
          text: err instanceof Error ? err.message : String(err),
        });
      } finally {
        setBusy(false);
      }
    },
    [busy, data],
  );

  const sendInstruction = useCallback(async () => {
    const message = instructionDraft.trim();
    if (!message || instructionBusy) {
      return;
    }
    setInstructionBusy(true);
    try {
      const args = ['instruct', '--json', '--message', message];
      if (instructionMode === 'apply') {
        args.push('--apply');
      }
      const payload = await runJsonCommand(args);
      setInstructionResult(payload);
      setInstructionDraft('');
      setActionMessage({
        kind: 'info',
        text: payload.applied
          ? 'Operator instruction applied to preferences.'
          : 'Operator instruction parsed.',
      });
      const next = await loadDashboard();
      setData(next);
      setError(null);
    } catch (err) {
      setInstructionResult({
        instruction: {
          summary: 'Instruction failed.',
          should_update_preferences: false,
          requires_confirmation: false,
          rationale: err instanceof Error ? err.message : String(err),
          preference_update: {},
        },
        applied: false,
        updated_preferences: null,
      });
      setActionMessage({
        kind: 'error',
        text: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setInstructionBusy(false);
    }
  }, [instructionBusy, instructionDraft, instructionMode]);

  const nextPage = useCallback(() => {
    setPage((current) => pages[(pages.indexOf(current) + 1) % pages.length]);
  }, []);

  const prevPage = useCallback(() => {
    setPage(
      (current) =>
        pages[(pages.indexOf(current) - 1 + pages.length) % pages.length],
    );
  }, []);

  return {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
    instructionDraft,
    setInstructionDraft,
    instructionBusy,
    setInstructionBusy,
    instructionMode,
    setInstructionMode,
    instructionResult,
    setInstructionResult,
    sendInstruction,
  };
}

/**
 * Render the interactive Agentic Trader control-room dashboard and wire keyboard input, runtime actions, and chat behavior.
 *
 * Sets up dashboard state with periodic refresh, binds keys for page navigation and global runtime actions, and provides a chat composer that sends messages via the CLI and updates the in-UI chat history.
 *
 * @returns {import('react').ReactElement} A React element of the DashboardView configured for interactive use.
 */
function InteractiveDashboardApp() {
  const {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
    instructionDraft,
    setInstructionDraft,
    instructionBusy,
    instructionMode,
    setInstructionMode,
    instructionResult,
    sendInstruction,
  } = useDashboardState({ interactive: true });

  const sendChat = useCallback(async () => {
    const message = chatDraft.trim();
    if (!message || chatBusy) {
      return;
    }
    setChatBusy(true);
    try {
      const payload = await runJsonCommand([
        'chat',
        '--json',
        '--persona',
        chatPersona,
        '--message',
        message,
      ]);
      setChatHistory((current) => [
        ...current,
        {
          user: payload.message,
          persona: payload.persona,
          response: payload.response,
        },
      ]);
      refreshNow();
      setChatDraft('');
    } catch (err) {
      setChatHistory((current) => [
        ...current,
        {
          user: message,
          persona: chatPersona,
          response: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
      setChatDraft('');
    } finally {
      setChatBusy(false);
    }
  }, [
    chatBusy,
    chatDraft,
    chatPersona,
    refreshNow,
    setChatBusy,
    setChatDraft,
    setChatHistory,
  ]);

  useInput((input, key) => {
    handleDashboardInput(input, key, {
      exit,
      nextPage,
      page,
      prevPage,
      refreshNow,
      runAction,
      sendChat,
      sendInstruction,
      setChatDraft,
      setChatPersona,
      setInstructionDraft,
      setInstructionMode,
      setPage,
    });
  });

  return e(DashboardView, {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  });
}

/**
 * Render a read-only snapshot of the dashboard UI.
 *
 * Uses the dashboard state hook in non-interactive mode and returns the
 * DashboardView element populated with that state (no input wiring or periodic refresh).
 *
 * @returns {import('react').ReactElement} The DashboardView React element showing the current snapshot.
 */
function StaticDashboardApp() {
  const {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  } = useDashboardState({ interactive: false });
  return e(DashboardView, {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  });
}

const isDirectRun =
  Boolean(process.argv[1]) &&
  import.meta.url === pathToFileURL(process.argv[1]).href;

if (isDirectRun) {
  await import('ink').then(({ render }) => {
    render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
  });
}

export {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  failedCheckNames,
  formatMarketSession,
  formatMarketSessionWithTradable,
  formatMTFSnapshot,
  formatPersona,
  getAgentEventLines,
  getCurrentCycleLines,
  getExplorerLines,
  getInspectionLines,
  getInstructionResultLines,
  getJournalLines,
  getMarketContextLines,
  getRecentRunsLines,
  getReplayLines,
  getReviewLines,
  getStatusBorderColor,
  getSupervisorLogLines,
  getSystemLines,
  getTraceLines,
  getTradeContextLines,
  handleChatInput,
  handleDashboardInput,
  handleGlobalInput,
  handleSettingsInput,
  normalizeChatHistory,
  overviewRuntimeMode,
  providerLines,
  readinessLines,
  renderLinesFallback,
  renderUnavailableMessage,
  rotateInstructionMode,
  rotatePersona,
  sourceHealthSummaryLine,
};
export { getPageLabel } from './copy.mjs';
