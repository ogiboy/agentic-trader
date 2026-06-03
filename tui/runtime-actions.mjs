import { runJsonCommand, runTextCommand } from "./cli-runtime.mjs";
import {
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
} from "./dashboard-defaults.mjs";

async function performRuntimeAction(kind, data) {
  if (kind === "start") {
    if (data.status.live_process) {
      return {
        kind: "info",
        text: `Runtime already active with PID ${data.status.state?.pid ?? "-"}.`,
      };
    }
    const symbols = defaultSymbolsFromPreferences(data.preferences);
    await runTextCommand([
      "launch",
      "--symbols",
      symbols,
      "--interval",
      "1d",
      "--lookback",
      "180d",
      "--continuous",
      "--background",
      "--poll-seconds",
      "300",
    ]);
    return {
      kind: "info",
      text: `Background runtime launch requested for ${symbols}.`,
    };
  }

  if (kind === "stop") {
    if (!data.status.state?.pid) {
      return { kind: "info", text: "No managed runtime is currently active." };
    }
    await runTextCommand(["stop-service"]);
    return {
      kind: "info",
      text: `Stop requested for PID ${data.status.state.pid}.`,
    };
  }

  if (kind === "one-shot") {
    if (data.status.live_process) {
      return {
        kind: "info",
        text: `Runtime already active with PID ${data.status.state?.pid ?? "-"}. Stop it before running a one-shot cycle.`,
      };
    }
    const symbol = defaultSingleSymbol(data);
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await runTextCommand([
      "run",
      "--symbol",
      symbol,
      "--interval",
      interval,
      "--lookback",
      lookback,
    ]);
    return {
      kind: "info",
      text: `Strict one-shot cycle completed for ${symbol} (${interval}, ${lookback}).`,
    };
  }

  if ((data.status.state?.symbols || []).length) {
    await runTextCommand(["restart-service"]);
    return { kind: "info", text: "Background runtime restart requested." };
  }
  return {
    kind: "info",
    text: "No saved runtime launch config is available yet.",
  };
}

async function loadDashboard() {
  const payload = await runJsonCommand([
    "dashboard-snapshot",
    "--log-limit",
    "14",
  ]);
  return {
    ...payload,
    loadedAt: new Date().toISOString(),
  };
}

export { loadDashboard, performRuntimeAction };
