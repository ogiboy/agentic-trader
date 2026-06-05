import { useInput } from "ink";
import React, { useCallback } from "react";
import { runJsonCommand } from "./cli-runtime.mjs";
import { DashboardView } from "./DashboardView.mjs";
import { handleDashboardInput } from "./input.mjs";
import { useDashboardState } from "./dashboard-state.mjs";

const e = React.createElement;

export function InteractiveDashboardApp() {
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
        "chat",
        "--json",
        "--persona",
        chatPersona,
        "--message",
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
      setChatDraft("");
    } catch (err) {
      setChatHistory((current) => [
        ...current,
        {
          user: message,
          persona: chatPersona,
          response: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
      setChatDraft("");
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

export function StaticDashboardApp() {
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
