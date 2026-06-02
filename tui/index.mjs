import { Box, Text, useApp, useInput } from 'ink';
import { pathToFileURL } from 'node:url';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { normalizeChatHistory } from './chat-history.mjs';
import { cliExecutable, once, runJsonCommand } from './cli-runtime.mjs';
import {
  dashboardPages as pages,
  dashboardStatusLine,
  dashboardTitle,
} from './copy.mjs';
import { handleDashboardInput } from './input.mjs';
import { getPageView } from './pages.mjs';
import { loadDashboard, performRuntimeAction } from './runtime-actions.mjs';

const e = React.createElement;

/**
 * Render the Ink dashboard UI for the control room using the provided view state and props.
 *
 * Renders an error view when `error` is present, a loading view when `data` is absent, and the selected page with header/footer and optional action message when `data` is available.
 *
 * @param {Object} props - Component props.
 * @param {?Object} props.data - Dashboard snapshot payload; expected to include `loadedAt` (ISO string) used for the footer timestamp.
 * @param {?string} props.error - Error message to display in the header area; when present the full dashboard is replaced by the error view.
 * @param {string} props.loadingText - Text displayed while the dashboard snapshot is loading.
 * @param {string} props.page - Current page key; one of 'overview','runtime','portfolio','review','memory','chat','settings'.
 * @param {?{kind:string,text:string}} props.actionMessage - Optional transient action message; `kind === 'error'` renders in red, other kinds render in yellow.
 * @param {boolean} props.busy - When true, shows a working indicator in the header.
 * @param {string} props.chatPersona - Selected chat persona key for the chat composer.
 * @param {Array<Object>} props.chatHistory - Normalized chat history entries shown in the chat page.
 * @param {string} props.chatDraft - Current chat composer draft text.
 * @param {boolean} props.chatBusy - When true, indicates an in-flight chat send and disables composer actions.
 * @param {string} props.instructionDraft - Current settings/instruction composer draft text.
 * @param {boolean} props.instructionBusy - When true, indicates an in-flight instruction preview/apply request.
 * @param {string} props.instructionMode - Settings page submit mode; either 'preview' or 'apply'.
 * @param {?object} props.instructionResult - Latest parsed/applied instruction payload returned by the CLI (used to render preview/result on the settings page).
 * @returns {import('react').ReactElement} The Ink element tree representing the dashboard view.
 */
function DashboardView({
  data,
  error,
  loadingText,
  page,
  actionMessage,
  busy,
  chatPersona,
  chatHistory,
  chatDraft,
  chatBusy,
  instructionDraft,
  instructionBusy,
  instructionMode,
  instructionResult,
}) {
  if (error) {
    return e(
      Box,
      { flexDirection: 'column' },
      e(
        Text,
        { color: 'red', bold: true },
        dashboardTitle,
      ),
      e(Text, { color: 'red' }, `Error: ${error}`),
      e(Text, { color: 'gray' }, `CLI executable: ${cliExecutable}`),
    );
  }

  if (!data) {
    return e(
      Box,
      { flexDirection: 'column' },
      e(
        Text,
        { color: 'green', bold: true },
        dashboardTitle,
      ),
      e(Text, { color: 'gray' }, loadingText),
    );
  }

  const terminalRows = process.stdout.rows || 36;
  const terminalColumns = process.stdout.columns || 100;
  const navRows = terminalColumns < 140 ? 2 : 1;
  const headerRows = 1 + navRows + (actionMessage ? 1 : 0);
  const footerRows = 1;
  const bodyHeight = Math.max(1, terminalRows - headerRows - footerRows);
  const compact = terminalRows <= 30 || terminalColumns <= 110;

  const view = getPageView({
    page,
    data,
    chat: {
      persona: chatPersona,
      history: chatHistory,
      draft: chatDraft,
      busy: chatBusy,
    },
    instruction: {
      draft: instructionDraft,
      busy: instructionBusy,
      mode: instructionMode,
      result: instructionResult,
    },
    compact,
  });

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Text,
      { color: 'green', bold: true },
      dashboardTitle,
    ),
    e(Text, { color: 'gray' }, dashboardStatusLine({ busy, page })),
    actionMessage
      ? e(
          Text,
          { color: actionMessage.kind === 'error' ? 'red' : 'yellow' },
          actionMessage.text,
        )
      : null,
    e(
      Box,
      {
        flexDirection: 'column',
        width: '100%',
        height: bodyHeight,
        overflowY: 'hidden',
      },
      view,
    ),
    e(Text, { color: 'gray' }, `Last refresh: ${data.loadedAt}`),
  );
}

/**
 * Manage dashboard state, periodic refresh, runtime actions, and chat UI state for the dashboard UI.
 *
 * Initializes and exposes dashboard data, error/loading indicators, page navigation, runtime action handling,
 * and chat-related state (persona, history, draft, busy). When `interactive` is true, the hook also starts a
 * 2s interval to refresh the dashboard automatically.
 *
 * @param {{ interactive: boolean }} params - Configuration options.
 * @param {boolean} params.interactive - If true, enable periodic automatic refresh and input-interactive behavior.
 * @returns {{
 *   data: any,
 *   error: string|null,
 *   loadingText: string,
 *   refreshNow: () => void,
 *   exit: () => void,
 *   page: string,
 *   setPage: (p: string) => void,
 *   nextPage: () => void,
 *   prevPage: () => void,
 *   runAction: (kind: string) => Promise<void>,
 *   busy: boolean,
 *   actionMessage: { kind: string, text: string }|null,
 *   chatPersona: string,
 *   setChatPersona: (p: string) => void,
 *   chatHistory: Array<any>,
 *   setChatHistory: (h: Array<any>) => void,
 *   chatDraft: string,
 *   setChatDraft: (d: string) => void,
 *   chatBusy: boolean,
 *   setChatBusy: (b: boolean) => void,
 *   instructionDraft: string,
 *   setInstructionDraft: (d: string) => void,
 *   instructionBusy: boolean,
 *   setInstructionBusy: (b: boolean) => void,
 *   instructionMode: string,
 *   setInstructionMode: (m: string) => void,
 *   instructionResult: object|null,
 *   setInstructionResult: (r: object|null) => void,
 *   sendInstruction: () => Promise<void>
 * }}
 */
function useDashboardState({ interactive }) {
  const { exit } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [page, setPage] = useState('overview');
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [chatPersona, setChatPersona] = useState('operator_liaison');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatDraft, setChatDraft] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [instructionDraft, setInstructionDraft] = useState('');
  const [instructionBusy, setInstructionBusy] = useState(false);
  const [instructionMode, setInstructionMode] = useState('preview');
  const [instructionResult, setInstructionResult] = useState(null);
  const loadingText = useMemo(() => `Connecting to ${cliExecutable}...`, []);

  const refresh = useCallback(async () => {
    try {
      const next = await loadDashboard();
      setData(next);
      setError(null);
      if (once) {
        setTimeout(() => exit(), 50);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      if (once) {
        setTimeout(() => exit(), 50);
      }
    }
  }, [exit]);

  useEffect(() => {
    refresh();
  }, [refresh, refreshCount]);

  useEffect(() => {
    if (!data) {
      return;
    }
    setChatHistory(normalizeChatHistory(data));
  }, [data]);

  useEffect(() => {
    if (!interactive) {
      return undefined;
    }
    const timer = setInterval(() => {
      setRefreshCount((current) => current + 1);
    }, 2000);
    return () => clearInterval(timer);
  }, [interactive]);

  const refreshNow = useCallback(() => {
    setRefreshCount((current) => current + 1);
  }, []);

  const runAction = useCallback(
    async (kind) => {
      if (!data || busy) {
        return;
      }
      setBusy(true);
      try {
        setActionMessage(await performRuntimeAction(kind, data));
        const next = await loadDashboard();
        setData(next);
        setError(null);
      } catch (err) {
        setActionMessage({
          kind: 'error',
          text: err instanceof Error ? err.message : String(err),
        });
      } finally {
        setBusy(false);
      }
    },
    [busy, data],
  );

  const sendInstruction = useCallback(async () => {
    const message = instructionDraft.trim();
    if (!message || instructionBusy) {
      return;
    }
    setInstructionBusy(true);
    try {
      const args = ['instruct', '--json', '--message', message];
      if (instructionMode === 'apply') {
        args.push('--apply');
      }
      const payload = await runJsonCommand(args);
      setInstructionResult(payload);
      setInstructionDraft('');
      setActionMessage({
        kind: 'info',
        text: payload.applied
          ? 'Operator instruction applied to preferences.'
          : 'Operator instruction parsed.',
      });
      const next = await loadDashboard();
      setData(next);
      setError(null);
    } catch (err) {
      setInstructionResult({
        instruction: {
          summary: 'Instruction failed.',
          should_update_preferences: false,
          requires_confirmation: false,
          rationale: err instanceof Error ? err.message : String(err),
          preference_update: {},
        },
        applied: false,
        updated_preferences: null,
      });
      setActionMessage({
        kind: 'error',
        text: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setInstructionBusy(false);
    }
  }, [instructionBusy, instructionDraft, instructionMode]);

  const nextPage = useCallback(() => {
    setPage((current) => pages[(pages.indexOf(current) + 1) % pages.length]);
  }, []);

  const prevPage = useCallback(() => {
    setPage(
      (current) =>
        pages[(pages.indexOf(current) - 1 + pages.length) % pages.length],
    );
  }, []);

  return {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
    instructionDraft,
    setInstructionDraft,
    instructionBusy,
    setInstructionBusy,
    instructionMode,
    setInstructionMode,
    instructionResult,
    setInstructionResult,
    sendInstruction,
  };
}

/**
 * Render the interactive Agentic Trader control-room dashboard and wire keyboard input, runtime actions, and chat behavior.
 *
 * Sets up dashboard state with periodic refresh, binds keys for page navigation and global runtime actions, and provides a chat composer that sends messages via the CLI and updates the in-UI chat history.
 *
 * @returns {import('react').ReactElement} A React element of the DashboardView configured for interactive use.
 */
function InteractiveDashboardApp() {
  const {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
    instructionDraft,
    setInstructionDraft,
    instructionBusy,
    instructionMode,
    setInstructionMode,
    instructionResult,
    sendInstruction,
  } = useDashboardState({ interactive: true });

  const sendChat = useCallback(async () => {
    const message = chatDraft.trim();
    if (!message || chatBusy) {
      return;
    }
    setChatBusy(true);
    try {
      const payload = await runJsonCommand([
        'chat',
        '--json',
        '--persona',
        chatPersona,
        '--message',
        message,
      ]);
      setChatHistory((current) => [
        ...current,
        {
          user: payload.message,
          persona: payload.persona,
          response: payload.response,
        },
      ]);
      refreshNow();
      setChatDraft('');
    } catch (err) {
      setChatHistory((current) => [
        ...current,
        {
          user: message,
          persona: chatPersona,
          response: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
      setChatDraft('');
    } finally {
      setChatBusy(false);
    }
  }, [
    chatBusy,
    chatDraft,
    chatPersona,
    refreshNow,
    setChatBusy,
    setChatDraft,
    setChatHistory,
  ]);

  useInput((input, key) => {
    handleDashboardInput(input, key, {
      exit,
      nextPage,
      page,
      prevPage,
      refreshNow,
      runAction,
      sendChat,
      sendInstruction,
      setChatDraft,
      setChatPersona,
      setInstructionDraft,
      setInstructionMode,
      setPage,
    });
  });

  return e(DashboardView, {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  });
}

/**
 * Render a read-only snapshot of the dashboard UI.
 *
 * Uses the dashboard state hook in non-interactive mode and returns the
 * DashboardView element populated with that state (no input wiring or periodic refresh).
 *
 * @returns {import('react').ReactElement} The DashboardView React element showing the current snapshot.
 */
function StaticDashboardApp() {
  const {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  } = useDashboardState({ interactive: false });
  return e(DashboardView, {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
    instructionDraft,
    instructionBusy,
    instructionMode,
    instructionResult,
  });
}

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
} from './copy.mjs';
export {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  getSupervisorLogLines,
} from './dashboard-defaults.mjs';
export {
  handleChatInput,
  handleDashboardInput,
  handleGlobalInput,
  handleSettingsInput,
} from './input.mjs';
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
} from './line-formatters.mjs';
export { normalizeChatHistory };
