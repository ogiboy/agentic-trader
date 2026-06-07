import { getFundamentalAssessmentLines } from "../review-lines.mjs";

function renderUnavailableMessage(error) {
  return [
    "unavailable",
    error || "The runtime writer currently owns the database.",
  ];
}

function getTradeContextLines(tradeContext) {
  if (tradeContext?.available === false) {
    return renderUnavailableMessage(tradeContext.error);
  }
  if (!tradeContext?.record) {
    return ["No persisted trade context is available yet."];
  }
  const record = tradeContext.record;
  return [
    `Trade ID: ${record.trade_id}`,
    `Run ID: ${record.run_id ?? "-"}`,
    `Consensus: ${record.consensus.alignment_level}`,
    ...getFundamentalAssessmentLines(record.fundamental_assessment),
    `Manager Rationale: ${record.manager_rationale}`,
    `Execution Rationale: ${record.execution_rationale}`,
    `Execution Backend: ${record.execution_backend ?? "-"}`,
    `Execution Adapter: ${record.execution_adapter ?? "-"}`,
    `Execution Outcome: ${record.execution_outcome_status ?? "-"}`,
    `Rejection Reason: ${record.execution_rejection_reason ?? "-"}`,
    `Review Summary: ${record.review_summary}`,
    `Routed Models: ${
      Object.entries(record.routed_models || {})
        .map(([role, model]) => `${role}:${model}`)
        .join(" | ") || "-"
    }`,
    `Memory Roles: ${Object.keys(record.retrieved_memory_summary || {}).join(", ") || "-"}`,
    `Tool Roles: ${Object.keys(record.tool_outputs || {}).join(", ") || "-"}`,
  ];
}

function getMarketContextLines(marketContext) {
  if (marketContext?.available === false) {
    return renderUnavailableMessage(marketContext.error);
  }
  const pack = marketContext?.contextPack;
  if (!pack) {
    return ["No persisted Market Context Pack is available yet."];
  }
  const horizons = (pack.horizons || [])
    .slice(0, 5)
    .map(
      (item) =>
        `${item.horizon_bars}b ${item.trend_vote} return=${item.return_pct ?? "-"} drawdown=${item.max_drawdown_pct ?? "-"}`,
    );
  return [
    `Summary: ${pack.summary || "-"}`,
    `Lookback: ${pack.lookback ?? "-"} | Interval: ${pack.interval}`,
    `Window: ${pack.window_start ?? "-"} -> ${pack.window_end ?? "-"}`,
    `Bars: ${pack.bars_analyzed}/${pack.bars_expected ?? "?"} coverage=${pack.coverage_ratio ?? "?"}`,
    `Interval Semantics: ${pack.interval_semantics}`,
    `HTF: ${pack.higher_timeframe} used=${pack.higher_timeframe_used}`,
    `Quality: ${(pack.data_quality_flags || []).join(", ") || "-"}`,
    `Anomalies: ${(pack.anomaly_flags || []).join(", ") || "-"}`,
    ...horizons,
  ];
}

export {
  getMarketContextLines,
  getTradeContextLines,
  renderUnavailableMessage,
};
