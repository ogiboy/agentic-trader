#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const RESEARCH_FLOW_DIR = join(ROOT_DIR, 'sidecars', 'research_flow');

const SCOPE_IDS = ['core', 'sidecar', 'camofox', 'build', 'status'];

/**
 * Print the command-line usage message to stdout and terminate the process.
 *
 * Writes the script's help text describing available options and then exits
 * using the provided exit code.
 *
 * @param {number} exitCode - Process exit code to use when terminating (default: 0).
 */
function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-update.mjs [options]

Plan or run the app update lifecycle lane.

Default behavior is a dry-run plan. Mutating updates require selecting one or
more scopes plus --yes.

Options:
  --core     Update root pnpm workspace and root uv lock/env owners.
  --sidecar  Update the CrewAI Flow sidecar uv lock/env owner.
  --camofox  Update optional Camofox helper package dependencies only.
  --build    Run repository build/check validation after selected updates.
  --status   Run app:doctor after selected updates.
  --all      Select every update, build, and status scope.
  --yes      Approve selected update actions.
  --dry-run  Print the update plan without running commands.
  --json     Emit a machine-readable summary.
  -h, --help Show this help.
`);
  process.exit(exitCode);
}

/**
 * Parse CLI arguments into an options object for the scoped update script.
 *
 * Recognizes scope flags (--core, --sidecar, --camofox, --build, --status, --all),
 * execution flags (--yes, --dry-run) and output flags (--json). Unknown options
 * cause an error message to stderr and invoke usage(2). If `--yes` is provided
 * without `--dry-run` and no scopes are selected, an error is written to stderr
 * and usage(2) is invoked to prevent accidental mutating runs.
 *
 * @param {string[]} argv - Command-line arguments to parse (typically process.argv.slice(2)).
 * @returns {{ dryRun: boolean, json: boolean, selectedScopes: Set<string>, yes: boolean }}
 * An options object:
 * - dryRun: true when planning-only mode was requested.
 * - json: true when JSON output was requested.
 * - selectedScopes: set of selected scope identifiers (subset of SCOPE_IDS).
 * - yes: true when the user approved executing mutating steps.
 */
function parseArgs(argv) {
  const options = {
    dryRun: false,
    json: false,
    selectedScopes: new Set(),
    yes: false,
  };

  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--core') {
      options.selectedScopes.add('core');
    } else if (arg === '--sidecar') {
      options.selectedScopes.add('sidecar');
    } else if (arg === '--camofox') {
      options.selectedScopes.add('camofox');
    } else if (arg === '--build') {
      options.selectedScopes.add('build');
    } else if (arg === '--status') {
      options.selectedScopes.add('status');
    } else if (arg === '--all') {
      for (const scope of SCOPE_IDS) {
        options.selectedScopes.add(scope);
      }
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.yes && !options.dryRun && options.selectedScopes.size === 0) {
    process.stderr.write('Select at least one update scope before using --yes.\n');
    usage(2);
  }

  return options;
}

/**
 * Create a standardized plan step descriptor for the update lifecycle.
 * @param {string} id - Unique step identifier.
 * @param {string} label - Short human-friendly name for the step.
 * @param {string[]} command - Command and its arguments to execute.
 * @param {string} scope - Scope identifier for the step (e.g. 'core', 'sidecar', 'camofox', 'build', 'status').
 * @param {Object} [options] - Optional overrides.
 * @param {string} [options.cwd] - Working directory for the command; defaults to the repository root.
 * @param {boolean} [options.mutates=true] - Whether the step performs mutating changes.
 * @param {string} [options.reason] - Optional reason shown when the step is planned or skipped.
 * @returns {Object} A step descriptor containing `id`, `label`, `command`, `cwd`, `scope`, `mutates`, `selected`, and `reason`.
 */
function updateStep(id, label, command, scope, options = {}) {
  return {
    id,
    label,
    command,
    cwd: options.cwd ?? ROOT_DIR,
    scope,
    mutates: options.mutates ?? true,
    selected: false,
    reason: options.reason,
  };
}

/**
 * Constructs the ordered list of lifecycle update steps for a scoped "app update".
 *
 * The plan includes core mutating steps (workspace & Python lock/sync), sidecar lock/sync for the Research Flow,
 * an optional Camofox helper update, non-mutating build checks, and a final status/reporting step.
 * @returns {Array<Object>} An array of step descriptor objects. Each object contains `id`, `label`, `command`, `cwd`, `scope`, `mutates`, `selected`, and optionally `reason`.
 */
function updatePlan() {
  return [
    updateStep(
      'root-node-workspace',
      'Update root pnpm workspace dependency resolution',
      ['pnpm', 'update', '--recursive', '--latest'],
      'core',
    ),
    updateStep(
      'root-python-lock',
      'Upgrade root uv lock metadata',
      ['uv', 'lock', '--upgrade'],
      'core',
    ),
    updateStep(
      'root-python-sync',
      'Sync root uv Python environment with dev extras',
      ['uv', 'sync', '--locked', '--all-extras', '--group', 'dev'],
      'core',
    ),
    updateStep(
      'research-flow-lock',
      'Upgrade CrewAI Flow sidecar uv lock metadata',
      ['uv', 'lock', '--upgrade'],
      'sidecar',
      { cwd: RESEARCH_FLOW_DIR },
    ),
    updateStep(
      'research-flow-sync',
      'Sync CrewAI Flow sidecar uv environment',
      ['uv', 'sync', '--locked'],
      'sidecar',
      { cwd: RESEARCH_FLOW_DIR },
    ),
    updateStep(
      'camofox-tool-root',
      'Update optional Camofox helper package dependencies without fetching browser binaries',
      ['pnpm', '--dir', 'tools/camofox-browser', '--ignore-workspace', 'update'],
      'camofox',
      {
        reason: 'Browser binary fetch remains explicit through fetch:camofox and is not part of app:update.',
      },
    ),
    updateStep(
      'workspace-check',
      'Run repository static/build/test checks after selected updates',
      ['pnpm', 'run', 'check'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'research-flow-check',
      'Run CrewAI Flow sidecar checks after selected updates',
      ['pnpm', 'run', 'check:research-flow'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'camofox-check',
      'Run optional Camofox helper syntax check after selected updates',
      ['pnpm', 'run', 'check:camofox'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'app-doctor',
      'Report setup, provider, V1, and app-owned service readiness after updates',
      ['pnpm', 'run', 'app:doctor', '--', '--json'],
      'status',
      { mutates: false },
    ),
  ];
}

/**
 * Provide the set of human-readable safety statements describing what the scoped update lane does and does not perform.
 * @returns {string[]} An array of safety-note strings included in the produced payload and CLI output.
 */
function safetyNotes() {
  return [
    'app:update defaults to a dry-run plan.',
    'Mutating updates require an explicit scope plus --yes.',
    'The update lane uses native dependency owners: pnpm for Node workspaces/tool roots and uv for Python locks/environments.',
    'No trading daemon, app-owned service start/stop, browser binary fetch, Ollama model pull, provider account, secret, brokerage config, or runtime state deletion is performed.',
  ];
}

/**
 * Mark steps as selected when their scope is present in the provided set.
 * @param {Array<Object>} plan - Array of step descriptors.
 * @param {Set<string>} selectedScopes - Set of scope identifiers to select.
 * @returns {Array<Object>} The plan with each step's `selected` property set to `true` if its `scope` is in `selectedScopes`, otherwise `false`.
 */
function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

/**
 * Produce a planning-only representation of a step for output.
 * @param {object} step - The original step descriptor.
 * @param {Set<string>} selectedScopes - Set of currently selected scope ids.
 * @returns {object} The step object augmented for planning with:
 *   - `status`: `'planned'` if no scopes are selected or the step is selected, `'deferred'` otherwise.
 *   - `exit_code`: always `null`.
 *   - `stdout`: empty string.
 *   - `stderr`: empty string.
 */
function plannedStep(step, selectedScopes) {
  return {
    ...step,
    status:
      selectedScopes.size === 0 || step.selected
        ? 'planned'
        : 'deferred',
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

/**
 * Mark a planned or pending step as skipped and attach a reason.
 *
 * @param {Object} step - The step descriptor to mark as skipped.
 * @param {string} reason - A human-readable explanation why the step was skipped.
 * @returns {Object} The step augmented with `status: 'skipped'`, the provided `reason`, `exit_code` set to `null`, and empty `stdout` and `stderr`.
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
 * Execute a plan step's command and return the step augmented with its execution result.
 * @param {{ id: string, label?: string, command: string[], cwd?: string, mutates?: boolean, scope?: string, selected?: boolean, reason?: string }} step - Step descriptor; `command` is the argv-style array where the first element is the executable and the rest are arguments, `cwd` is the working directory (defaults to repository root).
 * @returns {{ id: string, label?: string, command: string[], cwd?: string, mutates?: boolean, scope?: string, selected?: boolean, reason?: string, status: 'passed'|'failed', exit_code: number, stdout: string, stderr: string }} The original step fields plus:
 * - `status`: `'passed'` when the process exited with code 0, `'failed'` otherwise.
 * - `exit_code`: numeric exit code (uses `1` when the actual code is unavailable).
 * - `stdout`: captured standard output as a UTF-8 string.
 * - `stderr`: captured standard error as a UTF-8 string.
 */
function runStep(step) {
  const completed = spawnSync(step.command[0], step.command.slice(1), {
    cwd: step.cwd,
    env: process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

/**
 * Builds the update payload describing planned and executed steps for a scoped app update.
 *
 * Produces a plan from the configured update steps, marks steps as planned when in dry-run or when their
 * scope is not selected, executes selected steps sequentially when approved, stops executing remaining
 * selected steps after the first execution failure, and records whether any mutating steps were run.
 *
 * @param {Object} options - Invocation options.
 * @param {Set<string>} options.selectedScopes - Scopes selected for execution (subset of allowed scope IDs).
 * @param {boolean} options.yes - Approval flag; when true (and not overridden by dryRun) permits execution of selected steps.
 * @param {boolean} options.dryRun - Explicit dry-run request; when true, no steps are executed.
 * @returns {{ payload: Object, exitCode: number }} An object containing:
 *   - payload.action: `'update'` indicating the action.
 *   - payload.mode: `'scoped'` indicating scoped execution.
 *   - payload.dry_run: boolean indicating whether the run was a dry-run.
 *   - payload.approved: boolean reflecting the `options.yes` approval.
 *   - payload.mutated: boolean set to true if any mutating step was executed.
 *   - payload.selected_scopes: array of selected scope ids.
 *   - payload.safety_notes: array of safety note strings.
 *   - payload.steps: array of step result objects (planned, skipped, or executed).
 *   - payload.next_commands: array of suggested follow-up commands.
 *   - exitCode: 0 when all executed steps succeeded (or none executed), 1 if any executed step failed.
 */
function buildPayload(options) {
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectSteps(updatePlan(), selectedScopes);
  const steps = [];
  let exitCode = 0;
  let mutated = false;
  let previousFailure = false;

  for (const step of plan) {
    if (dryRun || !step.selected) {
      steps.push(plannedStep(step, selectedScopes));
      continue;
    }
    if (previousFailure) {
      steps.push(skippedStep(step, 'A previous selected update step failed.'));
      continue;
    }
    const result = runStep(step);
    steps.push(result);
    mutated = mutated || step.mutates;
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'update',
      mode: 'scoped',
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: SCOPE_IDS.filter((scope) => selectedScopes.has(scope)),
      safety_notes: safetyNotes(),
      steps,
      next_commands: [
        'pnpm run app:update -- --dry-run',
        'pnpm run app:update -- --core --sidecar --build --status --yes',
        'pnpm run app:doctor',
      ],
    },
    exitCode,
  };
}

/**
 * Render a human-readable summary of an update payload to stdout.
 *
 * Prints header information (dry-run state and selected scopes) and a line per step
 * showing status marker, step id, optional working directory, and label. If a step
 * includes a `reason` it is printed indented on the following line. When `payload.dry_run`
 * is true, prints an instruction for executing a scoped update.
 *
 * @param {Object} payload - The update payload produced by buildPayload().
 * @param {boolean} payload.dry_run - Whether the payload is a dry-run.
 * @param {string[]} payload.selected_scopes - List of selected scope identifiers.
 * @param {Array<Object>} payload.steps - Ordered list of step result objects.
 * @param {string} payload.steps[].id - Step identifier.
 * @param {string} payload.steps[].label - Human-readable step label.
 * @param {string} payload.steps[].cwd - Working directory where the step runs.
 * @param {string} payload.steps[].status - Step status (`planned`, `deferred`, `skipped`, `passed`, `failed`, etc.).
 * @param {string} [payload.steps[].reason] - Optional reason or note for the step.
 */
function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:update\n');
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    const cwdNote = step.cwd === ROOT_DIR ? '' : ` (${step.cwd})`;
    process.stdout.write(`${marker} ${step.id}${cwdNote}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:update -- --core --build --status --yes to execute a scoped update lane.\n');
  }
}

/**
 * Parse CLI arguments, produce the scoped update payload, print it as JSON or human-readable text, and exit.
 *
 * This function reads command-line options, constructs the update plan and execution payload, writes the payload
 * to stdout either as pretty-printed JSON when `--json` is set or as human-readable output otherwise, and then
 * terminates the process with the payload's exit code.
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
