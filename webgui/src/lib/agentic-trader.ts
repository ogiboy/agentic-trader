import { execFile } from "node:child_process";
import { resolve } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const workspaceRoot = resolve(process.cwd(), "..");
const cliExecutable = process.env.AGENTIC_TRADER_CLI || "agentic-trader";
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;

type ExecOptions = {
  expectJson?: boolean;
  timeoutMs?: number;
};

function buildAttempts(args: string[]): Array<[string, string[]]> {
  const attempts: Array<[string, string[]]> = [];
  if (pythonExecutable) {
    attempts.push([pythonExecutable, ["-m", "agentic_trader.cli", ...args]]);
  }
  attempts.push([cliExecutable, args]);
  return attempts;
}

function defaultSymbolsFromPreferences(preferences: {
  exchanges?: string[];
  regions?: string[];
}): string {
  const exchanges = preferences.exchanges || [];
  const regions = preferences.regions || [];
  if (exchanges.includes("BIST") || regions.includes("TR")) {
    return "THYAO.IS,GARAN.IS";
  }
  if (
    exchanges.includes("NASDAQ") ||
    exchanges.includes("NYSE") ||
    regions.includes("US")
  ) {
    return "AAPL,MSFT";
  }
  return "BTC-USD,ETH-USD";
}

function defaultSingleSymbol(data: Record<string, any>): string {
  return (
    data?.status?.state?.current_symbol ||
    data?.tradeContext?.record?.symbol ||
    data?.review?.record?.symbol ||
    defaultSymbolsFromPreferences(data?.preferences || {}).split(",")[0]
  );
}

function defaultRuntimeInterval(data: Record<string, any>): string {
  return data?.status?.state?.interval || data?.marketContext?.contextPack?.interval || "1d";
}

function defaultRuntimeLookback(data: Record<string, any>): string {
  return (
    data?.status?.state?.lookback ||
    data?.marketContext?.contextPack?.lookback ||
    "180d"
  );
}

function extractError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export async function execTrader(
  args: string[],
  { expectJson = false, timeoutMs = 30_000 }: ExecOptions = {},
): Promise<any> {
  let lastError: unknown;

  for (const [command, commandArgs] of buildAttempts(args)) {
    try {
      const { stdout, stderr } = await execFileAsync(command, commandArgs, {
        cwd: workspaceRoot,
        env: process.env,
        timeout: timeoutMs,
        maxBuffer: 8 * 1024 * 1024,
      });
      if (expectJson) {
        return JSON.parse(stdout || "{}");
      }
      return { stdout, stderr };
    } catch (error: any) {
      lastError = error;
      if (error && typeof error === "object" && error.code !== "ENOENT") {
        const detail = error.stderr || error.stdout || error.message;
        throw new Error(String(detail).trim() || "Agentic Trader command failed.");
      }
    }
  }

  throw new Error(extractError(lastError || "No Agentic Trader executable was available."));
}

export async function getDashboardSnapshot(): Promise<any> {
  return execTrader(["dashboard-snapshot", "--log-limit", "14"], {
    expectJson: true,
    timeoutMs: 30_000,
  });
}

export async function runRuntimeAction(kind: string): Promise<{
  message: string;
  dashboard: any;
}> {
  const data = await getDashboardSnapshot();

  if (kind === "start") {
    if (data?.status?.live_process) {
      return {
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? "-"}.`,
        dashboard: data,
      };
    }
    const symbols = defaultSymbolsFromPreferences(data?.preferences || {});
    await execTrader(
      [
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
      ],
      { timeoutMs: 60_000 },
    );
    return {
      message: `Background runtime launch requested for ${symbols}.`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === "stop") {
    if (!data?.status?.state?.pid) {
      return {
        message: "No managed runtime is currently active.",
        dashboard: data,
      };
    }
    await execTrader(["stop-service"], { timeoutMs: 30_000 });
    return {
      message: `Stop requested for PID ${data.status.state.pid}.`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === "restart") {
    if ((data?.status?.state?.symbols || []).length) {
      await execTrader(["restart-service"], { timeoutMs: 30_000 });
      return {
        message: "Background runtime restart requested.",
        dashboard: await getDashboardSnapshot(),
      };
    }
    return {
      message: "No saved runtime launch config is available yet.",
      dashboard: data,
    };
  }

  if (kind === "one-shot") {
    if (data?.status?.live_process) {
      return {
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? "-"}. Stop it before running a one-shot cycle.`,
        dashboard: data,
      };
    }
    const symbol = defaultSingleSymbol(data);
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await execTrader(
      ["run", "--symbol", symbol, "--interval", interval, "--lookback", lookback],
      { timeoutMs: 240_000 },
    );
    return {
      message: `Strict one-shot cycle completed for ${symbol} (${interval}, ${lookback}).`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  throw new Error(`Unsupported runtime action: ${kind}`);
}

export async function runInstruction(message: string, apply: boolean): Promise<any> {
  const args = ["instruct", "--json", "--message", message];
  if (apply) {
    args.push("--apply");
  }
  return execTrader(args, {
    expectJson: true,
    timeoutMs: 180_000,
  });
}

export async function runChat(persona: string, message: string): Promise<any> {
  return execTrader(
    ["chat", "--json", "--persona", persona, "--message", message],
    {
      expectJson: true,
      timeoutMs: 180_000,
    },
  );
}
