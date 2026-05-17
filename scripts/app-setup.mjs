#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');

/**
 * Print the CLI usage/help message to stdout and terminate the process with the given exit code.
 * @param {number} [exitCode=0] - Exit code to use when exiting the process.
 */
function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-setup.mjs [options]

Plan or run the conservative setup lifecycle slice.

Default behavior is a dry-run plan. The only mutating path implemented in this
slice is explicit core dependency repair with --core --yes.

Options:
  --core      Select root Node workspace and root uv Python repair.
  --yes       Approve the selected mutating setup scope.
  --dry-run   Print the setup plan without running mutating commands.
  --json      Emit a machine-readable summary.
  -h, --help  Show this help.
`);
  process.exit(exitCode);
}

/**
 * Parse CLI arguments for the app-setup script into an options object.
 *
 * @param {string[]} argv - Command-line arguments to parse (typically process.argv.slice(2)).
 * @returns {{core: boolean, dryRun: boolean, json: boolean, yes: boolean}} An object with boolean flags:
 *  - `core`: whether core-only mode was requested.
 *  - `dryRun`: whether to perform a dry-run plan.
 *  - `json`: whether output should be JSON.
 *  - `yes`: whether mutating actions are approved.
 *
 * If an unknown option is encountered, the function writes an error to stderr and calls `usage(2)` (which exits).
 * If `--yes` is provided without `--core` and without `--dry-run`, the function writes an explanatory error to stderr and calls `usage(2)` (which exits).
 */
function parseArgs(argv) {
  const options = {
    core: false,
    dryRun: false,
    json: false,
    yes: false,
  };
  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--core') {
      options.core = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }
  if (options.yes && !options.core && !options.dryRun) {
    process.stderr.write('The current app:setup slice requires --core before --yes can mutate setup.\n');
    usage(2);
  }
  return options;
}

/**
 * Create a step descriptor representing a core, mutating, selected setup step.
 *
 * @param {string} id - Unique step identifier.
 * @param {string} label - Human-readable step label.
 * @param {string[]} command - Command array where the first element is the executable and remaining elements are arguments.
 * @returns {{id: string, label: string, command: string[], category: 'core', mutates: true, selected: true}} The step descriptor object.
 */
function coreStep(id, label, command) {
  return {
    id,
    label,
    command,
    category: 'core',
    mutates: true,
    selected: true,
  };
}

/**
 * Create a descriptor for a non-mutating, not-selected setup step that is deferred.
 * @param {string} id - Unique step identifier.
 * @param {string} label - Human-readable step title.
 * @param {string[]} command - Command array to execute the step (executable followed by args).
 * @param {string} reason - Explanation why this step is deferred and not run by default.
 * @returns {{id:string,label:string,command:string[],category:'deferred',mutates:false,selected:false,reason:string}} The step descriptor object.
 */
function deferredStep(id, label, command, reason) {
  return {
    id,
    label,
    command,
    category: 'deferred',
    mutates: false,
    selected: false,
    reason,
  };
}

/**
 * Provide the ordered setup plan used by the script, combining core mutating steps and deferred non-mutating steps.
 *
 * @returns {Array<Object>} An array of step descriptor objects. Each descriptor includes `id`, `label`, and `command`; core descriptors have `category: 'core'`, `mutates: true`, and `selected: true`; deferred descriptors have `category: 'deferred'`, `mutates: false`, `selected: false` and may include a `reason` explaining why the step is deferred.
 */
function setupPlan() {
  return [
    coreStep('node-workspace', 'Install and verify root/webgui/docs/tui Node workspace dependencies', [
      'pnpm',
      'run',
      'setup:node',
    ]),
    coreStep('python-env', 'Sync the root uv Python 3.13 development environment', [
      'pnpm',
      'run',
      'install:python',
    ]),
    deferredStep('research-flow-sidecar', 'CrewAI Flow sidecar dependency setup', ['pnpm', 'run', 'setup:research-flow'], 'Sidecar setup stays explicit until app:setup grows opt-in side-application ownership.'),
    deferredStep('camofox-deps', 'Camofox helper dependency setup', ['pnpm', 'run', 'setup:camofox'], 'Browser helper setup remains optional and separate from core dependency repair.'),
    deferredStep('camofox-browser', 'Camofox browser binary fetch', ['pnpm', 'run', 'fetch:camofox'], 'Browser downloads require explicit operator approval and are never hidden in app:setup core repair.'),
    deferredStep('model-service-start', 'App-owned Ollama/model-service start', ['agentic-trader', 'model-service', 'start'], 'Provider ownership and model choice must be explicit before starting or pulling models.'),
    deferredStep('camofox-service-start', 'App-owned Camofox service start', ['agentic-trader', 'camofox-service', 'start'], 'Browser-backed helpers require loopback/access-key readiness before service start.'),
    deferredStep('webgui-service-start', 'App-owned Web GUI service start', ['agentic-trader', 'webgui-service', 'start'], 'Web GUI launch belongs to app:up/app:start, not setup repair.'),
  ];
}

/**
 * Human-readable safety notes describing default behavior and the limited mutating scope of the app:setup command.
 * @returns {string[]} An array of note strings included in the setup payload and displayed to users. 
 */
function safetyNotes() {
  return [
    'app:setup defaults to a dry-run plan.',
    'The current mutating scope is only --core --yes: root pnpm workspace setup plus root uv Python sync.',
    'No trading daemon, Web GUI service, model-service, Camofox service, browser binary fetch, Ollama model pull, provider account, secret, or brokerage config is changed.',
    'Optional tools remain deferred until ownership is explicit: host-owned, app-owned, API/key-only, or skipped.',
  ];
}

/**
 * Create a result object representing a planned or deferred step.
 * @param {Object} step - Step descriptor; if `step.selected` is `true` the returned object will have `status: 'planned'`, otherwise `status: 'deferred'`. Original step fields are preserved.
 * @returns {Object} The step result containing the original step fields plus `status`, `exit_code` (null), `stdout` (empty string), and `stderr` (empty string).
 */
function plannedStep(step) {
  return {
    ...step,
    status: step.selected ? 'planned' : 'deferred',
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

/**
 * Produce a standardized result object for a step that was skipped.
 * @param {object} step - Original step descriptor; its fields are preserved in the returned result.
 * @param {string} reason - Explanation for why the step was skipped.
 * @returns {object} Result object containing the original step fields, `status: 'skipped'`, the provided `reason`, `exit_code: null`, and empty `stdout` and `stderr`.
 */
function skippedStep(step, reason) {
  return {
    ...step,
    status: 'skipped',
    reason,
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

/**
 * Execute the step's command and produce a result record that includes execution outcome and captured output.
 * @param {Object} step - Step descriptor. Must include `command` as an array where the first element is the executable and the rest are arguments; other step fields are retained in the returned object.
 * @returns {Object} Result object containing the original step fields plus:
 *  - `status`: `'passed'` if the command exited with code 0, `'failed'` otherwise.
 *  - `exit_code`: numeric exit code (uses `1` if the child process exit code is unavailable).
 *  - `stdout`: captured standard output as a UTF-8 string.
 *  - `stderr`: captured standard error as a UTF-8 string.
 */
function runStep(step) {
  const completed = spawnSync(step.command[0], step.command.slice(1), {
    cwd: ROOT_DIR,
    env: process.env,
    encoding: 'utf8',
    stdio: 'pipe',
    maxBuffer: 10 * 1024 * 1024,
  });
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    spawn_error: completed.error,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

/**
 * Build the setup action payload and determine the process exit code according to the provided options.
 *
 * The function evaluates the configured plan, optionally executes selected core steps (only when
 * `options.core` and `options.yes` are set and `options.dryRun` is not), and aggregates step results,
 * safety notes, and suggested next commands into a structured payload.
 *
 * @param {Object} options - CLI-derived flags that control behavior.
 * @param {boolean} options.core - When true, target core (mutating) steps instead of a read-only plan.
 * @param {boolean} options.dryRun - When true, prevent executing any mutating steps (overridden by internal logic).
 * @param {boolean} options.json - When true, caller intends to render payload as JSON (not used by this function's logic).
 * @param {boolean} options.yes - Approval flag required (with `core`) to actually perform mutations.
 * @returns {{payload: Object, exitCode: number}} An object containing:
 *   - payload.action: `'setup'`.
 *   - payload.mode: `'core'` when `options.core` is true, otherwise `'plan'`.
 *   - payload.dry_run: boolean indicating whether the run was non-mutating.
 *   - payload.mutated: boolean indicating whether any mutating steps were attempted.
 *   - payload.approved: the `options.yes` value.
 *   - payload.safety_notes: array of strings describing safety guidance.
 *   - payload.steps: array of step result objects (each with status, exit_code, stdout, stderr and original step fields).
 *   - payload.next_commands: array of suggested follow-up command strings.
 *   - exitCode: `0` when all executed steps succeeded or no mutation was attempted, `1` if any executed step failed.
 */
function buildPayload(options) {
  const requestedMutation = options.core && options.yes && !options.dryRun;
  const dryRun = !requestedMutation;
  const plan = setupPlan();
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of plan) {
    if (!step.selected) {
      results.push(plannedStep(step));
      continue;
    }
    if (dryRun) {
      results.push(plannedStep(step));
      continue;
    }
    if (previousFailure) {
      results.push(skippedStep(step, 'A previous core setup step failed.'));
      continue;
    }
    attemptedMutation = true;
    const result = runStep(step);
    results.push(result);
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'setup',
      mode: options.core ? 'core' : 'plan',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      safety_notes: safetyNotes(),
      steps: results,
      next_commands: [
        'pnpm run app:doctor',
        'pnpm run app:setup -- --core --yes',
        'pnpm run app:up (future guided first-run path)',
      ],
    },
    exitCode,
  };
}

/**
 * Print a human-readable summary of a setup payload to stdout.
 *
 * Writes a header, the run mode and dry-run status, then lists each step with
 * a status marker (`ok` for `passed`, `fail` for `failed`, otherwise the
 * step's `status`). If a step includes `reason`, it is printed indented on the
 * next line. When `payload.dry_run` is true, prints a final instruction for
 * executing core repairs.
 *
 * @param {Object} payload - The structured setup payload to render.
 * @param {string} payload.mode - The planned action mode (e.g., `"core"` or `"plan"`).
 * @param {boolean} payload.dry_run - Whether the payload represents a dry run.
 * @param {Array<Object>} payload.steps - Ordered list of step result objects.
 * @param {string} payload.steps[].id - Step identifier.
 * @param {string} payload.steps[].label - Human-readable step label.
 * @param {string} payload.steps[].status - Step status (`planned`, `passed`, `failed`, `skipped`, etc.).
 * @param {string} [payload.steps[].reason] - Optional explanation for deferred/skipped steps.
 */
function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:setup\n');
  process.stdout.write(`mode: ${payload.mode}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  for (const step of payload.steps) {
    const marker = step.status === 'passed' ? 'ok' : step.status === 'failed' ? 'fail' : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:setup -- --core --yes to execute only core dependency repair.\n');
  }
}

/**
 * Orchestrates the CLI: parses arguments, builds the setup payload, writes JSON or a human-readable summary, and exits with the computed code.
 *
 * If `--json` is present the payload is printed as formatted JSON to stdout; otherwise a human summary is rendered. This function terminates the process with the resulting exit code.
 */
function main() {
  const options = parseArgs(process.argv.slice(2));
  const { payload, exitCode } = buildPayload(options);
  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    renderHuman(payload);
  }
  process.exit(exitCode);
}

main();
