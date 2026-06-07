import {
  CHAT_PERSONAS,
  formatChatPersona,
  type ChatPersona,
} from '@/lib/chat-personas';
import { useTranslations } from 'next-intl';

import type { DashboardData } from '../control-room.helpers';
import { asRecord, asString } from '../control-room.helpers';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Panel, TextList } from './Primitives';

function chatPersonaLabel(
  persona: unknown,
  labels: Readonly<Record<ChatPersona, string>>,
): string {
  if (typeof persona === 'string' && persona in labels) {
    return labels[persona as ChatPersona];
  }
  return formatChatPersona(persona);
}

export function ChatView({
  dashboard,
  chatPersona,
  chatHistory,
  chatDraft,
  busy,
  onChatPersonaChange,
  onChatDraftChange,
  onSendChat,
}: Readonly<{
  dashboard: DashboardData;
  chatPersona: ChatPersona;
  chatHistory: Array<Record<string, string>>;
  chatDraft: string;
  busy: string | null;
  onChatPersonaChange: (value: ChatPersona) => void;
  onChatDraftChange: (value: string) => void;
  onSendChat: () => Promise<void>;
}>) {
  const common = useTranslations('controlRoom.common');
  const t = useTranslations('controlRoom.chat');
  const personaLabels: Record<ChatPersona, string> = {
    operator_liaison: t('personas.operator_liaison'),
    portfolio_manager: t('personas.portfolio_manager'),
    regime_analyst: t('personas.regime_analyst'),
    risk_steward: t('personas.risk_steward'),
    strategy_selector: t('personas.strategy_selector'),
  };
  const agentActivity = asRecord(dashboard.agentActivity);
  const tradeContext = asRecord(dashboard.tradeContext);
  const tradeRecord = asRecord(tradeContext.record);
  const toolOutputs = asRecord(tradeRecord.tool_outputs);
  const retrievedMemory = asRecord(tradeRecord.retrieved_memory_summary);

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.operatorChat')} accent='lime'>
        <div className='form-row'>
          <div className='field-label'>
            <span>{t('role')}</span>
            <Select
              value={chatPersona}
              onValueChange={(value) =>
                onChatPersonaChange(value as ChatPersona)
              }
            >
              <SelectTrigger aria-label={t('role')} className='field-select'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHAT_PERSONAS.map((persona) => (
                  <SelectItem key={persona} value={persona}>
                    {chatPersonaLabel(persona, personaLabels)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className='chat-log'>
          {chatHistory.length ? (
            chatHistory.map((entry, index) => (
              <article className='chat-bubble' key={`${entry.user}-${index}`}>
                <div className='chat-bubble__meta'>{t('userLabel')}</div>
                <p>{entry.user}</p>
                <div className='chat-bubble__meta'>
                  {chatPersonaLabel(entry.persona, personaLabels)}
                </div>
                <p>{entry.response}</p>
              </article>
            ))
          ) : (
            <p className='empty-copy'>{t('empty')}</p>
          )}
        </div>
        <div className='composer'>
          <Textarea
            value={chatDraft}
            onChange={(event) => onChatDraftChange(event.target.value)}
            placeholder={t('placeholder')}
          />
          <button
            className='button button--solid'
            disabled={busy === 'chat'}
            onClick={() => void onSendChat()}
            type='button'
          >
            {busy === 'chat' ? common('working') : t('send')}
          </button>
        </div>
      </Panel>
      <Panel title={t('panels.decisionWorkflowContext')} accent='cyan'>
        <TextList
          items={[
            `${t('workflow.currentStage')}: ${asString(agentActivity.current_stage)}`,
            `${t('workflow.stageStatus')}: ${asString(agentActivity.current_stage_status)}`,
            `${t('workflow.stageDetail')}: ${asString(agentActivity.current_stage_message)}`,
            `${t('workflow.lastCompleted')}: ${asString(agentActivity.last_completed_stage)}`,
            `${t('workflow.completedDetail')}: ${asString(agentActivity.last_completed_message)}`,
            `${t('workflow.toolRoles')}: ${Object.keys(toolOutputs).join(', ') || '-'}`,
            `${t('workflow.memoryRoles')}: ${Object.keys(retrievedMemory).join(', ') || '-'}`,
          ]}
        />
      </Panel>
    </div>
  );
}
