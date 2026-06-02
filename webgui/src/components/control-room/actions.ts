import { useCallback } from 'react';

import type { ChatPersona } from '@/lib/chat-personas';

import type {
  DashboardData,
  InstructionMode,
  InstructionResult,
  ProposalActionKind,
  ToolActionKind,
} from '../control-room.helpers';
import
  {
    markAuthRequiredOnUnauthorized,
    messageFromError,
    runDashboardMutation,
    type SetState,
  } from './action-request';
import { readJson } from './api';
import type { DashboardLoader } from './dashboard-polling';
import type { ControlRoomCopy } from './labels';
import type { ControlRoomMessage, RuntimeActionKind } from './shell';

type ControlRoomActionsProps = {
  abortDashboardRequest: () => void;
  applyLatestDashboard: (payload: DashboardData) => void;
  chatDraft: string;
  chatPersona: ChatPersona;
  copy: ControlRoomCopy['feedback'];
  instructionDraft: string;
  instructionMode: InstructionMode;
  loadDashboard: DashboardLoader;
  proposalNote: string;
  setAuthRequired: SetState<boolean>;
  setBusyState: SetState<string | null>;
  setChatDraft: SetState<string>;
  setInstructionDraft: SetState<string>;
  setInstructionResult: SetState<InstructionResult | null>;
  setMessage: SetState<ControlRoomMessage | null>;
  setProposalNote: SetState<string>;
};

export function useControlRoomActions({
  abortDashboardRequest,
  applyLatestDashboard,
  chatDraft,
  chatPersona,
  copy,
  instructionDraft,
  instructionMode,
  loadDashboard,
  proposalNote,
  setAuthRequired,
  setBusyState,
  setChatDraft,
  setInstructionDraft,
  setInstructionResult,
  setMessage,
  setProposalNote,
}: ControlRoomActionsProps) {
  const runAction = useCallback(
    async (kind: RuntimeActionKind) => {
      if (kind === 'refresh') {
        setBusyState('refresh');
        await loadDashboard({ force: true });
        setMessage({ text: copy.dashboardRefreshed, tone: 'neutral' });
        setBusyState(null);
        return;
      }
      setBusyState(kind);
      abortDashboardRequest();
      try {
        await runDashboardMutation({
          endpoint: '/api/runtime',
          body: { kind },
          applyLatestDashboard,
          setAuthRequired,
          setMessage,
        });
      } finally {
        setBusyState(null);
      }
    },
    [
      abortDashboardRequest,
      applyLatestDashboard,
      loadDashboard,
      copy.dashboardRefreshed,
      setAuthRequired,
      setBusyState,
      setMessage,
    ],
  );

  const runToolAction = useCallback(
    async (kind: ToolActionKind) => {
      setBusyState(kind);
      abortDashboardRequest();
      try {
        await runDashboardMutation({
          endpoint: '/api/tools',
          body: { kind },
          applyLatestDashboard,
          setAuthRequired,
          setMessage,
        });
      } finally {
        setBusyState(null);
      }
    },
    [
      abortDashboardRequest,
      applyLatestDashboard,
      setAuthRequired,
      setBusyState,
      setMessage,
    ],
  );

  const runProposalAction = useCallback(
    async (kind: ProposalActionKind, proposalId: string) => {
      const reviewNotes = proposalNote.trim();
      setBusyState(`proposal-${kind}`);
      abortDashboardRequest();
      try {
        await runDashboardMutation({
          endpoint: '/api/proposals',
          body: { kind, proposalId, reviewNotes },
          applyLatestDashboard,
          setAuthRequired,
          setMessage,
          onSuccess: () => setProposalNote(''),
        });
      } finally {
        setBusyState(null);
      }
    },
    [
      abortDashboardRequest,
      applyLatestDashboard,
      proposalNote,
      setAuthRequired,
      setBusyState,
      setMessage,
      setProposalNote,
    ],
  );

  const sendChat = useCallback(async () => {
    const messageText = chatDraft.trim();
    if (!messageText) {
      return;
    }
    setBusyState('chat');
    abortDashboardRequest();
    try {
      await readJson<Record<string, string>>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          persona: chatPersona,
          message: messageText,
        }),
      });
      setChatDraft('');
      setMessage({ text: copy.operatorReplyReceived, tone: 'good' });
      await loadDashboard({ force: true });
    } catch (nextError) {
      markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
      setMessage({
        text: messageFromError(nextError),
        tone: 'bad',
      });
    } finally {
      setBusyState(null);
    }
  }, [
    abortDashboardRequest,
    chatDraft,
    chatPersona,
    loadDashboard,
    copy.operatorReplyReceived,
    setAuthRequired,
    setBusyState,
    setChatDraft,
    setMessage,
  ]);

  const sendInstruction = useCallback(async () => {
    const messageText = instructionDraft.trim();
    if (!messageText) {
      return;
    }
    setBusyState('instruction');
    abortDashboardRequest();
    try {
      const result = await readJson<{
        result: InstructionResult;
        dashboard: DashboardData;
      }>('/api/instruct', {
        method: 'POST',
        body: JSON.stringify({
          message: messageText,
          apply: instructionMode === 'apply',
        }),
      });
      setInstructionResult(result.result);
      applyLatestDashboard(result.dashboard);
      if (instructionMode === 'apply') {
        setInstructionDraft('');
      }
      setMessage({
        text:
          instructionMode === 'apply'
            ? copy.preferencesUpdated
            : copy.instructionPreviewReady,
        tone: 'good',
      });
    } catch (nextError) {
      markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
      setMessage({
        text: messageFromError(nextError),
        tone: 'bad',
      });
    } finally {
      setBusyState(null);
    }
  }, [
    abortDashboardRequest,
    applyLatestDashboard,
    instructionDraft,
    instructionMode,
    copy.instructionPreviewReady,
    copy.preferencesUpdated,
    setAuthRequired,
    setBusyState,
    setInstructionDraft,
    setInstructionResult,
    setMessage,
  ]);

  return {
    runAction,
    runProposalAction,
    runToolAction,
    sendChat,
    sendInstruction,
  };
}
