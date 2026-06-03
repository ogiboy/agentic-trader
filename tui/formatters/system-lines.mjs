import { defaultSymbolsFromPreferences } from "../dashboard-defaults.mjs";

function getStatusBorderColor(runtimeState) {
  switch (runtimeState) {
    case "active":
      return "green";
    case "stale":
      return "yellow";
    default:
      return "cyan";
  }
}

function formatMarketSession(session) {
  if (!session) return "unavailable";
  return `${session.venue} ${session.session_state}`;
}

function formatMarketSessionWithTradable(session) {
  if (!session) return "unavailable";
  return `${session.venue} ${session.session_state} tradable=${session.tradable_now}`;
}

function formatMTFSnapshot(snapshot) {
  if (!snapshot) return "-";
  return `${snapshot.mtf_alignment} @ ${snapshot.higher_timeframe}`;
}

function renderLinesFallback(title, available, error, fallback) {
  if (available === false) {
    return [
      fallback,
      error || "The runtime writer currently owns the database.",
    ];
  }
  return null;
}

function failedCheckNames(section) {
  const failed = (section?.checks || [])
    .filter((item) => item.blocking !== false && !item.passed)
    .map((item) => item.name)
    .slice(0, 3);
  return failed.length ? failed.join(", ") : "-";
}

function sourceHealthSummaryLine(summary) {
  if (!summary) {
    return "-";
  }
  return `fresh ${summary.fresh ?? 0} / missing ${summary.missing ?? 0} / unknown ${summary.unknown ?? 0}`;
}

function readinessLines(data) {
  const readiness = data.v1Readiness || {};
  const broker = data.broker || {};
  const paper = readiness.paper_operations || {};
  const alpaca = readiness.alpaca_paper || {};
  return [
    `Can run local paper cycle: ${paper.allowed ? "yes" : "no"}`,
    `Why paper cycle is blocked: ${failedCheckNames(paper)}`,
    `Can use Alpaca paper: ${alpaca.ready ? "yes" : "no"}`,
    `Why Alpaca paper is blocked: ${failedCheckNames(alpaca)}`,
    `Backend: ${broker.backend ?? "-"}`,
    `External paper mode active: ${broker.external_paper ? "yes" : "no"}`,
    `Kill Switch: ${broker.kill_switch_active ? "active" : "inactive"}`,
    `Broker Health: ${broker.healthcheck?.message ?? broker.message ?? "-"}`,
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
    `Market Provider: ${market.selected_provider ?? "-"}`,
    `Market Role: ${market.selected_role ?? "-"}`,
    `News Mode: ${diagnostics.news?.mode ?? "-"}`,
    `Finnhub Key: ${keys.finnhub ? "configured" : "missing"}`,
    `FMP Key: ${keys.fmp ? "configured" : "missing"}`,
    `Alpaca Key: ${keys.alpaca ? "configured" : "missing"}`,
    ...(warnings.length ? warnings.slice(0, 2) : ["No provider warnings."]),
  ];
}

function ownershipMode(data, tool) {
  return data.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? "undecided";
}

function overviewRuntimeMode(runtime, data) {
  return (
    runtime.runtime_mode ??
    runtime.state?.runtime_mode ??
    data.doctor?.runtime_mode ??
    "-"
  );
}

function compactCurrentCycleLines(data) {
  const runtime = data.status;
  const marketContext = data.marketContext;
  const agentActivity = data.agentActivity;
  return [
    `Runtime: ${runtime.runtime_state}`,
    `Mode: ${overviewRuntimeMode(runtime, data)}`,
    `Current Symbol: ${runtime.state?.current_symbol ?? "-"}`,
    `Cycle Count: ${runtime.state?.cycle_count ?? "-"}`,
    `Status: ${runtime.status_message}`,
    `Current Stage: ${agentActivity?.current_stage ?? "-"}`,
    `Stage Status: ${agentActivity?.current_stage_status ?? "-"}`,
    `Consensus: ${data.review.record?.artifacts?.consensus?.alignment_level ?? "-"}`,
    `Context Quality: ${(marketContext?.contextPack?.data_quality_flags || []).join(", ") || "-"}`,
    `Last Outcome: ${agentActivity?.last_outcome_message ?? "Waiting for a completed symbol or service result."}`,
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
    `Live Process: ${runtime.live_process ? "yes" : "no"}`,
    `Current Symbol: ${runtime.state?.current_symbol ?? "-"}`,
    `Cycle Count: ${runtime.state?.cycle_count ?? "-"}`,
    `Status: ${runtime.status_message}`,
    `Current Note: ${runtime.state?.message ?? "-"}`,
    `Current Stage: ${agentActivity?.current_stage ?? "-"}`,
    `Stage Status: ${agentActivity?.current_stage_status ?? "-"}`,
    `Stage Detail: ${agentActivity?.current_stage_message ?? "-"}`,
    `Last Completed Stage: ${agentActivity?.last_completed_stage ?? "-"}`,
    `Completed Detail: ${agentActivity?.last_completed_message ?? "-"}`,
    `Consensus: ${data.review.record?.artifacts?.consensus?.alignment_level ?? "-"}`,
    `MTF Alignment: ${latestSnapshot?.mtf_alignment ?? "-"}`,
    `Higher Timeframe: ${latestSnapshot?.higher_timeframe ?? "-"}`,
    `Context Pack: ${marketContext?.contextPack?.summary ?? "-"}`,
    `Context Quality: ${(marketContext?.contextPack?.data_quality_flags || []).join(", ") || "-"}`,
    "",
    `Last Outcome Type: ${agentActivity?.last_outcome_type ?? "-"}`,
    `Last Outcome: ${agentActivity?.last_outcome_message ?? "Waiting for a completed symbol or service result."}`,
  ];
}

function getCurrentCycleLines(data, compact) {
  if (compact) {
    return compactCurrentCycleLines(data);
  }
  return fullCurrentCycleLines(data);
}

function compactSystemLines(data) {
  const doctor = data.doctor;
  const calendar = data.calendar;
  const broker = data.broker;
  return [
    `Model: ${doctor.model}`,
    `Runtime Mode: ${doctor.runtime_mode ?? "-"}`,
    `Ollama Reachable: ${doctor.ollama_reachable ? "yes" : "no"}`,
    `Model Available: ${doctor.model_available ? "yes" : "no"}`,
    `Broker Backend: ${broker?.backend ?? "-"}`,
    `Broker State: ${broker?.state ?? "-"}`,
    `Ollama Ownership: ${ownershipMode(data, "ollama")}`,
    `Firecrawl Ownership: ${ownershipMode(data, "firecrawl")}`,
    `Camofox Ownership: ${ownershipMode(data, "camofox")}`,
    `Camofox: ${data.camofoxService?.message ?? "-"}`,
    `Research: ${data.research?.status ?? "-"} (${data.research?.backend ?? "-"})`,
    `Research Control: ${data.research?.cycleControl?.status ?? "-"}`,
    `Research Trigger: ${data.research?.cycleControl?.trigger_now_requested ? "requested" : "clear"}`,
    `Research Digest Replay: ${data.research?.latestDigestReplay?.available ? "available" : "-"}`,
    `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
    `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? "yes" : "no"}`,
    `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? "yes" : "no"}`,
    `Market Session: ${formatMarketSession(calendar.session)}`,
  ];
}

function fullSystemLines(data) {
  const doctor = data.doctor;
  const preferences = data.preferences;
  const calendar = data.calendar;
  const broker = data.broker;
  const marketCache = data.marketCache;
  return [
    `Model: ${doctor.model}`,
    `Runtime Mode: ${doctor.runtime_mode ?? "-"}`,
    `Base URL: ${doctor.base_url}`,
    `Ollama Reachable: ${doctor.ollama_reachable ? "yes" : "no"}`,
    `Model Available: ${doctor.model_available ? "yes" : "no"}`,
    `Runtime Dir: ${doctor.runtime_dir}`,
    `Database: ${doctor.database}`,
    `Broker Backend: ${broker?.backend ?? "-"}`,
    `Broker State: ${broker?.state ?? "-"}`,
    `Broker Health: ${broker?.healthcheck?.message ?? broker?.message ?? "-"}`,
    `Ollama Ownership: ${ownershipMode(data, "ollama")}`,
    `Firecrawl Ownership: ${ownershipMode(data, "firecrawl")}`,
    `Camofox Ownership: ${ownershipMode(data, "camofox")}`,
    `Camofox: ${data.camofoxService?.message ?? "-"}`,
    `Camofox Owned: ${data.camofoxService?.app_owned ? "yes" : "no"}`,
    `Camofox URL: ${data.camofoxService?.base_url ?? "-"}`,
    `Research: ${data.research?.status ?? "-"} (${data.research?.backend ?? "-"})`,
    `Research Control: ${data.research?.cycleControl?.status ?? "-"}`,
    `Research Trigger: ${data.research?.cycleControl?.trigger_now_requested ? "requested" : "clear"}`,
    `Research Digest Replay: ${data.research?.latestDigestReplay?.available ? "available" : "-"}`,
    `Research Sources: ${sourceHealthSummaryLine(data.research?.source_health_summary)}`,
    `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? "yes" : "no"}`,
    `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? "yes" : "no"}`,
    `Provider Warnings: ${(data.providerDiagnostics?.warnings || []).length}`,
    `Default Symbols: ${defaultSymbolsFromPreferences(preferences)}`,
    `Market Session: ${formatMarketSession(calendar.session)}`,
    `News Tool: ${data.news?.mode ?? "off"}`,
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
    return ["No live agent stage events yet."];
  }
  return agentEvents.map(
    (event) =>
      `${event.created_at} | ${event.stage} | ${event.status} | ${event.message}`,
  );
}

export {
  compactCurrentCycleLines,
  compactSystemLines,
  failedCheckNames,
  formatMarketSession,
  formatMarketSessionWithTradable,
  formatMTFSnapshot,
  fullCurrentCycleLines,
  fullSystemLines,
  getAgentEventLines,
  getCurrentCycleLines,
  getStatusBorderColor,
  getSystemLines,
  overviewRuntimeMode,
  ownershipMode,
  providerLines,
  readinessLines,
  renderLinesFallback,
  sourceHealthSummaryLine,
};
