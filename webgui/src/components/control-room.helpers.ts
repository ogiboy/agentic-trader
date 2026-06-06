import { asRecord, asRecordArray, asString } from './control-room/payload';
import type { DashboardData } from './control-room/types';

export type {
  DashboardData,
  DashboardRecord,
  InstructionMode,
  InstructionResult,
  KeyValueItems,
  MessageTone,
  PanelAccent,
  ProposalActionKind,
  TabId,
  ToolActionKind
} from './control-room/types';

export
{
  accountCurrency,
  canonicalLines,
  marketContextLines,
  positionPlanCoverageLines,
  proposalApprovalBlockedReason,
  proposalHeadline,
  proposalHeadlineWithCopy,
  proposalLines,
  tradeContextLines,
  unavailableSectionLines
} from './control-room/context-formatting';
export
{
  diagnosticsCopy,
  failedCheckNames,
  formatSourceHealthCount,
  localizedStatusText,
  providerWarningLines,
  readinessLines,
  sourceHealthSummaryLine,
  systemStatusItems
} from './control-room/diagnostics-formatting';
export type {
  ControlRoomDiagnosticsCopySource
} from './control-room/diagnostics-formatting';
export
{
  localToolActionLines,
  localToolLines
} from './control-room/diagnostics-tool-lines';
export
{
  cx,
  formatList,
  formatNumber,
  formatPercent,
  formatTimestamp
} from './control-room/formatting';
export
{
  asRecord,
  asRecordArray,
  asString,
  asStringArray,
  isRecord
} from './control-room/payload';

export const marketLensImage =
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80';

/**
 * Convert dashboard chat history into a simple list of chat records.
 *
 * @param data - Dashboard payload that may contain `chatHistory.entries`; `null` or missing entries result in an empty list.
 * @returns An array of objects each with `user`, `persona`, and `response` properties, produced by reversing the original `entries` order.
 */
export function normalizeChatHistory(
  data: DashboardData | null,
): Array<Record<string, string>> {
  const chatHistory = asRecord(data?.chatHistory);
  const entries = asRecordArray(chatHistory.entries);
  return [...entries].reverse().map((entry) => ({
    user: asString(entry.user_message, ''),
    persona: asString(entry.persona, ''),
    response: asString(entry.response_text, ''),
  }));
}
