import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const e = React.createElement;
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;
const once = process.argv.includes('--once');
const projectRoot = fileURLToPath(new URL('..', import.meta.url));
const pages = ['overview', 'runtime', 'portfolio', 'review', 'memory', 'chat'];
const personas = [
  'operator_liaison',
  'regime_analyst',
  'strategy_selector',
  'risk_steward',
  'portfolio_manager',
];

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
 * Choose a default comma-separated symbol list based on user preferences.
 *
 * @param {Object} preferences - Preferences object that may include `exchanges` and `regions` arrays.
 * @returns {string} A comma-separated symbol list: `THYAO.IS,GARAN.IS` when `exchanges` contains `BIST` or `regions` contains `TR`; `AAPL,MSFT` when `exchanges` contains `NASDAQ` or `NYSE` or `regions` contains `US`; otherwise `BTC-USD,ETH-USD`.
 */
function defaultSymbolsFromPreferences(preferences) {
  const exchanges = preferences?.exchanges || [];
  const regions = preferences?.regions || [];
  if (exchanges.includes('BIST') || regions.includes('TR')) {
    return 'THYAO.IS,GARAN.IS';
  }
  if (
    exchanges.includes('NASDAQ') ||
    exchanges.includes('NYSE') ||
    regions.includes('US')
  ) {
    return 'AAPL,MSFT';
  }
  return 'BTC-USD,ETH-USD';
}

/**
 * Produce a short tail of the supervisor's recent daemon log lines.
 *
 * @param {Object|undefined} supervisor - Supervisor state object that may contain `stderr_tail` and/or `stdout_tail` arrays of log lines.
 * @returns {string[]} An array of strings: if `stderr_tail` has entries, `['stderr:', ...lastUpTo3Lines]`; else if `stdout_tail` has entries, `['stdout:', ...lastUpTo3Lines]`; otherwise `['No daemon log tail yet.']`.
 */
function getSupervisorLogLines(supervisor) {
  if (supervisor?.stderr_tail?.length) {
    return ['stderr:', ...supervisor.stderr_tail.slice(-3)];
  }
  if (supervisor?.stdout_tail?.length) {
    return ['stdout:', ...supervisor.stdout_tail.slice(-3)];
  }
  return ['No daemon log tail yet.'];
}

/**
 * Produce an array of human-readable lines summarizing a trade context for display.
 *
 * If `tradeContext.available === false`, returns the unavailable-message lines (including the provided error).
 * If `tradeContext.record` is missing, returns a single-line notice that no persisted trade context exists.
 *
 * @param {Object} tradeContext - Trade context payload from the dashboard snapshot.
 *   Expected shape (partial): `{ available?: boolean, error?: string, record?: Object }`.
 *   The `record` object may contain `trade_id`, `run_id`, `consensus.alignment_level`, `manager_rationale`,
 *   `execution_rationale`, `review_summary`, `routed_models`, `retrieved_memory_summary`, and `tool_outputs`.
 * @returns {string[]} Lines suitable for rendering in the UI describing IDs, consensus, rationales, routed models,
 *   memory roles, and tool roles, or fallback lines when unavailable or absent.
 */
function getTradeContextLines(tradeContext) {
  if (tradeContext?.available === false) {
    return renderUnavailableMessage(tradeContext.error);
  }
  if (!tradeContext?.record) {
    return ['No persisted trade context is available yet.'];
  }
  const record = tradeContext.record;
  return [
    `Trade ID: ${record.trade_id}`,
    `Run ID: ${record.run_id ?? '-'}`,
    `Consensus: ${record.consensus.alignment_level}`,
    `Manager Rationale: ${record.manager_rationale}`,
    `Execution Rationale: ${record.execution_rationale}`,
    `Review Summary: ${record.review_summary}`,
    `Routed Models: ${
      Object.entries(record.routed_models || {})
        .map(([role, model]) => `${role}:${model}`)
        .join(' | ') || '-'
    }`,
    `Memory Roles: ${Object.keys(record.retrieved_memory_summary || {}).join(', ') || '-'}`,
    `Tool Roles: ${Object.keys(record.tool_outputs || {}).join(', ') || '-'}`,
  ];
}

/**
 * Perform a runtime control action (start, stop, or restart) based on the provided dashboard snapshot and return a user-facing action message.
 *
 * @param {string} kind - The action to perform: "start", "stop", or other (treated as restart if a previous launch config exists).
 * @param {Object} data - Dashboard snapshot containing runtime `status` and `preferences` used to decide behavior.
 * @returns {{kind: string, text: string}} An action message describing the requested operation or why no action was taken (e.g., `{ kind: 'info', text: '...' }`).
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
 * Rotate the chat persona selection by a signed offset within the available personas.
 *
 * @param {string} current - The currently selected persona key.
 * @param {number} offset - Signed integer offset to apply (positive moves forward, negative moves backward).
 * @returns {string} The persona key at the resulting rotated position.
 */
function rotatePersona(current, offset) {
  return personas[
    (personas.indexOf(current) + offset + personas.length) % personas.length
  ];
}

/**
 * Handle a single chat input keystroke, updating chat draft or persona or triggering send when applicable.
 *
 * @param {string} input - The raw input character (e.g., a typed character or '['/']').
 * @param {{return?: boolean, backspace?: boolean, delete?: boolean, ctrl?: boolean, meta?: boolean}} key - Key flags indicating special keys pressed.
 * @param {{sendChat: Function, setChatDraft: Function, setChatPersona: Function}} handlers - Handler functions used to mutate chat state:
 *   - sendChat(): send the current draft as a chat message.
 *   - setChatDraft(fn): update the draft; receives the current draft and should return the new draft.
 *   - setChatPersona(fn): rotate/set the current persona; receives the current persona and should return the new persona.
 * @returns {boolean} `true` if the input was handled (consumed), `false` otherwise.
 */
function handleChatInput(input, key, handlers) {
  if (key.return) {
    handlers.sendChat();
    return true;
  }
  if (key.backspace || key.delete) {
    handlers.setChatDraft((current) => current.slice(0, -1));
    return true;
  }
  if (input === '[') {
    handlers.setChatPersona((current) => rotatePersona(current, -1));
    return true;
  }
  if (input === ']') {
    handlers.setChatPersona((current) => rotatePersona(current, 1));
    return true;
  }
  if (!key.ctrl && !key.meta && input) {
    handlers.setChatDraft((current) => current + input);
    return true;
  }
  return false;
}

/**
 * Handle top-level single-key commands and page selection from keyboard input.
 *
 * Recognizes:
 * - 'q' to exit,
 * - 'r' to refresh,
 * - 's' to start the runtime,
 * - 'x' to stop the runtime,
 * - 'R' to restart the runtime,
 * - '1'..'6' to switch to the corresponding page.
 *
 * @param {string} input - The raw key input (single character).
 * @param {{ exit: Function, refreshNow: Function, runAction: Function, setPage: Function }} handlers - Action handlers to invoke for recognized keys.
 * @returns {boolean} `true` if the input was handled, `false` otherwise.
 */
function handleGlobalInput(input, handlers) {
  const normalized = input.toLowerCase();
  if (normalized === 'q') {
    handlers.exit();
    return true;
  }
  if (input === 'R') {
    handlers.runAction('restart');
    return true;
  }
  if (normalized === 'r') {
    handlers.refreshNow();
    return true;
  }
  if (normalized === 's') {
    handlers.runAction('start');
    return true;
  }
  if (normalized === 'x') {
    handlers.runAction('stop');
    return true;
  }
  if (['1', '2', '3', '4', '5', '6'].includes(input)) {
    handlers.setPage(pages[Number(input) - 1]);
    return true;
  }
  return false;
}

/**
 * Load the dashboard snapshot from the CLI and attach a retrieval timestamp.
 *
 * Requests a dashboard snapshot and returns the snapshot object augmented with
 * a `loadedAt` field containing the ISO 8601 timestamp when the snapshot was fetched.
 *
 * @returns {object} The dashboard snapshot payload augmented with a `loadedAt` ISO 8601 string.
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
 * Map a page key to its human-readable label.
 * @param {string} page - The page key (e.g., 'overview', 'runtime').
 * @returns {string} The display label for the given page key, or 'Unknown' if the key is not recognized.
 */
function getPageLabel(page) {
  const labels = {
    overview: 'Overview',
    runtime: 'Runtime',
    portfolio: 'Portfolio',
    review: 'Review',
    memory: 'Memory',
    chat: 'Chat',
  };
  return labels[page] || 'Unknown';
}

/**
 * Selects and returns the UI component element corresponding to the specified page key.
 *
 * @param {string} page - Page key ('overview', 'runtime', 'portfolio', 'review', 'memory', or other for chat).
 * @param {Object} data - Dashboard snapshot and related data passed into the page component.
 * @param {string} chatPersona - Active chat persona (used when rendering the chat page).
 * @param {Array<Object>} chatHistory - Normalized chat history entries (used when rendering the chat page).
 * @param {string} chatDraft - Current chat draft text (used when rendering the chat page).
 * @param {boolean} chatBusy - Whether a chat request is in progress (used when rendering the chat page).
 * @returns {import('react').ReactElement} The rendered Ink/React element for the requested page (defaults to the Chat page for unknown keys).
 */
function getPageView(
  page,
  data,
  chatPersona,
  chatHistory,
  chatDraft,
  chatBusy,
) {
  switch (page) {
    case 'overview':
      return e(OverviewPage, { data });
    case 'runtime':
      return e(RuntimePage, { data });
    case 'portfolio':
      return e(PortfolioPage, { data });
    case 'review':
      return e(ReviewPage, { data });
    case 'memory':
      return e(MemoryPage, { data });
    default:
      return e(ChatPage, {
        data,
        persona: chatPersona,
        history: chatHistory,
        draft: chatDraft,
        chatBusy,
      });
  }
}

function getStatusBorderColor(runtimeState) {
  switch (runtimeState) {
    case 'active':
      return 'green';
    case 'stale':
      return 'yellow';
    default:
      return 'cyan';
  }
}

function formatMarketSession(session) {
  if (!session) return 'unavailable';
  return `${session.venue} ${session.session_state}`;
}

function formatMarketSessionWithTradable(session) {
  if (!session) return 'unavailable';
  return `${session.venue} ${session.session_state} tradable=${session.tradable_now}`;
}

function formatMTFSnapshot(snapshot) {
  if (!snapshot) return '-';
  return `${snapshot.mtf_alignment} @ ${snapshot.higher_timeframe}`;
}

function renderUnavailableMessage(error) {
  return [
    'unavailable',
    error || 'The runtime writer currently owns the database.',
  ];
}

function getReviewLines(reviewRecord) {
  if (!reviewRecord) {
    return ['No persisted runs are available yet.'];
  }
  return [
    `Run ID: ${reviewRecord.run_id}`,
    `Created: ${reviewRecord.created_at}`,
    `Symbol: ${reviewRecord.symbol}`,
    `Approved: ${reviewRecord.approved}`,
    `Coordinator Focus: ${reviewRecord.artifacts.coordinator.market_focus}`,
    `Regime: ${reviewRecord.artifacts.regime.regime}`,
    `Strategy: ${reviewRecord.artifacts.strategy.strategy_family}`,
    `Manager Bias: ${reviewRecord.artifacts.manager.action_bias}`,
    `Consensus: ${reviewRecord.artifacts.consensus.alignment_level}`,
    `Review Summary: ${reviewRecord.artifacts.review.summary}`,
  ];
}

function getTraceLines(traceRecord) {
  if (!traceRecord?.artifacts?.agent_traces?.length) {
    return ['No persisted agent traces are available yet.'];
  }
  return traceRecord.artifacts.agent_traces.map(
    (stageTrace) =>
      `${stageTrace.role} | ${stageTrace.model_name} | fallback=${stageTrace.used_fallback} | ${stageTrace.output_json.replaceAll(/\s+/g, ' ').slice(0, 72)}`,
  );
}

function getReplayLines(replayState) {
  if (!replayState) {
    return ['No replayable run is available yet.'];
  }
  return [
    `Final Side: ${replayState.final_side}`,
    `Approved: ${replayState.approved}`,
    `Consensus: ${replayState.consensus.alignment_level}`,
    `MTF: ${replayState.snapshot.mtf_alignment} @ ${replayState.snapshot.higher_timeframe}`,
    `Manager: ${(replayState.manager_override_notes || []).join(' / ')}`,
    `Conflict Count: ${(replayState.manager_conflicts || []).length}`,
    ...(replayState.manager_conflicts || [])
      .slice(0, 3)
      .map(
        (conflict) =>
          `${conflict.conflict_type} [${conflict.severity}] | ${conflict.summary}`,
      ),
    `Final Rationale: ${replayState.final_rationale}`,
    ...replayState.stages
      .slice(0, 5)
      .map(
        (stage) =>
          `${stage.role} | memories=${stage.retrieved_memories.length} | bus=${(stage.shared_memory_bus || []).length} | tools=${stage.tool_outputs.length} | fallback=${stage.used_fallback}`,
      ),
  ];
}

function getExplorerLines(explorer) {
  if (!explorer?.matches?.length) {
    return ['No similar historical memories found yet.'];
  }
  return explorer.matches.map(
    (match) =>
      `${match.created_at} | ${match.symbol} | score=${match.similarity_score} | ${match.retrieval_source} | ${match.regime} | ${match.strategy_family} | ${match.summary}`,
  );
}

function getInspectionLines(inspection) {
  if (!inspection?.stages?.length) {
    return ['No retrieval inspection data available yet.'];
  }
  return inspection.stages.flatMap((stage) => {
    const retrieved = stage.retrieved_memories?.length ?? 0;
    const notes = stage.memory_notes?.length ?? 0;
    const recentRuns = stage.recent_runs?.length ?? 0;
    const sharedBus = stage.shared_memory_bus?.length ?? 0;
    const headline = `${stage.role} | retrieved=${retrieved} | trade-memory=${notes} | shared-bus=${sharedBus} | recent-runs=${recentRuns}`;
    const sample =
      stage.retrieved_memories?.[0] ||
      stage.memory_notes?.[0] ||
      'No retrieval context attached.';
    return [headline, `  ${sample}`, ''];
  });
}

function getJournalLines(journal) {
  if (!journal?.entries?.length) {
    return ['No trade journal entries yet.'];
  }
  return journal.entries.map(
    (entry) =>
      `${entry.opened_at} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`,
  );
}

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

function renderLinesFallback(title, available, error, fallback) {
  if (available === false) {
    return [
      fallback,
      error || 'The runtime writer currently owns the database.',
    ];
  }
  return null;
}

function OverviewPage({ data }) {
  const doctor = data.doctor;
  const runtime = data.status;
  const preferences = data.preferences;
  const calendar = data.calendar;
  const broker = data.broker;
  const marketCache = data.marketCache;
  const latestSnapshot = data.review.record?.artifacts?.snapshot;
  const agentActivity = data.agentActivity;
  const agentEvents = agentActivity?.recent_stage_events || [];

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
          [
            `Runtime: ${runtime.runtime_state}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `Status: ${runtime.status_message}`,
            `Current Note: ${runtime.state?.message ?? '-'}`,
            `Current Stage: ${agentActivity?.current_stage ?? '-'}`,
            `Stage Status: ${agentActivity?.current_stage_status ?? '-'}`,
            `Stage Detail: ${agentActivity?.current_stage_message ?? '-'}`,
            `Last Completed Stage: ${agentActivity?.last_completed_stage ?? '-'}`,
            `Completed Detail: ${agentActivity?.last_completed_message ?? '-'}`,
            `Consensus: ${data.review.record?.artifacts?.consensus?.alignment_level ?? '-'}`,
            `MTF Alignment: ${latestSnapshot?.mtf_alignment ?? '-'}`,
            `Higher Timeframe: ${latestSnapshot?.higher_timeframe ?? '-'}`,
            '',
            `Last Outcome Type: ${agentActivity?.last_outcome_type ?? '-'}`,
            `Last Outcome: ${agentActivity?.last_outcome_message ?? 'Waiting for a completed symbol or service result.'}`,
          ],
          getStatusBorderColor(runtime.runtime_state),
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'SYSTEM',
          [
            `Model: ${doctor.model}`,
            `Base URL: ${doctor.base_url}`,
            `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
            `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
            `Runtime Dir: ${doctor.runtime_dir}`,
            `Database: ${doctor.database}`,
            `Broker Backend: ${broker?.backend ?? '-'}`,
            `Broker State: ${broker?.state ?? '-'}`,
            `Default Symbols: ${defaultSymbolsFromPreferences(preferences)}`,
            `Market Session: ${formatMarketSession(calendar.session)}`,
            `News Tool: ${data.news?.mode ?? 'off'}`,
            `Cached Snapshots: ${marketCache.count}`,
          ],
          doctor.ollama_reachable && doctor.model_available ? 'green' : 'red',
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
          'AGENT ACTIVITY',
          agentEvents.length
            ? agentEvents.map(
                (event) =>
                  `${event.created_at} | ${event.stage} | ${event.status} | ${event.message}`,
              )
            : ['No live agent stage events yet.'],
          'magenta',
        ),
      ),
    ),
  );
}

/**
 * Render the Runtime page showing runtime status, supervisor/stage flow, and recent events.
 *
 * Renders three panels summarizing the current runtime state (process, PID, symbols, timing,
 * stage details, broker and snapshot info), the supervisor and stage flow (log tails, stage
 * statuses, and latest review summary), and recent runtime events.
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
            `Kill Switch: ${broker?.kill_switch_active ?? false}`,
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

function PortfolioPage({ data }) {
  const portfolio = data.portfolio;
  const riskReport = data.riskReport;
  const journal = data.journal;
  const preferences = data.preferences;
  const snapshot = portfolio.snapshot;
  const positions = portfolio.positions;

  const portfolioLines = renderLinesFallback(
    'PORTFOLIO',
    portfolio.available,
    portfolio.error,
    'Portfolio view is temporarily unavailable.',
  ) || [
    `Cash: ${snapshot.cash.toFixed(2)}`,
    `Market Value: ${snapshot.market_value.toFixed(2)}`,
    `Equity: ${snapshot.equity.toFixed(2)}`,
    `Realized PnL: ${snapshot.realized_pnl.toFixed(2)}`,
    `Unrealized PnL: ${snapshot.unrealized_pnl.toFixed(2)}`,
    `Open Positions: ${positions.length}`,
  ];

  const riskLines =
    riskReport.available === false || !riskReport.report
      ? [
          'Risk report is temporarily unavailable.',
          riskReport.error || 'The runtime writer currently owns the database.',
        ]
      : [
          `Equity: ${riskReport.report.equity.toFixed(2)}`,
          `Gross Exposure: ${(riskReport.report.gross_exposure_pct * 100).toFixed(2)}%`,
          `Largest Position: ${(riskReport.report.largest_position_pct * 100).toFixed(2)}%`,
          `Drawdown: ${(riskReport.report.drawdown_from_peak_pct * 100).toFixed(2)}%`,
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
 * Render the Review page with panels for run review, agent trace, memory-aware replay, and trade context.
 *
 * @param {{ data: { review: Object, trace: Object, replay: Object, tradeContext: Object } }} props
 * @param {Object} props.data - Dashboard snapshot subsets used to populate panels.
 *   Expected keys:
 *     - review: { available?: boolean, record?: Object, error?: string }
 *     - trace: { available?: boolean, record?: Object, error?: string }
 *     - replay: { available?: boolean, replay?: Object, error?: string }
 *     - tradeContext: Object
 * @returns {import('react').ReactElement} An Ink layout containing four titled panels: "LATEST RUN REVIEW", "AGENT TRACE", "MEMORY-AWARE REPLAY", and "TRADE CONTEXT".
 */
function ReviewPage({ data }) {
  const review = data.review;
  const trace = data.trace;
  const replay = data.replay;
  const tradeContext = data.tradeContext;
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
        { width: '100%' },
        panel('TRADE CONTEXT', tradeContextLines, 'cyan'),
      ),
    ),
  );
}

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
        panel('SIMILAR MEMORIES', matchLines.slice(0, 10), 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('RETRIEVAL INSPECTION', retrievalLines.slice(0, 12), 'yellow'),
      ),
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
            `Persona: ${persona}`,
            'Type directly to write. Enter sends. Backspace deletes. [ and ] switch persona.',
            chatBusy ? 'Sending message to the operator surface...' : 'Ready.',
            '',
            ...(history.length
              ? history
                  .slice(-8)
                  .flatMap((entry) => [
                    `you: ${entry.user}`,
                    `${entry.persona}: ${entry.response}`,
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
          panel('LIVE AGENT ACTIVITY', activityLines, 'cyan'),
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
 * Render the Ink dashboard UI for the control room based on current state and props.
 *
 * Renders an error view when `error` is present, a loading view when `data` is absent,
 * and the selected page plus header/footer when `data` is available. Displays action
 * messages and a busy indicator when appropriate.
 *
 * @param {Object} props - Component props.
 * @param {?Object} props.data - Dashboard snapshot payload; expected to include `loadedAt`.
 * @param {?string} props.error - Error message to display instead of the dashboard.
 * @param {string} props.loadingText - Text to display while loading.
 * @param {string} props.page - Current page key (one of 'overview','runtime','portfolio','review','memory','chat').
 * @param {?{kind:string,text:string}} props.actionMessage - Optional action message; `kind` controls color.
 * @param {boolean} props.busy - When true, shows a working indicator in the header.
 * @param {string} props.chatPersona - Currently selected chat persona key.
 * @param {Array<Object>} props.chatHistory - Normalized chat history entries for display.
 * @param {string} props.chatDraft - Current chat composer draft text.
 * @param {boolean} props.chatBusy - When true, indicates an in-flight chat send.
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
}) {
  if (error) {
    return e(
      Box,
      { flexDirection: 'column' },
      e(
        Text,
        { color: 'red', bold: true },
        'AGENTIC TRADER // INK CONTROL ROOM',
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
        'AGENTIC TRADER // INK CONTROL ROOM',
      ),
      e(Text, { color: 'gray' }, loadingText),
    );
  }

  const pageIndex = pages.indexOf(page) + 1;
  const pageLabel = getPageLabel(page);

  const view = getPageView(
    page,
    data,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
  );

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Text,
      { color: 'green', bold: true },
      'AGENTIC TRADER // INK CONTROL ROOM',
    ),
    e(
      Text,
      { color: 'gray' },
      `page ${pageIndex}/6: ${pageLabel}  |  1 overview  2 runtime  3 portfolio  4 review  5 memory  6 chat  |  r refresh  s start  x stop  R restart  q quit${busy ? '  |  working...' : ''}`,
    ),
    actionMessage
      ? e(
          Text,
          { color: actionMessage.kind === 'error' ? 'red' : 'yellow' },
          actionMessage.text,
        )
      : null,
    view,
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
 *   setChatBusy: (b: boolean) => void
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
  };
}

/**
 * Render the interactive Agentic Trader control-room dashboard and wire its input, actions, and chat behavior.
 *
 * Manages dashboard state and periodic refresh, handles keyboard-driven page navigation and global runtime actions, and provides a chat composer that sends messages via the CLI and updates the in-UI chat history.
 *
 * @returns {import('react').ReactElement} The rendered DashboardView component configured for interactive use.
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
    if (key.rightArrow || input === '\t') {
      nextPage();
      return;
    }
    if (key.leftArrow) {
      prevPage();
      return;
    }
    if (['1', '2', '3', '4', '5', '6'].includes(input) && page !== 'chat') {
      setPage(pages[Number(input) - 1]);
      return;
    }
    if (
      page === 'chat' &&
      handleChatInput(input, key, { sendChat, setChatDraft, setChatPersona })
    ) {
      return;
    }
    handleGlobalInput(input, { exit, refreshNow, runAction, setPage });
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
  });
}

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
  });
}

await import('ink').then(({ render }) => {
  render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
});
