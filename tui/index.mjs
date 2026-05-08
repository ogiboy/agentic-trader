import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import {
  getCanonicalAnalysisLines,
  getFundamentalAssessmentLines,
} from './review-lines.mjs';

const execFileAsync = promisify(execFile);
const e = React.createElement;
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;
const once = process.argv.includes('--once');
const projectRoot = fileURLToPath(new URL('..', import.meta.url));
const pages = [
  'overview',
  'runtime',
  'portfolio',
  'review',
  'memory',
  'chat',
  'settings',
];
const personas = [
  'operator_liaison',
  'regime_analyst',
  'strategy_selector',
  'risk_steward',
  'portfolio_manager',
];
const personaLabels = {
  operator_liaison: 'Operator Assistant',
  regime_analyst: 'Market Regime Analyst',
  strategy_selector: 'Strategy Selector',
  risk_steward: 'Risk Steward',
  portfolio_manager: 'Portfolio Manager',
};
const instructionModes = ['preview', 'apply'];

function formatPersona(value) {
  return personaLabels[value] || value || '-';
}

function accountCurrency(data) {
  return (
    data.financeOps?.accounting?.currency ||
    data.portfolio?.accounting?.currency ||
    data.preferences?.currencies?.[0] ||
    'USD'
  );
}

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
 * Selects a default single trading symbol from dashboard snapshot data.
 *
 * @param {object} data - Dashboard snapshot which may contain `status.state.current_symbol`, `tradeContext.record.symbol`, `review.record.symbol`, and `preferences`.
 * @returns {string} The first available symbol from (in order): the current runtime symbol, the trade context record symbol, the review record symbol, or the first symbol derived from preferences.
 */
function defaultSingleSymbol(data) {
  return (
    data?.status?.state?.current_symbol ||
    data?.tradeContext?.record?.symbol ||
    data?.review?.record?.symbol ||
    defaultSymbolsFromPreferences(data?.preferences).split(',')[0]
  );
}

/**
 * Resolve the runtime interval from the provided dashboard data, falling back to the market context pack and then '1d'.
 * @param {Object} data - Dashboard snapshot that may contain `status.state.interval` or `marketContext.contextPack.interval`.
 * @returns {string} The resolved interval value, or '1d' if none is present.
 */
function defaultRuntimeInterval(data) {
  return (
    data?.status?.state?.interval ||
    data?.marketContext?.contextPack?.interval ||
    '1d'
  );
}

/**
 * Selects the runtime lookback interval from dashboard data, falling back to '180d'.
 * @param {object} data - Dashboard snapshot that may contain `status.state.lookback` or `marketContext.contextPack.lookback`.
 * @returns {string} The lookback interval string from runtime state if present, otherwise from the market context pack, otherwise `'180d'`.
 */
function defaultRuntimeLookback(data) {
  return (
    data?.status?.state?.lookback ||
    data?.marketContext?.contextPack?.lookback ||
    '180d'
  );
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
    ...getFundamentalAssessmentLines(record.fundamental_assessment),
    `Manager Rationale: ${record.manager_rationale}`,
    `Execution Rationale: ${record.execution_rationale}`,
    `Execution Backend: ${record.execution_backend ?? '-'}`,
    `Execution Adapter: ${record.execution_adapter ?? '-'}`,
    `Execution Outcome: ${record.execution_outcome_status ?? '-'}`,
    `Rejection Reason: ${record.execution_rejection_reason ?? '-'}`,
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
 * Format a persisted Market Context Pack into an array of human-readable lines.
 *
 * @param {Object} marketContext - Dashboard marketContext payload. May include
 *   `{ available?: boolean, error?: string, contextPack?: Object }`.
 * @returns {string[]} Lines summarizing the pack (summary, lookback, window,
 *   bars/coverage, interval semantics, higher-timeframe usage, data quality and
 *   anomaly flags, plus up to five horizon vote entries). If `available === false`
 *   the returned lines convey unavailability; if no `contextPack` is present a
 *   single notice line is returned.
 */
function getMarketContextLines(marketContext) {
  if (marketContext?.available === false) {
    return renderUnavailableMessage(marketContext.error);
  }
  const pack = marketContext?.contextPack;
  if (!pack) {
    return ['No persisted Market Context Pack is available yet.'];
  }
  const horizons = (pack.horizons || [])
    .slice(0, 5)
    .map(
      (item) =>
        `${item.horizon_bars}b ${item.trend_vote} return=${item.return_pct ?? '-'} drawdown=${item.max_drawdown_pct ?? '-'}`,
    );
  return [
    `Summary: ${pack.summary || '-'}`,
    `Lookback: ${pack.lookback ?? '-'} | Interval: ${pack.interval}`,
    `Window: ${pack.window_start ?? '-'} -> ${pack.window_end ?? '-'}`,
    `Bars: ${pack.bars_analyzed}/${pack.bars_expected ?? '?'} coverage=${pack.coverage_ratio ?? '?'}`,
    `Interval Semantics: ${pack.interval_semantics}`,
    `HTF: ${pack.higher_timeframe} used=${pack.higher_timeframe_used}`,
    `Quality: ${(pack.data_quality_flags || []).join(', ') || '-'}`,
    `Anomalies: ${(pack.anomaly_flags || []).join(', ') || '-'}`,
    ...horizons,
  ];
}

/**
 * Control the runtime (start, stop, one-shot, or restart) using the provided dashboard snapshot and produce a user-facing action message.
 *
 * @param {string} kind - Action to perform: "start", "stop", "one-shot", or other (treated as restart when a saved launch config exists).
 * @param {Object} data - Dashboard snapshot containing runtime `status` and `preferences` used to decide behavior.
 * @returns {{kind: string, text: string}} An action message describing the requested operation or why no action was taken (`kind: 'info'`, `text` explains the outcome).
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
 * Rotate the current instruction mode by a signed offset within the available modes.
 * @param {string} current - The currently selected instruction mode.
 * @param {number} offset - Signed offset to move within the mode list (positive for forward, negative for backward).
 * @returns {string} The instruction mode after applying the offset, wrapped around the mode list.
 */
function rotateInstructionMode(current, offset) {
  return instructionModes[
    (instructionModes.indexOf(current) + offset + instructionModes.length) %
      instructionModes.length
  ];
}

/**
 * Process a single chat keystroke to update the draft, rotate the persona, or submit the message.
 *
 * @param {string} input - Raw input character (e.g., a typed character or '[' / ']' for persona rotation).
 * @param {{return?: boolean, backspace?: boolean, delete?: boolean, ctrl?: boolean, meta?: boolean}} key - Flags for special keys pressed.
 * @param {{sendChat: Function, setChatDraft: Function, setChatPersona: Function}} handlers - State mutators:
 *   - sendChat(): submit the current draft as a chat message.
 *   - setChatDraft(fn): update the draft; receives current draft and returns new draft.
 *   - setChatPersona(fn): update the current persona; receives current persona and returns new persona.
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
 * Handle keyboard input for the settings/instruction composer.
 *
 * Processes Enter to send the instruction, Backspace/Delete to truncate the draft,
 * `[`/`]` to rotate instruction mode, and printable characters to append to the draft.
 *
 * @param {string} input - The raw character input (empty string for non-printable keys).
 * @param {object} key - Parsed key state (e.g., `{ return, backspace, delete, ctrl, meta }`).
 * @param {object} handlers - UI handlers.
 * @param {Function} handlers.sendInstruction - Trigger submission of the current instruction.
 * @param {Function} handlers.setInstructionDraft - Setter for the instruction draft; receives an updater function.
 * @param {Function} handlers.setInstructionMode - Setter for the instruction mode; receives an updater function.
 * @returns {boolean} `true` if the input was handled, `false` otherwise.
 */
function handleSettingsInput(input, key, handlers) {
  if (key.return) {
    handlers.sendInstruction();
    return true;
  }
  if (key.backspace || key.delete) {
    handlers.setInstructionDraft((current) => current.slice(0, -1));
    return true;
  }
  if (input === '[') {
    handlers.setInstructionMode((current) =>
      rotateInstructionMode(current, -1),
    );
    return true;
  }
  if (input === ']') {
    handlers.setInstructionMode((current) => rotateInstructionMode(current, 1));
    return true;
  }
  if (!key.ctrl && !key.meta && input) {
    handlers.setInstructionDraft((current) => current + input);
    return true;
  }
  return false;
}

/**
 * Handle top-level single-key keyboard commands and page selection.
 *
 * Invokes the corresponding handler when a recognized key is pressed:
 * q (exit), r (refresh), o (one-shot run), s (start), x (stop), R (restart),
 * and numeric keys 1–7 to switch pages.
 *
 * @param {string} input - The raw key input (single character).
 * @param {{ exit: Function, refreshNow: Function, runAction: Function, setPage: Function }} handlers - Callback handlers for actions: `exit()`, `refreshNow()`, `runAction(kind)`, and `setPage(page)`.
 * @returns {boolean} `true` if the input was handled and a handler was invoked, `false` otherwise.
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
  if (normalized === 'o') {
    handlers.runAction('one-shot');
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
  if (['1', '2', '3', '4', '5', '6', '7'].includes(input)) {
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
    memory: 'Decision Evidence',
    chat: 'Chat',
    settings: 'Settings',
  };
  return labels[page] || 'Unknown';
}

/**
 * Return the UI component element for the given dashboard page key.
 *
 * @param {string} page - Page key: 'overview', 'runtime', 'portfolio', 'review', 'memory', 'settings', or other (defaults to chat).
 * @param {Object} data - Dashboard snapshot and related data passed into the page component.
 * @param {string} chatPersona - Active chat persona used by the chat page.
 * @param {Array<Object>} chatHistory - Normalized chat history entries used by the chat page.
 * @param {string} chatDraft - Current chat draft text used by the chat page.
 * @param {boolean} chatBusy - Whether a chat request is in progress.
 * @param {string} instructionDraft - Current instruction draft text used by the settings page.
 * @param {boolean} instructionBusy - Whether an instruction request is in progress (settings page).
 * @param {string} instructionMode - Instruction mode ('preview' or 'apply') used by the settings page.
 * @param {Object|null} instructionResult - Result object from the last instruction invocation shown in the settings page.
 * @param {boolean} compact - Whether to render pages in compact mode (affects applicable pages).
 * @returns {import('react').ReactElement} The page element corresponding to `page`; unknown keys render the Chat page.
 */
function getPageView(
  page,
  data,
  chatPersona,
  chatHistory,
  chatDraft,
  chatBusy,
  instructionDraft,
  instructionBusy,
  instructionMode,
  instructionResult,
  compact,
) {
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
        draft: instructionDraft,
        instructionBusy,
        instructionMode,
        instructionResult,
        compact,
      });
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

/**
 * Format a review record into an array of display lines for the review panel.
 *
 * @param {Object|null} reviewRecord - Review snapshot or null/undefined when none available.
 *   Expected shape (properties used): `run_id`, `created_at`, `symbol`, `approved`, and
 *   `artifacts` containing `coordinator.market_focus`, `fundamental`, `regime.regime`,
 *   `strategy.strategy_family`, `manager.action_bias`, `consensus.alignment_level`, and
 *   `review.summary`.
 * @returns {string[]} An array of human-readable lines describing the review. If `reviewRecord`
 *   is falsy, returns `['No persisted runs are available yet.']`.
 */
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
    ...getFundamentalAssessmentLines(reviewRecord.artifacts.fundamental),
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
    (match) => {
      const reason = match.explanation?.eligibility_reason || match.retrieval_source;
      return `${match.created_at} | ${match.symbol} | score=${match.similarity_score} | why=${reason} | ${match.regime} | ${match.strategy_family} | ${match.summary}`;
    },
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
    const why = stage.retrieval_explanations?.length ?? 0;
    const headline = `${stage.role} | retrieved=${retrieved} | why=${why} | trade-memory=${notes} | shared-bus=${sharedBus} | recent-runs=${recentRuns}`;
    const firstWhy = stage.retrieval_explanations?.[0]?.explanation;
    const whyLine = firstWhy
      ? `Why: ${firstWhy.eligibility_reason || '-'} | freshness=${firstWhy.freshness || '-'} | outcome=${firstWhy.outcome_tag || '-'}`
      : null;
    const sample =
      stage.retrieved_memories?.[0] ||
      stage.memory_notes?.[0] ||
      'No retrieval context attached.';
    return [headline, whyLine ? `  ${whyLine}` : `  ${sample}`, ''];
  });
}

/**
 * Produce display lines summarizing a trade journal's entries.
 * @param {Object} journal - Object containing a list of journal entries under `entries`.
 * @returns {string[]} An array of lines; each entry is formatted as `opened_at | symbol | journal_status | planned_side | realized_pnl`, or `['No trade journal entries yet.']` when there are no entries.
 */
function getJournalLines(journal) {
  if (!journal?.entries?.length) {
    return ['No trade journal entries yet.'];
  }
  return journal.entries.map(
    (entry) =>
      `${entry.opened_at} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`,
  );
}

/**
 * Produce display lines summarizing recent run records for the dashboard.
 *
 * @param {object} recentRuns - Snapshot of recent runs.
 * @param {boolean} [recentRuns.available] - If false, the runs are unavailable and `error` may explain why.
 * @param {string} [recentRuns.error] - Error message when unavailable.
 * @param {Array} [recentRuns.runs] - Array of run records; each record is expected to include `created_at`, `symbol`, `interval`, `approved`, and `run_id`.
 * @returns {string[]} An array of lines for display:
 *   - If `available === false`, returns the unavailable message lines (including the error if present).
 *   - If there are no runs, returns a single line: `"No recent runs recorded yet."`.
 *   - Otherwise returns one line per run formatted as: "<created_at> | <symbol> | <interval> | approved=<approved> | <run_id>".
 */
function getRecentRunsLines(recentRuns) {
  if (recentRuns?.available === false) {
    return renderUnavailableMessage(recentRuns.error);
  }
  if (!recentRuns?.runs?.length) {
    return ['No recent runs recorded yet.'];
  }
  return recentRuns.runs.map(
    (run) =>
      `${run.created_at} | ${run.symbol} | ${run.interval} | approved=${run.approved} | ${run.run_id}`,
  );
}

/**
 * Format an instruction result into display-ready text lines.
 * @param {Object|null} result - The instruction result object (or null/undefined). Expected shape: `{ applied?: boolean, instruction?: { summary?: string, rationale?: string, should_update_preferences?: boolean, requires_confirmation?: boolean, preference_update?: Object } }`.
 * @returns {string[]} An array of human-readable lines summarizing the instruction: a summary, whether preferences should be updated, whether confirmation is required, whether the instruction was applied, the rationale, and a formatted preference-update line (or example help lines when `result` is falsy).
 */
function getInstructionResultLines(result) {
  if (!result) {
    return [
      'Type a safe operator instruction.',
      'Examples:',
      '  make the system conservative',
      '  switch to capital preservation',
    ];
  }
  const instruction = result.instruction || {};
  const update = instruction.preference_update || {};
  const updateLines = Object.entries(update)
    .filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    )
    .map(
      ([key, value]) =>
        `${key}=${Array.isArray(value) ? value.join(',') : value}`,
    );
  return [
    `Summary: ${instruction.summary ?? '-'}`,
    `Update Preferences: ${instruction.should_update_preferences ?? false}`,
    `Requires Confirmation: ${instruction.requires_confirmation ?? false}`,
    `Applied: ${result.applied ? 'yes' : 'no'}`,
    `Rationale: ${instruction.rationale ?? '-'}`,
    `Preference Update: ${updateLines.join(' | ') || '-'}`,
  ];
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

function renderLinesFallback(title, available, error, fallback) {
  if (available === false) {
    return [
      fallback,
      error || 'The runtime writer currently owns the database.',
    ];
  }
  return null;
}

function failedCheckNames(section) {
  const failed = (section?.checks || [])
    .filter((item) => item.blocking !== false && !item.passed)
    .map((item) => item.name)
    .slice(0, 3);
  return failed.length ? failed.join(', ') : '-';
}

function sourceHealthSummaryLine(summary) {
  if (!summary) {
    return '-';
  }
  return `fresh ${summary.fresh ?? 0} / missing ${summary.missing ?? 0} / unknown ${summary.unknown ?? 0}`;
}

function readinessLines(data) {
  const readiness = data.v1Readiness || {};
  const broker = data.broker || {};
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

function providerLines(data) {
  const diagnostics = data.providerDiagnostics || {};
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
    ...(warnings.length ? warnings.slice(0, 2) : ['No provider warnings.']),
  ];
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
  const preferences = data.preferences;
  const calendar = data.calendar;
  const broker = data.broker;
  const marketCache = data.marketCache;
  const marketContext = data.marketContext;
  const latestSnapshot = data.review.record?.artifacts?.snapshot;
  const agentActivity = data.agentActivity;
  const agentEvents = agentActivity?.recent_stage_events || [];
  const currentCycleLines = compact
    ? [
        `Runtime: ${runtime.runtime_state}`,
        `Mode: ${runtime.runtime_mode ?? runtime.state?.runtime_mode ?? data.doctor?.runtime_mode ?? '-'}`,
        `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
        `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
        `Status: ${runtime.status_message}`,
        `Current Stage: ${agentActivity?.current_stage ?? '-'}`,
        `Stage Status: ${agentActivity?.current_stage_status ?? '-'}`,
        `Consensus: ${data.review.record?.artifacts?.consensus?.alignment_level ?? '-'}`,
        `Context Quality: ${(marketContext?.contextPack?.data_quality_flags || []).join(', ') || '-'}`,
        `Last Outcome: ${agentActivity?.last_outcome_message ?? 'Waiting for a completed symbol or service result.'}`,
      ]
    : [
        `Runtime: ${runtime.runtime_state}`,
        `Mode: ${runtime.runtime_mode ?? runtime.state?.runtime_mode ?? data.doctor?.runtime_mode ?? '-'}`,
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
        `Context Pack: ${marketContext?.contextPack?.summary ?? '-'}`,
        `Context Quality: ${(marketContext?.contextPack?.data_quality_flags || []).join(', ') || '-'}`,
        '',
        `Last Outcome Type: ${agentActivity?.last_outcome_type ?? '-'}`,
        `Last Outcome: ${agentActivity?.last_outcome_message ?? 'Waiting for a completed symbol or service result.'}`,
      ];
  const systemLines = compact
    ? [
        `Model: ${doctor.model}`,
        `Runtime Mode: ${doctor.runtime_mode ?? '-'}`,
        `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
        `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
        `Broker Backend: ${broker?.backend ?? '-'}`,
        `Broker State: ${broker?.state ?? '-'}`,
        `Camofox: ${data.camofoxService?.message ?? '-'}`,
        `Research: ${data.research?.status ?? '-'} (${data.research?.backend ?? '-'})`,
        `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
        `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
        `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
        `Market Session: ${formatMarketSession(calendar.session)}`,
      ]
    : [
        `Model: ${doctor.model}`,
        `Runtime Mode: ${doctor.runtime_mode ?? '-'}`,
        `Base URL: ${doctor.base_url}`,
        `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
        `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
        `Runtime Dir: ${doctor.runtime_dir}`,
        `Database: ${doctor.database}`,
        `Broker Backend: ${broker?.backend ?? '-'}`,
        `Broker State: ${broker?.state ?? '-'}`,
        `Broker Health: ${broker?.healthcheck?.message ?? broker?.message ?? '-'}`,
        `Camofox: ${data.camofoxService?.message ?? '-'}`,
        `Camofox Owned: ${data.camofoxService?.app_owned ? 'yes' : 'no'}`,
        `Camofox URL: ${data.camofoxService?.base_url ?? '-'}`,
        `Research: ${data.research?.status ?? '-'} (${data.research?.backend ?? '-'})`,
        `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
        `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
        `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
        `Provider Warnings: ${(data.providerDiagnostics?.warnings || []).length}`,
        `Default Symbols: ${defaultSymbolsFromPreferences(preferences)}`,
        `Market Session: ${formatMarketSession(calendar.session)}`,
        `News Tool: ${data.news?.mode ?? 'off'}`,
        `Cached Snapshots: ${marketCache.count}`,
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
        panel('WHY THIS CONTEXT WAS USED', retrievalLines.slice(0, 12), 'yellow'),
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
  const terminalRows = process.stdout.rows || 36;
  const terminalColumns = process.stdout.columns || 100;
  const navRows = terminalColumns < 140 ? 2 : 1;
  const headerRows = 1 + navRows + (actionMessage ? 1 : 0);
  const footerRows = 1;
  const bodyHeight = Math.max(1, terminalRows - headerRows - footerRows);
  const compact = terminalRows <= 30 || terminalColumns <= 110;

  const view = getPageView(
    page,
    data,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
    compact,
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
      `page ${pageIndex}/7: ${pageLabel}  |  1 overview  2 runtime  3 portfolio  4 review  5 memory  6 chat  7 settings  |  r refresh  o one-shot  s start  x stop  R restart  q quit${busy ? '  |  working...' : ''}`,
    ),
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
    if (key.rightArrow || input === '\t') {
      nextPage();
      return;
    }
    if (key.leftArrow) {
      prevPage();
      return;
    }
    if (
      ['1', '2', '3', '4', '5', '6', '7'].includes(input) &&
      !['chat', 'settings'].includes(page)
    ) {
      setPage(pages[Number(input) - 1]);
      return;
    }
    if (
      page === 'chat' &&
      handleChatInput(input, key, { sendChat, setChatDraft, setChatPersona })
    ) {
      return;
    }
    if (
      page === 'settings' &&
      handleSettingsInput(input, key, {
        sendInstruction,
        setInstructionDraft,
        setInstructionMode,
      })
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

await import('ink').then(({ render }) => {
  render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
});
