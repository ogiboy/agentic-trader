import {
  CHAT_PERSONAS,
  formatChatPersona,
  type ChatPersona,
} from '@/lib/chat-personas';

import type { DashboardData } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { Panel, TextList } from './primitives';

export function ChatView({
  copy,
  dashboard,
  chatPersona,
  chatHistory,
  chatDraft,
  busy,
  onChatPersonaChange,
  onChatDraftChange,
  onSendChat,
}: Readonly<{
  copy: ControlRoomCopy;
  dashboard: DashboardData;
  chatPersona: ChatPersona;
  chatHistory: Array<Record<string, string>>;
  chatDraft: string;
  busy: string | null;
  onChatPersonaChange: (value: ChatPersona) => void;
  onChatDraftChange: (value: string) => void;
  onSendChat: () => Promise<void>;
}>) {
  return (
    <div className="grid grid--2">
      <Panel title={copy.chat.panels.operatorChat} accent="lime">
        <div className="form-row">
          <label className="field-label">
            <span>{copy.chat.role}</span>
            <select
              value={chatPersona}
              onChange={(event) =>
                onChatPersonaChange(event.target.value as ChatPersona)
              }
            >
              {CHAT_PERSONAS.map((persona) => (
                <option key={persona} value={persona}>
                  {formatChatPersona(persona)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="chat-log">
          {chatHistory.length ? (
            chatHistory.map((entry, index) => (
              <article className="chat-bubble" key={`${entry.user}-${index}`}>
                <div className="chat-bubble__meta">{copy.chat.userLabel}</div>
                <p>{entry.user}</p>
                <div className="chat-bubble__meta">
                  {formatChatPersona(entry.persona)}
                </div>
                <p>{entry.response}</p>
              </article>
            ))
          ) : (
            <p className="empty-copy">{copy.chat.empty}</p>
          )}
        </div>
        <div className="composer">
          <textarea
            value={chatDraft}
            onChange={(event) => onChatDraftChange(event.target.value)}
            placeholder={copy.chat.placeholder}
          />
          <button
            className="button button--solid"
            disabled={busy === 'chat'}
            onClick={() => void onSendChat()}
            type="button"
          >
            {busy === 'chat' ? copy.common.working : copy.chat.send}
          </button>
        </div>
      </Panel>
      <Panel title={copy.chat.panels.decisionWorkflowContext} accent="cyan">
        <TextList
          items={[
            `${copy.chat.workflow.currentStage}: ${dashboard.agentActivity?.current_stage ?? '-'}`,
            `${copy.chat.workflow.stageStatus}: ${dashboard.agentActivity?.current_stage_status ?? '-'}`,
            `${copy.chat.workflow.stageDetail}: ${dashboard.agentActivity?.current_stage_message ?? '-'}`,
            `${copy.chat.workflow.lastCompleted}: ${dashboard.agentActivity?.last_completed_stage ?? '-'}`,
            `${copy.chat.workflow.completedDetail}: ${dashboard.agentActivity?.last_completed_message ?? '-'}`,
            `${copy.chat.workflow.toolRoles}: ${Object.keys(dashboard.tradeContext?.record?.tool_outputs || {}).join(', ') || '-'}`,
            `${copy.chat.workflow.memoryRoles}: ${Object.keys(dashboard.tradeContext?.record?.retrieved_memory_summary || {}).join(', ') || '-'}`,
          ]}
        />
      </Panel>
    </div>
  );
}
