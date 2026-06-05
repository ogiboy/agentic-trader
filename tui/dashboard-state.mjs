import { useApp } from "ink";
import { useCallback, useEffect, useMemo, useState } from "react";
import { normalizeChatHistory } from "./chat-history.mjs";
import { cliExecutable, once, runJsonCommand } from "./cli-runtime.mjs";
import { dashboardPages as pages, tuiCopy } from "./copy.mjs";
import { loadDashboard, performRuntimeAction } from "./runtime-actions.mjs";

export function useDashboardState({ interactive }) {
  const { exit } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [page, setPage] = useState("overview");
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [chatPersona, setChatPersona] = useState("operator_liaison");
  const [chatHistory, setChatHistory] = useState([]);
  const [chatDraft, setChatDraft] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [instructionDraft, setInstructionDraft] = useState("");
  const [instructionBusy, setInstructionBusy] = useState(false);
  const [instructionMode, setInstructionMode] = useState("preview");
  const [instructionResult, setInstructionResult] = useState(null);
  const loadingText = useMemo(
    () => tuiCopy.connectingTo.replace("{executable}", cliExecutable),
    [],
  );

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
          kind: "error",
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
      const args = ["instruct", "--json", "--message", message];
      if (instructionMode === "apply") {
        args.push("--apply");
      }
      const payload = await runJsonCommand(args);
      setInstructionResult(payload);
      setInstructionDraft("");
      setActionMessage({
        kind: "info",
        text: payload.applied
          ? tuiCopy.instructionApplied
          : tuiCopy.instructionParsed,
      });
      const next = await loadDashboard();
      setData(next);
      setError(null);
    } catch (err) {
      setInstructionResult({
        instruction: {
          summary: tuiCopy.instructionFailed,
          should_update_preferences: false,
          requires_confirmation: false,
          rationale: err instanceof Error ? err.message : String(err),
          preference_update: {},
        },
        applied: false,
        updated_preferences: null,
      });
      setActionMessage({
        kind: "error",
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
