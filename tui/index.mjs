import { pathToFileURL } from "node:url";
import React from "react";
import { normalizeChatHistory } from "./chat-history.mjs";
import { once } from "./cli-runtime.mjs";
import { InteractiveDashboardApp, StaticDashboardApp } from "./DashboardApp.mjs";

const e = React.createElement;

const isDirectRun =
  Boolean(process.argv[1]) &&
  import.meta.url === pathToFileURL(process.argv[1]).href;

if (isDirectRun) {
  await import("ink").then(({ render }) => {
    render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
  });
}

export {
  formatPersona,
  getPageLabel,
  rotateInstructionMode,
  rotatePersona,
} from "./copy.mjs";
export {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  getSupervisorLogLines,
} from "./dashboard-defaults.mjs";
export {
  handleChatInput,
  handleDashboardInput,
  handleGlobalInput,
  handleSettingsInput,
} from "./input.mjs";
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
} from "./line-formatters.mjs";
export { InteractiveDashboardApp, StaticDashboardApp } from "./DashboardApp.mjs";
export { DashboardView } from "./DashboardView.mjs";
export { useDashboardState } from "./dashboard-state.mjs";
export { normalizeChatHistory };
