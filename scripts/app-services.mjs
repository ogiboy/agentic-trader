#!/usr/bin/env node
import {
  ownershipModeFor,
  parseJsonPayload,
  resolveAgenticTrader,
  runLifecycleCommand,
} from './lib/app-lifecycle.mjs';

const SERVICE_IDS = ['model-service', 'camofox-service', 'webgui-service'];

/**
 * Print the CLI usage help to stdout and exit the process.
 * 
 * Writes the command synopsis, option descriptions, and behavioral notes to standard
 * output, then terminates the process with the provided exit code.
 * @param {number} exitCode - The process exit code to use when terminating (defaults to 0).
 */
function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-services.mjs <start|stop> [options]

Plan or run app-owned service lifecycle slices.

Default behavior is a dry-run plan. Mutating start/stop requires an explicit
service selection plus --yes.

Options:
  --webgui        Select the app-owned Web GUI service.
  --model-service Select the app-owned local model-service.
  --camofox-service Select the app-owned Camofox helper service.
  --all           Select all app-owned helper services.
  --yes           Approve the selected mutating service action.
  --dry-run       Print the service plan without starting or stopping services.
  --json          Emit a machine-readable summary.
  --open-browser  With start + webgui, ask the OS to open the Web GUI URL.
  -h, --help      Show this help.
`);
  process.exit(exitCode);
}

/**
 * Parse CLI arguments into an options object for app service lifecycle commands.
 *
 * Parses a list of arguments, validates the lifecycle mode (`start` or `stop`),
 * processes flags (`--webgui`, `--model-service`, `--camofox-service`, `--all`,
 * `--dry-run`, `--json`, `--open-browser`, `--yes`, `-h/--help`), and returns
 * a populated options object. On invalid or conflicting input the function
 * writes an error to stderr and calls `usage()` which exits the process.
 *
 * @param {string[]} argv - CLI arguments (typically process.argv.slice(2)).
 * @returns {{mode: string, dryRun: boolean, json: boolean, openBrowser: boolean, selectedServices: Set<string>, yes: boolean}}
 *          An options object where `mode` is "start" or "stop", `selectedServices`
 *          is a Set containing any of the SERVICE_IDS, and boolean flags reflect
 *          the parsed options.
 */
function parseArgs(argv) {
  const [mode, ...rest] = argv.filter((arg) => arg !== '--');
  if (mode === '-h' || mode === '--help') {
    usage(0);
  }
  if (mode !== 'start' && mode !== 'stop') {
    process.stderr.write('Expected lifecycle mode: start or stop.\n');
    usage(2);
  }

  const options = {
    mode,
    dryRun: false,
    json: false,
    openBrowser: false,
    selectedServices: new Set(),
    yes: false,
  };

  for (const arg of rest) {
    if (arg === '--webgui') {
      options.selectedServices.add('webgui-service');
    } else if (arg === '--model-service') {
      options.selectedServices.add('model-service');
    } else if (arg === '--camofox-service') {
      options.selectedServices.add('camofox-service');
    } else if (arg === '--all') {
      for (const serviceId of SERVICE_IDS) {
        options.selectedServices.add(serviceId);
      }
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--open-browser') {
      options.openBrowser = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.openBrowser && mode !== 'start') {
    process.stderr.write('--open-browser only applies to app:start.\n');
    usage(2);
  }
  if (options.openBrowser && !options.selectedServices.has('webgui-service')) {
    process.stderr.write('--open-browser requires selecting --webgui or --all.\n');
    usage(2);
  }
  if (options.yes && !options.dryRun && options.selectedServices.size === 0) {
    process.stderr.write('Select at least one service before using --yes.\n');
    usage(2);
  }

  return options;
}

/**
 * Create a step descriptor for an app-owned service lifecycle action.
 * @param {string} id - Step identifier (e.g., service id).
 * @param {string} label - Human-readable step label.
 * @param {string[]} args - Arguments to append to the `agentic-trader` command.
 * @param {boolean} selected - Whether this step was selected for execution.
 * @param {string} reason - Human explanation for the step's selection or omission.
 * @param {{requiresOwner?: {tool: string, mode: string}}} [options] - Optional settings; may include `requiresOwner` describing required ownership (`tool` and `mode`).
 * @returns {{id: string, label: string, command: string[], category: string, mutates: true, selected: boolean, reason: string, requires_owner?: {tool: string, mode: string}}} The constructed step descriptor suitable for planning or execution.
 */
function serviceStep(id, label, args, selected, reason, options = {}) {
  return {
    id,
    label,
    command: ['agentic-trader', ...args],
    category: 'app-owned-service',
    mutates: true,
    selected,
    reason,
    requires_owner: options.requiresOwner,
  };
}

/**
 * Builds the ordered plan of start steps for each app-owned service.
 *
 * Each returned step is a step descriptor for one of: model-service, camofox-service, and webgui-service.
 * The `selected` flag for each step is determined from `options.selectedServices`, and the web GUI step
 * includes an `--open-browser` or `--no-open-browser` argument based on `options.openBrowser`.
 *
 * @param {Object} options - Planner options.
 * @param {Set<string>} options.selectedServices - Set of service ids selected by CLI flags.
 * @param {boolean} options.openBrowser - Whether the web GUI step should include browser-opening.
 * @returns {Array<Object>} An ordered array of step descriptor objects for starting the services.
function startPlan(options) {
  return [
    serviceStep(
      'model-service',
      'Start app-owned loopback Ollama/model-service',
      ['model-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('model-service'),
      'Select with --model-service or --all after provider ownership is configured.',
      { requiresOwner: { tool: 'ollama', mode: 'app-owned' } },
    ),
    serviceStep(
      'camofox-service',
      'Start app-owned loopback Camofox helper',
      ['camofox-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('camofox-service'),
      'Select with --camofox-service or --all after loopback/access-key readiness is configured.',
      { requiresOwner: { tool: 'camofox', mode: 'app-owned' } },
    ),
    serviceStep(
      'webgui-service',
      'Start app-owned loopback Web GUI service',
      [
        'webgui-service',
        'start',
        options.openBrowser ? '--open-browser' : '--no-open-browser',
        '--json',
      ],
      options.selectedServices.has('webgui-service'),
      'Select with --webgui or --all. Browser opening stays opt-in through --open-browser.',
    ),
  ];
}

/**
 * Builds an ordered plan of stop steps for app-owned services.
 *
 * Each step targets one of the supported services and is marked selected when
 * its id is present in options.selectedServices.
 *
 * @param {Object} options - Planner options.
 * @param {Set<string>} options.selectedServices - Service IDs chosen via CLI flags.
 * @returns {Array<Object>} An ordered array of step descriptor objects for stopping services.
 */
function stopPlan(options) {
  return [
    serviceStep(
      'webgui-service',
      'Stop app-owned Web GUI service if recorded by the app',
      ['webgui-service', 'stop', '--json'],
      options.selectedServices.has('webgui-service'),
      'Select with --webgui or --all. Host-owned/external Web GUI listeners are not claimed.',
    ),
    serviceStep(
      'camofox-service',
      'Stop app-owned Camofox helper if recorded by the app',
      ['camofox-service', 'stop', '--json'],
      options.selectedServices.has('camofox-service'),
      'Select with --camofox-service or --all. Host-owned browser helpers are not claimed.',
    ),
    serviceStep(
      'model-service',
      'Stop app-owned model-service if recorded by the app',
      ['model-service', 'stop', '--json'],
      options.selectedServices.has('model-service'),
      'Select with --model-service or --all. Host-owned Ollama on 11434 is preserved.',
    ),
  ];
}

/**
 * Produce human-readable safety and behavior notes for the requested service action.
 *
 * @param {'start'|'stop'} mode - Lifecycle mode indicating the action being planned.
 * @param {{ openBrowser?: boolean }} options - Additional flags affecting behavior.
 * @param {boolean} [options.openBrowser] - When true, indicates the Web GUI will be opened after starting services.
 * @returns {string[]} An ordered list of safety and behavior notes describing dry-run defaults, unchanged artifacts, ownership delegation, and the Web GUI open-browser status.
 */
function safetyNotes(mode, options) {
  const verb = mode === 'start' ? 'starts' : 'stops';
  return [
    `app:${mode} defaults to a dry-run plan and only ${verb} explicitly selected app-owned service surfaces after --yes.`,
    'No dependency install, browser binary fetch, Ollama model pull, provider account, secret, brokerage config, or trading daemon is changed.',
    'Service ownership remains delegated to model-service, camofox-service, and webgui-service safeguards; host-owned processes must not be killed or claimed.',
    options.openBrowser
      ? 'Web GUI browser opening was explicitly requested with --open-browser.'
      : 'Web GUI browser opening is disabled by default; pass --open-browser when that is intended.',
  ];
}

/**
 * Determine whether a selected start step must be blocked due to an ownership mismatch.
 *
 * If `mode` is not `"start"` or the step does not declare `requires_owner`, no blocker is returned.
 * When a required ownership matches the current ownership, no blocker is returned.
 * If the current ownership is `"undecided"`, returns an instruction string to record the required ownership before starting the step.
 * If the current ownership conflicts with the required ownership, returns a message describing the mismatch.
 *
 * @param {Object} step - Step descriptor.
 * @param {string} [step.id] - Identifier of the step (e.g., "model-service").
 * @param {Object} [step.requires_owner] - Ownership requirement, with `tool` and `mode` properties.
 * @param {string} step.requires_owner.tool - The tool whose ownership is being checked (e.g., "ollama").
 * @param {string} step.requires_owner.mode - The required ownership mode (e.g., "app-owned").
 * @param {string} mode - Lifecycle mode, either `"start"` or `"stop"`.
 * @returns {string|null} A blocking message to explain why the step is blocked, or `null` if the step may proceed.
 */
function ownerBlocker(step, mode) {
  if (mode !== 'start' || !step.requires_owner) {
    return null;
  }
  const actual = ownershipModeFor(step.requires_owner.tool);
  if (actual === step.requires_owner.mode) {
    return null;
  }
  if (actual === 'undecided') {
    return `Record ${step.requires_owner.tool} ownership ${step.requires_owner.mode} before starting ${step.id}. Run pnpm run app:up -- --${step.requires_owner.tool}-owner=${step.requires_owner.mode} --${step.id === 'model-service' ? 'model-service' : 'camofox-service'} --yes.`;
  }
  return `${step.id} requires ${step.requires_owner.tool} ownership ${step.requires_owner.mode}; current choice is ${actual}.`;
}

/**
 * Convert a step descriptor into its planned result state, marking blocked, planned, or deferred.
 *
 * @param {Object} step - The step descriptor produced by serviceStep; `step.selected` indicates whether the step was chosen for execution and `step.reason` may contain a human-readable rationale.
 * @param {string} mode - Lifecycle mode, e.g. 'start' or 'stop', used when checking ownership blockers.
 * @returns {Object} A result object containing the original step fields plus:
 *  - `status`: `'blocked'` if an ownership blocker exists, `'planned'` if selected and unblocked, or `'deferred'` if not selected.
 *  - `reason`: the blocker message when blocked, otherwise the original step reason.
 *  - `exit_code`: `1` for blocked steps, `null` otherwise.
 *  - `stdout` and `stderr`: both empty strings.
 */
function plannedStep(step, mode) {
  const blocker = step.selected ? ownerBlocker(step, mode) : null;
  return {
    ...step,
    status: blocker ? 'blocked' : step.selected ? 'planned' : 'deferred',
    reason: blocker ?? step.reason,
    exit_code: blocker ? 1 : null,
    stdout: '',
    stderr: '',
  };
}

/**
 * Mark a planned step as blocked while preserving its metadata.
 * @param {Object} step - The original step descriptor.
 * @param {string} reason - Human-readable explanation for why the step is blocked.
 * @returns {Object} A step result with `status` set to `'blocked'`, `exit_code` set to `1`, `stdout` and `stderr` cleared, and `reason` attached.
 */
function blockedStep(step, reason) {
  return {
    ...step,
    status: 'blocked',
    reason,
    exit_code: 1,
    stdout: '',
    stderr: '',
  };
}

/**
 * Create a skipped step result preserving step metadata and clearing command output.
 * @param {Object} step - Original step descriptor to base the result on.
 * @param {string} reason - Human-readable explanation for why the step was skipped.
 * @returns {Object} A step result object with `status` set to `'skipped'`, `reason` set to the provided message, `exit_code` set to `null`, and empty `stdout`/`stderr`.
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
 * Determines whether a lifecycle command's parsed payload represents success for the given mode.
 * @param {'start'|'stop'} mode - Lifecycle mode, either `'start'` or `'stop'`.
 * @param {any} payload - Parsed JSON payload from the lifecycle command's stdout.
 * @returns {boolean} `true` if the payload indicates success for the mode: for `'start'` when `app_owned` is `true`, for `'stop'` when `app_owned` is not `true`; `false` otherwise.
 */
function commandSucceeded(mode, payload) {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  if (mode === 'start') {
    return payload.app_owned === true;
  }
  return payload.app_owned !== true;
}

/**
 * Executes the lifecycle command for a step and returns the step result with execution details.
 *
 * @param {string} cliPath - Filesystem path to the lifecycle CLI entrypoint used to resolve the command.
 * @param {Object} step - Step descriptor containing at least a `command` array and metadata to preserve.
 * @param {string} mode - Lifecycle mode, e.g. `'start'` or `'stop'`, used to evaluate success semantics.
 * @returns {Object} Result object based on the original step augmented with:
 *  - `resolved_command` (string[]) — the full command executed,
 *  - `status` (`'passed'|'failed'`) — outcome determined from the process exit code and payload semantics,
 *  - `exit_code` (number|null) — process exit code (defaults to `1` when not provided),
 *  - `payload` (Object|null) — parsed JSON payload from stdout when available, otherwise `null`,
 *  - `stdout` (string) — process standard output,
 *  - `stderr` (string) — process standard error.
 */
function runStep(cliPath, step, mode) {
  const completed = runLifecycleCommand([cliPath, ...step.command.slice(1)]);
  const payload = completed.status === 0 ? parseJsonPayload(completed.stdout) : null;
  const passed = completed.status === 0 && commandSucceeded(mode, payload);
  return {
    ...step,
    resolved_command: [cliPath, ...step.command.slice(1)],
    status: passed ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

/**
 * Plan and optionally execute the service lifecycle steps, returning a structured result and exit code.
 *
 * Builds a step plan for starting or stopping app-owned services, evaluates ownership and blockers,
 * executes lifecycle commands when permitted, and aggregates step results with safety notes and next commands.
 *
 * @param {Object} options - Runtime options controlling planning and execution.
 * @param {'start'|'stop'} options.mode - Lifecycle action to plan/execute.
 * @param {boolean} options.yes - Whether the user approved performing mutations.
 * @param {boolean} options.dryRun - Whether to force a dry run (overrides approval).
 * @param {Set<string>} options.selectedServices - Set of service IDs explicitly selected.
 * @param {boolean} [options.openBrowser] - Whether to request opening the web GUI when starting.
 * @returns {{payload: Object, exitCode: number}} An object containing:
 *   - payload.action: the requested mode (`'start'` or `'stop'`),
 *   - payload.mode: the string `'services'`,
 *   - payload.dry_run: whether this run was a dry run,
 *   - payload.mutated: whether any mutation was attempted,
 *   - payload.approved: the original `options.yes` value,
 *   - payload.selected_services: array of selected service IDs,
 *   - payload.cli_path: resolved path to the agentic-trader entrypoint (or null),
 *   - payload.open_browser: mirrors `options.openBrowser`,
 *   - payload.safety_notes: array of safety/behavior notes,
 *   - payload.steps: ordered array of step result objects,
 *   - payload.next_commands: suggested follow-up commands;
 *   - exitCode: aggregated process exit code (0 on success, 1 on any failure/block).
 */
function buildPayload(options) {
  const dryRun = !(options.yes && !options.dryRun);
  const cliPath = resolveAgenticTrader();
  const plan = options.mode === 'start' ? startPlan(options) : stopPlan(options);
  const selectedServices = SERVICE_IDS.filter((serviceId) => options.selectedServices.has(serviceId));
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of plan) {
    if (!step.selected || dryRun) {
      const planned = plannedStep(step, options.mode);
      results.push(planned);
      if (!dryRun && step.selected && planned.status === 'blocked') {
        exitCode = 1;
        previousFailure = true;
      }
      continue;
    }
    if (!cliPath) {
      results.push(blockedStep(step, 'agentic-trader entrypoint was not found. Run make setup, then retry the lifecycle command.'));
      exitCode = 1;
      continue;
    }
    if (options.mode === 'start' && previousFailure) {
      results.push(skippedStep(step, 'A previous selected start step failed.'));
      continue;
    }
    const blocker = ownerBlocker(step, options.mode);
    if (blocker) {
      results.push(blockedStep(step, blocker));
      exitCode = 1;
      previousFailure = true;
      continue;
    }

    attemptedMutation = true;
    const result = runStep(cliPath, step, options.mode);
    results.push(result);
    if (result.status !== 'passed') {
      exitCode = 1;
      previousFailure = true;
    }
  }

  return {
    payload: {
      action: options.mode,
      mode: 'services',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      selected_services: selectedServices,
      cli_path: cliPath,
      open_browser: options.openBrowser,
      safety_notes: safetyNotes(options.mode, options),
      steps: results,
      next_commands: [
        'pnpm run app:doctor',
        'pnpm run app:start -- --webgui --yes',
        'pnpm run app:stop -- --all --yes',
      ],
    },
    exitCode,
  };
}

/**
 * Print a human-readable report of the planned or executed service lifecycle actions to stdout.
 *
 * Prints the overall action, dry-run status, selected services (or "none"), and a line per step
 * with a short status marker (`ok`, `fail`, or the step status), step id and label. If a step is
 * `deferred` or `blocked` and includes a `reason`, that reason is printed indented on the next line.
 * When `payload.dry_run` is true, prints a suggested command to run the Web GUI action.
 *
 * @param {Object} payload - The plan or execution payload.
 * @param {string} payload.action - The action name (e.g., `"start"` or `"stop"`).
 * @param {boolean} payload.dry_run - Whether the run was a dry run.
 * @param {Array<string>} payload.selected_services - List of selected service ids.
 * @param {Array<Object>} payload.steps - Ordered list of step result objects; each step should
 *   include `id`, `label`, `status`, and optionally `reason`.
 */
function renderHuman(payload) {
  process.stdout.write(`Agentic Trader app:${payload.action}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  if (payload.selected_services.length > 0) {
    process.stdout.write(`selected: ${payload.selected_services.join(', ')}\n`);
  } else {
    process.stdout.write('selected: none\n');
  }
  for (const step of payload.steps) {
    const marker = step.status === 'passed' ? 'ok' : step.status === 'failed' ? 'fail' : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.status === 'deferred' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
    if (step.status === 'blocked' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(`Run pnpm run app:${payload.action} -- --webgui --yes to ${payload.action} the Web GUI service only.\n`);
  }
}

/**
 * Parse CLI arguments, build the service action payload, emit either JSON or human-readable output, and terminate the process with the aggregated exit code.
 *
 * The function reads arguments from process.argv, computes the planned or executed steps via the planner/executor, writes pretty JSON when the `--json` option was provided or human-friendly text otherwise, and calls process.exit with the final exit code.
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
