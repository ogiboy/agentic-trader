import {
  defaultSymbolsFromPreferences,
} from './dashboard-defaults.mjs';
import {
  getFundamentalAssessmentLines,
} from './review-lines.mjs';

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
  return explorer.matches.map((match) => {
    const reason =
      match.explanation?.eligibility_reason || match.retrieval_source;
    return `${match.created_at} | ${match.symbol} | score=${match.similarity_score} | why=${reason} | ${match.regime} | ${match.strategy_family} | ${match.summary}`;
  });
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

/**
 * Build an array of display lines summarizing market/news provider selection, API key configuration, and up to two provider warnings.
 * @param {object} data - Object containing provider diagnostics under `providerDiagnostics`. Expected shape: `{ market_data?, configured_keys?, warnings? }`.
 * @returns {string[]} An ordered list of lines:
 *   - "Market Provider: <provider or '-'">"
 *   - "Market Role: <role or '-'">"
 *   - "News Mode: <mode or '-'">"
 *   - "Finnhub Key: 'configured' or 'missing'"
 *   - "FMP Key: 'configured' or 'missing'"
 *   - "Alpaca Key: 'configured' or 'missing'"
 *   - Up to two warning strings from `providerDiagnostics.warnings`, or a single "No provider warnings." line when none exist.
 */
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
 * Resolve the ownership decision mode for a specific tool.
 * @param {Object} data - Dashboard data containing tool ownership decisions.
 * @param {string} tool - Tool identifier to look up in decisions_by_tool.
 * @returns {string} The ownership mode for the tool, or `'undecided'` if no decision is present.
 */
function ownershipMode(data, tool) {
  return data.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? 'undecided';
}

/**
 * Resolve the effective runtime mode to display in the dashboard.
 *
 * Checks the runtime object and dashboard data for a configured runtime mode and
 * returns the first found value, or `'-'` when none is present.
 *
 * @param {object} runtime - Runtime state object (may include `runtime_mode` or nested `state.runtime_mode`).
 * @param {object} data - Dashboard data object (may include `doctor.runtime_mode`).
 * @returns {string} The resolved runtime mode, or `'-'` if no mode is available.
 */
function overviewRuntimeMode(runtime, data) {
  return (
    runtime.runtime_mode ??
    runtime.state?.runtime_mode ??
    data.doctor?.runtime_mode ??
    '-'
  );
}

function compactCurrentCycleLines(data) {
  const runtime = data.status;
  const marketContext = data.marketContext;
  const agentActivity = data.agentActivity;
  return [
    `Runtime: ${runtime.runtime_state}`,
    `Mode: ${overviewRuntimeMode(runtime, data)}`,
    `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
    `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
    `Status: ${runtime.status_message}`,
    `Current Stage: ${agentActivity?.current_stage ?? '-'}`,
    `Stage Status: ${agentActivity?.current_stage_status ?? '-'}`,
    `Consensus: ${data.review.record?.artifacts?.consensus?.alignment_level ?? '-'}`,
    `Context Quality: ${(marketContext?.contextPack?.data_quality_flags || []).join(', ') || '-'}`,
    `Last Outcome: ${agentActivity?.last_outcome_message ?? 'Waiting for a completed symbol or service result.'}`,
  ];
}

function fullCurrentCycleLines(data) {
  const runtime = data.status;
  const marketContext = data.marketContext;
  const latestSnapshot = data.review.record?.artifacts?.snapshot;
  const agentActivity = data.agentActivity;
  return [
    `Runtime: ${runtime.runtime_state}`,
    `Mode: ${overviewRuntimeMode(runtime, data)}`,
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
}

function getCurrentCycleLines(data, compact) {
  if (compact) {
    return compactCurrentCycleLines(data);
  }
  return fullCurrentCycleLines(data);
}

/**
 * Produce a compact list of system-status lines for the dashboard.
 *
 * @param {Object} data - Dashboard data object containing system snapshots (e.g., `doctor`, `calendar`, `broker`, `research`, `camofoxService`, `v1Readiness`, and ownership decisions).
 * @returns {string[]} An ordered array of formatted status lines suitable for the compact "SYSTEM" panel. Each element is a single-line summary (model, runtime mode, provider reachability/availability, broker info, ownership modes, research status, readiness flags, and market session).
 */
function compactSystemLines(data) {
  const doctor = data.doctor;
  const calendar = data.calendar;
  const broker = data.broker;
  return [
    `Model: ${doctor.model}`,
    `Runtime Mode: ${doctor.runtime_mode ?? '-'}`,
    `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
    `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
    `Broker Backend: ${broker?.backend ?? '-'}`,
    `Broker State: ${broker?.state ?? '-'}`,
    `Ollama Ownership: ${ownershipMode(data, 'ollama')}`,
    `Firecrawl Ownership: ${ownershipMode(data, 'firecrawl')}`,
    `Camofox Ownership: ${ownershipMode(data, 'camofox')}`,
    `Camofox: ${data.camofoxService?.message ?? '-'}`,
    `Research: ${data.research?.status ?? '-'} (${data.research?.backend ?? '-'})`,
    `Research Control: ${data.research?.cycleControl?.status ?? '-'}`,
    `Research Trigger: ${data.research?.cycleControl?.trigger_now_requested ? 'requested' : 'clear'}`,
    `Research Digest Replay: ${data.research?.latestDigestReplay?.available ? 'available' : '-'}`,
    `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
    `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
    `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
    `Market Session: ${formatMarketSession(calendar.session)}`,
  ];
}

/**
 * Build a comprehensive list of human-readable system status lines for the full "SYSTEM" panel.
 *
 * @param {object} data - Dashboard data object containing doctor, preferences, calendar, broker, marketCache and other subsystem summaries used to generate the lines.
 * @returns {string[]} An ordered array of formatted status lines covering model/runtime info, broker status, ownership of tooling, research and readiness summaries, provider warnings, default symbols, market session, news tool mode, and cached snapshot count.
 */
function fullSystemLines(data) {
  const doctor = data.doctor;
  const preferences = data.preferences;
  const calendar = data.calendar;
  const broker = data.broker;
  const marketCache = data.marketCache;
  return [
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
    `Ollama Ownership: ${ownershipMode(data, 'ollama')}`,
    `Firecrawl Ownership: ${ownershipMode(data, 'firecrawl')}`,
    `Camofox Ownership: ${ownershipMode(data, 'camofox')}`,
    `Camofox: ${data.camofoxService?.message ?? '-'}`,
    `Camofox Owned: ${data.camofoxService?.app_owned ? 'yes' : 'no'}`,
    `Camofox URL: ${data.camofoxService?.base_url ?? '-'}`,
    `Research: ${data.research?.status ?? '-'} (${data.research?.backend ?? '-'})`,
    `Research Control: ${data.research?.cycleControl?.status ?? '-'}`,
    `Research Trigger: ${data.research?.cycleControl?.trigger_now_requested ? 'requested' : 'clear'}`,
    `Research Digest Replay: ${data.research?.latestDigestReplay?.available ? 'available' : '-'}`,
    `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
    `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
    `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
    `Provider Warnings: ${(data.providerDiagnostics?.warnings || []).length}`,
    `Default Symbols: ${defaultSymbolsFromPreferences(preferences)}`,
    `Market Session: ${formatMarketSession(calendar.session)}`,
    `News Tool: ${data.news?.mode ?? 'off'}`,
    `Cached Snapshots: ${marketCache.count}`,
  ];
}

function getSystemLines(data, compact) {
  if (compact) {
    return compactSystemLines(data);
  }
  return fullSystemLines(data);
}

function getAgentEventLines(agentEvents) {
  if (!agentEvents.length) {
    return ['No live agent stage events yet.'];
  }
  return agentEvents.map(
    (event) =>
      `${event.created_at} | ${event.stage} | ${event.status} | ${event.message}`,
  );
}

export {
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
};
