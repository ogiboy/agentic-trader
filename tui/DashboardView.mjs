import { Box, Text } from "ink";
import React from "react";
import { cliExecutable } from "./cli-runtime.mjs";
import { dashboardStatusLine, dashboardTitle, tuiCopy } from "./copy.mjs";
import { getPageView } from "./pages.mjs";

const e = React.createElement;

export function DashboardView({
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
      { flexDirection: "column" },
      e(Text, { color: "red", bold: true }, dashboardTitle),
      e(Text, { color: "red" }, `${tuiCopy.errorLabel}: ${error}`),
      e(
        Text,
        { color: "gray" },
        `${tuiCopy.cliExecutableLabel}: ${cliExecutable}`,
      ),
    );
  }

  if (!data) {
    return e(
      Box,
      { flexDirection: "column" },
      e(Text, { color: "green", bold: true }, dashboardTitle),
      e(Text, { color: "gray" }, loadingText),
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
    { flexDirection: "column", width: "100%" },
    e(Text, { color: "green", bold: true }, dashboardTitle),
    e(Text, { color: "gray" }, dashboardStatusLine({ busy, page })),
    actionMessage
      ? e(
          Text,
          { color: actionMessage.kind === "error" ? "red" : "yellow" },
          actionMessage.text,
        )
      : null,
    e(
      Box,
      {
        flexDirection: "column",
        width: "100%",
        height: bodyHeight,
        overflowY: "hidden",
      },
      view,
    ),
    e(Text, { color: "gray" }, `${tuiCopy.lastRefresh}: ${data.loadedAt}`),
  );
}
