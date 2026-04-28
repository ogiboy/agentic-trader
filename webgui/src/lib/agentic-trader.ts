/* eslint-disable @typescript-eslint/no-explicit-any -- CLI/dashboard payloads are schema-loose JSON today */
import { execFile } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const moduleDir = dirname(fileURLToPath(import.meta.url));

function isWorkspaceRoot(candidate: string): boolean {
  return (
    existsSync(resolve(candidate, 'pyproject.toml')) &&
    existsSync(resolve(candidate, 'agentic_trader'))
  );
}

function findWorkspaceRoot(start: string): null | string {
  let current = resolve(start);
  while (true) {
    if (isWorkspaceRoot(current)) {
      return current;
    }
    const parent = resolve(current, '..');
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

const workspaceRootCandidates = [process.cwd(), resolve(moduleDir, '../../..')];
const detectedWorkspaceRoot = workspaceRootCandidates
  .map(findWorkspaceRoot)
  .find((candidate): candidate is string => Boolean(candidate));

if (!detectedWorkspaceRoot) {
  throw new Error(
    `Unable to locate Agentic Trader workspace root from ${workspaceRootCandidates.join(' or ')}. ` +
      'Start the Web GUI from the repository worktree or set AGENTIC_TRADER_PYTHON/AGENTIC_TRADER_CLI explicitly.',
  );
}
const workspaceRoot = detectedWorkspaceRoot;
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;

type ExecOptions = {
  expectJson?: boolean;
  timeoutMs?: number;
};

/**
 * Reads the local Codex environment manifest and returns the declared Conda environment name when present.
 *
 * @returns The Conda environment name from `.codex/environments/environment.toml`, or `null` when the file is missing or does not declare a `conda activate <name>` command.
 */
function detectManagedCondaEnvName(): null | string {
  const manifestPath = resolve(
    workspaceRoot,
    '.codex/environments/environment.toml',
  );
  if (!existsSync(manifestPath)) {
    return null;
  }
  const manifest = readFileSync(manifestPath, 'utf-8');
  const match = manifest.match(/conda activate ([^\s'"]+)/);
  return match?.[1] || null;
}

/**
 * Resolve the most reliable Python executable for the current worktree without requiring explicit user configuration.
 *
 * Preference order:
 * 1. active virtual environment
 * 2. active non-base Conda environment
 * 3. repo-declared Codex Conda environment derived from `CONDA_EXE`
 *
 * @returns An absolute Python path when one can be resolved locally; otherwise `null`.
 */
function detectManagedPythonExecutable(): null | string {
  if (process.env.VIRTUAL_ENV) {
    const virtualEnvPython = resolve(process.env.VIRTUAL_ENV, 'bin', 'python');
    if (existsSync(virtualEnvPython)) {
      return virtualEnvPython;
    }
  }

  if (
    process.env.CONDA_PREFIX &&
    process.env.CONDA_DEFAULT_ENV &&
    process.env.CONDA_DEFAULT_ENV !== 'base'
  ) {
    const activeCondaPython = resolve(
      process.env.CONDA_PREFIX,
      'bin',
      'python',
    );
    if (existsSync(activeCondaPython)) {
      return activeCondaPython;
    }
  }

  const managedEnvName = detectManagedCondaEnvName();
  if (!managedEnvName) {
    return null;
  }

  const condaRoots = new Set<string>();
  if (process.env.CONDA_EXE) {
    condaRoots.add(resolve(dirname(process.env.CONDA_EXE), '..'));
  }
  if (process.env.HOME) {
    condaRoots.add(resolve(process.env.HOME, 'miniconda3'));
    condaRoots.add(resolve(process.env.HOME, 'anaconda3'));
  }
  condaRoots.add('/opt/anaconda3');
  condaRoots.add('/usr/local/anaconda3');

  for (const condaRoot of condaRoots) {
    const managedCondaPython = resolve(
      condaRoot,
      'envs',
      managedEnvName,
      'bin',
      'python',
    );
    if (existsSync(managedCondaPython)) {
      return managedCondaPython;
    }
  }

  return null;
}

/**
 * Build an ordered list of executable invocation attempts for the given CLI arguments.
 *
 * @param args - Command-line arguments to pass to the Agentic Trader CLI
 * @returns An array of tuples where each tuple is `[executablePath, argv]`; the list prefers the configured Python module runner (if available) followed by the direct CLI executable fallback
 */
function buildAttempts(args: string[]): Array<[string, string[]]> {
  const attempts: Array<[string, string[]]> = [];
  const managedPythonExecutable = detectManagedPythonExecutable();
  if (pythonExecutable) {
    attempts.push([pythonExecutable, ['-m', 'agentic_trader.cli', ...args]]);
  }
  if (managedPythonExecutable) {
    attempts.push([
      managedPythonExecutable,
      ['-m', 'agentic_trader.cli', ...args],
    ]);
  }
  attempts.push([cliExecutable, args]);

  const seen = new Set<string>();
  return attempts.filter(([command, commandArgs]) => {
    const key = `${command}\u0000${commandArgs.join('\u0000')}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

/**
 * Selects a default comma-separated list of market symbols based on exchange and region preferences.
 *
 * @param preferences - Object containing optional `exchanges` and `regions` arrays used to infer market preference.
 * @returns `THYAO.IS,GARAN.IS` when `exchanges` contains `BIST` or `regions` contains `TR`; `AAPL,MSFT` when `exchanges` contains `NASDAQ` or `NYSE` or `regions` contains `US`; otherwise `BTC-USD,ETH-USD`.
 */
function defaultSymbolsFromPreferences(preferences: {
  exchanges?: string[];
  regions?: string[];
}): string {
  const exchanges = preferences.exchanges || [];
  const regions = preferences.regions || [];
  if (exchanges.includes('BIST') || regions.includes('TR')) {
    return 'THYAO.IS,GARAN.IS';
  }
  if (
    exchanges.includes('NASDAQ') ||
    exchanges.includes('NYSE') ||
    regions.includes('US')
  ) {
    return 'AAPL,MSFT';
  }
  return 'BTC-USD,ETH-USD';
}

/**
 * Selects a single trading symbol from the provided application state or preferences.
 *
 * @param data - Application state object which may contain `status.state.current_symbol`, `tradeContext.record.symbol`, `review.record.symbol`, or `preferences` used to derive defaults.
 * @returns The chosen symbol string from the first available source in priority order: `status.state.current_symbol`, `tradeContext.record.symbol`, `review.record.symbol`, or the first symbol from defaults derived from `preferences`.
 */
function defaultSingleSymbol(data: Record<string, any>): string {
  return (
    data?.status?.state?.current_symbol ||
    data?.tradeContext?.record?.symbol ||
    data?.review?.record?.symbol ||
    defaultSymbolsFromPreferences(data?.preferences || {}).split(',')[0]
  );
}

/**
 * Selects the runtime interval for the trader from available data sources.
 *
 * Checks `data.status.state.interval` first, then `data.marketContext.contextPack.interval`, and falls back to `"1d"`.
 *
 * @param data - Object containing runtime and market context (`status.state.interval` and `marketContext.contextPack.interval` are checked)
 * @returns The chosen interval string (e.g., `"1d"`) from status, context pack, or the `"1d"` fallback
 */
function defaultRuntimeInterval(data: Record<string, any>): string {
  return (
    data?.status?.state?.interval ||
    data?.marketContext?.contextPack?.interval ||
    '1d'
  );
}

/**
 * Selects the runtime lookback period from available sources or falls back to "180d".
 *
 * @param data - Object that may contain `status.state.lookback` or `marketContext.contextPack.lookback`
 * @returns The lookback string from `status.state.lookback` if present, otherwise from `marketContext.contextPack.lookback`, otherwise `"180d"`
 */
function defaultRuntimeLookback(data: Record<string, any>): string {
  return (
    data?.status?.state?.lookback ||
    data?.marketContext?.contextPack?.lookback ||
    '180d'
  );
}

/**
 * Determine whether the managed runtime is currently active according to the dashboard snapshot.
 *
 * @param data - Dashboard snapshot that may expose both `status.live_process` and `status.state.pid`
 * @returns `true` only when the dashboard confirms a live process; persisted PIDs can describe historical terminal states.
 */
function isTraderRunning(data: Record<string, any>): boolean {
  return data?.status?.live_process === true;
}

/**
 * Extracts a human-readable message from an unknown error value.
 *
 * @param error - The value to extract a message from; may be an `Error` or any other value
 * @returns The error's `message` if `error` is an `Error`, otherwise `String(error)`
 */
function extractError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

/**
 * Execute the Agentic Trader CLI with the provided arguments, trying configured executable entrypoints until one succeeds.
 *
 * @param args - Command-line arguments to pass to the Agentic Trader CLI (e.g., `["run", "--symbol", "AAPL"]`)
 * @param options.expectJson - If `true`, parse and return `stdout` as JSON; otherwise return raw `stdout` and `stderr`
 * @param options.timeoutMs - Process execution timeout in milliseconds
 * @returns When `expectJson` is `true`, the parsed JSON result from `stdout`; otherwise an object `{ stdout, stderr }` with the command output
 * @throws Error when a command invocation fails with a non-ENOENT error (message includes the command's `stderr`, `stdout`, or error message), or when no suitable Agentic Trader executable is available
 */
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
        return JSON.parse(stdout || '{}');
      }
      return { stdout, stderr };
    } catch (error: any) {
      lastError = error;
      if (error && typeof error === 'object' && error.code !== 'ENOENT') {
        const detail = error.stderr || error.stdout || error.message;
        throw new Error(
          String(detail).trim() || 'Agentic Trader command failed.',
        );
      }
    }
  }

  throw new Error(
    extractError(lastError || 'No Agentic Trader executable was available.'),
  );
}

/**
 * Fetches the Agentic Trader dashboard snapshot.
 *
 * @returns The dashboard data parsed from the CLI's JSON output.
 */
export async function getDashboardSnapshot(): Promise<any> {
  return execTrader(['dashboard-snapshot', '--log-limit', '14'], {
    expectJson: true,
    timeoutMs: 30_000,
  });
}

/**
 * Orchestrates runtime actions (start, stop, restart, one-shot) for the Agentic Trader and returns a message and updated dashboard.
 *
 * @param kind - Action to perform: "start", "stop", "restart", or "one-shot".
 * @returns An object with a human-readable `message` describing the outcome and the current `dashboard` snapshot.
 * @throws Error if `kind` is unsupported.
 */
export async function runRuntimeAction(kind: string): Promise<{
  message: string;
  dashboard: any;
}> {
  const data = await getDashboardSnapshot();

  if (kind === 'start') {
    if (isTraderRunning(data)) {
      return {
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? '-'}.`,
        dashboard: data,
      };
    }
    const symbols = defaultSymbolsFromPreferences(data?.preferences || {});
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await execTrader(
      [
        'launch',
        '--symbols',
        symbols,
        '--interval',
        interval,
        '--lookback',
        lookback,
        '--continuous',
        '--background',
        '--poll-seconds',
        '300',
      ],
      { timeoutMs: 60_000 },
    );
    return {
      message: `Background runtime launch requested for ${symbols} (${interval}, ${lookback}).`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === 'stop') {
    if (!isTraderRunning(data)) {
      return {
        message: 'No managed runtime is currently active.',
        dashboard: data,
      };
    }
    await execTrader(['stop-service'], { timeoutMs: 30_000 });
    return {
      message: `Stop requested for PID ${data.status.state.pid}.`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === 'restart') {
    if ((data?.status?.state?.symbols || []).length) {
      await execTrader(['restart-service'], { timeoutMs: 30_000 });
      return {
        message: 'Background runtime restart requested.',
        dashboard: await getDashboardSnapshot(),
      };
    }
    return {
      message: 'No saved runtime launch config is available yet.',
      dashboard: data,
    };
  }

  if (kind === 'one-shot') {
    if (isTraderRunning(data)) {
      return {
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? '-'}. Stop it before running a one-shot cycle.`,
        dashboard: data,
      };
    }
    const symbol = defaultSingleSymbol(data);
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await execTrader(
      [
        'run',
        '--symbol',
        symbol,
        '--interval',
        interval,
        '--lookback',
        lookback,
      ],
      { timeoutMs: 240_000 },
    );
    return {
      message: `Strict one-shot cycle completed for ${symbol} (${interval}, ${lookback}).`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  throw new Error(`Unsupported runtime action: ${kind}`);
}

/**
 * Sends an instruction message to the Agentic Trader CLI and returns the CLI's JSON response.
 *
 * @param message - The plaintext instruction to send to the CLI.
 * @param apply - If `true`, apply the instruction; if `false`, perform a non-applying evaluation (dry run).
 * @returns The parsed JSON response produced by the Agentic Trader CLI.
 */
export async function runInstruction(
  message: string,
  apply: boolean,
): Promise<any> {
  const args = ['instruct', '--json', '--message', message];
  if (apply) {
    args.push('--apply');
  }
  return execTrader(args, {
    expectJson: true,
    timeoutMs: 180_000,
  });
}

/**
 * Send a chat message as a specified persona to the Agentic Trader.
 *
 * @param persona - The persona name to use for the chat assistant
 * @param message - The chat message to send
 * @returns The parsed JSON response produced by the chat command
 */
export async function runChat(persona: string, message: string): Promise<any> {
  return execTrader(
    ['chat', '--json', '--persona', persona, '--message', message],
    {
      expectJson: true,
      timeoutMs: 180_000,
    },
  );
}
