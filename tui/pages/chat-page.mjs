import { Box } from 'ink';
import React from 'react';
import { formatPersona } from '../copy.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

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

export { ChatPage };
