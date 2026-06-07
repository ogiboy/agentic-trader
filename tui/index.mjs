import { pathToFileURL } from 'node:url';
import React from 'react';

import { once } from './src/cli-runtime.mjs';
import {
  InteractiveDashboardApp,
  StaticDashboardApp,
} from './src/DashboardApp.mjs';

const e = React.createElement;

const isDirectRun =
  Boolean(process.argv[1]) &&
  import.meta.url === pathToFileURL(process.argv[1]).href;

if (isDirectRun) {
  await import('ink').then(({ render }) => {
    render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
  });
}

export {
  formatPersona,
  getPageLabel,
  rotateInstructionMode,
  rotatePersona,
} from './src/copy.mjs';
export {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  getSupervisorLogLines,
} from './src/dashboard-defaults.mjs';
export { useDashboardState } from './src/dashboard-state.mjs';
export {
  InteractiveDashboardApp,
  StaticDashboardApp,
} from './src/DashboardApp.mjs';
export { DashboardView } from './src/DashboardView.mjs';
export {
  handleChatInput,
  handleDashboardInput,
  handleGlobalInput,
  handleSettingsInput,
} from './src/input.mjs';
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
} from './src/line-formatters.mjs';

export { normalizeChatHistory } from './src/chat-history.mjs';
