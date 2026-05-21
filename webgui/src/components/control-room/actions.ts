/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard action payloads are schema-loose JSON today */
import { useCallback } from 'react';

import type { ChatPersona } from '@/lib/chat-personas';

import type {
  DashboardData,
  InstructionMode,
  ProposalActionKind,
  ToolActionKind,
} from '../control-room.helpers';
import { readJson, WebguiHttpError } from './api';
import type { DashboardLoader } from './dashboard-polling';
import type { ControlRoomCopy } from './labels';
import type {
  ControlRoomMessage,
  RuntimeActionKind,
} from './shell';

type SetState<T> = (value: T) => void;

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
  setInstructionResult: SetState<Record<string, any> | null>;
  setMessage: SetState<ControlRoomMessage | null>;
  setProposalNote: SetState<string>;
};

function messageFromError(nextError: unknown): string {
  return nextError instanceof Error ? nextError.message : String(nextError);
}

function markAuthRequiredOnUnauthorized(
  nextError: unknown,
  setAuthRequired: SetState<boolean>,
): void {
  if (nextError instanceof WebguiHttpError && nextError.status === 401) {
    setAuthRequired(true);
  }
}

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
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/runtime', {
          method: 'POST',
          body: JSON.stringify({ kind }),
        });
        applyLatestDashboard(result.dashboard);
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
        setMessage({
          text: messageFromError(nextError),
          tone: 'bad',
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
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/tools', {
          method: 'POST',
          body: JSON.stringify({ kind }),
        });
        applyLatestDashboard(result.dashboard);
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
        setMessage({
          text: messageFromError(nextError),
          tone: 'bad',
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
        const result = await readJson<{
          message: string;
          dashboard: DashboardData;
        }>('/api/proposals', {
          method: 'POST',
          body: JSON.stringify({ kind, proposalId, reviewNotes }),
        });
        applyLatestDashboard(result.dashboard);
        setProposalNote('');
        setMessage({ text: result.message, tone: 'good' });
      } catch (nextError) {
        markAuthRequiredOnUnauthorized(nextError, setAuthRequired);
        setMessage({
          text: messageFromError(nextError),
          tone: 'bad',
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
        result: Record<string, any>;
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
      setInstructionDraft('');
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
