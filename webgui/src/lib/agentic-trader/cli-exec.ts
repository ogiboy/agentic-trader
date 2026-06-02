import { execFile } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { redactAndCapText } from '../http/redaction';
import { asRecord, asString } from '../json-record';

const execFileAsync = promisify(execFile);
const moduleDir = dirname(fileURLToPath(import.meta.url));

export type ExecOptions = {
  expectJson?: boolean;
  timeoutMs?: number;
};

const TRANSIENT_DUCKDB_LOCK_PATTERN =
  /Could not set lock on file|Conflicting lock is held/i;
const DB_LOCK_RETRY_DELAYS_MS =
  process.env.NODE_ENV === 'test' ? [0, 0, 0] : [500, 1_500, 3_000, 5_000];

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

const workspaceRootCandidates = [process.cwd(), resolve(moduleDir, '../../../..')];
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

function detectManagedCondaEnvName(): null | string {
  const manifestPath = resolve(
    workspaceRoot,
    '.codex/environments/environment.toml',
  );
  if (!existsSync(manifestPath)) {
    return null;
  }
  const manifest = readFileSync(manifestPath, 'utf-8');
  const match = /conda activate ([^\s'"]+)/.exec(manifest);
  return match?.[1] || null;
}

function detectManagedPythonExecutable(): null | string {
  if (process.env.VIRTUAL_ENV) {
    const virtualEnvPython = resolve(process.env.VIRTUAL_ENV, 'bin', 'python');
    if (existsSync(virtualEnvPython)) {
      return virtualEnvPython;
    }
  }

  const uvVenvPython = resolve(workspaceRoot, '.venv', 'bin', 'python');
  if (existsSync(uvVenvPython)) {
    return uvVenvPython;
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

function extractError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function isTransientDuckDbLockError(error: unknown): boolean {
  return TRANSIENT_DUCKDB_LOCK_PATTERN.test(extractError(error));
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function execTrader(
  args: string[],
  { expectJson = false, timeoutMs = 30_000 }: ExecOptions = {},
): Promise<unknown> {
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
    } catch (error) {
      lastError = error;
      const errorRecord = asRecord(error);
      if (errorRecord.code !== 'ENOENT') {
        const detail =
          asString(errorRecord.stderr, '') ||
          asString(errorRecord.stdout, '') ||
          asString(errorRecord.message, '');
        throw new Error(
          redactAndCapText(detail).trim() || 'Agentic Trader command failed.',
        );
      }
    }
  }

  throw new Error(
    redactAndCapText(
      extractError(lastError || 'No Agentic Trader executable was available.'),
    ),
  );
}

export async function execTraderWithDbLockRetry(
  args: string[],
  options: ExecOptions,
): Promise<unknown> {
  let lastError: unknown;
  for (const retryDelayMs of [0, ...DB_LOCK_RETRY_DELAYS_MS]) {
    if (retryDelayMs > 0) {
      await sleep(retryDelayMs);
    }
    try {
      return await execTrader(args, options);
    } catch (error) {
      lastError = error;
      if (!isTransientDuckDbLockError(error)) {
        throw error;
      }
    }
  }
  throw lastError;
}
