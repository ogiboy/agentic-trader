import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { cliExecutionUnavailable } from './copy.mjs';

const execFileAsync = promisify(execFile);
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;
const once = process.argv.includes('--once');
const projectRoot = fileURLToPath(new URL('..', import.meta.url));

async function execCli(args, { expectJson = false } = {}) {
  const attempts = [];
  if (pythonExecutable) {
    attempts.push([pythonExecutable, ['-m', 'agentic_trader.cli', ...args]]);
  }
  if (cliExecutable) {
    attempts.push([cliExecutable, args]);
  }

  let lastError;
  for (const [command, commandArgs] of attempts) {
    try {
      const { stdout, stderr } = await execFileAsync(command, commandArgs, {
        cwd: projectRoot,
        env: process.env,
        maxBuffer: 1024 * 1024 * 8,
      });
      return expectJson ? JSON.parse(stdout) : { stdout, stderr };
    } catch (error) {
      lastError = error;
      if (error && typeof error === 'object' && error.code !== 'ENOENT') {
        throw error;
      }
    }
  }

  throw lastError || new Error(cliExecutionUnavailable);
}

function runJsonCommand(args) {
  return execCli(args, { expectJson: true });
}

function runTextCommand(args) {
  return execCli(args, { expectJson: false });
}

export { cliExecutable, execCli, once, runJsonCommand, runTextCommand };
