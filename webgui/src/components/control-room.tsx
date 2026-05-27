/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
'use client';

import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from 'react';

import type { ChatPersona } from '@/lib/chat-personas';

import type {
  DashboardData,
  InstructionMode,
  TabId,
} from './control-room.helpers';
import { normalizeChatHistory } from './control-room.helpers';
import { useControlRoomActions } from './control-room/actions';
import { ActiveView } from './control-room/active-view';
import { authenticateWebguiSession, errorMessage } from './control-room/api';
import { useDashboardPolling } from './control-room/dashboard-polling';
import { controlRoomTabs, getControlRoomCopy } from './control-room/labels';
import {
  ControlRoomLoadingPanel,
  ControlRoomUnavailablePanel,
} from './control-room/loading-panel';
import {
  ControlRoomAuthShell,
  ControlRoomShell,
  type ControlRoomMessage,
} from './control-room/shell';
import {
  useControlRoomLocaleState,
  useLoadingSeconds,
} from './control-room/state-hooks';
import {
  currentCycleItems,
  systemStatusViewItems,
} from './control-room/view-model';

export {
  canonicalLines,
  failedCheckNames,
  formatList,
  formatNumber,
  formatPercent,
  formatSourceHealthCount,
  formatTimestamp,
  localToolActionLines,
  localToolLines,
  marketContextLines,
  normalizeChatHistory,
  positionPlanCoverageLines,
  proposalHeadline,
  proposalLines,
  providerWarningLines,
  readinessLines,
  sourceHealthSummaryLine,
  systemStatusItems,
  tradeContextLines,
  unavailableSectionLines,
} from './control-room.helpers';
export type {
  DashboardData,
  InstructionMode,
  KeyValueItems,
  MessageTone,
  PanelAccent,
  ProposalActionKind,
  TabId,
  ToolActionKind,
} from './control-room.helpers';
export { ActiveView } from './control-room/active-view';
export { readJson, WebguiHttpError } from './control-room/api';
export { ChatView } from './control-room/chat-view';
export {
  ControlRoomLoadingPanel,
  ControlRoomUnavailablePanel,
} from './control-room/loading-panel';
export { MemoryView } from './control-room/memory-view';
export { OverviewView } from './control-room/overview-view';
export { PortfolioView } from './control-room/portfolio-view';
export { ProposalDeskView } from './control-room/proposal-desk-view';
export { ReviewView } from './control-room/review-view';
export { RuntimeView } from './control-room/runtime-view';
export { SettingsView } from './control-room/settings-view';
export {
  useControlRoomLocaleState,
  useLoadingSeconds,
} from './control-room/state-hooks';
export {
  currentCycleItems,
  systemStatusViewItems,
} from './control-room/view-model';

/**
 * Operator control room UI component for viewing dashboard data and controlling runtime, local tools, chat, and operator instructions.
 *
 * Handles polling the dashboard, same-origin WebGUI token unlocking, and exposes tabbed views (overview, runtime, portfolio, proposals, review, memory, chat, settings) with actions that invoke backend endpoints.
 *
 * @returns A React element containing the tabbed operator dashboard UI and its runtime/tool/chat/instruction controls
 */
export function ControlRoom() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [tab, setTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<ControlRoomMessage | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const busyRef = useRef<string | null>(null);
  const [chatDraft, setChatDraft] = useState('');
  const [chatPersona, setChatPersona] =
    useState<ChatPersona>('operator_liaison');
  const [chatHistory, setChatHistory] = useState<Array<Record<string, string>>>(
    [],
  );
  const [instructionDraft, setInstructionDraft] = useState('');
  const [instructionMode, setInstructionMode] =
    useState<InstructionMode>('preview');
  const [instructionResult, setInstructionResult] = useState<Record<
    string,
    any
  > | null>(null);
  const [proposalNote, setProposalNote] = useState('');
  const [lastLoadedAt, setLastLoadedAt] = useState<string>('-');
  const [webguiToken, setWebguiToken] = useState('');
  const [authRequired, setAuthRequired] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [locale, selectLocale] = useControlRoomLocaleState();
  const loadingSeconds = useLoadingSeconds(loading);
  const copy = useMemo(() => getControlRoomCopy(locale), [locale]);
  const localizedTabs = useMemo(() => controlRoomTabs(copy), [copy]);
  const activeTabLabel =
    localizedTabs.find((item) => item.id === tab)?.label ?? copy.tabs.overview;

  const selectTab = useCallback((nextTab: TabId) => {
    setTab(nextTab);
    setError(null);
    setMessage(null);
  }, []);

  const setBusyState = useCallback((nextBusy: string | null) => {
    busyRef.current = nextBusy;
    setBusy(nextBusy);
  }, []);

  const applyDashboardPayload = useCallback((payload: DashboardData) => {
    setDashboard(payload);
    setChatHistory(normalizeChatHistory(payload));
    setLastLoadedAt(new Date().toLocaleTimeString());
    setAuthRequired(false);
    setAuthError(null);
    setError(null);
  }, []);

  const { abortDashboardRequest, applyLatestDashboard, loadDashboard } =
    useDashboardPolling({
      applyDashboardPayload,
      busyRef,
      setAuthError,
      setAuthRequired,
      setDashboard,
      setError,
      setLoading,
    });

  const unlockWebgui = useCallback(
    async (event: SyntheticEvent<HTMLFormElement>) => {
      event.preventDefault();
      const token = webguiToken.trim();
      if (!token) {
        return;
      }
      setAuthBusy(true);
      setAuthError(null);
      try {
        await authenticateWebguiSession(token);
        setWebguiToken('');
        setAuthRequired(false);
        await loadDashboard({ force: true });
      } catch (nextError) {
        setAuthRequired(true);
        setAuthError(errorMessage(nextError));
      } finally {
        setAuthBusy(false);
      }
    },
    [loadDashboard, webguiToken],
  );

  const {
    runAction,
    runProposalAction,
    runToolAction,
    sendChat,
    sendInstruction,
  } = useControlRoomActions({
    abortDashboardRequest,
    applyLatestDashboard,
    chatDraft,
    chatPersona,
    copy: copy.feedback,
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
  });

  const currentCycle = useMemo(
    () => currentCycleItems(dashboard, copy),
    [copy, dashboard],
  );

  const system = useMemo(
    () => systemStatusViewItems(dashboard, copy),
    [copy, dashboard],
  );

  const activeView = dashboard ? (
    <ActiveView
      tab={tab}
      copy={copy}
      dashboard={dashboard}
      currentCycle={currentCycle}
      system={system}
      chatPersona={chatPersona}
      chatHistory={chatHistory}
      chatDraft={chatDraft}
      instructionDraft={instructionDraft}
      instructionMode={instructionMode}
      instructionResult={instructionResult}
      proposalNote={proposalNote}
      busy={busy}
      onChatPersonaChange={setChatPersona}
      onChatDraftChange={setChatDraft}
      onSendChat={sendChat}
      onInstructionDraftChange={setInstructionDraft}
      onInstructionModeChange={setInstructionMode}
      onSendInstruction={sendInstruction}
      onToolAction={(kind) => void runToolAction(kind)}
      onProposalNoteChange={setProposalNote}
      onProposalAction={runProposalAction}
    />
  ) : null;
  const content = (() => {
    if (loading) {
      return (
        <ControlRoomLoadingPanel copy={copy} loadingSeconds={loadingSeconds} />
      );
    }
    if (dashboard) {
      return activeView;
    }
    return <ControlRoomUnavailablePanel copy={copy} />;
  })();

  if (authRequired) {
    return (
      <ControlRoomAuthShell
        authBusy={authBusy}
        authError={authError}
        copy={copy}
        onSubmit={unlockWebgui}
        onTokenChange={setWebguiToken}
        token={webguiToken}
      />
    );
  }

  return (
    <ControlRoomShell
      activeTabLabel={activeTabLabel}
      busy={busy}
      content={content}
      copy={copy}
      dashboard={dashboard}
      error={error}
      lastLoadedAt={lastLoadedAt}
      locale={locale}
      message={message}
      onRunAction={(kind) => void runAction(kind)}
      onSelectLocale={selectLocale}
      onSelectTab={selectTab}
      tab={tab}
      tabs={localizedTabs}
    />
  );
}
