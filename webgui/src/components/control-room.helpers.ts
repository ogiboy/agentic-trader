import type { DashboardData, TabId } from './control-room/types';

export type {
  DashboardData,
  InstructionMode,
  KeyValueItems,
  MessageTone,
  PanelAccent,
  ProposalActionKind,
  TabId,
  ToolActionKind,
} from './control-room/types';

export {
  accountCurrency,
  canonicalLines,
  marketContextLines,
  positionPlanCoverageLines,
  proposalApprovalBlockedReason,
  proposalHeadline,
  proposalLines,
  tradeContextLines,
  unavailableSectionLines,
} from './control-room/context-formatting';
export {
  failedCheckNames,
  formatSourceHealthCount,
  localizedStatusText,
  localToolActionLines,
  localToolLines,
  providerWarningLines,
  readinessLines,
  sourceHealthSummaryLine,
  systemStatusItems,
} from './control-room/diagnostics-formatting';
export {
  cx,
  formatList,
  formatNumber,
  formatPercent,
  formatTimestamp,
} from './control-room/formatting';

export const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'runtime', label: 'Runtime' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'proposals', label: 'Proposals' },
  { id: 'review', label: 'Review' },
  { id: 'memory', label: 'Decision Evidence' },
  { id: 'chat', label: 'Chat' },
  { id: 'settings', label: 'Settings' },
];

export const marketLensImage =
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80';

type ChatHistoryEntry = {
  persona?: string;
  response_text?: string;
  user_message?: string;
};

/**
 * Convert dashboard chat history into a simple list of chat records.
 *
 * @param data - Dashboard payload that may contain `chatHistory.entries`; `null` or missing entries result in an empty list.
 * @returns An array of objects each with `user`, `persona`, and `response` properties, produced by reversing the original `entries` order.
 */
export function normalizeChatHistory(
  data: DashboardData | null,
): Array<Record<string, string>> {
  const entries = (data?.chatHistory?.entries || []) as ChatHistoryEntry[];
  return [...entries].reverse().map((entry) => ({
    user: entry.user_message ?? '',
    persona: entry.persona ?? '',
    response: entry.response_text ?? '',
  }));
}
