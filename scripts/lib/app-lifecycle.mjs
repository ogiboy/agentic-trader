import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

export function commandExists(command) {
  const result = spawnSync('sh', ['-c', 'command -v "$1"', 'sh', command], {
    cwd: ROOT_DIR,
    encoding: 'utf8',
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

export function resolveAgenticTrader() {
  if (Object.prototype.hasOwnProperty.call(process.env, 'AGENTIC_TRADER_CLI')) {
    return process.env.AGENTIC_TRADER_CLI || null;
  }
  const worktreeEntrypoint = join(ROOT_DIR, '.venv/bin/agentic-trader');
  if (existsSync(worktreeEntrypoint)) {
    return worktreeEntrypoint;
  }
  return commandExists('agentic-trader');
}

export function parseJsonPayload(stdout) {
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

export function runLifecycleCommand(command, options = {}) {
  return spawnSync(command[0], command.slice(1), {
    cwd: options.cwd ?? ROOT_DIR,
    env: options.env ?? process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
}
