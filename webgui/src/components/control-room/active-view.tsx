/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
import type { ChatPersona } from '@/lib/chat-personas';

import type {
  DashboardData,
  InstructionMode,
  KeyValueItems,
  ProposalActionKind,
  TabId,
  ToolActionKind,
} from '../control-room.helpers';
import { getControlRoomCopy, type ControlRoomCopy } from './labels';
import { ChatView } from './chat-view';
import { MemoryView } from './memory-view';
import { OverviewView } from './overview-view';
import { PortfolioView } from './portfolio-view';
import { ProposalDeskView } from './proposal-desk-view';
import { ReviewView } from './review-view';
import { RuntimeView } from './runtime-view';
import { SettingsView } from './settings-view';

type ActiveViewProps = Readonly<{
  tab: TabId;
  copy?: ControlRoomCopy;
  dashboard: DashboardData;
  currentCycle: KeyValueItems;
  system: KeyValueItems;
  chatPersona: ChatPersona;
  chatHistory: Array<Record<string, string>>;
  chatDraft: string;
  instructionDraft: string;
  instructionMode: InstructionMode;
  instructionResult: Record<string, any> | null;
  proposalNote: string;
  busy: string | null;
  onChatPersonaChange: (value: ChatPersona) => void;
  onChatDraftChange: (value: string) => void;
  onSendChat: () => Promise<void>;
  onInstructionDraftChange: (value: string) => void;
  onInstructionModeChange: (value: InstructionMode) => void;
  onSendInstruction: () => Promise<void>;
  onToolAction: (kind: ToolActionKind) => void;
  onProposalNoteChange: (value: string) => void;
  onProposalAction: (
    kind: ProposalActionKind,
    proposalId: string,
  ) => Promise<void>;
}>;

/**
 * Renders the dashboard tab specified by `props.tab` and forwards the relevant
 * slice of state and handlers to the corresponding view component.
 *
 * @param props - Component props containing `tab`, the `dashboard` payload, UI state such as `busy`,
 *                and any view-specific handlers and data (chat, instruction, tool actions, etc.).
 * @returns The JSX element for the active tab view.
 */
export function ActiveView(props: ActiveViewProps) {
  const copy = props.copy ?? getControlRoomCopy('en');

  switch (props.tab) {
    case 'overview':
      return (
        <OverviewView
          copy={copy}
          dashboard={props.dashboard}
          currentCycle={props.currentCycle}
          system={props.system}
          busy={props.busy}
          onToolAction={props.onToolAction}
        />
      );
    case 'runtime':
      return <RuntimeView copy={copy} dashboard={props.dashboard} />;
    case 'portfolio':
      return <PortfolioView copy={copy} dashboard={props.dashboard} />;
    case 'proposals':
      return (
        <ProposalDeskView
          copy={copy}
          dashboard={props.dashboard}
          busy={props.busy}
          proposalNote={props.proposalNote}
          onProposalAction={props.onProposalAction}
          onProposalNoteChange={props.onProposalNoteChange}
        />
      );
    case 'review':
      return <ReviewView copy={copy} dashboard={props.dashboard} />;
    case 'memory':
      return <MemoryView copy={copy} dashboard={props.dashboard} />;
    case 'chat':
      return (
        <ChatView
          copy={copy}
          dashboard={props.dashboard}
          chatPersona={props.chatPersona}
          chatHistory={props.chatHistory}
          chatDraft={props.chatDraft}
          busy={props.busy}
          onChatPersonaChange={props.onChatPersonaChange}
          onChatDraftChange={props.onChatDraftChange}
          onSendChat={props.onSendChat}
        />
      );
    case 'settings':
      return (
        <SettingsView
          copy={copy}
          dashboard={props.dashboard}
          instructionDraft={props.instructionDraft}
          instructionMode={props.instructionMode}
          instructionResult={props.instructionResult}
          busy={props.busy}
          onInstructionDraftChange={props.onInstructionDraftChange}
          onInstructionModeChange={props.onInstructionModeChange}
          onSendInstruction={props.onSendInstruction}
        />
      );
  }
}
